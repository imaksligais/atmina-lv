"""Saeimas likumprojektu klasifikācija + DB ops.

F4.3 izvilkts no src/saeima.py monolīta. Satur visas TIKAI-no-DB-atkarīgās
helper funkcijas: bill type/stage validāciju, motif regexes, base law slug
resolution, kā arī upsert_bill / append_bill_stage atomic writes.

Tāpat tur SAEIMA_BASE_URL + _resolve_vote_url + _parse_vote_datetime — šie ir
share-otie URL/datuma helperi, ko `votes.py` un `claims.py` abi izsauc;
turot tos te (bez saeima/ iekšējiem importiem) tiek pārtraukts cikls
votes ↔ claims.

CLAUDE.md punkts 12: `append_bill_stage()` ir VIENĪGAIS rakstītājs uz
`saeima_votes.bill_id` un `saeima_bills.current_stage`. Šī fakta loģika
glabājas `_canonicalize_stage_name` validācijā + tranzakcijas atomiskumā
(stage row + bill UPDATE = vienā commit).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.db import get_db, now_lv

SAEIMA_BASE_URL = "https://titania.saeima.lv/LIVS14/SaeimaLIVS2_DK.nsf"

# ---------------------------------------------------------------------------
# Bill type & stage validation (Phase 1A)
# ---------------------------------------------------------------------------

_VALID_BILL_TYPES: frozenset[str] = frozenset({"Lp14", "Lm14", "P14"})

_VALID_STAGE_NAMES: frozenset[str] = frozenset({
    "iesniegts",
    "1.lasījums", "2.lasījums", "2.lasījums priekšlikums",
    "3.lasījums", "3.lasījums priekšlikums",
    "atgriezts komisijā", "atsaukts",
    "tiesneša_amats", "procesuāls", "Lm14 cits",
    "paziņojuma_balsojums",
    "nezināms",
})


def _canonicalize_stage_name(name: str) -> str:
    """Strip whitespace and verify against _VALID_STAGE_NAMES.

    Raises ValueError if not in the closed vocabulary set.
    See spec § 3.3 stage vocabulary table.
    """
    cleaned = (name or "").strip()
    if cleaned not in _VALID_STAGE_NAMES:
        raise ValueError(f"Unknown stage_name: {name!r}")
    return cleaned


# ---------------------------------------------------------------------------
# Motif classification helpers (Phase 1A)
# ---------------------------------------------------------------------------

_DOCUMENT_NR_RE = re.compile(r"(?<!\w)\(?(\d+\s*/\s*(?:Lp14|Lm14|P14))\)?")
_READING_RE = re.compile(r"\b(\d)\.\s?lasījum", re.IGNORECASE)
_PRIEKSLIK_RE = re.compile(r"priekšlikum", re.IGNORECASE)
_TIESNESHA_RE = re.compile(
    r"iecelšanu par.*tiesnesi|apstiprināšanu par.*tiesnesi"
    r"|atbrīvošanu no tiesneša|atbrīvošanu no.*tiesneša"
    r"|tiesneša.*atbrīvošan",
    re.IGNORECASE,
)
_PROCESUALS_RE = re.compile(
    r"termiņa pagarināšanu|komisijas noteikšanu|atsaukšanu no.*komisijas",
    re.IGNORECASE,
)
_NODOSANA_KOMISIJAI_RE = re.compile(
    r"nodošana\s+komisij",
    re.IGNORECASE,
)


def resolve_bill_from_motif(motif: str) -> Optional[str]:
    """Extract document_nr (e.g. '1315/Lp14') from a motif string.

    Matches both parenthesized '(NNN/Xx14)' and bare 'NNN/Xx14' forms.
    Normalizes whitespace around '/' so '127 / P14' → '127/P14'.
    Returns None if no matching pattern is found.
    Spec § 4.3 helper signature.
    """
    if not motif:
        return None
    m = _DOCUMENT_NR_RE.search(motif)
    if not m:
        return None
    # Normalize: strip whitespace around '/' introduced by \s* tolerance
    return re.sub(r"\s*/\s*", "/", m.group(1))


def _reading_from_motif(motif: str) -> str:
    """Canonical stage_name no motif (case-insensitive); pirmais piemērojamais
    noteikums uzvar (sk. spec § 3.3 priority list). Rules 4–5 substring-match
    motif (kas Saeimas agenda formātā satur document_nr).

    Returns one of _VALID_STAGE_NAMES. Falls back to 'nezināms'.
    Note: 'atgriezts komisijā' un 'atsaukts' netiek automātiski klasificēti
    (agent prompt-driven only).
    """
    if not motif:
        return "nezināms"

    # Rule 1: reading number wins (most specific lexical anchor)
    m = _READING_RE.search(motif)
    if m:
        n = m.group(1)
        if _PRIEKSLIK_RE.search(motif):
            return f"{n}.lasījums priekšlikums"
        return f"{n}.lasījums"

    # Rule 2: judicial appointment / removal
    if _TIESNESHA_RE.search(motif):
        return "tiesneša_amats"

    # Rule 3: procedural (termiņi, komisijas)
    if _PROCESUALS_RE.search(motif):
        return "procesuāls"

    # Rule 4: bill referral to committee = first agenda appearance
    if _NODOSANA_KOMISIJAI_RE.search(motif):
        return "iesniegts"

    # Rule 5-6: document_nr suffix-based fallback
    if "/P14" in motif:
        return "paziņojuma_balsojums"
    if "/Lm14" in motif:
        return "Lm14 cits"

    # Rule 7: default
    return "nezināms"


def _resolve_base_law_slug(
    motif: str, laws_index: dict[str, str]
) -> Optional[str]:
    """Match motif text against `wiki/laws/likumi.md` slug → title index.

    Priority (case-insensitive):
    1. Exact title substring match → return slug.
    2. Title with trailing 'likums' inflection stripped, substring match → return slug.
    3. None.

    Spec § 6.2 contract.
    """
    if not motif or not laws_index:
        return None

    motif_lower = motif.lower()
    for slug, title in laws_index.items():
        if title.lower() in motif_lower:
            return slug
    # Fallback: try matching just the law name without trailing 'likums' inflection
    for slug, title in laws_index.items():
        base = re.sub(r"\s+likum[saiu]?\s*$", "", title, flags=re.IGNORECASE)
        if base and base.lower() in motif_lower:
            return slug
    return None


LAW_TITLE_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)


def load_laws_index(wiki_dir: Path) -> dict[str, str]:
    """Build slug → title dict from wiki/laws/*.md files (skip likumi.md indekss).

    Used by:
    - scripts/backfill_base_law_slug.py (retro-backfill)
    - upsert_bill() auto-resolution
    - src/generate.py:_load_law_titles_cache (Phase 1B-ii Task 5)
    """
    laws_dir = wiki_dir / "laws"
    index: dict[str, str] = {}
    if not laws_dir.exists():
        return index
    for md_file in sorted(laws_dir.glob("*.md")):
        if md_file.name == "likumi.md":
            continue
        slug = md_file.stem
        try:
            content = md_file.read_text(encoding="utf-8")
            m = LAW_TITLE_RE.search(content)
            index[slug] = m.group(1) if m else slug.replace("-", " ").title()
        except OSError:
            continue
    return index


def _resolve_vote_url(vote_url: Optional[str]) -> Optional[str]:
    """Return an absolute Saeima URL from either a relative path or an absolute URL.

    Accepting both shapes keeps callers flexible: scrapers that already
    captured the absolute URL can pass it straight through, while older
    code paths that stored only the `./0/HEX?OpenDocument` fragment still
    get resolved. Passing an absolute URL through `.lstrip('./')` used to
    silently double-prefix the base URL, producing broken links in stored
    documents and claims.
    """
    if not vote_url:
        return None
    if vote_url.startswith(("http://", "https://")):
        return vote_url
    return f"{SAEIMA_BASE_URL}/{vote_url.lstrip('./')}"


def _parse_vote_datetime(date_str: Optional[str], time_str: Optional[str]) -> Optional[str]:
    """Parse date (YYYY-MM-DD or dd.mm.yyyy) and hh:mm:ss into ISO datetime string."""
    if not date_str:
        return None
    try:
        if "." in date_str:
            d = datetime.strptime(date_str, "%d.%m.%Y")
        else:
            d = datetime.strptime(date_str, "%Y-%m-%d")
        if time_str:
            t = datetime.strptime(time_str, "%H:%M:%S")
            d = d.replace(hour=t.hour, minute=t.minute, second=t.second)
        return d.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Bill upsert & stage append (Phase 1A)
# ---------------------------------------------------------------------------

def upsert_bill(
    db_path: str,
    document_nr: str,
    title: str,
    bill_type: str,
    institutional_submitter: Optional[str] = None,
    topic: Optional[str] = None,
    base_law_slug: Optional[str] = None,
    summary: Optional[str] = None,
    wiki_dir: Optional[Path] = None,
) -> int:
    """Insert or update a saeima_bills row by document_nr (idempotent).

    On re-upsert: title, bill_type, topic, institutional_submitter,
    base_law_slug, summary are overwritten with new non-None values
    (COALESCE pattern keeps existing values when caller passes None);
    first_seen_at is preserved.

    If base_law_slug is None and title is non-empty, auto-resolves by matching
    against wiki/laws/ index (wiki_dir defaults to repo root + "/wiki").
    On UPDATE the SQL COALESCE ensures an already-populated base_law_slug is
    never overwritten.

    Returns the bill_id. Raises ValueError if bill_type not in
    _VALID_BILL_TYPES. Spec § 4.3 + § 5.2 backfill use.
    """
    if bill_type not in _VALID_BILL_TYPES:
        raise ValueError(
            f"bill_type must be one of {sorted(_VALID_BILL_TYPES)}, got {bill_type!r}"
        )

    # Auto-resolve base_law_slug when not explicitly provided
    if base_law_slug is None and title:
        _wiki_dir = wiki_dir if wiki_dir is not None else Path(__file__).resolve().parent.parent.parent / "wiki"
        laws_index = load_laws_index(_wiki_dir)
        base_law_slug = _resolve_base_law_slug(title, laws_index)

    db = get_db(db_path)
    now = now_lv()
    existing = db.execute(
        "SELECT id FROM saeima_bills WHERE document_nr=?", (document_nr,)
    ).fetchone()

    if existing:
        bid = existing["id"]
        db.execute(
            """UPDATE saeima_bills SET
                title = ?,
                bill_type = ?,
                topic = COALESCE(?, topic),
                institutional_submitter = COALESCE(?, institutional_submitter),
                base_law_slug = COALESCE(base_law_slug, ?),
                summary = COALESCE(?, summary),
                last_updated_at = ?
              WHERE id = ?""",
            (title, bill_type, topic, institutional_submitter, base_law_slug,
             summary, now, bid),
        )
    else:
        cur = db.execute(
            """INSERT INTO saeima_bills (
                document_nr, bill_type, title, topic, institutional_submitter,
                base_law_slug, summary, current_status, first_seen_at,
                last_updated_at
              ) VALUES (?, ?, ?, ?, ?, ?, ?, 'procesā', ?, ?)""",
            (document_nr, bill_type, title, topic, institutional_submitter,
             base_law_slug, summary, now, now),
        )
        bid = cur.lastrowid

    db.commit()
    db.close()
    return bid


def append_bill_stage(
    db_path: str,
    bill_id: int,
    stage_name: str,
    stage_result: Optional[str],
    stage_date: str,
    vote_id: Optional[int] = None,
    session_id: Optional[int] = None,
    amendment_nr: Optional[str] = None,
) -> int:
    """Append a stage row + atomically update parent bill's denorm fields.

    stage_name validated via _canonicalize_stage_name (raises ValueError
    if invalid). All-or-nothing transaction: stage row + bill update
    commit together, or both rollback.

    Updates saeima_bills.current_stage to the latest stage by stage_date
    (recomputed inside the transaction so callers can append out of order).

    current_status mapping:
      - 3.lasījums + 'pieņemts' → 'pieņemts' (final)
      - any 'noraidīts' result on the latest stage → 'noraidīts'
      - else → 'procesā'

    stage_kind defaults to 'vote' at DB level (Phase 1A only writes
    vote-kind stages; debate/commission reserved for Phase 3).

    Returns the new stage row id. Spec § 4.3.
    """
    canonical = _canonicalize_stage_name(stage_name)  # raises before opening txn

    db = get_db(db_path)
    try:
        cur = db.execute(
            """INSERT INTO saeima_bill_stages (
                bill_id, stage_name, stage_result, stage_date,
                vote_id, session_id, amendment_nr, stage_kind
              ) VALUES (?, ?, ?, ?, ?, ?, ?, 'vote')""",
            (bill_id, canonical, stage_result, stage_date, vote_id,
             session_id, amendment_nr),
        )
        sid = cur.lastrowid

        # Recompute current_stage / current_status from latest stage by date
        latest = db.execute(
            """SELECT stage_name, stage_result FROM saeima_bill_stages
               WHERE bill_id=? AND stage_kind='vote'
               ORDER BY stage_date DESC, id DESC LIMIT 1""",
            (bill_id,),
        ).fetchone()
        new_stage = latest["stage_name"]
        new_result_norm = (latest["stage_result"] or "").strip().lower()
        if new_result_norm == "pieņemts" and new_stage.startswith("3."):
            new_status = "pieņemts"
        elif new_result_norm == "noraidīts":
            new_status = "noraidīts"
        else:
            new_status = "procesā"

        db.execute(
            "UPDATE saeima_bills SET current_stage=?, current_status=?, "
            "last_updated_at=? WHERE id=?",
            (new_stage, new_status, now_lv(), bill_id),
        )

        # CLAUDE.md invariant #12: this function is the SOLE writer to
        # saeima_votes.bill_id. For vote-kind stages the vote must be bound to
        # the parent bill inside the same transaction; doing it later (as
        # @saeima-tracker did pre-2026-05-16) leaves a window where stages
        # exist but the vote row is unbound, and any aborted run leaves
        # permanently inconsistent denorm.
        if vote_id is not None:
            db.execute(
                "UPDATE saeima_votes SET bill_id=? WHERE id=?",
                (bill_id, vote_id),
            )

        db.commit()
        return sid
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Agenda bill dataclass (parsed from snapshot, persisted via upsert_bill)
# ---------------------------------------------------------------------------

@dataclass
class AgendaBill:
    """Single bill extracted from an agenda snapshot.

    Spec § 4.3.
    """
    document_nr: str                                # "1315/Lp14", "127/P14"
    bill_type: str                                  # "Lp14" | "Lm14" | "P14"
    title: str
    individual_submitters: list[str] = field(default_factory=list)
    institutional_submitter: Optional[str] = None
    reading_hint: Optional[str] = None
    vote_uuid: Optional[str] = None
