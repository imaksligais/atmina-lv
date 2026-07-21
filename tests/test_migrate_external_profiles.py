"""Tests for scripts/migrate_external_profiles.py — idempotent one-shot migration."""
import sqlite3
import pytest


@pytest.fixture
def fresh_db(tmp_path):
    """Migrētspējīga DB ar mazu paraugu social_accounts datiem."""
    from src.db import init_db, get_db
    db_path = str(tmp_path / "atmina.db")
    init_db(db_path)
    db = get_db(db_path)
    # Simulate the pre-migration prod state: this DB predates
    # idx_social_accounts_unique (now declared in schema.sql / created by
    # init_db). Drop it so we can seed the duplicate twitter row that the
    # migration is supposed to dedupe; run_migration dedupes then re-creates
    # the index (IF NOT EXISTS).
    db.execute("DROP INDEX IF EXISTS idx_social_accounts_unique")
    db.execute("INSERT INTO tracked_politicians (id, name, relationship_type) VALUES (10, 'Test FB', 'tracked')")
    db.execute("INSERT INTO tracked_politicians (id, name, relationship_type) VALUES (20, 'Test X Dup', 'tracked')")
    db.execute("INSERT INTO tracked_politicians (id, name, relationship_type) VALUES (62, 'Nepareizais', 'inactive')")
    db.execute("INSERT INTO tracked_politicians (id, name, relationship_type) VALUES (59, 'KNL', 'inactive')")
    # FB row → must move to external_profiles
    db.execute("INSERT INTO social_accounts (opponent_id, platform, handle, active) VALUES (10, 'facebook', 'edvins.snore', 1)")
    # website row with URL stuffed into handle → must move + url filled
    db.execute("INSERT INTO social_accounts (opponent_id, platform, handle, active) VALUES (10, 'website', 'https://rihardskols.lv', 1)")
    # X duplicate
    db.execute("INSERT INTO social_accounts (opponent_id, platform, handle, active, last_post_id, feed_type) VALUES (20, 'twitter', 'AinarsSlesers', 1, NULL, 'first_party')")
    db.execute("INSERT INTO social_accounts (opponent_id, platform, handle, active, last_post_id, feed_type) VALUES (20, 'twitter', 'AinarsSlesers', 1, '17890', 'first_party')")
    # X normal — must stay
    db.execute("INSERT INTO social_accounts (opponent_id, platform, handle, active, feed_type) VALUES (62, 'twitter', 'realNepareizais', 0, 'first_party')")
    db.execute("INSERT INTO social_accounts (opponent_id, platform, handle, active, feed_type) VALUES (59, 'twitter', 'KNL_LTV1', 0, 'first_party')")
    db.commit()
    db.close()
    return db_path


def test_migration_moves_facebook_rows(fresh_db):
    from scripts.migrate_external_profiles import run_migration
    run_migration(fresh_db)
    db = sqlite3.connect(fresh_db)
    db.row_factory = sqlite3.Row
    fb = db.execute(
        "SELECT * FROM external_profiles WHERE platform='facebook' AND opponent_id=10"
    ).fetchall()
    assert len(fb) == 1
    assert fb[0]["handle"] == "edvins.snore"
    assert fb[0]["url"] == "https://www.facebook.com/edvins.snore"
    # Should be removed from social_accounts
    sa_fb = db.execute("SELECT COUNT(*) FROM social_accounts WHERE platform='facebook'").fetchone()[0]
    assert sa_fb == 0
    db.close()


def test_migration_moves_website_rows(fresh_db):
    from scripts.migrate_external_profiles import run_migration
    run_migration(fresh_db)
    db = sqlite3.connect(fresh_db)
    db.row_factory = sqlite3.Row
    w = db.execute(
        "SELECT * FROM external_profiles WHERE platform='website' AND opponent_id=10"
    ).fetchall()
    assert len(w) == 1
    assert w[0]["url"] == "https://rihardskols.lv"
    assert w[0]["handle"] is None  # URL nepiebāzts kā handle
    sa_w = db.execute("SELECT COUNT(*) FROM social_accounts WHERE platform='website'").fetchone()[0]
    assert sa_w == 0
    db.close()


def test_migration_dedupes_x_keeping_richer_row(fresh_db):
    from scripts.migrate_external_profiles import run_migration
    run_migration(fresh_db)
    db = sqlite3.connect(fresh_db)
    rows = db.execute(
        "SELECT last_post_id FROM social_accounts WHERE handle='AinarsSlesers'"
    ).fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "17890"  # palicis bagātākais ieraksts
    db.close()


def test_migration_reclassifies_nepareizais_and_knl(fresh_db):
    from scripts.migrate_external_profiles import run_migration
    run_migration(fresh_db)
    db = sqlite3.connect(fresh_db)
    db.row_factory = sqlite3.Row
    nep = db.execute("SELECT relationship_type FROM tracked_politicians WHERE id=62").fetchone()
    assert nep["relationship_type"] == "commentator"
    nep_sa = db.execute("SELECT active, feed_type FROM social_accounts WHERE handle='realNepareizais'").fetchone()
    assert nep_sa["active"] == 1
    assert nep_sa["feed_type"] == "first_party"

    knl = db.execute("SELECT relationship_type FROM tracked_politicians WHERE id=59").fetchone()
    assert knl["relationship_type"] == "journalist"
    knl_sa = db.execute("SELECT active, feed_type FROM social_accounts WHERE handle='KNL_LTV1'").fetchone()
    assert knl_sa["active"] == 1
    assert knl_sa["feed_type"] == "relay"
    db.close()


def test_migration_is_idempotent(fresh_db):
    from scripts.migrate_external_profiles import run_migration
    run_migration(fresh_db)
    run_migration(fresh_db)  # otrā reize neko nemaina
    db = sqlite3.connect(fresh_db)
    fb_count = db.execute("SELECT COUNT(*) FROM external_profiles WHERE platform='facebook'").fetchone()[0]
    assert fb_count == 1  # nav dublēts
    sa_dups = db.execute("SELECT COUNT(*) FROM social_accounts WHERE handle='AinarsSlesers'").fetchone()[0]
    assert sa_dups == 1
    db.close()


def test_migration_adds_unique_index_on_social_accounts(fresh_db):
    from scripts.migrate_external_profiles import run_migration
    run_migration(fresh_db)
    db = sqlite3.connect(fresh_db)
    idx = db.execute("PRAGMA index_list(social_accounts)").fetchall()
    names = {r[1] for r in idx}
    assert "idx_social_accounts_unique" in names
    # Pārbaude — unique index novērš atkārtotu insert
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO social_accounts (opponent_id, platform, handle) VALUES (62, 'twitter', 'realNepareizais')"
        )
        db.commit()
    db.close()
