"""One-shot idempotent seed: 2026-04-25 tracked entities batch.

Adds 6 X commentators, 1 journalist (Gatis Madžiņš), and 1 tracked politician
(Mārtiņš Štāls — Jelgavas vicemērs + JKP līdzpriekšsēdētājs). Also consolidates
the existing 'Nepareizais' entry (id=62) with its real identity: Edgars Svirskis.

Classification conventions:
- Anonymous X commentators are stored with name = "@handle" (kept parallel to
  handle so UI surfaces the @-prefix cue and a future rename is trivial).
- Non-Saeima party affiliations (e.g. JKP) go in `tracked_politicians.party`
  as free text. `parties` table is not touched here — `get_coalition_map`
  defaults unknown parties to 'other' → "Bez Saeimas frakcijas" rail in UI
  (līdz 2026-07-22 "Ārpus Saeimas").
- Idempotent: re-running emits "unchanged"/"exists" and commits nothing new.

Usage:
    python -m scripts.seed_2026_04_25_additions
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db import get_db, now_lv  # noqa: E402


ENTRIES: list[dict] = [
    {
        # Svirskis consolidation: rename existing Nepareizais row, add ESvirskis
        # as second social_account. realNepareizais handle stays (already there).
        "existing_id": 62,
        "name": "Edgars Svirskis",
        "x_handle": "ESvirskis",
        "additional_handles": ["realNepareizais"],
        "relationship_type": "commentator",
        "role": None,
        "party": None,
        "notes": "Komentētājs zem 'Nepareizais' pseidonīma; pārvalda arī "
                 "@realNepareizais kontu. Konsolidēts 2026-04-25.",
    },
    {
        "name": "@Heinrih5",
        "x_handle": "Heinrih5",
        "relationship_type": "commentator",
        "role": None,
        "party": None,
        "notes": "Anonīms X komentētājs; identitāte nav zināma.",
    },
    {
        "name": "@Tuksumsz",
        "x_handle": "Tuksumsz",
        "relationship_type": "commentator",
        "role": None,
        "party": None,
        "notes": "Anonīms X komentētājs; identitāte nav zināma.",
    },
    {
        "name": "Mārtiņš Štāls",
        "x_handle": "martinsstals",
        "relationship_type": "tracked",
        "role": "Jelgavas vicemērs, JKP līdzpriekšsēdētājs",
        "party": "JKP",
        "notes": "Jelgavas vicemērs (jelgava.lv); Jaunā Konservatīvā Partija "
                 "līdzpriekšsēdētājs (partijajkp.lv); CES.lv dibinātājs.",
    },
    {
        "name": "Toms Lūsis",
        "x_handle": "LusisToms",
        "relationship_type": "commentator",
        "role": None,
        "party": None,
        "notes": "TVNET 'Lūsis komentē' kolumnists; aktīvs X komentētājs.",
    },
    {
        "name": "@Kurmitis_",
        "x_handle": "Kurmitis_",
        "relationship_type": "commentator",
        "role": None,
        "party": None,
        "notes": "Anonīms X komentētājs; identitāte nav zināma.",
    },
    {
        "name": "Gatis Madžiņš",
        "x_handle": "Madzins",
        "relationship_type": "journalist",
        "role": "Žurnālists (Diena / db.lv)",
        "party": None,
        "notes": "Diena, Dienas bizness, Sestdiena, KDI, Sporta Avīze; "
                 "diena.lv, db.lv.",
    },
    {
        "name": "@PStrautins",
        "x_handle": "PStrautins",
        "relationship_type": "commentator",
        "role": None,
        "party": None,
        "notes": "Anonīms X komentētājs; identitāte nav zināma.",
    },
]


def _upsert_politician(db, entry: dict) -> tuple[int, str]:
    """Find or create tracked_politicians row. Returns (pid, action)."""
    # Special case: rename by existing_id (Svirskis → id=62 rename)
    if "existing_id" in entry:
        pid = entry["existing_id"]
        cur = db.execute(
            "UPDATE tracked_politicians "
            "SET name = ?, x_handle = ?, relationship_type = ?, notes = ? "
            "WHERE id = ? AND ("
            "  name != ? OR x_handle != ? OR relationship_type != ? "
            "  OR COALESCE(notes, '') != ?"
            ")",
            (entry["name"], entry["x_handle"], entry["relationship_type"], entry["notes"],
             pid,
             entry["name"], entry["x_handle"], entry["relationship_type"], entry["notes"]),
        )
        return pid, "renamed" if cur.rowcount > 0 else "unchanged"

    # Look up by name
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

    # Insert new
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
    """Idempotent social_accounts insert. Returns action string."""
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
        for entry in ENTRIES:
            pid, action = _upsert_politician(db, entry)
            print(f"[{action}] {entry['name']} (id={pid}, rel={entry['relationship_type']})")
            r = _upsert_social_account(db, pid, entry["x_handle"])
            print(f"    {r}: @{entry['x_handle']}")
            for add_h in entry.get("additional_handles", []):
                r = _upsert_social_account(db, pid, add_h)
                print(f"    {r}: @{add_h}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
