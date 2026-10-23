"""Vienreizējs labojums: `saeima_bill_stages.stage_result` «Pieņemts» → «Likums» no titania.

Kāpēc: līdz ~2026-09 ielāde steidzama likumprojekta galīgajā (2.) lasījumā
ierakstīja «Pieņemts», nevis Saeimas iznākumu «Likums», tāpēc
`src.saeima.bills.derive_bill_denorm()` (kas «Likums» pareizi uzskata par galīgu
jebkurā lasījumā) atstāj pieņemtus likumus «procesā». Labojam IEVADDATUS no
patiesības avota (titania posmu tabula, `scripts/scrape_titania_bill_stages.py`
CSV), nevis noteikumu. Motīva heiristika («2.lasījums, steidzams») ir aizliegta:
steidzamību var atsaukt (1454/Lp14, 1455/Lp14).

Plāns: titania tabulā «N. lasījums» rezultāts ir «Likums» UN DB ir rinda
`stage_name='N.lasījums'` (bez «priekšlikums»), `stage_kind='vote'`, tas pats
datums, `stage_result='Pieņemts'` → `stage_result='Likums'`. Nekas cits.
`last_updated_at` NEmainās. `current_status` pēc tam pārrēķina
`scripts/recompute_bill_status.py` (savs plāns + sava atgriešana).

Drošība (kā `recompute_bill_status.py`): dry run (noklusējums) uzraksta
atgriešanas SQL ar plāna hash; `--apply` atsakās, ja plāns kopš tā mainījies;
atjaunināto skaitam jāsakrīt ar plānu, citādi transakcija atceļas.

Lietošana (`--db` obligāts):
    .venv/Scripts/python.exe scripts/backfill_bill_stage_result_from_titania.py --db data/atmina.db --rollback data/rollback_<x>.sql
    .venv/Scripts/python.exe scripts/backfill_bill_stage_result_from_titania.py --db data/atmina.db --rollback data/rollback_<x>.sql --apply
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DEFAULT_CSV = ROOT / "data" / "titania_bill_stages_2026-10-19.csv"
_READING_RE = re.compile(r"^(\d)\.\s*lasījums$")


def load_titania(csv_path: Path) -> list[dict]:
    with csv_path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def build_plan(db: sqlite3.Connection, titania_rows: list[dict]):
    """→ [(stage_id, bill_id, document_nr, stage_name, stage_date)], kārtots pēc stage_id."""
    plan = []
    for row in titania_rows:
        if row["error"]:
            continue
        bill = db.execute("SELECT id FROM saeima_bills WHERE document_nr = ?",
                          (row["document_nr"],)).fetchone()
        if bill is None:
            continue
        for st in json.loads(row["stages"]):
            m = _READING_RE.match(st["name"] or "")
            if not m or (st["result"] or "").strip() != "Likums" or not st["date"]:
                continue
            for s in db.execute(
                    "SELECT id, stage_name, stage_date FROM saeima_bill_stages "
                    "WHERE bill_id = ? AND stage_name = ? AND stage_kind = 'vote' "
                    "AND stage_date = ? AND stage_result = 'Pieņemts'",
                    (bill["id"], f"{m[1]}.lasījums", st["date"])).fetchall():
                plan.append((s["id"], bill["id"], row["document_nr"],
                             s["stage_name"], s["stage_date"]))
    return sorted(plan)


def plan_hash(plan) -> str:
    return hashlib.sha256(repr(plan).encode("utf-8")).hexdigest()[:16]


def rollback_sql(plan, db_path: str, csv_path: str, today: str) -> str:
    out = [
        "-- Forward: scripts/backfill_bill_stage_result_from_titania.py --apply —",
        "-- saeima_bill_stages.stage_result 'Pieņemts' → 'Likums' tur, kur titania",
        "-- posmu tabulā tā paša lasījuma (tā paša datuma) rezultāts ir «Likums».",
        "-- last_updated_at nemainās. current_status atgriež recompute_bill_status.py",
        "-- atgriešanas fails (piemēro TO pirms šī, ja tas jau piemērots).",
        f"-- Ģenerēts dry run {today} no DB: {db_path}; titania CSV: {csv_path}",
        "-- Apply date: nav piemērots (ieraksti datumu, kad piemēro).",
        f"-- plan-hash: {plan_hash(plan)} count: {len(plan)}",
        "BEGIN;",
    ]
    for sid, _bid, nr, _name, _date in plan:
        out.append(f"UPDATE saeima_bill_stages SET stage_result = 'Pieņemts' "
                   f"WHERE id = {sid} AND stage_result = 'Likums';  -- {nr}")
    out.append("COMMIT;")
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--db", required=True)
    ap.add_argument("--csv", default=str(DEFAULT_CSV))
    ap.add_argument("--rollback", required=True,
                    help="JAUNS fails katram labojumam — piemērotie ir iekomitēti")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)

    from datetime import date
    rows = load_titania(Path(args.csv))
    db = sqlite3.connect(args.db)
    db.row_factory = sqlite3.Row
    plan = build_plan(db, rows)
    bills = Counter(p[2] for p in plan)
    print(f"titania rindas: {len(rows)} (ar kļūdu: {sum(1 for r in rows if r['error'])}); "
          f"mainīsies posmi: {len(plan)}, likumprojekti: {len(bills)}")
    for name, n in sorted(Counter(p[3] for p in plan).items()):
        print(f"  {name}: {n}")
    status = {r["document_nr"]: r["titania_status"] for r in rows}
    print("  plāna likumprojektu titania statuss:")
    for st, n in Counter(status.get(nr, "") for nr in bills).most_common():
        print(f"    {st}: {n}")
    for nr in sorted(bills):
        if status.get(nr) != "Izsludināts":
            print(f"  KAROGS — nav «Izsludināts»: {nr} ({status.get(nr)!r})")
    for nr, n in sorted(bills.items()):
        if n > 1:
            print(f"  VAIRĀKI posmi vienam likumprojektam: {nr} × {n}")
    print(f"plan-hash: {plan_hash(plan)}")

    rb = Path(args.rollback)
    if not args.apply:
        rb.write_text(rollback_sql(plan, args.db, args.csv, date.today().isoformat()),
                      encoding="utf-8")
        print(f"DRY RUN — nekas nav mainīts. Atgriešanas SQL: {rb}")
        return 0

    if not rb.exists():
        print(f"ATTEIKTS: nav atgriešanas faila {rb} — vispirms dry run + commit.")
        return 1
    header = next((ln for ln in rb.read_text(encoding="utf-8").splitlines()
                   if ln.startswith("-- plan-hash:")), "")
    if f"plan-hash: {plan_hash(plan)} count: {len(plan)}" not in header:
        print(f"ATTEIKTS: plāns mainījies kopš dry run ({header!r}) — ģenerē atgriešanas failu no jauna.")
        return 1
    with db:
        n = 0
        for sid, _bid, _nr, _name, _date in plan:
            n += db.execute(
                "UPDATE saeima_bill_stages SET stage_result = 'Likums' "
                "WHERE id = ? AND stage_result = 'Pieņemts' AND stage_kind = 'vote'",
                (sid,)).rowcount
        if n != len(plan):
            raise RuntimeError(f"atjaunināti {n} no {len(plan)} — transakcija atcelta")
    print(f"PIEMĒROTS: {n} posmi. Atgriešana: sqlite3 {args.db} < {rb}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
