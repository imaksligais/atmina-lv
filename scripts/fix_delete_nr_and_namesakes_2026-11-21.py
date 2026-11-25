"""Operatora lēmums 2026-11-21: dzēš 3 pozīcijas un 4 vārdabrāļu junction saites.

Pozīcijas:
- 755950 (Braže) — dublikāts: tā pati TV24 «Globuss» epizode jau glabāta kā 753859 (13.11.);
  la.lv 161535 (18.11.) atstāsta to pašu; 21.11. TV24 klips bez raidījuma dienas.
- 755949 (Smiltēns) — dublikāts: tas pats arguments (komisijas pēc valdības sastāva) jau ir
  753743 (12.11.); saturs ir pirms 17.11. valdības balsojuma.
- 755929 (Velps) — nesaprotams konteksts (nav zināms, par ko «šī kļūda Saeimā»).
Saites (`document_politicians`, role='subject', 0 pozīciju): 164655→189 («Pūces nakts»),
42438→218 (Jānis Lapiņš, ATD), 71037→218 (Salvis Lapiņš), 81504→218 («lapiņa» augam).
DELETE ieraksta `document_politician_suppressions` (režīms 'record'), tāpēc saites neatgriezīsies.

    .venv/Scripts/python.exe scripts/fix_delete_nr_and_namesakes_2026-11-21.py          # dry-run + rollback
    .venv/Scripts/python.exe scripts/fix_delete_nr_and_namesakes_2026-11-21.py --apply

Rollback: data/rollback_delete_nr_and_namesakes_2026-11-21.sql (tiešs INSERT atceļ saišu
apslāpēšanu; pēc tam re-embed: scripts/reembed_claims.py 755929 755949 755950).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db import get_db  # noqa: E402

CLAIMS = {755950: 15, 755949: 69, 755929: 185}
LINKS = [(164655, 189), (42438, 218), (71037, 218), (81504, 218)]
ROLLBACK = ROOT / "data/rollback_delete_nr_and_namesakes_2026-11-21.sql"


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

    ccols = [r[1] for r in db.execute("PRAGMA table_info(claims)")
             if r[1] not in ("review_status", "review_status_at")]
    lcols = [r[1] for r in db.execute("PRAGMA table_info(document_politicians)")]
    lines = ["-- Rollback: scripts/fix_delete_nr_and_namesakes_2026-11-21.py (apply 2026-11-21).",
             "-- Forward: DELETE claims 755950, 755949, 755929; DELETE document_politicians "
             "164655/189, 42438/218, 71037/218, 81504/218 (vārdabrāļi).",
             "-- Pēc tam: .venv/Scripts/python.exe scripts/reembed_claims.py 755929 755949 755950",
             "BEGIN;"]
    for cid, pid in CLAIMS.items():
        cl = db.execute("SELECT * FROM claims WHERE id=?", (cid,)).fetchone()
        if cl is None or cl["opponent_id"] != pid:
            sys.exit(f"STOP: claim {cid} nav atrasts vai cits pid")
        if db.execute("SELECT 1 FROM contradictions WHERE claim_old_id=? OR claim_new_id=?",
                      (cid, cid)).fetchone():
            sys.exit(f"STOP: uz {cid} atsaucas pretruna")
        lines.append(f"INSERT INTO claims ({', '.join(ccols)}) VALUES "
                     f"({', '.join(lit(cl[c]) for c in ccols)});")
    for d, p in LINKS:
        row = db.execute("SELECT * FROM document_politicians WHERE document_id=? AND politician_id=?",
                         (d, p)).fetchone()
        if row is None:
            sys.exit(f"STOP: saite {d}/{p} nav atrasta")
        if db.execute("SELECT 1 FROM claims WHERE document_id=? AND opponent_id=?", (d, p)).fetchone():
            sys.exit(f"STOP: saitei {d}/{p} ir pozīcijas")
        lines.append(f"INSERT INTO document_politicians ({', '.join(lcols)}) VALUES "
                     f"({', '.join(lit(row[c]) for c in lcols)});")
    lines.append("COMMIT;")
    ROLLBACK.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"rollback uzrakstīts: {ROLLBACK.relative_to(ROOT)}; pozīcijas {len(CLAIMS)}, saites {len(LINKS)}")
    if not apply:
        return

    with db:
        for cid in CLAIMS:
            db.execute("DELETE FROM claim_vectors WHERE claim_id = ?", (cid,))
            db.execute("DELETE FROM claims WHERE id = ?", (cid,))
        for d, p in LINKS:
            db.execute("DELETE FROM document_politicians WHERE document_id=? AND politician_id=?", (d, p))
    left_c = db.execute(f"SELECT COUNT(*) FROM claims WHERE id IN ({','.join('?'*len(CLAIMS))})",
                        list(CLAIMS)).fetchone()[0]
    left_l = sum(db.execute("SELECT COUNT(*) FROM document_politicians WHERE document_id=? AND politician_id=?",
                            lk).fetchone()[0] for lk in LINKS)
    supp = sum(db.execute("SELECT COUNT(*) FROM document_politician_suppressions WHERE document_id=? AND politician_id=?",
                          lk).fetchone()[0] > 0 for lk in LINKS)
    print(f"atlikušas pozīcijas {left_c}, saites {left_l}; apslāpētas {supp} no {len(LINKS)}")


if __name__ == "__main__":
    main("--apply" in sys.argv)
