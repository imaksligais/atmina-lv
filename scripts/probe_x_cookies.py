"""Probe each x_cookies/{slot}.json against 4 X GraphQL endpoints.

Detects per-endpoint regressions early. As of 2026-04-29 we know:
  - get_user + UserTweets are LENIENT (accept Patch 4 stub TID)
  - SearchTimeline + UserTweetsAndReplies are STRICT (reject stub TID, return 404)

READ THIS BEFORE REFRESHING ANY COOKIE (2026-07-25). A STRICT 404 here usually
says NOTHING about the account or its cookies. Each twikit Client derives its
x-client-transaction-id key once, at bootstrap, and caches it for life; some
bootstraps produce a key X rejects, and then exactly those two STRICT endpoints
404 for that client only. The symptom therefore hops between slots as each run
builds fresh clients — which is what sent us chasing ct0 refreshes for weeks.
This probe now rebuilds the key and retries before reporting, so a slot that
still fails is a real finding. The "recovered after N rebuild(s)" note tells
you the bootstrap was the problem, not the credentials. Full evidence chain:
`src.x_pool.reset_transaction_key` + BACKLOG § twikit "BROKEN 2/4".

Usage: python scripts/probe_x_cookies.py
"""
import asyncio
import sys
from pathlib import Path

from twikit import Client

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.x_pool import TRANSACTION_KEY_ATTEMPTS, reset_transaction_key  # noqa: E402


COOKIES_DIR = Path(__file__).resolve().parent.parent / "data" / "x_cookies"


async def probe_one(slot: int, cookie_path: Path) -> dict:
    res = {
        "slot": slot,
        "file": cookie_path.name,
        "get_user": None,
        "user_tweets": None,
        "user_replies": None,
        "search_tweet": None,
        "error": None,
        "key_rebuilds": 0,
    }
    try:
        client = Client("en-US")
        client.load_cookies(str(cookie_path))

        try:
            user = await client.get_user_by_screen_name("AtminaLV")
            res["get_user"] = f"ok ({user.screen_name})"
            uid = user.id
        except Exception as e:
            res["get_user"] = f"FAIL: {type(e).__name__}: {str(e)[:100]}"
            return res

        try:
            tweets = await client.get_user_tweets(uid, "Tweets", count=2)
            res["user_tweets"] = f"ok ({len(tweets)})"
        except Exception as e:
            res["user_tweets"] = f"FAIL: {type(e).__name__}: {str(e)[:100]}"

        async def strict(label, call):
            """Run a STRICT call, rebuilding the transaction key between 404s."""
            for attempt in range(1, TRANSACTION_KEY_ATTEMPTS + 1):
                try:
                    return await call()
                except Exception as e:
                    last = f"FAIL: {type(e).__name__}: {str(e)[:100]}"
                    if attempt == TRANSACTION_KEY_ATTEMPTS or not reset_transaction_key(client):
                        res[label] = last
                        return None
                    res["key_rebuilds"] += 1
            return None

        try:
            replies = await strict(
                "user_replies", lambda: client.get_user_tweets(uid, "Replies", count=2))
            if replies is not None:
                res["user_replies"] = f"ok ({len(replies)})"
        except Exception as e:
            res["user_replies"] = f"FAIL: {type(e).__name__}: {str(e)[:100]}"

        search = await strict(
            "search_tweet", lambda: client.search_tweet("Latvija", "Latest", count=1))
        if search is not None:
            res["search_tweet"] = f"ok ({len(search)})"

    except Exception as e:
        res["error"] = f"{type(e).__name__}: {str(e)[:120]}"

    return res


_ENDPOINT_KEYS = ("get_user", "user_tweets", "user_replies", "search_tweet")


def _slot_status(res: dict) -> tuple[str, int, int]:
    """(marker, probed, failed) — [OK] only when all 4 endpoints ran with 0 FAIL.

    A slot whose probes never ran (bootstrap/load_cookies exception leaves every
    endpoint None) or ran only partially is NOT_PROBED, never OK.
    """
    probed = sum(1 for k in _ENDPOINT_KEYS if res.get(k) is not None)
    failed = sum(1 for k in _ENDPOINT_KEYS if res.get(k) and "FAIL" in res[k])
    if probed == 4 and failed == 0:
        marker = "OK"
    elif probed < 4:
        marker = f"NOT_PROBED ({probed}/4)"
    else:
        marker = f"BROKEN ({failed}/4)"
    return marker, probed, failed


async def main() -> None:
    files = sorted(p for p in COOKIES_DIR.glob("*.json") if p.stem.isdigit())
    if not files:
        print(f"No cookie files in {COOKIES_DIR}")
        sys.exit(1)

    print(f"Probing {len(files)} cookie file(s) across 4 endpoints...\n")
    for i, p in enumerate(files, 1):
        res = await probe_one(i, p)
        marker, probed, failed = _slot_status(res)
        print(f"[{marker}] slot {res['slot']} ({res['file']}):")
        print(f"  endpoints     : {probed}/4 probed, {failed} FAIL")
        print(f"  get_user      : {res['get_user']}")
        print(f"  user_tweets   : {res['user_tweets']}")
        print(f"  user_replies  : {res['user_replies']}")
        print(f"  search_tweet  : {res['search_tweet']}")
        if res.get("key_rebuilds"):
            note = ("recovered after" if failed == 0 else "attempted")
            print(f"  transaction key: {note} {res['key_rebuilds']} rebuild(s) "
                  f"— a bootstrap problem, NOT the cookies")
        if res["error"]:
            print(f"  error         : {res['error']}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
