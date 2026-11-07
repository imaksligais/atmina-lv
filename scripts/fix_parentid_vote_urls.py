"""`Voting?ReadForm&parentID=` balsojumu saites → pastāvīgās `/0/<UNID>?OpenDocument`.

Titania `parentID=` lapa vēlāk ir tukša. Skripts sameklē katras tādas `saeima_votes`
rindas pastāvīgo saiti sēdes darba kārtībā (`DK?ReadForm&nr={uuid}`) un salīdzina pēc
(datums, laiks), kopsummām, deputātu skaita un motīva.

Dzīvo DB skripts NEMAINA. Bez karodziņiem tikai lasa un drukā saucējus. Ar `--write`
tīrajām rindām uzraksta pārī `data/fix_parentid_vote_urls_<datums>.sql` un
`data/rollback_parentid_vote_urls_<datums>.sql` un papildina
`src/saeima/parentid_url_map.json`, pēc kura renderis labo jau publicētos pārskatus
(T15: to teksts nemainās). SQL pielieto pēc abu failu iekomitēšanas (eskalācija 8).

Izejas kods: 0 — nekas nav palicis; 1 — palikušas rindas ar problēmām, neatrastas vai
kļūdas (tīrās tik un tā tiek ierakstītas); 2 — šodienas faili jau eksistē, nekas nav
rakstīts.

Lietošana:
    .venv/Scripts/python.exe scripts/fix_parentid_vote_urls.py
    .venv/Scripts/python.exe scripts/fix_parentid_vote_urls.py --write --out .scratch/parentid.json
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import time
from collections import Counter
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.audit_saeima_agenda_parity import _iso, _session_dates  # noqa: E402
from scripts.p3_backfill_year_urllib import (  # noqa: E402
    _extract_vote_urls_from_agenda,
    _fetch,
    _parse_vote_page,
)
from src.saeima.convocation import base_url  # noqa: E402
from src.saeima.manifest import MANIFEST_PATH, load_manifest  # noqa: E402

DEFAULT_DB = REPO_ROOT / "data" / "atmina.db"
DEFAULT_MAP = REPO_ROOT / "src" / "saeima" / "parentid_url_map.json"
DEFAULT_OUT_DIR = REPO_ROOT / "data"

MISSING_REASONS = {
    "nav_manifesta": "dienai manifestā nav sēdes (pārģenerē manifestu)",
    "dziva_sede": "sēdei vēl nav `nr=` UUID (pagaidi vai pārģenerē manifestu)",
    "lasisanas_kluda": "darba kārtību vai lapu neizdevās nolasīt (atkārto)",
    "vel_parentid": "darba kārtība vēl rāda tikai `parentID=` (pagaidi)",
    "nav_darba_kartiba": "darba kārtībā nav šī (datums, laiks) (īsts robs)",
}


def _fetch_with_retry(url: str, delay: float) -> str:
    for attempt in range(3):
        try:
            return _fetch(url)
        except Exception:  # noqa: BLE001
            if attempt == 2:
                raise
            if delay:
                time.sleep(2 * (attempt + 1))
    raise AssertionError("nesasniedzams")


def _norm(text: str | None) -> str:
    return re.sub(r"\W+", " ", text or "").strip().lower()


def _read_rows(db: sqlite3.Connection) -> list[sqlite3.Row]:
    return db.execute(
        """SELECT v.id, v.url, v.vote_date, v.vote_time, v.motif,
                  v.total_par, v.total_pret, v.total_atturas,
                  (SELECT COUNT(*) FROM saeima_individual_votes iv WHERE iv.vote_id = v.id) AS deputies,
                  (SELECT COUNT(*) FROM claims c WHERE c.source_url = v.url
                     AND c.claim_type = 'saeima_vote') AS vote_claims,
                  (SELECT COUNT(*) FROM claims c WHERE c.source_url = v.url
                     AND c.claim_type IS NOT 'saeima_vote') AS other_claims
           FROM saeima_votes v WHERE v.url LIKE '%parentID=%' ORDER BY v.id"""
    ).fetchall()


def _precheck(db: sqlite3.Connection, rows: list[sqlite3.Row]) -> tuple[dict, list[dict]]:
    """(meklējamie pēc (datums, laiks), rindas, kurām saiti nedrīkst meklēt)."""
    by_key: dict[tuple, list[sqlite3.Row]] = {}
    for row in rows:
        by_key.setdefault((row["vote_date"], row["vote_time"]), []).append(row)

    permanent = {(r[0], r[1]): r[2] for r in db.execute(
        "SELECT vote_date, vote_time, id FROM saeima_votes WHERE url IS NULL OR url NOT LIKE '%parentID=%'")}

    targets, refused = {}, []
    for key, group in by_key.items():
        problem = None
        if not key[0] or not key[1]:
            problem = "rindai nav datuma vai laika"
        elif len(group) > 1:
            problem = f"tas pats (datums, laiks) vairākām `parentID=` rindām: {[r['id'] for r in group]}"
        elif key in permanent:
            problem = f"dublikāts: tas pats (datums, laiks) jau ir rindai {permanent[key]}"
        if problem:
            refused.extend({"id": r["id"], "old": r["url"], "new": None, "date": key[0], "time": key[1],
                            "problems": [problem]} for r in group)
        else:
            targets[key] = group[0]
    return targets, refused


def _compare(page: dict, row: sqlite3.Row) -> list[str]:
    problems = []
    page_totals = (page["par"], page["pret"], page["atturas"])
    db_totals = (row["total_par"], row["total_pret"], row["total_atturas"])
    if page_totals != db_totals:
        problems.append(f"kopsummas: lapā {page_totals}, DB {db_totals}")
    if len(page["deputies"]) != row["deputies"]:
        problems.append(f"deputāti: lapā {len(page['deputies'])}, DB {row['deputies']}")
    if _norm(page["motif"])[:60] != _norm(row["motif"])[:60]:
        problems.append(f"motīvs: lapā {page['motif'][:80]!r}, DB {row['motif'][:80]!r}")
    return problems


def find_permanent_urls(db: sqlite3.Connection, sessions: list[dict], delay: float) -> dict:
    """Staigā darba kārtības un sagrupē katru `parentID=` rindu tieši vienā grupā."""
    rows = _read_rows(db)
    targets, refused = _precheck(db, rows)
    existing = {r[0] for r in db.execute("SELECT url FROM saeima_votes WHERE url IS NOT NULL")}
    found: dict[int, dict] = {}
    errors: list[dict] = []
    stats: Counter = Counter()
    date_state: dict[str, set] = {}
    seen_agendas: set[str] = set()
    seen_pages: set[str] = set()

    for day in sorted({key[0] for key in targets}):
        on_day = [s for s in sessions if day in _session_dates(s)]
        state = date_state.setdefault(day, set())
        if not on_day:
            state.add("nav_manifesta")
        if any(not s.get("uuid") for s in on_day):
            state.add("dziva_sede")
        for session in on_day:
            if not session.get("uuid") or session["uuid"] in seen_agendas:
                continue
            seen_agendas.add(session["uuid"])
            base = base_url(session.get("convocation", 14))
            try:
                agenda = _fetch_with_retry(f"{base}/DK?ReadForm&nr={session['uuid']}", delay)
            except Exception as e:  # noqa: BLE001
                errors.append({"date": day, "uuid": session["uuid"], "err": f"darba kārtība: {e}"})
                state.add("lasisanas_kluda")
                continue
            for url in _extract_vote_urls_from_agenda(agenda, base=base):
                stats["saites_darba_kartiba"] += 1
                if "parentID=" in url:
                    stats["darba_kartiba_parentid"] += 1
                    state.add("vel_parentid")
                    continue
                if url in existing:
                    stats["jau_db"] += 1
                    continue
                if url in seen_pages:
                    continue
                seen_pages.add(url)
                try:
                    page = _parse_vote_page(_fetch_with_retry(url, delay))
                except Exception as e:  # noqa: BLE001
                    errors.append({"date": day, "url": url, "err": str(e)})
                    state.add("lasisanas_kluda")
                    continue
                if delay:
                    time.sleep(delay)
                key = _iso(page)
                if not key[0] or not key[1]:
                    errors.append({"date": day, "url": url, "err": "lapā nav datuma vai laika"})
                    state.add("lasisanas_kluda")
                    continue
                row = targets.get(key)
                if row is None:
                    stats["lapa_citam_balsojumam"] += 1
                    continue
                if row["id"] in found:
                    found[row["id"]]["problems"].append(f"divas pastāvīgās saites: arī {url}")
                    continue
                found[row["id"]] = {
                    "id": row["id"], "old": row["url"], "new": url, "date": key[0], "time": key[1],
                    "vote_claims": row["vote_claims"],
                    "problems": _compare(page, row),
                }

    for row in targets.values():
        entry = found.get(row["id"])
        if entry is None:
            continue
        # `source_url` ir idempotences atslēgas daļa (Data Contract #3): ja pastāvīgā
        # saite jau ir kādam claim, UPDATE saplūdinātu divas rindas vienā atslēgā.
        taken = db.execute("SELECT COUNT(*) FROM claims WHERE source_url = ?", (entry["new"],)).fetchone()[0]
        if taken:
            entry["problems"].append(f"pastāvīgā saite jau ir {taken} claim rindām")
        # SQL labo tikai `saeima_vote` rindas; citas paliktu ar tukšo saiti.
        if row["other_claims"]:
            entry["problems"].append(f"{row['other_claims']} citu tipu claim rindas ar veco saiti")

    missing = []
    for key, row in targets.items():
        if row["id"] in found:
            continue
        state = date_state[key[0]]
        reason = next((r for r in MISSING_REASONS if r in state), "nav_darba_kartiba")
        missing.append({"id": row["id"], "date": key[0], "time": key[1], "old": row["url"], "reason": reason})

    return {
        "total": len(rows),
        "found": list(found.values()),
        "refused": refused,
        "missing": missing,
        "errors": errors,
        "stats": dict(stats),
    }


def _with_map_conflicts(result: dict, mapping: dict[str, str]) -> None:
    for entry in result["found"]:
        known = mapping.get(entry["old"])
        if known and known != entry["new"]:
            entry["problems"].append(f"kartējumā šai saitei jau ir cita: {known}")


def _sql_literal(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def _render_sql(clean: list[dict], today: str) -> tuple[str, str]:
    fix_name = f"fix_parentid_vote_urls_{today}.sql"
    rollback_name = f"rollback_parentid_vote_urls_{today}.sql"
    what = ("balsojumu saites `Voting?ReadForm&parentID=` (tukšas) ↔ pastāvīgās `/0/<UNID>?OpenDocument`; "
            f"ģenerēts {today} ar scripts/fix_parentid_vote_urls.py, pielieto pēc abu failu iekomitēšanas.")
    counts = (f"-- {len(clean)} saeima_votes.url + {sum(e['vote_claims'] for e in clean)} claims.source_url.\n"
              "-- Re-embed nav vajadzīgs (saeima_vote rindām vektoru nav).\n")

    def _updates(direction: str) -> list[str]:
        lines = []
        for e in clean:
            frm, to = (e["old"], e["new"]) if direction == "fix" else (e["new"], e["old"])
            lines.append(f"UPDATE saeima_votes SET url = {_sql_literal(to)} "
                         f"WHERE id = {e['id']} AND url = {_sql_literal(frm)};")
            lines.append(f"UPDATE claims SET source_url = {_sql_literal(to)} "
                         f"WHERE source_url = {_sql_literal(frm)} AND claim_type = 'saeima_vote';")
        return lines

    def _file(head: str, direction: str) -> str:
        return head + counts + "BEGIN;\n" + "\n".join(_updates(direction)) + "\nCOMMIT;\n"

    return (_file(f"-- Labojums; rollback data/{rollback_name}: {what}\n", "fix"),
            _file(f"-- Rollback; forward data/{fix_name}: {what}\n", "rollback"))


def _merge_map(path: Path, mapping: dict[str, str], clean: list[dict]) -> int:
    """Papildina kartējumu tajā pašā formā (kārtots, viens pāris rindā), lai diff rāda tikai jauno."""
    merged = {**mapping, **{e["old"]: e["new"] for e in clean}}
    pairs = ",\n".join(f"{json.dumps(k)}: {json.dumps(v)}" for k, v in sorted(merged.items()))
    newline = "\r\n" if b"\r\n" in path.read_bytes() else "\n"
    path.write_text("{\n" + pairs + "\n}\n", encoding="utf-8", newline=newline)
    return len(merged) - len(mapping)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--manifest", default=str(MANIFEST_PATH))
    ap.add_argument("--map", default=str(DEFAULT_MAP), help="parentid_url_map.json ceļš")
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="kur rakstīt fix_/rollback_ SQL")
    ap.add_argument("--out", default=None, help="pilns iznākums JSON failā (neobligāts)")
    ap.add_argument("--delay", type=float, default=0.15)
    ap.add_argument("--write", action="store_true", help="uzrakstīt SQL pāri un papildināt kartējumu")
    args = ap.parse_args()

    today = date.today().isoformat()
    out_dir = Path(args.out_dir)
    fix_path = out_dir / f"fix_parentid_vote_urls_{today}.sql"
    rollback_path = out_dir / f"rollback_parentid_vote_urls_{today}.sql"
    if args.write and (fix_path.exists() or rollback_path.exists()):
        print(f"STOP: {fix_path.name} vai {rollback_path.name} jau eksistē; nekas nav rakstīts. "
              "Pārvieto vai iekomitē un pielieto iepriekšējo pāri, tad atkārto rīt vai ar citu --out-dir.",
              file=sys.stderr)
        return 2

    sessions, generated_at = load_manifest(args.manifest)
    map_path = Path(args.map)
    mapping = json.loads(map_path.read_text(encoding="utf-8"))

    db = sqlite3.connect(f"{Path(args.db).resolve().as_uri()}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        result = find_permanent_urls(db, sessions, args.delay)
    finally:
        db.close()
    _with_map_conflicts(result, mapping)

    clean = [e for e in result["found"] if not e["problems"]]
    bad = [e for e in result["found"] if e["problems"]] + result["refused"]
    missing, errors = result["missing"], result["errors"]
    if result["total"] != len(clean) + len(bad) + len(missing):
        raise AssertionError("saucējs nesakrīt: kāda rinda pazudusi no atskaites")

    print(f"Manifests ģenerēts: {generated_at}")
    print(f"Saucēji: kopā {result['total']}; kartēti {len(result['found'])}; tīri {len(clean)}; "
          f"ar problēmām {len(bad)}; nav atrasti {len(missing)}; kļūdas {len(errors)}")
    print(f"Darba kārtībās: {result['stats']}")
    for entry in bad:
        print(f"  PROBLĒMA id={entry['id']} {entry['date']} {entry['time']}: {'; '.join(entry['problems'])}")
    for reason, n in Counter(m["reason"] for m in missing).items():
        print(f"  NAV ATRASTI {n}: {MISSING_REASONS[reason]}")
    for m in missing:
        print(f"    id={m['id']} {m['date']} {m['time']} [{m['reason']}]")
    for err in errors:
        print(f"  KĻŪDA {err}")

    if args.out:
        Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")

    if args.write and clean:
        fix_sql, rollback_sql = _render_sql(clean, today)
        fix_path.write_text(fix_sql, encoding="utf-8", newline="\n")
        rollback_path.write_text(rollback_sql, encoding="utf-8", newline="\n")
        added = _merge_map(map_path, mapping, clean)
        print(f"Uzrakstīts: {fix_path}, {rollback_path}; kartējumā jaunas {added} rindas "
              f"(tagad {len(mapping) + added}). DB nav mainīta.")
    elif args.write:
        print("Tīru rindu nav: faili nav rakstīti, kartējums nav mainīts.")

    return 1 if bad or missing or errors else 0


if __name__ == "__main__":
    sys.exit(main())
