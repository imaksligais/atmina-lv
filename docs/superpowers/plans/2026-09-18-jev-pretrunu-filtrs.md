# Jev pretrunu priekšfiltrs — izpildes plāns

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Jev (TypeSafe System One) vērtē pozīciju pārus «vai jaunā nostāja ir pretēja vecajai tajā pašā jautājumā», lai `@contradiction-hunter` / `/deep-check` lasa īsu sarakstu, nevis nesakārtotu kaudzi — ieviešams tikai tad, ja pārbaude uz zināmajām pretrunām neko nepazaudē.

**Architecture:** Trīs slāņi, katrs savā failā. (1) `src/jev_filter.py` — vispārīgs pakešu Noul vērtētājs pēc pg-jev parauga (40 rindas vienā `state`, viens jautājums uz rindu ar `rows[i]` atsauci, kešs pēc rindas satura, tokenu/izmaksu skaitītājs, krīt atvērti). (2) `src/contradiction_candidates.py` — kandidātu pāri no `claim_vectors` (katrai pozīcijai top-k kaimiņi pēc kosinusa, hronoloģiski sakārtoti) + pāra `state` un LV jautājuma teksts. (3) Divi skripti: `scripts/jev_contradiction_eval.py` (zelta tests pret 23 `contradictions` rindām, denominatori pirmie) un `scripts/jev_contradiction_shortlist.py` (īsais saraksts vienam politiķim, ko lasa hunter). Integrācija `/deep-check` un hunter promptā notiek TIKAI pēc zelta testa verdikta.

**Tech Stack:** Python 3 (`.venv`), stdlib `urllib` caur esošo `src/typesafe_client.system_one`, `numpy` (jau instalēts — `src/langdetect.py` to importē), `sqlite_vec`, pytest.

Izmērīts pirms plāna (2026-09-18, sesijas vaicājumi uz `data/atmina.db`):
- `contradictions`: 30 rindas, 27 `confirmed=1`; 23 pāri ir `position`↔`position` (20 apstiprināti + #40, #47, #48 neapstiprināti), 7 ir `position`↔`saeima_vote` (tos Jev NEskar — balsojumu pusi meklē hunter strukturālais SQL, T9).
- Zelta pāru vieta kaimiņu sarakstā (kosinuss `claim_vectors`, pirmās puses pozīcijas): `min_rank` < 40 ir **21/23**; < 100 ir **22/23** (#37 rank 82); #4 rank 132 paliek ārpusē pie jebkura saprātīga k. Tātad kandidātu ģenerēšana ir pilnīguma griesti — ne Jev.
- Pirmās puses pozīciju skaits: 170 politiķi, mediāna 14,5, maksimums 570 (id 10); zelta politiķiem 39…570.
- Divi dzīvi pieprasījumi (430 un 1017 ievades tokeni): 4 spēļu pāri vienā `state` ar `pairs[i]` atsaucēm → 0,97 / 0,13 / 0,05 / 0,91 — pretējie augstu, precizējums un cita tēma zemu. Modelis atbild `jev-1.13.0`, atbildē ir `usage.input_tokens`/`output_tokens`.
- Cena: docs rerank cookbook — 1 536 002 ievades tokeni = $0,0645 → ≈ $0,042 par 1 M ievades tokenu (aplēse, ne tarifs).

## Global Constraints

- Vienmēr `.venv/Scripts/python.exe`, nekad bare `python` (CLAUDE.md § Commands).
- Katrs ceļš pēdiņās — mājas direktorijā ir atstarpe.
- **Neviens tests nesauc API.** Katrs tests, kas skar `judge_rows`, `patch("src.jev_filter.system_one", …)`; `tests/conftest.py` jau piesprauž `ATMINA_TYPESAFE_VETO=off`.
- **Jev nekad neraksta DB.** Neviens no šī plāna failiem nesauc `store_contradiction`, `store_claim` vai `UPDATE`; `contradictions.confirmed` maina tikai operators ar roku.
- **Denominators pirmais.** Katrs skripts pirms atradumiem drukā: cik politiķu, cik pozīciju, cik kandidātu pāru, cik nosūtīts, cik no keša, cik nepieejami, tokeni un aplēstā cena.
- **Krīt atvērti.** `TypeSafeUnavailable` → `None` attiecīgajām rindām, skaitītājs `unavailable`, nekāda izņēmuma uz āru (kā `src/matcher_veto.py`).
- Uz API aiziet tikai `claims.stance`, `claims.quote`, `claims.topic`, `stated_at` — publisku avotu teksts. NE `reasoning`, NE `context_notes`, NE politiķa vārds (nav vajadzīgs spriedumam).
- Kešs `data/jev_cache.db` (`*.db` ir `.gitignore`); nekādas jaunas tabulas `data/atmina.db`.
- Izdevumu vārts: skripts atsakās sūtīt vairāk par `--max-pairs` (noklusējums 80 000) — kā pg-jev `max_rows_per_statement`.
- LV gramatikas vārts attiecas uz jautājuma tekstu un skripta izdruku (tie ir MŪSU vārdi); `stance`/`quote` iet uz API kā ir.
- Katrs uzdevums beidzas ar `bash scripts/check.sh` zaļu un komitu. Commit ziņojumi bez operatoru identificējošas informācijas.

---

### Task 1: `src/jev_filter.py` — pakešu Noul vērtētājs ar kešu un statistiku

**Files:**
- Create: `src/jev_filter.py`
- Test: `tests/test_jev_filter.py`

**Interfaces:**
- Consumes: `src.typesafe_client.system_one(state, questions, *, model, timeout, retries) -> dict` (atbilde `{"model": str, "answers": {qid: {"type":"noul","noul": float}}, "usage": {"input_tokens": int, "output_tokens": int}}`), `src.typesafe_client.TypeSafeUnavailable`, `src.typesafe_client.DEFAULT_MODEL`.
- Produces:
  - `judge_rows(rows: list[dict], instructions: str, criteria: dict[str, str], *, context: dict | None = None, model: str = DEFAULT_MODEL, batch_size: int = 40, workers: int = 4, cache: JevCache | None = None, stats: JevStats | None = None) -> list[float | None]` — `instructions` satur vietturi `{row}`, ko aizstāj ar `rows[i]`; rezultāts izlīdzināts ar `rows`.
  - `JevStats` (dataclass: `requests, input_tokens, output_tokens, cache_hits, unavailable`; īpašība `est_usd`; metode `summary() -> str`).
  - `JevCache(path: Path)` ar `get_many(keys) -> dict[str, float]`, `put_many(items: dict[str, tuple[float, str]])`; `cache_key(model, context, instructions, criteria, row) -> str`.
  - Konstantes `DEFAULT_BATCH = 40`, `DEFAULT_WORKERS = 4`, `USD_PER_M_INPUT = 0.042`, `CACHE_PATH = Path("data/jev_cache.db")`.

- [ ] **Step 1: Uzraksti krītošos testus**

```python
# tests/test_jev_filter.py
"""Pakešu Noul vērtētājs — testi bez API (system_one vienmēr aizstāts)."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src import jev_filter
from src.jev_filter import JevCache, JevStats, cache_key, judge_rows
from src.typesafe_client import TypeSafeUnavailable

INSTR = "Vai `{row}.new` nostāja ir pretēja `{row}.old` nostājai?"
CRIT = {"true": "pretēja", "false": "nav pretēja"}


def _rows(n: int) -> list[dict]:
    return [{"old": f"vecā {i}", "new": f"jaunā {i}"} for i in range(n)]


def _fake_answers(calls: list[dict]):
    """system_one aizstājējs: reģistrē izsaukumus, atbild i/10 katrai rindai."""
    def fake(state, questions, **kw):
        calls.append({"state": state, "questions": questions, "kw": kw})
        answers = {}
        for qid in questions:
            i = int(qid[1:])
            answers[qid] = {"type": "noul", "noul": min(0.99, i / 10)}
        return {"model": "jev-1.13.0", "answers": answers,
                "usage": {"input_tokens": 100 * len(questions), "output_tokens": len(questions)}}
    return fake


@pytest.fixture
def tmp_cache():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield JevCache(Path(path))
    try:
        os.unlink(path)
    except (PermissionError, FileNotFoundError):
        pass


def test_batches_and_aligns_probabilities(tmp_cache):
    calls: list[dict] = []
    stats = JevStats()
    with patch("src.jev_filter.system_one", _fake_answers(calls)):
        probs = judge_rows(_rows(5), INSTR, CRIT, context={"politician": "tas pats"},
                           batch_size=2, workers=1, cache=tmp_cache, stats=stats)
    assert len(calls) == 3                                   # 2 + 2 + 1
    assert [len(c["questions"]) for c in calls] == [2, 2, 1]
    # katra pakete: konteksts + tikai savas rindas; jautājums atsaucas uz rows[i]
    assert calls[0]["state"] == {"politician": "tas pats", "rows": _rows(5)[:2]}
    assert calls[0]["questions"]["r1"]["instructions"] == INSTR.replace("{row}", "rows[1]")
    assert calls[0]["questions"]["r1"]["criteria"] == CRIT
    assert calls[0]["questions"]["r1"]["type"] == "noul"
    # rezultāts izlīdzināts ar ievadi: paketes lokālais indekss, ne globālais
    assert probs == pytest.approx([0.0, 0.1, 0.0, 0.1, 0.0])
    assert stats.requests == 3
    assert stats.input_tokens == 500
    assert stats.output_tokens == 5
    assert stats.cache_hits == 0


def test_cache_hit_skips_request(tmp_cache):
    calls: list[dict] = []
    with patch("src.jev_filter.system_one", _fake_answers(calls)):
        first = judge_rows(_rows(3), INSTR, CRIT, batch_size=40, workers=1, cache=tmp_cache)
        stats = JevStats()
        second = judge_rows(_rows(3), INSTR, CRIT, batch_size=40, workers=1,
                            cache=tmp_cache, stats=stats)
    assert len(calls) == 1
    assert second == first
    assert stats.requests == 0 and stats.cache_hits == 3


def test_cache_key_changes_with_question_and_context():
    row = {"old": "a", "new": "b"}
    k1 = cache_key("jev-latest", None, INSTR, CRIT, row)
    assert k1 == cache_key("jev-latest", None, INSTR, CRIT, dict(row))
    assert k1 != cache_key("jev-latest", {"x": 1}, INSTR, CRIT, row)
    assert k1 != cache_key("jev-latest", None, INSTR + " ?", CRIT, row)
    assert k1 != cache_key("jev-1.13.0", None, INSTR, CRIT, row)


def test_unavailable_batch_yields_none_others_fine(tmp_cache):
    calls: list[dict] = []
    real = _fake_answers(calls)

    def flaky(state, questions, **kw):
        if state["rows"][0]["old"] == "vecā 2":
            raise TypeSafeUnavailable("down")
        return real(state, questions, **kw)

    stats = JevStats()
    with patch("src.jev_filter.system_one", flaky):
        probs = judge_rows(_rows(4), INSTR, CRIT, batch_size=2, workers=1,
                           cache=tmp_cache, stats=stats)
    assert probs[:2] == pytest.approx([0.0, 0.1])
    assert probs[2:] == [None, None]
    assert stats.unavailable == 2
    # nepieejamais NAV kešā — nākamreiz mēģina vēlreiz
    with patch("src.jev_filter.system_one", real):
        again = judge_rows(_rows(4), INSTR, CRIT, batch_size=2, workers=1, cache=tmp_cache)
    assert again[2:] == pytest.approx([0.0, 0.1])


def test_malformed_answer_is_none_not_crash(tmp_cache):
    def bad(state, questions, **kw):
        return {"model": "x", "answers": {"r0": {"type": "noul"}}, "usage": {}}
    with patch("src.jev_filter.system_one", bad):
        assert judge_rows(_rows(1), INSTR, CRIT, workers=1, cache=tmp_cache) == [None]


def test_stats_summary_reports_denominator_and_cost():
    s = JevStats(requests=2, input_tokens=1_000_000, output_tokens=10, cache_hits=3, unavailable=1)
    assert s.est_usd == pytest.approx(jev_filter.USD_PER_M_INPUT)
    text = s.summary()
    for needle in ("pieprasījumi 2", "kešs 3", "nepieejami 1", "1 000 000", "$0.04"):
        assert needle in text, text


def test_instructions_must_contain_row_placeholder(tmp_cache):
    with pytest.raises(ValueError):
        judge_rows(_rows(1), "bez viettura", CRIT, cache=tmp_cache)
```

- [ ] **Step 2: Palaid — jākrīt ar ImportError**

Run: `.venv/Scripts/python.exe -m pytest tests/test_jev_filter.py -q`
Expected: `ImportError: cannot import name 'JevCache' from 'src.jev_filter'` (vai `No module named 'src.jev_filter'`).

- [ ] **Step 3: Uzraksti `src/jev_filter.py`**

```python
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
from dataclasses import dataclass
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

    @property
    def est_usd(self) -> float:
        return self.input_tokens / 1_000_000 * USD_PER_M_INPUT

    def summary(self) -> str:
        tokens = f"{self.input_tokens:,}".replace(",", " ")   # 1 000 000, ne 1,000,000
        return (f"Jev: pieprasījumi {self.requests}, kešs {self.cache_hits}, "
                f"nepieejami {self.unavailable}, ievades tokeni {tokens}, "
                f"izvades {self.output_tokens}, aplēstā cena ${self.est_usd:.2f}")


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
        with self._conn() as db:
            db.execute("CREATE TABLE IF NOT EXISTS answers ("
                       "key TEXT PRIMARY KEY, prob REAL NOT NULL, model TEXT, ts TEXT)")

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=30.0)

    def get_many(self, keys: list[str]) -> dict[str, float]:
        if not keys:
            return {}
        out: dict[str, float] = {}
        with self._conn() as db:
            for i in range(0, len(keys), 500):
                chunk = keys[i:i + 500]
                q = f"SELECT key, prob FROM answers WHERE key IN ({','.join('?' * len(chunk))})"
                out.update(db.execute(q, chunk).fetchall())
        return out

    def put_many(self, items: dict[str, tuple[float, str]]) -> None:
        if not items:
            return
        ts = now_lv()
        with self._conn() as db:
            db.executemany("INSERT OR REPLACE INTO answers (key, prob, model, ts) VALUES (?, ?, ?, ?)",
                           [(k, p, m, ts) for k, (p, m) in items.items()])


def _question(i: int, instructions: str, criteria: dict) -> dict:
    return {"type": "noul",
            "instructions": instructions.replace(ROW_PLACEHOLDER, f"rows[{i}]"),
            "criteria": criteria}


def _call_batch(rows: list[dict], instructions: str, criteria: dict,
                context: dict | None, model: str) -> tuple[list[float | None], str, dict]:
    """Viens pieprasījums; atgriež (varbūtības, modelis, usage). Izņēmumu nemet."""
    state = {**(context or {}), "rows": rows}
    questions = {f"r{i}": _question(i, instructions, criteria) for i in range(len(rows))}
    try:
        resp = system_one(state, questions, model=model)
    except TypeSafeUnavailable as e:
        log.warning("jev_filter: pakete (%d rindas) nav pieejama: %s", len(rows), e)
        return [None] * len(rows), model, {}
    answers = resp.get("answers", {})
    probs: list[float | None] = []
    for i in range(len(rows)):
        try:
            probs.append(float(answers[f"r{i}"]["noul"]))
        except (KeyError, TypeError, ValueError):
            probs.append(None)
    return probs, str(resp.get("model", model)), resp.get("usage", {}) or {}


def judge_rows(rows: list[dict], instructions: str, criteria: dict[str, str], *,
               context: dict | None = None, model: str = DEFAULT_MODEL,
               batch_size: int = DEFAULT_BATCH, workers: int = DEFAULT_WORKERS,
               cache: JevCache | None = None, stats: JevStats | None = None) -> list[float | None]:
    """Noul varbūtība katrai rindai (izlīdzināta ar `rows`); `None` = nav atbildes.

    `instructions` satur `{row}` — to aizstāj ar `rows[i]`, lai jautājums
    norāda uz konkrēto rindu paketes `state`. `context` pievieno kopīgus
    laukus blakus `rows` (piem. `{"politician": "tas pats abos"}`).
    """
    if ROW_PLACEHOLDER not in instructions:
        raise ValueError(f"instructions must contain {ROW_PLACEHOLDER!r}")
    stats = stats if stats is not None else JevStats()
    cache = cache if cache is not None else JevCache()
    keys = [cache_key(model, context, instructions, criteria, r) for r in rows]
    cached = cache.get_many(list(set(keys)))
    result: list[float | None] = [cached.get(k) for k in keys]
    stats.cache_hits += sum(1 for k in keys if k in cached)

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
        for batch_keys, (probs, used_model, usage) in pool.map(run, batches):
            stats.requests += 1 if usage else 0
            stats.input_tokens += int(usage.get("input_tokens", 0) or 0)
            stats.output_tokens += int(usage.get("output_tokens", 0) or 0)
            for k, p in zip(batch_keys, probs, strict=True):
                if p is None:
                    stats.unavailable += 1
                else:
                    fresh[k] = (p, used_model)
    cache.put_many(fresh)
    for i, k in enumerate(keys):
        if result[i] is None and k in fresh:
            result[i] = fresh[k][0]
    return result
```

- [ ] **Step 4: Palaid testus — jāiet zaļi**

Run: `.venv/Scripts/python.exe -m pytest tests/test_jev_filter.py -q`
Expected: `7 passed`.

Piezīme testam `test_batches_and_aligns_probabilities`: `stats.requests` skaita tikai atbildētās paketes (`usage` nav tukšs) — nepieejama pakete nav pieprasījums, tā ir `unavailable`.

- [ ] **Step 5: `bash scripts/check.sh` + commit**

Run: `bash scripts/check.sh`
Expected: ruff tīrs, pytest zaļš, render smoke zaļš.

```bash
git add src/jev_filter.py tests/test_jev_filter.py
git commit -m "Jev pakešu Noul vērtētājs (src/jev_filter.py): 40 rindas/state ar rows[i] atsaucēm, kešs data/jev_cache.db, JevStats ar denominatoru; krīt atvērti, DB neraksta"
```

---

### Task 2: `src/contradiction_candidates.py` — kandidātu pāri no `claim_vectors` + pāra `state` + LV jautājums

**Files:**
- Create: `src/contradiction_candidates.py`
- Test: `tests/test_contradiction_candidates.py`

**Interfaces:**
- Consumes: `src.db.get_db(db_path)`, `src.party_contradictions.ensure_vec(db)`, tabulas `claims` (`id, opponent_id, topic, stance, quote, stated_at, claim_type, speaker_id`) un `claim_vectors(claim_id, embedding float[384])`.
- Produces:
  - `load_position_vectors(db, opponent_id) -> tuple[list[int], np.ndarray]` — pirmās puses `position` pozīcijas AR vektoru, `ids` augošā secībā, matrica `(n, 384)` L2-normēta.
  - `candidate_pairs(opponent_id, *, k: int = DEFAULT_K, db_path: str | None = None) -> list[tuple[int, int]]` — `(old_id, new_id)` hronoloģiski (`stated_at`, tad `id`), unikāli, sakārtoti pēc `(old stated_at, new stated_at, old_id, new_id)`.
  - `pair_states(db, pairs) -> list[dict]` — `{"old": {...}, "new": {...}}` ar laukiem `stance, quote, topic, date` (datums = `stated_at[:10]` vai `""`).
  - Konstantes `DEFAULT_K = 40`, `PAIR_CONTEXT`, `OPPOSITE_INSTRUCTIONS` (satur `{row}`), `OPPOSITE_CRITERIA`.

- [ ] **Step 1: Uzraksti krītošos testus**

```python
# tests/test_contradiction_candidates.py
"""Kandidātu pāri no claim_vectors — bez API, uz pagaidu DB."""
from __future__ import annotations

import os
import struct
import tempfile

import numpy as np
import pytest

from src.contradiction_candidates import (
    OPPOSITE_CRITERIA,
    OPPOSITE_INSTRUCTIONS,
    PAIR_CONTEXT,
    candidate_pairs,
    load_position_vectors,
    pair_states,
)
from src.db import get_db, init_db
from src.party_contradictions import ensure_vec


def _unit(*vals: float) -> list[float]:
    vec = list(vals) + [0.0] * (384 - len(vals))
    n = float(np.linalg.norm(vec)) or 1.0
    return [v / n for v in vec]


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    try:
        os.unlink(path)
    except (PermissionError, FileNotFoundError):
        pass


def _claim(db, cid, pid, stance, stated_at, *, topic="Nodokļi", claim_type="position",
           speaker_id=None, vector=None, quote=None):
    db.execute(
        "INSERT INTO claims (id, opponent_id, topic, stance, quote, source_url, stated_at, "
        "claim_type, speaker_id, document_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)",
        (cid, pid, topic, stance, quote, f"https://x/{cid}", stated_at, claim_type, speaker_id),
    )
    if vector is not None:
        ensure_vec(db)
        db.execute("INSERT INTO claim_vectors (claim_id, embedding) VALUES (?, ?)",
                   (cid, struct.pack("384f", *vector)))


def _seed(db_path):
    db = get_db(db_path)                       # PRAGMA foreign_keys=ON → dokuments 1 jāeksistē
    db.execute("INSERT INTO documents (id, content, content_hash, scraped_at) "
               "VALUES (1, 'teksts', 'h1', '2025-01-01 00:00:00')")
    db.execute("INSERT INTO tracked_politicians (id, name, party) VALUES (7, 'Testa Persona', 'P')")
    db.execute("INSERT INTO tracked_politicians (id, name, party) VALUES (8, 'Cits Cilvēks', 'P')")
    # 1 ↔ 2 gandrīz vienādi; 3 tuvāks 1 nekā 2; 4 ortogonāls
    _claim(db, 1, 7, "Atbalsta nodokļu celšanu", "2025-01-10", vector=_unit(1.0, 0.0, 0.0))
    _claim(db, 2, 7, "Pret nodokļu celšanu", "2025-03-01", vector=_unit(0.95, 0.1, 0.0), quote="Nē!")
    _claim(db, 3, 7, "Nodokļus jāceļ pakāpeniski", "2025-02-01", vector=_unit(0.8, 0.0, 0.3))
    _claim(db, 4, 7, "Rail Baltica jāaptur", "2025-04-01", topic="Rail Baltica", vector=_unit(0.0, 0.0, 1.0))
    _claim(db, 5, 7, "Bez vektora", "2025-05-01")                                   # nav vektora → ārā
    _claim(db, 6, 7, "Balsoja PAR", "2025-05-02", claim_type="saeima_vote", vector=_unit(1.0, 0.0, 0.0))
    _claim(db, 9, 7, "Komentārs par 7", "2025-05-03", speaker_id=8, vector=_unit(1.0, 0.0, 0.0))
    _claim(db, 10, 8, "Cita politiķa", "2025-05-04", vector=_unit(1.0, 0.0, 0.0))
    db.commit()
    db.close()


def test_load_position_vectors_filters_type_speaker_and_missing(db_path):
    _seed(db_path)
    db = get_db(db_path)
    ids, M = load_position_vectors(db, 7)
    db.close()
    assert ids == [1, 2, 3, 4]
    assert M.shape == (4, 384)
    assert np.allclose(np.linalg.norm(M, axis=1), 1.0)


def test_candidate_pairs_k1_are_nearest_neighbours_chronological(db_path):
    _seed(db_path)
    pairs = candidate_pairs(7, k=1, db_path=db_path)
    # kosinusi: (1,2)=0.99 (1,3)=0.94 (2,3)=0.93 (3,4)=0.35 (1,4)=(2,4)=0
    # k=1: 1→2, 2→1, 3→1, 4→3 → pāri {1,2} {1,3} {3,4}; hronoloģiski
    # 1 (01-10) < 3 (02-01) < 2 (03-01) < 4 (04-01), kārtoti pēc (old, new):
    assert pairs == [(1, 3), (1, 2), (3, 4)]
    # katrs pāris hronoloģisks: old.stated_at <= new.stated_at
    db = get_db(db_path)
    dates = dict(db.execute("SELECT id, stated_at FROM claims").fetchall())
    db.close()
    assert all(dates[a] <= dates[b] for a, b in pairs)


def test_candidate_pairs_k_large_gives_all_pairs(db_path):
    _seed(db_path)
    pairs = candidate_pairs(7, k=10, db_path=db_path)
    assert len(pairs) == 6                       # C(4,2)
    assert len(set(pairs)) == 6


def test_candidate_pairs_empty_for_unknown_or_single(db_path):
    _seed(db_path)
    assert candidate_pairs(999, db_path=db_path) == []
    assert candidate_pairs(8, db_path=db_path) == []      # viena pozīcija — nav pāru


def test_pair_states_shape_and_privacy(db_path):
    _seed(db_path)
    db = get_db(db_path)
    states = pair_states(db, [(1, 2)])
    db.close()
    assert states == [{
        "old": {"stance": "Atbalsta nodokļu celšanu", "quote": None, "topic": "Nodokļi", "date": "2025-01-10"},
        "new": {"stance": "Pret nodokļu celšanu", "quote": "Nē!", "topic": "Nodokļi", "date": "2025-03-01"},
    }]
    # uz API neiet ne reasoning, ne politiķa vārds, ne id
    assert "reasoning" not in states[0]["old"] and "id" not in states[0]["old"]


def test_question_texts_are_latvian_and_reference_row():
    assert "{row}" in OPPOSITE_INSTRUCTIONS
    assert set(OPPOSITE_CRITERIA) == {"true", "false"}
    assert "politiķ" in PAIR_CONTEXT["politician"]
    for txt in (OPPOSITE_INSTRUCTIONS, *OPPOSITE_CRITERIA.values()):
        assert "ā" in txt or "ē" in txt or "ī" in txt   # garumzīmes — nav ASCII-nolobīts
```

- [ ] **Step 2: Palaid — jākrīt ar ImportError**

Run: `.venv/Scripts/python.exe -m pytest tests/test_contradiction_candidates.py -q`
Expected: `ModuleNotFoundError: No module named 'src.contradiction_candidates'`.

- [ ] **Step 3: Uzraksti `src/contradiction_candidates.py`**

```python
"""Kandidātu pāri retorika-pret-retoriku pretrunu meklēšanai + Jev jautājums.

Kāpēc kNN, ne visi pāri: 170 politiķiem visi pāri = 532 250 (2026-09-18);
politiķim ar 570 pozīcijām vien 162 165. Kosinusa slieksnis neko nefiltrē
(hunter prompts § threshold), bet RELATĪVĀ kaimiņu secība tur informāciju:
no 23 zelta position↔position pretrunām 21 ir viena otras top-40 kaimiņos,
22 top-100 (#37 rank 82), #4 (rank 132) — ne. Tāpēc k ir pilnīguma
griesti, un katrs skripts to drukā kā denominatoru.

Jev vērtē pāri, ne meklē: šis modulis dod pārus + `state`, `src.jev_filter`
tos sūta. Neviens ceļš šeit neraksta DB.
"""
from __future__ import annotations

import sqlite3
from typing import Optional

import numpy as np

from src.db import get_db
from src.party_contradictions import ensure_vec

DEFAULT_K = 40

# Uz API iet tikai šie lauki — publisku avotu teksts, bez vārda un bez reasoning.
PAIR_CONTEXT = {"politician": "abus izteikumus ir teicis viens un tas pats politiķis",
                "old": "agrākais izteikums", "new": "vēlākais izteikums"}
OPPOSITE_INSTRUCTIONS = (
    "Vai `{row}.new` nostāja ir pretēja `{row}.old` nostājai tajā pašā konkrētajā jautājumā?"
)
OPPOSITE_CRITERIA = {
    "true": ("new noliedz, apgriež vai atsauc to, ko old apgalvo par to pašu lietu — "
             "piemēram, agrāk atbalstīja, tagad iebilst; agrāk izslēdza, tagad pieļauj"),
    "false": ("new ir par citu lietu, vai abas nostājas var būt spēkā vienlaikus — "
              "precizējums, papildinājums, cita tēma, tas pats viedoklis citiem vārdiem"),
}

_POSITIONS_SQL = """
    SELECT c.id, v.embedding
      FROM claims c JOIN claim_vectors v ON v.claim_id = c.id
     WHERE c.opponent_id = ? AND c.claim_type = 'position'
       AND (c.speaker_id IS NULL OR c.speaker_id = c.opponent_id)
     ORDER BY c.id
"""


def load_position_vectors(db: sqlite3.Connection, opponent_id: int) -> tuple[list[int], np.ndarray]:
    """Pirmās puses `position` pozīcijas ar vektoru; matrica L2-normēta (dot == cos)."""
    ensure_vec(db)
    rows = db.execute(_POSITIONS_SQL, (opponent_id,)).fetchall()
    if not rows:
        return [], np.zeros((0, 384), dtype=np.float32)
    ids = [int(r[0]) for r in rows]
    M = np.vstack([np.frombuffer(r[1], dtype=np.float32) for r in rows]).astype(np.float32)
    norms = np.linalg.norm(M, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return ids, M / norms


def _order_key(db: sqlite3.Connection, ids: list[int]) -> dict[int, tuple[str, int]]:
    q = f"SELECT id, COALESCE(stated_at, '') FROM claims WHERE id IN ({','.join('?' * len(ids))})"
    return {int(i): (str(s), int(i)) for i, s in db.execute(q, ids).fetchall()}


def candidate_pairs(opponent_id: int, *, k: int = DEFAULT_K,
                    db_path: Optional[str] = None) -> list[tuple[int, int]]:
    """Unikāli `(old_id, new_id)` pāri: katrai pozīcijai tās top-k kaimiņi pēc kosinusa."""
    db = get_db(db_path)
    try:
        ids, M = load_position_vectors(db, opponent_id)
        if len(ids) < 2:
            return []
        sims = M @ M.T
        np.fill_diagonal(sims, -np.inf)
        kk = min(k, len(ids) - 1)
        seen: set[frozenset[int]] = set()
        for i in range(len(ids)):
            top = np.argpartition(-sims[i], kk - 1)[:kk] if kk < len(ids) - 1 else np.arange(len(ids))
            for j in top:
                if j != i:
                    seen.add(frozenset((ids[i], ids[int(j)])))
        order = _order_key(db, ids)
        pairs = [tuple(sorted(p, key=lambda cid: order[cid])) for p in seen]
        return sorted(pairs, key=lambda ab: (order[ab[0]], order[ab[1]]))
    finally:
        db.close()


def pair_states(db: sqlite3.Connection, pairs: list[tuple[int, int]]) -> list[dict]:
    """Jev `state` katram pārim — tikai stance/quote/topic/date, bez vārda un reasoning."""
    wanted = sorted({cid for ab in pairs for cid in ab})
    if not wanted:
        return []
    q = (f"SELECT id, stance, quote, topic, COALESCE(SUBSTR(stated_at, 1, 10), '') "
         f"FROM claims WHERE id IN ({','.join('?' * len(wanted))})")
    by_id = {int(r[0]): {"stance": r[1], "quote": r[2], "topic": r[3], "date": r[4]}
             for r in db.execute(q, wanted).fetchall()}
    return [{"old": by_id[a], "new": by_id[b]} for a, b in pairs]
```

- [ ] **Step 4: Palaid testus — jāiet zaļi**

Run: `.venv/Scripts/python.exe -m pytest tests/test_contradiction_candidates.py -q`
Expected: `6 passed`. Ja `test_candidate_pairs_k1_are_nearest_neighbours_chronological` krīt uz pāru kopu — pārrēķini kosinusus fikstūrā (4. vektors `(0,0,1)`: cos ar 3 = 0.3/|3| ≈ 0.35, ar 1 un 2 = 0 un ≈0) un labo TESTA gaidīto, ne algoritmu.

- [ ] **Step 5: Zelta pilnīguma mērījums uz dzīvās DB (tikai lasa, 0 API)**

Run:
```bash
.venv/Scripts/python.exe - <<'EOF'
from src.db import get_db
from src.contradiction_candidates import candidate_pairs
db = get_db()
gold = db.execute("""SELECT c.id, c.opponent_id, c.claim_old_id, c.claim_new_id FROM contradictions c
  JOIN claims a ON a.id=c.claim_old_id JOIN claims b ON b.id=c.claim_new_id
  WHERE a.claim_type='position' AND b.claim_type='position'""").fetchall()
db.close()
for k in (40, 100):
    hit = 0; total_pairs = 0
    for pid in sorted({g[1] for g in gold}):
        pairs = candidate_pairs(pid, k=k); total_pairs += len(pairs)
        s = {frozenset(p) for p in pairs}
        hit += sum(1 for g in gold if g[1] == pid and frozenset((g[2], g[3])) in s)
    print(f"k={k}: zelts kandidātos {hit}/{len(gold)}, kandidātu pāru kopā {total_pairs}")
EOF
```
Expected: `k=40: zelts kandidātos 21/23`, `k=100: 22/23` (sakrīt ar sesijas mērījumu; ja mazāk — kļūda pāru ģenerēšanā, STOP). Pieraksti abus `total_pairs` skaitļus — tie nosaka 4. uzdevuma cenu.

- [ ] **Step 6: `bash scripts/check.sh` + commit**

```bash
git add src/contradiction_candidates.py tests/test_contradiction_candidates.py
git commit -m "Pretrunu kandidātu pāri no claim_vectors (top-k kaimiņi, hronoloģiski) + Jev pāra state un LV jautājums; zelts kandidātos 21/23 pie k=40, 22/23 pie k=100"
```

---

### Task 3: `scripts/jev_contradiction_eval.py` — zelta tests ar denominatoriem

**Files:**
- Create: `scripts/jev_contradiction_eval.py`
- Test: `tests/test_jev_contradiction_eval.py`

**Interfaces:**
- Consumes: `candidate_pairs`, `pair_states`, `PAIR_CONTEXT`, `OPPOSITE_INSTRUCTIONS`, `OPPOSITE_CRITERIA` (Task 2); `judge_rows`, `JevStats`, `JevCache` (Task 1); `get_db`.
- Produces (tīras funkcijas, testējamas bez DB/API):
  - `gold_pairs(db) -> list[dict]` — `{"id", "opponent_id", "old", "new", "confirmed", "severity"}` tikai position↔position.
  - `summarize(gold: list[dict], probs: dict[frozenset[int], float | None], thresholds: list[float]) -> dict` — `{"in_candidates": int, "gold_total": int, "judged": int, "unavailable": int, "rows": [{"threshold", "gold_kept", "gold_confirmed_kept", "candidates_kept", "kept_pct"}], "gold_detail": [{"id","p","confirmed"}]}`.
  - `render(summary, stats) -> str` — denominatori pirmajās rindās, tad tabula.
- CLI: `--k 40`, `--politicians 2,12,10` (noklusējums: visi zelta politiķi), `--dry-run` (tikai kandidātu pilnīgums, 0 API), `--max-pairs 80000`, `--thresholds 0.5,0.6,0.7,0.8,0.9`, `--out data/jev_eval_<YYYY-MM-DD>.json`.

- [ ] **Step 1: Uzraksti krītošos testus**

```python
# tests/test_jev_contradiction_eval.py
"""Zelta testa aprēķins — tīras funkcijas, bez DB rakstīšanas un bez API."""
from __future__ import annotations

import importlib.util
import os
import tempfile
from pathlib import Path

import pytest

from src.db import get_db, init_db

_spec = importlib.util.spec_from_file_location(
    "jev_contradiction_eval", Path(__file__).resolve().parent.parent / "scripts" / "jev_contradiction_eval.py")
ev = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ev)


def _gold(i, a, b, confirmed=1):
    return {"id": i, "opponent_id": 1, "old": a, "new": b, "confirmed": confirmed, "severity": "reversal"}


def test_summarize_counts_denominators_and_thresholds():
    gold = [_gold(1, 10, 11), _gold(2, 12, 13, confirmed=0), _gold(3, 14, 15)]   # #3 nav kandidātos
    probs = {frozenset((10, 11)): 0.92, frozenset((12, 13)): 0.55,
             frozenset((20, 21)): 0.10, frozenset((22, 23)): 0.70, frozenset((24, 25)): None}
    s = ev.summarize(gold, probs, [0.5, 0.9])
    assert s["gold_total"] == 3 and s["in_candidates"] == 2
    assert s["judged"] == 4 and s["unavailable"] == 1
    r05, r09 = s["rows"]
    assert (r05["threshold"], r05["gold_kept"], r05["gold_confirmed_kept"]) == (0.5, 2, 1)
    assert r05["candidates_kept"] == 3 and r05["kept_pct"] == pytest.approx(75.0)
    assert (r09["gold_kept"], r09["candidates_kept"]) == (1, 1)
    assert [d["id"] for d in s["gold_detail"]] == [1, 2, 3]
    assert s["gold_detail"][2]["p"] is None                       # ārpus kandidātiem = None


def test_render_puts_denominator_before_findings():
    gold = [_gold(1, 10, 11)]
    s = ev.summarize(gold, {frozenset((10, 11)): 0.9}, [0.5])
    from src.jev_filter import JevStats
    text = ev.render(s, JevStats(requests=1, input_tokens=1000))
    lines = text.splitlines()
    assert lines[0].startswith("Denominators:")
    assert "zelts 1, kandidātos 1" in lines[0]
    assert "0.5" in text and "1/1" in text


def test_gold_pairs_reads_only_position_pairs():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    db = get_db(path)
    db.execute("INSERT INTO documents (id, content, content_hash, scraped_at) "
               "VALUES (1, 'teksts', 'h1', '2025-01-01 00:00:00')")
    db.execute("INSERT INTO tracked_politicians (id, name, party) VALUES (1, 'A B', 'P')")
    for cid, ct in ((1, "position"), (2, "position"), (3, "saeima_vote")):
        db.execute("INSERT INTO claims (id, opponent_id, topic, stance, source_url, claim_type, document_id) "
                   "VALUES (?, 1, 't', 's', 'https://x', ?, 1)", (cid, ct))
    db.execute("INSERT INTO contradictions (id, opponent_id, claim_old_id, claim_new_id, topic, summary, severity, confirmed) "
               "VALUES (1, 1, 1, 2, 't', 's', 'reversal', 1)")
    db.execute("INSERT INTO contradictions (id, opponent_id, claim_old_id, claim_new_id, topic, summary, severity, confirmed) "
               "VALUES (2, 1, 1, 3, 't', 's', 'minor_shift', 1)")
    db.commit()
    gold = ev.gold_pairs(db)
    db.close()
    os.unlink(path)
    assert [g["id"] for g in gold] == [1]
    assert gold[0] == {"id": 1, "opponent_id": 1, "old": 1, "new": 2, "confirmed": 1, "severity": "reversal"}
```

- [ ] **Step 2: Palaid — jākrīt**

Run: `.venv/Scripts/python.exe -m pytest tests/test_jev_contradiction_eval.py -q`
Expected: `FileNotFoundError` / `AttributeError: module has no attribute 'summarize'`.

- [ ] **Step 3: Uzraksti `scripts/jev_contradiction_eval.py`**

```python
"""Zelta tests Jev pretrunu priekšfiltram — denominatori pirmie, DB tikai lasa.

Jautājums, uz ko atbild: ja `@contradiction-hunter` lasītu tikai pārus, kam
Jev dod p ≥ θ, vai tas pazaudētu kādu no jau ZINĀMAJĀM pretrunām
(`contradictions`, position↔position), un cik kandidātu tas noņemtu?

Divi atsevišķi denominatori — nekad nesapludināt:
  1. zelts kandidātos / zelts kopā   — kNN kandidātu ģenerēšanas griesti (k)
  2. zelts virs θ / zelts kandidātos — paša Jev pilnīgums
Zelts ārpus kandidātiem Jev nekad neredz; tas ir k jautājums, ne modeļa.

Usage:
  .venv/Scripts/python.exe scripts/jev_contradiction_eval.py --dry-run          # 0 API: tikai (1)
  .venv/Scripts/python.exe scripts/jev_contradiction_eval.py --k 40             # dzīvs skrējiens
  .venv/Scripts/python.exe scripts/jev_contradiction_eval.py --politicians 2,12 --k 100
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.contradiction_candidates import (  # noqa: E402
    DEFAULT_K, OPPOSITE_CRITERIA, OPPOSITE_INSTRUCTIONS, PAIR_CONTEXT, candidate_pairs, pair_states,
)
from src.db import get_db  # noqa: E402
from src.jev_filter import JevCache, JevStats, judge_rows  # noqa: E402

DEFAULT_THRESHOLDS = [0.5, 0.6, 0.7, 0.8, 0.9]

_GOLD_SQL = """
    SELECT c.id, c.opponent_id, c.claim_old_id, c.claim_new_id, c.confirmed, c.severity
      FROM contradictions c
      JOIN claims a ON a.id = c.claim_old_id
      JOIN claims b ON b.id = c.claim_new_id
     WHERE a.claim_type = 'position' AND b.claim_type = 'position'
     ORDER BY c.id
"""


def gold_pairs(db: sqlite3.Connection) -> list[dict]:
    return [{"id": int(r[0]), "opponent_id": int(r[1]), "old": int(r[2]), "new": int(r[3]),
             "confirmed": int(r[4] or 0), "severity": r[5]} for r in db.execute(_GOLD_SQL).fetchall()]


def summarize(gold: list[dict], probs: dict[frozenset[int], float | None],
              thresholds: list[float]) -> dict:
    detail = []
    for g in gold:
        key = frozenset((g["old"], g["new"]))
        detail.append({"id": g["id"], "confirmed": g["confirmed"], "severity": g["severity"],
                       "in_candidates": key in probs, "p": probs.get(key)})
    in_cand = [d for d in detail if d["in_candidates"]]
    judged = sum(1 for p in probs.values() if p is not None)
    unavailable = sum(1 for p in probs.values() if p is None)
    rows = []
    for t in thresholds:
        kept = sum(1 for p in probs.values() if p is not None and p >= t)
        rows.append({
            "threshold": t,
            "gold_kept": sum(1 for d in in_cand if d["p"] is not None and d["p"] >= t),
            "gold_confirmed_kept": sum(1 for d in in_cand if d["confirmed"] and d["p"] is not None and d["p"] >= t),
            "candidates_kept": kept,
            "kept_pct": (100.0 * kept / judged) if judged else 0.0,
        })
    return {"gold_total": len(gold), "in_candidates": len(in_cand),
            "gold_confirmed_in_candidates": sum(1 for d in in_cand if d["confirmed"]),
            "judged": judged, "unavailable": unavailable, "rows": rows, "gold_detail": detail}


def render(s: dict, stats: JevStats) -> str:
    out = [f"Denominators: zelts {s['gold_total']}, kandidātos {s['in_candidates']} "
           f"(apstiprināti {s['gold_confirmed_in_candidates']}), vērtēti pāri {s['judged']}, "
           f"nepieejami {s['unavailable']}",
           stats.summary(),
           "",
           f"{'θ':>5} | {'zelts ≥θ':>10} | {'apstipr. ≥θ':>12} | {'kandidāti ≥θ':>13} | {'paliek %':>8}"]
    for r in s["rows"]:
        out.append(f"{r['threshold']:>5} | {r['gold_kept']:>4}/{s['in_candidates']:<5} | "
                   f"{r['gold_confirmed_kept']:>5}/{s['gold_confirmed_in_candidates']:<6} | "
                   f"{r['candidates_kept']:>13} | {r['kept_pct']:>7.1f}")
    out.append("")
    out.append("Zelta pāri (p = Jev varbūtība; None = ārpus kandidātiem vai nepieejams):")
    for d in s["gold_detail"]:
        p = "None" if d["p"] is None else f"{d['p']:.2f}"
        out.append(f"  #{d['id']:<3} {d['severity']:<20} confirmed={d['confirmed']} p={p}"
                   + ("" if d["in_candidates"] else "  (ārpus top-k kandidātiem)"))
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--k", type=int, default=DEFAULT_K)
    ap.add_argument("--politicians", default="", help="komatu saraksts ar opponent_id; tukšs = visi zelta")
    ap.add_argument("--dry-run", action="store_true", help="tikai kandidātu pilnīgums, 0 API")
    ap.add_argument("--max-pairs", type=int, default=80_000, help="izdevumu vārts: vairāk nesūta")
    ap.add_argument("--thresholds", default=",".join(map(str, DEFAULT_THRESHOLDS)))
    ap.add_argument("--out", default=f"data/jev_eval_{date.today().isoformat()}.json")
    args = ap.parse_args()
    thresholds = [float(t) for t in args.thresholds.split(",") if t]

    db = get_db()
    gold = gold_pairs(db)
    pids = sorted({g["opponent_id"] for g in gold})
    if args.politicians:
        chosen = {int(x) for x in args.politicians.split(",") if x}
        pids = [p for p in pids if p in chosen]
        gold = [g for g in gold if g["opponent_id"] in chosen]

    all_pairs: list[tuple[int, int]] = []
    per_pid: dict[int, int] = {}
    for pid in pids:
        pairs = candidate_pairs(pid, k=args.k)
        per_pid[pid] = len(pairs)
        all_pairs.extend(pairs)
    cand = {frozenset(p) for p in all_pairs}
    in_cand = sum(1 for g in gold if frozenset((g["old"], g["new"])) in cand)
    print(f"Politiķi {len(pids)}, k={args.k}, kandidātu pāri {len(all_pairs)} "
          f"({', '.join(f'{p}:{n}' for p, n in per_pid.items())}); zelts kandidātos {in_cand}/{len(gold)}")

    if args.dry_run:
        db.close()
        return 0
    if len(all_pairs) > args.max_pairs:
        print(f"STOP: {len(all_pairs)} pāri > --max-pairs {args.max_pairs}; sašaurini --politicians vai --k")
        db.close()
        return 2

    states = pair_states(db, all_pairs)
    db.close()
    stats = JevStats()
    probs_list = judge_rows(states, OPPOSITE_INSTRUCTIONS, OPPOSITE_CRITERIA,
                            context=PAIR_CONTEXT, cache=JevCache(), stats=stats)
    probs = {frozenset(p): pr for p, pr in zip(all_pairs, probs_list, strict=True)}
    s = summarize(gold, probs, thresholds)
    print(render(s, stats))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps({"k": args.k, "politicians": pids, "per_pid": per_pid,
                                          "summary": s, "stats": stats.__dict__,
                                          "pairs": [[a, b, probs[frozenset((a, b))]] for a, b in all_pairs]},
                                         ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nRezultāts: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Palaid testus — jāiet zaļi**

Run: `.venv/Scripts/python.exe -m pytest tests/test_jev_contradiction_eval.py -q`
Expected: `3 passed`.

- [ ] **Step 5: Sausais skrējiens uz dzīvās DB (0 API)**

Run: `.venv/Scripts/python.exe scripts/jev_contradiction_eval.py --dry-run --k 40` un `--k 100`
Expected: `zelts kandidātos 21/23` (k=40) un `22/23` (k=100), plus pāru skaits per politiķis. Pieraksti abus pāru kopskaitus 4. uzdevumam.

- [ ] **Step 6: `bash scripts/check.sh` + commit**

```bash
git add scripts/jev_contradiction_eval.py tests/test_jev_contradiction_eval.py
git commit -m "Jev pretrunu zelta tests (scripts/jev_contradiction_eval.py): divi denominatori (zelts kandidātos / zelts virs θ), sliekšņu tabula, --dry-run 0 API, --max-pairs izdevumu vārts"
```

---

### Task 4: Dzīvais zelta skrējiens un verdikts (operatora solis)

**Files:**
- Read: `data/jev_eval_<date>.json` (gitignored), `wiki/operations/quality-bars.md` § pretrunas.
- Modify: `wiki/CHANGELOG.md` (jauns ieraksts `## 2026-MM-DD (n) — Jev pretrunu priekšfiltrs: zelta tests`, ≤5 rindas, katrs skaitlis ar komandu).

Šis uzdevums NAV koda uzdevums. Pirms tā — operatora „jā" izdevumam (aplēse: pāru skaits no 3. uzdevuma × ~350 ievades tokeni × $0,042/M; pie ~60 000 pāriem ≈ $1, ~10–15 min pie 4 paralēliem pieprasījumiem).

- [ ] **Step 1: Dzīvais skrējiens k=40**

Run: `.venv/Scripts/python.exe scripts/jev_contradiction_eval.py --k 40`
Expected: tabula ar 5 sliekšņiem; `nepieejami 0` (ja >0 — atkārto: kešs saglabā atbildētos, sūta tikai trūkstošos).

- [ ] **Step 2: Verdikts pēc tabulas — trīs iznākumi, tikai viens rakstāms**

Pieņemšanas vārts (nosaka PIRMS skatīt skaitļus): eksistē θ ∈ {0,5 … 0,9}, pie kura `apstipr. ≥θ` = **visi** apstiprinātie zelta pāri kandidātos (pie k=40 tie ir 18/18 vai cik tabula rāda saucējā) UN `paliek %` ≤ 30.
- **Iztur** → 5. un 6. uzdevums ar šo θ.
- **Neiztur pilnīgumā** (kāds apstiprināts zelts < 0,5) → izlasi to pāri (`gold_detail`), noskaidro, vai Jev kļūdās vai pāris zeltā ir vājš (#40/#47/#48 ir neapstiprināti tieši tāpēc). Vienu jautājuma teksta laboju drīkst mēģināt (`OPPOSITE_CRITERIA`), tad atkārto. Otro reizi neiztur → STOP, ziņo, 5./6. uzdevumu nedara.
- **Neiztur noņemšanā** (`paliek %` > 30 pie jebkura θ, kur zelts vēl 100 %) → Jev neko neietaupa; STOP, ziņo.

- [ ] **Step 3: CHANGELOG ieraksts**

Forma (aizpildi ar reālajiem skaitļiem un komandām, ne vairāk par 5 rindām):

```markdown
## 2026-MM-DD (n) — Jev pretrunu priekšfiltrs: zelta tests <IZTUR|NEIZTUR>

- Ideja no pg-jev (Postgres paplašinājums, mums neder — SQLite), pārņemts tikai paterns: `src/jev_filter.py` (40 rindas/state, kešs `data/jev_cache.db`), `src/contradiction_candidates.py` (top-k kaimiņi no `claim_vectors`), `scripts/jev_contradiction_eval.py`.
- Kandidātu griesti: zelts kandidātos 21/23 pie k=40, 22/23 pie k=100 (`jev_contradiction_eval.py --dry-run --k …`); #4 (rank 132) un #37 (rank 82) ārpus — kNN, ne Jev.
- Jev pilnīgums pie θ=<…>: apstiprinātie <a>/<b>, kandidātu paliek <…> % no <N> (`jev_contradiction_eval.py --k 40`, `data/jev_eval_<date>.json`); tokeni <…>, cena ≈ $<…>.
- Lēmums: <hunter lasa īso sarakstu pirmo / netiek ieviests, jo …>. Jev DB neraksta; `confirmed` maina tikai operators.
```

```bash
git add wiki/CHANGELOG.md
git commit -m "CHANGELOG: Jev pretrunu priekšfiltra zelta tests — <verdikts> (zelts <a>/<b> pie θ=<…>, paliek <…> %)"
```

---

**Iznākums (2026-09-18, ierakstīts pēc gala pārskata):** vārts, kā šeit iepriekš noteikts, NAV izpildīts — v1 2/18 pie 0,5; v2 16/18 pie θ=0,3 (6,7 % paliek), 18/18 tikai pie 0,22 ar 32 %. Operators pēc skaitļu redzēšanas nolēma v2 pieņemt kā lasīšanas secību (ne vārtus) un turpināt 5.–6. uzdevumu; pilns v2 atkārtojums izlaists. Kanoniskais pieraksts: `wiki/CHANGELOG.md` 2026-09-18 (2). Šis plāns paliek kā rakstīts — vārta teksts nav labots pēc fakta.

---

### Task 5: `scripts/jev_contradiction_shortlist.py` — īsais saraksts vienam politiķim (TIKAI ja 4. uzdevums iztur)

**Files:**
- Create: `scripts/jev_contradiction_shortlist.py`
- Test: `tests/test_jev_contradiction_shortlist.py`

**Interfaces:**
- Consumes: Task 1 + Task 2 API; `tracked_politicians(id, name)`.
- Produces: `format_shortlist(name: str, n_claims: int, pairs: list[dict], threshold: float, stats: JevStats) -> str` — markdown; `pairs` elementi `{"old_id","new_id","p","old_date","new_date","old_topic","new_topic","old_stance","new_stance"}`.
- CLI: `<opponent_id | vārda fragments> [--k 40] [--threshold θ] [--all]` (`--all` drukā arī pārus zem θ, sakārtotus dilstoši — lasīšanas secība).

- [ ] **Step 1: Uzraksti krītošo testu**

```python
# tests/test_jev_contradiction_shortlist.py
from __future__ import annotations

import importlib.util
from pathlib import Path

from src.jev_filter import JevStats

_spec = importlib.util.spec_from_file_location(
    "jev_contradiction_shortlist",
    Path(__file__).resolve().parent.parent / "scripts" / "jev_contradiction_shortlist.py")
sl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sl)


def test_format_shortlist_denominator_first_then_rows_desc_by_p():
    pairs = [
        {"old_id": 1, "new_id": 2, "p": 0.61, "old_date": "2025-01-10", "new_date": "2025-03-01",
         "old_topic": "Nodokļi", "new_topic": "Nodokļi", "old_stance": "Par", "new_stance": "Pret"},
        {"old_id": 3, "new_id": 4, "p": 0.93, "old_date": "2024-05-01", "new_date": "2025-06-01",
         "old_topic": "Rail Baltica", "new_topic": "Transports", "old_stance": "Jāceļ", "new_stance": "Jāaptur"},
        {"old_id": 5, "new_id": 6, "p": 0.20, "old_date": "2024-01-01", "new_date": "2024-02-01",
         "old_topic": "X", "new_topic": "X", "old_stance": "a", "new_stance": "b"},
    ]
    text = sl.format_shortlist("Testa Persona", 12, pairs, 0.6, JevStats(requests=1, input_tokens=2000))
    lines = text.splitlines()
    assert lines[0].startswith("# Testa Persona — Jev īsais saraksts")
    assert "pozīcijas 12, kandidātu pāri 3, virs θ=0.6: 2" in text
    # rindas dilstoši pēc p; pāris zem θ nav tabulā
    i93, i61 = text.index("0.93"), text.index("0.61")
    assert i93 < i61 and "0.20" not in text
    assert "#3 → #4" in text and "2024-05-01 → 2025-06-01" in text
    assert "Rail Baltica → Transports" in text
```

- [ ] **Step 2: Palaid — jākrīt**

Run: `.venv/Scripts/python.exe -m pytest tests/test_jev_contradiction_shortlist.py -q`
Expected: `FileNotFoundError`.

- [ ] **Step 3: Uzraksti skriptu**

```python
"""Jev īsais saraksts vienam politiķim — ko `@contradiction-hunter` lasa PIRMO.

Kandidātu pāri (top-k kaimiņi no claim_vectors) → Jev «vai new ir pretēja
old tajā pašā jautājumā» → pāri ar p ≥ θ dilstoši. Tas ir LASĪŠANAS SECĪBA
ar pierādītu pilnīgumu (zelta tests, CHANGELOG), ne verdikts: katru pāri
joprojām vērtē hunter → @devils-advocate → operators, `confirmed=0` paliek.
Balsojumu pusi (retorika-pret-balsojumu) šis skripts NESKAR — T9.

Usage:
  .venv/Scripts/python.exe scripts/jev_contradiction_shortlist.py 10 --threshold 0.7
  .venv/Scripts/python.exe scripts/jev_contradiction_shortlist.py "Kulbergs" --k 100 --all
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.contradiction_candidates import (  # noqa: E402
    DEFAULT_K, OPPOSITE_CRITERIA, OPPOSITE_INSTRUCTIONS, PAIR_CONTEXT, candidate_pairs, pair_states,
)
from src.db import get_db  # noqa: E402
from src.jev_filter import JevCache, JevStats, judge_rows  # noqa: E402

DEFAULT_THRESHOLD = 0.7   # PĀRRAKSTI ar 4. uzdevuma θ pēc zelta testa


def format_shortlist(name: str, n_claims: int, pairs: list[dict], threshold: float,
                     stats: JevStats, show_all: bool = False) -> str:
    ranked = sorted((p for p in pairs if p["p"] is not None), key=lambda p: -p["p"])
    above = [p for p in ranked if p["p"] >= threshold]
    out = [f"# {name} — Jev īsais saraksts",
           f"Denominators: pozīcijas {n_claims}, kandidātu pāri {len(pairs)}, virs θ={threshold}: {len(above)}, "
           f"nepieejami {sum(1 for p in pairs if p['p'] is None)}",
           stats.summary(), "",
           "| p | pāris | datumi | tēmas | vecā nostāja | jaunā nostāja |",
           "|---|---|---|---|---|---|"]
    for p in (ranked if show_all else above):
        out.append(f"| {p['p']:.2f} | #{p['old_id']} → #{p['new_id']} | {p['old_date']} → {p['new_date']} | "
                   f"{p['old_topic']} → {p['new_topic']} | {p['old_stance']} | {p['new_stance']} |")
    return "\n".join(out)


def _resolve(db, arg: str) -> tuple[int, str]:
    if arg.isdigit():
        row = db.execute("SELECT id, name FROM tracked_politicians WHERE id = ?", (int(arg),)).fetchone()
    else:
        rows = db.execute("SELECT id, name FROM tracked_politicians WHERE name LIKE ? AND "
                          "relationship_type IS NOT 'inactive'", (f"%{arg}%",)).fetchall()
        if len(rows) != 1:
            raise SystemExit(f"'{arg}' atbilst {len(rows)} politiķiem: {[r[1] for r in rows]}")
        row = rows[0]
    if row is None:
        raise SystemExit(f"politiķis {arg!r} nav atrasts")
    return int(row[0]), str(row[1])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("politician")
    ap.add_argument("--k", type=int, default=DEFAULT_K)
    ap.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    ap.add_argument("--all", action="store_true", help="drukā arī pārus zem θ (dilstoši)")
    args = ap.parse_args()

    db = get_db()
    pid, name = _resolve(db, args.politician)
    pairs = candidate_pairs(pid, k=args.k)
    n_claims = db.execute("SELECT COUNT(*) FROM claims WHERE opponent_id = ? AND claim_type = 'position' "
                          "AND (speaker_id IS NULL OR speaker_id = opponent_id)", (pid,)).fetchone()[0]
    states = pair_states(db, pairs)
    db.close()
    stats = JevStats()
    probs = judge_rows(states, OPPOSITE_INSTRUCTIONS, OPPOSITE_CRITERIA,
                       context=PAIR_CONTEXT, cache=JevCache(), stats=stats)
    rows = [{"old_id": a, "new_id": b, "p": p,
             "old_date": s["old"]["date"], "new_date": s["new"]["date"],
             "old_topic": s["old"]["topic"], "new_topic": s["new"]["topic"],
             "old_stance": s["old"]["stance"], "new_stance": s["new"]["stance"]}
            for (a, b), s, p in zip(pairs, states, probs, strict=True)]
    print(format_shortlist(name, n_claims, rows, args.threshold, stats, show_all=args.all))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Palaid testu — zaļš**

Run: `.venv/Scripts/python.exe -m pytest tests/test_jev_contradiction_shortlist.py -q`
Expected: `1 passed`.

- [ ] **Step 5: Dzīvā pārbaude uz viena zelta politiķa (kešs — 0 jauni pieprasījumi, ja k sakrīt ar 4. uzdevumu)**

Run: `.venv/Scripts/python.exe scripts/jev_contradiction_shortlist.py 72 --threshold <θ>`
Expected: denominatoru rinda, `pieprasījumi 0, kešs N`, tabulā redzams pāris #32 (zelts, id 72). Ja #32 nav tabulā — θ vai k neatbilst 4. uzdevumam; STOP.

- [ ] **Step 6: `bash scripts/check.sh` + commit**

```bash
git add scripts/jev_contradiction_shortlist.py tests/test_jev_contradiction_shortlist.py
git commit -m "Jev īsais saraksts vienam politiķim (scripts/jev_contradiction_shortlist.py): pāri virs θ dilstoši, denominators pirmais, kešs no zelta testa"
```

---

### Task 6: Ieaust `/deep-check` un `@contradiction-hunter` (TIKAI ja 4. uzdevums iztur)

**Files:**
- Modify: `.claude/commands/deep-check.md` — § Procedure, 1. punkts (pēc rindas „For each, pull the full claim history…").
- Modify: `.claude/agents/contradiction-hunter.md` — § Step 2 (Position-over-Time), pirms rindkopas „**Scope:** ALL politicians with 5+ position claims".
- Modify: `wiki/operations/agenti/contradiction-hunter.md` (cilvēka lasāmais apraksts) — viens teikums ar saiti uz skriptu.
- Test: `tests/test_deep_check_mentions_jev_shortlist.py`

**Interfaces:** nav koda; tikai prompta teksts. Jev paliek lasīšanas secība ar pierādītu pilnīgumu — vārti, kas VAR krist (zelta tests), ne verdikts.

- [ ] **Step 1: Uzraksti krītošo testu**

```python
# tests/test_deep_check_mentions_jev_shortlist.py
"""Prompta sargs: pēc zelta testa /deep-check un hunter lasa Jev īso sarakstu pirmo."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_deep_check_and_hunter_reference_shortlist_script():
    for rel in (".claude/commands/deep-check.md", ".claude/agents/contradiction-hunter.md"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "scripts/jev_contradiction_shortlist.py" in text, rel
        assert "T9" in text                      # balsojumu puse paliek strukturālā SQL


def test_shortlist_is_reading_order_not_verdict():
    text = (ROOT / ".claude/agents/contradiction-hunter.md").read_text(encoding="utf-8")
    i = text.index("scripts/jev_contradiction_shortlist.py")
    window = text[i - 200: i + 1500].lower()
    assert "devils-advocate" in window and "confirmed=0" in window
```

- [ ] **Step 2: Palaid — jākrīt**

Run: `.venv/Scripts/python.exe -m pytest tests/test_deep_check_mentions_jev_shortlist.py -q`
Expected: `AssertionError` uz `deep-check.md`.

- [ ] **Step 3: Papildini `.claude/commands/deep-check.md` § Procedure 1. punktu**

Ievieto pēc rindas „For each, pull the full claim history (`search_similar_claims` directional, `claim_type_filter` per direction) — **for rhetoric-vs-rhetoric only**.":

```markdown
   - **Jev īsais saraksts pirmais (kopš 2026-MM-DD, zelta tests CHANGELOG 2026-MM-DD (n)).** Katram politiķim palaid `.venv/Scripts/python.exe scripts/jev_contradiction_shortlist.py <id> --threshold <θ>` un iedod hunter sub-aģentam izdruku: pāri ar p ≥ θ dilstoši ir LASĪŠANAS SECĪBA ar pierādītu pilnīgumu (apstiprinātie zelta pāri kandidātos <a>/<a> pie θ=<θ>, kandidātu paliek <…> %), ne verdikts — hunter joprojām lasa pāri, `@devils-advocate` joprojām uzbrūk, `confirmed=0` paliek. Divas robežas, ko saraksts NEsedz: (1) pāri ārpus top-k kaimiņiem (k=40 → 21/23 zelta; #4 un #37 ārpus) — korpusam ≤150 pozīciju hunter joprojām izlasa hronoloģiju pa tēmām; (2) retorika-pret-balsojumu — Jev to neredz, strukturālais SQL (T9) paliek vienīgais ceļš. Denominatoru rinda no skripta iet ziņojumā.
```

- [ ] **Step 4: Papildini `.claude/agents/contradiction-hunter.md` § Step 2**

Ievieto pirms „**Scope:** ALL politicians with 5+ position claims":

```markdown
**Jev īsais saraksts (kopš 2026-MM-DD).** Ja orķestrators tev iedod
`scripts/jev_contradiction_shortlist.py` izdruku, sāc ar to: katrs pāris ar
p ≥ θ ir kandidāts, ko lasi PIRMO — atver abus claim ID, pārbaudi datumus,
kontekstu un vai tas nav precizējums vai tas pats viedoklis citiem vārdiem.
Saraksts ir lasīšanas secība ar izmērītu pilnīgumu (CHANGELOG), ne
verdikts: tavs kandidāts tāpat iet uz `@devils-advocate`, un glabā ar
`confirmed=0`. Saraksts NEsedz pārus ārpus top-k kaimiņiem un NEsedz
retorika-pret-balsojumu (T9) — Step 1 strukturālais SQL paliek obligāts.
Ja saraksts tukšs, tas nozīmē «Jev neko neatrada kandidātos», ne «pretrunu
nav» — korpusam ≤150 pozīciju izlasi hronoloģiju pa tēmām kā līdz šim.
```

- [ ] **Step 5: `wiki/operations/agenti/contradiction-hunter.md` — viens teikums**

Pievieno sadaļā par darba gaitu: „Kopš 2026-MM-DD orķestrators var iedot Jev īso sarakstu (`scripts/jev_contradiction_shortlist.py`) — lasīšanas secība retorika-pret-retoriku pāriem ar izmērītu pilnīgumu; balsojumu pusi tas neskar."

- [ ] **Step 6: Palaid testu — zaļš; `bash scripts/check.sh`; commit**

Run: `.venv/Scripts/python.exe -m pytest tests/test_deep_check_mentions_jev_shortlist.py -q` → `2 passed`; `bash scripts/check.sh` zaļš (arī `tests/test_wiki_lint.py` u.c. wiki sargi).

```bash
git add .claude/commands/deep-check.md .claude/agents/contradiction-hunter.md wiki/operations/agenti/contradiction-hunter.md tests/test_deep_check_mentions_jev_shortlist.py
git commit -m "/deep-check + @contradiction-hunter: Jev īsais saraksts kā lasīšanas secība (θ=<…>, zelts <a>/<a>); balsojumu puse un devils-advocate nemainās"
```

---

### Task 7: Pirmais īstais skens — `stale-pol` vilnis (operatora solis, pēc 6. uzdevuma)

**Files:** nav koda. Izpilda `/deep-check stale-pol` esošo procedūru (viļņi pa 4–5 politiķiem, lielākie pirmie), katram vispirms `scripts/jev_contradiction_shortlist.py`.

- [ ] **Step 1:** `from src.coverage import stale_pol_politicians; stale_pol_politicians()` → izvēlies 4–5 ar lielāko pozīciju skaitu.
- [ ] **Step 2:** Katram `scripts/jev_contradiction_shortlist.py <id> --threshold <θ>`; pieraksti denominatoru rindas.
- [ ] **Step 3:** `/deep-check <vārdi>` ar īsajiem sarakstiem hunter promptā. Survivor-i `confirmed=0`.
- [ ] **Step 4:** CHANGELOG ieraksts (≤5 rindas): politiķi, pozīcijas, kandidātu pāri, virs θ, hunter kandidāti, devils-advocate survivor-i, cena. Ja vilnis dod 0 survivor-u — tas ir derīgs iznākums (ROI ~1/2700), ne signāls pazemināt θ.

---

## Pašpārbaude (izpildīta plāna rakstīšanas laikā)

- **Spec pārklājums:** jev_filter (T1) ✔, kandidāti + jautājums (T2) ✔, zelta tests ar 23 pāriem un diviem denominatoriem (T3–T4) ✔, ieviešana /deep-check tikai pēc verdikta (T5–T6) ✔, pirmais stale-pol skens (T7) ✔. Retorika-pret-balsojumu apzināti ārpus — T9.
- **Vietturi:** nav „TBD"; `<θ>`, `<a>/<b>`, `<date>` ir operatora aizpildāmi skaitļi no 4. uzdevuma tabulas, ne plāna caurumi.
- **Tipu saskaņa:** `judge_rows(rows, instructions, criteria, *, context, model, batch_size, workers, cache, stats) -> list[float|None]` lietots identiski T3 un T5; `candidate_pairs(pid, *, k, db_path) -> list[tuple[int,int]]` un `pair_states(db, pairs) -> list[dict]` ar laukiem `stance/quote/topic/date` sakrīt T2 testā, T3 un T5; `JevStats.summary()` teksts sakrīt ar T1 testu (`pieprasījumi N, kešs N, nepieejami N`).
- **Zināmie riski:** (a) `np.argpartition` ar `kk == len(ids)-1` — apstrādāts ar `np.arange` zaru; (b) `stated_at` NULL → tukša virkne kārtojas pirmā — pāris tad ir „vecais = bez datuma", hunter to redz kolonnā `datumi`; (c) keša atslēga ietver `model` — `jev-latest` maiņa uz jaunu versiju nozīmē pilnu pārvērtēšanu (apzināti: atbildes nav pārnesamas starp modeļiem).
