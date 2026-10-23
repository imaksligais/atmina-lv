#!/usr/bin/env python
"""Junction-atgūšanas apsekojums — citētie `mentioned` runātāji ar
`extracted_at IS NULL` (noteikumi: `src/quoted_speaker.py::recovery_survey`).

Tikai lasa DB; neko neraksta. Aizstāj rokas SQL no `/dienas-rutina` § 2.

Lietošana:
    .venv/Scripts/python.exe scripts/recovery_survey.py --days 2
    .venv/Scripts/python.exe scripts/recovery_survey.py --days 2 --json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src.db import get_db  # noqa: E402
from src.quoted_speaker import format_recovery_line, lv_pairs, recovery_survey  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Junction-atgūšanas apsekojums (tikai lasa DB).")
    ap.add_argument("--days", type=int, default=1, help="logs dienās (noklusējums 1)")
    ap.add_argument("--json", action="store_true", help="izvade JSON formā")
    args = ap.parse_args(argv)

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    os.chdir(REPO)  # DB_PATH ir relatīvs repo saknei

    db = get_db()
    try:
        survey = recovery_survey(db, days=args.days)
    finally:
        db.close()

    if args.json:
        print(json.dumps(survey, ensure_ascii=False, indent=2))
        return 0

    n = survey["checked"]
    print(f"{format_recovery_line(survey)} — pārbaudīti {n} {lv_pairs(n)}")
    for band in ("inversion", "beside_subject"):
        pairs = survey["bands"][band]
        print(f"\n{band} ({len(pairs)}):")
        if not pairs:
            print("  (nav)")
        for p in pairs:
            print(f"  doc {p['document_id']:<7} pid {p['politician_id']:<5} "
                  f"{p['name']:<28} {p['platform']:<10} signāli {p['signals']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
