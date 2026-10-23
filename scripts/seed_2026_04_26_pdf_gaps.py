"""One-shot idempotent seed: 2026-04-26 PDF coverage gaps.

Adds 3 tracked politicians surfaced by the 2026-04 events PDF audit who were
not yet in tracked_politicians:

- Edgars Tāvars (AS) — Saeimas deputāts, aktīvs Siliņas tēriņu kritiķis,
  citēts vairākos PDF avotos par VIP zāļu skandālu.
- Jānis Tutins (LPV) — Rēzeknes mērs no 2026-04-10. Latgales LPV balss,
  Finanšu un budžeta komitejas vadītājs.
- Aleksandrs Bartaševičs — atstādinātais Rēzeknes mērs (kopš 2002), partija
  šobrīd neskaidra (vēsturiski Saskaņa); kontekstam KNAB/krimināllietas dēļ.

X handles ar nolūku atstāti tukši — tiks pievienoti, ja operators tos atradīs.
Skripts neraksta `social_accounts` rindas, ja `x_handle` ir None.

Idempotents: re-running emits "exists" un nekas nemainās.

Usage:
    python -m scripts.seed_2026_04_26_pdf_gaps
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db import get_db, now_lv  # noqa: E402


ENTRIES: list[dict] = [
    {
        "name": "Edgars Tāvars",
        "x_handle": None,
        "relationship_type": "tracked",
        "role": "Saeimas deputāts",
        "party": "Apvienotais saraksts",
        "notes": "AS deputāts; aktīvs publisks kritiķis valdības tēriņiem "
                 "(piem., Siliņas VIP zāļu izdevumi 2026-04). Pievienots "
                 "2026-04-26 pēc PDF coverage audita.",
    },
    {
        "name": "Jānis Tutins",
        "x_handle": None,
        "relationship_type": "tracked",
        "role": "Rēzeknes domes priekšsēdētājs",
        "party": "Latvija Pirmajā Vietā",
        "notes": "Rēzeknes mērs no 2026-04-10 (8/3 balsis); iepriekš mēra "
                 "vietnieks, Finanšu un budžeta komitejas vadītājs. Politikā "
                 "kopš 2002. gada. LPV/Kopā Latvijai saraksts. Pievienots "
                 "2026-04-26 pēc PDF coverage audita.",
    },
    {
        "name": "Aleksandrs Bartaševičs",
        "x_handle": None,
        "relationship_type": "tracked",
        "role": "Bijušais Rēzeknes mērs",
        "party": None,
        "notes": "Atstādināts no Rēzeknes mēra amata 2026 sakarā ar KNAB "
                 "kriminālprocesu un nesaņemtu pielaidi valsts noslēpumiem. "
                 "Vēsturiski Saskaņa; pašreizējā partijas piederība nav "
                 "verificēta. Pievienots 2026-04-26 pēc PDF coverage audita.",
    },
]


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
        (entry["name"], entry["relationship_type"], entry.get("x_handle"),
         entry.get("role"), entry.get("party"), entry.get("notes"), now_lv()),
    )
    pid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    return pid, "inserted"


def _upsert_social_account(db, pid: int, handle: str | None) -> str:
    if not handle:
        return "skipped (no handle)"
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
            r = _upsert_social_account(db, pid, entry.get("x_handle"))
            print(f"    {r}: @{entry.get('x_handle')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
