"""Add X/Twitter mention-scan sources (journalists, media, institutions).

For each entry: verifies the handle exists via twikit's lenient
`get_user_by_screen_name` endpoint, then INSERTs both a tracked_politicians
row (so junctions work) and a social_accounts row (so the mentions scanner
picks up the timeline).

Idempotent — handles already in social_accounts are skipped.

Edit the SOURCES list below to add new batches; re-run safely.

Usage:
    python scripts/add_mention_sources.py [--dry-run]
"""

import argparse
import asyncio
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.db import get_db  # noqa: E402
from src.x_pool import get_pool  # noqa: E402

# Edit this list to add new mention sources. Re-running is safe — already-
# inserted handles are skipped via social_accounts uniqueness check.
SOURCES = [
    # Mediji — žurnālistu kategorija + relay feed_type
    {"handle": "nralv",         "name": "Neatkarīgā Rīta Avīze", "rt": "journalist",   "feed": "relay"},
    {"handle": "letanewslv",    "name": "LETA",                  "rt": "journalist",   "feed": "relay"},
    {"handle": "TV3zinas",      "name": "TV3 Ziņas",             "rt": "journalist",   "feed": "relay"},
    {"handle": "ltvpanorama",   "name": "LTV Panorāma",          "rt": "journalist",   "feed": "relay"},
    {"handle": "ltvdefacto",    "name": "LTV De Facto",          "rt": "journalist",   "feed": "relay"},
    {"handle": "irLV",          "name": "IR žurnāls",            "rt": "journalist",   "feed": "relay"},
    {"handle": "Krustpunkta",   "name": "Krustpunktā",           "rt": "journalist",   "feed": "relay"},
    # Institūcijas — organization
    {"handle": "Jekaba11",      "name": "Saeimas ziņas",         "rt": "organization", "feed": "relay"},
]


def _existing_handles(db) -> set[str]:
    rows = db.execute(
        "SELECT handle FROM social_accounts WHERE platform='twitter'"
    ).fetchall()
    return {r["handle"].lower() for r in rows}


async def _verify_handle(pool, handle: str) -> tuple[bool, str | None]:
    """Returns (exists, display_name_or_error)."""
    try:
        slot = pool.get_next_slot()
        client = pool.get_client(slot)
    except RuntimeError as e:
        return False, f"pool: {e}"
    try:
        user = await client.get_user_by_screen_name(handle)
        return True, user.name or handle
    except Exception as e:
        return False, str(e)


async def main_async(dry_run: bool) -> int:
    db = get_db()
    existing = _existing_handles(db)

    pool = await get_pool()

    skipped_existing: list[str] = []
    verified: list[dict] = []
    failed: list[tuple[str, str]] = []

    for s in SOURCES:
        h = s["handle"]
        if h.lower() in existing:
            skipped_existing.append(h)
            print(f"[skip] @{h} — already in social_accounts")
            continue
        ok, info = await _verify_handle(pool, h)
        if ok:
            print(f"[ok]   @{h} — verified ({info})")
            verified.append({**s, "display_name": info})
        else:
            print(f"[FAIL] @{h} — {info}")
            failed.append((h, str(info)))

    if dry_run:
        print(f"\n[dry-run] would INSERT {len(verified)}, skipped {len(skipped_existing)}, failed {len(failed)}")
        return 0

    inserted = 0
    for v in verified:
        cur = db.execute(
            "INSERT INTO tracked_politicians (name, relationship_type, x_handle) "
            "VALUES (?, ?, ?)",
            (v["name"], v["rt"], v["handle"]),
        )
        opponent_id = cur.lastrowid
        db.execute(
            "INSERT INTO social_accounts (opponent_id, platform, handle, "
            "feed_type, active) VALUES (?, 'twitter', ?, ?, 1)",
            (opponent_id, v["handle"], v["feed"]),
        )
        inserted += 1
        print(f"[insert] @{v['handle']} → opponent_id={opponent_id} ({v['rt']}/{v['feed']})")
    db.commit()
    db.close()

    print(f"\n[done] inserted={inserted} skipped_existing={len(skipped_existing)} "
          f"failed={len(failed)}")
    if failed:
        print("\nFailed handles (NOT inserted):")
        for h, err in failed:
            print(f"  @{h}: {err}")
    return 0 if not failed else 2


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--dry-run", action="store_true",
                   help="Verify handles but do not write to DB")
    args = p.parse_args(argv)
    return asyncio.run(main_async(args.dry_run))


if __name__ == "__main__":
    raise SystemExit(main())
