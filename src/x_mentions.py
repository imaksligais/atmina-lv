"""
X/Twitter mentions monitor.

For each tracked politician we collect tweets that mention any tracked handle,
store them as documents with ``platform='x_mention'``, and let downstream
matchers link author/target relationships (see ``src/social.py::fetch_all_mentions``).

Two strategies are supported via a feature flag:

* ``search`` (default): ``SearchTimeline`` queries with OR-batched ``@handle``
  predicates. Captures mentions by *any* author, including untracked
  journalists and commentators. Higher reach, more sensitive to TID/feature-flag
  drift on the search endpoint (mitigated by a pre-flight slot-health guardrail).
* ``timeline``: per-politician ``UserTweets`` GraphQL fetch + textual
  ``@mention`` filter. Captures tracked-to-tracked interactions only. Lower
  reach, but very stable against X anti-bot drift (UserTweets is a lenient
  endpoint). Kept as the guardrail fallback and an opt-in strategy.

Strategy selection precedence:
    explicit ``strategy=`` kwarg  >  ``X_MENTIONS_STRATEGY`` env var  >  ``"search"``

**Historical context — why timeline-scan used to be the default:**
2026-04-29 X tightened ``x-client-transaction-id`` validation on
``SearchTimeline`` and ``UserTweetsAndReplies``. ``twikit`` 2.3.3 (with
``patch_twikit.py`` Patch 4 fallback) sent a stub TID that only the lenient
endpoints (``UserTweets``, ``UserByScreenName``) accepted; strict endpoints
returned 404 with empty body. Timeline-scan was the default from 2026-04-29
through 2026-06-12 as the workaround. 2026-05-08 Patch 5 (upstream
``d60/twikit#410``) restored a real TID — both strict endpoints work again.
After the 2026-06-10..06-12 A/B (0 errors, ~5–7× faster, production chain
verified) ``search`` became the default; ``timeline`` remains as the guardrail
fallback (see the slot-health probe below) and an opt-in strategy.

See ``wiki/operations/twikit-notes.md`` § 2026-05-08 for Patch 5 details and
``wiki/CHANGELOG.md`` § 2026-06-12 for the default-flip rationale.

Usage:
    from src.x_mentions import fetch_mentions

    # Default (search):
    mentions, errors = await fetch_mentions(handle_to_pid)

    # Force timeline strategy:
    mentions, errors = await fetch_mentions(handle_to_pid, strategy="timeline")

    # Or via env: export X_MENTIONS_STRATEGY=timeline
"""
import asyncio
import logging
import os
import time
from datetime import datetime

from twikit.errors import TooManyRequests, TwitterException

from src.x_pool import get_pool

logger = logging.getLogger(__name__)

# Which strategy the most recent ``fetch_mentions`` call actually EXECUTED,
# including a guardrail fallback (a ``search`` request that tripped the
# slot-health probe and ran ``timeline`` instead resolves to ``"timeline"``).
# ``None`` until the first run. Read by ``src/social.py`` to record the executed
# strategy in the ``mentions_fetch`` log details.
last_run_strategy: str | None = None

REQUEST_DELAY = 2.0  # seconds between per-politician fetches or per-query searches
DEFAULT_BATCH_SIZE = 1  # legacy alias kept for src.social.py total_queries calc
SEARCH_HANDLES_PER_BATCH = 8  # OR-batched handles per SearchTimeline query
SEARCH_COUNT_PER_QUERY = 50  # tweets per SearchTimeline query (max 50)

# Search-endpoint guardrail: SearchTimeline is the strict TID endpoint and slots
# degrade unpredictably under load (2026-05-16 ingest: 5/6 → 3/6 in one run). Below
# this many healthy slots, the dispatcher silently falls back to the timeline
# strategy rather than risk a silent stored=0 day. Skipped when pool.slot_count is
# already below the threshold — single-slot fake pools used in tests bypass probing.
SEARCH_MIN_HEALTHY_SLOTS = 4
SEARCH_PROBE_QUERY = "Latvija"  # cheap, broad query for the count=1 health probe
SEARCH_PROBE_TIMEOUT_S = 5.0


def _normalize_mention(tweet, handle_to_pid: dict[str, int]) -> dict:
    """Convert a twikit Tweet to a mention dict.

    Args:
        tweet: twikit Tweet object
        handle_to_pid: {handle: politician_id}

    Returns:
        Dict with: id, text, created_at, platform, lang, reply/retweet/favorite counts,
        source_url, mentioner_handle, mentioner_name, opponent_id, mention_target_ids
    """
    handle = tweet.user.screen_name if tweet.user else "unknown"
    display_name = tweet.user.name if tweet.user else "unknown"
    created = tweet.created_at_datetime
    text = tweet.full_text or tweet.text or ""

    mention_target_ids: list[int] = []
    text_lower = text.lower()
    for h, pid in handle_to_pid.items():
        if f"@{h.lower()}" in text_lower or f"@{h}" in text:
            mention_target_ids.append(pid)

    author_pid = handle_to_pid.get(handle)
    opponent_id = author_pid

    if author_pid and author_pid in mention_target_ids:
        mention_target_ids.remove(author_pid)

    return {
        "id": str(tweet.id),
        "text": text,
        "created_at": (
            created.isoformat() if isinstance(created, datetime)
            else (str(created) if created else None)
        ),
        "platform": "x_mention",
        "lang": getattr(tweet, "lang", None),
        "reply_count": getattr(tweet, "reply_count", 0) or 0,
        "retweet_count": getattr(tweet, "retweet_count", 0) or 0,
        "favorite_count": getattr(tweet, "favorite_count", 0) or 0,
        "source_url": f"https://x.com/{handle}/status/{tweet.id}",
        "mentioner_handle": handle,
        "mentioner_name": display_name,
        "opponent_id": opponent_id,
        "mention_target_ids": mention_target_ids,
    }


async def _resolve_handle(client, handle: str) -> str | None:
    """Look up a handle's user_id via working `get_user_by_screen_name`."""
    try:
        user = await client.get_user_by_screen_name(handle)
        return user.id
    except Exception as e:
        logger.warning("fetch_mentions: handle resolution failed for @%s (%s)", handle, e)
        return None


async def _fetch_mentions_via_timeline(
    handle_to_pid: dict[str, int],
    limit: int = 20,
    delay: float = REQUEST_DELAY,
) -> tuple[list[dict], int]:
    """Per-politician UserTweets timeline scan + textual `@mention` filter.

    Captures tracked-to-tracked interactions only. Lower reach but stable
    against anti-bot drift on the search endpoint.
    """
    pool = await get_pool()
    seen_ids: set[str] = set()
    all_mentions: list[dict] = []
    errors = 0

    handles = list(handle_to_pid.keys())
    handle_to_uid: dict[str, str] = {}
    for handle in handles:
        try:
            slot = pool.get_next_slot()
            client = pool.get_client(slot)
        except RuntimeError:
            logger.warning(
                "fetch_mentions: all pool slots exhausted during handle resolution"
            )
            errors += 1
            break
        uid = await _resolve_handle(client, handle)
        if uid is None:
            errors += 1
            continue
        handle_to_uid[handle] = uid

    for i, (handle, uid) in enumerate(handle_to_uid.items()):
        logger.info(
            "fetch_mentions[timeline]: scanning @%s [%d/%d]",
            handle, i + 1, len(handle_to_uid),
        )
        success = False
        for _retry in range(pool.slot_count):
            try:
                slot = pool.get_next_slot()
                client = pool.get_client(slot)
            except RuntimeError:
                logger.warning("fetch_mentions: all pool slots exhausted")
                errors += 1
                break

            try:
                tweets = await client.get_user_tweets(uid, "Tweets", count=min(limit, 40))
                success = True
                for tweet in tweets:
                    mention = _normalize_mention(tweet, handle_to_pid)
                    if mention["id"] in seen_ids:
                        continue
                    if not mention["mention_target_ids"]:
                        continue  # tweet doesn't @-mention any tracked politician
                    seen_ids.add(mention["id"])
                    all_mentions.append(mention)
                break
            except TooManyRequests as e:
                reset_time = e.rate_limit_reset if e.rate_limit_reset else time.time() + 60
                pool.report_rate_limit(slot, reset_time + 2)
                logger.warning(
                    "fetch_mentions: slot %d rate-limited on @%s, trying next",
                    slot, handle,
                )
                continue
            except TwitterException as e:
                logger.warning(
                    "fetch_mentions: slot %d API error on @%s (%s), trying next slot",
                    slot, handle, e,
                )
                continue
            except Exception:
                logger.exception(
                    "fetch_mentions: unexpected error fetching @%s", handle,
                )
                errors += 1
                break

        if not success:
            errors += 1

        if i < len(handle_to_uid) - 1 and delay > 0:
            await asyncio.sleep(delay)

    logger.info(
        "fetch_mentions[timeline]: %d unique mentions across %d politiķi, %d errors",
        len(all_mentions), len(handle_to_uid), errors,
    )
    return all_mentions, errors


async def _fetch_mentions_via_search(
    handle_to_pid: dict[str, int],
    limit: int = SEARCH_COUNT_PER_QUERY,
    batch_size: int = SEARCH_HANDLES_PER_BATCH,
    delay: float = REQUEST_DELAY,
) -> tuple[list[dict], int]:
    """OR-batched SearchTimeline queries — captures mentions by ANY author.

    Builds queries of the form ``"(@h1 OR @h2 OR ... OR @hN) -filter:retweets"``
    and pages results from the working ``search_tweet`` endpoint. Includes
    untracked-author mentions (journalists, commentators) at the cost of
    higher rate-limit pressure on the search endpoint.

    Args:
        limit: tweets per query (search_tweet `count`, capped at 50 by X)
        batch_size: tracked handles OR-batched per query (default 8)
    """
    pool = await get_pool()
    seen_ids: set[str] = set()
    all_mentions: list[dict] = []
    errors = 0

    handles = list(handle_to_pid.keys())
    batches = [
        handles[i:i + batch_size] for i in range(0, len(handles), batch_size)
    ]

    for i, batch_handles in enumerate(batches):
        # SearchTimeline syntax: '@h1 OR @h2 OR ...' returns tweets mentioning
        # any handle in the batch. `-filter:retweets` drops RT noise (retweets
        # of tracked-handle mentions tend to inflate counts without adding
        # signal).
        query = " OR ".join(f"@{h}" for h in batch_handles) + " -filter:retweets"
        logger.info(
            "fetch_mentions[search]: batch %d/%d (%d handles)",
            i + 1, len(batches), len(batch_handles),
        )
        success = False
        for _retry in range(pool.slot_count):
            try:
                slot = pool.get_next_slot()
                client = pool.get_client(slot)
            except RuntimeError:
                logger.warning("fetch_mentions: all pool slots exhausted")
                errors += 1
                break

            try:
                tweets = await client.search_tweet(
                    query, "Latest", count=min(limit, SEARCH_COUNT_PER_QUERY)
                )
                success = True
                for tweet in tweets:
                    mention = _normalize_mention(tweet, handle_to_pid)
                    if mention["id"] in seen_ids:
                        continue
                    if not mention["mention_target_ids"]:
                        continue  # query may surface false-positive substring matches
                    seen_ids.add(mention["id"])
                    all_mentions.append(mention)
                break
            except TooManyRequests as e:
                reset_time = e.rate_limit_reset if e.rate_limit_reset else time.time() + 60
                pool.report_rate_limit(slot, reset_time + 2)
                logger.warning(
                    "fetch_mentions: slot %d rate-limited on search batch %d, trying next",
                    slot, i,
                )
                continue
            except TwitterException as e:
                logger.warning(
                    "fetch_mentions: slot %d search error on batch %d (%s), trying next slot",
                    slot, i, e,
                )
                continue
            except Exception:
                logger.exception(
                    "fetch_mentions: unexpected error on search batch %d", i,
                )
                errors += 1
                break

        if not success:
            errors += 1

        if i < len(batches) - 1 and delay > 0:
            await asyncio.sleep(delay)

    logger.info(
        "fetch_mentions[search]: %d unique mentions from %d batches, %d errors",
        len(all_mentions), len(batches), errors,
    )
    return all_mentions, errors


def _resolve_strategy(strategy: str | None) -> str:
    if strategy is not None:
        return strategy.lower()
    return os.environ.get("X_MENTIONS_STRATEGY", "search").lower()


async def _probe_search_slot_health() -> int:
    """Count pool slots that currently respond to ``search_tweet``.

    SearchTimeline is the strict-TID endpoint; slots can degrade between runs
    (typically transient TID drift). A pre-flight probe lets the dispatcher
    decide whether to commit to a full ``search`` run or fall back to the more
    forgiving ``timeline`` strategy.

    Returns the count of slots that returned without raising within
    ``SEARCH_PROBE_TIMEOUT_S``. Uninitialized and rate-limited slots count as
    unhealthy.
    """
    pool = await get_pool()
    healthy = 0
    for slot in range(pool.slot_count):
        try:
            client = pool.get_client(slot)
        except RuntimeError:
            continue  # uninitialized — no cookies loaded
        try:
            await asyncio.wait_for(
                client.search_tweet(
                    SEARCH_PROBE_QUERY, "Latest", count=1,
                ),
                timeout=SEARCH_PROBE_TIMEOUT_S,
            )
            healthy += 1
        except Exception as e:
            logger.debug(
                "_probe_search_slot_health: slot %d unhealthy (%s)", slot, e,
            )
    return healthy


async def fetch_mentions(
    handle_to_pid: dict[str, int],
    limit: int = 20,
    batch_size: int | None = None,
    delay: float = REQUEST_DELAY,
    *,
    strategy: str | None = None,
) -> tuple[list[dict], int]:
    """Dispatch to the configured mentions-collection strategy.

    Strategy precedence: explicit ``strategy=`` kwarg > ``X_MENTIONS_STRATEGY``
    env var > ``"search"`` default.

    Args:
        handle_to_pid: {handle: politician_id} mapping
        limit: ``timeline``: tweets per politician (capped at 40);
               ``search``: tweets per query (capped at 50).
        batch_size: ``timeline``: ignored;
                    ``search``: handles per OR-batched query (default 8).
        delay: seconds between per-fetch units.
        strategy: ``"timeline"`` or ``"search"``. ``None`` reads env var.

    Returns:
        Tuple of (deduplicated mention dicts, error count).
    """
    if not handle_to_pid:
        return [], 0

    global last_run_strategy
    resolved = _resolve_strategy(strategy)
    if resolved == "search":
        # Pre-flight guardrail: probe slot health on the strict SearchTimeline
        # endpoint. Skipped when pool is smaller than the threshold (test fake
        # pools are slot_count=1). The committed get_pool() default is
        # slot_count=5, so it loads 1.json..5.json — five DISTINCT accounts.
        # RESOLVED 2026-06-14: the historical total=6 guardrail logs came from a
        # local pool that also loaded 6.json, which was a byte-identical DUPLICATE
        # of 2.json (@npm_run_feels) — the same account in two slots, zero
        # resilience gain and bot-risky. 6.json was moved out of the pool; the
        # pool stays 5 distinct and the committed default=5 is correct. Do NOT
        # raise the default to 6 unless a genuinely NEW 6th account is added.
        pool = await get_pool()
        if pool.slot_count >= SEARCH_MIN_HEALTHY_SLOTS:
            healthy = await _probe_search_slot_health()
            if healthy < SEARCH_MIN_HEALTHY_SLOTS:
                logger.warning(
                    "fetch_mentions: only %d/%d slots healthy on search_tweet "
                    "(need %d) — falling back to timeline strategy",
                    healthy, pool.slot_count, SEARCH_MIN_HEALTHY_SLOTS,
                )
                # Persist the trip so the operator dashboard can count
                # falls-to-timeline within the last 24h. The follow-up
                # timeline run still emits its own mentions_fetch row.
                from src.db import log_action
                log_action(
                    "mentions_fetch_guardrail",
                    status="tripped",
                    details={
                        "healthy": healthy,
                        "total": pool.slot_count,
                        "min_required": SEARCH_MIN_HEALTHY_SLOTS,
                        "fallback": "timeline",
                    },
                )
                last_run_strategy = "timeline"
                return await _fetch_mentions_via_timeline(
                    handle_to_pid, limit=limit, delay=delay,
                )
        last_run_strategy = "search"
        return await _fetch_mentions_via_search(
            handle_to_pid,
            limit=limit if limit != 20 else SEARCH_COUNT_PER_QUERY,
            batch_size=batch_size or SEARCH_HANDLES_PER_BATCH,
            delay=delay,
        )
    if resolved == "timeline":
        last_run_strategy = "timeline"
        return await _fetch_mentions_via_timeline(
            handle_to_pid, limit=limit, delay=delay,
        )
    raise ValueError(
        f"Unknown X_MENTIONS_STRATEGY: {resolved!r} (expected 'timeline' or 'search')"
    )
