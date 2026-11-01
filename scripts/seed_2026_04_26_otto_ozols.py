"""One-shot idempotent seed: Otto Ozols (žurnālists, rakstnieks).

Pievieno tracked_politicians rindu (relationship_type='journalist') un
social_accounts rindu (twitter, feed_type='first_party'). Šablons identisks
seed_2026_04_25_additions.py — atkārtota palaišana neko nedublē.

Usage:
    python -m scripts.seed_2026_04_26_otto_ozols
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db import get_db, now_lv  # noqa: E402


ENTRY = {
    "name": "Otto Ozols",
    "x_handle": "OttoOzols",
    "relationship_type": "journalist",
    "role": "Žurnālists, rakstnieks",
    "party": None,
    "notes": "Latviešu žurnālists un rakstnieks; aktīvs publicists X.",
}


def _upsert_politician(db, entry: dict) -> tuple[int, str]:
    existing = db.execute(
        "SELECT id, relationship_type FROM tracked_politicians WHERE name = ?",
        (entry["name"],),
    ).fetchone()
    if existing:
        pid = existing["id"]
        if existing["relationship_type"] != entry["relationship_type"]:
            db.execute(
                "UPDATE tracked_politicians SET relationship_type = ? WHERE id = ?",
                (entry["relationship_type"], pid),
            )
            return pid, f"updated(relationship_type → {entry['relationship_type']})"
        return pid, "exists"

    db.execute(
        "INSERT INTO tracked_politicians "
        "(name, relationship_type, x_handle, role, party, notes, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (entry["name"], entry["relationship_type"], entry["x_handle"],
         entry.get("role"), entry.get("party"), entry.get("notes"), now_lv()),
    )
    pid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    return pid, "inserted"


def _upsert_social_account(db, pid: int, handle: str) -> str:
    has = db.execute(
        "SELECT 1 FROM social_accounts "
        "WHERE opponent_id = ? AND platform = 'twitter' AND handle = ?",
        (pid, handle),
    ).fetchone()
    if has:
        return "exists"
    db.execute(
        "INSERT INTO social_accounts "
        "(opponent_id, platform, handle, active, feed_type) "
        "VALUES (?, 'twitter', ?, 1, 'first_party')",
        (pid, handle),
    )
    return "inserted"


def main() -> int:
    db = get_db()
    with db:
        pid, action = _upsert_politician(db, ENTRY)
        print(f"[{action}] {ENTRY['name']} (id={pid}, rel={ENTRY['relationship_type']})")
        r = _upsert_social_account(db, pid, ENTRY["x_handle"])
        print(f"    {r}: @{ENTRY['x_handle']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
