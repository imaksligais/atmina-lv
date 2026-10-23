"""A STRICT-endpoint 404 must trigger a transaction-key rebuild, not a verdict.

A twikit Client derives its ``x-client-transaction-id`` key once, on its first
request, and caches it for life. Some bootstraps produce a key X rejects: the
STRICT endpoints (SearchTimeline, UserTweetsAndReplies) answer with an empty
404 while LENIENT ones never check it. Measured 2026-07-25 — an interleaved
round-robin had one slot's client fail 10/10 rounds over 75s while the other
four passed 10/10 in the same seconds, and a forced rebuild recovered the
failing client within 1-3 tries (3/3 reproductions).

Before this, both STRICT consumers treated that 404 as a slot verdict:
`fetch_user_replies` condemned the slot for the whole process, and the mentions
search-health probe counted it unhealthy, which could drop the pool under
SEARCH_MIN_HEALTHY_SLOTS and fall a whole run back to the timeline strategy.
See BACKLOG § twikit "BROKEN 2/4".
"""
from __future__ import annotations

import asyncio

import pytest
from twikit.errors import NotFound, TooManyRequests

from src import x_mentions, x_scraper
from src.x_pool import TRANSACTION_KEY_ATTEMPTS, reset_transaction_key


class FakeTransaction:
    def __init__(self):
        self.home_page_response = "a-cached-home-page"


class FakeClient:
    """Fails STRICT calls until its key has been rebuilt `heals_after` times."""

    def __init__(self, heals_after: int = 1):
        self.client_transaction = FakeTransaction()
        self.heals_after = heals_after
        self.rebuilds = 0
        self.strict_calls = 0

    def _strict(self):
        self.strict_calls += 1
        # twikit rebuilds the key lazily: a cleared home_page_response means the
        # NEXT request bootstraps a fresh one.
        if self.client_transaction.home_page_response is None:
            self.rebuilds += 1
            self.client_transaction.home_page_response = "rebuilt"
        if self.rebuilds < self.heals_after:
            raise NotFound('status: 404, message: ""')
        return ["result"]

    async def get_user_tweets(self, user_id=None, tweet_type=None, count=None):
        return self._strict()

    async def search_tweet(self, query, product, count=None):
        return self._strict()


def test_reset_transaction_key_clears_the_cached_bootstrap():
    client = FakeClient()
    assert reset_transaction_key(client) is True
    assert client.client_transaction.home_page_response is None


def test_reset_transaction_key_reports_when_twikit_internals_moved():
    """If twikit renames the attribute, callers must stop retrying a no-op."""

    class Moved:
        client_transaction = object()

    assert reset_transaction_key(Moved()) is False


# --- replies path -----------------------------------------------------------


def test_replies_recovers_after_one_rebuild():
    client = FakeClient(heals_after=1)

    result = asyncio.run(x_scraper._replies_with_key_repair(client, "42", 10))

    assert result == ["result"]
    assert client.rebuilds == 1


def test_replies_gives_up_after_the_attempt_budget():
    client = FakeClient(heals_after=99)

    result = asyncio.run(x_scraper._replies_with_key_repair(client, "42", 10))

    assert result is None
    assert client.strict_calls == TRANSACTION_KEY_ATTEMPTS


def test_replies_does_not_retry_when_repair_is_unavailable():
    """No point burning the budget rebuilding a key we cannot clear."""

    class Unrepairable(FakeClient):
        def __init__(self):
            super().__init__(heals_after=99)
            self.client_transaction = object()  # twikit internals moved

        def _strict(self):
            self.strict_calls += 1
            raise NotFound('status: 404, message: ""')

    client = Unrepairable()
    assert asyncio.run(x_scraper._replies_with_key_repair(client, "42", 10)) is None
    assert client.strict_calls == 1


def test_replies_propagates_rate_limit_untouched():
    """Rate limits are not key problems — the caller rotates slots for them."""

    class RateLimited(FakeClient):
        async def get_user_tweets(self, user_id=None, tweet_type=None, count=None):
            raise TooManyRequests("slow down")

    with pytest.raises(TooManyRequests):
        asyncio.run(x_scraper._replies_with_key_repair(RateLimited(), "42", 10))


# --- mentions search-health path --------------------------------------------


def test_search_probe_counts_a_repaired_slot_as_healthy():
    client = FakeClient(heals_after=2)

    assert asyncio.run(x_mentions._search_probe_with_key_repair(client, slot=3)) is True
    assert client.rebuilds == 2


def test_search_probe_reports_unhealthy_only_after_the_budget():
    client = FakeClient(heals_after=99)

    assert asyncio.run(x_mentions._search_probe_with_key_repair(client, slot=3)) is False
    assert client.strict_calls == TRANSACTION_KEY_ATTEMPTS
