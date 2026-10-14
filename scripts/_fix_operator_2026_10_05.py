"""Operatora lēmumi 2026-10-05 vakarā: NEEDS_REVIEW izvērtēšana (#730611, #730593),
Līdakas #730604 dzēšana, Levrences (pid 54) role.

--rollback raksta data/rollback_operator_2026-10-05.sql, --apply izpilda.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import sqlite_vec

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
DB_PATH = ROOT / "data" / "atmina.db"
ROLLBACK = ROOT / "data" / "rollback_operator_2026-10-05.sql"

REVIEW = {
    730611: ("NEEDS_REVIEW: ",
             "Izvērtēts 2026-10-05: atkāpšanos apstiprina vēl 5 avoti (delfi 126303 u. c.); "),
    730593: ("NEEDS_REVIEW: ",
             "Izvērtēts 2026-10-05: pamatojums ir pavediena 2/2 tvītā (doc 125853). "),
}
DELETE_ID = 730604
LEVRENCE = (54, "Bijusī 14. Saeimas deputāte", "15. Saeimā ievēlēta — PRO")


def q(v):
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def main(mode: str) -> None:
    db = sqlite3.connect(DB_PATH)
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    plan = []
    for cid, (old_p, new_p) in REVIEW.items():
        r = db.execute("SELECT reasoning FROM claims WHERE id=?", (cid,)).fetchone()[0]
        assert r.startswith(old_p), (cid, r[:40])
        plan.append((cid, r, new_p + r[len(old_p):]))
    cols = [c[1] for c in db.execute("PRAGMA table_info(claims)")]
    row = db.execute(f"SELECT {','.join(cols)} FROM claims WHERE id=?", (DELETE_ID,)).fetchone()
    assert row is not None and row[cols.index("document_id")] == 125533, row
    pid, old_role, new_role = LEVRENCE
    cur_role = db.execute("SELECT role FROM tracked_politicians WHERE id=?", (pid,)).fetchone()[0]
    assert cur_role == old_role, cur_role

    if mode == "--rollback":
        lines = [
            "-- Forward (2026-10-05 vakarā, operatora lēmums, nekad nav deployots): scripts/_fix_operator_2026_10_05.py",
            "--   claims 730611, 730593: reasoning NEEDS_REVIEW → «Izvērtēts 2026-10-05:» (review_status pārrēķina trigeris);",
            "--   claims 730604 (Līdaka) dzēsts: avots ir Hirša tvīts, kas citē Līdaku (sekundārs, 2025-11-02);",
            "--   tracked_politicians 54 role «Bijusī 14. Saeimas deputāte» → «15. Saeimā ievēlēta — PRO» (doc 125761).",
            "-- Pēc rollback: .venv/Scripts/python.exe scripts/reembed_claims.py 730604",
            "BEGIN;",
        ]
        for cid, old, _ in plan:
            lines.append(f"UPDATE claims SET reasoning = {q(old)} WHERE id = {cid};")
        lines.append(f"INSERT INTO claims ({', '.join(cols)}) VALUES ({', '.join(q(v) for v in row)});")
        lines.append(f"UPDATE tracked_politicians SET role = {q(old_role)} WHERE id = {pid};")
        lines.append("COMMIT;")
        ROLLBACK.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("rollback", ROLLBACK.name)
    elif mode == "--apply":
        assert ROLLBACK.exists()
        with db:
            for cid, old, new in plan:
                assert db.execute("UPDATE claims SET reasoning=? WHERE id=? AND reasoning=?",
                                  (new, cid, old)).rowcount == 1
            db.execute("DELETE FROM claim_vectors WHERE claim_id=?", (DELETE_ID,))
            assert db.execute("DELETE FROM claims WHERE id=?", (DELETE_ID,)).rowcount == 1
            assert db.execute("UPDATE tracked_politicians SET role=? WHERE id=? AND role=?",
                              (new_role, pid, old_role)).rowcount == 1
        for cid in REVIEW:
            print(cid, db.execute("SELECT review_status FROM claims WHERE id=?", (cid,)).fetchone())
        print("deleted", DELETE_ID, db.execute("SELECT COUNT(*) FROM claims WHERE id=?", (DELETE_ID,)).fetchone()[0] == 0)
    else:
        print(len(plan), "reasoning;", "delete", DELETE_ID, row[cols.index("opponent_id")], "; role", cur_role)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "--dry")
