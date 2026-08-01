"""Fetch X profile photos for politicians missing assets/photos/{slug}.jpg.

Reads tracked_politicians + social_accounts, identifies gaps, fetches each
handle's profile image via twikit (cookie-pool), downloads the high-res
variant, saves as JPEG.

Usage:
    python -m scripts.fetch_profile_photos                # fetch all missing
    python -m scripts.fetch_profile_photos --names "X,Y"  # specific names
    python -m scripts.fetch_profile_photos --dry-run      # report only
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sqlite3
import sys
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

PHOTO_DIR = Path("assets/photos")
DB_PATH = "data/atmina.db"


def _slugify(name: str) -> str:
    # Mirrors src.generate._slugify (must stay in sync). Keep minimal here
    # so the script doesn't have to import the whole generate module.
    import re
    s = name.lower()
    repl = {"ā": "a", "ē": "e", "ī": "i", "ū": "u", "ņ": "n", "ļ": "l",
            "ķ": "k", "ģ": "g", "š": "s", "ž": "z", "č": "c"}
    for k, v in repl.items():
        s = s.replace(k, v)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def _missing_photo_targets(only_names: list[str] | None = None) -> list[dict]:
    """Politicians with handles but no .jpg in assets/photos."""
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    existing = set(os.listdir(PHOTO_DIR)) if PHOTO_DIR.is_dir() else set()
    rows = db.execute("""
        SELECT tp.id, tp.name, tp.x_handle,
               (SELECT handle FROM social_accounts
                WHERE opponent_id = tp.id AND platform = 'twitter'
                ORDER BY id LIMIT 1) AS sa_handle
        FROM tracked_politicians tp
        WHERE tp.relationship_type != 'inactive'
        ORDER BY tp.name
    """).fetchall()
    db.close()
    targets = []
    for r in rows:
        if only_names and r["name"] not in only_names:
            continue
        slug = _slugify(r["name"])
        if f"{slug}.jpg" in existing:
            continue
        handle = r["x_handle"] or r["sa_handle"]
        if not handle:
            continue
        targets.append({"id": r["id"], "name": r["name"], "slug": slug, "handle": handle})
    return targets


def _high_res_url(url: str) -> str:
    """Twitter convention: replace _normal.<ext> with _400x400.<ext>."""
    for size in ("_normal", "_bigger", "_mini"):
        if size in url:
            return url.replace(size, "_400x400")
    return url


async def _fetch_one(target: dict, dry_run: bool) -> dict:
    """Lookup user via twikit pool, download avatar. Returns result dict."""
    from src.x_pool import get_pool
    from twikit.errors import UserNotFound, UserUnavailable, TooManyRequests

    pool = await get_pool()
    handle = target["handle"]
    slug = target["slug"]

    for _attempt in range(pool.slot_count + 1):
        try:
            slot = pool.get_next_slot()
            client = pool.get_client(slot)
        except RuntimeError:
            return {**target, "status": "pool_exhausted"}

        try:
            user = await client.get_user_by_screen_name(handle)
        except (UserNotFound, UserUnavailable) as e:
            return {**target, "status": "user_not_found", "error": str(e)}
        except TooManyRequests:
            pool.report_rate_limit(slot, 0)
            continue
        except Exception as e:
            return {**target, "status": "lookup_error", "error": f"{type(e).__name__}: {e}"}

        url = getattr(user, "profile_image_url", None)
        if not url:
            return {**target, "status": "no_avatar"}

        hires_url = _high_res_url(url)

        if dry_run:
            return {**target, "status": "would_download", "url": hires_url}

        try:
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as c:
                r = await c.get(hires_url)
                r.raise_for_status()
                dest = PHOTO_DIR / f"{slug}.jpg"
                dest.write_bytes(r.content)
                return {**target, "status": "saved", "url": hires_url, "bytes": len(r.content)}
        except Exception as e:
            return {**target, "status": "download_error", "error": f"{type(e).__name__}: {e}", "url": hires_url}

    return {**target, "status": "all_slots_rate_limited"}


async def main_async(only_names: list[str] | None, dry_run: bool) -> int:
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    targets = _missing_photo_targets(only_names)
    if not targets:
        print("No missing-photo targets.")
        return 0

    print(f"Fetching {len(targets)} profile photo(s){' (dry run)' if dry_run else ''}:\n")
    results = []
    for t in targets:
        print(f"  → @{t['handle']:<20} {t['name']}")
        result = await _fetch_one(t, dry_run)
        results.append(result)
        marker = {"saved": "✓", "would_download": "→",
                  "user_not_found": "✗", "no_avatar": "·",
                  "download_error": "✗", "lookup_error": "✗",
                  "pool_exhausted": "✗", "all_slots_rate_limited": "✗"}.get(result["status"], "?")
        suffix = ""
        if result["status"] == "saved":
            suffix = f" ({result['bytes']} bytes → assets/photos/{t['slug']}.jpg)"
        elif "error" in result:
            suffix = f" — {result['error']}"
        elif result["status"] == "would_download":
            suffix = f" → {result.get('url', '')}"
        print(f"    {marker} {result['status']}{suffix}")
        # gentle pacing between API hits
        await asyncio.sleep(2)

    saved = sum(1 for r in results if r["status"] == "saved")
    failed = len(results) - saved
    print(f"\nDone: {saved} saved, {failed} other.")
    return 0 if failed == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--names", help="Comma-separated list of exact tracked_politicians.name values; default = all missing")
    ap.add_argument("--dry-run", action="store_true", help="Lookup only; don't download")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    only_names = [n.strip() for n in args.names.split(",")] if args.names else None
    return asyncio.run(main_async(only_names, args.dry_run))


if __name__ == "__main__":
    sys.exit(main())
