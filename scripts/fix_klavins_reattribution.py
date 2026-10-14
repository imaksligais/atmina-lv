"""Reattribute Līga Kļaviņa's votes from journalist id191 → deputy id104.

Root cause: journalist "Krišjānis Kļaviņš" (id 191) carried the feminine
surname form "Kļaviņa" in ``name_forms``. The Saeima vote ledger records
deputy "Kļaviņa Līga" (surname-first format) for the real deputy Līga
Kļaviņa (id 104). The matcher routed all 4161 surname-first rows to the
journalist instead of the deputy, while the name-first "Līga Kļaviņa"
rows (1176) went to the correct id 104.

This script moves both the raw vote ledger rows and the derived
``saeima_vote`` claims from 191 → 104, then strips the feminine forms
from the journalist's ``name_forms`` and adds a negative pattern so a
future re-scrape can't re-absorb them. The journalist's own 25
``position`` claims are untouched.

Idempotent: re-running after a successful pass is a no-op (no rows left
on 191 with deputy_name 'Kļaviņa Līga').

Usage:
    .venv/Scripts/python.exe scripts/fix_klavins_reattribution.py [--apply]

Without --apply it prints the plan (dry run). With --apply it mutates
``data/atmina.db`` inside a single transaction and writes a rollback SQL
file to data/.
"""
from __future__ import annotations

import json
import sqlite3
import sys

DB = "data/atmina.db"
JOURNALIST = 191  # Krišjānis Kļaviņš
DEPUTY = 104      # Līga Kļaviņa
DEPUTY_NAME = "Kļaviņa Līga"  # surname-first ledger format that mis-routed


def main(apply: bool) -> None:
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row

    j = db.execute("SELECT id, name, relationship_type, role, name_forms, negative_patterns "
                   "FROM tracked_politicians WHERE id=?", (JOURNALIST,)).fetchone()
    d = db.execute("SELECT id, name, relationship_type, role FROM tracked_politicians WHERE id=?",
                   (DEPUTY,)).fetchone()
    assert j and j["relationship_type"] == "journalist", "id191 precondition failed"
    assert d and d["name"] == "Līga Kļaviņa", "id104 precondition failed"

    iv = db.execute("SELECT COUNT(*) FROM saeima_individual_votes "
                    "WHERE politician_id=? AND deputy_name=?", (JOURNALIST, DEPUTY_NAME)).fetchone()[0]
    iv_other = db.execute("SELECT COUNT(*) FROM saeima_individual_votes "
                          "WHERE politician_id=? AND deputy_name!=?", (JOURNALIST, DEPUTY_NAME)).fetchone()[0]
    sv = db.execute("SELECT COUNT(*) FROM claims WHERE opponent_id=? AND claim_type='saeima_vote'",
                    (JOURNALIST,)).fetchone()[0]
    pos = db.execute("SELECT COUNT(*) FROM claims WHERE opponent_id=? AND claim_type='position'",
                     (JOURNALIST,)).fetchone()[0]

    # vote_id overlap that would create logical duplicates on the deputy
    overlap = db.execute(
        "SELECT COUNT(*) FROM saeima_individual_votes a "
        "WHERE a.politician_id=? AND a.deputy_name=? AND a.vote_id IN "
        "(SELECT vote_id FROM saeima_individual_votes WHERE politician_id=?)",
        (JOURNALIST, DEPUTY_NAME, DEPUTY)).fetchone()[0]

    print(f"journalist id{JOURNALIST}: {j['name']} ({j['role']})")
    print(f"deputy     id{DEPUTY}: {d['name']} ({d['role']})")
    print(f"  individual votes to move (deputy_name='{DEPUTY_NAME}'): {iv}")
    print(f"  individual votes that STAY on journalist (other name):  {iv_other}")
    print(f"  saeima_vote claims to move: {sv}")
    print(f"  position claims kept on journalist: {pos}")
    print(f"  vote_id overlap with deputy (logical dupes): {overlap}")

    if iv_other:
        # Safety: there should be NO non-Kļaviņa-Līga votes on a journalist.
        rows = db.execute("SELECT DISTINCT deputy_name FROM saeima_individual_votes "
                          "WHERE politician_id=? AND deputy_name!=?", (JOURNALIST, DEPUTY_NAME)).fetchall()
        print("  WARNING: journalist also holds votes for:", [r[0] for r in rows])

    if not apply:
        print("\n[dry run] pass --apply to mutate the DB")
        return

    # Capture rollback set: the exact siv ids and claim ids being moved.
    moved_iv = [r[0] for r in db.execute(
        "SELECT id FROM saeima_individual_votes WHERE politician_id=? AND deputy_name=?",
        (JOURNALIST, DEPUTY_NAME)).fetchall()]
    moved_claims = [r[0] for r in db.execute(
        "SELECT id FROM claims WHERE opponent_id=? AND claim_type='saeima_vote'",
        (JOURNALIST,)).fetchall()]

    # name_forms hygiene: drop feminine surname forms from the journalist.
    forms = json.loads(j["name_forms"] or "[]")
    feminine = {"Kļaviņa", "Klaviņa", "Klavina"}
    new_forms = [f for f in forms if f not in feminine]
    neg = json.loads(j["negative_patterns"] or "[]")
    for pat in ("Kļaviņa Līga", "Līga Kļaviņa"):
        if pat not in neg:
            neg.append(pat)

    try:
        db.execute("BEGIN")
        db.execute("UPDATE saeima_individual_votes SET politician_id=? "
                   "WHERE politician_id=? AND deputy_name=?", (DEPUTY, JOURNALIST, DEPUTY_NAME))
        db.execute("UPDATE claims SET opponent_id=? "
                   "WHERE opponent_id=? AND claim_type='saeima_vote'", (DEPUTY, JOURNALIST))
        db.execute("UPDATE tracked_politicians SET name_forms=?, negative_patterns=? WHERE id=?",
                   (json.dumps(new_forms, ensure_ascii=False),
                    json.dumps(neg, ensure_ascii=False), JOURNALIST))
        db.execute("COMMIT")
    except Exception:
        db.execute("ROLLBACK")
        raise

    rb = "data/rollback_klavins_reattribution.sql"
    with open(rb, "w", encoding="utf-8") as f:
        f.write(f"-- reverse reattribution {DEPUTY}->{JOURNALIST}\n")
        if moved_iv:
            ids = ",".join(map(str, moved_iv))
            f.write(f"UPDATE saeima_individual_votes SET politician_id={JOURNALIST} WHERE id IN ({ids});\n")
        if moved_claims:
            ids = ",".join(map(str, moved_claims))
            f.write(f"UPDATE claims SET opponent_id={JOURNALIST} WHERE id IN ({ids});\n")
        old_neg = j["negative_patterns"] or "[]"
        f.write(f"UPDATE tracked_politicians SET name_forms='{j['name_forms']}', "
                f"negative_patterns='{old_neg}' WHERE id={JOURNALIST};\n")

    # verify
    after_j = db.execute("SELECT COUNT(*) FROM saeima_individual_votes WHERE politician_id=?",
                         (JOURNALIST,)).fetchone()[0]
    after_d = db.execute("SELECT COUNT(*) FROM saeima_individual_votes WHERE politician_id=?",
                         (DEPUTY,)).fetchone()[0]
    after_jsv = db.execute("SELECT COUNT(*) FROM claims WHERE opponent_id=? AND claim_type='saeima_vote'",
                           (JOURNALIST,)).fetchone()[0]
    print(f"\nAPPLIED. moved {len(moved_iv)} votes + {len(moved_claims)} claims.")
    print(f"  journalist votes now: {after_j} (saeima_vote claims: {after_jsv})")
    print(f"  deputy votes now: {after_d}")
    print(f"  rollback written: {rb}")
    db.close()


if __name__ == "__main__":
    main("--apply" in sys.argv)
