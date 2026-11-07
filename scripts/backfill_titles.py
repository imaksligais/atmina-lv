"""One-shot backfill: populate documents.title for legacy web rows.

Strategy: for every documents row where platform='web' AND title IS NULL/empty,
derive a title from the first reasonable content line, applying the same
suffix-strip + entity-decode pipeline as src/title_extract.

Run once after the title-extraction forward-fix lands. Idempotent — safe to
re-run; only updates rows still missing a title.

Usage:
    python -m scripts.backfill_titles                  # dry-run summary
    python -m scripts.backfill_titles --apply          # write to DB
    python -m scripts.backfill_titles --limit 100      # cap rows touched
"""
from __future__ import annotations

import argparse
import re
import sys
from typing import Optional

from src.db import DB_PATH, get_db
from src.title_extract import _normalize  # reuse suffix-strip + entity decode

# First content line is candidate. Reject lines outside [10, 250] chars.
_MIN_LEN = 10
_MAX_LEN = 250

# LA.lv content often ends headline with " 0" (comment count). Strip.
_LA_COMMENT_COUNT_RE = re.compile(r"\s+0\s*$")


def derive_title_from_content(content: Optional[str]) -> Optional[str]:
    """Pick the first non-trivial content line as a title candidate."""
    if not content or not isinstance(content, str):
        return None
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        # Strip LA.lv comment-count suffix before length check
        line = _LA_COMMENT_COUNT_RE.sub("", line).strip()
        # RSS-sourced docs join title+description with " — " (see
        # src/ingest.py:_parse_rss_items). When the joined line overruns
        # the length gate, recover the title by taking the prefix.
        if len(line) > _MAX_LEN and " — " in line:
            line = line.split(" — ", 1)[0].strip()
        if _MIN_LEN <= len(line) <= _MAX_LEN:
            return _normalize(line)
    return None


def backfill(db_path: str = DB_PATH, apply: bool = False, limit: Optional[int] = None) -> dict:
    """Walk title-less web docs and either preview or apply derived titles."""
    db = get_db(db_path)
    where = "platform='web' AND (title IS NULL OR title = '')"
    sql = f"SELECT id, content FROM documents WHERE {where}"
    if limit:
        sql += f" LIMIT {int(limit)}"

    rows = db.execute(sql).fetchall()
    derived = 0
    skipped = 0
    updates: list[tuple[str, int]] = []
    for r in rows:
        title = derive_title_from_content(r["content"])
        if title:
            derived += 1
            updates.append((title, r["id"]))
        else:
            skipped += 1

    if apply and updates:
        db.executemany("UPDATE documents SET title = ? WHERE id = ?", updates)
        db.commit()

    db.close()
    return {
        "scanned": len(rows),
        "derived": derived,
        "skipped": skipped,
        "applied": len(updates) if apply else 0,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true", help="write updates to DB")
    p.add_argument("--limit", type=int, default=None, help="cap rows scanned")
    args = p.parse_args()

    summary = backfill(apply=args.apply, limit=args.limit)
    print(f"Scanned:  {summary['scanned']}")
    print(f"Derived:  {summary['derived']}")
    print(f"Skipped:  {summary['skipped']}")
    print(f"Applied:  {summary['applied']}")
    if not args.apply:
        print("\n(dry-run — re-run with --apply to persist)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
