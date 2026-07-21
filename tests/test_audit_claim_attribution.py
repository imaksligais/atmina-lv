"""Tests for scripts.audit_claim_attribution — read-only claim attribution audit."""

import sqlite3

import pytest

import src.db as db_mod
import src.ingest as ing_mod
import src.matcher as matcher_mod
from src.matcher import _clear_politician_cache


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "atmina_test.db")
    db_mod.init_db(db_path)

    orig_get_db = db_mod.get_db

    def _redirected_get_db(db_path_arg: str = db_path) -> sqlite3.Connection:
        return orig_get_db(db_path)

    monkeypatch.setattr(db_mod, "get_db", _redirected_get_db)
    monkeypatch.setattr(ing_mod, "get_db", _redirected_get_db)
    monkeypatch.setattr(matcher_mod, "get_db", _redirected_get_db)
    monkeypatch.setattr(db_mod, "DB_PATH", db_path)

    _clear_politician_cache()

    conn = orig_get_db(db_path)
    yield conn
    conn.close()


def test_audit_flags_claim_with_mismatched_author(tmp_db):
    from scripts.audit_claim_attribution import find_suspect_claims

    tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms) VALUES (45, 'Mārtiņš Krusts', '[]')"
    )
    tmp_db.execute(
        "INSERT INTO social_accounts (opponent_id, platform, handle) VALUES (45, 'twitter', 'krusts')"
    )
    tmp_db.execute(
        """
        INSERT INTO claims (opponent_id, topic, stance, quote, confidence, salience,
                            source_url, stated_at, claim_type)
        VALUES (45, 'Degviela', 'Test stance', 'test quote', 0.8, 0.5,
                'https://x.com/KasparsH/status/2045853390337405314',
                '2026-04-18', 'position')
        """
    )
    tmp_db.commit()

    suspects = find_suspect_claims(tmp_db)
    assert len(suspects) == 1
    assert suspects[0]["opponent_id"] == 45
    assert suspects[0]["url_author"] == "kasparsh"
    assert suspects[0]["verdict"] == "mismatch"


def test_audit_ignores_claim_on_own_tweet(tmp_db):
    from scripts.audit_claim_attribution import find_suspect_claims

    tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms) VALUES (45, 'Mārtiņš Krusts', '[]')"
    )
    tmp_db.execute(
        "INSERT INTO social_accounts (opponent_id, platform, handle) VALUES (45, 'twitter', 'krusts')"
    )
    tmp_db.execute(
        """
        INSERT INTO claims (opponent_id, topic, stance, quote, confidence, salience,
                            source_url, stated_at, claim_type)
        VALUES (45, 'Degviela', 'Own stance', 'own quote', 0.8, 0.5,
                'https://x.com/krusts/status/12345',
                '2026-04-18', 'position')
        """
    )
    tmp_db.commit()

    suspects = find_suspect_claims(tmp_db)
    assert suspects == []


def test_audit_skips_non_twitter_sources(tmp_db):
    from scripts.audit_claim_attribution import find_suspect_claims

    tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms) VALUES (146, 'Andris Bērziņš', '[]')"
    )
    tmp_db.execute(
        """
        INSERT INTO claims (opponent_id, topic, stance, quote, confidence, salience,
                            source_url, stated_at, claim_type)
        VALUES (146, 'Ekonomika', 'stance', 'quote', 0.7, 0.5,
                'https://www.la.lv/par-partiku', '2026-04-18', 'position')
        """
    )
    tmp_db.commit()

    suspects = find_suspect_claims(tmp_db)
    assert suspects == []


def test_audit_skips_saeima_claims(tmp_db):
    """saeima_vote claims use a different URL scheme, skip."""
    from scripts.audit_claim_attribution import find_suspect_claims

    tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms) VALUES (9, 'Krištopans', '[]')"
    )
    tmp_db.execute(
        """
        INSERT INTO claims (opponent_id, topic, stance, quote, confidence, salience,
                            source_url, stated_at, claim_type)
        VALUES (9, 'Vēlēšanas', 'voted yes', NULL, 1.0, 0.5,
                'https://titania.saeima.lv/...', '2026-04-18', 'saeima_vote')
        """
    )
    tmp_db.commit()

    suspects = find_suspect_claims(tmp_db)
    assert suspects == []


def test_audit_flags_unverifiable_when_politician_has_no_handle(tmp_db):
    """Politician without a social_accounts row gets 'unverifiable' verdict."""
    from scripts.audit_claim_attribution import find_suspect_claims

    tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms) VALUES (100, 'No Handle', '[]')"
    )
    tmp_db.execute(
        """
        INSERT INTO claims (opponent_id, topic, stance, quote, confidence, salience,
                            source_url, stated_at, claim_type)
        VALUES (100, 'Vide', 'stance', 'quote', 0.8, 0.5,
                'https://x.com/someuser/status/1', '2026-04-18', 'position')
        """
    )
    tmp_db.commit()

    suspects = find_suspect_claims(tmp_db)
    assert len(suspects) == 1
    assert suspects[0]["verdict"] == "unverifiable"
    assert suspects[0]["politician_handles"] == ""
