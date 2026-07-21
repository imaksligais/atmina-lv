"""Audit claims whose source_url author does not match the opponent politician's handles.

Read-only. Output is a CSV for human review — does NOT auto-delete or modify
claims, because claim deletion has downstream effects (wiki pages, briefs,
public site) that require per-case human judgment.

Usage:
    python scripts/audit_claim_attribution.py > claim_audit.csv
"""

from __future__ import annotations

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


def find_suspect_claims(db) -> list[dict[str, Any]]:
    """Return claims whose Twitter source_url author does not match opponent handles."""
    pid_to_handles = _load_pid_to_handles(db)

    rows = db.execute(
        """
        SELECT c.id, c.opponent_id, tp.name AS opponent_name, c.topic,
               c.stance, c.source_url, c.stated_at, c.created_at, c.claim_type
        FROM claims c
        JOIN tracked_politicians tp ON tp.id = c.opponent_id
        WHERE c.claim_type = 'position'
          AND (c.source_url LIKE 'https://x.com/%' OR c.source_url LIKE 'https://twitter.com/%')
        ORDER BY c.id DESC
        """
    ).fetchall()

    suspects: list[dict[str, Any]] = []
    for row in rows:
        author_handle = extract_twitter_author_handle(row["source_url"])
        if author_handle is None:
            continue
        pol_handles = pid_to_handles.get(row["opponent_id"], set())
        if not pol_handles:
            suspects.append(
                {
                    "claim_id": row["id"],
                    "opponent_id": row["opponent_id"],
                    "opponent_name": row["opponent_name"],
                    "topic": row["topic"],
                    "stance": (row["stance"] or "")[:200],
                    "url_author": author_handle,
                    "politician_handles": "",
                    "verdict": "unverifiable",
                    "source_url": row["source_url"],
                    "created_at": row["created_at"],
                }
            )
            continue
        if author_handle not in pol_handles:
            suspects.append(
                {
                    "claim_id": row["id"],
                    "opponent_id": row["opponent_id"],
                    "opponent_name": row["opponent_name"],
                    "topic": row["topic"],
                    "stance": (row["stance"] or "")[:200],
                    "url_author": author_handle,
                    "politician_handles": ",".join(sorted(pol_handles)),
                    "verdict": "mismatch",
                    "source_url": row["source_url"],
                    "created_at": row["created_at"],
                }
            )

    return suspects


def main():
    db = get_db()
    suspects = find_suspect_claims(db)
    writer = csv.DictWriter(
        sys.stdout,
        fieldnames=[
            "claim_id",
            "opponent_id",
            "opponent_name",
            "topic",
            "stance",
            "url_author",
            "politician_handles",
            "verdict",
            "source_url",
            "created_at",
        ],
    )
    writer.writeheader()
    for s in suspects:
        writer.writerow(s)
    n_mismatch = sum(1 for s in suspects if s["verdict"] == "mismatch")
    n_unverifiable = sum(1 for s in suspects if s["verdict"] == "unverifiable")
    sys.stderr.write(
        f"\n{len(suspects)} suspect claims ({n_mismatch} mismatches, {n_unverifiable} unverifiable).\n"
    )
    db.close()


if __name__ == "__main__":
    main()
