"""Dzēš Siliņas pozīciju #123 — saglabātajā avotā nav viņas izteikuma.

Atsauktā pretruna #17 (confirmed=-1, 2026-11-04) jau saka to pašu; labojuma lapa
`pretrunas/17.html` renderējas tikai no pretrunu rindas (`_fetch_withdrawn_contradictions`),
tāpēc claim_new_id → NULL to neietekmē (paraugs: #27, 2026-09-30). Dokuments 3717
(Delfi, web) paliek — tas ir avots, ne mūsu apgalvojums; nodzēsta tikai pozīcija
Siliņas profilā un pozīciju datos.

    .venv/Scripts/python.exe scripts/fix_delete_claim_123_2026-11-08.py           # dry-run
    .venv/Scripts/python.exe scripts/fix_delete_claim_123_2026-11-08.py --apply

Rollback: data/rollback_delete_claim_123_2026-11-08.sql (pēc tam re-embed:
scripts/reembed_claims.py 123).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db import get_db  # noqa: E402

CONTRA_ID = 17
CLAIM_ID = 123
ROLLBACK = ROOT / "data/rollback_delete_claim_123_2026-11-08.sql"


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

    ct = db.execute("SELECT * FROM contradictions WHERE id=?", (CONTRA_ID,)).fetchone()
    cl = db.execute("SELECT * FROM claims WHERE id=?", (CLAIM_ID,)).fetchone()
    if ct is None or cl is None:
        sys.exit("STOP: pretruna vai claim nav atrasti")
    if ct["confirmed"] != -1 or ct["claim_new_id"] != CLAIM_ID:
        sys.exit(f"STOP: negaidīts stāvoklis confirmed={ct['confirmed']} claim_new_id={ct['claim_new_id']}")
    other = db.execute(
        "SELECT id FROM contradictions WHERE id<>? AND (claim_old_id=? OR claim_new_id=?)",
        (CONTRA_ID, CLAIM_ID, CLAIM_ID)).fetchall()
    if other:
        sys.exit(f"STOP: #{CLAIM_ID} atsaucas arī citas pretrunas {[r[0] for r in other]}")
    print(f"#{CONTRA_ID}: claim_new_id {CLAIM_ID} → NULL; claim #{CLAIM_ID} dzēst")

    # Rollback raksta arī dry-run, lai to var komitēt PIRMS --apply (escalation 8).
    cols = [r[1] for r in db.execute("PRAGMA table_info(claims)")
            if r[1] not in ("review_status", "review_status_at")]
    ROLLBACK.write_text("\n".join([
        "-- Rollback: scripts/fix_delete_claim_123_2026-11-08.py (apply 2026-11-08).",
        f"-- Forward: DELETE claim #{CLAIM_ID} (Siliņa, avotā nav viņas izteikuma); "
        f"contradictions #{CONTRA_ID}.claim_new_id → NULL.",
        f"-- Pēc tam: .venv/Scripts/python.exe scripts/reembed_claims.py {CLAIM_ID}",
        "BEGIN;",
        f"INSERT INTO claims ({', '.join(cols)}) VALUES ({', '.join(lit(cl[c]) for c in cols)});",
        f"UPDATE contradictions SET claim_new_id = {CLAIM_ID} WHERE id = {CONTRA_ID};",
        "COMMIT;",
    ]) + "\n", encoding="utf-8")
    print(f"rollback uzrakstīts: {ROLLBACK.relative_to(ROOT)}")
    if not apply:
        return

    with db:
        db.execute("UPDATE contradictions SET claim_new_id = NULL WHERE id = ?", (CONTRA_ID,))
        db.execute("DELETE FROM claim_vectors WHERE claim_id = ?", (CLAIM_ID,))
        db.execute("DELETE FROM claims WHERE id = ?", (CLAIM_ID,))
    ct = db.execute("SELECT confirmed, claim_new_id FROM contradictions WHERE id=?",
                    (CONTRA_ID,)).fetchone()
    left = db.execute("SELECT COUNT(*) FROM claims WHERE id=?", (CLAIM_ID,)).fetchone()[0]
    queue = db.execute("SELECT COUNT(*) FROM claims WHERE review_status='needs_review'").fetchone()[0]
    print(f"pēc: confirmed={ct[0]} claim_new_id={ct[1]}; claim paliek={left}; needs_review rinda={queue}")
    if ct[0] != -1 or ct[1] is not None or left:
        sys.exit("STOP: saglabātais != plānotais")
    print(f"rollback {ROLLBACK.relative_to(ROOT)}")


if __name__ == "__main__":
    main("--apply" in sys.argv)
