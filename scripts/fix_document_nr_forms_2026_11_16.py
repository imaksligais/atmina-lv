#!/usr/bin/env python
"""Vienreizējs labojums: `saeima_votes.document_nr` vienā formā (backlog/saeima.md,
«Vienam likumprojektam vairākas `document_nr` formas vai NULL», 2026-11-13).

Divas klases, abas tikai no ielādēm līdz 2026-08 (kopš 2026-09 ielāde tās nerada):
  1. bez sufiksa («1393» blakus «1393/Lp14») — pilno formu ņem no motīva;
  2. NULL, bet motīvā ir tieši VIENS numurs «NNNN/Lp14|Lm14|P14»;
  3. NULL, motīvā kails «(NNNN)», kam `saeima_bills` dod tieši vienu formu.
Tēmas atslēga (`src.saeima.topics.document_key`) visām rindām paliek tā pati — tā
jau tagad šīs formas atrisina no motīva. Izlaiž: motīvā vairāki dažādi numuri; numurs nesakrīt ar `saeima_bills.document_nr`
tā paša `bill_id` rindai. `bill_id` / `current_stage` neaiztiek (inv #12).

    .venv/Scripts/python.exe scripts/fix_document_nr_forms_2026_11_16.py            # dry-run
    .venv/Scripts/python.exe scripts/fix_document_nr_forms_2026_11_16.py --write    # forward + rollback SQL
    git commit data/rollback_document_nr_forms_2026-11-16.sql                       # PIRMS apply
    sqlite3 <db> < data/fix_document_nr_forms_2026-11-16.sql                        # tikai ar operatora «jā»
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src.db import get_db  # noqa: E402

NR = re.compile(r"(?<!\d)(\d+/(?:Lp|Lm|P)14)(?![\w/])")
BARE = re.compile(r"\((\d{3,4})\)")
FORWARD = REPO / "data" / "fix_document_nr_forms_2026-11-16.sql"
ROLLBACK = REPO / "data" / "rollback_document_nr_forms_2026-11-16.sql"


def plan(db) -> tuple[list[tuple[int, str | None, str]], list[tuple[int, str]]]:
    bills = {r[0]: r[1] for r in db.execute("SELECT id, document_nr FROM saeima_bills")}
    fixes, skipped = [], []
    rows = db.execute(
        "SELECT id, document_nr, motif, bill_id FROM saeima_votes "
        "WHERE document_nr IS NULL OR document_nr NOT LIKE '%/%' ORDER BY id"
    ).fetchall()
    for vid, old, motif, bill_id in rows:
        found = sorted(set(NR.findall(motif or "")))
        if not found and old is None:
            # 3. klase: kails «(1149)» motīvā, ja `saeima_bills` tam dod tieši vienu formu (6449)
            bare = set(BARE.findall(motif or ""))
            if len(bare) == 1:
                n = bare.pop()
                found = [b for b in bills.values() if b and b.split("/")[0] == n]
                if len(found) != 1:
                    found = []
        if old is not None:
            found = [n for n in found if n.split("/")[0] == old]
        if len(found) != 1:
            if found or old is not None:
                skipped.append((vid, f"numuri motīvā: {found or 'nav'}"))
            continue
        new = found[0]
        if bill_id is not None and bills.get(bill_id) not in (None, new):
            skipped.append((vid, f"{new} ≠ saeima_bills #{bill_id} {bills.get(bill_id)}"))
            continue
        fixes.append((vid, old, new))
    return fixes, skipped


def _q(v: str | None) -> str:
    return "NULL" if v is None else "'" + v.replace("'", "''") + "'"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="uzraksta forward un rollback SQL")
    args = ap.parse_args()
    db = get_db()
    try:
        fixes, skipped = plan(db)
    finally:
        db.close()
    n_suffix = sum(1 for _, old, _ in fixes if old is not None)
    print(f"labojamas {len(fixes)} rindas (bez sufiksa {n_suffix}, NULL {len(fixes) - n_suffix}); "
          f"izlaistas {len(skipped)}")
    for vid, why in skipped:
        print(f"  izlaista {vid}: {why}")
    if not args.write:
        print("Dry-run — nekas nav rakstīts.")
        return 0
    ids = ",".join(str(v) for v, _, _ in fixes)
    head = (f"-- Forward: saeima_votes.document_nr vienā formā {len(fixes)} rindām "
            "(scripts/fix_document_nr_forms_2026_11_16.py). bill_id netiek aiztikts.\n")
    FORWARD.write_text(
        head + "-- Apply date: tikai pēc operatora «jā».\nBEGIN;\n"
        + "".join(f"UPDATE saeima_votes SET document_nr = {_q(new)} WHERE id = {vid} "
                  f"AND document_nr IS {_q(old)};\n" for vid, old, new in fixes)
        + "COMMIT;\n"
        + f"-- Pārbaude: SELECT count(*) FROM saeima_votes WHERE id IN ({ids}) "
          "AND document_nr LIKE '%/%'  → jābūt " + str(len(fixes)) + "\n",
        encoding="utf-8")
    ROLLBACK.write_text(
        "-- Rollback: " + head[len("-- Forward: "):] + "BEGIN;\n"
        + "".join(f"UPDATE saeima_votes SET document_nr = {_q(old)} WHERE id = {vid};\n"
                  for vid, old, _ in fixes)
        + "COMMIT;\n", encoding="utf-8")
    print(f"Uzrakstīts: {FORWARD.name}, {ROLLBACK.name}. Commitē rollback PIRMS apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
