"""Tests for X/Twitter mentions monitor (search + timeline strategies).

After 2026-04-29 X tightened TID validation on `SearchTimeline`, so
`fetch_mentions` switched from OR-query search to per-politician
`get_user_tweets` timeline scan + text-filter. 2026-05-08 Patch 5 restored
SearchTimeline; after the 2026-06-10..06-12 A/B, ``search`` is the default
strategy. ``timeline`` remains the guardrail fallback and is opt-in via
``X_MENTIONS_STRATEGY=timeline`` env var or explicit ``strategy="timeline"``
kwarg.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from src import x_mentions


@pytest.fixture(autouse=True)
def _isolate_x_mentions_strategy(monkeypatch):
    """Don't inherit the operator's ambient ``X_MENTIONS_STRATEGY``.

    The operator may export ``X_MENTIONS_STRATEGY`` in the dev shell. Clearing
    it ensures every test starts from the ``search`` default; timeline-strategy
    tests opt in explicitly via a ``strategy="timeline"`` kwarg, and env-routing
    tests set the var themselves via ``setenv`` after this autouse fixture runs.
    """
    monkeypatch.delenv("X_MENTIONS_STRATEGY", raising=False)


def _fake_tweet(tid, screen_name, name, text):
    """Build a minimal twikit Tweet-like mock with the fields _normalize_mention reads."""
    tweet = MagicMock()
    tweet.id = tid
    tweet.full_text = text
    tweet.text = text
    tweet.created_at_datetime = None
    tweet.user = MagicMock()
    tweet.user.screen_name = screen_name
    tweet.user.name = name
    tweet.lang = "lv"
    tweet.reply_count = 0
    tweet.retweet_count = 0
    tweet.favorite_count = 0
    return tweet


def _fake_pool(client):
    pool = MagicMock()
    pool.slot_count = 1
    pool.get_next_slot.return_value = 0
    pool.get_client.return_value = client
    return pool


def test_normalize_mention_extracts_targets_from_text():
    """Subject @-mentions in tweet text become mention_target_ids."""
    tweet = _fake_tweet("100", "krisjaniskarins", "K Kariņš",
                        "Sveiki @evikasilina ko domājat?")
    out = x_mentions._normalize_mention(
        tweet, {"krisjaniskarins": 1, "evikasilina": 2}
    )
    assert out["mentioner_handle"] == "krisjaniskarins"
    assert out["opponent_id"] == 1
    assert out["mention_target_ids"] == [2]
    assert out["source_url"] == "https://x.com/krisjaniskarins/status/100"
    assert out["platform"] == "x_mention"


def test_normalize_mention_excludes_self_reference():
    """Author mentioning self is NOT a mention target — opponent_id only."""
    tweet = _fake_tweet("101", "krisjaniskarins", "K Kariņš",
                        "Esmu @KrisjanisKarins viedoklī par @evikasilina jautājumu")
    out = x_mentions._normalize_mention(
        tweet, {"krisjaniskarins": 1, "evikasilina": 2}
    )
    assert out["opponent_id"] == 1
    assert 1 not in out["mention_target_ids"]
    assert 2 in out["mention_target_ids"]


def test_normalize_mention_external_author_is_none_opponent():
    """Untracked author → opponent_id is None, just mention_target_ids set."""
    tweet = _fake_tweet("102", "random_journalist", "Random",
                        "@krisjaniskarins atbildi par @evikasilina viedokli!")
    out = x_mentions._normalize_mention(
        tweet, {"krisjaniskarins": 1, "evikasilina": 2}
    )
    assert out["opponent_id"] is None
    assert sorted(out["mention_target_ids"]) == [1, 2]


def test_fetch_mentions_uses_per_politician_timeline_scan(monkeypatch):
    """Strategy: for each handle, fetch their last N tweets via working UserTweets,
    filter for those mentioning ANY OTHER tracked handle. Reject SearchTimeline path."""
    fake_client = MagicMock()
    fake_client.get_user_by_screen_name = AsyncMock(side_effect=[
        MagicMock(id="UID_A"),  # krisjaniskarins
        MagicMock(id="UID_B"),  # evikasilina
    ])
    fake_client.get_user_tweets = AsyncMock(side_effect=[
        # first call (Tweets product) returns one tweet that mentions evikasilina
        [_fake_tweet("200", "krisjaniskarins", "K Kariņš",
                     "Sveiki @evikasilina ko domājat?")],
        # second call returns no tweets
        [],
    ])
    # timeline path must not touch search_tweet
    fake_client.search_tweet = AsyncMock(side_effect=AssertionError(
        "timeline path must not call search_tweet"
    ))

    fake_pool = _fake_pool(fake_client)
    monkeypatch.setattr(x_mentions, "get_pool", AsyncMock(return_value=fake_pool))

    handle_to_pid = {"krisjaniskarins": 1, "evikasilina": 2}
    mentions, errors = asyncio.run(
        x_mentions.fetch_mentions(handle_to_pid, limit=20, delay=0, strategy="timeline")
    )
    assert errors == 0
    assert len(mentions) == 1
    m = mentions[0]
    assert m["mentioner_handle"] == "krisjaniskarins"
    assert m["opponent_id"] == 1
    assert m["mention_target_ids"] == [2]
    # Verified search_tweet was not called
    fake_client.search_tweet.assert_not_called()


def test_fetch_mentions_skips_tweets_without_tracked_target(monkeypatch):
    """A tweet that mentions only untracked accounts is dropped."""
    fake_client = MagicMock()
    fake_client.get_user_by_screen_name = AsyncMock(return_value=MagicMock(id="UID_A"))
    fake_client.get_user_tweets = AsyncMock(return_value=[
        _fake_tweet("300", "krisjaniskarins", "K Kariņš",
                    "Sveiki @some_journalist ko domājat?"),
    ])
    fake_pool = _fake_pool(fake_client)
    monkeypatch.setattr(x_mentions, "get_pool", AsyncMock(return_value=fake_pool))

    mentions, errors = asyncio.run(
        x_mentions.fetch_mentions({"krisjaniskarins": 1}, limit=20, delay=0, strategy="timeline")
    )
    assert errors == 0
    assert mentions == []


def test_fetch_mentions_dedupes_across_politicians(monkeypatch):
    """If two handles fetch a tweet referencing both, store it once."""
    shared_tweet = _fake_tweet(
        "400", "krisjaniskarins", "K Kariņš",
        "@evikasilina @gunars_pred jautājums",
    )
    fake_client = MagicMock()
    fake_client.get_user_by_screen_name = AsyncMock(side_effect=[
        MagicMock(id="UID_A"),
        MagicMock(id="UID_B"),
        MagicMock(id="UID_C"),
    ])
    fake_client.get_user_tweets = AsyncMock(side_effect=[
        [shared_tweet],   # krisjaniskarins
        [shared_tweet],   # evikasilina (somehow surfaced same tweet, e.g. retweet path)
        [],
    ])
    fake_pool = _fake_pool(fake_client)
    monkeypatch.setattr(x_mentions, "get_pool", AsyncMock(return_value=fake_pool))

    mentions, errors = asyncio.run(
        x_mentions.fetch_mentions(
            {"krisjaniskarins": 1, "evikasilina": 2, "gunars_pred": 3},
            limit=20, delay=0, strategy="timeline",
        )
    )
    assert errors == 0
    assert len(mentions) == 1


def test_fetch_mentions_empty_handle_dict_returns_empty():
    mentions, errors = asyncio.run(x_mentions.fetch_mentions({}))
    assert mentions == []
    assert errors == 0


def test_fetch_mentions_default_strategy_is_search(monkeypatch):
    """No env, no kwarg → search is the default; timeline path is not touched.

    Uses a single-slot fake pool so the slot-health guardrail is skipped
    (slot_count < SEARCH_MIN_HEALTHY_SLOTS) and search runs directly.
    """
    fake_client = MagicMock()
    fake_client.search_tweet = AsyncMock(return_value=[])
    fake_client.get_user_tweets = AsyncMock(
        side_effect=AssertionError("default=search must skip timeline path")
    )
    fake_client.get_user_by_screen_name = AsyncMock(
        side_effect=AssertionError("default=search must not resolve handles")
    )
    fake_pool = _fake_pool(fake_client)
    monkeypatch.setattr(x_mentions, "get_pool", AsyncMock(return_value=fake_pool))

    asyncio.run(x_mentions.fetch_mentions({"alpha": 1}, delay=0))
    fake_client.get_user_tweets.assert_not_called()
    fake_client.search_tweet.assert_called_once()


def test_fetch_mentions_sets_last_run_strategy(monkeypatch):
    """``last_run_strategy`` records the strategy the last fetch executed."""
    # (a) search run
    search_client = MagicMock()
    search_client.search_tweet = AsyncMock(return_value=[])
    monkeypatch.setattr(
        x_mentions, "get_pool", AsyncMock(return_value=_fake_pool(search_client))
    )
    asyncio.run(x_mentions.fetch_mentions({"alpha": 1}, delay=0, strategy="search"))
    assert x_mentions.last_run_strategy == "search"

    # (b) explicit timeline run
    timeline_client = MagicMock()
    timeline_client.get_user_by_screen_name = AsyncMock(return_value=MagicMock(id="UID"))
    timeline_client.get_user_tweets = AsyncMock(return_value=[])
    monkeypatch.setattr(
        x_mentions, "get_pool", AsyncMock(return_value=_fake_pool(timeline_client))
    )
    asyncio.run(x_mentions.fetch_mentions({"alpha": 1}, delay=0, strategy="timeline"))
    assert x_mentions.last_run_strategy == "timeline"


# --- search strategy (default; timeline opt-in via env var or strategy= kwarg) ---


def test_fetch_mentions_search_strategy_dispatches_to_search_tweet(monkeypatch):
    """strategy='search' routes to SearchTimeline, NOT to per-politician timeline."""
    fake_client = MagicMock()
    fake_client.search_tweet = AsyncMock(return_value=[
        _fake_tweet("500", "random_journalist", "Random",
                    "@krisjaniskarins atbild par @evikasilina jautājumu"),
    ])
    # If anyone calls timeline-scan, fail loudly
    fake_client.get_user_tweets = AsyncMock(
        side_effect=AssertionError("search strategy must NOT call get_user_tweets")
    )
    fake_client.get_user_by_screen_name = AsyncMock(
        side_effect=AssertionError("search strategy must NOT resolve handles")
    )
    fake_pool = _fake_pool(fake_client)
    monkeypatch.setattr(x_mentions, "get_pool", AsyncMock(return_value=fake_pool))

    handle_to_pid = {"krisjaniskarins": 1, "evikasilina": 2}
    mentions, errors = asyncio.run(
        x_mentions.fetch_mentions(handle_to_pid, delay=0, strategy="search")
    )
    assert errors == 0
    assert len(mentions) == 1
    m = mentions[0]
    assert m["mentioner_handle"] == "random_journalist"
    assert m["opponent_id"] is None  # untracked author
    assert sorted(m["mention_target_ids"]) == [1, 2]
    fake_client.search_tweet.assert_called_once()


def test_fetch_mentions_search_or_batches_handles(monkeypatch):
    """OR-batched query format: '@h1 OR @h2 OR ... -filter:retweets'."""
    captured_queries: list[str] = []

    async def capture_search(query, product, count):
        captured_queries.append(query)
        return []

    fake_client = MagicMock()
    fake_client.search_tweet = AsyncMock(side_effect=capture_search)
    fake_pool = _fake_pool(fake_client)
    monkeypatch.setattr(x_mentions, "get_pool", AsyncMock(return_value=fake_pool))

    # 3 handles, batch_size=2 → 2 batches: [a, b] + [c]
    handle_to_pid = {"alpha": 1, "beta": 2, "gamma": 3}
    asyncio.run(
        x_mentions.fetch_mentions(
            handle_to_pid, delay=0, batch_size=2, strategy="search",
        )
    )
    assert len(captured_queries) == 2
    assert captured_queries[0] == "@alpha OR @beta -filter:retweets"
    assert captured_queries[1] == "@gamma -filter:retweets"


def test_fetch_mentions_search_dedupes_across_batches(monkeypatch):
    """Same tweet surfacing in two OR-batches is stored once."""
    shared = _fake_tweet(
        "600", "random_journalist", "Random",
        "@alpha @beta @gamma kopā",
    )
    fake_client = MagicMock()
    fake_client.search_tweet = AsyncMock(side_effect=[[shared], [shared]])
    fake_pool = _fake_pool(fake_client)
    monkeypatch.setattr(x_mentions, "get_pool", AsyncMock(return_value=fake_pool))

    handle_to_pid = {"alpha": 1, "beta": 2, "gamma": 3}
    mentions, errors = asyncio.run(
        x_mentions.fetch_mentions(
            handle_to_pid, delay=0, batch_size=2, strategy="search",
        )
    )
    assert errors == 0
    assert len(mentions) == 1
    assert sorted(mentions[0]["mention_target_ids"]) == [1, 2, 3]


def test_fetch_mentions_env_var_routes_strategy(monkeypatch):
    """X_MENTIONS_STRATEGY env var picks strategy when no explicit kwarg."""
    monkeypatch.setenv("X_MENTIONS_STRATEGY", "search")
    fake_client = MagicMock()
    fake_client.search_tweet = AsyncMock(return_value=[])
    fake_client.get_user_tweets = AsyncMock(
        side_effect=AssertionError("env=search must skip timeline path")
    )
    fake_client.get_user_by_screen_name = AsyncMock(
        side_effect=AssertionError("env=search must skip timeline path")
    )
    fake_pool = _fake_pool(fake_client)
    monkeypatch.setattr(x_mentions, "get_pool", AsyncMock(return_value=fake_pool))

    asyncio.run(x_mentions.fetch_mentions({"alpha": 1}, delay=0))
    fake_client.search_tweet.assert_called_once()


def test_fetch_mentions_explicit_strategy_overrides_env(monkeypatch):
    """Explicit strategy= kwarg wins over env var."""
    monkeypatch.setenv("X_MENTIONS_STRATEGY", "search")
    fake_client = MagicMock()
    # explicit strategy="timeline" must take timeline path despite env=search
    fake_client.get_user_by_screen_name = AsyncMock(return_value=MagicMock(id="UID"))
    fake_client.get_user_tweets = AsyncMock(return_value=[])
    fake_client.search_tweet = AsyncMock(
        side_effect=AssertionError("explicit strategy='timeline' must not call search")
    )
    fake_pool = _fake_pool(fake_client)
    monkeypatch.setattr(x_mentions, "get_pool", AsyncMock(return_value=fake_pool))

    asyncio.run(
        x_mentions.fetch_mentions({"alpha": 1}, delay=0, strategy="timeline")
    )
    fake_client.search_tweet.assert_not_called()
    fake_client.get_user_by_screen_name.assert_called()


def test_fetch_mentions_unknown_strategy_raises():
    with pytest.raises(ValueError, match="Unknown X_MENTIONS_STRATEGY"):
        asyncio.run(x_mentions.fetch_mentions({"a": 1}, strategy="invalid"))


# --- search-slot-health guardrail (production-scale pool, slot_count>=4) ---


def _fake_pool_multi(clients_by_slot: dict[int, MagicMock]) -> MagicMock:
    """Fake pool that returns specific clients per slot (test-only)."""
    pool = MagicMock()
    pool.slot_count = len(clients_by_slot)
    cursor = {"i": 0}

    def _next_slot():
        s = cursor["i"]
        cursor["i"] = (cursor["i"] + 1) % pool.slot_count
        return s

    pool.get_next_slot = _next_slot
    pool.get_client = lambda slot: clients_by_slot[slot]
    return pool


def test_fetch_mentions_search_falls_back_to_timeline_when_slots_unhealthy(monkeypatch):
    """Production-scale pool (6 slots), only 3 healthy on search_tweet → fallback."""
    healthy_tweet = _fake_tweet(
        "700", "krisjaniskarins", "K Kariņš", "Sveiki @evikasilina"
    )

    # 6 slots: 3 fail on search_tweet probe, 3 OK. All 6 OK on timeline path.
    clients = {}
    for slot in range(6):
        c = MagicMock()
        c.get_user_by_screen_name = AsyncMock(return_value=MagicMock(id=f"UID_{slot}"))
        c.get_user_tweets = AsyncMock(return_value=[healthy_tweet])
        if slot in (0, 2, 4):
            c.search_tweet = AsyncMock(
                side_effect=AssertionError(
                    "after fallback, search_tweet must NOT be called"
                )
            )
        else:
            # Probe will succeed, but search batches must also not be called
            # after the fallback decision.
            async def _probe_only(*args, **kwargs):
                return []
            c.search_tweet = AsyncMock(side_effect=_probe_only)
        clients[slot] = c
    # Make probe see slots 0,2,4 as broken
    for slot in (0, 2, 4):
        clients[slot].search_tweet = AsyncMock(
            side_effect=RuntimeError("status: 404, message: \"\"")
        )

    fake_pool = _fake_pool_multi(clients)
    monkeypatch.setattr(x_mentions, "get_pool", AsyncMock(return_value=fake_pool))

    # The fallback decision writes a 'mentions_fetch_guardrail' audit row via
    # log_action(), which opens the live DB. That side effect is incidental to
    # what this test asserts (the search→timeline switch), so stub it out —
    # otherwise the row insert hits the absent (gitignored) DB in CI. fetch_mentions
    # does `from src.db import log_action`, so patch it at the source module.
    monkeypatch.setattr("src.db.log_action", lambda *a, **k: None)

    mentions, errors = asyncio.run(
        x_mentions.fetch_mentions(
            {"krisjaniskarins": 1, "evikasilina": 2},
            delay=0, strategy="search",
        )
    )
    # Fallback executed → timeline path returned the seeded tweet
    assert errors == 0
    assert len(mentions) == 1
    assert mentions[0]["mentioner_handle"] == "krisjaniskarins"
    # Guardrail fallback ran timeline → executed strategy is "timeline"
    assert x_mentions.last_run_strategy == "timeline"
    # Search probe was attempted on every slot; non-probe search batches must
    # NOT have run — slots 0/2/4 have the AssertionError side_effect that the
    # probe call already consumed (their FIRST call is the probe), so any
    # later call would re-raise the RuntimeError; for slots 1/3/5 their FIRST
    # call returns []. No batch_size=8 OR-query should ever be issued.
    for slot in (1, 3, 5):
        # Exactly 1 call (the probe), no batches
        assert clients[slot].search_tweet.call_count == 1


def test_fetch_mentions_search_runs_when_enough_slots_healthy(monkeypatch):
    """Production-scale pool with 4+ healthy slots → search proceeds normally."""
    found = _fake_tweet(
        "701", "random_journalist", "Random",
        "@krisjaniskarins atbild par @evikasilina",
    )

    clients = {}
    for slot in range(6):
        c = MagicMock()
        # Timeline path must NOT be hit when search proceeds
        c.get_user_by_screen_name = AsyncMock(
            side_effect=AssertionError("search OK path must not resolve handles")
        )
        c.get_user_tweets = AsyncMock(
            side_effect=AssertionError("search OK path must not call get_user_tweets")
        )
        c.search_tweet = AsyncMock(return_value=[found])
        clients[slot] = c

    fake_pool = _fake_pool_multi(clients)
    monkeypatch.setattr(x_mentions, "get_pool", AsyncMock(return_value=fake_pool))

    mentions, errors = asyncio.run(
        x_mentions.fetch_mentions(
            {"krisjaniskarins": 1, "evikasilina": 2},
            delay=0, strategy="search",
        )
    )
    assert errors == 0
    assert len(mentions) == 1
    assert mentions[0]["mentioner_handle"] == "random_journalist"
