"""One-shot idempotent seed: Aivis Ceriņš (Apvienotais saraksts).

Pievieno:
- ``tracked_politicians`` rindu Aivis Ceriņš (relationship_type='tracked',
  party='Apvienotais saraksts').
- ``social_accounts`` rindu (twitter, feed_type='first_party').

Atkārtota palaišana neko nedublē — emits "exists"/"inserted".

Konteksts:
    2026-05-16 11:41 LV laikā @CerinsAivis tweetā paziņoja par formālu
    pievienošanos biedrībai "Latvijas restarts" (vadītājs Andris Kulbergs,
    pid=10), kas ir viena no Apvienotā saraksta daļām. Tas noslēdz 12 gadu
    karjeru TV24 raidījumā "Preses klubs" (pēdējais dzīvais ēters 2026-05-01)
    un atver pirmā-personas politiskās komentēšanas posmu, ko platforma
    sāk izsekot kā tracked deputāta kandidātu/aktīvistu.

Avots: Wikipedia + X profils (id=2305393238, ~5600 sekotāji), tweet ID
``2055569382248497491`` (2026-05-16 08:41 UTC).

Usage:
    .venv/Scripts/python.exe -m scripts.seed_2026_05_16_cerins
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db import get_db, now_lv  # noqa: E402


ENTRY = {
    "name": "Aivis Ceriņš",
    "x_handle": "CerinsAivis",
    "relationship_type": "tracked",
    "party": "Apvienotais saraksts",
    "role": (
        "Biedrības 'Latvijas restarts' biedrs (no 2026-05-16); "
        "bijušais TV24 'Preses klubs' vadītājs (12 gadi, līdz 2026-05-01); "
        "būvinženieris"
    ),
    "notes": (
        "2026-05-16 X paziņojumā formāli pievienojas Andra Kulberga (pid=10) "
        "vadītajai biedrībai 'Latvijas restarts', kas darbojas Apvienotā "
        "saraksta orbītā. Pirms tam — 12 gadi TV24 raidījuma 'Preses klubs' "
        "vadītājs, pēdējais dzīvais ēters 2026-05-01. X profila apraksts: "
        "'manas subjektīvās realitātes komentāri'. Dzimis 1988-09-19 Cēsīs."
    ),
    # Diakritika + ASCII formas; matcher pats auto-pievieno declensijas
    # (-ņa/-ņam/-ņu palatalizācija no -ņš + -a/-am/-u no ASCII -s).
    # Sk. [[feedback_matcher_no_diacritic_strip]].
    "name_forms": [
        "Aivis Ceriņš",
        "Ceriņš",
        "Aivis Cerins",
        "Cerins",
    ],
}


def _upsert_politician(db, entry: dict) -> tuple[int, str]:
    existing = db.execute(
        "SELECT id, relationship_type, party FROM tracked_politicians WHERE name = ?",
        (entry["name"],),
    ).fetchone()
    if existing:
        pid = existing["id"]
        changes = []
        if existing["relationship_type"] != entry["relationship_type"]:
            db.execute(
                "UPDATE tracked_politicians SET relationship_type = ? WHERE id = ?",
                (entry["relationship_type"], pid),
            )
            changes.append(f"relationship_type → {entry['relationship_type']}")
        if existing["party"] != entry["party"]:
            db.execute(
                "UPDATE tracked_politicians SET party = ? WHERE id = ?",
                (entry["party"], pid),
            )
            changes.append(f"party → {entry['party']}")
        return pid, ("updated(" + ", ".join(changes) + ")" if changes else "exists")
    db.execute(
        "INSERT INTO tracked_politicians "
        "(name, relationship_type, x_handle, role, party, notes, name_forms, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            entry["name"], entry["relationship_type"], entry["x_handle"],
            entry["role"], entry["party"], entry["notes"],
            json.dumps(entry["name_forms"], ensure_ascii=False),
            now_lv(),
        ),
    )
    pid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    return pid, "inserted"


def _upsert_social_account(db, pid: int, handle: str) -> tuple[int | None, str]:
    has = db.execute(
        "SELECT id FROM social_accounts "
        "WHERE opponent_id = ? AND platform = 'twitter' AND handle = ?",
        (pid, handle),
    ).fetchone()
    if has:
        return has["id"], "exists"
    db.execute(
        "INSERT INTO social_accounts "
        "(opponent_id, platform, handle, active, feed_type) "
        "VALUES (?, 'twitter', ?, 1, 'first_party')",
        (pid, handle),
    )
    sid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    return sid, "inserted"


def main() -> int:
    db = get_db()
    with db:
        pid, p_action = _upsert_politician(db, ENTRY)
        print(f"[{p_action}] {ENTRY['name']} (pid={pid}, party={ENTRY['party']})")
        sid, s_action = _upsert_social_account(db, pid, ENTRY["x_handle"])
        print(f"[{s_action}] social_account @{ENTRY['x_handle']} "
              f"(social_account_id={sid}, feed_type='first_party')")

    # Quick matcher self-check — verify name_forms cover the tweet's anticipated
    # mention strings (full name + bare surname, diacritic + ASCII).
    from src.matcher import _clear_politician_cache, match_politician
    _clear_politician_cache()
    for sample in ["Aivis Ceriņš", "Ceriņš paziņoja", "Aivis Cerins", "Cerins"]:
        m = match_politician(sample)
        ok = "OK" if m == pid else f"FAIL (got {m})"
        print(f"  matcher self-check: {sample!r} → {ok}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
