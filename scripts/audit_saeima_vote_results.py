"""Audit saeima_votes.result against present-majority recomputation.

Background: commit 78d87fb fixed a fallback path that used wrong absolute 51-of-100
threshold instead of "klātesošo vairākums" (par > present // 2). The main parsing
path was always correct, but this script guardrails against future regressions
or manually inserted rows.

Usage:
    python scripts/audit_saeima_vote_results.py            # exit 0 ok, 1 if mismatches
    python scripts/audit_saeima_vote_results.py --verbose  # print each mismatch
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db import DB_PATH


def compute_expected_result(par: int, pret: int, atturas: int) -> str:
    """Apply Saeimas present-majority rule.

    Present = par + pret + atturas (those who registered a vote on the floor).
    Pieņemts iff par > present // 2; equality is NOT a majority.
    Special case: if no one voted, return 'nezināms' rather than fabricating
    a result.

    `Nebalsoja` is deliberately NOT in the denominator. Checked 2026-08-17: only
    25 rows in the corpus discriminate between the two readings, and the three
    that were ingested live by @saeima-tracker (the rendered page carries the
    real result: votes 183, 194, 213) all match this formula. The 22 that match
    the other reading were all written by the urllib backfill's compute-from-
    totals fallback, which uses `+ total_nebalso` — i.e. they are that
    fallback's own output, not evidence from saeima.lv.
    """
    present = par + pret + atturas
    if present == 0:
        return "nezināms"
    if par > present // 2:
        return "pieņemts"
    return "noraidīts"


# Literal source labels that are NOT `Pieņemts`/`Noraidīts` but still assert an
# outcome. The agenda page writes the ACTION that the carried motion produced
# instead of the generic word — `Nod. kom.` = "nodots komisijām", i.e. the
# referral happened, i.e. the motion carried. We store the label VERBATIM
# (operator verdict 2026-08-18, BACKLOG § Saeima) rather than flattening it to
# `Pieņemts`: the source distinction is real and mapping it away is not ours to
# make. The audit still checks the NUMBERS against the present-majority rule —
# the alias only tells it which outcome class the label belongs to, so this is a
# dictionary extension, not a gate bypass.
_OUTCOME_ALIASES = {
    "nod. kom.": "pieņemts",
    # 2026-08-21: verbatim action-labels from the live agenda page (all rows
    # carry result_source='agenda_label', 20.08 session ingest). 'Likums' =
    # "likums pieņemts" (final-reading adoption), 'Paziņojums' = announcement
    # carried — both are the ACTION the carried motion produced, same class as
    # 'Nod. kom.'. Corpus-wide: exactly 5 + 2 rows, every one with a par
    # majority (numbers still checked against the present-majority rule).
    "likums": "pieņemts",
    "paziņojums": "pieņemts",
}


def _normalize(s: Optional[str]) -> str:
    return (s or "").strip().lower()


def _outcome_class(stored: Optional[str]) -> str:
    """Map a stored `result` label onto the pieņemts/noraidīts outcome class."""
    norm = _normalize(stored)
    return _OUTCOME_ALIASES.get(norm, norm)


def audit(verbose: bool = False) -> int:
    """Return mismatch count. Print verbose details on demand."""
    db = sqlite3.connect(DB_PATH)
    rows = db.execute(
        "SELECT id, total_par, total_pret, total_atturas, result, motif "
        "FROM saeima_votes"
    ).fetchall()
    mismatches = 0
    fabricated = 0
    unknown = 0
    aliased = 0
    for vid, par, pret, atturas, stored, motif in rows:
        expected = compute_expected_result(par, pret, atturas)
        if _normalize(stored) in _OUTCOME_ALIASES:
            aliased += 1
        if _normalize(stored) == "":
            # NULL/empty = we assert nothing about this vote. That is the honest
            # state for a procedural row (no ballot cast) and for a sub-item vote
            # whose outcome the source never labels — not a defect. Counted so
            # the denominator stays visible; never a mismatch.
            unknown += 1
            continue
        if expected == "nezināms":
            # No ballot was cast (attendance registration, quorum check, office
            # ballot) yet a result IS asserted — fabrication, always a finding.
            fabricated += 1
            mismatches += 1
        elif _outcome_class(stored) != _normalize(expected):
            mismatches += 1
        else:
            continue
        if verbose:
            print(
                f"vote_id={vid} par={par} pret={pret} atturas={atturas} "
                f"stored={stored!r} expected={expected!r} motif={(motif or '')[:80]!r}"
            )
    # Denominators, not just the finding: a gate that reports only "0 mismatches"
    # hides the case where it compared nothing (CLAUDE.md § Working Conventions).
    print(
        f"rows={len(rows)} asserted={len(rows) - unknown} unknown={unknown} "
        f"aliased={aliased} "
        f"mismatches={mismatches} (of which fabricated on no-ballot rows: {fabricated})"
    )
    return mismatches


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    return 0 if audit(verbose=args.verbose) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
