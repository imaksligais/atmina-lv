"""Retweets must store the FULL original text, not X's legacy 140-char cut.

Measured 2026-07-24: 110 stored `RT @` documents, 74 of them exactly 140
characters, 88 ending in an ellipsis, maximum 144 — while ordinary tweets from
the same day reached 4410. The truncation is invisible in extraction (a bare
retweet is not a first-party position) but `link_politicians_to_documents`
text-scans `content`, so a politician named only past the cut never gets
linked. See BACKLOG § Retvītu saturs apraujas 140 rakstzīmēs.
"""
from __future__ import annotations

from datetime import datetime

from src.x_scraper import _normalize_tweet, _tweet_text


class FakeUser:
    def __init__(self, screen_name):
        self.screen_name = screen_name


class FakeTweet:
    """Minimal stand-in for a twikit Tweet."""

    def __init__(self, *, id="1", full_text="", user=None, retweeted_tweet=None,
                 lang="lv"):
        self.id = id
        self.full_text = full_text
        self.text = full_text
        self.user = user
        self.lang = lang
        self.created_at_datetime = datetime(2026, 7, 24, 12, 0, 0)
        self.reply_count = 0
        self.retweet_count = 0
        self.favorite_count = 0
        self._retweeted_tweet = retweeted_tweet

    @property
    def retweeted_tweet(self):
        return self._retweeted_tweet


LONG_ORIGINAL = (
    "Šodien Saeimā balsojām par grozījumiem, kas skar pašvaldību finansējumu. "
    "Aicinu kolēģi Jāni Bērziņu paskaidrot, kāpēc frakcija atturējās — šī daļa "
    "tekstā atrodas krietni pēc 140. rakstzīmes un tieši tāpēc līdz šim nekad "
    "nenonāca līdz teksta skenerim."
)


def test_plain_tweet_text_unchanged():
    tweet = FakeTweet(full_text="Vienkāršs tvīts bez retvīta.",
                      user=FakeUser("kaspars"))
    assert _tweet_text(tweet) == "Vienkāršs tvīts bez retvīta."


def test_retweet_expands_to_full_original_text():
    original = FakeTweet(full_text=LONG_ORIGINAL, user=FakeUser("autors"))
    truncated = "RT @autors: " + LONG_ORIGINAL[:120] + "…"
    retweet = FakeTweet(full_text=truncated, user=FakeUser("retvitotajs"),
                        retweeted_tweet=original)

    result = _tweet_text(retweet)

    assert result == f"RT @autors: {LONG_ORIGINAL}"
    # The whole point: past the legacy cut, and no ellipsis left behind.
    assert len(result) > 144
    assert "Jāni Bērziņu" in result
    assert not result.endswith("…")


def test_retweet_keeps_rt_prefix_for_downstream_readers():
    """`src/render/x.py` and `src/render/parties.py` detect retweets by the
    literal `RT @` prefix — expansion must not drop it."""
    original = FakeTweet(full_text="Oriģinālais teksts.", user=FakeUser("autors"))
    retweet = FakeTweet(full_text="RT @autors: Oriģinālais tek…",
                        user=FakeUser("retvitotajs"), retweeted_tweet=original)

    assert _tweet_text(retweet).startswith("RT @")


def test_retweet_without_original_user_recovers_handle_from_prefix():
    original = FakeTweet(full_text="Pilnais oriģināls.", user=None)
    retweet = FakeTweet(full_text="RT @autors: Pilnais orig…",
                        user=FakeUser("retvitotajs"), retweeted_tweet=original)

    assert _tweet_text(retweet) == "RT @autors: Pilnais oriģināls."


def test_empty_original_falls_back_to_stored_text():
    original = FakeTweet(full_text="", user=FakeUser("autors"))
    retweet = FakeTweet(full_text="RT @autors: kaut kas…",
                        user=FakeUser("retvitotajs"), retweeted_tweet=original)

    assert _tweet_text(retweet) == "RT @autors: kaut kas…"


def test_twikit_payload_drift_does_not_break_normalization():
    """`retweeted_tweet` parses raw payload internals; if X drifts the format
    we keep the truncated text rather than losing the tweet entirely."""

    class DriftingTweet(FakeTweet):
        @property
        def retweeted_tweet(self):
            raise KeyError("retweeted_status_result")

    tweet = DriftingTweet(full_text="RT @autors: saīsināts…",
                          user=FakeUser("retvitotajs"))
    assert _tweet_text(tweet) == "RT @autors: saīsināts…"


def test_normalize_tweet_uses_expanded_text_and_retweeter_source_url():
    """source_url stays the RETWEETER's status — that is the document we hold."""
    original = FakeTweet(full_text=LONG_ORIGINAL, user=FakeUser("autors"))
    retweet = FakeTweet(id="999", full_text="RT @autors: saīsināts…",
                        user=FakeUser("retvitotajs"), retweeted_tweet=original)

    normalized = _normalize_tweet(retweet)

    assert normalized["text"] == f"RT @autors: {LONG_ORIGINAL}"
    assert normalized["source_url"] == "https://x.com/retvitotajs/status/999"
