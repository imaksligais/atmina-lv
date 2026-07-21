"""Backfill document_politicians junctions for ALL X/Twitter documents.

Mirrors the role logic from `src.matcher.link_politicians_to_documents`
(src/matcher.py:490) but scoped to platform IN ('twitter','x_mention') and
without the recency cutoff. Idempotent — uses INSERT OR IGNORE on the PK
(document_id, politician_id, role).

Driven by the 2026-04-30 unification: the @-handle-only junction logic in
_normalize_mention and _store_tweets misses tweets that mention politicians
by surname only ("Siliņa apstiprina X" without @-tag). This script
retroactively adds those junctions using the existing match_politicians()
infrastructure.

Backup the DB first:
    cp data/atmina.db data/atmina.db.pre-x-backfill.db

Usage:
    python scripts/backfill_x_junctions.py [--dry-run] [--limit N]
"""
import argparse
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.db import get_db  # noqa: E402
from src.matcher import extract_twitter_author_handle, match_politicians  # noqa: E402


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--dry-run", action="store_true",
                   help="Compute but don't INSERT")
    p.add_argument("--limit", type=int, default=None,
                   help="Process only first N docs (debug)")
    p.add_argument("--progress-every", type=int, default=500,
                   help="Print a progress line every N docs (default 500)")
    args = p.parse_args(argv)

    db = get_db()

    sa_rows = db.execute(
        "SELECT handle, opponent_id, feed_type FROM social_accounts "
        "WHERE platform = 'twitter'"
    ).fetchall()
    pid_to_handles: dict[int, set[str]] = {}
    for sa in sa_rows:
        if sa["handle"]:
            pid_to_handles.setdefault(sa["opponent_id"], set()).add(
                sa["handle"].lower()
            )

    pre_total_docs = db.execute(
        "SELECT COUNT(*) FROM documents WHERE platform IN ('twitter','x_mention')"
    ).fetchone()[0]
    pre_total_junctions = db.execute(
        "SELECT COUNT(*) FROM document_politicians dp "
        "JOIN documents d ON dp.document_id = d.id "
        "WHERE d.platform IN ('twitter','x_mention')"
    ).fetchone()[0]
    print(f"[pre]  X docs={pre_total_docs}, X junctions={pre_total_junctions}")

    sql = (
        "SELECT id, content, source_url, platform FROM documents "
        "WHERE platform IN ('twitter','x_mention') ORDER BY id"
    )
    if args.limit:
        sql += f" LIMIT {int(args.limit)}"
    rows = db.execute(sql).fetchall()
    print(f"[scan] processing {len(rows)} documents...")

    new_junctions = 0
    docs_with_new = 0
    docs_processed = 0
    t0 = time.time()

    for r in rows:
        docs_processed += 1
        if docs_processed % args.progress_every == 0:
            elapsed = time.time() - t0
            rate = docs_processed / elapsed if elapsed > 0 else 0
            print(f"  [{docs_processed}/{len(rows)}] {rate:.0f} docs/s, "
                  f"+{new_junctions} junctions so far")

        matches = match_politicians(r["content"])
        if not matches:
            continue

        platform = r["platform"]
        author_handle = (
            extract_twitter_author_handle(r["source_url"])
            if platform == "twitter"
            else None
        )

        added_for_doc = 0
        for pid, role in matches:
            if platform == "x_mention" and role == "subject":
                role = "mention_target"
            elif (
                platform == "twitter"
                and role == "subject"
                and author_handle is not None
                and author_handle not in pid_to_handles.get(pid, set())
            ):
                role = "mentioned"

            if args.dry_run:
                exists = db.execute(
                    "SELECT 1 FROM document_politicians "
                    "WHERE document_id=? AND politician_id=? AND role=?",
                    (r["id"], pid, role),
                ).fetchone()
                if not exists:
                    new_junctions += 1
                    added_for_doc += 1
            else:
                cur = db.execute(
                    "INSERT OR IGNORE INTO document_politicians "
                    "(document_id, politician_id, role) VALUES (?, ?, ?)",
                    (r["id"], pid, role),
                )
                if cur.rowcount > 0:
                    new_junctions += 1
                    added_for_doc += 1

        if added_for_doc > 0:
            docs_with_new += 1

    if not args.dry_run:
        db.commit()

    elapsed = time.time() - t0
    print(f"\n[done] processed={docs_processed} in {elapsed:.1f}s "
          f"({docs_processed/elapsed:.0f} docs/s)")
    print(f"       new junctions: {new_junctions}")
    print(f"       docs with new junction: {docs_with_new}")

    if not args.dry_run:
        post_total_junctions = db.execute(
            "SELECT COUNT(*) FROM document_politicians dp "
            "JOIN documents d ON dp.document_id = d.id "
            "WHERE d.platform IN ('twitter','x_mention')"
        ).fetchone()[0]
        print(f"[post] X junctions={post_total_junctions} "
              f"(+{post_total_junctions - pre_total_junctions})")

    db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
