"""Add 9 historic 14. Saeima deputies as relationship_type='inactive'.

These deputies left 14. Saeima at various points (resignations, ministerial
appointments, MEP, etc.) and were not in tracked_politicians at backfill time —
causing 97.27% match rate instead of ~99%+. Adding them as 'inactive' lets the
matcher attribute their historic votes via subsequent backfill.

name_forms include both diacritic and ASCII variants per
`feedback_matcher_no_diacritic_strip`. Latvian noun forms (gen., dat.) for
matcher robustness on rhetoric mentions.

Run idempotently: SELECT-before-INSERT skips already-present rows.

After insertion, runs matcher backfill UPDATE on saeima_individual_votes
WHERE politician_id IS NULL to retroactively attribute their historic votes.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

DB_PATH = str(REPO_ROOT / "data" / "atmina.db")
TODAY_LV = "2026-05-27"


# Each entry: (name, name_forms, party, keywords, notes)
HISTORIC_DEPUTIES = [
    (
        "Andrejs Vilks",
        ["Vilks", "Vilka", "Vilkam", "Andrejs Vilks"],
        "Zaļo un Zemnieku savienība",
        ["ZZS", "ekonomika", "finanses"],
        f"Added {TODAY_LV} — P3 historic backfill catchup. Left 14. Saeima during term.",
    ),
    (
        "Mairita Lūse",
        ["Lūse", "Luse", "Lūses", "Luses", "Lūsei", "Lusei", "Mairita Lūse", "Mairita Luse"],
        "Progresīvie",
        ["PRO", "progresīvie"],
        f"Added {TODAY_LV} — P3 historic backfill catchup.",
    ),
    (
        "Viktors Pučka",
        ["Pučka", "Pucka", "Pučkas", "Puckas", "Pučkam", "Puckam", "Viktors Pučka", "Viktors Pucka"],
        "Stabilitātei!",
        ["ST!", "Stabilitātei"],
        f"Added {TODAY_LV} — P3 historic backfill catchup.",
    ),
    (
        "Ģirts Valdis Kristovskis",
        [
            "Kristovskis", "Kristovska", "Kristovskim",
            "Ģirts Valdis Kristovskis", "Girts Valdis Kristovskis",
            "Ģirts Kristovskis", "Girts Kristovskis",
        ],
        "Jaunā Vienotība",
        ["JV", "aizsardzība", "ārlietas"],
        f"Added {TODAY_LV} — P3 historic backfill catchup. Long-serving politician (former Aiz.min., Ārlietu min.).",
    ),
    (
        "Ģirts Štekerhofs",
        [
            "Štekerhofs", "Stekerhofs", "Štekerhofa", "Stekerhofa",
            "Štekerhofam", "Stekerhofam", "Ģirts Štekerhofs", "Girts Stekerhofs",
        ],
        "Zaļo un Zemnieku savienība",
        ["ZZS"],
        f"Added {TODAY_LV} — P3 historic backfill catchup.",
    ),
    (
        "Edgars Zelderis",
        ["Zelderis", "Zeldera", "Zelderim", "Edgars Zelderis"],
        "Progresīvie",
        ["PRO", "progresīvie", "Talsi", "Mēs Talsiem un novadam"],
        # Verified post-insert 2026-05-27 via web search (LSM, TVNet, Wikipedia).
        # Elected on PRO list via "Mēs – Talsiem un novadam" cooperation in 14. Saeima.
        # Left PRO faction 2024-06-19 (coalition dropped to 50 seats), became
        # non-faction — that's why faction=None in 2025 snapshots, not a parsing bug.
        # Died 2025-12-24 after long illness.
        f"Added {TODAY_LV} — P3 historic backfill catchup. Elected 14. Saeima 2022 no Progresīvo (PRO) saraksta caur \"Mēs – Talsiem un novadam\" sadarbību. Pamet PRO frakciju 2024-06-19; turpmāk strādāja kā pie frakcijām nepiederošs (tāpēc faction=None 2025 snapshotos). Miris 2025-12-24 pēc ilgstošas slimības. Avoti: lsm.lv 19.06.2024, tvnet.lv 29.12.2025, lv.wikipedia.org/wiki/Edgars_Zelderis.",
    ),
    (
        "Aleksejs Rosļikovs",
        [
            "Rosļikovs", "Roslikovs", "Rosļikova", "Roslikova",
            "Rosļikovam", "Roslikovam", "Aleksejs Rosļikovs", "Aleksejs Roslikovs",
        ],
        "Stabilitātei!",
        ["ST!", "Stabilitātei", "EP deputāts"],
        f"Added {TODAY_LV} — P3 historic backfill catchup. ST! founder; became MEP 2024-07.",
    ),
    (
        "Ervins Labanovskis",
        ["Labanovskis", "Labanovska", "Labanovskim", "Ervins Labanovskis"],
        "Progresīvie",
        ["PRO", "progresīvie"],
        f"Added {TODAY_LV} — P3 historic backfill catchup.",
    ),
    (
        "Jānis Reirs",
        ["Reirs", "Reira", "Reiram", "Jānis Reirs", "Janis Reirs"],
        "Jaunā Vienotība",
        ["JV", "finanses", "ekonomika"],
        f"Added {TODAY_LV} — P3 historic backfill catchup. Long-serving politician (former Fin.min., Lab.min.).",
    ),
]


def main() -> int:
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()

    inserted: list[tuple[int, str]] = []
    skipped: list[str] = []

    for name, name_forms, party, keywords, notes in HISTORIC_DEPUTIES:
        # Idempotency: skip if name already present
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
        new_id = cur.lastrowid
        inserted.append((new_id, name))

    db.commit()

    print(f"=== Insertion summary ===")
    print(f"  inserted: {len(inserted)}")
    for pid, name in inserted:
        print(f"    pid={pid}  {name}")
    if skipped:
        print(f"  skipped (already present): {len(skipped)}")
        for s in skipped:
            print(f"    {s}")

    # Retroactively attribute their historic votes by re-running the matcher
    # on saeima_individual_votes WHERE politician_id IS NULL.
    print()
    print(f"=== Retroactive matcher backfill ===")
    from src.saeima.votes import _build_name_index
    name_index = _build_name_index(DB_PATH)

    null_rows = cur.execute(
        "SELECT id, deputy_name FROM saeima_individual_votes WHERE politician_id IS NULL"
    ).fetchall()
    print(f"  rows with politician_id IS NULL: {len(null_rows)}")

    updated = 0
    still_missing: dict[str, int] = {}
    for vote_id, deputy_name in null_rows:
        key = deputy_name.lower().strip()
        pid = name_index.get(key)
        if pid is None:
            # Partial match — same logic as match_deputies_to_politicians
            for name_key, candidate in name_index.items():
                if key == name_key or name_key in key or key in name_key:
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
        print(f"  still missing ({len(still_missing)} distinct names):")
        for n, c in sorted(still_missing.items(), key=lambda x: -x[1])[:15]:
            print(f"    {n}: {c} votes")

    # NOTE: claims for these historic votes are NOT auto-generated here.
    # store_claim() requires per-vote context (vote_id, vote.motif, etc.) — that
    # logic lives in generate_claims_from_votes(). A separate retroactive
    # claim-generation pass would be needed if we want full saeima_vote claim
    # coverage for these deputies. For now, the saeima_individual_votes
    # politician_id linkage is sufficient for vote-ledger reads.
    print()
    print("=== Done. NOTE: claims NOT generated for retro-matched rows. ===")
    print("  If full saeima_vote claim coverage needed for these 9 deputies,")
    print("  separate retroactive claim-generation pass required.")

    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
