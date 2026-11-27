"""Pieliek NEEDS_REVIEW marķieri Rinkēviča pozīcijai #758021 (biroja balss — operatoram).

#758021 (diena.lv/LETA, 26.11.) un #758022 ir prezidenta padomnieka Drēģera nodots pārstāsts
par slēgtu tikšanos Rīgas pilī. `.claude/references/claim-extractor/sloti.md` § «Biroja balss
nav amatpersonas balss» šādu izteikumu par pozīciju neuzskata, ja tā pati nostāja ±5 d nav
amatpersonas pašas vārdos. #758022 marķieris palika (2c, 26.11.); #758021 marķiera nebija, tāpēc
skelets to nestu pārskatā. Lēmumu (dzēst vai paturēt) pieņem operators.

    .venv/Scripts/python.exe scripts/fix_mark_needs_review_758021_2026-11-26.py           # dry-run + rollback
    .venv/Scripts/python.exe scripts/fix_mark_needs_review_758021_2026-11-26.py --apply

Rollback: data/rollback_mark_needs_review_758021_2026-11-26.sql
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db import get_db  # noqa: E402

CLAIM_ID = 758021
ROLLBACK = ROOT / "data/rollback_mark_needs_review_758021_2026-11-26.sql"
MARKER = ("NEEDS_REVIEW: biroja balss — prezidenta padomnieka nodots slēgtas tikšanās pārstāsts "
          "(sloti.md § Biroja balss); operatora lēmums: paturēt vai dzēst. ")


def lit(v):
    return "NULL" if v is None else "'" + str(v).replace("'", "''") + "'"


def main(apply: bool) -> None:
    db = get_db(None)
    row = db.execute("SELECT opponent_id, reasoning FROM claims WHERE id=?", (CLAIM_ID,)).fetchone()
    if row is None or row["opponent_id"] != 1:
        sys.exit("STOP: claim nav atrasts vai nav Rinkēviča (pid 1)")
    old = row["reasoning"] or ""
    if old.startswith("NEEDS_REVIEW:"):
        sys.exit("STOP: marķieris jau ir")
    ROLLBACK.write_text("\n".join([
        "-- Rollback: scripts/fix_mark_needs_review_758021_2026-11-26.py (apply 2026-11-26).",
        f"-- Forward: claims #{CLAIM_ID}.reasoning = NEEDS_REVIEW marķieris + vecais teksts.",
        "BEGIN;",
        f"UPDATE claims SET reasoning = {lit(old)} WHERE id = {CLAIM_ID};",
        "COMMIT;",
    ]) + "\n", encoding="utf-8")
    print(f"rollback uzrakstīts: {ROLLBACK.relative_to(ROOT)}")
    if not apply:
        return
    with db:
        db.execute("UPDATE claims SET reasoning = ? WHERE id = ?", (MARKER + old, CLAIM_ID))
    st = db.execute("SELECT review_status FROM claims WHERE id=?", (CLAIM_ID,)).fetchone()[0]
    print(f"#{CLAIM_ID} review_status: {st}")


if __name__ == "__main__":
    main("--apply" in sys.argv)
