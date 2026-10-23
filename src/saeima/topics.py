"""Saeimas balsojumu tēmas — vienīgais rakstītājs (spec 2026-10-21).

Lēmums tiek pieņemts dokumentam (`document_key`), balsojumi un to ieraksti to
manto. `saeima_votes.topic` / `claims.topic` (claim_type='saeima_vote') raksta
TIKAI šis modulis.
"""
from __future__ import annotations

import hashlib
import os
import re
import sqlite3
import subprocess
from contextlib import contextmanager
from pathlib import Path

from src.topic_map import TOPIC_GROUPS

PROCEDURAL_TOPIC = "Saeimas darbs"
RUBRIC_VERSION = "2026-10-22.2"

_DOCNR_RE = re.compile(r"\b(\d+)/(Lp|Lm|P)(\d+)\b")
_CANON_RE = re.compile(r"^\d+/(Lp|Lm|P)\d+$")


def document_key(document_nr: str | None, motif: str) -> tuple[str | None, str]:
    """Normalizēta dokumenta atslēga balsojumam; None = kails numurs, ko motīvs neatrisina."""
    raw = (document_nr or "").strip()
    if _CANON_RE.match(raw):
        return raw, "canonical"
    found = {f"{n}/{k}{c}" for n, k, c in _DOCNR_RE.findall(motif or "")}
    if raw.isdigit():
        hits = [f for f in found if f.split("/")[0] == raw]
        if len(hits) == 1:
            return hits[0], "bare-number-repaired"
        return None, f"kails numurs {raw}: motīvā {len(hits)} atbilstības"
    if len(found) == 1:
        return found.pop(), "from-motif"
    digest = hashlib.sha1((motif or "").strip().encode("utf-8")).hexdigest()[:12]
    if len(found) > 1:
        # Vairāki numuri (piem., balsojums 3512): sava atslēga, bet lēmums tikai
        # ar roku — `reason='multi'` liek klasifikatoram atteikties (8. uzd.).
        return f"motif:{digest}", "multi"
    return f"motif:{digest}", "no-number"


# --- Klasifikatora ievade (`input_text`) -------------------------------------
#
# Viena forma zelta kopai (`scripts/vote_topic_gold_sample.py`) un ielādei: slieksnis
# ir mērīts uz šīs formas, tāpēc ielāde nedrīkst sūtīt citādu tekstu.

SUMMARY_MAX, SUMMARY_N = 600, 3
_NR_IN_MOTIF = re.compile(r"\(\s*(?:Nr\.\s*)?\d+\s*/\s*(?:Lp|Lm|P)\d+\s*\)")
_LEADING_PROC = re.compile(
    r"^\s*(?:Par\s+priekšlikumu\s+Nr\.?\s*\d+\.?\s*(?:\([^)]*\))?\s*[—–-]?\s*"
    r"|Par\s+likumprojekta\s+atzīšanu\s+par\s+steidzamu\.\s*"
    r"|Par\s+likumprojekta\s+)+",
    re.IGNORECASE)


def document_title(motif: str, key: str | None) -> str:
    """Motīvs līdz pirmajam «(NNN/XxNN)», bez sākuma procedūras frāzēm; `motif:` → viss."""
    if key is None or key.startswith("motif:"):
        return motif.strip()
    head = _NR_IN_MOTIF.split(motif, maxsplit=1)[0]
    return _LEADING_PROC.sub("", head).strip(" ,.—–-") or motif.strip()


def compose_input_text(title: str, summaries: list[str],
                       bill: tuple[str | None, str | None] | None) -> str:
    """«Virsraksts:» + līdz 3 «Kopsavilkums:» + likumprojekta rindas (bez atkārtojumiem)."""
    lines = [f"Virsraksts: {title}"]
    lines += [f"Kopsavilkums: {s[:SUMMARY_MAX]}" for s in summaries[:SUMMARY_N]]
    if bill:  # dublikātus (Lm rindās bieži = virsraksts/kopsavilkums) neatkārto
        b_title = (bill[0] or "").strip()
        b_summary = (bill[1] or "").strip()[:SUMMARY_MAX]
        if b_title and b_title != title:
            lines.append(f"Likumprojekts: {b_title}")
        if b_summary and b_summary not in {s[:SUMMARY_MAX] for s in summaries[:SUMMARY_N]}:
            lines.append(f"Likumprojekta kopsavilkums: {b_summary}")
    return "\n".join(lines)


def ingest_input_text(db, document_nr: str | None, motif: str, summary: str | None) -> str:
    """`input_text` vienam jaunam balsojumam: tā motīvs, summary un likumprojekts (ja ir)."""
    key, _ = document_key(document_nr, motif)
    bill = None
    # `saeima_bills` veido `init_saeima_bills`, ne `init_saeima_tables` — DB bez tās ir derīga.
    has_bills = db.execute("SELECT 1 FROM sqlite_master WHERE type='table'"
                           " AND name='saeima_bills'").fetchone()
    if key and not key.startswith("motif:") and has_bills:
        row = db.execute("SELECT title, summary FROM saeima_bills WHERE document_nr=?"
                         " ORDER BY id LIMIT 1", (key,)).fetchone()
        bill = (row[0], row[1]) if row else None
    s = (summary or "").strip()
    return compose_input_text(document_title(motif or "", key), [s] if s else [], bill)


# --- Partiju dzinējs: lēmums → freeze (snapshot) → rollback fails → apply ----
#
# Transakcijas: `get_db()` dod savienojumu ar Python noklusēto (legacy)
# isolation_level, kas pirms DML pats atver transakciju. Tāpēc katra rakstošā
# darbība šeit (1) atsakās, ja savienojumā jau ir nepabeigta transakcija (citādi
# mūsu COMMIT/ROLLBACK paņemtu līdzi arī izsaucēja darbu), un (2) pati izpilda
# `BEGIN IMMEDIATE` … `COMMIT` / `ROLLBACK` — rakstīšanas slēdzene tiek paņemta
# PIRMS lasīšanas, tāpēc snapshot un pārbaudes redz to pašu stāvokli, ko maina.

REPO_ROOT = Path(__file__).resolve().parents[2]

_DECISION_SQL = (
    "SELECT d.topic FROM saeima_document_topics d WHERE d.document_key = {key}"
    " AND d.review_status != 'rejected' ORDER BY d.id DESC LIMIT 1"
)


@contextmanager
def _write_tx(db: sqlite3.Connection):
    if db.in_transaction:
        raise RuntimeError(
            "savienojumā ir nepabeigta transakcija — vispirms commit() vai rollback()")
    db.execute("BEGIN IMMEDIATE")
    try:
        yield
        db.execute("COMMIT")
    except BaseException:
        # Sargs: ja SQLite transakciju jau atcēla pats, ROLLBACK kļūda
        # aizsegtu sākotnējo; neizdevies COMMIT arī nonāk šeit.
        if db.in_transaction:
            db.execute("ROLLBACK")
        raise


# Vai kāda VĒLĀK piemērota partija skar kaut vienu šīs partijas rindu? Atkarīgs
# tikai no partiju statusiem, tāpēc rollback failā tā pati atbilde visiem
# priekšrakstiem. Secība pēc `applied_at` ar milisekundēm (UTC). Stingrais `>`:
# vienādi laiki praksē nerodas, jo piemērošanas serializējas zem BEGIN IMMEDIATE
# un katra ilgst vismaz sekundes (tas pats salīdzinājums `rollback_batch`).
_LATER_OVERLAP_SQL = (
    "EXISTS (SELECT 1 FROM vote_topic_snapshot s JOIN vote_topic_snapshot o"
    " ON o.table_name = s.table_name AND o.row_id = s.row_id AND o.batch_id != s.batch_id"
    " JOIN vote_topic_batches ob ON ob.batch_id = o.batch_id AND ob.status = 'applied'"
    " JOIN vote_topic_batches sb ON sb.batch_id = s.batch_id"
    " WHERE s.batch_id = {b} AND ob.applied_at > sb.applied_at)"
)
_NOW_MS = "strftime('%Y-%m-%d %H:%M:%f', 'now')"


def record_decision(db, key, topic, *, method, model, confidence, input_hash,
                    review_status="auto", document_nr_raw=None) -> int:
    """Pieraksta dokumenta tēmas lēmumu (tikai pievieno; jaunākais derīgais uzvar).

    Komitē pats, ja izsaucējs nav atvēris savu transakciju.
    """
    if topic not in TOPIC_GROUPS:
        raise ValueError(f"nekanoniska tēma: {topic!r}")
    if not key:
        raise ValueError("tukša dokumenta atslēga")
    outer = db.in_transaction
    cur = db.execute(
        "INSERT INTO saeima_document_topics (document_key, document_nr_raw, topic,"
        " method, model, confidence, input_hash, rubric_version, review_status)"
        " VALUES (?,?,?,?,?,?,?,?,?)",
        (key, document_nr_raw, topic, method, model,
         confidence, input_hash, RUBRIC_VERSION, review_status))
    if not outer:
        db.commit()
    return cur.lastrowid


def current_decision(db, key):
    return db.execute(
        "SELECT * FROM saeima_document_topics WHERE document_key=? AND "
        "review_status != 'rejected' ORDER BY id DESC LIMIT 1", (key,)).fetchone()


# --- Ielāde: jauna balsojuma tēma no dokumenta lēmuma (plāns, 8. uzd.) ------
#
# Ielādes klasifikators — operatora lēmums 2026-10-22 (`data/saeima_topic_gold/
# ATSKAITE.md`, CHANGELOG 2026-10-22 (2)): Jev; prognoze ar pārliecību zem sliekšņa
# (vai None / kļūda) → atslēgvārdu tēma ar `review_status='pending'`.
INGEST_METHOD = "jev"
# Ielāde: max(dev likums, 0,9) — ielādē nav pārbaudes pret esošo tēmu.
INGEST_CONFIDENCE_THRESHOLD = 0.9
# Vēsturiskās partijas (plāna 9. uzd. 1. solis): dev likums (zemākais t ar dev
# precizitāti ≥ 0,90, solis 0,05) uz jev-1.14.0 ar vienu dokumentu pieprasījumā
# (`data/saeima_topic_gold/ATSKAITE.md` § Jev 1.14, viens dokuments pieprasījumā).
# Agrākais 0,7 bija mērīts 16 dokumentu paketēs un šai formai neder.
BATCH_CONFIDENCE_THRESHOLD = 0.8
# Abi sliekšņi mērīti TIKAI šim modelim un `JEV_CHUNK_SIZE` — ne `jev-latest`.
# Jauna versija vai cits pieprasījuma izmērs = jauns mērījums pirms nomaiņas.
JEV_MODEL = "jev-1.14.0"
# Viens dokuments vienā Jev pieprasījumā — visur (ielāde, partijas, zelta mērījums).
# Jev atbilde atkarīga no pārējiem dokumentiem tajā pašā pieprasījumā (565/Lp14 viens:
# Tieslietas ~0,74; 16 dokumentu paketē: Budžets 0,27), tāpēc sliekšņi der tikai tai
# pieprasījuma formai, kurā mērīti (ATSKAITE § Jev 1.14, viens dokuments pieprasījumā).
JEV_CHUNK_SIZE = 1
# Klātbūtnes reģistrācija ir parlamenta iekšējā kārtība (Global Constraints) —
# noteikums, ne klasifikators. Prefikss, ne apakšvirkne (sk. votes.py).
REGISTRATION_MOTIF_PREFIX = "Deputātu klātbūtnes reģistrācija"
# Kārtības rullis → «Valsts pārvalde» vienmēr (RUBRIKA 2026-10-22.2; Jev to b01/b02 sauca
# citādi). Tikai «rullī/rullis» — «(Saeimas kārtības ruļļa 39.p. kārtībā)» ir procedūra
# CITĀ likumā (40+ dokumenti), tiem tēmu dod Jev.
RULES_OF_PROCEDURE_TOPIC = "Valsts pārvalde"
_RULES_OF_PROCEDURE_RE = re.compile(r"\bSaeimas kārtības rull(?:ī|is)\b")


# Kails «Par priekšlikumu [Nr.N]» bez dokumenta numura: tā `motif:` atslēga apvieno
# dažādu likumu balsojumus (2609 + 6686, b02) — ielāde tās lēmumu nemanto.
_BARE_AMENDMENT_RE = re.compile(r"^\s*Par\s+priekšlikumu(?:\s+Nr\.?\s*\d+)?\s*$", re.I)


def rule_topic(motif: str) -> str | None:
    """Tēma no noteikuma (bez klasifikatora) vai `None`; kopīgs ielādei un `classify`."""
    motif = (motif or "").strip()
    if motif.startswith(REGISTRATION_MOTIF_PREFIX):
        return PROCEDURAL_TOPIC
    if _RULES_OF_PROCEDURE_RE.search(motif):
        return RULES_OF_PROCEDURE_TOPIC
    return None
# `off` = klasifikatoru nesauc (ielāde bez tīkla; testos vienmēr — tests/conftest.py).
CLASSIFIER_SWITCH_ENV = "ATMINA_VOTE_TOPIC_CLASSIFIER"


def _ingest_classify(input_text: str):
    """Viens Jev zvans vienam dokumentam → (Prediction | None, kļūdas teksts | None).

    Nekad nemet: `classify_jev` pats norij `TypeSafeUnavailable`, bet rubrikas
    versijas kļūda, kešs vai cita kļūme ielādi apturēt nedrīkst.
    """
    if os.environ.get(CLASSIFIER_SWITCH_ENV, "").strip().lower() == "off":
        return None, f"klasifikators izslēgts ({CLASSIFIER_SWITCH_ENV}=off)"
    from src.saeima import topic_classifiers as tc  # cikls: tc importē šo moduli
    try:
        return tc.classify_jev([{"input_text": input_text}], model=JEV_MODEL)[0], None
    except Exception as e:  # noqa: BLE001 — jebkura kļūme = rezerve + žurnāls
        return None, f"{type(e).__name__}: {e}"


def _keyword_topic(input_text: str, motif: str) -> str:
    from src.saeima import topic_classifiers as tc
    if (motif or "").strip():
        return tc.classify_keyword(input_text, motif).topic
    from src.saeima.claims import _motif_to_topic
    return _motif_to_topic(motif or "")


def _db_file(db) -> str | None:
    """Savienojuma galvenās DB fails — `log_action` raksta tajā pašā DB."""
    row = db.execute("PRAGMA database_list").fetchone()
    return row[2] if row and row[2] else None


def topic_for_new_vote(db, document_nr, motif, input_text) -> str:
    """Tēma jaunam balsojumam; viens klasifikatora zvans dokumentam, ne balsojumam.

    1) Atslēgai jau ir lēmums (arī `pending`) → tā tēma, bez zvana.
    2) Noteikums (`rule_topic`: klātbūtnes reģistrācija, kārtības rullis) → `auto`, bez zvana.
    3) Atslēga `None` (arī kails «Par priekšlikumu Nr.N») vai `reason='multi'` → atslēgvārdi, klasifikatoru nesauc;
       `multi` saņem `pending` lēmumu, `None` atslēgai lēmumu ierakstīt nevar
       (nav atslēgas) — paliek tikai žurnāla rinda.
    4) Citādi Jev: pārliecība ≥ `INGEST_CONFIDENCE_THRESHOLD` → `auto`; zemāk,
       `None` vai kļūda → atslēgvārdu tēma, `pending`.
    Katrs rezerves gadījums → `log_action('vote_topic_fallback', status='warning')`.

    Komitē lēmumu pats — izsaucējam nedrīkst būt atvērtas transakcijas.
    """
    from src.db import log_action
    from src.saeima.topic_classifiers import input_hash

    motif = motif or ""
    key, reason = document_key(document_nr, motif)
    if reason == "no-number" and _BARE_AMENDMENT_RE.match(motif):
        key, reason = None, "kails «Par priekšlikumu» bez dokumenta numura"
    if key is not None:
        dec = current_decision(db, key)
        if dec is not None:
            return dec["topic"]
    ihash = input_hash(input_text)

    def record(topic, *, method, model=None, confidence=None, status="auto"):
        record_decision(db, key, topic, method=method, model=model, confidence=confidence,
                        input_hash=ihash, review_status=status, document_nr_raw=document_nr)

    def fallback(why, **extra) -> str:
        topic = _keyword_topic(input_text, motif)
        if key is not None:
            record(topic, method="keyword", status="pending")
        log_action(action="vote_topic_fallback", status="warning",
                   error_message=f"{key or document_nr}: {why} — tēma no atslēgvārdiem"
                                 f" «{topic}», lēmums gaida pārskatīšanu",
                   details={"document_key": key, "document_nr": document_nr,
                            "reason": why, "topic": topic, **extra},
                   db_path=_db_file(db))
        return topic

    ruled = rule_topic(motif)
    if ruled is not None and key is not None:
        record(ruled, method="keyword")
        return ruled
    if key is None:
        return fallback(reason)
    if reason == "multi":
        return fallback("multi: motīvā vairāki dokumentu numuri — lēmums tikai ar roku")

    pred, error = _ingest_classify(input_text)
    if pred is not None and pred.confidence is not None \
            and pred.confidence >= INGEST_CONFIDENCE_THRESHOLD:
        record(pred.topic, method=INGEST_METHOD, model=pred.model, confidence=pred.confidence)
        return pred.topic
    if pred is None:
        why = f"{INGEST_METHOD}: {error or 'nav derīgas atbildes'}"
    else:
        why = f"{INGEST_METHOD}: pārliecība {pred.confidence} < {INGEST_CONFIDENCE_THRESHOLD}"
    return fallback(why, classifier_topic=pred.topic if pred else None,
                    classifier_confidence=pred.confidence if pred else None,
                    classifier_model=pred.model if pred else None)


def _votes_for_keys(db, keys) -> list[tuple[str, int]]:
    """(atslēga, vote_id) visiem balsojumiem, kuru `document_key` ir `keys` kopā.

    `None` atslēga (neatrisināts kails numurs) nekad netiek piesaistīta.
    """
    wanted = {k for k in keys if k is not None}
    out = []
    for vid, nr, motif in db.execute("SELECT id, document_nr, motif FROM saeima_votes"):
        k, _ = document_key(nr, motif)
        if k is not None and k in wanted:
            out.append((k, vid))
    return out


def _batch_status(db, batch_id) -> tuple[str, str | None]:
    row = db.execute("SELECT status, rollback_file FROM vote_topic_batches "
                     "WHERE batch_id=?", (batch_id,)).fetchone()
    if row is None:
        raise ValueError(f"partija {batch_id!r} neeksistē")
    return row[0], row[1]


def freeze_batch(db, batch_id, keys, *, allow_pending=False) -> dict:
    """Iesaldē partiju: dalībnieki + snapshot (vecā → jaunā tēma) katrai rindai.

    Snapshot tiek ierakstīts arī rindām, kur vecā == jaunā, lai atgriešana būtu
    precīza. Atsakās (ValueError): esošs batch_id, atslēga bez lēmuma, lēmums
    `pending` (zemas pārliecības rezerve, gaida cilvēku — spec § Lēmumi 6) bez
    `allow_pending`, 0 balsojumu; (RuntimeError): balsojums jau ir citā vēl
    nepiemērotā partijā.
    """
    keys = list(dict.fromkeys(k for k in keys if k))
    if not keys:
        raise ValueError("nav atslēgu")
    with _write_tx(db):
        if db.execute("SELECT 1 FROM vote_topic_batches WHERE batch_id=?",
                      (batch_id,)).fetchone():
            raise ValueError(f"partija {batch_id!r} jau ir")
        missing = [k for k in keys if current_decision(db, k) is None]
        if missing:
            raise ValueError(f"nav lēmuma: {', '.join(missing[:10])}"
                             + (f" (+{len(missing) - 10})" if len(missing) > 10 else ""))
        pending = [k for k in keys if current_decision(db, k)["review_status"] == "pending"]
        if pending and not allow_pending:
            raise ValueError(f"{len(pending)} atslēgām lēmums ir 'pending' (gaida pārskatīšanu):"
                             f" {', '.join(pending[:10])} — apzināti: allow_pending/--allow-pending")
        members = _votes_for_keys(db, keys)
        if not members:
            raise ValueError(f"atslēgām {len(keys)} atrasti 0 balsojumu")
        db.execute("INSERT INTO vote_topic_batches (batch_id, status) VALUES (?, 'snapshotted')",
                   (batch_id,))
        db.executemany("INSERT INTO vote_topic_batch_members (batch_id, document_key, vote_id)"
                       " VALUES (?,?,?)", [(batch_id, k, vid) for k, vid in members])
        busy = db.execute(
            "SELECT count(*) FROM vote_topic_batch_members m JOIN vote_topic_batch_members o"
            " ON o.vote_id = m.vote_id AND o.batch_id != m.batch_id"
            " JOIN vote_topic_batches b ON b.batch_id = o.batch_id AND b.status = 'snapshotted'"
            " WHERE m.batch_id = ?", (batch_id,)).fetchone()[0]
        if busy:
            raise RuntimeError(f"{busy} balsojumi jau ir citā iesaldētā, nepiemērotā partijā")
        db.execute(
            "INSERT INTO vote_topic_snapshot (batch_id, table_name, row_id, old_topic, new_topic)"
            " SELECT m.batch_id, 'saeima_votes', v.id, v.topic, ("
            + _DECISION_SQL.format(key="m.document_key") + ")"
            " FROM vote_topic_batch_members m JOIN saeima_votes v ON v.id = m.vote_id"
            " WHERE m.batch_id = ?", (batch_id,))
        db.execute(
            "INSERT INTO vote_topic_snapshot (batch_id, table_name, row_id, old_topic, new_topic)"
            " SELECT s.batch_id, 'claims', c.id, c.topic, s.new_topic"
            " FROM vote_topic_snapshot s JOIN saeima_votes v ON v.id = s.row_id"
            " JOIN claims c ON c.source_url = v.url AND c.claim_type = 'saeima_vote'"
            " WHERE s.batch_id = ? AND s.table_name = 'saeima_votes'", (batch_id,))
        counts = dict(db.execute("SELECT table_name, count(*) FROM vote_topic_snapshot"
                                 " WHERE batch_id=? GROUP BY table_name", (batch_id,)).fetchall())
    return {"members": len(members), "keys": len(keys), "pending": len(pending),
            "snapshot_votes": counts.get("saeima_votes", 0),
            "snapshot_claims": counts.get("claims", 0)}


def _repo_relative(path: Path) -> str:
    path = Path(path).resolve()
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def _resolve(rb: str) -> Path:
    p = Path(rb)
    return p if p.is_absolute() else REPO_ROOT / p


def write_rollback_sql(db, batch_id, path) -> Path:
    """Uzraksta atgriešanas SQL partijai (atjauno no vote_topic_snapshot).

    Fails darbojas tikai, kamēr partija ir `applied` UN neviena vēlāk piemērota
    partija neskar tās rindas — citādi (arī atkārtoti vai pirms piemērošanas)
    tas neko nemaina. Esošu failu nepārraksta.
    """
    status, _ = _batch_status(db, batch_id)
    if status != "snapshotted":
        raise RuntimeError(f"partija {batch_id} ir {status}; rollback failu raksta tikai iesaldētai")
    path = Path(path)
    if path.exists():
        raise RuntimeError(f"rollback fails {path} jau ir — nepārrakstu")
    path.parent.mkdir(parents=True, exist_ok=True)
    b = batch_id.replace("'", "''")
    later = _LATER_OVERLAP_SQL.format(b=f"'{b}'")
    applied = (f"(SELECT status FROM vote_topic_batches WHERE batch_id='{b}') = 'applied'"
               f"\n  AND NOT {later}")
    sql = f"""-- Rollback: vote topic batch {batch_id}
-- Forward: scripts/vote_topics.py apply {batch_id} (spec 2026-10-21-saeimas-balsojumu-temas)
-- ATKARĪBA: atjauno no vote_topic_snapshot (šī partija) — tās rindas nedrīkst dzēst.
-- Iedarbojas tikai, ja partijas statuss ir 'applied' un neviena vēlāk piemērota
-- partija neskar tās pašas rindas (citādi neko nemaina); drošs atkārtot.
BEGIN;
UPDATE saeima_votes SET topic = (SELECT old_topic FROM vote_topic_snapshot s
  WHERE s.batch_id='{b}' AND s.table_name='saeima_votes' AND s.row_id=saeima_votes.id)
WHERE id IN (SELECT row_id FROM vote_topic_snapshot WHERE batch_id='{b}' AND table_name='saeima_votes')
  AND {applied};
UPDATE claims SET topic = (SELECT old_topic FROM vote_topic_snapshot s
  WHERE s.batch_id='{b}' AND s.table_name='claims' AND s.row_id=claims.id)
WHERE id IN (SELECT row_id FROM vote_topic_snapshot WHERE batch_id='{b}' AND table_name='claims')
  AND {applied};
-- Ieraksti, kas radušies PĒC piemērošanas (atkārtota ielāde, jauns deputāts): snapshot
-- tos nepazīst, bet tie nes balsojuma jauno tēmu → atpakaļ uz balsojuma veco (T2).
UPDATE claims SET topic = (SELECT s.old_topic FROM vote_topic_snapshot s
  JOIN saeima_votes v ON v.id = s.row_id
  WHERE s.batch_id='{b}' AND s.table_name='saeima_votes' AND v.url = claims.source_url
    AND s.new_topic IS claims.topic LIMIT 1)
WHERE claim_type = 'saeima_vote'
  AND id NOT IN (SELECT row_id FROM vote_topic_snapshot WHERE batch_id='{b}' AND table_name='claims')
  AND EXISTS (SELECT 1 FROM vote_topic_snapshot s JOIN saeima_votes v ON v.id = s.row_id
    WHERE s.batch_id='{b}' AND s.table_name='saeima_votes' AND v.url = claims.source_url
      AND s.new_topic IS claims.topic AND s.old_topic IS NOT NULL)
  AND {applied};
UPDATE vote_topic_batches SET status='rolled_back' WHERE batch_id='{b}' AND {applied};
COMMIT;
"""
    with open(path, "x", encoding="utf-8") as fh:
        fh.write(sql)
    with _write_tx(db):
        db.execute("UPDATE vote_topic_batches SET rollback_file=? WHERE batch_id=?",
                   (_repo_relative(path), batch_id))
    return path


def _is_tracked(path) -> bool:
    """True tikai, ja fails ir repo, git to seko un darba kopija == HEAD."""
    p = _resolve(str(path)).resolve()
    try:
        rel = p.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return False
    if not p.exists():
        return False
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", "--", rel],
                             cwd=REPO_ROOT, capture_output=True)
    if tracked.returncode != 0:
        return False
    clean = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", rel],
                           cwd=REPO_ROOT, capture_output=True)
    return clean.returncode == 0


def _distribution(db, batch_id, table) -> dict:
    return dict(db.execute(
        f"SELECT t.topic, count(*) FROM {table} t JOIN vote_topic_snapshot s "
        "ON s.row_id=t.id AND s.table_name=? AND s.batch_id=? GROUP BY t.topic",
        (table, batch_id)).fetchall())


def _update_rows(db, batch_id, table) -> int:
    """Viens kopas UPDATE; rinda mainās TIKAI, ja tās tēma joprojām ir snapshot vecā.

    Ja kaut viena rinda kopš iesaldēšanas mainīta vai dzēsta, skaits nesakrīt →
    RuntimeError('drift'), un izsaucēja transakcija atceļas.
    """
    expected = db.execute("SELECT count(*) FROM vote_topic_snapshot WHERE batch_id=?"
                          " AND table_name=?", (batch_id, table)).fetchone()[0]
    cur = db.execute(
        f"UPDATE {table} SET topic = s.new_topic FROM vote_topic_snapshot s"
        f" WHERE s.batch_id = ? AND s.table_name = ? AND s.row_id = {table}.id"
        f" AND {table}.topic IS s.old_topic", (batch_id, table))
    if cur.rowcount != expected:
        raise RuntimeError(f"drift: {table} — {expected - cur.rowcount} no {expected} rindām "
                           "kopš iesaldēšanas mainītas vai dzēstas")
    return cur.rowcount


def _update_claims(db, batch_id) -> int:
    return _update_rows(db, batch_id, "claims")


def _check_membership(db, batch_id) -> None:
    """Kopš iesaldēšanas nedrīkst rasties jauni balsojumi/ieraksti partijas atslēgām."""
    keys = [r[0] for r in db.execute("SELECT DISTINCT document_key FROM vote_topic_batch_members"
                                     " WHERE batch_id=?", (batch_id,))]
    now = {vid for _, vid in _votes_for_keys(db, keys)}
    frozen = {r[0] for r in db.execute("SELECT vote_id FROM vote_topic_batch_members"
                                       " WHERE batch_id=?", (batch_id,))}
    if now != frozen:
        raise RuntimeError(f"drift: balsojumu kopa mainījusies ({len(now - frozen)} jauni, "
                           f"{len(frozen - now)} pazuduši) — iesaldē no jauna")
    extra = db.execute(
        "SELECT count(*) FROM vote_topic_batch_members m JOIN saeima_votes v ON v.id = m.vote_id"
        " JOIN claims c ON c.source_url = v.url AND c.claim_type = 'saeima_vote'"
        " WHERE m.batch_id = ? AND NOT EXISTS (SELECT 1 FROM vote_topic_snapshot s"
        "   WHERE s.batch_id = m.batch_id AND s.table_name = 'claims' AND s.row_id = c.id)",
        (batch_id,)).fetchone()[0]
    if extra:
        raise RuntimeError(f"drift: {extra} jauni balsojumu ieraksti kopš iesaldēšanas")


def _collisions(db, batch_id) -> int:
    """(opponent_id, source_url, topic) dublikāti GALA stāvoklī (T2, Data Contract #3).

    Skatās visus ierakstus (jebkura claim_type) ar partijas balsojumu URL; gala
    tēma = snapshot jaunā, ja rinda ir partijā, citādi tagadējā.
    """
    return db.execute(
        "WITH urls AS (SELECT v.url FROM vote_topic_batch_members m"
        "   JOIN saeima_votes v ON v.id = m.vote_id WHERE m.batch_id = ?),"
        " fin AS (SELECT c.opponent_id, c.source_url, COALESCE(s.new_topic, c.topic) AS topic"
        "   FROM claims c LEFT JOIN vote_topic_snapshot s ON s.batch_id = ?"
        "     AND s.table_name = 'claims' AND s.row_id = c.id"
        "   WHERE c.source_url IN (SELECT url FROM urls))"
        " SELECT count(*) FROM (SELECT 1 FROM fin GROUP BY opponent_id, source_url, topic"
        "   HAVING count(*) > 1)", (batch_id, batch_id)).fetchone()[0]


def _batch_parity(db, batch_id) -> int:
    return db.execute(
        "SELECT count(*) FROM vote_topic_batch_members m JOIN saeima_votes v ON v.id = m.vote_id"
        " JOIN claims c ON c.source_url = v.url AND c.claim_type = 'saeima_vote'"
        " WHERE m.batch_id = ? AND c.topic IS NOT v.topic", (batch_id,)).fetchone()[0]


def global_parity_mismatch(db) -> int:
    """Visā DB: `saeima_vote` ieraksti, kuru tēma atšķiras no sava balsojuma tēmas."""
    return db.execute(
        "SELECT count(*) FROM claims c JOIN saeima_votes v ON v.url = c.source_url"
        " WHERE c.claim_type = 'saeima_vote' AND c.topic IS NOT v.topic").fetchone()[0]


def apply_batch(db, batch_id, *, require_tracked=True) -> dict:
    """Piemēro iesaldētu partiju vienā transakcijā (viss vai nekas).

    Atsakās, ja: statuss nav `snapshotted`; rollback fails nav komitēts
    (eskalācija 8, ja `require_tracked`); balsojumu/ierakstu kopa vai kāda
    tēma kopš iesaldēšanas mainījusies (drift); rastos idempotences sadursme.
    """
    status, rb = _batch_status(db, batch_id)
    if status != "snapshotted":
        raise RuntimeError(f"partija {batch_id} ir {status}, nevar piemērot")
    if require_tracked and (not rb or not _is_tracked(rb)):
        raise RuntimeError(f"rollback {rb} nav komitēts — eskalācija 8")
    with _write_tx(db):
        status, _ = _batch_status(db, batch_id)
        if status != "snapshotted":
            raise RuntimeError(f"partija {batch_id} ir {status}, nevar piemērot")
        _check_membership(db, batch_id)
        collisions = _collisions(db, batch_id)
        if collisions:
            raise RuntimeError(f"{collisions} idempotences sadursmes — STOP (T2)")
        before = {t: _distribution(db, batch_id, t) for t in ("saeima_votes", "claims")}
        votes = _update_rows(db, batch_id, "saeima_votes")
        claims = _update_claims(db, batch_id)
        parity = _batch_parity(db, batch_id)
        if parity:
            raise RuntimeError(f"{parity} partijas ieraksti nesakrīt ar balsojuma tēmu — STOP")
        db.execute(f"UPDATE vote_topic_batches SET status='applied', applied_at={_NOW_MS}"
                   " WHERE batch_id=?", (batch_id,))
        after = {t: _distribution(db, batch_id, t) for t in ("saeima_votes", "claims")}
    return {"votes": votes, "claims": claims, "before": before, "after": after,
            "collisions": 0, "parity_mismatch": _batch_parity(db, batch_id),
            "parity_mismatch_global": global_parity_mismatch(db)}


def rollback_batch(db, batch_id) -> dict:
    """Izpilda partijas rollback failu un pārbauda, ka visas rindas atjaunotas."""
    status, rb = _batch_status(db, batch_id)
    if status != "applied":
        raise RuntimeError(f"partija {batch_id} ir {status}; atgriezt var tikai 'applied'")
    if not rb or not _resolve(rb).exists():
        raise RuntimeError(f"rollback fails {rb} nav atrodams")
    if db.in_transaction:
        raise RuntimeError(
            "savienojumā ir nepabeigta transakcija — vispirms commit() vai rollback()")
    later = db.execute(
        "SELECT DISTINCT o.batch_id FROM vote_topic_snapshot s JOIN vote_topic_snapshot o"
        " ON o.table_name = s.table_name AND o.row_id = s.row_id AND o.batch_id != s.batch_id"
        " JOIN vote_topic_batches ob ON ob.batch_id = o.batch_id AND ob.status = 'applied'"
        " JOIN vote_topic_batches sb ON sb.batch_id = s.batch_id"
        # Stingrais `>` — sk. komentāru pie _LATER_OVERLAP_SQL (vienādi laiki nerodas).
        " WHERE s.batch_id = ? AND ob.applied_at > sb.applied_at", (batch_id,)).fetchall()
    if later:
        raise RuntimeError("vēlāk piemērotas partijas skar tās pašas rindas: "
                           + ", ".join(r[0] for r in later) + " — vispirms atgriez tās")
    try:
        db.executescript(_resolve(rb).read_text(encoding="utf-8"))
    except BaseException:
        if db.in_transaction:  # fails krita pusceļā — neatstāj pusi
            db.execute("ROLLBACK")
        raise
    if _batch_status(db, batch_id)[0] != "rolled_back":
        raise RuntimeError(f"rollback {rb} neiestatīja statusu 'rolled_back'")
    out = {}
    for table, key in (("saeima_votes", "votes"), ("claims", "claims")):
        bad = db.execute(
            f"SELECT count(*) FROM vote_topic_snapshot s LEFT JOIN {table} t ON t.id = s.row_id"
            f" WHERE s.batch_id = ? AND s.table_name = ? AND t.topic IS NOT s.old_topic",
            (batch_id, table)).fetchone()[0]
        if bad:
            raise RuntimeError(f"pēc rollback {bad} {table} rindām nav vecās tēmas")
        out[key] = db.execute("SELECT count(*) FROM vote_topic_snapshot WHERE batch_id=?"
                              " AND table_name=?", (batch_id, table)).fetchone()[0]
    # Snapshot rindas pārbaudītas precīzi augstāk. Atlikušie partijas balsojumu ieraksti
    # (radušies pēc piemērošanas) drīkst atšķirties no balsojuma tēmas 0 reižu; pilnā
    # partijas paritāte var būt > 0 tikai tad, ja tāda atšķirība bija jau PIRMS apply.
    stray = db.execute(
        "SELECT count(*) FROM vote_topic_batch_members m JOIN saeima_votes v ON v.id = m.vote_id"
        " JOIN claims c ON c.source_url = v.url AND c.claim_type = 'saeima_vote'"
        " WHERE m.batch_id = ? AND c.topic IS NOT v.topic AND c.id NOT IN (SELECT row_id"
        "   FROM vote_topic_snapshot WHERE batch_id = m.batch_id AND table_name = 'claims')",
        (batch_id,)).fetchone()[0]
    if stray:
        raise RuntimeError("pēc rollback partijas balsojumu ierakstu (radušos pēc piemērošanas)"
                           f" skaits, kas nesakrīt ar balsojuma tēmu: {stray} — STOP, pārbaudi ar roku")
    out["parity_mismatch"] = _batch_parity(db, batch_id)
    return out


def abandon_batch(db, batch_id) -> None:
    """Pamet iesaldētu, nepiemērotu partiju (piem., neizdevās uzrakstīt rollback failu).

    Tikai no `snapshotted` — piemērotu partiju atgriež ar `rollback_batch`, nekad
    nepamet. Pamesta partija vairs neskaitās pārklājumā; snapshot rindas paliek.
    """
    with _write_tx(db):
        status, _ = _batch_status(db, batch_id)
        if status != "snapshotted":
            raise RuntimeError(f"partija {batch_id} ir {status}; pamest var tikai 'snapshotted'")
        db.execute("UPDATE vote_topic_batches SET status='abandoned' WHERE batch_id=?",
                   (batch_id,))


# --- Likumu tēmas seko lēmumiem (plāns 2026-10-21, 10. uzd.) ------------------
#
# Divas fāzes kā partijām (eskalācija 8): `sync_bill_topics` iesaldē maināmās
# `saeima_bills` rindas (`bill_topic_snapshot`) un uzraksta PAŠPIETIEKAMU rollback
# failu ar burtiskām vecajām vērtībām — tēmas vēl nemainās; `apply_bill_sync`
# maina tikai pēc tam, kad fails ir komitēts. Lēmums = `current_decision`
# (bez `rejected`); `pending` lēmumus izlaiž tāpat kā `freeze_batch`.

def _sql_lit(v) -> str:
    return "NULL" if v is None else "'" + str(v).replace("'", "''") + "'"


def _sync_status(db, sync_id) -> tuple[str, str | None]:
    row = db.execute("SELECT status, rollback_file FROM bill_topic_syncs WHERE sync_id=?",
                     (sync_id,)).fetchone()
    if row is None:
        raise ValueError(f"likumu sinhronizācija {sync_id!r} neeksistē")
    return row[0], row[1]


def sync_bill_topics(db, sync_id, *, keys=None, rollback_dir=None) -> dict:
    """1. fāze: snapshot + rollback fails `rollback_bill_topics_<sync_id>.sql`.

    `keys` = tikai šo dokumentu likumi (9. uzd. 6. solis: partijas atslēgas);
    `None` = visi. Atgriež saucējus: `bills` (aplūkoti), `changed`, `unchanged`,
    `skipped_pending`, `no_decision`. Ja `changed == 0`, nekas netiek ierakstīts.
    """
    wanted = None if keys is None else {k for k in keys if k}
    path = Path(rollback_dir or REPO_ROOT / "data") / f"rollback_bill_topics_{sync_id}.sql"
    out = {"sync_id": sync_id, "bills": 0, "changed": 0, "unchanged": 0,
           "skipped_pending": 0, "no_decision": 0, "rollback_file": None}
    with _write_tx(db):
        if db.execute("SELECT 1 FROM bill_topic_syncs WHERE sync_id=?", (sync_id,)).fetchone():
            raise ValueError(f"likumu sinhronizācija {sync_id!r} jau ir")
        rows = []
        for bid, nr, title, topic in db.execute(
                "SELECT id, document_nr, title, topic FROM saeima_bills ORDER BY id").fetchall():
            key, _ = document_key(nr, title or "")
            if wanted is not None and key not in wanted:
                continue
            out["bills"] += 1
            dec = current_decision(db, key) if key else None
            if dec is None:
                out["no_decision"] += 1
            elif dec["review_status"] == "pending":
                out["skipped_pending"] += 1
            elif topic == dec["topic"]:
                out["unchanged"] += 1
            else:
                rows.append((sync_id, bid, nr, topic, dec["topic"]))
        out["changed"] = len(rows)
        if not rows:
            return out
        db.execute("INSERT INTO bill_topic_syncs (sync_id, status, rollback_file)"
                   " VALUES (?, 'snapshotted', ?)", (sync_id, _repo_relative(path)))
        db.executemany("INSERT INTO bill_topic_snapshot (sync_id, bill_id, document_nr,"
                       " old_topic, new_topic) VALUES (?,?,?,?,?)", rows)
        s = _sql_lit(sync_id)
        applied = f"(SELECT status FROM bill_topic_syncs WHERE sync_id={s}) = 'applied'"
        lines = [
            f"-- Rollback: likumu tēmu sinhronizācija {sync_id} ({len(rows)} rindas)",
            f"-- Forward: scripts/vote_topics.py bills-apply {sync_id}"
            " (saeima_bills.topic ← saeima_document_topics)",
            "-- Pašpietiekams: vecās vērtības ierakstītas burtiski. Rinda mainās tikai, ja tās",
            "-- tēma joprojām ir sinhronizācijas jaunā un statuss ir 'applied'; drošs atkārtot.",
            "BEGIN;",
        ]
        lines += [f"UPDATE saeima_bills SET topic = {_sql_lit(old)} WHERE id = {bid}"
                  f" AND topic IS {_sql_lit(new)} AND {applied};  -- {nr}"
                  for _, bid, nr, old, new in rows]
        lines += [f"UPDATE bill_topic_syncs SET status='rolled_back' WHERE sync_id={s}"
                  " AND status='applied';", "COMMIT;", ""]
        path.parent.mkdir(parents=True, exist_ok=True)
        # Fails transakcijas iekšpusē: ja rakstīšana krīt, DB nekas nepaliek.
        with open(path, "x", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
    out["rollback_file"] = _repo_relative(path)
    return out


def apply_bill_sync(db, sync_id, *, require_tracked=True) -> dict:
    """2. fāze: piemēro vienā transakcijā; atsaka bez komitēta rollback faila vai pie drift."""
    status, rb = _sync_status(db, sync_id)
    if status != "snapshotted":
        raise RuntimeError(f"likumu sinhronizācija {sync_id} ir {status}, nevar piemērot")
    if require_tracked and (not rb or not _is_tracked(rb)):
        raise RuntimeError(f"rollback {rb} nav komitēts — eskalācija 8")
    with _write_tx(db):
        snap = db.execute("SELECT bill_id, document_nr, new_topic FROM bill_topic_snapshot"
                          " WHERE sync_id=?", (sync_id,)).fetchall()
        moved = [nr for _, nr, new in snap
                 if (current_decision(db, document_key(nr, "")[0]) or {"topic": None})["topic"] != new]
        if moved:
            raise RuntimeError(f"drift: {len(moved)} lēmumi mainījušies kopš sinhronizācijas"
                               f" ({', '.join(moved[:5])}) — sinhronizē no jauna")
        cur = db.execute(
            "UPDATE saeima_bills SET topic = s.new_topic FROM bill_topic_snapshot s"
            " WHERE s.sync_id = ? AND s.bill_id = saeima_bills.id"
            " AND saeima_bills.topic IS s.old_topic", (sync_id,))
        if cur.rowcount != len(snap):
            raise RuntimeError(f"drift: saeima_bills — {len(snap) - cur.rowcount} no {len(snap)}"
                               " rindām kopš sinhronizācijas mainītas vai dzēstas")
        db.execute(f"UPDATE bill_topic_syncs SET status='applied', applied_at={_NOW_MS}"
                   " WHERE sync_id=?", (sync_id,))
    return {"sync_id": sync_id, "updated": cur.rowcount}


def rollback_bill_sync(db, sync_id) -> dict:
    """Izpilda rollback failu un pārbauda, ka katrai rindai atjaunota vecā tēma."""
    status, rb = _sync_status(db, sync_id)
    if status != "applied":
        raise RuntimeError(f"likumu sinhronizācija {sync_id} ir {status}; atgriezt var tikai 'applied'")
    if not rb or not _resolve(rb).exists():
        raise RuntimeError(f"rollback fails {rb} nav atrodams")
    if db.in_transaction:
        raise RuntimeError("savienojumā ir nepabeigta transakcija — vispirms commit() vai rollback()")
    try:
        db.executescript(_resolve(rb).read_text(encoding="utf-8"))
    except BaseException:
        if db.in_transaction:
            db.execute("ROLLBACK")
        raise
    bad = db.execute("SELECT count(*) FROM bill_topic_snapshot s LEFT JOIN saeima_bills b"
                     " ON b.id = s.bill_id WHERE s.sync_id = ? AND b.topic IS NOT s.old_topic",
                     (sync_id,)).fetchone()[0]
    if bad or _sync_status(db, sync_id)[0] != "rolled_back":
        raise RuntimeError(f"pēc rollback {bad} likumu rindām nav vecās tēmas — pārbaudi ar roku"
                           " (vēlāka sinhronizācija vai roku labojums?)")
    return {"sync_id": sync_id, "restored": db.execute(
        "SELECT count(*) FROM bill_topic_snapshot WHERE sync_id=?", (sync_id,)).fetchone()[0]}


# --- Partiju plāns (plāns 2026-10-21, 9. uzd.) ---------------------------------

PLAN_FIRST_TOPICS = ("Valsts pārvalde", "Vide")

# Operatora noklusējums 2026-10-22 — atvērtais lēmums `backlog/saeima.md`
# § «Saeimas balsojumu tēmas …», punkts «Operatora lēmums vajadzīgs pirms 9. uzd.»:
# ikgadējo valsts budžeta likumu (un vidēja termiņa budžeta ietvara likumu) ķēdes
# NEiekļauj nevienā partijā, jo 92 % to balsojumu (342/370) pieder citai tēmai nekā
# dokuments. Tās patur pašreizējās balsojumu tēmas, līdz operators izlemj. Likums
# (`/Lp`), kura motīvs SĀKAS ar nosaukumu; citāts pēdiņās (apropriāciju pārdales
# `/Lm` lēmumi) neskaitās. 2026-10-22: 152/Lp14, 430/Lp14, 757/Lp14, 1130/Lp14.
_BUDGET_LAW_RE = re.compile(
    r"^\s*Par (?:valsts budžetu \d{4}\.\s*gadam|vidēja termiņa budžeta ietvaru)\b")


def is_budget_law(key: str | None, motif: str) -> bool:
    return bool(key) and "/Lp" in key and bool(_BUDGET_LAW_RE.match(motif or ""))


def current_vote_topic(items: list[tuple[int, str | None]]) -> str | None:
    """Dokumenta pašreizējā tēma: biežākā balsojumu tēma; vienādos — mazākā balsojuma id.

    `items` = [(vote_id, topic)] jebkurā secībā. Tas pats noteikums kā `pred_stored.csv`.
    """
    cnt: dict = {}
    for vid, t in sorted(items, key=lambda it: it[0]):
        n, first = cnt.get(t, (0, vid))
        cnt[t] = (n + 1, first)
    return min(cnt, key=lambda t: (-cnt[t][0], cnt[t][1])) if cnt else None


def plan_batches(db, size: int) -> tuple[list[tuple[str, str]], dict]:
    """Deterministisks partiju plāns: [(batch_id, document_key)] + saucēji.

    Secība pēc ietekmes: dokumenti ar pašreizējo «Valsts pārvalde», tad «Vide», tad
    pārējie; katrā grupā pēc balsojumu skaita dilstoši, vienādos — pēc atslēgas.
    Pašreizējā tēma = biežākā `saeima_votes.topic` (vienādos — mazākā balsojuma id;
    tas pats noteikums kā `pred_stored.csv`). Tikai lasa.
    """
    if size < 1:
        raise ValueError("size jābūt ≥ 1")
    votes: dict[str, list[tuple[int, str | None]]] = {}
    budget: set[str] = set()
    multi: set[str] = set()
    unresolved = 0
    for vid, nr, motif, topic in db.execute(
            "SELECT id, document_nr, motif, topic FROM saeima_votes ORDER BY id"):
        key, reason = document_key(nr, motif or "")
        if key is None:
            unresolved += 1
            continue
        votes.setdefault(key, []).append((vid, topic))
        if reason == "multi":
            multi.add(key)
        if is_budget_law(key, motif):
            budget.add(key)

    def rank(k):
        t = current_vote_topic(votes[k])
        group = PLAN_FIRST_TOPICS.index(t) if t in PLAN_FIRST_TOPICS else len(PLAN_FIRST_TOPICS)
        return group, -len(votes[k]), k

    docs = sorted((k for k in votes if k not in budget), key=rank)
    rows = [(f"b{i // size + 1:02d}", k) for i, k in enumerate(docs)]
    info = {"documents": len(votes), "planned": len(docs),
            "excluded_budget": {k: len(votes[k]) for k in sorted(budget)},
            "multi_keys": len(multi & set(docs)), "unresolved_votes": unresolved,
            "votes_per_batch": {}}
    for bid, k in rows:
        info["votes_per_batch"][bid] = info["votes_per_batch"].get(bid, 0) + len(votes[k])
    return rows, info
