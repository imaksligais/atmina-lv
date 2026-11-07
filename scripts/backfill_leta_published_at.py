"""Backfill documents.published_at for leta.lv articles from the LETA dateline.

leta.lv pages carry no date metadata, so 2 577 of 2 578 leta.lv documents had
published_at NULL (2026-10-14). Their text opens with a dateline such as
"Rīga, 24. marts, LETA." — day + month, no year. ``src.ingest.leta_published_at``
turns it into ``YYYY-MM-DDT00:00:00`` (year from scraped_at, ±7-day window);
this script applies that same function to the stored rows.

Default is DRY-RUN against a read-only connection: prints scanned / would-fill
/ skipped-by-reason counts. ``--write-rollback PATH`` additionally writes the
paired rollback SQL for the exact ids the dry-run would fill.

``--apply --rollback PATH`` fills ONLY the ids listed in that rollback file,
and only where published_at is still NULL — rows ingested after the dry-run
are never touched, so the committed rollback always covers the write. Then it
verifies filled == intended and exits 1 on any mismatch.

Usage:
    .venv/Scripts/python.exe scripts/backfill_leta_published_at.py \
        --write-rollback data/rollback_leta_published_at_2026-10-14.sql
    .venv/Scripts/python.exe scripts/backfill_leta_published_at.py --db COPY.db \
        --apply --rollback data/rollback_leta_published_at_2026-10-14.sql
"""
from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db import PRODUCTION_DB_PATH  # noqa: E402
from src.ingest import (  # noqa: E402
    _LETA_DATELINE_RE,
    LETA_DATELINE_MAX_GAP_DAYS,
    _lv_month,
    leta_published_at,
)

SCAN_SQL = """SELECT id, source_url, scraped_at, published_at, content
              FROM documents
              WHERE platform = 'web' AND source_domain LIKE '%leta.lv'
              ORDER BY id"""


def _skip_reason(text: str, scraped_at: str) -> str:
    """Why leta_published_at returned None — diagnostics only."""
    lines = [ln.strip() for ln in (text or "").split("\n") if ln.strip()][:5]
    m = next((m for m in map(_LETA_DATELINE_RE.match, lines) if m), None)
    if not m:
        return "no_dateline"
    month = _lv_month(m["mon"])
    if month is None:
        return "unparsed_month"
    scraped = datetime.fromisoformat(scraped_at).date()
    try:
        found = date(scraped.year, month, int(m["day"]))
    except ValueError:
        return "invalid_day"
    if found > scraped:
        found = found.replace(year=scraped.year - 1)
    if (scraped - found).days > LETA_DATELINE_MAX_GAP_DAYS:
        return "outside_window"
    return "unknown"


def plan(db: sqlite3.Connection) -> tuple[dict[int, str], Counter, int]:
    fills: dict[int, str] = {}
    skipped: Counter = Counter()
    scanned = 0
    for doc_id, url, scraped_at, published_at, content in db.execute(SCAN_SQL):
        scanned += 1
        if published_at is not None:
            skipped["already_set"] += 1
            continue
        if not scraped_at:
            skipped["no_scraped_at"] += 1
            continue
        value = leta_published_at(url, content, scraped_at)
        if value:
            fills[doc_id] = value
        else:
            skipped[_skip_reason(content, scraped_at)] += 1
    return fills, skipped, scanned


def write_rollback(path: Path, ids: list[int]) -> None:
    body = ",".join(str(i) for i in ids)
    path.write_text(
        "-- Rollback for scripts/backfill_leta_published_at.py\n"
        "-- Forward change (2026-10-14): documents.published_at set from the LETA\n"
        "-- dateline (YYYY-MM-DDT00:00:00) for leta.lv rows where it was NULL.\n"
        f"-- Ids: {len(ids)} (exactly the dry-run would-fill set).\n"
        f"UPDATE documents SET published_at=NULL WHERE id IN ({body});\n",
        encoding="utf-8",
    )


def read_rollback_ids(path: Path) -> list[int]:
    m = re.search(r"WHERE id IN \(([\d,\s]+)\)", path.read_text(encoding="utf-8"))
    if not m:
        raise SystemExit(f"no id list found in {path}")
    return [int(x) for x in m.group(1).split(",") if x.strip()]


def apply(db_path: str, rollback: Path) -> int:
    ids = read_rollback_ids(rollback)
    db = sqlite3.connect(db_path)
    ph = ",".join("?" * len(ids))
    rows = db.execute(
        f"SELECT id, source_url, scraped_at, content FROM documents "
        f"WHERE id IN ({ph}) AND published_at IS NULL", ids).fetchall()
    intended = {}
    for doc_id, url, scraped_at, content in rows:
        value = leta_published_at(url, content, scraped_at)
        if value:
            intended[doc_id] = value
    with db:
        changed = sum(
            db.execute("UPDATE documents SET published_at=? "
                       "WHERE id=? AND published_at IS NULL", (v, i)).rowcount
            for i, v in intended.items())
    filled = db.execute(
        f"SELECT COUNT(*) FROM documents WHERE id IN ({ph}) "
        f"AND published_at GLOB '????-??-??T00:00:00'", ids).fetchone()[0]
    db.close()
    print(f"rollback ids: {len(ids)}  still NULL: {len(rows)}  "
          f"intended: {len(intended)}  updated: {changed}  "
          f"rollback ids now date-filled: {filled}")
    if changed != len(intended) or len(intended) != len(rows):
        print("MISMATCH: updated != intended (or a listed NULL row no longer parses)",
              file=sys.stderr)
        return 1
    return 0


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--db", default=PRODUCTION_DB_PATH)
    ap.add_argument("--write-rollback", type=Path,
                    help="dry-run: write the paired rollback SQL here")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--rollback", type=Path,
                    help="--apply: rollback file whose ids are filled")
    args = ap.parse_args()

    if args.apply:
        if not args.rollback or not args.rollback.is_file():
            print("--apply needs --rollback PATH to an existing rollback file "
                  "(generate it with a dry-run --write-rollback first)", file=sys.stderr)
            return 2
        return apply(args.db, args.rollback)

    db = sqlite3.connect(f"file:{Path(args.db).as_posix()}?mode=ro", uri=True)
    fills, skipped, scanned = plan(db)
    db.close()
    print(f"scanned: {scanned}  would-fill: {len(fills)}  "
          f"skipped: {sum(skipped.values())}")
    for reason, n in sorted(skipped.items()):
        print(f"  skipped {reason}: {n}")
    if fills:
        vals = sorted(fills.values())
        print(f"  fill range: {vals[0]} … {vals[-1]}")
    if args.write_rollback:
        write_rollback(args.write_rollback, sorted(fills))
        print(f"rollback written: {args.write_rollback} ({len(fills)} ids)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
