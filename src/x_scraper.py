"""
Twikit-based X/Twitter scraper.

Auth flow:
1. Pool loads cookies from data/x_cookies/{slot}.json (managed by XClientPool)
2. Rate-limited slots are rotated automatically

Usage:
    from src.x_scraper import fetch_user_tweets, fetch_user_replies
    tweets = await fetch_user_tweets("aseradens", limit=20)
    replies = await fetch_user_replies("aseradens", limit=10)
"""
import asyncio
import logging
import re
import time
from datetime import datetime

from twikit.errors import (
    NotFound,
    TooManyRequests,
    UserNotFound,
    UserUnavailable,
    TwitterException,
)

from src.x_pool import (
    TRANSACTION_KEY_ATTEMPTS,
    get_pool,
    reset_pool,
    reset_transaction_key,
)

logger = logging.getLogger(__name__)

REQUEST_DELAY = 2  # seconds between requests
MAX_RETRIES = 2  # kept for backward compat

# Per-slot replies-endpoint health. A slot returning 404 on the with_replies
# timeline is added here and skipped on subsequent calls; other slots keep
# working. Cleared by reset_replies_flag / reset_client.
#
# 2026-07-25: a slot only lands here after transaction-key repair has failed
# TRANSACTION_KEY_ATTEMPTS times. Most 404s on this endpoint are a bad
# transaction key rather than a dead slot (see
# `src.x_pool.reset_transaction_key`), and condemning the slot for the rest of
# the process cost us the account's replies for a whole ingest run.
_replies_broken_slots: set[int] = set()


async def _replies_with_key_repair(client, user_id: str, count: int):
    """Fetch the with_replies timeline, rebuilding the transaction key on 404.

    Returns the twikit result, or None when every repair attempt still 404s —
    only then is the slot genuinely unusable for this endpoint. Any other
    exception propagates to the caller's existing handling (rate limits,
    unexpected errors), because those are not key problems.
    """
    for attempt in range(1, TRANSACTION_KEY_ATTEMPTS + 1):
        try:
            return await client.get_user_tweets(
                user_id=user_id, tweet_type="Replies", count=count)
        except (NotFound, TwitterException) as e:
            if isinstance(e, TwitterException) and not isinstance(e, NotFound):
                if "404" not in str(e):
                    raise
            if attempt == TRANSACTION_KEY_ATTEMPTS:
                return None
            if not reset_transaction_key(client):
                return None
            logger.info(
                "replies 404 — rebuilding transaction key (attempt %d/%d)",
                attempt, TRANSACTION_KEY_ATTEMPTS,
            )
    return None


def _tweet_text(tweet) -> str:
    """Tweet body, with pure retweets expanded past X's legacy 140-char cut.

    A retweet's own `full_text` is the legacy truncated form — `RT @user: …`
    capped at 140 characters. Measured 2026-07-24: of 110 stored RT documents,
    74 were exactly 140 chars and 88 ended in an ellipsis, while ordinary
    tweets from the same day ran to 4410. The cost is not extraction (a bare
    retweet is nobody's first-party position anyway) but linkage:
    `link_politicians_to_documents` text-scans `content`, so a politician
    named only past the cut is never linked — a silent coverage gap.

    twikit exposes the original as `tweet.retweeted_tweet`, so we rebuild
    `RT @handle: <full original>`. The `RT @` prefix is load-bearing —
    `src/render/x.py` and `src/render/parties.py` detect retweets by it.
    """
    text = tweet.full_text or tweet.text or ""
    try:
        original = tweet.retweeted_tweet
    except Exception:  # twikit payload drift — keep the truncated text
        return text
    if original is None:
        return text

    full = (original.full_text or original.text or "").strip()
    if not full:
        return text

    handle = original.user.screen_name if original.user else None
    if not handle:
        match = re.match(r"RT @(\w+):", text)
        handle = match.group(1) if match else None
    return f"RT @{handle}: {full}" if handle else full


def _normalize_tweet(tweet) -> dict:
    """Convert a twikit Tweet object to a flat dict matching our pipeline format."""
    handle = tweet.user.screen_name if tweet.user else "unknown"
    created = tweet.created_at_datetime
    return {
        "id": str(tweet.id),
        "text": _tweet_text(tweet),
        "created_at": created.isoformat() if isinstance(created, datetime) else str(created) if created else None,
        "platform": "twitter",
        "lang": getattr(tweet, "lang", None),
        "reply_count": getattr(tweet, "reply_count", 0) or 0,
        "retweet_count": getattr(tweet, "retweet_count", 0) or 0,
        "favorite_count": getattr(tweet, "favorite_count", 0) or 0,
        "source_url": f"https://x.com/{handle}/status/{tweet.id}",
    }


def reset_client():
    """Reset cached client (backward compat wrapper). Delegates to reset_pool()."""
    reset_pool()
    _replies_broken_slots.clear()


def reset_replies_flag():
    """Re-enable replies endpoint on all slots after prior 404s disabled some."""
    _replies_broken_slots.clear()


async def fetch_user_tweets(handle: str, since_id: str | None = None,
                            limit: int = 20) -> list[dict]:
    """Fetch recent tweets for a user by handle. Rotates pool slots on rate limit."""
    pool = await get_pool()

    for _attempt in range(pool.slot_count + 1):
        try:
            slot = pool.get_next_slot()
            client = pool.get_client(slot)
        except RuntimeError:
            logger.warning("fetch_user_tweets(@%s): all pool slots exhausted", handle)
            return []

        try:
            user = await client.get_user_by_screen_name(handle)
        except (UserNotFound, UserUnavailable) as e:
            logger.warning("fetch_user_tweets: @%s — %s", handle, e)
            return []
        except TooManyRequests as e:
            reset_time = e.rate_limit_reset if e.rate_limit_reset else time.time() + 60
            pool.report_rate_limit(slot, reset_time + 2)
            logger.warning("fetch_user_tweets(@%s): slot %d rate-limited, trying next", handle, slot)
            continue
        except Exception:
            logger.exception("fetch_user_tweets: @%s lookup error", handle)
            return []

        try:
            result = await client.get_user_tweets(
                user_id=user.id, tweet_type="Tweets", count=min(limit, 40))
        except TooManyRequests as e:
            reset_time = e.rate_limit_reset if e.rate_limit_reset else time.time() + 60
            pool.report_rate_limit(slot, reset_time + 2)
            logger.warning("fetch_user_tweets(@%s): slot %d rate-limited on tweets, trying next", handle, slot)
            continue
        except TwitterException:
            logger.exception("fetch_user_tweets: API error for @%s", handle)
            return []
        except Exception as e:
            logger.exception("fetch_user_tweets: unexpected error for @%s — %s", handle, type(e).__name__)
            return []

        tweets = []
        if result:
            for tweet in result:
                normalized = _normalize_tweet(tweet)
                if since_id and normalized["id"] <= since_id:
                    continue
                tweets.append(normalized)
                if len(tweets) >= limit:
                    break
        return tweets

    logger.warning("fetch_user_tweets(@%s): exhausted all slots", handle)
    return []


async def fetch_tweet_by_id(tweet_id: str) -> dict | None:
    """Fetch a single tweet by ID, normalized to our pipeline shape.

    Uses get_tweets_by_ids (the batch endpoint) instead of get_tweet_by_id
    because the latter parses TweetDetail timeline entries through find_dict()
    which type-confuses User objects in conversation threads with Tweet
    results — KeyError 'user_results' on the first reply with a participant.
    Batch endpoint returns flat tweet results, no thread wrapper, no confusion.
    """
    pool = await get_pool()
    for _attempt in range(pool.slot_count + 1):
        try:
            slot = pool.get_next_slot()
        except RuntimeError:
            logger.warning("fetch_tweet_by_id(%s): all pool slots exhausted", tweet_id)
            return None
        client = pool.get_client(slot)
        try:
            tweets = await client.get_tweets_by_ids([tweet_id])
        except TooManyRequests as e:
            reset_time = e.rate_limit_reset if e.rate_limit_reset else time.time() + 60
            pool.report_rate_limit(slot, reset_time + 2)
            logger.warning("fetch_tweet_by_id(%s): slot %d rate-limited, trying next", tweet_id, slot)
            continue
        except (NotFound, UserNotFound, UserUnavailable) as e:
            logger.warning("fetch_tweet_by_id(%s): %s", tweet_id, e)
            return None
        except TwitterException:
            logger.exception("fetch_tweet_by_id(%s): API error", tweet_id)
            return None
        except Exception as e:
            logger.exception("fetch_tweet_by_id(%s): unexpected error — %s", tweet_id, type(e).__name__)
            return None
        first = tweets[0] if tweets else None
        return _normalize_tweet(first) if first is not None else None
    return None


async def fetch_tweets_by_ids(tweet_ids: list[str]) -> dict[str, dict]:
    """Fetch many tweets in one request, keyed by the ids we ASKED for.

    X's ``TweetResultsByRestIds`` accepts ~100 ids per call and answers with a
    position-aligned list carrying ``None`` where a tweet is deleted, private
    or suspended. Measured 2026-07-25 on live data: 100 ids returned in ~1s,
    and a deliberately bogus id came back as ``None`` in its own slot rather
    than shortening the list.

    That shape is a data-corruption trap. Zipping the response against the
    request — or mapping by position without checking — writes one account's
    text into another account's document as soon as a single tweet in the
    batch has been deleted. So every result is verified against the id it is
    supposed to answer, and anything unexpected is dropped rather than stored:
    a wrong id in the response is a bug signal, not content.

    Returns ``{tweet_id: normalized_tweet_dict}`` containing only ids that
    came back intact. Callers must treat a missing key as "unavailable" and
    leave whatever they already have alone.
    """
    if not tweet_ids:
        return {}

    pool = await get_pool()
    for _attempt in range(pool.slot_count + 1):
        try:
            slot = pool.get_next_slot()
        except RuntimeError:
            logger.warning("fetch_tweets_by_ids: all pool slots exhausted")
            return {}
        client = pool.get_client(slot)
        try:
            tweets = await client.get_tweets_by_ids(tweet_ids)
        except TooManyRequests as e:
            reset_time = e.rate_limit_reset if e.rate_limit_reset else time.time() + 60
            pool.report_rate_limit(slot, reset_time + 2)
            logger.warning("fetch_tweets_by_ids: slot %d rate-limited, trying next", slot)
            continue
        except (NotFound, UserNotFound, UserUnavailable) as e:
            logger.warning("fetch_tweets_by_ids: %s", e)
            return {}
        except TwitterException:
            logger.exception("fetch_tweets_by_ids: API error")
            return {}
        except Exception as e:
            logger.exception(
                "fetch_tweets_by_ids: unexpected error — %s", type(e).__name__)
            return {}

        requested = set(tweet_ids)
        out: dict[str, dict] = {}
        for tweet in tweets or []:
            if tweet is None:
                continue
            got = str(getattr(tweet, "id", "") or "")
            if got not in requested:
                logger.warning(
                    "fetch_tweets_by_ids: response carried unrequested id %s — dropped",
                    got)
                continue
            out[got] = _normalize_tweet(tweet)
        return out
    return {}


async def fetch_user_replies(handle: str, limit: int = 10) -> list[dict]:
    """Fetch recent replies by a user. Skips slots whose replies endpoint 404s.

    Status 2026-05-08+: real TID restored via twikit Patch 5 (PR #410
    two-stage ondemand.s.js parser). UserTweetsAndReplies endpoint accepts
    requests again; `_replies_broken_slots` should stay empty under normal
    operation. The slot-skip mechanism remains as a safety net in case X
    drifts the format again. See wiki/operations/twikit-notes.md § 2026-05-08
    and wiki/CHANGELOG.md § 2026-05-08.
    """
    pool = await get_pool()

    if len(_replies_broken_slots) >= pool.slot_count:
        return []

    for _attempt in range(pool.slot_count + 1):
        try:
            slot = pool.get_next_slot()
            client = pool.get_client(slot)
        except RuntimeError:
            logger.warning("fetch_user_replies(@%s): all pool slots exhausted", handle)
            return []

        if slot in _replies_broken_slots:
            continue

        # User lookup
        try:
            user = await client.get_user_by_screen_name(handle)
        except (UserNotFound, UserUnavailable) as e:
            logger.warning("fetch_user_replies: @%s — %s", handle, e)
            return []
        except TooManyRequests as e:
            reset_time = e.rate_limit_reset if e.rate_limit_reset else time.time() + 60
            pool.report_rate_limit(slot, reset_time + 2)
            logger.warning("fetch_user_replies(@%s): slot %d rate-limited on lookup, trying next", handle, slot)
            continue
        except Exception:
            logger.exception("fetch_user_replies: @%s lookup error", handle)
            return []

        # Replies fetch with endpoint health detection. A 404 here is usually a
        # bad transaction key, not a dead slot, so try rebuilding the key
        # before condemning the slot for the rest of the process.
        try:
            result = await _replies_with_key_repair(
                client, user.id, min(limit, 40))
        except TooManyRequests as e:
            reset_time = e.rate_limit_reset if e.rate_limit_reset else time.time() + 60
            pool.report_rate_limit(slot, reset_time + 2)
            logger.warning("fetch_user_replies(@%s): slot %d rate-limited on replies, trying next", handle, slot)
            continue
        except TwitterException:
            logger.exception("fetch_user_replies: API error for @%s", handle)
            return []
        except Exception as e:
            logger.exception("fetch_user_replies: unexpected error for @%s — %s", handle, type(e).__name__)
            return []

        if result is None:
            logger.warning(
                "fetch_user_replies(@%s): slot %d still 404s after %d "
                "transaction-key rebuilds — marking slot as broken, trying next",
                handle, slot, TRANSACTION_KEY_ATTEMPTS,
            )
            _replies_broken_slots.add(slot)
            if len(_replies_broken_slots) >= pool.slot_count:
                return []
            continue

        replies = []
        if result:
            for tweet in result:
                replies.append(_normalize_tweet(tweet))
                if len(replies) >= limit:
                    break
        return replies

    logger.warning("fetch_user_replies(@%s): exhausted all slots", handle)
    return []


async def fetch_all_x_accounts(accounts: list[dict], delay: float = REQUEST_DELAY) -> dict[int, list[dict]]:
    """Fetch tweets + replies for a batch of social_accounts rows."""
    results = {}
    total = len(accounts)

    for i, account in enumerate(accounts, 1):
        handle = account["handle"]
        opponent_id = account["opponent_id"]
        since_id = account.get("last_post_id")

        logger.info("X fetch [%d/%d]: @%s (opponent_id=%d)", i, total, handle, opponent_id)

        try:
            tweets = await fetch_user_tweets(handle, since_id=since_id, limit=20)
            replies = await fetch_user_replies(handle, limit=10)
        except Exception as e:
            logger.exception("  @%s: failed (%s), skipping", handle, type(e).__name__)
            if i < total:
                await asyncio.sleep(delay)
            continue

        all_posts = tweets + replies
        if all_posts:
            results.setdefault(opponent_id, []).extend(all_posts)
            logger.info("  @%s: %d tweets, %d replies", handle, len(tweets), len(replies))
        else:
            logger.info("  @%s: no new posts", handle)

        if i < total:
            await asyncio.sleep(delay)

    return results
