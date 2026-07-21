"""Demote 7 commentators from tracked_politicians to social_accounts relay-only.

Idempotent — drīkst palaist atkārtoti. Veic 3 darbības per commentator:
1. tracked_politicians.relationship_type: 'commentator' -> 'inactive'
   (Saglabā rindu, lai vēsturiskās commentary claims ar speaker_id FK
   paliek validas. 'inactive' filtrē no profila ģenerēšanas un
   get_pending_politicians.)
2. social_accounts: visām (var būt vairākas) tabulas rindām pid &
   platform='twitter' — feed_type -> 'relay'.
   Ja nav nevienas — INSERT (opponent_id, platform='twitter',
   handle no tracked_politicians.x_handle, feed_type='relay').
3. Nesaska ar tracked_politicians.x_handle (paliek; tas ir audit trail).
"""
import argparse
import sqlite3
from pathlib import Path


COMMENTATOR_IDS = [62, 169, 171, 172, 174, 175, 177]


def demote_commentators(
    con: sqlite3.Connection,
    only_ids: list[int] | None = None,
    commit: bool = True,
) -> dict:
    """Run demotion. Returns counts dict. Pass commit=False for dry-run."""
    ids = only_ids if only_ids is not None else COMMENTATOR_IDS
    placeholders = ",".join("?" * len(ids))

    counts = {"reltype_updated": 0, "social_updated": 0, "social_created": 0}

    cur = con.cursor()

    cur.execute(
        f"UPDATE tracked_politicians SET relationship_type='inactive' "
        f"WHERE id IN ({placeholders}) AND relationship_type='commentator'",
        ids,
    )
    counts["reltype_updated"] = cur.rowcount

    for pid in ids:
        existing_rows = con.execute(
            "SELECT id, feed_type FROM social_accounts "
            "WHERE opponent_id=? AND platform='twitter'",
            (pid,),
        ).fetchall()
        if existing_rows:
            for row in existing_rows:
                if row[1] != "relay":
                    cur.execute(
                        "UPDATE social_accounts SET feed_type='relay' WHERE id=?",
                        (row[0],),
                    )
                    counts["social_updated"] += 1
        else:
            handle_row = con.execute(
                "SELECT x_handle FROM tracked_politicians WHERE id=?", (pid,)
            ).fetchone()
            if not handle_row or not handle_row[0]:
                continue
            handle = handle_row[0].lstrip("@")
            cur.execute(
                "INSERT INTO social_accounts (opponent_id, platform, handle, feed_type, active) "
                "VALUES (?, 'twitter', ?, 'relay', 1)",
                (pid, handle),
            )
            counts["social_created"] += 1

    if commit:
        con.commit()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/atmina.db")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    con = sqlite3.connect(args.db)
    if args.dry_run:
        print(f"DRY RUN — no commits. Demoting {len(COMMENTATOR_IDS)} commentators...")
        try:
            counts = demote_commentators(con, commit=False)
            con.rollback()
            print(f"Would update: relationship_type={counts['reltype_updated']}, "
                  f"social_accounts updated={counts['social_updated']}, "
                  f"created={counts['social_created']}")
        finally:
            con.close()
        return

    counts = demote_commentators(con)
    print(f"Demoted: relationship_type updated={counts['reltype_updated']}, "
          f"social_accounts updated={counts['social_updated']}, "
          f"created={counts['social_created']}")
    con.close()


if __name__ == "__main__":
    main()
