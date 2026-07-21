"""One-time (idempotent) seed of political commentators.

A 'commentator' in atmina.lv terms = a public X/Twitter figure who
posts substantive allegations or opinions about tracked politicians
without being an elected politician themselves. Their tweets are
captured via fetch_all_twitter() (same pipeline as politicians,
since we iterate social_accounts), then extracted as
claim_type='commentary' with speaker_id=<commentator.id> and
opponent_id=<mentioned tracked politician>.

Seed list is conservative — active posters whose output regularly
names tracked politicians with concrete substantive content.
Grow this list only when the operator sees value; every commentator
multiplies the daily fetch/extract cost.

Re-running this script is safe: idempotency is enforced application-side via
SELECT-then-INSERT guards (no UNIQUE DB constraints exist on the seed keys).
Under concurrent execution, two processes could race past the SELECT and both
INSERT — for a single-operator seed this is acceptable, but do not invoke
in parallel.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db import get_db, now_lv  # noqa: E402

# Conservative starter set. Add entries only after observing ≥5 substantive
# mentions of tracked politicians in the last ~14 days.
COMMENTATORS = [
    {
        "name": "Didzis Kļuciņš",
        "x_handle": "KlucisD",
        "notes": "Aktīvs X komentētājs; kritizē Rīgas pašvaldības iepirkumus, "
                 "AirBaltic finanses, partiju korupciju. Nav vēlēts politiķis "
                 "(pārbaudīts pret CVK 2025 RD sarakstu 2026-04-23).",
    },
]


def main() -> None:
    db = get_db()
    with db:
        for c in COMMENTATORS:
            # UPSERT tracked_politicians row
            existing = db.execute(
                "SELECT id, relationship_type FROM tracked_politicians WHERE name = ?",
                (c["name"],),
            ).fetchone()
            if existing:
                pid = existing["id"]
                if existing["relationship_type"] != "commentator":
                    db.execute(
                        "UPDATE tracked_politicians SET relationship_type = 'commentator' WHERE id = ?",
                        (pid,),
                    )
                    print(f"updated {c['name']} -> relationship_type=commentator (id={pid})")
                else:
                    print(f"skip {c['name']} — already commentator (id={pid})")
            else:
                db.execute(
                    "INSERT INTO tracked_politicians (name, relationship_type, x_handle, notes, created_at) "
                    "VALUES (?, 'commentator', ?, ?, ?)",
                    (c["name"], c["x_handle"], c["notes"], now_lv()),
                )
                pid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
                print(f"inserted {c['name']} (id={pid})")

            # UPSERT social_accounts row — matches fetch_all_twitter's iteration source
            has_account = db.execute(
                "SELECT 1 FROM social_accounts WHERE opponent_id = ? AND platform = 'twitter' AND handle = ?",
                (pid, c["x_handle"]),
            ).fetchone()
            if not has_account:
                db.execute(
                    "INSERT INTO social_accounts (opponent_id, platform, handle, active) "
                    "VALUES (?, 'twitter', ?, 1)",
                    (pid, c["x_handle"]),
                )
                print(f"  + social_accounts row for @{c['x_handle']}")


if __name__ == "__main__":
    main()
