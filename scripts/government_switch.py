#!/usr/bin/env python
"""Valdības maiņas diena: `parties.coalition_status` un ministru `role` vienā pārbaudītā solī.

Kāpēc: kad Saeima apstiprina jaunu valdību, jāmaina trīs lietas — `coalition_periods`
rinda (to dara `scripts/seed_coalition_periods.py`), partiju `coalition_status` un
ministru `tracked_politicians.role`. Šis skripts dara pēdējās divas pēc operatora
aizpildīta plāna, vispirms tikai rāda, tad uzraksta SQL pāri (eskalācijas
noteikums 8: rollback commit PIRMS piemērošanas) un tikai tad piemēro.

Režīmi:
    --template [--out FILE]            tikai lasa; izdrukā/ieraksta plāna sagatavi (YAML)
    --plan FILE                        dry-run (noklusējums): pārbauda plānu, rāda izmaiņas
    --plan FILE --write-sql [--out-dir DIR] [--date D]
                                       ieraksta fix_valdiba_<D>.sql + rollback_valdiba_<D>.sql
    --plan FILE --apply [--out-dir DIR] [--date D]
                                       piemēro fix_valdiba_<D>.sql vienā transakcijā

Ko skripts NEdara: nemaina `tracked_politicians.party`, `name_forms` vai ko citu;
nekārto Personu lapas grupēšanu un komisiju/frakciju lomu pārskatu (sk. runbook).
Runbook: wiki/operations/seeding.md § Valdības maiņas diena.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import yaml  # noqa: E402

from scripts.audit_integrity import Ctx, check_24  # noqa: E402
from scripts.seed_coalition_periods import (  # noqa: E402
    derive_periods,
    describe_fallback,
    stored_periods,
)
from src.db import PRODUCTION_DB_PATH, now_lv  # noqa: E402
from src.profile_kind import (  # noqa: E402
    CURRENT_TERM_START,
    current_term_vote_counts,
    derive_profile_kind,
)

STATUSES = ("coalition", "opposition", "not_in_saeima")
ROLE_MARKERS = ("ministr", "parlamentār")   # «Ministru prezident» ietilpst «ministr»
MANIFEST = "-- manifest: "


class Stop(Exception):
    """Plāns vai stāvoklis neder — nekas netiek rakstīts."""


def _connect(path: str, rw: bool = False) -> sqlite3.Connection:
    uri = f"file:{Path(path).as_posix()}?mode={'rw' if rw else 'ro'}"
    db = sqlite3.connect(uri, uri=True)
    db.row_factory = sqlite3.Row
    return db


def _git_tracked(path: Path) -> bool:
    """Vai fails ir git indeksā (rollback jābūt commitotam PIRMS --apply)."""
    r = subprocess.run(["git", "ls-files", "--error-unmatch", str(path)],
                       cwd=REPO, capture_output=True)
    return r.returncode == 0


# --- plāna sagatave ----------------------------------------------------------

def build_template(db: sqlite3.Connection) -> dict:
    periods = derive_periods(db)
    p = periods[-1] if periods else None
    if p is None:
        print("Nav neviena pieņemta uzticības balsojuma — koalīcija nav atvasināma.")
    else:
        print(f"jaunākais pieņemtais uzticības balsojums: id {p['source_vote_id']} "
              f"{p['valid_from_date']} {p['valid_from_time']} → {', '.join(p['factions']) or '(tukša)'}")
        if p.get("fallback"):
            print(describe_fallback(p))
    derivable = bool(p and p["valid_from_date"] >= CURRENT_TERM_START and p["factions"])
    note = ""
    if p and not derivable:
        note = (f"jaunās valdības balsojums vēl nav ielādēts: jaunākais ir {p['valid_from_date']}, "
                f"pirms šīs Saeimas sākuma ({CURRENT_TERM_START})") if p["valid_from_date"] < CURRENT_TERM_START \
            else "balsojumam atvasināta tukša koalīcija"
        print(f"KOALĪCIJA NAV ATVASINĀMA: {note}. Sagatave izveidota bez koalīcijas; "
              "vispirms /saeima-ingest un seed_coalition_periods.py.")
    elif p and p["source_vote_id"] not in stored_periods(db):
        print("coalition_periods rindas šim balsojumam vēl nav — pirms dry-run palaid "
              "scripts/seed_coalition_periods.py --apply.")
    coalition = set(p["factions"]) if derivable else set()
    voted = set(p["counts"]) if derivable else set()

    parties = []
    for r in db.execute("SELECT short_name, coalition_status FROM parties "
                        "WHERE short_name IS NOT NULL ORDER BY short_name"):
        sn, cur = r["short_name"], r["coalition_status"]
        if cur not in ("coalition", "opposition") and sn not in coalition and sn not in voted:
            continue
        new = (cur if not derivable else "coalition" if sn in coalition
               else "opposition" if sn in voted else "not_in_saeima")
        parties.append({"short_name": sn, "status": cur, "new_status": new})

    roles = []
    for r in db.execute("SELECT id, name, role FROM tracked_politicians "
                        "WHERE COALESCE(relationship_type, '') != 'inactive' ORDER BY id"):
        if any(m in (r["role"] or "").lower() for m in ROLE_MARKERS):
            roles.append({"id": r["id"], "name": r["name"], "role": r["role"], "new_role": r["role"]})

    print(f"partijas sagatavē: {len(parties)}; lomas sagatavē: {len(roles)} "
          "(ne-inactive politiķi, kuru role min ministru vai parlamentāro sekretāru)")
    return {
        "vote": None if p is None else {"id": p["source_vote_id"], "date": p["valid_from_date"],
                                        "time": p["valid_from_time"]},
        "coalition": sorted(coalition) if derivable else None,
        "coalition_note": note or "atvasināts no balsojuma (tā pati funkcija kā seed skriptā)",
        "parties": parties,
        "roles": roles,
    }


# --- plāna pārbaude un izmaiņas ---------------------------------------------

def _simulate_check_24(db: sqlite3.Connection, party_changes: list[dict]):
    """check_24 pret atmiņas kopiju (coalition_periods + parties) ar piemērotām izmaiņām."""
    mem = sqlite3.connect(":memory:")
    mem.row_factory = sqlite3.Row
    mem.execute("CREATE TABLE coalition_periods (id INTEGER, valid_from_date TEXT, "
                "valid_from_time TEXT, factions TEXT)")
    mem.execute("CREATE TABLE parties (id INTEGER, short_name TEXT, coalition_status TEXT)")
    mem.executemany("INSERT INTO coalition_periods VALUES (?, ?, ?, ?)", [tuple(r) for r in db.execute(
        "SELECT id, valid_from_date, valid_from_time, factions FROM coalition_periods")])
    mem.executemany("INSERT INTO parties VALUES (?, ?, ?)", [tuple(r) for r in db.execute(
        "SELECT id, short_name, coalition_status FROM parties")])
    for c in party_changes:
        mem.execute("UPDATE parties SET coalition_status = ? WHERE id = ?", (c["new"], c["id"]))
    try:
        return check_24(Ctx(db=mem, db_path=":memory:"))
    finally:
        mem.close()


def build_diff(db: sqlite3.Connection, plan: dict) -> dict:
    """Pārbauda plānu pret DB → {'vote_id', 'parties', 'roles', 'n_parties', 'n_roles', 'check24'}.
    Jebkura neatbilstība → Stop."""
    errors: list[str] = []
    vote = plan.get("vote") or {}
    if plan.get("coalition") is None:
        raise Stop("plānā koalīcija nav atvasināta (coalition: null) — vispirms ielādē jaunās "
                   "valdības balsojumu un izveido sagatavi no jauna.")
    derived = {p["source_vote_id"]: p for p in derive_periods(db)}
    p = derived.get(vote.get("id"))
    if p is None:
        raise Stop(f"balsojums id {vote.get('id')} nav pieņemts uzticības balsojums šajā DB.")
    plan_coal, der_coal = sorted(plan["coalition"]), sorted(p["factions"])
    if plan_coal != der_coal:
        raise Stop(f"plāna koalīcija {plan_coal} ≠ no balsojuma atvasinātā {der_coal}.")
    if not der_coal:
        raise Stop("no balsojuma atvasināta tukša koalīcija.")
    stored = stored_periods(db).get(p["source_vote_id"])
    if stored is None:
        raise Stop(f"coalition_periods rindas balsojumam id {p['source_vote_id']} nav — vispirms "
                   "palaid scripts/seed_coalition_periods.py (dry-run, tad --apply pēc rollback commit).")
    if sorted(f for f in stored[2].split(",") if f) != der_coal:
        raise Stop(f"coalition_periods rinda ({stored[2]}) ≠ atvasinātā koalīcija {der_coal}.")

    party_rows = {r["short_name"]: r for r in db.execute(
        "SELECT id, short_name, coalition_status FROM parties")}
    party_changes, seen = [], set()
    for e in plan.get("parties") or []:
        sn = e.get("short_name")
        if sn in seen:
            errors.append(f"partija {sn} plānā divreiz")
            continue
        seen.add(sn)
        row = party_rows.get(sn)
        if row is None:
            errors.append(f"partija {sn!r}: tāda short_name nav tabulā parties")
            continue
        if e.get("new_status") not in STATUSES:
            errors.append(f"partija {sn}: new_status {e.get('new_status')!r} nav no {STATUSES}")
            continue
        if e.get("status") != row["coalition_status"]:
            errors.append(f"partija {sn}: plānā status {e.get('status')!r}, DB tagad "
                          f"{row['coalition_status']!r} — sagatave novecojusi")
            continue
        if e["new_status"] != row["coalition_status"]:
            party_changes.append({"id": row["id"], "short_name": sn,
                                  "old": row["coalition_status"], "new": e["new_status"]})

    role_changes, seen = [], set()
    for e in plan.get("roles") or []:
        pid = e.get("id")
        if pid in seen:
            errors.append(f"politiķis id {pid} plānā divreiz")
            continue
        seen.add(pid)
        row = db.execute("SELECT id, name, role, relationship_type FROM tracked_politicians "
                         "WHERE id = ?", (pid,)).fetchone()
        if row is None:
            errors.append(f"politiķis id {pid}: nav tabulā tracked_politicians")
            continue
        if row["name"] != e.get("name"):
            errors.append(f"politiķis id {pid}: plānā vārds {e.get('name')!r}, DB {row['name']!r}")
            continue
        new_role = (e.get("new_role") or "").strip()
        if not new_role:
            errors.append(f"politiķis id {pid} ({row['name']}): new_role tukšs")
            continue
        if e.get("role") != row["role"]:
            errors.append(f"politiķis id {pid} ({row['name']}): plānā role {e.get('role')!r}, "
                          f"DB tagad {row['role']!r} — sagatave novecojusi")
            continue
        if new_role != row["role"]:
            role_changes.append({"id": pid, "name": row["name"], "old": row["role"], "new": new_role,
                                 "relationship_type": row["relationship_type"] or ""})
    if errors:
        raise Stop("plāns neder:\n  " + "\n  ".join(errors))
    return {"vote_id": p["source_vote_id"], "vote": p, "coalition": der_coal,
            "parties": party_changes, "roles": role_changes,
            "n_parties": len(plan.get("parties") or []), "n_roles": len(plan.get("roles") or []),
            "check24": _simulate_check_24(db, party_changes)}


def print_diff(db: sqlite3.Connection, d: dict) -> None:
    p = d["vote"]
    print(f"balsojums id {d['vote_id']} {p['valid_from_date']} {p['valid_from_time']}; "
          f"koalīcija: {', '.join(d['coalition'])}")
    print(f"partiju statuss — mainīsies {len(d['parties'])} no {d['n_parties']} plānā:")
    for c in d["parties"]:
        print(f"  {c['short_name']}: {c['old']} → {c['new']}")
    votes = current_term_vote_counts(db)
    print(f"lomas — mainīsies {len(d['roles'])} no {d['n_roles']} plānā:")
    for c in d["roles"]:
        n = votes.get(c["id"], 0)
        k_old = derive_profile_kind(c["relationship_type"], c["old"], n)
        k_new = derive_profile_kind(c["relationship_type"], c["new"], n)
        print(f"  id {c['id']} {c['name']}: {c['old']!r} → {c['new']!r}  "
              f"[profila veids {k_old} → {k_new}]")
    r = d["check24"]
    if r.flagged == 0:
        print(f"audit 24 pēc piemērošanas: iztur (periodi {r.checked}, atšķirības 0)")
    else:
        print(f"audit 24 pēc piemērošanas: NEIZTURĒTU — {r.rows}")


# --- SQL ---------------------------------------------------------------------

def _lit(v) -> str:
    return "NULL" if v is None else "'" + str(v).replace("'", "''") + "'"


def _guard(col: str, v) -> str:
    return f"{col} IS NULL" if v is None else f"{col} = {_lit(v)}"


def _statements(manifest: dict, reverse: bool = False) -> list[str]:
    out = []
    for c in manifest["parties"]:
        new, old = (c["old"], c["new"]) if reverse else (c["new"], c["old"])
        out.append(f"UPDATE parties SET coalition_status = {_lit(new)} "
                   f"WHERE id = {int(c['id'])} AND {_guard('coalition_status', old)};")
    for c in manifest["roles"]:
        new, old = (c["old"], c["new"]) if reverse else (c["new"], c["old"])
        out.append(f"UPDATE tracked_politicians SET role = {_lit(new)} "
                   f"WHERE id = {int(c['id'])} AND {_guard('role', old)};")
    return out


def _manifest(d: dict) -> dict:
    return {"vote_id": d["vote_id"],
            "parties": [{k: c[k] for k in ("id", "short_name", "old", "new")} for c in d["parties"]],
            "roles": [{k: c[k] for k in ("id", "name", "old", "new")} for c in d["roles"]]}


def _paths(out_dir: str, day: str) -> tuple[Path, Path]:
    base = Path(out_dir)
    if not base.is_absolute():
        base = REPO / base
    return base / f"fix_valdiba_{day}.sql", base / f"rollback_valdiba_{day}.sql"


def write_sql(d: dict, out_dir: str, day: str) -> tuple[Path, Path]:
    fix, rb = _paths(out_dir, day)
    existing = [str(f) for f in (fix, rb) if f.exists()]
    if existing:
        raise Stop(f"fails jau ir, nepārrakstu: {existing}")
    m = _manifest(d)
    if not m["parties"] and not m["roles"]:
        raise Stop("plānā nav nevienas izmaiņas — nav ko rakstīt.")
    p = d["vote"]
    pchanges = ", ".join("{} {}→{}".format(c["short_name"], c["old"], c["new"]) for c in m["parties"])
    change = (f"valdības maiņa — uzticības balsojums id {d['vote_id']} ({p['valid_from_date']} "
              f"{p['valid_from_time']}), koalīcija {','.join(d['coalition'])}; "
              f"parties.coalition_status {len(m['parties'])} rindas ({pchanges or '—'}); "
              f"tracked_politicians.role {len(m['roles'])} rindas (id "
              f"{', '.join(str(c['id']) for c in m['roles']) or '—'}). Apply date: {day}.")
    fwd = [f"-- Forward: {change}",
           f"-- Rollback: {rb.name}. Piemēro: scripts/government_switch.py --apply --date {day}.",
           MANIFEST + json.dumps(m, ensure_ascii=False),
           "BEGIN;", *_statements(m), "COMMIT;"]
    back = [f"-- Rollback of {fix.name}.",
            f"-- Forward: {change}",
            "BEGIN;", *_statements(m, reverse=True), "COMMIT;"]
    fix.parent.mkdir(parents=True, exist_ok=True)
    fix.write_text("\n".join(fwd) + "\n", encoding="utf-8")
    rb.write_text("\n".join(back) + "\n", encoding="utf-8")
    return fix, rb


def _split(sql: str) -> list[str]:
    """Izpildāmie priekšraksti (bez komentāriem un BEGIN/COMMIT)."""
    out, buf = [], ""
    for line in sql.splitlines(keepends=True):
        if not buf and (line.startswith("--") or not line.strip()):
            continue
        buf += line
        if sqlite3.complete_statement(buf):
            s = buf.strip()
            if s.upper() not in ("BEGIN;", "COMMIT;"):
                out.append(s)
            buf = ""
    return out


def apply(db: sqlite3.Connection, plan: dict, out_dir: str, day: str) -> int:
    fix, rb = _paths(out_dir, day)
    missing = [str(f) for f in (fix, rb) if not f.exists()]
    if missing:
        raise Stop(f"nav SQL failu: {missing} — vispirms --write-sql.")
    if not _git_tracked(rb):
        raise Stop(f"{rb} nav git indeksā — commit rollback PIRMS --apply (eskalācijas noteikums 8).")
    text = fix.read_text(encoding="utf-8")
    mline = next((ln for ln in text.splitlines() if ln.startswith(MANIFEST)), None)
    if mline is None:
        raise Stop(f"{fix.name}: nav manifesta rindas — fails nav šī skripta rakstīts.")
    m = json.loads(mline[len(MANIFEST):])

    stale = []
    for c in m["parties"]:
        cur = db.execute("SELECT coalition_status FROM parties WHERE id = ?", (c["id"],)).fetchone()
        if cur is None or cur[0] != c["old"]:
            stale.append(f"partija {c['short_name']}: SQL rakstot {c['old']!r}, tagad "
                         f"{None if cur is None else cur[0]!r}")
    for c in m["roles"]:
        cur = db.execute("SELECT role FROM tracked_politicians WHERE id = ?", (c["id"],)).fetchone()
        if cur is None or cur[0] != c["old"]:
            stale.append(f"id {c['id']} {c['name']}: SQL rakstot {c['old']!r}, tagad "
                         f"{None if cur is None else cur[0]!r}")
    if stale:
        raise Stop("plāns novecojis — DB mainījusies pēc --write-sql:\n  " + "\n  ".join(stale))

    d = build_diff(db, plan)
    if _manifest(d) != m:
        raise Stop("plāns mainīts pēc --write-sql (izmaiņas ≠ manifests) — izdzēs nepiemērotos "
                   "SQL failus un palaid --write-sql no jauna.")
    stmts = _split(text)
    if stmts != _statements(m):
        raise Stop(f"{fix.name} priekšraksti ≠ manifests — fails labots ar roku.")
    if d["check24"].flagged:
        raise Stop(f"audit 24 pēc piemērošanas neizturētu: {d['check24'].rows}")

    intended = len(m["parties"]) + len(m["roles"])
    db.isolation_level = None
    db.execute("BEGIN")
    try:
        changed = sum(db.execute(s).rowcount for s in stmts)
        wrong = [c["short_name"] for c in m["parties"] if db.execute(
            "SELECT coalition_status FROM parties WHERE id = ?", (c["id"],)).fetchone()[0] != c["new"]]
        wrong += [str(c["id"]) for c in m["roles"] if db.execute(
            "SELECT role FROM tracked_politicians WHERE id = ?", (c["id"],)).fetchone()[0] != c["new"]]
        if changed != intended or wrong:
            raise Stop(f"pēc izpildes mainītas {changed} rindas no {intended}; neatbilst: {wrong}")
        db.execute("COMMIT")
    except BaseException:
        db.execute("ROLLBACK")
        raise
    print(f"piemērots {fix.name}: partijas — mainītas {len(m['parties'])} no {d['n_parties']} plānā "
          f"pārbaudītajām; lomas — mainītas {len(m['roles'])} no {d['n_roles']} plānā uzskaitītajām; "
          f"rindas kopā {changed} no {intended} paredzētajām.")
    r = check_24(Ctx(db=db, db_path=":db:"))
    print(f"audit 24: periodi {r.checked}, atšķirības {r.flagged}")
    return 0


# --- CLI ---------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--db", default=PRODUCTION_DB_PATH)
    ap.add_argument("--template", action="store_true", help="izveidot plāna sagatavi (tikai lasa)")
    ap.add_argument("--out", help="sagataves fails (noklusējums: stdout)")
    ap.add_argument("--plan", help="aizpildītais plāns (YAML)")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--write-sql", action="store_true", help="ierakstīt fix + rollback SQL")
    mode.add_argument("--apply", action="store_true", help="piemērot fix SQL")
    ap.add_argument("--out-dir", default="data", help="SQL failu mape (noklusējums data/)")
    ap.add_argument("--date", default=now_lv()[:10], help="SQL failu datums (noklusējums šodiena LV)")
    args = ap.parse_args(argv)

    if args.template == bool(args.plan):
        ap.error("vajag tieši vienu: --template vai --plan FILE")
    try:
        if args.template:
            db = _connect(args.db)
            try:
                text = yaml.safe_dump(build_template(db), allow_unicode=True, sort_keys=False,
                                      width=200)
            finally:
                db.close()
            head = ("# Valdības maiņas plāns (scripts/government_switch.py). Labo tikai new_status un\n"
                    "# new_role; status/role ir pašreizējās vērtības un kalpo kā novecošanās pārbaude.\n")
            if args.out:
                Path(args.out).parent.mkdir(parents=True, exist_ok=True)
                Path(args.out).write_text(head + text, encoding="utf-8")
                print(f"sagatave ierakstīta: {args.out}")
            else:
                print(head + text)
            return 0

        plan = yaml.safe_load(Path(args.plan).read_text(encoding="utf-8")) or {}
        db = _connect(args.db, rw=args.apply)
        try:
            if args.apply:
                return apply(db, plan, args.out_dir, args.date)
            d = build_diff(db, plan)
            print_diff(db, d)
            if d["check24"].flagged:
                raise Stop("audit 24 pēc piemērošanas neizturētu — labo partiju statusus plānā.")
            if args.write_sql:
                fix, rb = write_sql(d, args.out_dir, args.date)
                print(f"ierakstīts: {fix}\nierakstīts: {rb}\nDB nav mainīta. Commit abus, tad --apply.")
            else:
                print("dry-run: DB nav mainīta. Tālāk --write-sql.")
            return 0
        finally:
            db.close()
    except Stop as e:
        print(f"STOP: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
