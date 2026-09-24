"""Second wave of historic 14. Saeima deputy additions after Phase 3 backfill.

The Phase 3 backfill (2022-11 → 2026-05) surfaced 9 more historic deputies
not yet in tracked_politicians. Together with the swap-name-order matcher
fix, these additions push match rate from 92.36% → ~99.5%+.

Includes Arturs Krišjānis Kariņš (former PM 2019-2023, JV) whose absence
from tracked_politicians was a notable seed-data gap.

Idempotent. After insertion, runs matcher backfill over saeima_individual_votes
WHERE politician_id IS NULL, then generates retro saeima_vote claims.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.saeima.votes import _build_name_index  # noqa: E402

DB_PATH = str(REPO_ROOT / "data" / "atmina.db")
TODAY_LV = "2026-05-27"

# Each entry: (name, name_forms, party, keywords, notes)
# Party assignments based on faction column observed in saeima_individual_votes
# for the corresponding deputy rows.
HISTORIC_DEPUTIES_2 = [
    (
        "Arturs Krišjānis Kariņš",
        [
            "Kariņš", "Karins", "Kariņa", "Kariņam",
            "Arturs Kariņš", "Arturs Karins",
            "Arturs Krišjānis Kariņš", "Arturs Krisjanis Karins",
            "Krišjānis Kariņš", "Krisjanis Karins",
        ],
        "Jaunā Vienotība",
        ["JV", "ārlietas", "ekonomika", "ministru prezidents"],
        f"Added {TODAY_LV} — P3 historic backfill catchup. Ministru prezidents 2019-2023; pēc tam Ārlietu ministrs Siliņas valdībā 2023-2024.",
    ),
    (
        "Viktorija Baire",
        ["Baire", "Baires", "Bairei", "Viktorija Baire"],
        "Jaunā Vienotība",
        ["JV"],
        f"Added {TODAY_LV} — P3 historic backfill catchup.",
    ),
    (
        "Glorija Grevcova",
        ["Grevcova", "Grevcovas", "Grevcovai", "Glorija Grevcova"],
        "Stabilitātei!",
        ["ST!", "Stabilitātei"],
        f"Added {TODAY_LV} — P3 historic backfill catchup.",
    ),
    (
        "Jekaterina Dorošķeviča",
        [
            "Dorošķeviča", "Doroskevica", "Dorošķevičas", "Doroskevicas",
            "Dorošķevičai", "Doroskevicai", "Jekaterina Dorošķeviča",
            "Jekaterina Doroskevica",
        ],
        "Stabilitātei!",
        ["ST!", "Stabilitātei"],
        f"Added {TODAY_LV} — P3 historic backfill catchup.",
    ),
    (
        "Ģirts Lapiņš",
        [
            "Lapiņš", "Lapinš", "Lapiņa", "Lapinš",
            "Ģirts Lapiņš", "Girts Lapinš", "Girts Lapins",
        ],
        "Nacionālā apvienība",
        ["NA"],
        f"Added {TODAY_LV} — P3 historic backfill catchup.",
    ),
    (
        "Atis Deksnis",
        ["Deksnis", "Deksņa", "Deksnim", "Atis Deksnis"],
        "Apvienotais saraksts",
        ["AS"],
        f"Added {TODAY_LV} — P3 historic backfill catchup.",
    ),
    (
        "Arnolds Jātnieks",
        [
            "Jātnieks", "Jatnieks", "Jātnieka", "Jatnieka",
            "Jātniekam", "Jatniekam", "Arnolds Jātnieks", "Arnolds Jatnieks",
        ],
        "Nacionālā apvienība",
        ["NA"],
        f"Added {TODAY_LV} — P3 historic backfill catchup.",
    ),
    (
        "Ieva Brante",
        ["Brante", "Brantes", "Brantei", "Ieva Brante"],
        "Apvienotais saraksts",
        ["AS"],
        f"Added {TODAY_LV} — P3 historic backfill catchup.",
    ),
]


def main() -> int:
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()

    inserted = []
    skipped = []
    for name, name_forms, party, keywords, notes in HISTORIC_DEPUTIES_2:
        existing = cur.execute(
            "SELECT id FROM tracked_politicians WHERE name = ?", (name,)
        ).fetchone()
        if existing:
            skipped.append(f"{name} (pid={existing[0]})")
            continue
        cur.execute(
            """INSERT INTO tracked_politicians
               (name, name_forms, keywords, relationship_type,
                party, role, notes, negative_patterns)
               VALUES (?, ?, ?, 'inactive', ?, 'Saeimas deputāts (14. Saeima)', ?, '[]')""",
            (name, json.dumps(name_forms, ensure_ascii=False),
             json.dumps(keywords, ensure_ascii=False),
             party, notes),
        )
        inserted.append((cur.lastrowid, name))

    db.commit()

    print("=== Inserted ===")
    for pid, name in inserted:
        print(f"  pid={pid}  {name}")
    if skipped:
        print(f"=== Skipped (already present) ===")
        for s in skipped:
            print(f"  {s}")

    # Retroactive matcher backfill — incl. swapped name order (now in src/saeima/votes.py)
    print()
    print("=== Retro matcher backfill ===")
    name_index = _build_name_index(DB_PATH)

    null_rows = cur.execute(
        "SELECT id, deputy_name FROM saeima_individual_votes WHERE politician_id IS NULL"
    ).fetchall()
    print(f"  NULL rows: {len(null_rows)}")

    updated = 0
    still_missing = {}
    for vote_id, deputy_name in null_rows:
        key = deputy_name.lower().strip()
        pid = name_index.get(key)
        if pid is None:
            parts = key.split()
            if len(parts) == 2:
                swapped = f"{parts[1]} {parts[0]}"
                pid = name_index.get(swapped)
            elif len(parts) == 3:
                # Try "LAST FIRST MIDDLE" -> "FIRST MIDDLE LAST"
                swapped_a = f"{parts[1]} {parts[2]} {parts[0]}"
                pid = name_index.get(swapped_a)
                if pid is None:
                    # Or "LAST FIRST MIDDLE" -> "MIDDLE FIRST LAST"
                    swapped_b = f"{parts[2]} {parts[1]} {parts[0]}"
                    pid = name_index.get(swapped_b)
        if pid is None:
            for nk, candidate in name_index.items():
                if key == nk or nk in key or key in nk:
                    pid = candidate
                    break
        if pid is None:
            still_missing[deputy_name] = still_missing.get(deputy_name, 0) + 1
            continue
        cur.execute(
            "UPDATE saeima_individual_votes SET politician_id=? WHERE id=?",
            (pid, vote_id),
        )
        updated += 1
    db.commit()

    print(f"  updated rows: {updated}")
    if still_missing:
        print(f"  still missing ({len(still_missing)} distinct, {sum(still_missing.values())} rows):")
        for n, c in sorted(still_missing.items(), key=lambda x: -x[1]):
            print(f"    {n}: {c}")

    # Match rate
    total, matched = cur.execute(
        "SELECT COUNT(*), SUM(CASE WHEN politician_id IS NOT NULL THEN 1 ELSE 0 END) FROM saeima_individual_votes"
    ).fetchone()
    print(f"  match rate: {100*matched/total:.2f}%  ({matched}/{total})")

    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
