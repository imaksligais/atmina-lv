"""Tests for scripts/migrate_commentator_demotion.py — idempotency, completeness."""
import sqlite3
from pathlib import Path

import pytest

from scripts.migrate_commentator_demotion import COMMENTATOR_IDS, demote_commentators


@pytest.fixture
def temp_db(tmp_path: Path) -> sqlite3.Connection:
    db_path = tmp_path / "test.db"
    con = sqlite3.connect(db_path)
    con.executescript("""
        CREATE TABLE tracked_politicians (
            id INTEGER PRIMARY KEY,
            name TEXT, party TEXT, x_handle TEXT,
            relationship_type TEXT
        );
        CREATE TABLE social_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            opponent_id INTEGER,
            platform TEXT, handle TEXT,
            feed_type TEXT DEFAULT 'first_party',
            active BOOLEAN DEFAULT 1
        );
    """)
    con.execute(
        "INSERT INTO tracked_politicians (id, name, x_handle, relationship_type) VALUES "
        "(171, '@Heinrih5', 'Heinrih5', 'commentator'), "
        "(175, '@Kurmitis_', 'Kurmitis_', 'commentator')"
    )
    con.execute(
        "INSERT INTO social_accounts (opponent_id, platform, handle, feed_type, active) VALUES "
        "(171, 'twitter', 'Heinrih5', 'first_party', 1)"
    )
    con.commit()
    return con


def test_demotion_changes_relationship_type_to_inactive(temp_db: sqlite3.Connection):
    demote_commentators(temp_db, only_ids=[171, 175])
    row = temp_db.execute("SELECT relationship_type FROM tracked_politicians WHERE id=171").fetchone()
    assert row[0] == "inactive"


def test_demotion_sets_feed_type_relay_for_existing_social_account(temp_db: sqlite3.Connection):
    demote_commentators(temp_db, only_ids=[171, 175])
    row = temp_db.execute(
        "SELECT feed_type FROM social_accounts WHERE opponent_id=171 AND platform='twitter'"
    ).fetchone()
    assert row[0] == "relay"


def test_demotion_creates_missing_social_account(temp_db: sqlite3.Connection):
    demote_commentators(temp_db, only_ids=[171, 175])
    row = temp_db.execute(
        "SELECT handle, feed_type, active FROM social_accounts "
        "WHERE opponent_id=175 AND platform='twitter'"
    ).fetchone()
    assert row is not None
    assert row[0] == "Kurmitis_"
    assert row[1] == "relay"
    assert row[2] == 1


def test_demotion_is_idempotent(temp_db: sqlite3.Connection):
    demote_commentators(temp_db, only_ids=[171, 175])
    demote_commentators(temp_db, only_ids=[171, 175])
    sa_count = temp_db.execute(
        "SELECT COUNT(*) FROM social_accounts WHERE opponent_id IN (171, 175) AND platform='twitter'"
    ).fetchone()[0]
    assert sa_count == 2


def test_demotion_preserves_unrelated_politicians(temp_db: sqlite3.Connection):
    temp_db.execute(
        "INSERT INTO tracked_politicians (id, name, relationship_type) VALUES (1, 'Politiķis', 'tracked')"
    )
    temp_db.commit()
    demote_commentators(temp_db, only_ids=[171, 175])
    row = temp_db.execute("SELECT relationship_type FROM tracked_politicians WHERE id=1").fetchone()
    assert row[0] == "tracked"


def test_demotion_handles_multiple_social_handles_per_pid(temp_db: sqlite3.Connection):
    """Svirskis has 2 X handles (realNepareizais + ESvirskis). Both must become relay."""
    temp_db.execute(
        "INSERT INTO tracked_politicians (id, name, x_handle, relationship_type) VALUES "
        "(62, 'Edgars Svirskis', 'ESvirskis', 'commentator')"
    )
    temp_db.execute(
        "INSERT INTO social_accounts (opponent_id, platform, handle, feed_type, active) VALUES "
        "(62, 'twitter', 'realNepareizais', 'first_party', 1), "
        "(62, 'twitter', 'ESvirskis', 'first_party', 1)"
    )
    temp_db.commit()

    demote_commentators(temp_db, only_ids=[62])
    rows = temp_db.execute(
        "SELECT handle, feed_type FROM social_accounts WHERE opponent_id=62 AND platform='twitter'"
    ).fetchall()
    assert len(rows) == 2
    assert all(r[1] == "relay" for r in rows), f"both handles must be relay, got {rows}"
