"""X cookie pool slot health snapshot — feeds the slot-health panel.

Mirrors `scripts/probe_x_cookies.py`: per-slot probe across four GraphQL
endpoints (get_user, user_tweets, user_replies, search_tweet). The
SearchTimeline endpoint is the strict-TID one; ``_probe_search_slot_health``
in ``src.x_mentions`` already counts healthy search slots before each
``fetch_mentions`` run, so the count here is purely a UI mirror of that
guardrail.

Cache:
    Module-level dict cache with 60 s TTL. Each call within TTL returns the
    same snapshot; ``force=True`` bypasses it (Task 2.3 refresh button).
"""
from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Any

from src.x_pool import COOKIES_DIR

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 60
_SLOT_CACHE: dict[str, Any] = {"probed_at": None, "result": None}

ENDPOINTS = ("get_user", "user_tweets", "user_replies", "search_tweet")
SEARCH_MIN_HEALTHY_SLOTS = 4  # mirrors src.x_mentions.SEARCH_MIN_HEALTHY_SLOTS


def _list_slot_files() -> list[Path]:
    """Return cookie files ordered by slot id (numeric stem)."""
    try:
        return sorted(p for p in COOKIES_DIR.glob("*.json") if p.stem.isdigit())
    except OSError:
        return []


async def _probe_one(slot: int, cookie_path: Path) -> dict[str, Any]:
    """Probe a single cookie slot against 4 GraphQL endpoints.

    Mirrors `scripts/probe_x_cookies.py` but returns a structured dict
    (no print side-effects).
    """
    from twikit import Client

    result: dict[str, Any] = {
        "slot": slot,
        "file": cookie_path.name,
        "get_user": None,
        "user_tweets": None,
        "user_replies": None,
        "search_tweet": None,
        "error": None,
    }
    try:
        client = Client("en-US")
        client.load_cookies(str(cookie_path))

        try:
            user = await client.get_user_by_screen_name("AtminaLV")
            result["get_user"] = f"ok ({user.screen_name})"
            uid = user.id
        except Exception as e:
            result["get_user"] = f"FAIL: {type(e).__name__}"
            return result

        try:
            tweets = await client.get_user_tweets(uid, "Tweets", count=2)
            result["user_tweets"] = f"ok ({len(tweets)})"
        except Exception as e:
            result["user_tweets"] = f"FAIL: {type(e).__name__}"

        try:
            replies = await client.get_user_tweets(uid, "Replies", count=2)
            result["user_replies"] = f"ok ({len(replies)})"
        except Exception as e:
            result["user_replies"] = f"FAIL: {type(e).__name__}"

        try:
            search = await client.search_tweet("Latvija", "Latest", count=1)
            result["search_tweet"] = f"ok ({len(search)})"
        except Exception as e:
            result["search_tweet"] = f"FAIL: {type(e).__name__}"

    except Exception as e:
        result["error"] = f"{type(e).__name__}: {str(e)[:120]}"

    return result


async def _probe_all_async() -> list[dict[str, Any]]:
    """Probe every cookie file sequentially.

    Sequential — not gathered — to avoid hammering X with parallel auth
    flushes from the same IP. Each probe is small (~1-2 s); 6 slots ≈ 8 s.
    """
    results = []
    for idx, cookie_path in enumerate(_list_slot_files(), start=1):
        try:
            res = await _probe_one(idx, cookie_path)
        except Exception as e:  # pragma: no cover — defensive only
            logger.exception("probe failed for slot %d", idx)
            res = {
                "slot": idx,
                "file": cookie_path.name,
                **{e: None for e in ENDPOINTS},
                "error": f"{type(e).__name__}: {str(e)[:120]}",
            }
        results.append(res)
    return results


def probe_all_slots() -> list[dict[str, Any]]:
    """Sync wrapper around the async probe — tests monkeypatch this."""
    try:
        return asyncio.run(_probe_all_async())
    except RuntimeError:
        # Already inside an event loop (rare for Flask sync routes; handle
        # the edge case so a misconfigured caller doesn't crash the dashboard).
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_probe_all_async())
        finally:
            loop.close()


def _is_endpoint_healthy(value: str | None) -> bool:
    return bool(value) and not value.startswith("FAIL")


def get_slot_snapshot(force: bool = False) -> dict[str, Any]:
    """Return cached or fresh slot-health snapshot.

    Args:
        force: When True, bypass the 60 s cache and probe immediately. The
            Task 2.3 refresh button passes ``force=True``; the default route
            handler uses cached data so page loads stay <1 s.

    Returns:
        dict with keys: slots, probed_at (epoch float), age_seconds,
        healthy_search_count (slots where ``search_tweet`` is OK),
        total_slots, guardrail_min, guardrail_tripped (count < min).
    """
    now = time.time()
    cached_at = _SLOT_CACHE["probed_at"]
    if (
        not force
        and cached_at is not None
        and (now - cached_at) < _CACHE_TTL_SECONDS
        and _SLOT_CACHE["result"] is not None
    ):
        slots_list = _SLOT_CACHE["result"]
        probed_at = cached_at
    else:
        slots_list = probe_all_slots()
        _SLOT_CACHE["probed_at"] = now
        _SLOT_CACHE["result"] = slots_list
        probed_at = now

    healthy_search_count = sum(
        1 for s in slots_list if _is_endpoint_healthy(s.get("search_tweet"))
    )
    return {
        "slots": slots_list,
        "probed_at": probed_at,
        "age_seconds": int(now - probed_at),
        "healthy_search_count": healthy_search_count,
        "total_slots": len(slots_list),
        "guardrail_min": SEARCH_MIN_HEALTHY_SLOTS,
        "guardrail_tripped": healthy_search_count < SEARCH_MIN_HEALTHY_SLOTS,
    }
