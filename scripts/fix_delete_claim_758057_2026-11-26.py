"""Dzēš Šlesera pozīciju #758057 — dublikāts #758068 (tā pati 26.11. Saeimas debašu runa).

#758057 (LSM 168684, bez citāta) un #758068 (Delfi 168717, ar burtisku citātu) abi atstāsta
vienu un to pašu Ainārs Šlesera runu par «Chapter 11» procesu. Abus saglabāja divi paralēli
atgūšanas aģenti; #758057 nonāca DB pēc #758068 aģenta dublikātu pārbaudes. Paliek pilnākā
#758068. Pretrunu atsauču nav; dokuments 168684 paliek.

    .venv/Scripts/python.exe scripts/fix_delete_claim_758057_2026-11-26.py           # dry-run
    .venv/Scripts/python.exe scripts/fix_delete_claim_758057_2026-11-26.py --apply

Rollback: data/rollback_delete_claim_758057_2026-11-26.sql (pēc tam re-embed:
scripts/reembed_claims.py 758057).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db import get_db  # noqa: E402

CLAIM_ID = 758057
OPPONENT_ID = 3
KEEP_ID = 758068
ROLLBACK = ROOT / "data/rollback_delete_claim_758057_2026-11-26.sql"


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

    cl = db.execute("SELECT * FROM claims WHERE id=?", (CLAIM_ID,)).fetchone()
    if cl is None or cl["opponent_id"] != OPPONENT_ID:
        sys.exit("STOP: claim nav atrasts vai nav Šlesera (pid 3)")
    keep = db.execute("SELECT opponent_id FROM claims WHERE id=?", (KEEP_ID,)).fetchone()
    if keep is None or keep[0] != OPPONENT_ID:
        sys.exit(f"STOP: paliekošais #{KEEP_ID} nav atrasts")
    refs = db.execute("SELECT id FROM contradictions WHERE claim_old_id=? OR claim_new_id=?",
                      (CLAIM_ID, CLAIM_ID)).fetchall()
    if refs:
        sys.exit(f"STOP: uz #{CLAIM_ID} atsaucas pretrunas {[r[0] for r in refs]}")
    print(f"claim #{CLAIM_ID} dzēst: {cl['stance'][:90]}…")

    cols = [r[1] for r in db.execute("PRAGMA table_info(claims)")
            if r[1] not in ("review_status", "review_status_at")]
    ROLLBACK.write_text("\n".join([
        "-- Rollback: scripts/fix_delete_claim_758057_2026-11-26.py (apply 2026-11-26).",
        f"-- Forward: DELETE claim #{CLAIM_ID} (Šlesers; dublikāts #{KEEP_ID}, tā pati debašu runa).",
        f"-- Pēc tam: .venv/Scripts/python.exe scripts/reembed_claims.py {CLAIM_ID}",
        "BEGIN;",
        f"INSERT INTO claims ({', '.join(cols)}) VALUES ({', '.join(lit(cl[c]) for c in cols)});",
        "COMMIT;",
    ]) + "\n", encoding="utf-8")
    print(f"rollback uzrakstīts: {ROLLBACK.relative_to(ROOT)}")
    if not apply:
        return

    with db:
        db.execute("DELETE FROM claim_vectors WHERE claim_id = ?", (CLAIM_ID,))
        db.execute("DELETE FROM claims WHERE id = ?", (CLAIM_ID,))
    left = db.execute("SELECT COUNT(*) FROM claims WHERE id=?", (CLAIM_ID,)).fetchone()[0]
    print(f"atlikušas rindas ar id {CLAIM_ID}: {left}")


if __name__ == "__main__":
    main("--apply" in sys.argv)
