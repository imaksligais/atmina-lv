"""CLI: atmina pārklājuma atskaite (read-only diagnostic).

Surfaces tracked politicians that lack a channel for positions/contradictions
to surface — primarily the "dark zone" (Saeima votes tracked, but no analyses,
no position claims, no X feed). That intersection is the concrete P4 target
list (audit 2026-06-08).

    .venv/Scripts/python scripts/coverage_report.py [--db data/atmina.db]

Read-only: opens the DB, prints a markdown report, writes nothing.
"""

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from src.coverage import compute_coverage, format_coverage_report  # noqa: E402


def main() -> None:
    # LV diacritics → force UTF-8 stdout so the report prints on Windows cp1252
    # consoles without needing PYTHONIOENCODING=utf-8.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description="atmina pārklājuma atskaite (read-only)")
    ap.add_argument("--db", default=None, help="DB ceļš (noklusē data/atmina.db)")
    args = ap.parse_args()
    cov = compute_coverage(args.db)
    print(format_coverage_report(cov))


if __name__ == "__main__":
    main()
