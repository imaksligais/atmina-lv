"""Pakešu Noul vērtētājs — pg-jev paterns Python pusē.

pg-jev (github.com/realZachi/pg-jev) ir Postgres paplašinājums; atmina dzīvo
SQLite, tāpēc pārņemam tikai tā darba principu: N rindas vienā `state`
(`{"...konteksts", "rows": [...]}`), viens Noul jautājums uz rindu ar
`rows[i]` atsauci, atbildes kešs pēc rindas satura, tokenu skaitītājs.

Jev ir FILTRS pēc nozīmes virs jau atlasītām rindām, ne meklēšanas dzinējs:
sašaurini ar SQL/kNN, tad vērtē ar Jev. Sauc `judge_rows()`; tas krīt atvērti
(`None` rindām, kuru pakete nebija pieejama) un NEKAD neraksta atmina DB.
"""
from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import dataclass, field
from pathlib import Path

from src.db import now_lv
from src.typesafe_client import DEFAULT_MODEL, TypeSafeUnavailable, system_one

log = logging.getLogger(__name__)

DEFAULT_BATCH = 40      # pg-jev noklusējums; 40 × 1 Noul = 40 jautājumi pieprasījumā
DEFAULT_WORKERS = 4     # paralēli pieprasījumi (pg-jev: 6)
# Aplēse no docs rerank cookbook (2026-09-18): 1 536 002 ievades tokeni = $0.0645.
# Nav tarifs — tikai lai izdruka nes lielumu kārtu.
USD_PER_M_INPUT = 0.042
CACHE_PATH = Path("data/jev_cache.db")
ROW_PLACEHOLDER = "{row}"


@dataclass
class JevStats:
    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_hits: int = 0
    unavailable: int = 0
    malformed: int = 0
    models: set[str] = field(default_factory=set)

    @property
    def est_usd(self) -> float:
        return self.input_tokens / 1_000_000 * USD_PER_M_INPUT

    def summary(self) -> str:
        tokens = f"{self.input_tokens:,}".replace(",", " ")   # 1 000 000, ne 1,000,000
        return (f"Jev: pieprasījumi {self.requests}, kešs {self.cache_hits}, "
                f"nepieejamas {self.unavailable}, kļūdainas {self.malformed}, "
                f"ievades tokeni {tokens}, "
                f"izvades {self.output_tokens}, aplēstā cena ${self.est_usd:.2f}"
                f", modelis {'/'.join(sorted(self.models)) or '—'}")


def _canon(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def cache_key(model: str, context: dict | None, instructions: str,
              criteria: dict, row: dict) -> str:
    return hashlib.sha256(_canon([model, context, instructions, criteria, row]).encode("utf-8")).hexdigest()


class JevCache:
    """Atbildes pēc rindas satura + jautājuma; atsevišķs fails, ne atmina.db."""

    def __init__(self, path: Path = CACHE_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._conn()) as db:
            db.execute("CREATE TABLE IF NOT EXISTS answers ("
                       "key TEXT PRIMARY KEY, prob REAL NOT NULL, model TEXT, ts TEXT)")
            db.commit()

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=30.0)

    def get_many(self, keys: list[str]) -> dict[str, tuple[float, str]]:
        if not keys:
            return {}
        out: dict[str, tuple[float, str]] = {}
        with closing(self._conn()) as db:
            for i in range(0, len(keys), 500):
                chunk = keys[i:i + 500]
                q = f"SELECT key, prob, model FROM answers WHERE key IN ({','.join('?' * len(chunk))})"
                for key, prob, model in db.execute(q, chunk).fetchall():
                    out[key] = (prob, model)
        return out

    def put_many(self, items: dict[str, tuple[float, str]]) -> None:
        if not items:
            return
        ts = now_lv()
        with closing(self._conn()) as db:
            db.executemany("INSERT OR REPLACE INTO answers (key, prob, model, ts) VALUES (?, ?, ?, ?)",
                           [(k, p, m, ts) for k, (p, m) in items.items()])
            db.commit()


def _question(i: int, instructions: str, criteria: dict) -> dict:
    return {"type": "noul",
            "instructions": instructions.replace(ROW_PLACEHOLDER, f"rows[{i}]"),
            "criteria": criteria}


def _call_batch(rows: list[dict], instructions: str, criteria: dict,
                context: dict | None, model: str) -> tuple[list[float | None], str, dict, bool]:
    """Viens pieprasījums; atgriež (varbūtības, modelis, usage, responded). Izņēmumu nemet.

    `responded=True`, tiklīdz `system_one` atgriezis atbildes ķermeni — arī
    tad, ja `usage` ir tukšs vai atsevišķas atbildes nav nolasāmas. Tikai
    transporta/pieejamības kļūda (arī nederīgs JSON ķermenis) dod
    `responded=False`, lai pakete netiek jaukta ar "atbildēja, bet slikti".
    """
    state = {**(context or {}), "rows": rows}
    questions = {f"r{i}": _question(i, instructions, criteria) for i in range(len(rows))}
    try:
        resp = system_one(state, questions, model=model)
    except (TypeSafeUnavailable, ValueError, TypeError) as e:
        log.warning("jev_filter: pakete (rindu skaits: %d) nav pieejama: %s", len(rows), e)
        return [None] * len(rows), model, {}, False
    if not isinstance(resp, dict) or not isinstance(resp.get("answers"), dict):
        log.warning("jev_filter: pakete (rindu skaits: %d) — atbildes ķermenis nav vārdnīca ar 'answers': %r",
                    len(rows), type(resp).__name__)
        return [None] * len(rows), model, {}, False
    answers = resp["answers"]
    probs: list[float | None] = []
    bad_count = 0
    bad_example: tuple[str, object] | None = None
    for i in range(len(rows)):
        qid = f"r{i}"
        try:
            probs.append(float(answers[qid]["noul"]))
        except (KeyError, TypeError, ValueError):
            probs.append(None)
            bad_count += 1
            if bad_example is None:
                bad_example = (qid, answers.get(qid))
    if bad_count:
        bad_qid, bad_raw = bad_example
        log.warning("jev_filter: paketē %d no %d atbildēm nav nolasāmas (piemērs: %s=%r)",
                    bad_count, len(rows), bad_qid, bad_raw)
    return probs, str(resp.get("model", model)), resp.get("usage", {}) or {}, True


def judge_rows(rows: list[dict], instructions: str, criteria: dict[str, str], *,
               context: dict | None = None, model: str = DEFAULT_MODEL,
               batch_size: int = DEFAULT_BATCH, workers: int = DEFAULT_WORKERS,
               cache: JevCache | None = None, stats: JevStats | None = None) -> list[float | None]:
    """Noul varbūtība katrai rindai (izlīdzināta ar `rows`); `None` = nav atbildes.

    `instructions` satur `{row}` — to aizstāj ar `rows[i]`, lai jautājums
    norāda uz konkrēto rindu paketes `state`. `context` pievieno kopīgus
    laukus blakus `rows` (piem. `{"politician": "tas pats abos"}`).
    Rindu vērtībām jābūt JSON-natīvām (dict/list/str/int/float/bool/None).
    """
    if ROW_PLACEHOLDER not in instructions:
        raise ValueError(f"instructions must contain {ROW_PLACEHOLDER!r}")
    if context and "rows" in context:
        raise ValueError("context must not contain 'rows'")
    stats = stats if stats is not None else JevStats()
    cache = cache if cache is not None else JevCache()
    keys = [cache_key(model, context, instructions, criteria, r) for r in rows]
    cached = cache.get_many(list(set(keys)))
    result: list[float | None] = [cached[k][0] if k in cached else None for k in keys]
    stats.cache_hits += sum(1 for k in keys if k in cached)
    stats.models.update(m for _, m in cached.values() if m)

    # Vienādas rindas vienā skrējienā sūtām vienreiz.
    todo: dict[str, dict] = {}
    for k, r in zip(keys, rows, strict=True):
        if k not in cached:
            todo.setdefault(k, r)
    todo_keys = list(todo)
    batches = [todo_keys[i:i + batch_size] for i in range(0, len(todo_keys), batch_size)]

    fresh: dict[str, tuple[float, str]] = {}

    def run(batch_keys: list[str]):
        return batch_keys, _call_batch([todo[k] for k in batch_keys], instructions, criteria, context, model)

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        for batch_keys, (probs, used_model, usage, responded) in pool.map(run, batches):
            stats.requests += 1 if responded else 0
            stats.input_tokens += int(usage.get("input_tokens", 0) or 0)
            stats.output_tokens += int(usage.get("output_tokens", 0) or 0)
            batch_fresh: dict[str, tuple[float, str]] = {}
            for k, p in zip(batch_keys, probs, strict=True):
                if p is None:
                    if responded:
                        stats.malformed += 1
                    else:
                        stats.unavailable += 1
                else:
                    batch_fresh[k] = (p, used_model)
                    stats.models.add(used_model)
            # katras paketes svaigās atbildes uzreiz kešā — nogalināts skrējiens nezaudē samaksāto
            cache.put_many(batch_fresh)
            fresh.update(batch_fresh)
    for i, k in enumerate(keys):
        if result[i] is None and k in fresh:
            result[i] = fresh[k][0]
    return result
