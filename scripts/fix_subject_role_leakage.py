"""One-shot backfill for 2026-04-23 matcher role-integrity regression.

Downgrades `document_politicians.role` from 'subject' to 'mentioned' for
twitter rows where source_url's author handle is NOT among the politician's
registered handles in social_accounts. This addresses 83 junction rows that
leaked through the live-fetch path (src.social._store_tweets) between the
2026-04-20 fix (which only patched the post-hoc scanner) and today's
complementary fix on the write path.

Idempotent: re-runs find nothing to update after the first pass.

Safety:
- UPDATE (not DELETE) — preserves the linkage metadata with the corrected
  role so mentions-monitor and downstream readers keep working.
- Read-only audit of claims potentially extracted from mis-tagged junction
  rows; DOES NOT auto-delete claims. Prints a report for operator review,
  mirroring the 2026-04-20 manual-delete pattern ('11 claims deleted' per
  project_matcher_role_integrity memory).
- Reports affected pids + counts so the operator can verify scope before/after.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db import get_db  # noqa: E402
from src.matcher import extract_twitter_author_handle  # noqa: E402


def main() -> None:
    db = get_db()
    # Note: get_db() already sets row_factory = sqlite3.Row (src/db.py:481),
    # so dict-style row access (row["handle"]) works without reassignment.

    # Build pid → lowercase handles map for all twitter social_accounts.
    # Note: NO active filter — must match Task 1's _store_tweets write-path
    # (src/social.py), which accepts any registered handle regardless of
    # active state. Asymmetry would cause spurious downgrades on inactive
    # but historically-valid handles.
    pid_handles: dict[int, set[str]] = {}
    for row in db.execute(
        "SELECT opponent_id, handle FROM social_accounts "
        "WHERE platform = 'twitter'"
    ).fetchall():
        pid_handles.setdefault(row["opponent_id"], set()).add(row["handle"].lower())

    # Find mismatched junction rows: role='subject' on twitter docs where
    # the doc's URL author is NOT in the pid's registered handles.
    candidates = db.execute(
        """
        SELECT dp.rowid AS jrow, dp.document_id, dp.politician_id, d.source_url,
               tp.name AS politician_name
        FROM document_politicians dp
        JOIN documents d ON d.id = dp.document_id
        JOIN tracked_politicians tp ON tp.id = dp.politician_id
        WHERE dp.role = 'subject'
          AND d.platform = 'twitter'
          AND d.source_url IS NOT NULL
        """
    ).fetchall()

    to_fix: list[tuple[int, int, int, str, str]] = []  # (jrow, doc_id, pid, name, source_url)
    for r in candidates:
        author = extract_twitter_author_handle(r["source_url"])
        pid = r["politician_id"]
        registered = pid_handles.get(pid, set())
        if author and author not in registered:
            to_fix.append(
                (r["jrow"], r["document_id"], pid, r["politician_name"], r["source_url"])
            )

    if not to_fix:
        print("No mismatched subject rows found — nothing to fix.")
        return

    # Affected-by-pid summary
    pid_counts: dict[tuple[int, str], int] = {}
    for _, _, pid, name, _ in to_fix:
        pid_counts[(pid, name)] = pid_counts.get((pid, name), 0) + 1
    print(f"Found {len(to_fix)} mismatched subject rows across {len(pid_counts)} politicians:")
    for (pid, name), count in sorted(pid_counts.items(), key=lambda x: -x[1]):
        print(f"  pid={pid:3d} {name:30s} {count} rows")

    # Audit: any claims written against these (politician_id, document_id) pairs?
    # These are potential mis-attributions needing manual review.
    print("\n--- Claim audit (potential mis-attributions) ---")
    affected_pairs = {(pid, doc_id) for _, doc_id, pid, _, _ in to_fix}
    claim_count = 0
    for pid, doc_id in affected_pairs:
        claims = db.execute(
            "SELECT id, topic, substr(stance, 1, 80) AS stance_preview "
            "FROM claims WHERE opponent_id = ? AND document_id = ?",
            (pid, doc_id),
        ).fetchall()
        for c in claims:
            claim_count += 1
            print(f"  claim #{c['id']} pid={pid} doc={doc_id} topic={c['topic']!r}")
            print(f"    {c['stance_preview']}")
    if claim_count == 0:
        print("  No claims tied to mis-tagged rows — clean downgrade, no manual review needed.")
    else:
        print(f"\n  {claim_count} claim(s) may be mis-attributed. Review manually;")
        print("  this script DOES NOT auto-delete them.")

    # Apply the UPDATE. `document_politicians` has UNIQUE(document_id,
    # politician_id, role), so straight UPDATE to 'mentioned' fails when a
    # 'mentioned' row already exists for the same (doc, pid) pair. In that
    # case the 'mentioned' row is authoritative — we just DELETE the
    # redundant 'subject' row. Otherwise UPDATE in place.
    print("\n--- Applying UPDATE/DELETE ---")
    updated = 0
    deleted = 0
    with db:
        for jrow, doc_id, pid, _name, _url in to_fix:
            existing = db.execute(
                "SELECT 1 FROM document_politicians "
                "WHERE document_id = ? AND politician_id = ? AND role = 'mentioned'",
                (doc_id, pid),
            ).fetchone()
            if existing:
                db.execute(
                    "DELETE FROM document_politicians WHERE rowid = ?",
                    (jrow,),
                )
                deleted += 1
            else:
                db.execute(
                    "UPDATE document_politicians SET role = 'mentioned' WHERE rowid = ?",
                    (jrow,),
                )
                updated += 1
    print(
        f"Resolved {len(to_fix)} junction rows: "
        f"{updated} UPDATE subject→mentioned, {deleted} DELETE (mentioned row already existed)."
    )

    # Post-run verification: the same SELECT should now return 0 mismatches.
    remaining = db.execute(
        """
        SELECT COUNT(*) FROM document_politicians dp
        JOIN documents d ON d.id = dp.document_id
        WHERE dp.role = 'subject' AND d.platform = 'twitter'
          AND d.source_url IS NOT NULL
        """
    ).fetchone()[0]
    # Re-count candidates where author mismatches after UPDATE
    still_bad = 0
    for r in db.execute(
        """
        SELECT dp.politician_id, d.source_url FROM document_politicians dp
        JOIN documents d ON d.id = dp.document_id
        WHERE dp.role = 'subject' AND d.platform = 'twitter' AND d.source_url IS NOT NULL
        """
    ).fetchall():
        author = extract_twitter_author_handle(r["source_url"])
        if author and author not in pid_handles.get(r["politician_id"], set()):
            still_bad += 1
    print(f"Post-update check: {remaining} twitter subject rows total, {still_bad} still mismatched.")
    if still_bad > 0:
        print(
            f"WARNING: post-update re-scan found {still_bad} remaining mismatch(es). "
            "The UPDATE has already committed. Investigate: possible concurrent write, "
            "or logic bug in extract_twitter_author_handle. Re-run the script to retry."
        )


if __name__ == "__main__":
    main()
