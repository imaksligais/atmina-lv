"""Junction role INVERSION sweep — the quoted speaker is linked `mentioned`.

READ-ONLY. Never writes; proposes nothing to apply.

WHY THIS EXISTS
`get_pending_politicians` builds the extraction queue from `role='subject'`.
A politician linked `mentioned` therefore never enters it — not even when they
are the article's only quoted source. Latvian news routinely puts the official
the story is *about* first and the politician who actually spoke later, so the
matcher's first-hit role assignment inverts the two. The document is then
stamped `reviewed_at` with zero positions and looks processed by every
indicator we have.

Measured 2026-08-02 over `platform='web'`, 90 days: 282 of 1897 candidate docs
(14.9 %), 390 lost speaker pairs, ~1.4 docs/day at the then-current rate, ~92 %
precision on a 12-doc manual re-read. That measurement was ad hoc and could not
be re-run; this script exists so the number has a query attached to it, per
CLAUDE.md ("a number is trustworthy only with the query that produced it").

The LETA sub-claim was REFUTED by the same measurement: LETA-marked documents
are slightly *less* affected (10.9 % vs 17.9 %). This is ordinary Latvian news
structure, not a wire-copy artifact.

DETECTOR LOGIC LIVES IN ``src/quoted_speaker.py`` (moved 2026-08-04, junction
inversijas plāna 4. solis) — the extraction queue's second lane imports the
same nominative-at-citation functions, so the audit measures exactly the class
the queue processes. Refactor gate: same-day checked/flagged identical before
and after the move (2026-08-04: checked=1277 flagged=281 abos).

Usage:
    .venv/Scripts/python.exe scripts/audit_junction_role_inversion.py
    .venv/Scripts/python.exe scripts/audit_junction_role_inversion.py --days 30
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db import get_db  # noqa: E402
from src.quoted_speaker import find_inversions  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--days", type=int, default=90)
    args = ap.parse_args()

    db = get_db()
    result = find_inversions(db, days=args.days)
    db.close()

    n = result["checked"]
    flagged = len(result["inversions"])
    print(f"Junction lomu inversija — READ-ONLY, pēdējās {args.days} dienas\n")
    for inv in result["inversions"][:60]:
        print(
            f"  doc {inv['document_id']:<7} runā(mentioned): "
            f"{', '.join(inv['speaker_names']) or '?':<34} "
            f"subject: {', '.join(inv['subject_names']) or '?'}"
        )
        print(f"           {inv['source_url']}")
    if flagged > 60:
        print(f"  ... vēl {flagged - 60} (izvade apgriezta pie 60)")
    pct = f"{flagged / n:.1%}" if n else "n/a"
    print(f"\nchecked={n} flagged={flagged} ({pct})")
    if n == 0:
        print("UZMANĪBU: denominators ir 0 — tie nav tīri dati, tie ir salauzti vārti.")
    print("Nekas nav mainīts. Lomu maiņa prasa operatora lēmumu + pāra rollback.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
