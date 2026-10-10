"""Atsauc publicēto pretrunu #27 (Siliņa) un tās nepamatoto agrāko pusi claim #6991.

Operatora lēmums 2026-09-30 (docs/plans/2026-09-30-pretrunas-atsaukums.md): #6991
ir Saeimas 1. aprīļa balsojuma apraksts, kurā Siliņa nerunā (stance pārbaude
«bez citāta», RUBRIKA 1. klase), tāpēc pretruna #27 ar viņas 10. maija prasību
(#18094) nav pamatota. Publicētais 10.05. pārskats saista uz /pretrunas/27.html,
tāpēc pretruna netiek slēpta (`confirmed=0`), bet atsaukta (`confirmed=-1` +
labojuma piezīme), un lapa paliek sasniedzama.

    .venv/Scripts/python.exe scripts/fix_withdraw_contradiction_27_2026-09-30.py           # dry-run
    .venv/Scripts/python.exe scripts/fix_withdraw_contradiction_27_2026-09-30.py --apply

Rollback: data/rollback_withdraw_contradiction_27_2026-09-30.sql (pēc tam re-embed #6991:
scripts/reembed_claims.py 6991).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db import get_db, withdraw_contradiction  # noqa: E402

CONTRA_ID = 27
CLAIM_ID = 6991
NOTE = (
    "Pretruna atsaukta 2026-09-30. Tās agrākā puse bija Saeimas 1. aprīļa balsojums, "
    "kurā koalīcija noraidīja Sprūda demisijas pieprasījumu; Siliņa šajā avotā nerunā, "
    "tāpēc tas nav viņas izteikums, un pretruna starp to un viņas 10. maija prasību nav pamatota."
)
ROLLBACK = ROOT / "data/rollback_withdraw_contradiction_27_2026-09-30.sql"


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
    if ct["confirmed"] != 1 or ct["claim_old_id"] != CLAIM_ID:
        sys.exit(f"STOP: negaidīts stāvoklis confirmed={ct['confirmed']} claim_old_id={ct['claim_old_id']}")
    other = db.execute(
        "SELECT id FROM contradictions WHERE id<>? AND (claim_old_id=? OR claim_new_id=?)",
        (CONTRA_ID, CLAIM_ID, CLAIM_ID)).fetchall()
    if other:
        sys.exit(f"STOP: #{CLAIM_ID} atsaucas arī citas pretrunas {[r[0] for r in other]}")
    print(f"#{CONTRA_ID}: confirmed=1 → -1; claim #{CLAIM_ID} dzēst; claim_old_id → NULL")
    if not apply:
        return

    cols = [r[1] for r in db.execute("PRAGMA table_info(claims)")
            if r[1] not in ("review_status", "review_status_at")]
    ROLLBACK.write_text("\n".join([
        f"-- Rollback: scripts/fix_withdraw_contradiction_27_2026-09-30.py (apply 2026-09-30).",
        f"-- Atjauno claim #{CLAIM_ID} un publicēto pretrunu #{CONTRA_ID}. Pēc tam: "
        f".venv/Scripts/python.exe scripts/reembed_claims.py {CLAIM_ID}",
        "BEGIN;",
        f"INSERT INTO claims ({', '.join(cols)}) VALUES ({', '.join(lit(cl[c]) for c in cols)});",
        f"UPDATE contradictions SET confirmed = 1, withdrawn_at = NULL, withdrawn_note = NULL, "
        f"claim_old_id = {CLAIM_ID} WHERE id = {CONTRA_ID};",
        "COMMIT;",
    ]) + "\n", encoding="utf-8")

    with db:
        withdraw_contradiction(CONTRA_ID, NOTE, db=db)
        db.execute("UPDATE contradictions SET claim_old_id = NULL WHERE id = ?", (CONTRA_ID,))
        db.execute("DELETE FROM claim_vectors WHERE claim_id = ?", (CLAIM_ID,))
        db.execute("DELETE FROM claims WHERE id = ?", (CLAIM_ID,))
    ct = db.execute("SELECT confirmed, claim_old_id, withdrawn_note FROM contradictions WHERE id=?",
                    (CONTRA_ID,)).fetchone()
    left = db.execute("SELECT COUNT(*) FROM claims WHERE id=?", (CLAIM_ID,)).fetchone()[0]
    print(f"pēc: confirmed={ct[0]} claim_old_id={ct[1]} piezīme={'ir' if ct[2] else 'NAV'}; claim paliek={left}")
    if ct[0] != -1 or ct[1] is not None or not ct[2] or left:
        sys.exit("STOP: saglabātais != plānotais")
    print(f"rollback {ROLLBACK.relative_to(ROOT)}")


if __name__ == "__main__":
    main("--apply" in sys.argv)
