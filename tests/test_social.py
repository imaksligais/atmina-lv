"""Tests for src/social.py — focused on _store_tweets role assignment.

2026-04-23 fix: _store_tweets previously hardcoded role='subject' for every
tweet it stored. twikit surfaces retweets, quote-tweets, and reply-thread
context via a politician's timeline endpoint — those tweets are authored by
OTHER handles, so tagging them 'subject' polluted the extractor queue with
non-speaker documents. See wiki/CHANGELOG 2026-04-23 for incident context.

Pattern note: we use _redirected_get_db (mirrors tests/test_audit_junction_roles.py)
so that insert_document's frozen db_path=DB_PATH default is transparently
redirected at call time. Monkeypatching DB_PATH alone doesn't work because
default parameter values are bound at function-definition time.
"""

import sqlite3

import pytest

import src.db as db_mod


@pytest.fixture
def tmp_social_db(tmp_path, monkeypatch):
    """Isolated DB per test. Redirects get_db in src.db and src.social so
    insert_document (frozen DB_PATH default) routes to the tmp file. Also
    stubs out embed_document and insert_chunks on src.social so tests don't
    drag in the sentence-transformer model for a role-assignment check."""
    db_path = str(tmp_path / "atmina_test.db")
    db_mod.init_db(db_path)

    orig_get_db = db_mod.get_db

    def _redirected_get_db(db_path_arg: str = db_path) -> sqlite3.Connection:
        return orig_get_db(db_path)

    monkeypatch.setattr(db_mod, "get_db", _redirected_get_db)
    monkeypatch.setattr(db_mod, "DB_PATH", db_path)

    # src.social imports get_db by name, so patch the rebinding there too.
    import src.social as social_mod
    monkeypatch.setattr(social_mod, "get_db", _redirected_get_db)

    # Skip real embeddings — they'd load a 100MB transformer model for a
    # test that only cares about role in document_politicians.
    monkeypatch.setattr(social_mod, "embed_document", lambda text: [])
    monkeypatch.setattr(social_mod, "insert_chunks", lambda *a, **kw: None)

    # Seed one tracked politician with one registered twitter handle.
    conn = orig_get_db(db_path)
    conn.execute(
        "INSERT INTO tracked_politicians (id, name, relationship_type) "
        "VALUES (1, 'Testa Politiķis', 'tracked')"
    )
    conn.execute(
        "INSERT INTO social_accounts (opponent_id, platform, handle, active) "
        "VALUES (1, 'twitter', 'TestaPolitikis', 1)"
    )
    conn.commit()
    yield conn
    conn.close()


def test_store_tweets_assigns_subject_when_author_matches(tmp_social_db):
    """Tweet whose source_url author is the politician's registered handle → role='subject'."""
    from src.social import _store_tweets
    tweets = [{
        "text": "Šodien parlamentā runāju par budžeta grozījumiem — atbalsta veselības sektoram. " * 2,
        "source_url": "https://x.com/TestaPolitikis/status/1234567890",
        "created_at": "2026-04-23T10:00:00+00:00",
        "lang": "lv",
    }]
    _store_tweets(tweets, opponent_id=1)

    role = tmp_social_db.execute(
        "SELECT role FROM document_politicians WHERE politician_id = 1"
    ).fetchone()
    assert role is not None, "expected a document_politicians row to be created"
    assert role[0] == "subject"


def test_store_tweets_assigns_mentioned_when_author_differs(tmp_social_db):
    """Tweet surfaced via politician's timeline but authored by another handle
    (retweet, quote-tweet, reply thread) → role='mentioned'. This is the
    regression fix for 2026-04-23 — previously every such tweet was incorrectly
    tagged 'subject' in _store_tweets.
    """
    from src.social import _store_tweets
    tweets = [{
        # Content is from @OtherAuthor, surfaced via @TestaPolitikis's timeline
        "text": "Rīgas domes priekšsēdētājs ziņo par jauno iepirkumu — pilsētas budžets palielinās.",
        "source_url": "https://x.com/OtherAuthor/status/9999999999",
        "created_at": "2026-04-23T11:00:00+00:00",
        "lang": "lv",
    }]
    _store_tweets(tweets, opponent_id=1)

    role = tmp_social_db.execute(
        "SELECT role FROM document_politicians WHERE politician_id = 1"
    ).fetchone()
    assert role is not None
    assert role[0] == "mentioned", (
        f"expected 'mentioned' for non-author tweet, got {role[0]!r}"
    )


def test_store_tweets_assigns_mentioned_when_source_url_missing(tmp_social_db):
    """Defensive: missing or malformed source_url falls back to 'mentioned'.
    Safer than 'subject' because we cannot verify authorship.
    """
    from src.social import _store_tweets
    tweets = [{
        "text": "Kaut kāda saruna par politiku — pietiekami gara, lai nepaliktu zem 50 rakstzīmju sliekšņa.",
        "source_url": None,
        "created_at": "2026-04-23T12:00:00+00:00",
        "lang": "lv",
    }]
    _store_tweets(tweets, opponent_id=1)

    role = tmp_social_db.execute(
        "SELECT role FROM document_politicians WHERE politician_id = 1"
    ).fetchone()
    # Missing source_url means we cannot prove authorship — default to 'mentioned'.
    # The doc may alternatively be skipped entirely if insert_document rejects
    # NULL source_url — either is acceptable; the critical invariant is
    # "NOT tagged subject without author proof".
    if role is not None:
        assert role[0] == "mentioned"
