"""Operatora «jā» 2026-11-24 vakarā (rutīnas pēcdarbi).

- claim 756134 (Rajevskis) dzēsts: «tas smagums» — neatšifrējams konteksts (NEEDS_REVIEW, pārskatā nebija).
- document_politicians (166624, 256) dzēsts: vārdabrālis — runā «Rīgas namu pārvaldnieka» vadītājs Māris Ozoliņš (T1).
- tracked_politicians 240 (Bergholcs) role papildināts: LSM doc 166643 «Ekonomikas ministra birojā kā padomnieks strādās arī … Edgars Bergholcs».
- claim 756207 reasoning: «paša» → «pašas».

Lietošana: --dry (noklusējums) | --rollback (raksta data/rollback_operator_2026-11-24.sql) | --apply
"""
import os
import sys
from pathlib import Path

os.chdir(r"E:\atmina")
sys.path.insert(0, r"E:\atmina")
from src.db import get_db  # noqa: E402

ROLLBACK = Path("data/rollback_operator_2026-11-24.sql")
DELETE_ID = 756134
DP = (166624, 256)
BERG_OLD = "Rīgas domes Pilsētas attīstības komitejas priekšsēdētājs"
BERG_NEW = "Rīgas domes Pilsētas attīstības komitejas priekšsēdētājs; ekonomikas ministra padomnieks (no 2026-11-24)"
R207_OLD = "Ingas Bērziņas paša tvīts"
R207_NEW = "Ingas Bērziņas pašas tvīts"


def q(v):
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def main(mode):
    db = get_db()
    import sqlite_vec
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)
    cols =[c[1] for c in db.execute("PRAGMA table_info(claims)")]
    row = db.execute(f"SELECT {','.join(cols)} FROM claims WHERE id=?", (DELETE_ID,)).fetchone()
    assert row is not None and row[cols.index("opponent_id")] == 63, row
    assert db.execute("SELECT COUNT(*) FROM contradictions WHERE claim_old_id=? OR claim_new_id=?",
                      (DELETE_ID, DELETE_ID)).fetchone()[0] == 0
    dpcols = [c[1] for c in db.execute("PRAGMA table_info(document_politicians)")]
    dprow = db.execute(f"SELECT {','.join(dpcols)} FROM document_politicians WHERE document_id=? AND politician_id=?", DP).fetchone()
    assert dprow is not None and dprow[dpcols.index("role")] == "mentioned", dprow
    assert db.execute("SELECT role FROM tracked_politicians WHERE id=240").fetchone()[0] == BERG_OLD
    r207 = db.execute("SELECT reasoning FROM claims WHERE id=756207").fetchone()[0]
    assert r207.count(R207_OLD) == 1

    if mode == "--rollback":
        lines = [
            "-- Rollback: scripts/_fix_operator_2026_11_24.py (apply 2026-11-24 vakarā, operatora «jā»).",
            "-- Forward: DELETE claim 756134 (+ vektors); DELETE document_politicians (166624, 256);",
            "--   tracked_politicians 240 role papildināts; claim 756207 reasoning «paša» → «pašas».",
            "-- Pēc šī: .venv/Scripts/python.exe scripts/reembed_claims.py 756134",
            "-- Piezīme: tiešs INSERT document_politicians atceļ suppression (CLAUDE.md § Schema invariants).",
            "BEGIN;",
            f"INSERT INTO claims ({', '.join(cols)}) VALUES ({', '.join(q(v) for v in row)});",
            f"INSERT INTO document_politicians ({', '.join(dpcols)}) VALUES ({', '.join(q(v) for v in dprow)});",
            f"UPDATE tracked_politicians SET role = {q(BERG_OLD)} WHERE id = 240;",
            f"UPDATE claims SET reasoning = {q(r207)} WHERE id = 756207;",
            "COMMIT;",
        ]
        ROLLBACK.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("rollback", ROLLBACK)
    elif mode == "--apply":
        assert ROLLBACK.exists()
        with db:
            db.execute("DELETE FROM claim_vectors WHERE claim_id=?", (DELETE_ID,))
            assert db.execute("DELETE FROM claims WHERE id=?", (DELETE_ID,)).rowcount == 1
            assert db.execute("DELETE FROM document_politicians WHERE document_id=? AND politician_id=?", DP).rowcount == 1
            assert db.execute("UPDATE tracked_politicians SET role=? WHERE id=240 AND role=?", (BERG_NEW, BERG_OLD)).rowcount == 1
            assert db.execute("UPDATE claims SET reasoning=? WHERE id=756207", (r207.replace(R207_OLD, R207_NEW),)).rowcount == 1
        print("claim 756134 dzēsts:", db.execute("SELECT COUNT(*) FROM claims WHERE id=?", (DELETE_ID,)).fetchone()[0] == 0)
        print("saite noņemta:", db.execute("SELECT COUNT(*) FROM document_politicians WHERE document_id=? AND politician_id=?", DP).fetchone()[0] == 0)
        print("suppression:", db.execute("SELECT COUNT(*) FROM document_politician_suppressions WHERE document_id=? AND politician_id=?", DP).fetchone()[0])
        print("Bergholcs:", db.execute("SELECT role FROM tracked_politicians WHERE id=240").fetchone()[0])
        print("756207 status:", db.execute("SELECT review_status FROM claims WHERE id=756207").fetchone()[0])
    else:
        print("dry: viss atrasts; delete", DELETE_ID, "dp", DP, "Bergholcs + 756207")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "--dry")
