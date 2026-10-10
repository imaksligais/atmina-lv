"""One-shot idempotent migration: konsolidē social_accounts un izveido external_profiles.

Operācijas (visas conditional → drīkst palaist atkārtoti):
  1. Pārvieto platform IN ('facebook','website') rindas no social_accounts uz
     external_profiles. URL veidots:
       - facebook: https://www.facebook.com/{handle}
       - website: handle pats ir URL → url=handle, handle=NULL
  2. Dedupē literālus X dublikātus (paturot rindu ar non-NULL last_post_id, vai
     jaunāku last_fetched, vai mazāku id kā tiebreaker).
  3. Pievieno UNIQUE index uz social_accounts(opponent_id, platform, handle).
  4. Reklasificē:
       - id=62 (realNepareizais): tracked_politicians.relationship_type='commentator',
         social_accounts.active=1, feed_type='first_party'.
       - id=59 (KNL_LTV1): tracked_politicians.relationship_type='journalist',
         social_accounts.active=1, feed_type='relay'.

Usage:
    python -m scripts.migrate_external_profiles
    python -m scripts.migrate_external_profiles --db data/atmina.db
"""
from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def _migrate_facebook_rows(db: sqlite3.Connection) -> int:
    """Pārvieto FB rindas. Atgriež pārvietoto skaitu."""
    rows = db.execute(
        "SELECT id, opponent_id, handle, last_fetched, last_post_id, active "
        "FROM social_accounts WHERE platform='facebook'"
    ).fetchall()
    moved = 0
    for r in rows:
        url = f"https://www.facebook.com/{r[2]}" if r[2] else None
        if not url:
            continue
        db.execute(
            "INSERT OR IGNORE INTO external_profiles "
            "(opponent_id, platform, url, handle, last_fetched, last_post_id, active) "
            "VALUES (?, 'facebook', ?, ?, ?, ?, ?)",
            (r[1], url, r[2], r[3], r[4], r[5]),
        )
        db.execute("DELETE FROM social_accounts WHERE id=?", (r[0],))
        moved += 1
    return moved


def _migrate_website_rows(db: sqlite3.Connection) -> int:
    """Pārvieto website rindas (handle satur URL)."""
    rows = db.execute(
        "SELECT id, opponent_id, handle, last_fetched, last_post_id, active "
        "FROM social_accounts WHERE platform='website'"
    ).fetchall()
    moved = 0
    for r in rows:
        url = r[2]
        if not url:
            continue
        db.execute(
            "INSERT OR IGNORE INTO external_profiles "
            "(opponent_id, platform, url, handle, last_fetched, last_post_id, active) "
            "VALUES (?, 'website', ?, NULL, ?, ?, ?)",
            (r[1], url, r[3], r[4], r[5]),
        )
        db.execute("DELETE FROM social_accounts WHERE id=?", (r[0],))
        moved += 1
    return moved


def _dedupe_x_handles(db: sqlite3.Connection) -> int:
    """Dedupē literālus X dublikātus. Patur rindu ar non-NULL last_post_id;
    citādi rindu ar jaunāku last_fetched; citādi mazāko id."""
    dups = db.execute(
        "SELECT opponent_id, handle FROM social_accounts "
        "WHERE platform='twitter' "
        "GROUP BY opponent_id, handle HAVING COUNT(*) > 1"
    ).fetchall()
    deleted = 0
    for opp_id, handle in dups:
        rows = db.execute(
            "SELECT id, last_post_id, last_fetched FROM social_accounts "
            "WHERE platform='twitter' AND opponent_id=? AND handle=? "
            "ORDER BY (last_post_id IS NULL) ASC, last_fetched DESC, id ASC",
            (opp_id, handle),
        ).fetchall()
        keep_id = rows[0][0]
        for r in rows[1:]:
            db.execute("DELETE FROM social_accounts WHERE id=?", (r[0],))
            deleted += 1
        logger.info("Dedupe %s (opp=%s): kept id=%s, removed %d", handle, opp_id, keep_id, len(rows) - 1)
    return deleted


def _add_social_accounts_unique_index(db: sqlite3.Connection) -> None:
    """UNIQUE index uz (opponent_id, platform, handle).

    PIRMS šī izsaukuma _dedupe_x_handles JĀBŪT pabeigtam — citādi indeks
    crashēs. Idempotents — IF NOT EXISTS.
    """
    db.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_social_accounts_unique "
        "ON social_accounts(opponent_id, platform, handle)"
    )


def _reclassify_nepareizais(db: sqlite3.Connection) -> bool:
    """tracked_politicians.id=62 → commentator; social_accounts → active=1."""
    cur = db.execute(
        "UPDATE tracked_politicians SET relationship_type='commentator' "
        "WHERE id=62 AND relationship_type != 'commentator'"
    )
    changed_tp = cur.rowcount > 0
    cur = db.execute(
        "UPDATE social_accounts SET active=1, feed_type='first_party' "
        "WHERE opponent_id=62 AND handle='realNepareizais' "
        "AND (active=0 OR feed_type != 'first_party')"
    )
    changed_sa = cur.rowcount > 0
    return changed_tp or changed_sa


def _reclassify_knl(db: sqlite3.Connection) -> bool:
    """tracked_politicians.id=59 → journalist; social_accounts → relay+active."""
    cur = db.execute(
        "UPDATE tracked_politicians SET relationship_type='journalist' "
        "WHERE id=59 AND relationship_type != 'journalist'"
    )
    changed_tp = cur.rowcount > 0
    cur = db.execute(
        "UPDATE social_accounts SET active=1, feed_type='relay' "
        "WHERE opponent_id=59 AND handle='KNL_LTV1' "
        "AND (active=0 OR feed_type != 'relay')"
    )
    changed_sa = cur.rowcount > 0
    return changed_tp or changed_sa


def run_migration(db_path: str) -> dict:
    """Izpilda visas operācijas vienā transakcijā. Idempotents."""
    db = sqlite3.connect(db_path)
    db.execute("PRAGMA foreign_keys = ON")
    try:
        # Sagatavošanās — pārliecināmies, ka external_profiles eksistē
        # (init_db jau būs to izveidojusi, bet ja palaiž skriptu pirms init,
        # kļūdas message ir skaidrāks).
        cur = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='external_profiles'"
        ).fetchone()
        if not cur:
            raise RuntimeError(
                "external_profiles tabula nav atrasta — palaidiet init_db pirms migrācijas"
            )

        fb_moved = _migrate_facebook_rows(db)
        web_moved = _migrate_website_rows(db)
        dedup = _dedupe_x_handles(db)
        _add_social_accounts_unique_index(db)
        nep_changed = _reclassify_nepareizais(db)
        knl_changed = _reclassify_knl(db)

        db.commit()
        result = {
            "facebook_moved": fb_moved,
            "website_moved": web_moved,
            "x_duplicates_removed": dedup,
            "nepareizais_reclassified": nep_changed,
            "knl_reclassified": knl_changed,
        }
        logger.info("Migration complete: %s", result)
        return result
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="data/atmina.db", help="DB ceļš")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    if not Path(args.db).exists():
        logger.error("DB not found: %s", args.db)
        return 1

    result = run_migration(args.db)
    print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
