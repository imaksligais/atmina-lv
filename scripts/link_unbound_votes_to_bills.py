"""Piesaista likumprojektam balsojumus ar `bill_id IS NULL` caur `append_bill_stage()`.

Kāpēc: Saeimas ielāde dažiem balsojumiem izlaida soli «piesaistīt balsojumu
likumprojektam» — `saeima_votes.bill_id` palika NULL, lai gan `saeima_bills`
rinda ar to pašu `document_nr` eksistē. Galīgā lasījuma balsojums tāpēc nekļuva
par posmu, un likums rādās «procesā». Šis skripts katram tādam balsojumam
izsauc `src.saeima.append_bill_stage()` — vienīgo `bill_id` / `current_stage` /
`current_status` rakstītāju (CLAUDE.md inv. #12; izņēmums nav vajadzīgs).
`touch_updated_at=False`: `last_updated_at` NEmainās — pēc tā kārto
`likumprojekti.html`, un vecs balsojums nav jauna aktivitāte (līdz 2026-10-20
skripts to uzlika uz `now_lv()`, un piesaistītie likumprojekti uzlēca augšā).

Vecais `scripts/backfill_saeima_bills.py` (izdzēsts 2026-10-20) izsauca `upsert_bill(summary=…)`
un tāpēc pārrakstīja likumprojektu kopsavilkumus/nosaukumus.

Drošība (kā `recompute_bill_status.py`):
- saraksts (`--document-nr` / `--nr-file`) ir OBLIGĀTS — pa visiem likumprojektiem
  bez skaidra saraksta skripts neiet;
- dry run (noklusējums) izdrukā plānu, prognozi un plāna hash, un uzraksta
  atgriešanas SQL; prognoze = tas pats `append_bill_stage()` uz pagaidu KOPIJAS
  (tikai mērķa likumprojekti, to posmi un balsojumi — `derive_bill_denorm()`
  lasa tikai `saeima_bill_stages WHERE bill_id=?`, tāpēc apakškopa dod to pašu
  rezultātu; 2,9 GB kopija katram dry run nav vajadzīga);
- `--apply` atsakās, ja hash (plāns + likumprojektu stāvoklis pirms) kopš dry
  run mainījies; pēc tam pārbauda: ievietoto posmu skaits == plānotais un katram
  plānotajam balsojumam ir `bill_id`. Citādi izeja ≠ 0.
- `append_bill_stage()` katru balsojumu iekomitē atsevišķi — kļūme pusceļā
  atstāj daļēju stāvokli; atgriešanas SQL (atslēga = vote_id) sedz arī to.

`--shared` (2026-10-20, operatora lēmums): «viens balsojums, divi dokumenti» —
lēmuma projekts par likumprojektu (1056/Lm14 ↔ 1352/Lp14). Ņem balsojumus, kas
jau piesaistīti CITAM likumprojektam un kuru motīvā ir «(<nr>)», un pievieno
posmu ar `append_bill_stage(keep_vote_bill_id=True)` — `saeima_votes.bill_id`
NEmainās (atgriešanas `bill_id → NULL` rinda tad neko neskar).

Lietošana:
    .venv/Scripts/python.exe scripts/link_unbound_votes_to_bills.py --nr-file nr.txt --rollback data/rollback_<x>.sql
    .venv/Scripts/python.exe scripts/link_unbound_votes_to_bills.py --nr-file nr.txt --rollback data/rollback_<x>.sql --apply
"""

from __future__ import annotations

import argparse
import hashlib
import sqlite3
import sys
import tempfile
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.db import PRODUCTION_DB_PATH, init_db  # noqa: E402
from src.saeima import init_saeima_bills, init_saeima_tables  # noqa: E402
from src.saeima.bills import (  # noqa: E402
    _canonicalize_stage_name,
    _reading_from_motif,
    append_bill_stage,
)


def build_plan(db: sqlite3.Connection, nrs: list[str], shared: bool = False):
    """→ (plan, snapshot, excluded, missing).

    plan:     [(bill_id, document_nr, vote_id, stage_name, result, vote_date)]
    snapshot: [(bill_id, document_nr, current_stage, current_status, last_updated_at)]
    excluded: [(document_nr, vote_id, stage_name, reason)]
    missing:  document_nr bez saeima_bills rindas
    """
    plan, snapshot, excluded, missing = [], [], [], []
    for nr in sorted(set(nrs)):
        b = db.execute(
            "SELECT id, current_stage, current_status, last_updated_at "
            "FROM saeima_bills WHERE document_nr=?", (nr,)).fetchone()
        if b is None:
            missing.append(nr)
            continue
        if shared:
            votes = db.execute(
                "SELECT id, motif, result, vote_date FROM saeima_votes "
                "WHERE bill_id IS NOT NULL AND bill_id != ? AND motif LIKE ? "
                "ORDER BY vote_date, id", (b["id"], f"%({nr})%")).fetchall()
        else:
            votes = db.execute(
                "SELECT id, motif, result, vote_date FROM saeima_votes "
                "WHERE bill_id IS NULL AND document_nr=? ORDER BY vote_date, id",
                (nr,)).fetchall()
        planned_here = 0
        for v in votes:
            stage = _reading_from_motif(v["motif"] or "")
            try:
                _canonicalize_stage_name(stage)
            except ValueError:
                excluded.append((nr, v["id"], stage, "nav posmu vārdnīcā"))
                continue
            if db.execute("SELECT 1 FROM saeima_bill_stages WHERE vote_id=? AND bill_id=?",
                          (v["id"], b["id"])).fetchone() or (not shared and db.execute(
                    "SELECT 1 FROM saeima_bill_stages WHERE vote_id=?", (v["id"],)).fetchone()):
                excluded.append((nr, v["id"], stage, "posms ar šo vote_id jau ir"))
                continue
            plan.append((b["id"], nr, v["id"], stage, v["result"], v["vote_date"]))
            planned_here += 1
        if planned_here:
            snapshot.append((b["id"], nr, b["current_stage"], b["current_status"],
                             b["last_updated_at"]))
    return plan, snapshot, excluded, missing


def plan_hash(plan, snapshot) -> str:
    return hashlib.sha256(repr((plan, snapshot)).encode("utf-8")).hexdigest()[:16]


def apply_plan(db_path: str, plan, shared: bool = False) -> None:
    for bid, _nr, vid, stage, result, vdate in plan:
        append_bill_stage(db_path, bid, stage, result, vdate, vote_id=vid,
                          keep_vote_bill_id=shared, touch_updated_at=False)


def predict(src_db: sqlite3.Connection, plan, snapshot, shared: bool = False) -> dict[int, tuple]:
    """Piemēro plānu pagaidu apakškopas DB → {bill_id: (stage, status)}."""
    bill_ids = sorted({s[0] for s in snapshot})
    if not bill_ids:
        return {}
    marks = ",".join("?" * len(bill_ids))
    nr_marks = ",".join("?" * len(snapshot))
    nrs = [s[1] for s in snapshot]
    vids = [p[2] for p in plan]
    vid_marks = ",".join("?" * len(vids))
    # ignore_cleanup_errors: Windows tur failu, kamēr kāds savienojums nav GC.
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
        tmp = str(Path(td) / "predict.db")
        init_db(tmp)
        init_saeima_tables(tmp)
        init_saeima_bills(tmp)
        t = sqlite3.connect(tmp)  # FK izslēgts: sesijas/darba kārtība netiek kopētas
        for table, where, args in (
            ("saeima_bills", f"id IN ({marks})", bill_ids),
            ("saeima_bill_stages", f"bill_id IN ({marks})", bill_ids),
            ("saeima_votes",
             f"document_nr IN ({nr_marks}) OR id IN ({vid_marks}) OR id IN "
             f"(SELECT vote_id FROM saeima_bill_stages WHERE bill_id IN ({marks}))",
             nrs + vids + bill_ids),
        ):
            cols = [c[1] for c in t.execute(f"PRAGMA table_info({table})")]
            src_cols = {c[1] for c in src_db.execute(f"PRAGMA table_info({table})")}
            cols = [c for c in cols if c in src_cols]
            rows = src_db.execute(
                f"SELECT {','.join(cols)} FROM {table} WHERE {where}", args).fetchall()
            t.executemany(
                f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                [tuple(r) for r in rows])
        t.execute("UPDATE saeima_bill_stages SET session_id=NULL")
        t.execute("UPDATE saeima_votes SET agenda_item_id=NULL")
        t.commit()
        t.close()
        apply_plan(tmp, plan, shared)
        t = sqlite3.connect(tmp)
        out = {r[0]: (r[1], r[2]) for r in t.execute(
            f"SELECT id, current_stage, current_status FROM saeima_bills "
            f"WHERE id IN ({marks})", bill_ids)}
        t.close()
    return out


def _q(v) -> str:
    return "NULL" if v is None else "'" + str(v).replace("'", "''") + "'"


def rollback_sql(plan, snapshot, db_path: str, today: str) -> str:
    out = [
        "-- Forward: scripts/link_unbound_votes_to_bills.py --apply —",
        "-- saeima_votes ar bill_id IS NULL piesaistīti likumprojektam ar to pašu",
        "-- document_nr caur src.saeima.append_bill_stage() (jauna saeima_bill_stages",
        "-- rinda katram balsojumam; saeima_bills.current_stage/current_status",
        "-- pārrēķināti; last_updated_at nemainās — atgriešana to tik un tā liek).",
        "-- Atgriešana: posmi dzēsti pēc vote_id (to id pirms apply nav zināmi),",
        "-- bill_id → NULL, likumprojekta lauki → dry run brīža vērtības.",
        "-- sqlite_sequence (saeima_bill_stages) netiek atgriezts — nekaitīgi.",
        "-- --shared: balsojuma bill_id netika mainīts; `bill_id = NULL` rinda neko neskar.",
        f"-- Ģenerēts dry run {today} no DB: {db_path}",
        "-- Apply date: nav piemērots (ieraksti datumu, kad piemēro).",
        f"-- plan-hash: {plan_hash(plan, snapshot)} votes: {len(plan)} bills: {len(snapshot)}",
        "BEGIN;",
    ]
    by_bill: dict[int, list[int]] = {}
    for bid, _nr, vid, *_ in plan:
        by_bill.setdefault(bid, []).append(vid)
    for bid, nr, old_stage, old_status, old_ts in snapshot:
        ids = ",".join(str(v) for v in by_bill[bid])
        out.append(f"-- {nr}")
        out.append(f"DELETE FROM saeima_bill_stages WHERE bill_id = {bid} AND vote_id IN ({ids});")
        out.append(f"UPDATE saeima_votes SET bill_id = NULL WHERE bill_id = {bid} AND id IN ({ids});")
        out.append(
            f"UPDATE saeima_bills SET current_stage = {_q(old_stage)}, "
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
    ap.add_argument("--db", default=PRODUCTION_DB_PATH)
    ap.add_argument("--document-nr", action="append",
                    help="likumprojekta numurs, piem. 1019/Lp14 (atkārtojams)")
    ap.add_argument("--nr-file", help="fails ar vienu document_nr rindā")
    ap.add_argument("--rollback", required=True,
                    help="JAUNS fails katram skrējienam — piemērotie ir iekomitēti")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--shared", action="store_true",
                    help="balsojums jau piesaistīts citam likumprojektam; bill_id nemainās")
    args = ap.parse_args(argv)

    nrs = _read_nrs(args)
    if not nrs:
        print("ATTEIKTS: nav saraksta (--document-nr / --nr-file) — pa visiem "
              "likumprojektiem bez skaidra saraksta skripts neiet.")
        return 2

    db = sqlite3.connect(args.db)
    db.row_factory = sqlite3.Row
    plan, snapshot, excluded, missing = build_plan(db, nrs, args.shared)
    h = plan_hash(plan, snapshot)

    print(f"saraksts: {len(set(nrs))} nr; bez likumprojekta rindas: {len(missing)}")
    for nr in missing:
        print(f"  NAV saeima_bills: {nr}")
    print(f"plānoti balsojumi: {len(plan)} ({len(snapshot)} likumprojekti); "
          f"izslēgti: {len(excluded)}; 'nezināms': "
          f"{sum(1 for p in plan if p[3] == 'nezināms')}")
    for nr, vid, stage, why in excluded:
        print(f"  IZSLĒGTS {nr} vote {vid} ({stage!r}): {why}")

    if not args.apply:
        pred = predict(db, plan, snapshot, args.shared)
        by_bill: dict[int, list] = {}
        for p in plan:
            by_bill.setdefault(p[0], []).append(p)
        for bid, nr, old_stage, old_status, _ts in snapshot:
            stages = Counter(p[3] for p in by_bill[bid])
            new_stage, new_status = pred[bid]
            print(f"  {nr}: {len(by_bill[bid])} balsojumi "
                  f"[{', '.join(f'{s}×{n}' for s, n in sorted(stages.items()))}] "
                  f"{old_stage}/{old_status} → {new_stage}/{new_status}")
        for (os_, ns), n in sorted(Counter(
                (s[3], pred[s[0]][1]) for s in snapshot).items()):
            print(f"  status {os_} → {ns}: {n}")
    print(f"plan-hash: {h}")

    rb = Path(args.rollback)
    if not args.apply:
        db.close()
        rb.write_text(rollback_sql(plan, snapshot, args.db, date.today().isoformat()),
                      encoding="utf-8")
        print(f"DRY RUN — nekas nav mainīts. Atgriešanas SQL: {rb}")
        return 0

    db.close()  # append_bill_stage atver savu savienojumu katram balsojumam
    if not rb.exists():
        print(f"ATTEIKTS: nav atgriešanas faila {rb} — vispirms dry run + commit.")
        return 1
    header = next((ln for ln in rb.read_text(encoding="utf-8").splitlines()
                   if ln.startswith("-- plan-hash:")), "")
    if f"plan-hash: {h} votes: {len(plan)} bills: {len(snapshot)}" not in header:
        print(f"ATTEIKTS: plāns mainījies kopš dry run ({header!r}) — ģenerē atgriešanas failu no jauna.")
        return 1

    before_bind = {p[2]: None for p in plan}
    if args.shared:
        db = sqlite3.connect(args.db)
        before_bind = {p[2]: db.execute("SELECT bill_id FROM saeima_votes WHERE id=?",
                                        (p[2],)).fetchone()[0] for p in plan}
        db.close()
    apply_plan(args.db, plan, args.shared)

    db = sqlite3.connect(args.db)
    vids = [p[2] for p in plan]
    marks = ",".join("?" * len(vids)) or "NULL"
    stages = sum(db.execute("SELECT COUNT(*) FROM saeima_bill_stages WHERE vote_id=? AND bill_id=?",
                            (p[2], p[0])).fetchone()[0] for p in plan)
    if args.shared:  # balsojums paliek pie sava likumprojekta
        bound = sum(db.execute("SELECT bill_id FROM saeima_votes WHERE id=?", (v,)).fetchone()[0]
                    == before_bind[v] for v in vids)
    else:
        bound = db.execute(
            f"SELECT COUNT(*) FROM saeima_votes v JOIN saeima_bill_stages s ON s.vote_id = v.id "
            f"AND s.bill_id = v.bill_id WHERE v.id IN ({marks})", vids).fetchone()[0]
    db.close()
    print(f"PĀRBAUDE: posmi {stages}/{len(plan)}; piesaistīti balsojumi {bound}/{len(plan)}")
    if stages != len(plan) or bound != len(plan):
        print(f"KĻŪDA: neatbilst plānam — atgriešana: sqlite3 {args.db} < {rb}")
        return 1
    print(f"PIEMĒROTS: {len(plan)} balsojumi, {len(snapshot)} likumprojekti. "
          f"Atgriešana: sqlite3 {args.db} < {rb}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
