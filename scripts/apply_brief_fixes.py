#!/usr/bin/env python
"""Pārskata labojumu piemērošana: «vecais → jaunais» pāri visās vietās, kur teksts stāv.

Aizstāj katras rutīnas rokas `.scratch/qr_fix*.py` (14.11. bija četri, viens
nokrita importā). Vietas atrod skripts, ne saucējs: pārskats (`--note`), tā
perioda konteksta piezīmes un spriedžu apraksti (rutīnas dienas logs,
`src.briefs.routine_day_window`; nedēļas pārskatam — visa nedēļa).

Noklusējums: dry-run (tikai lasa DB). Kārtība (CLAUDE.md escalation 8):

    .venv/Scripts/python.exe scripts/apply_brief_fixes.py --note N --fixes F.json --tag r1                  # 1. dry-run
    .venv/Scripts/python.exe scripts/apply_brief_fixes.py --note N --fixes F.json --tag r1 --write-rollback # 2. rollback
    git commit data/rollback_qr_fixes_<slugs>_r1.sql                                                        # 3. commit
    .venv/Scripts/python.exe scripts/apply_brief_fixes.py --note N --fixes F.json --tag r1 --apply          # 4. apply

`--fixes` = JSON saraksts `[["vecais teksts", "jaunais teksts"], …]`.

Atsaka VISU partiju (exit 2), neko nerakstot, ja:
- kāds vecais teksts nav atrasts nevienā vietā;
- labojums ievieš jaunu `lint_lv_style` atradumu (mantotie netraucē) vai teksts
  krīt garumzīmju pārbaudē;
- spriedzes apraksts pēc labojuma vairs nav viena rinda;
- teksts stāv konteksta piezīmē, kas jau ir publicēta (piezīmes ir append-only,
  CLAUDE.md inv. #8; labot drīkst tikai piezīmi, kas rakstīta pēc pēdējā deploy)
  — tad pievieno jaunu piezīmi vai lieto `--skip-published-notes`;
- (`--apply`) rollback nav commitēts vai neatbilst pašreizējam DB stāvoklim.

Pārskatu glabā caur `store_context_note()` (tās pašas struktūras pārbaudes).
Tas pārraksta `created_at`; dienas pārskatam, kas NAV šodienas rutīnas dienas,
skripts veco `created_at` atliek atpakaļ, jo jaunāks zīmogs izmestu
atpakaļdatētas pozīcijas no vēlāku dienu pārskatiem (`_NOT_ALREADY_BRIEFED_SQL`).
Publicēšanu neaiztiek: ja pārskats ir apstiprināts, pēc labojuma vajag
`scripts/approve_publish.py` vēlreiz (T15) — skripts to tikai pasaka.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src.briefs import (  # noqa: E402
    brief_publish_key,
    brief_subject_date,
    current_routine_day,
    routine_day_window,
)
from src.db import get_db  # noqa: E402
from src.lv_style import lint_lv_style  # noqa: E402
from src.quality import validate_lv_diacritics  # noqa: E402
from src.tools import store_context_note  # noqa: E402

DATA_DIR = REPO / "data"
_STATE_LINE = re.compile(r"^-- state-sha256: ([0-9a-f]{64})$", re.M)
_WEEK_END = re.compile(r"līdz (\d{4}-\d{2}-\d{2})")


class Refuse(Exception):
    """Partija nav piemērojama; ziņa nosauc iemeslu."""


def is_git_tracked(path: Path) -> bool:
    if not path.resolve().is_relative_to(REPO):
        return False
    return subprocess.run(
        ["git", "ls-files", "--error-unmatch", path.resolve().relative_to(REPO).as_posix()],
        cwd=REPO, capture_output=True,
    ).returncode == 0


def load_pairs(path: str) -> list[tuple[str, str]]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    pairs = []
    for item in raw:
        old, new = item
        if not isinstance(old, str) or not isinstance(new, str) or not old:
            raise ValueError(f"pāris nav [str, str] ar netukšu veco tekstu: {item!r}")
        if old == new:
            raise ValueError(f"vecais un jaunais teksts sakrīt: {old[:60]!r}")
        pairs.append((old, new))
    return pairs


def _sql_text(value: str) -> str:
    """SQL izteiksme, kas dod *value* baits baitā neatkarīgi no faila rindu galiem.

    Katra teksta rinda ir savs literālis, savienots ar char(10). Git šajā
    datorā izrakstot `.sql` failu, LF nomaina ar CRLF; daudzrindu literālis tad
    rollbackā atjaunotu tekstu ar liekiem CR (2026-11-16)."""
    parts = ["'" + line.replace("'", "''") + "'" for line in value.replace("\r\n", "\n").split("\n")]
    return "\n  || char(10) || ".join(parts)


def _new_lint(old: str, new: str) -> list[dict]:
    key = lambda i: (i.get("rule"), i.get("match"))  # noqa: E731
    extra = Counter(map(key, lint_lv_style(new))) - Counter(map(key, lint_lv_style(old)))
    return [{"rule": r, "match": m, "count": n} for (r, m), n in extra.items()]


def _period(note) -> tuple[str, str, str]:
    """(subjekta diena, loga sākums LV, loga beigas LV) pārskatam *note*."""
    subject = brief_subject_date(note["topic"], note["content"], note["created_at"])
    if not subject:
        raise Refuse(f"pārskatam {note['id']} nevar noteikt subjekta datumu")
    last = subject
    if note["note_type"] == "weekly_brief":
        m = _WEEK_END.search(note["topic"] or "")
        if not m:
            raise Refuse(f"nedēļas pārskata topic bez beigu datuma: {note['topic']!r}")
        last = m.group(1)
    return subject, routine_day_window(subject)[0], routine_day_window(last)[1]


def collect(db, note_id: int) -> dict:
    """Pārskats + tā perioda piezīmes un spriedzes: viss, kur labojums var stāvēt."""
    note = db.execute(
        "SELECT id, topic, note_type, content, source, created_at FROM context_notes WHERE id = ?",
        (note_id,),
    ).fetchone()
    if note is None or note["note_type"] not in ("daily_brief", "weekly_brief"):
        raise Refuse(f"piezīme {note_id} nav dienas vai nedēļas pārskats")
    subject, start, end = _period(note)
    notes = db.execute(
        "SELECT id, content, created_at FROM context_notes "
        "WHERE note_type = 'context' AND created_at >= ? AND created_at < ? ORDER BY id",
        (start, end),
    ).fetchall()
    tensions = db.execute(
        "SELECT id, description FROM political_tensions "
        "WHERE datetime(created_at, 'localtime') >= ? AND datetime(created_at, 'localtime') < ? "
        "ORDER BY id",
        (start, end),
    ).fetchall()
    last_deploy = db.execute(
        "SELECT MAX(timestamp) FROM logs WHERE action = 'deploy' AND status = 'success'"
    ).fetchone()[0]
    approved = db.execute(
        "SELECT 1 FROM publish_approvals WHERE subject_key = ?",
        (brief_publish_key(note["note_type"], subject),),
    ).fetchone() is not None
    return {"note": dict(note), "subject": subject, "window": (start, end),
            "notes": [dict(r) for r in notes], "tensions": [dict(r) for r in tensions],
            "last_deploy": last_deploy, "approved": approved}


def plan(state: dict, pairs: list[tuple[str, str]], skip_published_notes: bool) -> dict:
    """Aprēķina jaunos tekstus un pārbauda visus atteikuma iemeslus. Neko neraksta."""
    surfaces = [("brief", state["note"]["id"], state["note"]["content"])]
    surfaces += [("note", n["id"], n["content"]) for n in state["notes"]]
    surfaces += [("tension", t["id"], t["description"]) for t in state["tensions"]]
    published = {n["id"] for n in state["notes"]
                 if state["last_deploy"] and n["created_at"] <= state["last_deploy"]}

    texts = {(kind, sid): text for kind, sid, text in surfaces}
    hits: list[dict] = []
    for old, new in pairs:
        per = {}
        for kind, sid, _ in surfaces:
            if kind == "note" and sid in published and skip_published_notes:
                continue
            n = texts[(kind, sid)].count(old)
            if n:
                per[(kind, sid)] = n
                texts[(kind, sid)] = texts[(kind, sid)].replace(old, new)
        hits.append({"old": old, "new": new, "per": per})

    problems = [f"vecais teksts nav atrasts nevienā vietā: {h['old'][:80]!r}"
                for h in hits if not h["per"]]
    changed = [(kind, sid, text, texts[(kind, sid)]) for kind, sid, text in surfaces
               if texts[(kind, sid)] != text]
    for kind, sid, old_text, new_text in changed:
        label = f"{kind} {sid}"
        if kind == "note" and sid in published:
            problems.append(f"{label}: piezīme jau publicēta (rakstīta pirms deploy "
                            f"{state['last_deploy']}) — append-only; pievieno jaunu piezīmi "
                            "vai lieto --skip-published-notes")
        for issue in _new_lint(old_text, new_text):
            problems.append(f"{label}: jauns lint atradums {issue}")
        ok, reason = validate_lv_diacritics(new_text)
        if not ok:
            problems.append(f"{label}: garumzīmju pārbaude — {reason}")
        if kind == "tension" and ("\n" in new_text or "\r" in new_text):
            problems.append(f"{label}: spriedzes apraksts vairs nav viena rinda")
        if not new_text.strip():
            problems.append(f"{label}: pēc labojuma teksts ir tukšs")
    return {"hits": hits, "changed": changed, "problems": problems,
            "examined": {"brief": 1, "note": len(state["notes"]), "tension": len(state["tensions"])},
            "skipped_published": sorted(published) if skip_published_notes else []}


def state_hash(state: dict, pairs: list[tuple[str, str]], changed: list) -> str:
    payload = {"pairs": pairs, "created_at": state["note"]["created_at"],
               "old": [[kind, sid, old] for kind, sid, old, _ in changed]}
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def rollback_sql(state: dict, changed: list, digest: str, tag: str, fixes_path: str) -> str:
    note = state["note"]
    lines = [
        f"-- Rollback: pārskata labojumi ({tag}), piezīme {note['id']} «{note['topic']}» "
        "(scripts/apply_brief_fixes.py).",
        f"-- Forward: scripts/apply_brief_fixes.py --note {note['id']} --fixes {fixes_path} "
        f"--tag {tag} --apply; apply date: {current_routine_day()}.",
        f"-- Atjauno {len(changed)} vietu veco tekstu un pārskata created_at.",
        f"-- state-sha256: {digest}",
        "BEGIN;",
    ]
    for kind, sid, old_text, _ in changed:
        if kind == "tension":
            lines.append(f"UPDATE political_tensions SET description =\n  {_sql_text(old_text)}\nWHERE id = {sid};")
        elif kind == "brief":
            lines.append(f"UPDATE context_notes SET content =\n  {_sql_text(old_text)},\n"
                         f"  created_at = {_sql_text(note['created_at'])}\nWHERE id = {sid};")
        else:
            lines.append(f"UPDATE context_notes SET content =\n  {_sql_text(old_text)}\nWHERE id = {sid};")
    lines.append("COMMIT;")
    return "\n".join(lines) + "\n"


def apply_changes(state: dict, changed: list) -> str | None:
    """Raksta izmaiņas. Atgriež kļūdas tekstu vai None."""
    note = state["note"]
    brief_new = next((new for kind, _, _, new in changed if kind == "brief"), None)
    if brief_new is not None:
        result = json.loads(store_context_note(topic=note["topic"], note_type=note["note_type"],
                                               content=brief_new, source=note["source"]))
        if result.get("status") != "success" or result.get("note_id") != note["id"]:
            return f"store_context_note atteica vai ierakstīja citā rindā: {result}"
    db = get_db()
    try:
        with db:
            keep = note["note_type"] == "daily_brief" and state["subject"] != current_routine_day()
            if brief_new is not None and keep:
                db.execute("UPDATE context_notes SET created_at = ? WHERE id = ?",
                           (note["created_at"], note["id"]))
            for kind, sid, _, new_text in changed:
                if kind == "note":
                    db.execute("UPDATE context_notes SET content = ? WHERE id = ?", (new_text, sid))
                elif kind == "tension":
                    db.execute("UPDATE political_tensions SET description = ? WHERE id = ?", (new_text, sid))
    finally:
        db.close()
    return None


def _report(state: dict, p: dict) -> None:
    note, ex = state["note"], p["examined"]
    print(f"Pārskats {note['id']} «{note['topic']}»; logs {state['window'][0]} … {state['window'][1]} LV")
    print(f"Pārbaudītas vietas: pārskats 1, konteksta piezīmes {ex['note']}, spriedzes {ex['tension']}")
    if p["skipped_published"]:
        print(f"Izlaistas publicētās piezīmes (--skip-published-notes): {p['skipped_published']}")
    for i, h in enumerate(p["hits"], 1):
        where = ", ".join(f"{kind} {sid} ×{n}" for (kind, sid), n in h["per"].items()) or "NAV ATRASTS"
        print(f"{i}. {h['old'][:70]!r}\n   → {h['new'][:70]!r}\n   vietas: {where}")


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description="Pārskata labojumi visās vietās (noklusējums dry-run).")
    ap.add_argument("--note", type=int, required=True, help="pārskata context_notes.id")
    ap.add_argument("--fixes", required=True, help='JSON: [["vecais", "jaunais"], …]')
    ap.add_argument("--tag", required=True, help="rollback faila vārda daļa, piem. r1")
    ap.add_argument("--skip-published-notes", action="store_true",
                    help="nelabot jau publicētas konteksta piezīmes (tās paliek kā vēsture)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--write-rollback", action="store_true")
    g.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)

    try:
        pairs = load_pairs(args.fixes)
    except (ValueError, TypeError, json.JSONDecodeError) as e:
        print(f"ATSAKU: nederīgs fixes fails: {e}")
        return 2
    if not pairs:
        print("Fixes saraksts tukšs — nekas nav darāms.")
        return 0

    db = get_db()
    try:
        state = collect(db, args.note)
    except Refuse as e:
        print(f"ATSAKU: {e}")
        return 2
    finally:
        db.close()

    p = plan(state, pairs, args.skip_published_notes)
    _report(state, p)
    if p["problems"]:
        print("ATSAKU — nekas nav rakstīts:")
        for line in p["problems"]:
            print(f"  - {line}")
        return 2

    slug = brief_publish_key(state["note"]["note_type"], state["subject"])
    rb = DATA_DIR / f"rollback_qr_fixes_{slug}_{args.tag}.sql"
    digest = state_hash(state, pairs, p["changed"])

    if args.write_rollback:
        rb.parent.mkdir(parents=True, exist_ok=True)
        rb.write_text(rollback_sql(state, p["changed"], digest, args.tag, args.fixes),
                      encoding="utf-8", newline="\n")
        print(f"Rollback uzrakstīts: {rb}\nCommitē to PIRMS --apply (CLAUDE.md escalation 8).")
        return 0
    if not args.apply:
        print(f"Dry-run: pāru {len(pairs)}, mainītu vietu {len(p['changed'])} — nekas nav rakstīts. "
              "Nākamais solis: --write-rollback.")
        return 0

    if not rb.exists():
        print(f"ATSAKU: nav rollback faila {rb}. Vispirms --write-rollback un commit.")
        return 2
    if not is_git_tracked(rb):
        print(f"ATSAKU: {rb.name} nav commitēts (git ls-files). Commitē to PIRMS --apply.")
        return 2
    m = _STATE_LINE.search(rb.read_text(encoding="utf-8"))
    if not m or m.group(1) != digest:
        print("ATSAKU: rollback neatbilst pašreizējam DB tekstam vai šiem pāriem. "
              "Pārraksti ar --write-rollback un commitē vēlreiz.")
        return 2

    error = apply_changes(state, p["changed"])
    if error:
        print(f"KĻŪDA: {error}")
        return 1

    db = get_db()
    try:
        now = collect(db, args.note)
    finally:
        db.close()
    stored = {("brief", now["note"]["id"]): now["note"]["content"]}
    stored.update({("note", n["id"]): n["content"] for n in now["notes"]})
    stored.update({("tension", t["id"]): t["description"] for t in now["tensions"]})
    left = sum(1 for kind, sid, _, new_text in p["changed"] if stored.get((kind, sid)) != new_text)
    print(f"piemēroti {len(pairs)} pāri; vietas, kur glabātais teksts ir plānotais: "
          f"{len(p['changed']) - left} no {len(p['changed'])}. Rollback: {rb}")
    if state["approved"]:
        print(f"UZMANĪBU: «{slug}» ir apstiprināts publicēšanai — saturs mainīts, pirms deploy vajag "
              f"scripts/approve_publish.py {slug} vēlreiz (T15).")
    return 0 if left == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
