"""Retweet full-text backfill: batch fetch, targeted re-linking, in-place update.

The 2026-07-24 `_tweet_text()` fix is forward-only. History still holds 8910
truncated `RT @` documents whose politician linkage never saw the text past
X's legacy 140-char cut. See BACKLOG § Vēsturisko retvītu backfill.

Three things must hold, and each has bitten something before:

1. `fetch_tweets_by_ids` must map results to the ids it ASKED for. X returns a
   position-aligned list with `None` placeholders for deleted/protected
   tweets; a position-shifted or naively-zipped mapping would write one
   politician's tweet text into another politician's document — silent
   cross-contamination of exactly the kind CLAUDE.md § Silent success warns of.

2. `insert_document`'s update-in-place path is gated to `platform='web'`, so
   calling it for a tweet would INSERT A DUPLICATE rather than update. The
   backfill therefore updates the row directly and must keep `scraped_at`
   untouched — `routine._check_analysis` compares `documents.scraped_at`
   against `analyses.created_at`, so bumping it on 8910 historical rows would
   re-open thousands of politicians as "pending".

3. Re-linking must be scopeable to the docs actually updated.
"""
from __future__ import annotations

import asyncio

from datetime import datetime

from src.x_scraper import _tweet_text


class FakeUser:
    def __init__(self, screen_name):
        self.screen_name = screen_name


class FakeTweet:
    def __init__(self, *, id="1", full_text="", user=None, retweeted_tweet=None):
        self.id = id
        self.full_text = full_text
        self.text = full_text
        self.user = user
        self.lang = "lv"
        self.created_at_datetime = datetime(2026, 7, 24, 12, 0, 0)
        self.reply_count = 0
        self.retweet_count = 0
        self.favorite_count = 0
        self._retweeted_tweet = retweeted_tweet

    @property
    def retweeted_tweet(self):
        return self._retweeted_tweet


def _rt(tweet_id, handle, original_text):
    original = FakeTweet(id=f"orig{tweet_id}", full_text=original_text,
                         user=FakeUser(handle))
    return FakeTweet(id=tweet_id, full_text=f"RT @{handle}: {original_text[:100]}…",
                     user=FakeUser("retweeter"), retweeted_tweet=original)


class TestBatchFetchMapping:
    """`fetch_tweets_by_ids` keys results by tweet id, never by position."""

    def test_maps_by_id_with_none_placeholders(self, monkeypatch):
        from src import x_scraper

        asked = ["100", "200", "300"]
        # X returns position-aligned results; the middle tweet is gone.
        returned = [_rt("100", "alice", "Alpha " * 40), None,
                    _rt("300", "carol", "Gamma " * 40)]

        class FakeClient:
            async def get_tweets_by_ids(self, ids):
                assert ids == asked
                return returned

        class FakePool:
            slot_count = 1

            def get_next_slot(self):
                return 0

            def get_client(self, slot):
                return FakeClient()

            def report_rate_limit(self, slot, reset):
                raise AssertionError("no rate limit in this test")

        async def fake_pool():
            return FakePool()

        monkeypatch.setattr(x_scraper, "get_pool", fake_pool)

        out = asyncio.run(x_scraper.fetch_tweets_by_ids(asked))

        assert set(out) == {"100", "300"}, "deleted tweet must be absent, not shifted"
        assert "Alpha" in out["100"]["text"]
        assert "Gamma" in out["300"]["text"]

    def test_drops_result_whose_id_does_not_match_request(self, monkeypatch):
        """A response id we never asked for is a bug signal, not data."""
        from src import x_scraper

        class FakeClient:
            async def get_tweets_by_ids(self, ids):
                return [_rt("999", "mallory", "Wrong tweet " * 20)]

        class FakePool:
            slot_count = 1

            def get_next_slot(self):
                return 0

            def get_client(self, slot):
                return FakeClient()

        async def fake_pool():
            return FakePool()

        monkeypatch.setattr(x_scraper, "get_pool", fake_pool)

        out = asyncio.run(x_scraper.fetch_tweets_by_ids(["100"]))
        assert out == {}, "unrequested id must not be written under a requested key"

    def test_expands_retweet_to_full_original(self, monkeypatch):
        from src import x_scraper

        long_original = "Pilnais oriģināls ar politiķa vārdu Kulbergs " * 6
        tweet = _rt("100", "lsmlv", long_original)

        class FakeClient:
            async def get_tweets_by_ids(self, ids):
                return [tweet]

        class FakePool:
            slot_count = 1

            def get_next_slot(self):
                return 0

            def get_client(self, slot):
                return FakeClient()

        async def fake_pool():
            return FakePool()

        monkeypatch.setattr(x_scraper, "get_pool", fake_pool)

        out = asyncio.run(x_scraper.fetch_tweets_by_ids(["100"]))
        text = out["100"]["text"]
        assert text.startswith("RT @lsmlv: "), "RT @ prefix is load-bearing for render"
        assert "Kulbergs" in text
        assert len(text) > 140


class TestTweetTextStillExpands:
    """Guard the primitive the backfill leans on."""

    def test_rebuilds_full_text_from_retweeted_tweet(self):
        original = FakeTweet(id="o", full_text="A" * 500, user=FakeUser("src"))
        rt = FakeTweet(id="r", full_text="RT @src: " + "A" * 131,
                       user=FakeUser("mirror"), retweeted_tweet=original)
        assert len(_tweet_text(rt)) > 400


class TestTargetedRelinking:
    """`link_politicians_to_documents(doc_ids=[...])` ignores the time window."""

    def test_links_only_the_given_docs_regardless_of_age(self, tmp_path, monkeypatch):
        import src.db as db_mod
        from src import matcher

        db_file = tmp_path / "t.db"
        monkeypatch.setattr(db_mod, "DB_PATH", str(db_file))
        db_mod.init_db(str(db_file))
        db = db_mod.get_db(str(db_file))
        db.execute(
            "INSERT INTO tracked_politicians (id, name, name_forms, relationship_type) "
            "VALUES (1, 'Andris Kulbergs', ?, 'neutral')",
            ('["Andris Kulbergs", "Kulbergs"]',),
        )
        # Both docs are far outside any sane scraped_at window.
        for doc_id, content in (
            (10, "RT @lsmlv: garš teksts kurā minēts Andris Kulbergs un vēl daudz kas"),
            (11, "RT @lsmlv: cits teksts kurā arī minēts Andris Kulbergs bet to neskaram"),
        ):
            db.execute(
                "INSERT INTO documents (id, content, content_hash, platform, "
                "source_url, scraped_at, word_count) VALUES (?, ?, ?, 'twitter', ?, ?, ?)",
                (doc_id, content, f"h{doc_id}",
                 f"https://x.com/lsmlv/status/{doc_id}", "2026-01-01 00:00:00",
                 len(content.split())),
            )
        db.commit()
        db.close()

        monkeypatch.setattr(matcher, "get_db", lambda *a, **k: db_mod.get_db(str(db_file)))

        linked = matcher.link_politicians_to_documents(doc_ids=[10])

        assert 10 in linked, "explicitly requested doc must be linked despite its age"
        assert 11 not in linked, "doc outside the id list must be untouched"

        db = db_mod.get_db(str(db_file))
        rows = db.execute(
            "SELECT document_id FROM document_politicians ORDER BY document_id"
        ).fetchall()
        db.close()
        assert [r["document_id"] for r in rows] == [10]

    def test_empty_doc_ids_list_scans_nothing(self, tmp_path, monkeypatch):
        """`doc_ids=[]` means 'no documents', never 'fall back to the window'."""
        import src.db as db_mod
        from src import matcher

        db_file = tmp_path / "t.db"
        monkeypatch.setattr(db_mod, "DB_PATH", str(db_file))
        db_mod.init_db(str(db_file))
        db = db_mod.get_db(str(db_file))
        db.execute(
            "INSERT INTO tracked_politicians (id, name, name_forms, relationship_type) "
            "VALUES (1, 'Andris Kulbergs', ?, 'neutral')",
            ('["Andris Kulbergs", "Kulbergs"]',),
        )
        content = "RT @lsmlv: šodienas teksts kurā minēts Andris Kulbergs"
        db.execute(
            "INSERT INTO documents (id, content, content_hash, platform, source_url, "
            "scraped_at, word_count) VALUES (99, ?, 'h99', 'twitter', ?, ?, ?)",
            (content, "https://x.com/lsmlv/status/99", db_mod.now_lv(),
             len(content.split())),
        )
        db.commit()
        db.close()

        monkeypatch.setattr(matcher, "get_db", lambda *a, **k: db_mod.get_db(str(db_file)))

        assert matcher.link_politicians_to_documents(doc_ids=[]) == {}
