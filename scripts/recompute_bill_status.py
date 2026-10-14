"""Vienreizējs pārrēķins: `saeima_bills.current_stage` / `current_status` no posmiem.

Kāpēc: līdz 2026-10-09 `append_bill_stage()` Saeimas iznākumu «Likums» (likums
pieņemts galīgajā lasījumā; steidzamam — 2. lasījumā) atstāja `procesā`, un
10-09 posmu kārtības maiņa (priekšlikums neaizstāj tās pašas dienas lasījumu)
neskāra jau ierakstītās rindas; 2026-10-09 (2) — `tiesneša_amats` «Pieņemts» ir galīgs. Noteikums dzīvo VIENĀ vietā —
`src.saeima.bills.derive_bill_denorm()`; šis skripts to tikai piemēro vecajām
rindām. CLAUDE.md inv. #12 nosauktais izņēmums.

`last_updated_at` NEmainās — jauns posms nav noticis, un tas kārto lapas.

Drošība (kā `fix_saeima_stance_propnoun_case.py`): dry run (noklusējums)
uzraksta atgriešanas SQL ar plāna hash; `--apply` atsakās, ja plāns kopš tā
mainījies; atjaunināto skaitam jāsakrīt ar plānu, citādi transakcija atceļas.

Lietošana (`--db` obligāts):
    .venv/Scripts/python.exe scripts/recompute_bill_status.py --db data/atmina.db --rollback data/rollback_<x>.sql
    .venv/Scripts/python.exe scripts/recompute_bill_status.py --db data/atmina.db --rollback data/rollback_<x>.sql --apply
"""

from __future__ import annotations

import argparse
import hashlib
import sqlite3
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.saeima.bills import derive_bill_denorm  # noqa: E402

def build_plan(db: sqlite3.Connection):
    """→ [(bill_id, document_nr, old_stage, old_status, new_stage, new_status)]."""
    plan = []
    for b in db.execute("SELECT id, document_nr, current_stage, current_status "
                        "FROM saeima_bills ORDER BY id").fetchall():
        stage, status = derive_bill_denorm(db, b["id"])
        if stage is None:
            continue  # nav neviena balsojuma posma — nav ko pārrēķināt
        if (stage, status) != (b["current_stage"], b["current_status"]):
            plan.append((b["id"], b["document_nr"], b["current_stage"],
                         b["current_status"], stage, status))
    return plan


def plan_hash(plan) -> str:
    return hashlib.sha256(repr(plan).encode("utf-8")).hexdigest()[:16]


def _q(v) -> str:
    return "NULL" if v is None else "'" + str(v).replace("'", "''") + "'"


def rollback_sql(plan, db_path: str, today: str) -> str:
    out = [
        "-- Forward: scripts/recompute_bill_status.py --apply —",
        "-- saeima_bills.current_stage/current_status pārrēķināti ar",
        "-- src.saeima.bills.derive_bill_denorm() («Likums» → pieņemts; priekšlikums",
        "-- neaizstāj tās pašas dienas lasījumu). last_updated_at nemainās.",
        f"-- Ģenerēts dry run {today} no DB: {db_path}",
        "-- Apply date: nav piemērots (ieraksti datumu, kad piemēro).",
        f"-- plan-hash: {plan_hash(plan)} count: {len(plan)}",
        "BEGIN;",
    ]
    for bid, _nr, old_stage, old_status, new_stage, new_status in plan:
        out.append(
            f"UPDATE saeima_bills SET current_stage = {_q(old_stage)}, "
            f"current_status = {_q(old_status)} WHERE id = {bid} "
            f"AND current_stage = {_q(new_stage)} AND current_status = {_q(new_status)};")
    out.append("COMMIT;")
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--db", required=True)
    ap.add_argument("--rollback", required=True,
                    help="JAUNS fails katram pārrēķinam — piemērotie ir iekomitēti")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)

    from datetime import date
    db = sqlite3.connect(args.db)
    db.row_factory = sqlite3.Row
    plan = build_plan(db)
    total = db.execute("SELECT COUNT(*) FROM saeima_bills").fetchone()[0]
    print(f"saeima_bills: {total}; mainīsies: {len(plan)}")
    for (os_, ns), n in sorted(Counter((p[3], p[5]) for p in plan).items()):
        print(f"  status {os_} → {ns}: {n}")
    print(f"  tikai current_stage: {sum(1 for p in plan if p[3] == p[5])}")
    for p in plan:
        if p[3] != "procesā" or p[5] != "pieņemts":
            print(f"  {p[1]}: {p[2]}/{p[3]} → {p[4]}/{p[5]}")
    print(f"plan-hash: {plan_hash(plan)}")

    rb = Path(args.rollback)
    if not args.apply:
        rb.write_text(rollback_sql(plan, args.db, date.today().isoformat()), encoding="utf-8")
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
        for bid, _nr, old_stage, old_status, new_stage, new_status in plan:
            n += db.execute(
                "UPDATE saeima_bills SET current_stage = ?, current_status = ? "
                "WHERE id = ? AND current_stage IS ? AND current_status IS ?",
                (new_stage, new_status, bid, old_stage, old_status)).rowcount
        if n != len(plan):
            raise RuntimeError(f"atjaunināti {n} no {len(plan)} — transakcija atcelta")
    print(f"PIEMĒROTS: {n} likumprojekti. Atgriešana: sqlite3 {args.db} < {rb}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
