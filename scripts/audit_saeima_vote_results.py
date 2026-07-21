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
    """
    present = par + pret + atturas
    if present == 0:
        return "nezināms"
    if par > present // 2:
        return "pieņemts"
    return "noraidīts"


def _normalize(s: Optional[str]) -> str:
    return (s or "").strip().lower()


def audit(verbose: bool = False) -> int:
    """Return mismatch count. Print verbose details on demand."""
    db = sqlite3.connect(DB_PATH)
    rows = db.execute(
        "SELECT id, total_par, total_pret, total_atturas, result, motif "
        "FROM saeima_votes"
    ).fetchall()
    mismatches = 0
    for vid, par, pret, atturas, stored, motif in rows:
        expected = compute_expected_result(par, pret, atturas)
        if _normalize(stored) != _normalize(expected):
            mismatches += 1
            if verbose:
                print(
                    f"vote_id={vid} par={par} pret={pret} atturas={atturas} "
                    f"stored={stored!r} expected={expected!r} motif={(motif or '')[:80]!r}"
                )
    print(f"audited={len(rows)} mismatches={mismatches}")
    return mismatches


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    return 0 if audit(verbose=args.verbose) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
