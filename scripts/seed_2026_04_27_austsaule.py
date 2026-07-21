"""One-shot idempotent seed: Partija "Austošā Saule Latvijai" + 5 valdes locekļi.

Pievieno:
- `parties` rindu: ASL, x_handle=austsaule, coalition_status=not_in_saeima.
- 5 `tracked_politicians` rindas (relationship_type='tracked',
  party='Austošā Saule Latvijai' — pilnais nosaukums, sakrīt ar parties.name;
  īso 'ASL' atrisina _party_short_name + parties.short_name).
- 5 `social_accounts` rindas (twitter, feed_type='first_party').

Atkārtota palaišana neko nedublē — emits "exists"/"unchanged".

Avots: https://www.austsaule.lv (dibināta 2025-08-23, "rīcībpolitisks
nacionālisms un konservatīvisms"). Apstiprināts ar operatoru 2026-04-27:
visi 5 ir valdes locekļi.

Usage:
    python -m scripts.seed_2026_04_27_austsaule
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db import get_db, now_lv  # noqa: E402


PARTY = {
    "name": "Austošā Saule Latvijai",
    "short_name": "ASL",
    "x_handle": "austsaule",
    "website": "https://www.austsaule.lv",
    "ideology": "Rīcībpolitisks nacionālisms un konservatīvisms",
    "coalition_status": "not_in_saeima",
    "color": "#fbbf24",
    "description": "2025-08-23 dibināta partija. Valdes priekšsēdētājs Raivis Zeltīts.",
}


ENTRIES: list[dict] = [
    {
        "name": "Raivis Zeltīts",
        "x_handle": "RaivisZeltits",
        "relationship_type": "tracked",
        "role": "Valdes priekšsēdētājs, zemessargs, vēstures skolotājs",
        "party": "Austošā Saule Latvijai",
        "notes": "Partijas 'Austošā Saule Latvijai' valdes priekšsēdētājs; "
                 "zemessargs; ikdienā vēstures skolotājs.",
    },
    {
        "name": "Dace Lindberga",
        "x_handle": "lindberga22",
        "relationship_type": "tracked",
        "role": "Valdes locekle",
        "party": "Austošā Saule Latvijai",
        "notes": "Partijas 'Austošā Saule Latvijai' valdes locekle.",
    },
    {
        "name": "Andris Velps",
        "x_handle": "AndrisVelps",
        "relationship_type": "tracked",
        "role": "Valdes loceklis",
        "party": "Austošā Saule Latvijai",
        "notes": "Partijas 'Austošā Saule Latvijai' valdes loceklis.",
    },
    {
        "name": "Jānis Zalāns",
        "x_handle": "Janis_Zalans",
        "relationship_type": "tracked",
        "role": "Valdes loceklis",
        "party": "Austošā Saule Latvijai",
        "notes": "Partijas 'Austošā Saule Latvijai' valdes loceklis.",
    },
    {
        "name": "Matīss Žuravļevs",
        "x_handle": "zuravlevs",
        "relationship_type": "tracked",
        "role": "Valdes loceklis",
        "party": "Austošā Saule Latvijai",
        "notes": "Partijas 'Austošā Saule Latvijai' valdes loceklis.",
    },
]


def _upsert_party(db, party: dict) -> tuple[int, str]:
    existing = db.execute(
        "SELECT id, coalition_status, x_handle, website, color, ideology "
        "FROM parties WHERE name = ? OR short_name = ?",
        (party["name"], party["short_name"]),
    ).fetchone()
    if existing:
        return existing["id"], "exists"
    db.execute(
        "INSERT INTO parties "
        "(name, short_name, x_handle, website, ideology, coalition_status, "
        " color, description, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (party["name"], party["short_name"], party["x_handle"],
         party["website"], party["ideology"], party["coalition_status"],
         party["color"], party["description"], now_lv()),
    )
    pid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    return pid, "inserted"


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
        party_id, action = _upsert_party(db, PARTY)
        print(f"[{action}] PARTY {PARTY['name']} (id={party_id}, "
              f"short={PARTY['short_name']}, status={PARTY['coalition_status']})")
        for entry in ENTRIES:
            pid, p_action = _upsert_politician(db, entry)
            print(f"[{p_action}] {entry['name']} (id={pid}, party={entry['party']})")
            r = _upsert_social_account(db, pid, entry["x_handle"])
            print(f"    {r}: @{entry['x_handle']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
