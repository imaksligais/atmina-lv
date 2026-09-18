"""Fix the surname-collision mis-attribution discovered post-Phase-3.

Five 14. Saeima deputy pairs share surnames; the partial-match fallback in
match_deputies_to_politicians mis-attributed ~14k vote rows of the
2nd-of-pair to the 1st-of-pair (whichever was in tracked_politicians).

Verified party affiliations from saeima.lv / Wikipedia (2026-05-27):
  - Ričards Šlesers  → LPV
  - Vilis Krištopans → LPV
  - Andrejs Judins   → JV (Juridiskās komisijas vadītājs)
  - Normunds Dzintars → NA (substitute when Indriksone took Min. amatu)
  - Inese Kalniņa     → JV (LU Biznesa fak. lektore)

Pipeline:
  1. Insert the 5 new deputies as relationship_type='inactive'.
  2. UPDATE saeima_individual_votes WHERE deputy_name = 'Surname Firstname'
     (the snapshot order) → set politician_id to the new pid.
  3. Generate saeima_vote claims for the new pids over their iv rows.
     store_claim is idempotent on (opponent_id, source_url, topic),
     so each new (new_pid, URL, T) creates exactly one claim.

After this fix the old claims for the wrong pid stay intact (they were
created from the FIRST iv processed = the original deputy's own vote;
the duplicate iv's stance was never captured, so we lose nothing by
leaving those claims).
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.db import store_claim  # noqa: E402
from src.saeima.claims import _motif_to_topic, _vote_salience  # noqa: E402
from src.saeima.bills import _parse_vote_datetime, _resolve_vote_url  # noqa: E402

DB_PATH = str(REPO_ROOT / "data" / "atmina.db")
TODAY_LV = "2026-05-27"

# Each entry: (name, name_forms, party, keywords, notes, snapshot_form)
# snapshot_form is the "Surname Firstname" string used in older titania
# accessibility snapshots — this is the deputy_name we'll UPDATE for.
PAIRS = [
    (
        "Ričards Šlesers",
        ["Šlesers", "Šlesera", "Šleseram", "Ričards Šlesers", "Slesers", "Ricards Slesers"],
        "Latvija pirmajā vietā",
        ["LPV"],
        f"Added {TODAY_LV} — P3 surname-collision fix. Ainārs Šlesers's son; LPV faction in 14. Saeima.",
        "Šlesers Ričards",
    ),
    (
        "Vilis Krištopans",
        ["Krištopans", "Krištopana", "Krištopanam", "Vilis Krištopans", "Kristopans", "Vilis Kristopans"],
        "Latvija pirmajā vietā",
        ["LPV"],
        f"Added {TODAY_LV} — P3 surname-collision fix. LPV faction in 14. Saeima.",
        "Krištopans Vilis",
    ),
    (
        "Andrejs Judins",
        [
            "Judins", "Judina", "Judinam",
            "Andrejs Judins", "Judins Andrejs",
        ],
        "Jaunā Vienotība",
        ["JV", "jurists", "Juridiskā komisija"],
        f"Added {TODAY_LV} — P3 surname-collision fix. Juridiskās komisijas vadītājs 14. Saeimā; 11-13 Saeima arī bija deputāts.",
        "Judins Andrejs",
    ),
    (
        "Normunds Dzintars",
        [
            "Dzintars", "Dzintara", "Dzintaram",
            "Normunds Dzintars", "Dzintars Normunds",
        ],
        "Nacionālā apvienība",
        ["NA", "Liepāja", "izglītība"],
        f"Added {TODAY_LV} — P3 surname-collision fix. NA aizvietotājs (kad Indriksone bija Min.); latv. val. skolotājs Liepājas Valsts 1. ģimnāzijā.",
        "Dzintars Normunds",
    ),
    (
        "Inese Kalniņa",
        [
            "Kalniņa", "Kalniņas", "Kalniņai",
            "Inese Kalniņa", "Inese Kalnina", "Kalnina",
        ],
        "Jaunā Vienotība",
        ["JV", "LU Biznesa fakultāte", "ekonomika"],
        f"Added {TODAY_LV} — P3 surname-collision fix. LU Biznesa, vadības un ekonomikas fak. lektore; JV 14. Saeimā.",
        "Kalniņa Inese",
    ),
]


def _build_stance(deputy_vote: str, motif: str, summary: str | None) -> str:
    is_sentinel = bool(summary and summary.startswith("Kopsavilkums nav pieejams"))
    if summary and summary != motif and not is_sentinel:
        prefix = {
            'Par': 'Atbalsta', 'Pret': 'Iebilst pret',
            'Atturas': 'Atturējās balsojumā par', 'Nebalsoja': 'Nebalsoja par',
        }.get(deputy_vote, deputy_vote)
        s_lower = summary[0].lower() + summary[1:] if summary else ""
        return f"{prefix}: {s_lower}"
    vote_lv = {
        'Par': 'Balsoja PAR', 'Pret': 'Balsoja PRET',
        'Atturas': 'ATTURĒJĀS', 'Nebalsoja': 'NEBALSOJA',
    }
    return f"{vote_lv.get(deputy_vote, deputy_vote)}: {motif}"


def main() -> int:
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()

    inserted = []
    for name, name_forms, party, keywords, notes, snapshot_form in PAIRS:
        existing = cur.execute(
            "SELECT id FROM tracked_politicians WHERE name=?", (name,)
        ).fetchone()
        if existing:
            print(f"  SKIP {name} (pid={existing[0]} already)")
            inserted.append((existing[0], name, snapshot_form))
            continue
        cur.execute(
            """INSERT INTO tracked_politicians
               (name, name_forms, keywords, relationship_type, party, role, notes, negative_patterns)
               VALUES (?, ?, ?, 'inactive', ?, 'Saeimas deputāts (14. Saeima)', ?, '[]')""",
            (name, json.dumps(name_forms, ensure_ascii=False),
             json.dumps(keywords, ensure_ascii=False),
             party, notes),
        )
        new_pid = cur.lastrowid
        inserted.append((new_pid, name, snapshot_form))
        print(f"  INSERT pid={new_pid}  {name}  ({party})")

    db.commit()

    print()
    print("=== Reattributing iv rows ===")
    for pid, name, snap in inserted:
        # UPDATE iv WHERE deputy_name=snap → politician_id=pid
        before = cur.execute(
            "SELECT COUNT(*) FROM saeima_individual_votes WHERE deputy_name=?", (snap,)
        ).fetchone()[0]
        cur.execute(
            "UPDATE saeima_individual_votes SET politician_id=? WHERE deputy_name=?",
            (pid, snap),
        )
        updated = cur.rowcount
        print(f"  '{snap}' → pid={pid} ({name}):  total={before}  updated={updated}")
    db.commit()

    print()
    print("=== Generating retro claims for new pids ===")
    for pid, name, snap in inserted:
        rows = cur.execute(
            """
            SELECT iv.id, iv.deputy_name, iv.vote,
                   v.motif, v.url, v.summary,
                   v.vote_date, v.vote_time,
                   v.total_par, v.total_pret, v.total_atturas, v.total_nebalso
            FROM saeima_individual_votes iv
            JOIN saeima_votes v ON iv.vote_id = v.id
            WHERE iv.politician_id = ?
            """, (pid,)
        ).fetchall()

        created = 0
        for (iv_id, deputy_name, deputy_vote, motif, url, summary,
             vote_date, vote_time, total_par, total_pret,
             total_atturas, total_nebalso) in rows:
            topic = _motif_to_topic(motif or "")
            salience = _vote_salience(motif or "")
            full_url = _resolve_vote_url(url)
            stance = _build_stance(deputy_vote, motif or "", summary)
            reasoning = (
                f"Saeimas balsojums {vote_date}: {deputy_name} balsoja {deputy_vote}. "
                f"Kopējais rezultāts: par {total_par}, pret {total_pret}, "
                f"atturas {total_atturas}."
            )
            try:
                store_claim(
                    opponent_id=pid,
                    document_id=None,
                    topic=topic,
                    stance=stance,
                    quote=None,
                    confidence=1.0,
                    reasoning=reasoning,
                    salience=salience,
                    source_url=full_url,
                    stated_at=_parse_vote_datetime(vote_date, vote_time),
                    claim_type="saeima_vote",
                    db_path=DB_PATH,
                )
                created += 1
            except Exception as e:
                print(f"    FAIL iv_id={iv_id}: {e}")
        print(f"  pid={pid} {name[:25]:25s}  store_claim attempts={created}")

    # Final state check
    print()
    print("=== Final per-pid claim counts ===")
    for pid, name, _ in inserted:
        cnt = cur.execute(
            "SELECT COUNT(*) FROM claims WHERE opponent_id=? AND claim_type='saeima_vote'",
            (pid,)
        ).fetchone()[0]
        print(f"  pid={pid} {name[:25]:25s}  saeima_vote claims={cnt}")

    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
