"""One-off fix: relay-authored tweets had role='subject' wrongly assigned to
text-matched politicians. After 2026-04-25 matcher fix removing the relay
short-circuit, role should be 'mentioned'.

Strategy:
1. Find document_politicians rows where:
   - role='subject'
   - doc is platform='twitter'
   - URL author handle is a relay account
   - politician_id is NOT the relay account's owner (relay self-fetch case)
2. UPDATE those to role='mentioned'.

Idempotent: re-running finds 0 rows after first execution.
"""
import sqlite3
import argparse


def fix_relay_subjects(con: sqlite3.Connection) -> dict:
    cur = con.cursor()
    # Find (doc_id, pid) pairs where role='subject' on relay-authored tweet
    # is structurally wrong.
    candidates = con.execute("""
        SELECT dp.document_id, dp.politician_id
        FROM document_politicians dp
        JOIN documents d ON d.id = dp.document_id
        JOIN social_accounts sa
            ON LOWER(d.source_url) LIKE '%/' || LOWER(sa.handle) || '/status/%'
        WHERE dp.role = 'subject'
          AND d.platform = 'twitter'
          AND sa.feed_type = 'relay'
          AND sa.opponent_id != dp.politician_id
    """).fetchall()

    deleted = 0
    updated = 0
    for doc_id, pid in candidates:
        # If a 'mentioned' row already exists for this (doc, pid), drop the
        # wrong 'subject' row outright (the right relationship is already
        # captured). Otherwise UPDATE the 'subject' row to 'mentioned'.
        existing = con.execute(
            "SELECT 1 FROM document_politicians "
            "WHERE document_id=? AND politician_id=? AND role='mentioned'",
            (doc_id, pid),
        ).fetchone()
        if existing:
            cur.execute(
                "DELETE FROM document_politicians "
                "WHERE document_id=? AND politician_id=? AND role='subject'",
                (doc_id, pid),
            )
            deleted += 1
        else:
            cur.execute(
                "UPDATE document_politicians SET role='mentioned' "
                "WHERE document_id=? AND politician_id=? AND role='subject'",
                (doc_id, pid),
            )
            updated += 1

    con.commit()
    return {"updated": updated, "deleted": deleted, "total": updated + deleted}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/atmina.db")
    args = parser.parse_args()

    con = sqlite3.connect(args.db)
    result = fix_relay_subjects(con)
    print(f"Fixed relay-authored tweet subject roles: "
          f"{result['updated']} updated, {result['deleted']} deleted "
          f"(dup with existing 'mentioned'), total {result['total']}")
    con.close()


if __name__ == "__main__":
    main()
