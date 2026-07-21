"""Saeimas agenda snapshot parsers.

F4.3 izvilkts no src/saeima.py monolīta. Satur TIKAI agenda parsing —
`parse_agenda_snapshot()` + iekšējie helperi. Vote snapshot parsing
(`parse_vote_snapshot`) dzīvo `votes.py`, jo tas ražo `VoteResult` un
loģiski grupējas ar pārējo vote storage pipeline-u; lai izvairītos no
votes ↔ parsing cikla pār `VoteResult` import.
"""

from __future__ import annotations

import re
from typing import Optional

from src.saeima.bills import AgendaBill

# Bill heading + document_nr on a single line.
# Real Playwright agenda emits each bill multiple times (row, cell, nested
# row/cell, text, link); without DOTALL the `(.+?)` title capture is bounded
# to one line, and dedup-by-doc_nr keeps the first clean match.
# Synthetic test format ("Likumprojekts TITLE (1234/Lp14)" on one line)
# also matches this pattern.
_AGENDA_BILL_RE = re.compile(
    r"(Likumprojekts|Lēmuma projekts|Paziņojums|Pieprasījums)\s+(.+?)\s*\((\d+/(?:Lp14|Lm14|P14))\)",
    re.IGNORECASE,
)
# Individual submitter pattern — institutional submitter is matched inline
# in `_parse_institutional_submitter` (two distinct regex shapes for synthetic
# vs accessibility-tree formats), not via a shared module constant.
_INDIVIDUAL_SUBMITTER_RE = re.compile(
    r"Deputāti?\s+([^\n]+)",
    re.IGNORECASE,
)


def _extract_bill_type(doc_nr: str) -> Optional[str]:
    """Derive bill_type from document_nr suffix."""
    if doc_nr.endswith("/Lp14"):
        return "Lp14"
    if doc_nr.endswith("/Lm14"):
        return "Lm14"
    if doc_nr.endswith("/P14"):
        return "P14"
    return None


def _parse_individual_submitters(window: str) -> list[str]:
    """Extract individual deputy names from a text window."""
    m = _INDIVIDUAL_SUBMITTER_RE.search(window)
    if not m:
        return []
    raw = m.group(1).strip()
    # Strip trailing noise: " Debates", " [ref=", "Nodots", etc.
    raw = re.sub(r"\s+(Debates|Nodots|$).*", "", raw, flags=re.IGNORECASE).strip()
    return [n.strip() for n in raw.split(",") if n.strip()]


def _parse_institutional_submitter(window: str) -> Optional[str]:
    """Extract institutional submitter from a text window."""
    # Check for "Iesniedzējs: X" pattern (synthetic format)
    m_iesn = re.search(r"Iesniedzējs:\s*([^\n]+?)(?=\n|$)", window, re.IGNORECASE)
    if m_iesn:
        val = m_iesn.group(1).strip()
        if not val.lower().startswith("deputāt"):
            return val
    # Check for bare "Ministru kabinets" (accessibility tree format)
    if re.search(r"(?:^|\s|:\s)Ministru kabinets(?:\s|$)", window, re.IGNORECASE | re.MULTILINE):
        return "Ministru kabinets"
    return None


def parse_agenda_snapshot(snapshot_text: str) -> list[AgendaBill]:
    """Izvelk visus Lp14/Lm14/P14 items no agenda snapshot.

    Pattern: '(Likumprojekts|Lēmuma projekts|Paziņojums|Pieprasījums) TITLE
    (NNNN/Xx14)' uz vienas rindas. Strādā gan sintētiskajam testa formātam
    (viens match per bill), gan Playwright accessibility tree formātam (kur
    katrs bill atkārtojas kā row/cell/nested-row/cell/text rindās — pirmais
    match per `document_nr` uzvar dedup'ā).

    bill_type derivēts no document_nr sufiksa; nezināmi sufiksi netiek izvilkti
    (regex jau ierobežo whitelist).
    Spec § 4.3.
    """
    if not snapshot_text:
        return []

    bills: list[AgendaBill] = []
    seen_doc_nrs: set[str] = set()

    matches = list(_AGENDA_BILL_RE.finditer(snapshot_text))
    for i, m in enumerate(matches):
        raw_title, doc_nr = m.group(2), m.group(3)
        bill_type = _extract_bill_type(doc_nr)
        if bill_type is None or doc_nr in seen_doc_nrs:
            continue

        title = raw_title.strip().rstrip(",").strip()
        # Strip leading "N. N." numbering noise from accessibility-tree row prefix
        title = re.sub(r"^\d+\.\s*\d*\.?\s*", "", title).strip()

        # Look ahead up to 500 chars, but cap at the next bill's start so the
        # window cannot bleed deputies from bill i+1 into bill i. 2026-04-27
        # smoke caught MK bills incorrectly inheriting the next bill's deputies.
        end = m.end()
        next_start = matches[i + 1].start() if i + 1 < len(matches) else len(snapshot_text)
        window_end = min(end + 500, next_start)
        window = snapshot_text[end:window_end]

        institutional = _parse_institutional_submitter(window)
        individual = _parse_individual_submitters(window)

        seen_doc_nrs.add(doc_nr)
        bills.append(AgendaBill(
            document_nr=doc_nr,
            bill_type=bill_type,
            title=title,
            individual_submitters=individual,
            institutional_submitter=institutional,
        ))

    return bills
