"""One X batch looks up each account once, not once per timeline.

Failure this names: every account cost two `get_user_by_screen_name` requests
(tweets, then replies), ~175 needless requests per run. The saving must not lose
replies when the first lookup failed: only a successful lookup may be reused.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

from src import x_scraper


def _tweet(tweet_id: str, handle: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=tweet_id, full_text=f"{handle}: teksts", text=None, retweeted_tweet=None,
        user=SimpleNamespace(screen_name=handle),
        created_at_datetime=datetime(2026, 11, 4, tzinfo=timezone.utc), lang="lv",
    )


def test_batch_looks_up_each_account_once_and_keeps_both_timelines(monkeypatch):
    lookups: list[str] = []

    class Client:
        async def get_user_by_screen_name(self, handle):
            lookups.append(handle)
            if handle == "pirmoreiz_krit" and lookups.count(handle) == 1:
                raise RuntimeError("transient lookup failure")
            return SimpleNamespace(id=handle, statuses_count=1)

        async def get_user_tweets(self, user_id=None, tweet_type=None, count=None):
            suffix = "2" if tweet_type == "Replies" else "1"
            return [_tweet(f"{len(user_id)}{suffix}", user_id)]

    class Pool:
        slot_count = 1

        def get_next_slot(self):
            return 0

        def get_client(self, slot):
            return Client()

    async def fake_get_pool():
        return Pool()

    monkeypatch.setattr(x_scraper, "get_pool", fake_get_pool)
    x_scraper._replies_broken_slots.clear()
    accounts = [
        {"handle": "viens", "opponent_id": 1},
        {"handle": "divi", "opponent_id": 2},
        {"handle": "pirmoreiz_krit", "opponent_id": 3},
    ]

    posts = asyncio.run(x_scraper.fetch_all_x_accounts(accounts, delay=0))

    assert lookups.count("viens") == 1
    assert lookups.count("divi") == 1
    assert len(posts[1]) == 2 and len(posts[2]) == 2  # tweet + reply each
    # The failed lookup is retried for replies, so those replies are not lost.
    assert lookups.count("pirmoreiz_krit") == 2
    assert len(posts[3]) == 1
