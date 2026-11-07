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
from src.saeima.convocation import BILL_SUFFIX, base_url, is_valid_bill_type

SAEIMA_BASE_URL = base_url()

# ---------------------------------------------------------------------------
# Bill type & stage validation (Phase 1A)
# ---------------------------------------------------------------------------

_VALID_STAGE_NAMES: frozenset[str] = frozenset({
    "iesniegts",
    "1.lasījums", "2.lasījums", "2.lasījums priekšlikums",
    "3.lasījums", "3.lasījums priekšlikums",
    "otrreizēja caurlūkošana", "otrreizēja caurlūkošana priekšlikums",
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

_DOCUMENT_NR_RE = re.compile(rf"(?<!\w)\(?(\d+\s*/\s*{BILL_SUFFIX})\)?")
_PAZINOJUMS_NR_RE = re.compile(r"/P\d{2}(?!\d)")
_LEMUMS_NR_RE = re.compile(r"/Lm\d{2}(?!\d)")
_READING_RE = re.compile(r"\b(\d)\.\s?lasījum", re.IGNORECASE)
_PRIEKSLIK_RE = re.compile(r"priekšlikum", re.IGNORECASE)
# Valsts prezidenta atdots likums (Satversmes 71. p.) — atsevišķs posms pēc
# 3. lasījuma; motīvā nav lasījuma numura (56/Lp14, 1019/Lp14; 2026-10-20).
_OTRREIZ_RE = re.compile(r"otrreizēj\w* caurlūkošan", re.IGNORECASE)
_TIESNESHA_RE = re.compile(
    r"iecelšanu par.*tiesnesi|apstiprināšanu par.*tiesnesi"
    r"|atbrīvošanu no tiesneša|atbrīvošanu no.*tiesneša"
    r"|tiesneša.*atbrīvošan",
    re.IGNORECASE,
)
_PROCESUALS_RE = re.compile(
    r"termiņa pagarināšanu|komisijas noteikšanu|atsaukšanu no.*komisijas"
    # Lēmuma projekta balsojums, kas SĀKAS ar iekļaušanu darba kārtībā
    # (1108/Lm14, 2026-10-09). Tikai teikuma sākums: «… nodošana komisijām
    # iekļaušanu darba kārtībā» paliek `iesniegts`; «Par lēmuma projekta …
    # iekļaušanu …» arī ir procedūra (pieņemta iekļaušana ≠ pieņemts lēmums).
    r"|^Par iekļaušanu\s+[^.]*?darba kārtīb"
    r"|^Par lēmuma projekta\b.*iekļaušanu\s+[^.]*?darba kārtīb",
    re.IGNORECASE,
)
# Procedūra, kas NOSAUC lasījumu, bet nav pats lasījums — jāpārbauda PIRMS
# 1. noteikuma: «Par priekšlikumu iesniegšanas termiņu … 1.lasījums» citādi
# kļūst par '1.lasījums priekšlikums' (nav vārdnīcā → posms 'nezināms';
# balsojumi 8293/8294, 2026-09-24). Tāpat pārbalsošana un sēdes darba
# kārtības pārkārtošana (8258; 8202/8208). Iekļaušana darba kārtībā NAV šeit —
# tā vēsturiski paliek lasījuma posms.
_PROCESUALS_FIRST_RE = re.compile(
    r"priekšlikumu iesniegšanas termiņ|pārbalsošan"
    r"|izskatīšanu kā pirmo|grozīt sēdes darba kārtību",
    re.IGNORECASE,
)
_NODOSANA_KOMISIJAI_RE = re.compile(
    # «nodošana komisijai» un lēmuma projekta balsojums, kas SĀKAS ar
    # «Par nodošanu Izglītības, kultūras un zinātnes komisijai» (1104/Lm14).
    r"nodošana\s+komisij|^Par nodošanu\s+[^.()]*?komisij",
    re.IGNORECASE,
)


def resolve_bill_from_motif(motif: str) -> Optional[str]:
    """Extract document_nr (e.g. '1315/Lp14', '1/Lp15') from a motif string.

    Matches both parenthesized '(NNN/XxNN)' and bare 'NNN/XxNN' forms
    (jebkurš sasaukums).
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
    noteikums uzvar (sk. spec § 3.3 priority list). Rules 5–6 meklē ar regex
    dokumenta numuru motif tekstā (jebkurš sasaukums).

    Returns one of _VALID_STAGE_NAMES. Falls back to 'nezināms'.
    Note: 'atgriezts komisijā' un 'atsaukts' netiek automātiski klasificēti
    (agent prompt-driven only).
    """
    if not motif:
        return "nezināms"

    # Rule 0: procedural votes that merely name a reading
    if _PROCESUALS_FIRST_RE.search(motif):
        return "procesuāls"

    # Rule 1: reading number wins (most specific lexical anchor)
    m = _READING_RE.search(motif)
    if m:
        n = m.group(1)
        # Priekšlikumus balso tikai 2. un 3. lasījumā; '1.lasījums
        # priekšlikums' vārdnīcā nav, un append_bill_stage() to noraidītu.
        if n in ("2", "3") and _PRIEKSLIK_RE.search(motif):
            return f"{n}.lasījums priekšlikums"
        return f"{n}.lasījums"

    # Rule 1b: otrreizēja caurlūkošana (galīgais balsojums vai tā priekšlikums)
    if _OTRREIZ_RE.search(motif):
        if _PRIEKSLIK_RE.search(motif):
            return "otrreizēja caurlūkošana priekšlikums"
        return "otrreizēja caurlūkošana"

    # Rule 2: judicial appointment / removal
    if _TIESNESHA_RE.search(motif):
        return "tiesneša_amats"

    # Rule 3: procedural (termiņi, komisijas)
    if _PROCESUALS_RE.search(motif):
        return "procesuāls"

    # Rule 4: bill referral to committee = first agenda appearance
    if _NODOSANA_KOMISIJAI_RE.search(motif):
        return "iesniegts"

    # Rule 5-6: document_nr suffix-based fallback (jebkurš sasaukums).
    # "Lm14 cits" ir vēsturiska vārdnīcas etiķete visiem sasaukumiem —
    # glabāta tabulā `saeima_bill_stages`; pārdēvēšana = datu migrācija.
    if _PAZINOJUMS_NR_RE.search(motif):
        return "paziņojuma_balsojums"
    if _LEMUMS_NR_RE.search(motif):
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
    - src/render/bills.py:_get_law_titles (Phase 1B-ii Task 5)
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

    Returns the bill_id. Raises ValueError if bill_type is not Lp|Lm|P plus a
    two-digit convocation (jebkurš sasaukums, sk. `is_valid_bill_type`).
    Spec § 4.3 + § 5.2 backfill use.
    """
    if not is_valid_bill_type(bill_type):
        raise ValueError(
            f"bill_type must be Lp|Lm|P + two-digit convocation (e.g. 'Lp15'), got {bill_type!r}"
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


# Likumprojekta kopsavilkums saka, par ko tas ir un ko maina — ne balsojuma
# iznākumu (tas ir saeima_bill_stages / saeima_votes.result). Paterni ņemti no
# 77 esošajiem defektīvajiem summary (2026-10-19): lasījuma marķieris, «pieņemts
# par likumu», vienbalsīgi/vienprātīgi, balsu skaits, «noraidīts/-a».
_BILL_SUMMARY_OUTCOME = re.compile(
    r"(\d\.|pirm\w*|otr\w*|treš\w*|galīg\w*)\s*(\(galīgajā\)\s*)?lasījum"
    r"|pieņemt[si]?\s+par\s+likumu"
    r"|vienbalsīg|vienprātīg"
    r"|(?<![/\d])\b\d{1,3}\s+(par|balsīm)\b"
    r"|\(\s*(par=)?\d{1,3}\s*[/:]\s*\d{1,3}\b|\(\d{1,3}\s*[–-]\s*\d{1,3}\)"
    r"|\b\d{1,3}:\d{1,3}:\d{1,3}\b"
    r"|\bnoraidīt[sa]\b",
    re.IGNORECASE,
)


def set_bill_summary(db_path: str, document_nr: str, summary: str) -> None:
    """Raksta TIKAI saeima_bills.summary — last_updated_at nemaina, jo
    likumprojektu saraksti kārtojas pēc tā (upsert_bill to pārbīdītu uz «šodien»).

    Atsaka (ValueError): tukšu, ar jaunu rindu, ar balsojuma/lasījuma iznākumu,
    nezināmu document_nr.
    """
    text = (summary or "").strip()
    if not text:
        raise ValueError("summary ir tukšs")
    if "\n" in text:
        raise ValueError("summary jābūt vienā rindā")
    m = _BILL_SUMMARY_OUTCOME.search(text)
    if m:
        raise ValueError(f"summary satur balsojuma iznākumu: {m.group(0)!r}")
    db = get_db(db_path)
    cur = db.execute(
        "UPDATE saeima_bills SET summary=? WHERE document_nr=?", (text, document_nr)
    )
    db.commit()
    db.close()
    if cur.rowcount != 1:
        raise ValueError(f"likumprojekts {document_nr!r} nav atrasts")


# Posmi, kur viens balsojums ir galīgs lēmums (nav lasījumu): tiesneša
# iecelšana/atbrīvošana un lēmuma projekts (`Lm14 cits` — vēsturiska etiķete
# visiem sasaukumiem). Procedūras balsojumi («Par nodošanu … komisijai»,
# «Par iekļaušanu … darba kārtībā») klasifikators izdala pirms tam (2026-10-09).
_SINGLE_VOTE_FINAL = ("tiesneša_amats", "Lm14 cits")
# Tie paši, bet TIKAI lēmumiem un pieprasījumiem/paziņojumiem (ne Lp): Lp
# `procesuāls` ir priekšlikumu termiņš u.tml. lasījumu gaitā, ne lēmums
# (2026-10-20). `nezināms` = motīvs bez numura (997/Lm14 «Uzticības izteikšana
# Ministru kabinetam»).
_SINGLE_VOTE_FINAL_NOT_LP = ("procesuāls", "paziņojuma_balsojums", "nezināms")
# `procesuāls` lēmums, kas tikai virza dokumentu, nav galīgs (1104/Lm14).
_PROCEDURAL_NOT_FINAL_RE = re.compile(
    r"darba kārtīb|iekļaušan|nodošan\w*\s+[^.()]*?komisij", re.IGNORECASE)
# Saeimas iznākuma vārdi, kas viena balsojuma lēmumam nozīmē «pieņemts».
# «Paziņojums» ir Saeimas PAŠAS iznākuma vārds pieņemtam lēmumam, ko publicē kā
# Saeimas paziņojumu (titania 1112/Lm14: «Rezultāts: Paziņojums», pievienots
# «Paziņojuma teksts»). `saeima_votes.result` to glabā burtiski (operatora
# lēmums 2026-08-18: etiķetes nepārvērst divu vērtību skalā), tāpēc tulkojums
# notiek tikai šeit.
_FINAL_RESULTS = ("pieņemts", "paziņojums")
# Lēmums bez balsojuma (`stage_kind='decision'`, avots titania): arī «Izskatīts»
# (988/Lm14 — paziņojums par deputāta pilnvaru atjaunošanu).
_FINAL_DECISION_RESULTS = _FINAL_RESULTS + ("izskatīts",)
_STAGE_KINDS = ("vote", "decision")


def derive_bill_denorm(db, bill_id: int) -> tuple[Optional[str], str]:
    """(current_stage, current_status) no likumprojekta posmiem.

    Vienīgais šī noteikuma avots — to lieto `append_bill_stage()` un
    `scripts/recompute_bill_status.py` (pārrēķins vecajām rindām).

    Lasa `stage_kind` 'vote' un 'decision' (Saeimas lēmums bez balsojuma,
    avots titania; 2026-10-20).

    Procedūras posms (`procesuāls` — termiņš, pārbalsošana, darba
    kārtība) lasījumu neaizstāj (operatora lēmums 2026-09-28): tas kļūst
    par current_stage tikai tad, ja cita posma vēl nav. Priekšlikuma
    balsojums («N.lasījums priekšlikums») tās pašas dienas lasījumu arī
    neaizstāj — vēlāk ielādēts priekšlikums dabū lielāku id (2026-10-09).
    Tajā pašā dienā augstāks lasījums aizstāj zemāku neatkarīgi no id
    (steidzams 1.+2. vienā dienā; 2026-10-19).

    Statuss:
    - Saeimas iznākums «Atsaukts…» (arī «Atsaukts: X atsauc parakstu») →
      `atsaukts` (2026-10-20);
    - «Likums» = pieņemts galīgajā lasījumā jebkurā lasījumā (steidzamam —
      2.; 2026-10-09); 3. lasījums + «Pieņemts» → `pieņemts`;
    - viena balsojuma lēmums bez lasījumiem (`_SINGLE_VOTE_FINAL`; ne-Lp arī
      `_SINGLE_VOTE_FINAL_NOT_LP`) ar «Pieņemts» vai «Paziņojums» → `pieņemts`.
      `procesuāls` — tikai ja balsojuma motīvs nav darba kārtība / iekļaušana /
      nodošana komisijai (deputāta atsaukšana no komisijas, karavīru termiņa
      pagarinājums ir galīgi; 2026-10-20);
    - lēmums bez balsojuma (ne-Lp) ar «Pieņemts»/«Paziņojums»/«Izskatīts» →
      `pieņemts`;
    - otrreizēja caurlūkošana + «Pieņemts» → `pieņemts` (2026-10-20);
    - «Noraidīts» → `noraidīts`, ja tas nav priekšlikums; citādi `procesā`.
    """
    latest = db.execute(
        """SELECT st.stage_name, st.stage_result, st.stage_kind, v.motif,
                  b.bill_type
           FROM saeima_bill_stages st
           JOIN saeima_bills b ON b.id = st.bill_id
           LEFT JOIN saeima_votes v ON v.id = st.vote_id
           WHERE st.bill_id=? AND st.stage_kind IN ('vote', 'decision')
           ORDER BY (st.stage_name = 'procesuāls') ASC,
                    st.stage_date DESC,
                    (st.stage_name LIKE '% priekšlikums') ASC,
                    CASE WHEN st.stage_name GLOB '[0-9].lasījums*'
                         THEN CAST(substr(st.stage_name, 1, 1) AS INTEGER)
                         ELSE 0 END DESC,
                    st.id DESC LIMIT 1""",
        (bill_id,),
    ).fetchone()
    if latest is None:
        return None, "procesā"
    stage = latest["stage_name"]
    result = (latest["stage_result"] or "").strip().lower()
    not_lp = not (latest["bill_type"] or "").startswith("Lp")
    if result.startswith("atsaukts"):
        return stage, "atsaukts"
    if result == "likums" or (result == "pieņemts" and (
            stage.startswith("3.") or stage == "otrreizēja caurlūkošana")):
        return stage, "pieņemts"
    if latest["stage_kind"] == "decision":
        if not_lp and result in _FINAL_DECISION_RESULTS:
            return stage, "pieņemts"
    elif result in _FINAL_RESULTS and (
            stage in _SINGLE_VOTE_FINAL
            or (not_lp and stage in _SINGLE_VOTE_FINAL_NOT_LP and not (
                stage == "procesuāls"
                and _PROCEDURAL_NOT_FINAL_RE.search(latest["motif"] or "")))):
        return stage, "pieņemts"
    # Noraidīts priekšlikums likumprojektu nenoraida (2026-10-20).
    if result == "noraidīts" and not stage.endswith(" priekšlikums"):
        return stage, "noraidīts"
    return stage, "procesā"


def append_bill_stage(
    db_path: str,
    bill_id: int,
    stage_name: str,
    stage_result: Optional[str],
    stage_date: str,
    vote_id: Optional[int] = None,
    session_id: Optional[int] = None,
    amendment_nr: Optional[str] = None,
    stage_kind: str = "vote",
    keep_vote_bill_id: bool = False,
    touch_updated_at: bool = True,
) -> int:
    """Append a stage row + atomically update parent bill's denorm fields.

    stage_name validated via _canonicalize_stage_name (raises ValueError
    if invalid). All-or-nothing transaction: stage row + bill update
    commit together, or both rollback.

    Updates saeima_bills.current_stage to the latest stage by stage_date
    (recomputed inside the transaction so callers can append out of order).

    current_status mapping:
      - 3.lasījums + 'pieņemts' → 'pieņemts' (final)
      - 'Likums' result in any reading → 'pieņemts' (steidzams: 2.)
      - viena balsojuma lēmums ar 'Pieņemts'/'Paziņojums' → 'pieņemts'
      - 'Atsaukts…' → 'atsaukts'; 'noraidīts' → 'noraidīts'; else → 'procesā'
      (pilns noteikums: `derive_bill_denorm()`).

    stage_kind: 'vote' (noklusējums — balsojuma posms) vai 'decision' —
    Saeimas lēmums BEZ balsojuma (avots titania posmu tabula, stage_result =
    titania vārds burtiski, piem. «Pieņemts», «Atsaukts», «Izskatīts»;
    2026-10-20). 'decision' posmam vote_id nav — ar vote_id tas tiek atteikts,
    jo tas melotu par balsojumu. Citi veidi (debate/commission) — Phase 3.

    keep_vote_bill_id=True — šaurs ceļš «viens balsojums, divi dokumenti»
    (operatora lēmums 2026-10-20): lēmuma projekts par likumprojektu (termiņa
    pagarinājums, steidzamības atcelšana; 1056/Lm14 ↔ 1352/Lp14) — Lp gūst
    procedūras posmu, Lm lēmumu. Balsojumam JĀBŪT jau piesaistītam CITAM
    likumprojektam, un tā motīvā JĀBŪT «(<šī likumprojekta numurs>)»; tad posms
    tiek pievienots, bet `saeima_votes.bill_id` NEmainās. Citādi ValueError.

    touch_updated_at=False — vēsturiska posma iepildīšana (backfill,
    2026-10-20): `last_updated_at` NEmainās, jo pēc tā kārto
    `likumprojekti.html`; sens posms nav jauna aktivitāte. Ielāde atstāj True.

    Returns the new stage row id. Spec § 4.3.
    """
    canonical = _canonicalize_stage_name(stage_name)  # raises before opening txn
    if stage_kind not in _STAGE_KINDS:
        raise ValueError(f"Unknown stage_kind: {stage_kind!r}")
    if stage_kind == "decision" and vote_id is not None:
        raise ValueError("stage_kind='decision' ir lēmums bez balsojuma — vote_id nedrīkst būt")
    if keep_vote_bill_id and (vote_id is None or stage_kind != "vote"):
        raise ValueError("keep_vote_bill_id prasa balsojuma posmu ar vote_id")

    db = get_db(db_path)
    try:
        if keep_vote_bill_id:
            v = db.execute(
                "SELECT v.bill_id, v.motif, b.document_nr FROM saeima_votes v, "
                "saeima_bills b WHERE v.id=? AND b.id=?", (vote_id, bill_id),
            ).fetchone()
            if v is None or v["bill_id"] is None or v["bill_id"] == bill_id:
                raise ValueError("keep_vote_bill_id: balsojums nav piesaistīts citam likumprojektam")
            if f"({v['document_nr']})" not in (v["motif"] or ""):
                raise ValueError(
                    f"keep_vote_bill_id: balsojuma motīvā nav ({v['document_nr']})")
        # LAIKA ZONA — divas zonas trīsdesmit rindu attālumā, apzināti pierakstīts.
        # Šis INSERT NEuzskaita `created_at`, tāpēc posma rinda dabū SQLite
        # DEFAULT CURRENT_TIMESTAMP = **UTC**; UPDATE zemāk raksta
        # `saeima_bills.last_updated_at = now_lv()` = **LV**. Tātad viena
        # izsaukuma divi ieraksti stāv divās zonās. Sekas lasītājam: posmu
        # DATE-filtram vajag DATE(created_at, 'localtime'), likumprojekta
        # last_updated_at filtram — NEvajag. Nelabo to, rakstot now_lv() UTC
        # kolonnā (CLAUDE.md § Schema invariants: tas ir defekts, ne remonts).
        cur = db.execute(
            """INSERT INTO saeima_bill_stages (
                bill_id, stage_name, stage_result, stage_date,
                vote_id, session_id, amendment_nr, stage_kind
              ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (bill_id, canonical, stage_result, stage_date, vote_id,
             session_id, amendment_nr, stage_kind),
        )
        sid = cur.lastrowid

        new_stage, new_status = derive_bill_denorm(db, bill_id)

        # last_updated_at = LV (now_lv()) — pretstatā UTC `created_at` augstāk.
        db.execute(
            "UPDATE saeima_bills SET current_stage=?, current_status=?, "
            "last_updated_at=CASE WHEN ? THEN ? ELSE last_updated_at END WHERE id=?",
            (new_stage, new_status, touch_updated_at, now_lv(), bill_id),
        )

        # CLAUDE.md invariant #12: this function is the SOLE writer to
        # saeima_votes.bill_id. For vote-kind stages the vote must be bound to
        # the parent bill inside the same transaction; doing it later (as
        # @saeima-tracker did pre-2026-05-16) leaves a window where stages
        # exist but the vote row is unbound, and any aborted run leaves
        # permanently inconsistent denorm.
        # Izņēmums: keep_vote_bill_id — balsojums paliek pie sava likumprojekta.
        if vote_id is not None and not keep_vote_bill_id:
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
    bill_type: str                                  # "Lp14" | "Lm15" | "P15" … (jebkurš sasaukums)
    title: str
    individual_submitters: list[str] = field(default_factory=list)
    institutional_submitter: Optional[str] = None
    reading_hint: Optional[str] = None
    vote_uuid: Optional[str] = None
