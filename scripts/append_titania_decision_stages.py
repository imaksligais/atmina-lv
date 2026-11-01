"""Ieraksta Saeimas lēmumus BEZ balsojuma kā posmu `stage_kind='decision'` no titania.

Kāpēc (2026-10-20): daļai lēmumu projektu un pieprasījumu Saeima lēmumu
pieņēma bez balsojuma (termiņa pagarinājums, steidzamības atcelšana, paziņojums
par deputāta pilnvarām) vai dokuments tika atsaukts («Atsaukts», «Atsaukts:
X atsauc parakstu»). Balsojuma nav, tāpēc posma nebija un statuss palika
«procesā». Vienīgais avots ir titania posmu tabula
(`scripts/scrape_titania_bill_stages.py` CSV). Raksta TIKAI caur
`src.saeima.append_bill_stage(stage_kind='decision')` — CLAUDE.md inv. #12
viens rakstītājs; statusu izlemj `derive_bill_denorm()`.

Plāns katram saraksta numuram: titania pēdējais posms ar iznākumu un datumu.
- «Atsaukts…» → posms `atsaukts`, stage_result = titania vārds burtiski;
- Lm + «Pieņemts»/«Izskatīts»/«Paziņojums» → posms `Lm14 cits` (vēsturiskā
  etiķete visiem sasaukumiem), stage_result = titania vārds;
- citādi ATTEIKTS. Atteikts arī, ja tajā datumā ir balsojums ar šo
  document_nr vai šo numuru motīvā (tas ir balsojums, ne lēmums bez tā) vai
  ja šāds posms jau ir.
`last_updated_at` NEmainās (`touch_updated_at=False`, 2026-10-20) — vēsturisks
lēmums nav jauna aktivitāte, un pēc tā kārto `likumprojekti.html`.

Drošība (kā `link_unbound_votes_to_bills.py`): saraksts obligāts; dry run
(noklusējums) izdrukā plānu + prognozi (tas pats `append_bill_stage()` uz
pagaidu apakškopas kopijas) + plāna hash un uzraksta atgriešanas SQL;
`--apply` atsakās, ja hash mainījies; pēc tam pārbauda ievietoto skaitu.

Lietošana:
    .venv/Scripts/python.exe scripts/append_titania_decision_stages.py --db data/atmina.db --nr-file nr.txt --rollback data/rollback_<x>.sql
    .venv/Scripts/python.exe scripts/append_titania_decision_stages.py --db data/atmina.db --nr-file nr.txt --rollback data/rollback_<x>.sql --apply
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sqlite3
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.db import init_db  # noqa: E402
from src.saeima import init_saeima_bills, init_saeima_tables  # noqa: E402
from src.saeima.bills import append_bill_stage  # noqa: E402

DEFAULT_CSV = ROOT / "data" / "titania_bill_stages_2026-10-19.csv"
_ADOPTED = ("Pieņemts", "Izskatīts", "Paziņojums")


def load_titania(csv_path: Path) -> dict[str, dict]:
    with csv_path.open(encoding="utf-8", newline="") as f:
        return {r["document_nr"]: r for r in csv.DictReader(f)}


def build_plan(db: sqlite3.Connection, titania: dict[str, dict], nrs: list[str]):
    """→ (plan, snapshot, refused).

    plan:     [(bill_id, document_nr, stage_name, stage_result, stage_date)]
    snapshot: [(bill_id, document_nr, current_stage, current_status, last_updated_at)]
    refused:  [(document_nr, reason)]
    """
    plan, snapshot, refused = [], [], []
    for nr in sorted(set(nrs)):
        b = db.execute("SELECT id, bill_type, current_stage, current_status, last_updated_at "
                       "FROM saeima_bills WHERE document_nr=?", (nr,)).fetchone()
        row = titania.get(nr)
        if b is None:
            refused.append((nr, "nav saeima_bills rindas"))
            continue
        if row is None or row["error"]:
            refused.append((nr, "nav titania rindas (vai kļūda)"))
            continue
        done = [s for s in json.loads(row["stages"]) if s.get("result") and s.get("date")]
        if not done:
            refused.append((nr, "titanijā nav posma ar iznākumu"))
            continue
        last = max(enumerate(done), key=lambda t: (t[1]["date"], t[0]))[1]
        result, sdate = last["result"].strip(), last["date"]
        if result.startswith("Atsaukts"):
            stage = "atsaukts"
        elif b["bill_type"].startswith("Lm") and result in _ADOPTED:
            stage = "Lm14 cits"
        else:
            refused.append((nr, f"iznākums {result!r} nav lēmums bez balsojuma šim veidam"))
            continue
        # Balsojums var būt piesaistīts SAISTĪTAJAM likumprojektam (1056/Lm14 →
        # 1352/Lp14: document_nr ir Lp, numurs tikai motīvā) — meklē abos.
        if db.execute("SELECT 1 FROM saeima_votes WHERE vote_date=? AND "
                      "(document_nr=? OR motif LIKE ?)", (sdate, nr, f"%({nr})%")).fetchone():
            refused.append((nr, f"{sdate} ir balsojums — tas nav lēmums bez balsojuma"))
            continue
        if db.execute("SELECT 1 FROM saeima_bill_stages WHERE bill_id=? AND stage_name=? "
                      "AND stage_date=?", (b["id"], stage, sdate)).fetchone():
            refused.append((nr, "šāds posms jau ir"))
            continue
        plan.append((b["id"], nr, stage, result, sdate))
        snapshot.append((b["id"], nr, b["current_stage"], b["current_status"],
                         b["last_updated_at"]))
    return plan, snapshot, refused


def plan_hash(plan, snapshot) -> str:
    return hashlib.sha256(repr((plan, snapshot)).encode("utf-8")).hexdigest()[:16]


def apply_plan(db_path: str, plan) -> None:
    for bid, _nr, stage, result, sdate in plan:
        append_bill_stage(db_path, bid, stage, result, sdate, stage_kind="decision",
                          touch_updated_at=False)


def predict(src_db: sqlite3.Connection, plan) -> dict[int, tuple]:
    """Piemēro plānu pagaidu apakškopas DB → {bill_id: (stage, status)}."""
    ids = sorted({p[0] for p in plan})
    if not ids:
        return {}
    marks = ",".join("?" * len(ids))
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
        tmp = str(Path(td) / "predict.db")
        init_db(tmp)
        init_saeima_tables(tmp)
        init_saeima_bills(tmp)
        t = sqlite3.connect(tmp)
        for table, where in (
            ("saeima_bills", f"id IN ({marks})"),
            ("saeima_bill_stages", f"bill_id IN ({marks})"),
            ("saeima_votes", f"id IN (SELECT vote_id FROM saeima_bill_stages WHERE bill_id IN ({marks}))"),
        ):
            src_cols = {c[1] for c in src_db.execute(f"PRAGMA table_info({table})")}
            cols = [c[1] for c in t.execute(f"PRAGMA table_info({table})") if c[1] in src_cols]
            rows = src_db.execute(f"SELECT {','.join(cols)} FROM {table} WHERE {where}", ids).fetchall()
            t.executemany(f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                          [tuple(r) for r in rows])
        t.execute("UPDATE saeima_bill_stages SET session_id=NULL")
        t.execute("UPDATE saeima_votes SET agenda_item_id=NULL")
        t.commit()
        t.close()
        apply_plan(tmp, plan)
        t = sqlite3.connect(tmp)
        out = {r[0]: (r[1], r[2]) for r in t.execute(
            f"SELECT id, current_stage, current_status FROM saeima_bills WHERE id IN ({marks})", ids)}
        t.close()
    return out


def _q(v) -> str:
    return "NULL" if v is None else "'" + str(v).replace("'", "''") + "'"


def rollback_sql(plan, snapshot, db_path: str, csv_path: str, today: str) -> str:
    out = [
        "-- Forward: scripts/append_titania_decision_stages.py --apply —",
        "-- Saeimas lēmumi bez balsojuma ierakstīti kā saeima_bill_stages",
        "-- (stage_kind='decision', stage_result = titania vārds) caur",
        "-- append_bill_stage(); saeima_bills.current_stage/current_status/",
        "-- last_updated_at pārrēķināti.",
        "-- Atgriešana: decision posmi dzēsti pēc (bill_id, stage_name, stage_date,",
        "-- stage_result); likumprojekta lauki → dry run brīža vērtības.",
        f"-- Ģenerēts dry run {today} no DB: {db_path}; titania CSV: {csv_path}",
        "-- Apply date: nav piemērots (ieraksti datumu, kad piemēro).",
        f"-- plan-hash: {plan_hash(plan, snapshot)} count: {len(plan)}",
        "BEGIN;",
    ]
    snap = {s[0]: s for s in snapshot}
    for bid, nr, stage, result, sdate in plan:
        _b, _nr, old_stage, old_status, old_ts = snap[bid]
        out.append(f"-- {nr}")
        out.append(f"DELETE FROM saeima_bill_stages WHERE bill_id = {bid} AND stage_kind = 'decision' "
                   f"AND stage_name = {_q(stage)} AND stage_date = {_q(sdate)} "
                   f"AND stage_result = {_q(result)};")
        out.append(f"UPDATE saeima_bills SET current_stage = {_q(old_stage)}, "
                   f"current_status = {_q(old_status)}, last_updated_at = {_q(old_ts)} "
                   f"WHERE id = {bid};")
    out.append("COMMIT;")
    return "\n".join(out) + "\n"


def _read_nrs(args) -> list[str]:
    nrs = list(args.document_nr or [])
    if args.nr_file:
        for ln in Path(args.nr_file).read_text(encoding="utf-8").splitlines():
            ln = ln.strip()
            if ln and not ln.startswith("#"):
                nrs.append(ln)
    return nrs


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--db", required=True)
    ap.add_argument("--csv", default=str(DEFAULT_CSV))
    ap.add_argument("--document-nr", action="append", help="piem. 994/Lm14 (atkārtojams)")
    ap.add_argument("--nr-file", help="fails ar vienu document_nr rindā")
    ap.add_argument("--rollback", required=True,
                    help="JAUNS fails katram skrējienam — piemērotie ir iekomitēti")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)

    nrs = _read_nrs(args)
    if not nrs:
        print("ATTEIKTS: nav saraksta (--document-nr / --nr-file).")
        return 2

    db = sqlite3.connect(args.db)
    db.row_factory = sqlite3.Row
    plan, snapshot, refused = build_plan(db, load_titania(Path(args.csv)), nrs)
    h = plan_hash(plan, snapshot)
    print(f"saraksts: {len(set(nrs))}; plānoti lēmumi: {len(plan)}; atteikti: {len(refused)}")
    for nr, why in refused:
        print(f"  ATTEIKTS {nr}: {why}")
    if not args.apply:
        pred = predict(db, plan)
        snap = {s[0]: s for s in snapshot}
        for bid, nr, stage, result, sdate in plan:
            s = snap[bid]
            print(f"  {nr}: + {stage} «{result}» {sdate}  {s[2]}/{s[3]} → "
                  f"{pred[bid][0]}/{pred[bid][1]}")
    print(f"plan-hash: {h}")

    rb = Path(args.rollback)
    if not args.apply:
        db.close()
        rb.write_text(rollback_sql(plan, snapshot, args.db, args.csv, date.today().isoformat()),
                      encoding="utf-8")
        print(f"DRY RUN — nekas nav mainīts. Atgriešanas SQL: {rb}")
        return 0

    db.close()
    if not rb.exists():
        print(f"ATTEIKTS: nav atgriešanas faila {rb} — vispirms dry run + commit.")
        return 1
    header = next((ln for ln in rb.read_text(encoding="utf-8").splitlines()
                   if ln.startswith("-- plan-hash:")), "")
    if f"plan-hash: {h} count: {len(plan)}" not in header:
        print(f"ATTEIKTS: plāns mainījies kopš dry run ({header!r}) — ģenerē atgriešanas failu no jauna.")
        return 1

    apply_plan(args.db, plan)

    db = sqlite3.connect(args.db)
    n = sum(db.execute("SELECT COUNT(*) FROM saeima_bill_stages WHERE bill_id=? AND "
                       "stage_kind='decision' AND stage_name=? AND stage_date=? AND stage_result=?",
                       (bid, stage, sdate, result)).fetchone()[0]
            for bid, _nr, stage, result, sdate in plan)
    db.close()
    print(f"PĀRBAUDE: decision posmi {n}/{len(plan)}")
    if n != len(plan):
        print(f"KĻŪDA: neatbilst plānam — atgriešana: sqlite3 {args.db} < {rb}")
        return 1
    print(f"PIEMĒROTS: {n} lēmumi. Atgriešana: sqlite3 {args.db} < {rb}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
