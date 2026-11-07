"""NEEDS_REVIEW rinda 2026-11-07: katra rinda izlasīta pret avotu; plāns plan.json.

    --write-rollback   uzraksta data/rollback_needs_review_queue_2026-11-07.sql un .ids
    --apply            vienā transakcijā; bez iecommitota rollback atsaka

Pēc --apply: scripts/reembed_claims.py --ids-from data/rollback_needs_review_queue_2026-11-07.ids
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import sqlite_vec

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from src.db import get_db  # noqa: E402
from src.lv_style import lint_lv_style  # noqa: E402
from src.quality import validate_lv_diacritics  # noqa: E402

PLAN = json.loads((ROOT / "docs/audits/2026-11-07-needs-review/plan.json").read_text(encoding="utf-8"))
ROLLBACK = ROOT / "data/rollback_needs_review_queue_2026-11-07.sql"
IDS = ROLLBACK.with_suffix(".ids")
DAY = "2026-11-07"
MARK = "NEEDS_REVIEW: "
STATED = {2: "2025-12-18 00:00:00", 124: "2026-03-25 00:00:00"}  # avota publiskošanas diena
QUOTE_NULL = (10995,)


def sql(v):
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return repr(v)
    return "'" + str(v).replace("'", "''") + "'"


def gates(db) -> None:
    open_ids = {r[0] for r in db.execute("SELECT id FROM claims WHERE review_status='needs_review'")}
    plan_ids = {int(k) for k in PLAN}
    if open_ids != plan_ids:
        raise SystemExit(f"rinda nesakrīt ar plānu: {open_ids ^ plan_ids}")
    bad = []
    for k, p in PLAN.items():
        if p["action"] == "keep":
            continue
        for t in filter(None, (p.get("stance"), p["evidence"])):
            ok, why = validate_lv_diacritics(t)
            if not ok:
                bad.append((k, why))
            hits = lint_lv_style(t)
            if hits:
                bad.append((k, hits))
        if p["action"] == "delete":
            n = db.execute("SELECT COUNT(*) FROM contradictions WHERE claim_old_id=? OR claim_new_id=?", (k, k)).fetchone()[0]
            if n:
                bad.append((k, "ir pretrunā"))
    if bad:
        raise SystemExit(f"vārti: {bad}")
    print(f"vārti: {len(PLAN)} rindas, 0 atradumu")


def new_reasoning(old: str, evidence: str) -> str:
    assert old.startswith(MARK), old[:80]
    return f"Izvērtēts {DAY}: {evidence.rstrip('.')}. Sākotnēji: {old[len(MARK):]}"


def write_rollback(db) -> None:
    cols = [c[1] for c in db.execute("PRAGMA table_info(claims)") if c[1] not in ("review_status", "review_status_at")]
    lines = [f"-- Rollback: scripts/fix_needs_review_queue_2026-11-07.py (apply {DAY}).",
             "-- Atjauno izvērtētās, pārrakstītās un dzēstās NEEDS_REVIEW rindas. Pēc tam: scripts/reembed_claims.py ar .ids failu.",
             "BEGIN;"]
    ids = []
    for k, p in PLAN.items():
        if p["action"] == "keep":
            continue
        if p["action"] == "delete":
            r = db.execute(f"SELECT {', '.join(cols)} FROM claims WHERE id=?", (k,)).fetchone()
            lines.append(f"INSERT INTO claims ({', '.join(cols)}) VALUES ({', '.join(sql(v) for v in r)});")
            ids.append(k)
        else:
            r = db.execute("SELECT stance, reasoning FROM claims WHERE id=?", (k,)).fetchone()
            lines.append(f"UPDATE claims SET stance={sql(r[0])}, reasoning={sql(r[1])} WHERE id={k};")
            if p["action"] == "rewrite":
                ids.append(k)
    for k in STATED:
        old = db.execute("SELECT stated_at FROM claims WHERE id=?", (k,)).fetchone()[0]
        lines.append(f"UPDATE claims SET stated_at={sql(old)} WHERE id={k};")
    for k in QUOTE_NULL:
        lines.append(f"UPDATE claims SET quote='' WHERE id={k};")
    lines += ["COMMIT;", ""]
    ROLLBACK.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    IDS.write_text("\n".join(ids) + "\n", encoding="utf-8", newline="\n")
    print("rollback:", ROLLBACK.name, len(lines), "rindas;", len(ids), "id pārrēķinam")


def apply(db) -> None:
    for f in (ROLLBACK, IDS):
        tracked = subprocess.run(["git", "ls-files", "--error-unmatch", str(f)], cwd=ROOT, capture_output=True).returncode == 0
        dirty = subprocess.run(["git", "status", "--short", str(f)], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        if not tracked or dirty:
            raise SystemExit(f"{f.name} nav iecommitots")
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    with db:
        for k, p in PLAN.items():
            if p["action"] == "keep":
                continue
            if p["action"] == "delete":
                db.execute("DELETE FROM claim_vectors WHERE claim_id=?", (k,))
                assert db.execute("DELETE FROM claims WHERE id=?", (k,)).rowcount == 1, k
                continue
            old = db.execute("SELECT reasoning FROM claims WHERE id=?", (k,)).fetchone()[0]
            if p["action"] == "rewrite":
                n = db.execute("UPDATE claims SET stance=?, reasoning=? WHERE id=?",
                               (p["stance"], new_reasoning(old, p["evidence"]), k)).rowcount
            else:
                n = db.execute("UPDATE claims SET reasoning=? WHERE id=?", (new_reasoning(old, p["evidence"]), k)).rowcount
            assert n == 1, k
        for k, v in STATED.items():
            assert db.execute("UPDATE claims SET stated_at=? WHERE id=?", (v, k)).rowcount == 1
        for k in QUOTE_NULL:
            assert db.execute("UPDATE claims SET quote=NULL WHERE id=? AND quote=''", (k,)).rowcount == 1
    q = db.execute
    print("needs_review:", [r[0] for r in q("SELECT id FROM claims WHERE review_status='needs_review'")])
    print("reviewed no plāna:", q(f"SELECT COUNT(*) FROM claims WHERE review_status='reviewed' AND id IN ({','.join(PLAN)})").fetchone()[0])
    deleted = ",".join(k for k, p in PLAN.items() if p["action"] == "delete")
    print("dzēstas paliek:", q(f"SELECT COUNT(*) FROM claims WHERE id IN ({deleted})").fetchone()[0])


if __name__ == "__main__":
    conn = get_db()
    gates(conn)
    if "--write-rollback" in sys.argv:
        write_rollback(conn)
    elif "--apply" in sys.argv:
        apply(conn)
