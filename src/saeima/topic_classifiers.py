"""Saeimas dokumentu tēmu klasifikatori (spec 2026-10-21 § Lēmumi 5; plāns, 6. uzd.).

Divi ceļi ar vienu izvades formu `Prediction(topic, confidence, model)`:

- `classify_keyword(input_text, motif)` — šodienas ielādes ceļš
  `src.saeima.claims._motif_to_topic` (komisijas teikuma izgriešana →
  `_MOTIF_TOPIC_MAP` → `topic_map.normalize_topic` → noklusējums
  «Valsts pārvalde»). Bez motīva lieto `input_text` rindu «Virsraksts: …».
- `classify_jev(rows)` — TypeSafe System One (Jev) `choice` jautājums ar 35
  opcijām. Kļūme nekad nav klusa: nezināma etiķete vai nepieejams serviss →
  `None` + `log.warning`.

Jev līgums (https://docs.typesafe.ai/api.md, pārbaudīts ar dzīvu izsaukumu
2026-10-22; atbilde: `tests/fixtures/jev_choice_response.json`):

    POST /v1/systemone {"model", "state", "questions"}
    questions[qid] = {"type": "choice",
                      "instructions": str,
                      "criteria": {<opcijas nosaukums>: <apraksts>, ...}}   # 1–255 opcijas
    atbilde: {"model": <atrisinātais, piem. "jev-1.13.0">,
              "answers": {qid: {"type": "choice", "choice": <nosaukums>,
                                "confidence": 0..1,
                                "probabilities": {<nosaukums>: 0..1, ...}}},
              "usage": {"input_tokens", "output_tokens"}}

Pieprasījums: `state = {"rows": [{"input_text": ...}, ...]}` (`JEV_CHUNK_SIZE` = 1 rinda,
`src/saeima/topics.py`), jautājums `q{i}` norāda uz `rows[i].input_text`. Vairākas rindas
vienā pieprasījumā maina atbildes (ATSKAITE § Jev 1.14, viens dokuments pieprasījumā). Rindas projicē TIKAI uz `input_text` —
zelta etiķetes, pašreizējā tēma un strīdu lēmumi promptā nenonāk (plāna
Global Constraints). Opciju apraksti = tikai rubrikas «Ietver» rinda; noteikumi,
«Neietver» un «Robeža» nesatur `NNN/Lp14 → tēma` verdiktus promptā.

**Kad prognozes ir komitētas, jebkura prompta maiņa (INSTRUCTIONS, kritēriju
atlase vai `_RULE_REF_RE`) prasa RUBRIC_VERSION pacelšanu** (rubrikā un
`src/saeima/topics.py`), jo prognozes salīdzina pēc rubrikas versijas.

Kešs (`data/jev_topic_cache.db`, ne atmina.db): atslēga
`input_hash + RUBRIC_VERSION + prompt_hash + atbildējušais modelis`;
`prompt_hash` = sha1(INSTRUCTIONS + kritēriji + pieprasījuma izmērs), tāpēc mainīts
prompts vai cits rindu skaits pieprasījumā nekad nesaņem vecas atbildes, pat ja
versiju aizmirst pacelt. Rindas līdz 2026-10-22 (prompt_hash bez izmēra, 16 rindu
paketes) vairs netiek atrastas; tās ir nekaitīgas, tāpēc netiek dzēstas. Ja izsaucējs padod
aliasu (`jev-latest`), pirmā paketes atbilde to atrisina, un visas nākamās
paketes tajā skrējienā sūta jau atrisināto modeli — kešā nekad nejaucas modeļi
(sal. `backlog/dati-db.md` § Jev keša atslēga).
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import NamedTuple

from src.jev_filter import JevStats
from src.saeima.claims import _motif_to_topic
from src.saeima.topics import JEV_CHUNK_SIZE, JEV_MODEL, REPO_ROOT, RUBRIC_VERSION
from src.topic_map import TOPIC_GROUPS
from src.typesafe_client import TypeSafeUnavailable, system_one

log = logging.getLogger(__name__)

RUBRIC_PATH = REPO_ROOT / "data" / "saeima_topic_gold" / "RUBRIKA.md"
CACHE_PATH = REPO_ROOT / "data" / "jev_topic_cache.db"
# Katrs jautājums nes visus 35 kritērijus (~3,2k ievades tokenu), un serviss
# pieprasījumu virs ~64k tokenu noraida ar HTTP 400 `max_tokens_exceeded`
# (mērīts 2026-10-22: 20 rindas = 65 211 tokenu OK, 25 rindas = 400).
# Ražošanā sūta `JEV_CHUNK_SIZE` (1) rindu; MAX_BATCH ir tikai aizsargs.
MAX_BATCH = 20

INSTRUCTIONS = (
    "`rows[{i}].input_text` apraksta vienu Latvijas Saeimas dokumentu (likumprojektu, "
    "Saeimas lēmumu, pieprasījumu vai balsojumu bez numura). Izvēlies TIEŠI vienu tēmu, "
    "kas atbilst dokumenta saturam. Tēmu nosaka saturs, nevis komisijas nosaukums, "
    "iesniedzējs vai atsevišķs vārds virsrakstā. Likumprojekta procedūras balsojums "
    "(steidzamība, nodošana komisijai, priekšlikumu termiņš) pieder likuma tēmai."
)


class Prediction(NamedTuple):
    topic: str
    confidence: float | None
    model: str | None


def input_hash(input_text: str) -> str:
    """Tas pats kā `scripts/vote_topic_gold_sample.py` kolonna `input_hash`."""
    return hashlib.sha1(input_text.encode("utf-8")).hexdigest()


# --- A: atslēgvārdi ---------------------------------------------------------

def classify_keyword(input_text: str, motif: str) -> Prediction:
    """Šodienas ielādes ceļš uz īstā balsojuma motīva; `input_text` netiek lietots.

    Tukšs motīvs = kļūda: rezerve uz virsrakstu mērītu citu ievadi, nevis
    to, ko ielāde redz (motīvā ir numurs, lasījums, nodošanas teikums).
    """
    text = (motif or "").strip()
    if not text:
        raise ValueError("classify_keyword: vajag īstu balsojuma motīvu")
    return Prediction(_motif_to_topic(text), None, None)


# --- B: Jev ------------------------------------------------------------------

_TOPIC_HEAD_RE = re.compile(r"^### (.+?)\s*$")
_IETVER_RE = re.compile(r"^- Ietver:\s*(.+?)\s*$")
# «(11. noteikums)» → izmet visu iekavu; «(arī …, 10. noteikums)» → «(arī …)».
_RULE_REF_RE = re.compile(r"\s*\((?:sk\. )?\d+\. noteikum\w*\)")
_RULE_REF_TAIL_RE = re.compile(r",\s*(?:sk\. )?\d+\. noteikum\w*\)")


def load_rubric_criteria(path: Path | None = None) -> dict[str, str]:
    """`{tēma: «Ietver» rinda}` visām 35 tēmām; versijas neatbilstība = kļūda."""
    path = Path(path or RUBRIC_PATH)
    lines = path.read_text(encoding="utf-8").splitlines()
    first = lines[0].strip() if lines else ""
    if first != f"RUBRIC_VERSION: {RUBRIC_VERSION}":
        raise ValueError(
            f"RUBRIC_VERSION neatbilst: {path.name} saka {first!r}, "
            f"src/saeima/topics.py — {RUBRIC_VERSION!r}")
    criteria: dict[str, str] = {}
    topic: str | None = None
    for line in lines:
        head = _TOPIC_HEAD_RE.match(line)
        if head:
            topic = head.group(1)
            continue
        if line.startswith("## "):
            topic = None
            continue
        m = _IETVER_RE.match(line)
        if topic and m and topic not in criteria:
            criteria[topic] = _RULE_REF_TAIL_RE.sub(")", _RULE_REF_RE.sub("", m.group(1)))
    if set(criteria) != set(TOPIC_GROUPS):
        missing = sorted(set(TOPIC_GROUPS) - set(criteria))
        extra = sorted(set(criteria) - set(TOPIC_GROUPS))
        raise ValueError(f"rubrikas tēmas ≠ TOPIC_GROUPS: trūkst {missing}, lieki {extra}")
    return criteria


def _questions(n: int, criteria: dict[str, str]) -> dict:
    return {f"q{i}": {"type": "choice", "instructions": INSTRUCTIONS.format(i=i),
                      "criteria": criteria} for i in range(n)}


def prompt_hash(criteria: dict[str, str], chunk_size: int) -> str:
    """Atslēgā arī rindu skaits pieprasījumā: atbilde ir atkarīga no kaimiņiem paketē."""
    blob = json.dumps([INSTRUCTIONS, criteria, {"chunk_size": chunk_size}],
                      ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()


def _cache_conn() -> sqlite3.Connection:
    path = Path(CACHE_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=30.0)
    db.execute("CREATE TABLE IF NOT EXISTS topic_answers (input_hash TEXT NOT NULL,"
               " rubric_version TEXT NOT NULL, prompt_hash TEXT NOT NULL, model TEXT NOT NULL,"
               " topic TEXT NOT NULL, confidence REAL,"
               " PRIMARY KEY (input_hash, rubric_version, prompt_hash, model))")
    return db


def _cache_get(hashes: list[str], model: str, phash: str) -> dict[str, Prediction]:
    out: dict[str, Prediction] = {}
    with closing(_cache_conn()) as db:
        for h in set(hashes):
            row = db.execute("SELECT topic, confidence FROM topic_answers WHERE input_hash=?"
                             " AND rubric_version=? AND prompt_hash=? AND model=?",
                             (h, RUBRIC_VERSION, phash, model)).fetchone()
            if row and row[0] in TOPIC_GROUPS:
                out[h] = Prediction(row[0], row[1], model)
    return out


def cached_prediction(ihash: str, model: str = JEV_MODEL,
                      chunk_size: int = JEV_CHUNK_SIZE) -> Prediction | None:
    """Kešā glabātā Jev atbilde šim `input_hash` ar pašreizējo rubriku, promptu un
    pieprasījuma izmēru (bez zvana)."""
    return _cache_get([ihash], model,
                      prompt_hash(load_rubric_criteria(), chunk_size)).get(ihash)


def _cache_put(items: dict[str, Prediction], phash: str) -> None:
    if not items:
        return
    with closing(_cache_conn()) as db:
        db.executemany("INSERT OR REPLACE INTO topic_answers VALUES (?, ?, ?, ?, ?, ?)",
                       [(h, RUBRIC_VERSION, phash, p.model, p.topic, p.confidence)
                        for h, p in items.items()])
        db.commit()


def _call_batch(texts: list[str], criteria: dict[str, str], model: str,
                stats: JevStats) -> tuple[list[Prediction | None], str | None]:
    """Viena pakete; atgriež (prognozes, atbildējušais modelis). Izņēmumu nemet."""
    state = {"rows": [{"input_text": t} for t in texts]}
    try:
        resp = system_one(state, _questions(len(texts), criteria), model=model)
    except json.JSONDecodeError as e:
        # Serviss atbildēja ar ne-JSON ķermeni — kļūdaina atbilde, ne mūsu kods.
        stats.malformed += len(texts)
        log.warning("topic_classifiers: Jev atbilde nav JSON (rindu skaits: %d): %s", len(texts), e)
        return [None] * len(texts), None
    except TypeSafeUnavailable as e:
        stats.unavailable += len(texts)
        log.warning("topic_classifiers: Jev nav pieejams (rindu skaits: %d): %s", len(texts), e)
        return [None] * len(texts), None
    if not isinstance(resp, dict) or not isinstance(resp.get("answers"), dict):
        stats.malformed += len(texts)
        log.warning("topic_classifiers: Jev atbildē nav 'answers' vārdnīcas: %r", type(resp).__name__)
        return [None] * len(texts), None
    stats.requests += 1
    usage = resp.get("usage") or {}
    stats.input_tokens += int(usage.get("input_tokens", 0) or 0)
    stats.output_tokens += int(usage.get("output_tokens", 0) or 0)
    used = resp.get("model")
    used = str(used) if used else None
    if used:
        stats.models.add(used)
    preds: list[Prediction | None] = []
    for i in range(len(texts)):
        ans = resp["answers"].get(f"q{i}")
        choice = ans.get("choice") if isinstance(ans, dict) else None
        if choice not in TOPIC_GROUPS:
            stats.malformed += 1
            log.warning("topic_classifiers: Jev atbilde q%d nav kanoniska tēma: %r", i, choice)
            preds.append(None)
            continue
        try:
            conf = float(ans.get("confidence"))
        except (TypeError, ValueError):
            conf = None
        preds.append(Prediction(choice, conf, used))
    return preds, used


def classify_jev(rows: list[dict], *, model: str = JEV_MODEL,
                 batch_size: int = JEV_CHUNK_SIZE, stats: JevStats | None = None,
                 rubric_path: Path | None = None) -> list[Prediction | None]:
    """Jev tēma katrai rindai (izlīdzināta ar `rows`); `None` = nav derīgas atbildes.

    No rindas lasa tikai `input_text` (un `input_hash`, ja ir — citādi aprēķina).
    Noklusējums `JEV_MODEL` (piesaistīta versija, `src/saeima/topics.py`): sliekšņi
    mērīti vienam modelim; aliasu (`jev-latest`) padod tikai apzināti.
    """
    if not 1 <= batch_size <= MAX_BATCH:
        raise ValueError(f"batch_size jābūt 1…{MAX_BATCH}")
    stats = stats if stats is not None else JevStats()
    criteria = load_rubric_criteria(rubric_path)
    # Atslēga = nominālais izmērs (jāzina pirms sūtīšanas); pie 1 tas sakrīt ar faktisko.
    phash = prompt_hash(criteria, batch_size)
    texts = [str(r["input_text"]) for r in rows]
    hashes = [input_hash(t) for t in texts]
    result: list[Prediction | None] = [None] * len(rows)
    # Aliasu atrisina pirmā atbilde; līdz tam kešu nevar jautāt.
    resolved: str | None = None if model.endswith("-latest") else model
    todo = list(range(len(rows)))
    while todo:
        if resolved:
            cached = _cache_get([hashes[i] for i in todo], resolved, phash)
            stats.cache_hits += sum(1 for i in todo if hashes[i] in cached)
            if cached:
                stats.models.add(resolved)
            for i in todo:
                if hashes[i] in cached:
                    result[i] = cached[hashes[i]]
            todo = [i for i in todo if hashes[i] not in cached]
            # Vienāds teksts paketē tikai vienreiz.
            seen: dict[str, int] = {}
            for i in todo:
                seen.setdefault(hashes[i], i)
            send = list(seen.values())[:batch_size]
        else:
            send = todo[:batch_size]
        if not send:
            break
        preds, used = _call_batch([texts[i] for i in send], criteria,
                                  resolved or model, stats)
        if used and not resolved:
            resolved = used
        fresh: dict[str, Prediction] = {}
        for i, p in zip(send, preds, strict=True):
            result[i] = p
            if p is not None and p.model:
                fresh[hashes[i]] = p
        _cache_put(fresh, phash)
        sent_hashes = {hashes[i] for i in send}
        # Nosūtītās (arī neveiksmīgās) rindas neatkārto; dublikāti saņem to pašu.
        for i in todo:
            if hashes[i] in sent_hashes and result[i] is None:
                result[i] = next((result[j] for j in send if hashes[j] == hashes[i]), None)
        todo = [i for i in todo if hashes[i] not in sent_hashes]
    return result
