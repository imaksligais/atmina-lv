"""Audit document_politicians junction for role='subject' rows where the
URL author does not match the politician's registered Twitter handles.

Usage:
    python scripts/audit_junction_roles.py             # dry-run report (CSV to stdout)
    python scripts/audit_junction_roles.py --apply     # apply fixes
    python scripts/audit_junction_roles.py --limit 100 # first 100 rows only
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db import get_db  # noqa: E402
from src.matcher import extract_twitter_author_handle  # noqa: E402


def _load_pid_to_handles(db) -> dict[int, set[str]]:
    m: dict[int, set[str]] = {}
    for row in db.execute(
        "SELECT handle, opponent_id FROM social_accounts WHERE platform = 'twitter'"
    ).fetchall():
        m.setdefault(row["opponent_id"], set()).add(row["handle"].lower())
    return m


def find_mismatched_rows(db, limit: int | None = None) -> list[dict[str, Any]]:
    """Return list of junction rows whose role='subject' does not match URL author."""
    pid_to_handles = _load_pid_to_handles(db)

    query = """
        SELECT dp.document_id, dp.politician_id, dp.role, d.platform, d.source_url,
               tp.name AS politician_name
        FROM document_politicians dp
        JOIN documents d ON d.id = dp.document_id
        JOIN tracked_politicians tp ON tp.id = dp.politician_id
        WHERE dp.role = 'subject'
          AND d.platform IN ('twitter', 'x_mention')
        ORDER BY dp.document_id DESC
    """
    if limit:
        query += f" LIMIT {int(limit)}"

    results: list[dict[str, Any]] = []
    for row in db.execute(query).fetchall():
        platform = row["platform"]
        proposed_role: str | None = None
        author_handle = extract_twitter_author_handle(row["source_url"])

        if platform == "x_mention":
            proposed_role = "mention_target"
        elif platform == "twitter":
            if author_handle is None:
                continue
            pol_handles = pid_to_handles.get(row["politician_id"], set())
            if author_handle not in pol_handles:
                proposed_role = "mentioned"

        if proposed_role:
            results.append(
                {
                    "document_id": row["document_id"],
                    "politician_id": row["politician_id"],
                    "politician_name": row["politician_name"],
                    "platform": platform,
                    "source_url": row["source_url"],
                    "url_author": author_handle or "",
                    "politician_handles": ",".join(
                        sorted(pid_to_handles.get(row["politician_id"], set()))
                    ),
                    "current_role": row["role"],
                    "proposed_role": proposed_role,
                }
            )

    return results


def apply_fixes(db, mismatches: list[dict[str, Any]]) -> int:
    """Apply proposed role changes. INSERT OR IGNORE new role + DELETE old."""
    count = 0
    for m in mismatches:
        db.execute(
            """INSERT OR IGNORE INTO document_politicians
               (document_id, politician_id, role) VALUES (?, ?, ?)""",
            (m["document_id"], m["politician_id"], m["proposed_role"]),
        )
        db.execute(
            """DELETE FROM document_politicians
               WHERE document_id=? AND politician_id=? AND role='subject'""",
            (m["document_id"], m["politician_id"]),
        )
        count += 1
    db.commit()
    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="apply fixes (default: dry-run)")
    parser.add_argument("--limit", type=int, default=None, help="limit rows scanned")
    args = parser.parse_args()

    db = get_db()
    mismatches = find_mismatched_rows(db, limit=args.limit)

    writer = csv.DictWriter(
        sys.stdout,
        fieldnames=[
            "document_id",
            "politician_id",
            "politician_name",
            "platform",
            "source_url",
            "url_author",
            "politician_handles",
            "current_role",
            "proposed_role",
        ],
    )
    writer.writeheader()
    for m in mismatches:
        writer.writerow(m)

    sys.stderr.write(f"\n{len(mismatches)} mismatches found.\n")

    if args.apply:
        if not mismatches:
            sys.stderr.write("Nothing to apply.\n")
            return
        sys.stderr.write("Applying fixes...\n")
        n = apply_fixes(db, mismatches)
        sys.stderr.write(f"Updated {n} rows.\n")

    db.close()


if __name__ == "__main__":
    main()
