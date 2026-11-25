"""Dzēš Kulberga pozīciju #755901 — rīkojumu parakstīja nevis viņš, bet Ministru prezidenta p. i.

Pozīcija («Paraksta rīkojumu … Purgailis … bezalgas atvaļinājumā») glabāta no Dienas
(doc 163244), kas raksta «premjera Andra Kulberga (AS) parakstītais rīkojums». Pirmavotā —
Latvijas Vēstnesī, Ministru prezidenta rīkojums Nr. 2026/1.2.1.-333 (doc 164067) — parakstītājs
ir «Ministru prezidenta … pienākumu izpildītājs … E. Tavars». Operatora lēmums 2026-11-21: dzēst.
Pretrunu atsauču nav; dokuments 163244 paliek (avots, ne mūsu apgalvojums).

    .venv/Scripts/python.exe scripts/fix_delete_claim_755901_2026-11-21.py           # dry-run
    .venv/Scripts/python.exe scripts/fix_delete_claim_755901_2026-11-21.py --apply

Rollback: data/rollback_delete_claim_755901_2026-11-21.sql (pēc tam re-embed:
scripts/reembed_claims.py 755901).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db import get_db  # noqa: E402

CLAIM_ID = 755901
ROLLBACK = ROOT / "data/rollback_delete_claim_755901_2026-11-21.sql"


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
    if cl is None or cl["opponent_id"] != 10:
        sys.exit("STOP: claim nav atrasts vai nav Kulberga")
    refs = db.execute("SELECT id FROM contradictions WHERE claim_old_id=? OR claim_new_id=?",
                      (CLAIM_ID, CLAIM_ID)).fetchall()
    if refs:
        sys.exit(f"STOP: uz #{CLAIM_ID} atsaucas pretrunas {[r[0] for r in refs]}")
    print(f"claim #{CLAIM_ID} dzēst: {cl['stance'][:90]}…")

    cols = [r[1] for r in db.execute("PRAGMA table_info(claims)")
            if r[1] not in ("review_status", "review_status_at")]
    ROLLBACK.write_text("\n".join([
        "-- Rollback: scripts/fix_delete_claim_755901_2026-11-21.py (apply 2026-11-21).",
        f"-- Forward: DELETE claim #{CLAIM_ID} (Kulbergs; rīkojumu parakstīja Ministru prezidenta p. i. E. Tavars, Vēstnesis doc 164067).",
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
