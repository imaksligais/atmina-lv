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

    # src.matcher also imports get_db by name — the first-party mention scan
    # (2026-08-18) calls match_politicians(), which loads name forms from the DB.
    import src.matcher as matcher_mod
    monkeypatch.setattr(matcher_mod, "get_db", _redirected_get_db)
    matcher_mod._clear_politician_cache()

    # Skip real embeddings — they'd load a 100MB transformer model for a
    # test that only cares about role in document_politicians.
    monkeypatch.setattr(social_mod, "embed_document", lambda text: [])
    monkeypatch.setattr(social_mod, "insert_chunks", lambda *a, **kw: None)

    # Seed tracked politicians with registered twitter handles.
    #   id=1 Testa Politiķis — first_party fetch account (the classic case).
    #   id=2 Otrs Politiķis — first_party; author of tweets that surface via
    #        id=1's feed (cross-feed author subject junction, 2026-07-24 fix).
    #   id=3 LTV Ziņas — relay organization account; its own handle must never
    #        get a 'subject' junction (relay defers to text-scan mentions).
    conn = orig_get_db(db_path)
    conn.execute(
        "INSERT INTO tracked_politicians (id, name, relationship_type) "
        "VALUES (1, 'Testa Politiķis', 'tracked')"
    )
    conn.execute(
        "INSERT INTO tracked_politicians (id, name, relationship_type) "
        "VALUES (2, 'Otrs Politiķis', 'tracked')"
    )
    conn.execute(
        "INSERT INTO tracked_politicians (id, name, relationship_type) "
        "VALUES (3, 'LTV Ziņas', 'organization')"
    )
    conn.execute(
        "INSERT INTO social_accounts (opponent_id, platform, handle, active, feed_type) "
        "VALUES (1, 'twitter', 'TestaPolitikis', 1, 'first_party')"
    )
    conn.execute(
        "INSERT INTO social_accounts (opponent_id, platform, handle, active, feed_type) "
        "VALUES (2, 'twitter', 'OtrsPolitikis', 1, 'first_party')"
    )
    conn.execute(
        "INSERT INTO social_accounts (opponent_id, platform, handle, active, feed_type) "
        "VALUES (3, 'twitter', 'LTVZinas', 1, 'relay')"
    )
    #   id=4 Andris Ozoliņš — tracked politician with EXPLICIT name_forms. He
    #        owns no social_accounts row: he exists only to be named in someone
    #        else's tweet text, which is exactly the first-party mention case.
    conn.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms, relationship_type) "
        "VALUES (4, 'Andris Ozoliņš', ?, 'tracked')",
        ('["Andris Ozoliņš", "Ozoliņš", "Ozoliņu", "Ozoliņam"]',),
    )
    conn.commit()
    matcher_mod._clear_politician_cache()
    yield conn
    matcher_mod._clear_politician_cache()
    conn.close()


def _junctions(conn, doc_id: int) -> set[tuple[int, str]]:
    """Return {(politician_id, role)} for a document."""
    rows = conn.execute(
        "SELECT politician_id, role FROM document_politicians WHERE document_id = ?",
        (doc_id,),
    ).fetchall()
    return {(r[0], r[1]) for r in rows}


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


# --- 2026-07-24: cross-feed author resolution + dedup junction merge ---


def test_store_tweets_cross_feed_author_gets_subject(tmp_social_db):
    """A tweet authored by OtrsPolitikis (id=2) surfaced via TestaPolitikis's
    (id=1) first_party feed → the fetch owner is 'mentioned' AND the real
    author gets a 'subject' junction (resolved against ALL twitter accounts)."""
    from src.social import _store_tweets
    tweets = [{
        "text": "Es aicinu valdību pārskatīt nodokļu politiku — mazie uzņēmumi cieš no birokrātijas.",
        "source_url": "https://x.com/OtrsPolitikis/status/1111111111",
        "created_at": "2026-07-24T10:00:00+00:00",
        "lang": "lv",
    }]
    _store_tweets(tweets, opponent_id=1)

    doc_id = tmp_social_db.execute("SELECT id FROM documents").fetchone()[0]
    assert _junctions(tmp_social_db, doc_id) == {(1, "mentioned"), (2, "subject")}


def test_store_tweets_dedup_merges_missing_subject_junction(tmp_social_db):
    """Store the author's own tweet first via opponent 2 (→ (2,'subject')),
    then the SAME text+url arrives via opponent 1's feed. content_hash dedup
    must NOT drop the merge: exactly one documents row; junctions now include
    both (2,'subject') and (1,'mentioned'). This is the doc-72542 bug."""
    from src.social import _store_tweets
    text = "Es aicinu valdību pārskatīt nodokļu politiku — mazie uzņēmumi cieš no birokrātijas."
    url = "https://x.com/OtrsPolitikis/status/2222222222"

    # First: author's own timeline (opponent 2).
    _store_tweets([{
        "text": text, "source_url": url,
        "created_at": "2026-07-24T10:00:00+00:00", "lang": "lv",
    }], opponent_id=2)

    doc_ids = [r[0] for r in tmp_social_db.execute("SELECT id FROM documents").fetchall()]
    assert len(doc_ids) == 1
    assert _junctions(tmp_social_db, doc_ids[0]) == {(2, "subject")}

    # Second: same tweet surfaced via opponent 1's feed (reply context).
    _store_tweets([{
        "text": text, "source_url": url,
        "created_at": "2026-07-24T10:00:00+00:00", "lang": "lv",
    }], opponent_id=1)

    doc_ids2 = [r[0] for r in tmp_social_db.execute("SELECT id FROM documents").fetchall()]
    assert len(doc_ids2) == 1, "content_hash dedup must not create a second row"
    assert _junctions(tmp_social_db, doc_ids2[0]) == {(2, "subject"), (1, "mentioned")}


def test_store_tweets_dedup_different_url_does_not_merge(tmp_social_db):
    """Copypasta gate: identical text under a DIFFERENT source_url must NOT
    merge junctions onto the first doc. Second insert creates no new doc
    (content_hash dup) and leaves the first doc's junctions untouched."""
    from src.social import _store_tweets
    text = "Kopēts identisks teksts par politiku, kas ir pietiekami garš, lai to saglabātu kā dokumentu."

    _store_tweets([{
        "text": text, "source_url": "https://x.com/OtrsPolitikis/status/3333333333",
        "created_at": "2026-07-24T10:00:00+00:00", "lang": "lv",
    }], opponent_id=2)

    doc_ids = [r[0] for r in tmp_social_db.execute("SELECT id FROM documents").fetchall()]
    assert len(doc_ids) == 1
    before = _junctions(tmp_social_db, doc_ids[0])
    assert before == {(2, "subject")}

    # Same text, DIFFERENT url, via opponent 1's feed.
    _store_tweets([{
        "text": text, "source_url": "https://x.com/TestaPolitikis/status/4444444444",
        "created_at": "2026-07-24T10:00:00+00:00", "lang": "lv",
    }], opponent_id=1)

    doc_ids2 = [r[0] for r in tmp_social_db.execute("SELECT id FROM documents").fetchall()]
    assert len(doc_ids2) == 1, "content_hash dup — no new doc"
    assert _junctions(tmp_social_db, doc_ids2[0]) == before, "different-url must not merge"


def test_store_tweets_relay_feed_cross_author_subject(tmp_social_db):
    """Relay fetch (opponent 3 = LTV Ziņas): a tweet authored by OtrsPolitikis
    surfaces via the relay feed. No link for the relay org itself, but the real
    first_party author still gets a 'subject' junction."""
    from src.social import _store_tweets
    tweets = [{
        "text": "Es aicinu valdību pārskatīt nodokļu politiku — mazie uzņēmumi cieš no birokrātijas.",
        "source_url": "https://x.com/OtrsPolitikis/status/5555555555",
        "created_at": "2026-07-24T10:00:00+00:00",
        "lang": "lv",
    }]
    _store_tweets(tweets, opponent_id=3)

    doc_id = tmp_social_db.execute("SELECT id FROM documents").fetchone()[0]
    assert _junctions(tmp_social_db, doc_id) == {(2, "subject")}


def test_store_tweets_relay_owned_author_no_subject(tmp_social_db):
    """Author handle owned by a RELAY account (LTVZinas) surfaced via opponent
    1's first_party feed → only (1,'mentioned'); the relay org never gets a
    'subject' junction this way (relay convention defers to text scan)."""
    from src.social import _store_tweets
    tweets = [{
        "text": "Raidījumā šovakar diskutēsim par nodokļu reformu un tās ietekmi uz mājsaimniecībām.",
        "source_url": "https://x.com/LTVZinas/status/6666666666",
        "created_at": "2026-07-24T10:00:00+00:00",
        "lang": "lv",
    }]
    _store_tweets(tweets, opponent_id=1)

    doc_id = tmp_social_db.execute("SELECT id FROM documents").fetchone()[0]
    assert _junctions(tmp_social_db, doc_id) == {(1, "mentioned")}


# --- 2026-08-18: first-party mention scan (BACKLOG § Matcher junction gap) ---
#
# Before this, a first_party tweet got its author junction inside _store_tweets
# and was then INVISIBLE to link_politicians_to_documents forever: that
# function's default branch selects only documents with NO junction rows at
# all (src/matcher.py, LEFT JOIN ... WHERE dp.document_id IS NULL). So another
# tracked politician named in the author's own text was never linked. Measured
# minimal pair: doc 80165 (Liepnieka own tweet) missed Rasima; doc 80150 (same
# text via the relay path) linked both.


def test_first_party_subject_doc_links_named_politician_as_mentioned(tmp_social_db):
    """The author keeps 'subject'; a DIFFERENT tracked politician named in the
    text gets 'mentioned' from the new scan."""
    from src.social import _store_tweets
    tweets = [{
        "text": "Šodien komisijā runāju par budžetu, un Andris Ozoliņš atkal iebilda pret grozījumiem.",
        "source_url": "https://x.com/TestaPolitikis/status/7777777777",
        "created_at": "2026-08-18T10:00:00+00:00",
        "lang": "lv",
    }]
    _store_tweets(tweets, opponent_id=1)

    doc_id = tmp_social_db.execute("SELECT id FROM documents").fetchone()[0]
    assert _junctions(tmp_social_db, doc_id) == {(1, "subject"), (4, "mentioned")}


def test_first_party_mention_scan_never_assigns_subject(tmp_social_db):
    """Hard invariant: this path may only ever write role='mentioned'.

    The text names ONLY politician 4, so match_politicians() itself hands back
    role='subject' for him (first/highest-count match). The scan must discard
    that role, not pass it through — otherwise the extractor queue would treat
    a mentioned person as a speaker.
    """
    from src.matcher import match_politicians
    from src.social import _store_tweets
    text = "Ozoliņam vajadzētu paskaidrot, kāpēc viņš mainīja nostāju par nodokļu reformu."

    assert match_politicians(text) == [(4, "subject")], (
        "precondition: the matcher's own role for this text is 'subject'"
    )

    _store_tweets([{
        "text": text,
        "source_url": "https://x.com/TestaPolitikis/status/8888888888",
        "created_at": "2026-08-18T11:00:00+00:00",
        "lang": "lv",
    }], opponent_id=1)

    doc_id = tmp_social_db.execute("SELECT id FROM documents").fetchone()[0]
    subjects = {pid for pid, role in _junctions(tmp_social_db, doc_id) if role == "subject"}
    assert subjects == {1}, f"only the author may be 'subject', got {subjects}"
    assert (4, "mentioned") in _junctions(tmp_social_db, doc_id)


def test_first_party_mention_scan_does_not_duplicate_author(tmp_social_db):
    """The author names HIMSELF in the text (third-person, quote of his own
    handle/name). document_politicians' PK is (document_id, politician_id,
    role), so a naive scan would add a SECOND row (1,'mentioned') beside
    (1,'subject') — the author must be excluded from the scan."""
    from src.social import _store_tweets
    tweets = [{
        "text": "Testa Politiķis šodien iesniedza priekšlikumu par veselības budžeta palielināšanu.",
        "source_url": "https://x.com/TestaPolitikis/status/9999999991",
        "created_at": "2026-08-18T12:00:00+00:00",
        "lang": "lv",
    }]
    _store_tweets(tweets, opponent_id=1)

    doc_id = tmp_social_db.execute("SELECT id FROM documents").fetchone()[0]
    assert _junctions(tmp_social_db, doc_id) == {(1, "subject")}


def test_first_party_mention_scan_does_not_demote_cross_feed_author(tmp_social_db):
    """A tweet authored by politician 2 surfacing via politician 1's feed and
    naming politician 4: author 2 stays 'subject', fetch owner 1 stays
    'mentioned', 4 is added as 'mentioned' — no duplicate role rows."""
    from src.social import _store_tweets
    tweets = [{
        "text": "Es aicinu valdību pārskatīt nodokļus, un Andris Ozoliņš to pašu prasīja komisijā.",
        "source_url": "https://x.com/OtrsPolitikis/status/9999999992",
        "created_at": "2026-08-18T13:00:00+00:00",
        "lang": "lv",
    }]
    _store_tweets(tweets, opponent_id=1)

    doc_id = tmp_social_db.execute("SELECT id FROM documents").fetchone()[0]
    assert _junctions(tmp_social_db, doc_id) == {
        (2, "subject"), (1, "mentioned"), (4, "mentioned"),
    }


def test_relay_feed_still_defers_to_link_politicians(tmp_social_db):
    """Scope lock: the new scan runs for first_party fetches only. A relay
    fetch keeps its existing contract — no scan here, mentions are assigned
    later by link_politicians_to_documents (the RSS-shaped path)."""
    from src.social import _store_tweets
    tweets = [{
        "text": "Raidījumā šovakar par nodokļu reformu diskutēs deputāts Andris Ozoliņš un eksperti.",
        "source_url": "https://x.com/LTVZinas/status/9999999993",
        "created_at": "2026-08-18T14:00:00+00:00",
        "lang": "lv",
    }]
    _store_tweets(tweets, opponent_id=3)

    doc_id = tmp_social_db.execute("SELECT id FROM documents").fetchone()[0]
    assert _junctions(tmp_social_db, doc_id) == set(), (
        "relay path must leave the document unlinked for the later text scan"
    )
