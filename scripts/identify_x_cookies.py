"""Identify which X account each x_cookies/{slot}.json belongs to.

Slot 1 has twid embedded in the file directly. Slots 2 and 3 only contain
auth_token + ct0 — for those we resolve via twikit's account/settings call,
which returns the screen_name for the authenticated user.
"""
import asyncio
import json
import sys
from pathlib import Path

from twikit import Client

COOKIES_DIR = Path(__file__).resolve().parent.parent / "data" / "x_cookies"


async def identify_one(slot: int, cookie_path: Path) -> dict:
    res = {"slot": slot, "file": cookie_path.name, "screen_name": None,
           "user_id": None, "method": None, "error": None}

    raw = json.loads(cookie_path.read_text(encoding="utf-8"))
    twid = raw.get("twid", "")
    if twid.startswith("u="):
        res["user_id"] = twid[2:]

    try:
        client = Client("en-US")
        client.load_cookies(str(cookie_path))

        if res["user_id"]:
            try:
                user = await client.get_user_by_id(res["user_id"])
                res["screen_name"] = user.screen_name
                res["method"] = "twid -> get_user_by_id"
            except Exception as e:
                res["error"] = f"get_user_by_id: {type(e).__name__}: {str(e)[:80]}"

        if not res["screen_name"]:
            try:
                me = await client.user()
                res["screen_name"] = me.screen_name
                res["user_id"] = res["user_id"] or me.id
                res["method"] = "client.user() (authenticated)"
            except Exception as e:
                if not res["error"]:
                    res["error"] = f"client.user(): {type(e).__name__}: {str(e)[:80]}"

    except Exception as e:
        res["error"] = f"{type(e).__name__}: {str(e)[:120]}"

    return res


async def main() -> None:
    files = sorted(COOKIES_DIR.glob("*.json"))
    if not files:
        print(f"No cookie files in {COOKIES_DIR}")
        sys.exit(1)

    print(f"Identifying owner of {len(files)} cookie file(s)...\n")
    for i, p in enumerate(files, 1):
        res = await identify_one(i, p)
        marker = "OK" if res["screen_name"] else "??"
        print(f"[{marker}] slot {res['slot']} ({res['file']}):")
        print(f"  screen_name : {res['screen_name'] or '<could not identify>'}")
        print(f"  user_id     : {res['user_id'] or '<no twid in file>'}")
        print(f"  method      : {res['method']}")
        if res["error"]:
            print(f"  error       : {res['error']}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
