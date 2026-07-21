"""Probe each x_cookies/{slot}.json against 4 X GraphQL endpoints.

Detects per-endpoint regressions early. As of 2026-04-29 we know:
  - get_user + UserTweets are LENIENT (accept Patch 4 stub TID)
  - SearchTimeline + UserTweetsAndReplies are STRICT (reject stub TID, return 404)

Usage: python scripts/probe_x_cookies.py
"""
import asyncio
import sys
from pathlib import Path

from twikit import Client


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

        try:
            replies = await client.get_user_tweets(uid, "Replies", count=2)
            res["user_replies"] = f"ok ({len(replies)})"
        except Exception as e:
            res["user_replies"] = f"FAIL: {type(e).__name__}: {str(e)[:100]}"

        try:
            search = await client.search_tweet("Latvija", "Latest", count=1)
            res["search_tweet"] = f"ok ({len(search)})"
        except Exception as e:
            res["search_tweet"] = f"FAIL: {type(e).__name__}: {str(e)[:100]}"

    except Exception as e:
        res["error"] = f"{type(e).__name__}: {str(e)[:120]}"

    return res


async def main() -> None:
    files = sorted(p for p in COOKIES_DIR.glob("*.json") if p.stem.isdigit())
    if not files:
        print(f"No cookie files in {COOKIES_DIR}")
        sys.exit(1)

    print(f"Probing {len(files)} cookie file(s) across 4 endpoints...\n")
    for i, p in enumerate(files, 1):
        res = await probe_one(i, p)
        endpoints_failed = sum(
            1 for k in ("get_user", "user_tweets", "user_replies", "search_tweet")
            if res.get(k) and "FAIL" in res[k]
        )
        marker = "OK" if endpoints_failed == 0 else f"BROKEN ({endpoints_failed}/4)"
        print(f"[{marker}] slot {res['slot']} ({res['file']}):")
        print(f"  get_user      : {res['get_user']}")
        print(f"  user_tweets   : {res['user_tweets']}")
        print(f"  user_replies  : {res['user_replies']}")
        print(f"  search_tweet  : {res['search_tweet']}")
        if res["error"]:
            print(f"  error         : {res['error']}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
