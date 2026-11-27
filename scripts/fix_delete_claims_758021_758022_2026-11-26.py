"""Dzēš Rinkēviča pozīcijas #758021 un #758022 — biroja balss (operatora lēmums 2026-11-26).

Abas (diena.lv/LETA 168662, 168659) ir prezidenta padomnieka Drēģera nodots pārstāsts par
slēgtām tikšanām Rīgas pilī; `.claude/references/claim-extractor/sloti.md` § «Biroja balss nav
amatpersonas balss» tādas neglabā. Pretrunu atsauču nav; dokumenti paliek.

    .venv/Scripts/python.exe scripts/fix_delete_claims_758021_758022_2026-11-26.py           # dry-run
    .venv/Scripts/python.exe scripts/fix_delete_claims_758021_758022_2026-11-26.py --apply

Rollback: data/rollback_delete_claims_758021_758022_2026-11-26.sql (pēc tam re-embed:
scripts/reembed_claims.py 758021 758022).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db import get_db  # noqa: E402

CLAIM_IDS = (758021, 758022)
OPPONENT_ID = 1
ROLLBACK = ROOT / "data/rollback_delete_claims_758021_758022_2026-11-26.sql"


def lit(v):
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return repr(v)
    return "'" + str(v).replace("'", "''") + "'"


def main(apply: bool) -> None:
    db = get_db(None)
    import sqlite_vec
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)
    cols = [r[1] for r in db.execute("PRAGMA table_info(claims)")
            if r[1] not in ("review_status", "review_status_at")]
    lines = ["-- Rollback: scripts/fix_delete_claims_758021_758022_2026-11-26.py (apply 2026-11-26).",
             "-- Forward: DELETE claims #758021, #758022 (Rinkēvičs; biroja balss, operatora lēmums).",
             "-- Pēc tam: .venv/Scripts/python.exe scripts/reembed_claims.py 758021 758022",
             "BEGIN;"]
    for cid in CLAIM_IDS:
        cl = db.execute("SELECT * FROM claims WHERE id=?", (cid,)).fetchone()
        if cl is None or cl["opponent_id"] != OPPONENT_ID:
            sys.exit(f"STOP: #{cid} nav atrasts vai nav Rinkēviča")
        refs = db.execute("SELECT id FROM contradictions WHERE claim_old_id=? OR claim_new_id=?",
                          (cid, cid)).fetchall()
        if refs:
            sys.exit(f"STOP: uz #{cid} atsaucas pretrunas {[r[0] for r in refs]}")
        print(f"claim #{cid} dzēst: {cl['stance'][:80]}…")
        lines.append(f"INSERT INTO claims ({', '.join(cols)}) VALUES ({', '.join(lit(cl[c]) for c in cols)});")
    lines.append("COMMIT;")
    ROLLBACK.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"rollback uzrakstīts: {ROLLBACK.relative_to(ROOT)}")
    if not apply:
        return
    with db:
        for cid in CLAIM_IDS:
            db.execute("DELETE FROM claim_vectors WHERE claim_id = ?", (cid,))
            db.execute("DELETE FROM claims WHERE id = ?", (cid,))
    left = db.execute("SELECT COUNT(*) FROM claims WHERE id IN (758021, 758022)").fetchone()[0]
    print(f"atlikušas rindas: {left}")


if __name__ == "__main__":
    main("--apply" in sys.argv)
