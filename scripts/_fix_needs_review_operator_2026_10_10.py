"""2026-10-10 vēlu vakarā: atlikušās NEEDS_REVIEW (737546 Pūpols, 737562 Rajevskis)
izvērtētas pēc operatora lūguma; 737546 stance atruna, 737562 stated_at.

--rollback raksta data/rollback_needs_review_operator_2026-10-10.sql, --apply izpilda.
Pēc --apply: scripts/reembed_claims.py 737546.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "atmina.db"
ROLLBACK = ROOT / "data" / "rollback_needs_review_operator_2026-10-10.sql"
MARK = "NEEDS_REVIEW: "

REVIEW = {
    737546: "Izvērtēts 2026-10-10: paša tvīts (doc 130682); Kozins identificējams (130340, 123120 — bijušais LSM darbinieks); ironija kritikas nozīmi neapgriež; saite ir paša tvīta medijs; apsūdzība ietīta atrunā (operatora lēmums 2026-10-06). ",
    737562: "Izvērtēts 2026-10-10: tas pats teikums TV24 oriģinālā (doc 130750) un paša 10-09 tvītā ar la.lv virsrakstu «Politologs skaidro Šlesera absolūti viltīgo gājienu» (doc 130109); stated_at → 10-09. ",
}
OLD_STANCE_PART = "par to, ka tas iekārtojies «Novaja Gazeta»"
NEW_STANCE_PART = "par to, ka tas, pēc viņa vārdiem, iekārtojies «Novaja Gazeta»"
STATED = (737562, "2026-10-09 00:00:00")


def q(v):
    return "NULL" if v is None else "'" + str(v).replace("'", "''") + "'"


def main(mode: str) -> None:
    db = sqlite3.connect(DB_PATH)
    plan = []
    for cid, prefix in REVIEW.items():
        r = db.execute("SELECT reasoning FROM claims WHERE id=?", (cid,)).fetchone()[0]
        assert r.startswith(MARK), (cid, r[:40])
        rest = r[len(MARK):]
        assert "NEEDS_REVIEW" not in rest, cid
        plan.append((cid, r, prefix + "Sākotnēji: " + rest))
    stance = db.execute("SELECT stance FROM claims WHERE id=737546").fetchone()[0]
    assert stance.count(OLD_STANCE_PART) == 1
    old_stated = db.execute("SELECT stated_at FROM claims WHERE id=?", (STATED[0],)).fetchone()[0]

    if mode == "--rollback":
        lines = [
            "-- Forward (2026-10-10 vēlu vakarā, operatora lūgums izskatīt atlikušās, nekad nav deployots): scripts/_fix_needs_review_operator_2026_10_10.py",
            "--   claims 737546, 737562: reasoning NEEDS_REVIEW → «Izvērtēts 2026-10-10: … Sākotnēji: …»;",
            "--   737546 stance: «pēc viņa vārdiem» atruna; 737562 stated_at 2026-10-10 → 2026-10-09.",
            "-- Pēc rollback: .venv/Scripts/python.exe scripts/reembed_claims.py 737546",
            "BEGIN;",
        ]
        for cid, old, _ in plan:
            lines.append(f"UPDATE claims SET reasoning = {q(old)} WHERE id = {cid};")
        lines.append(f"UPDATE claims SET stance = {q(stance)} WHERE id = 737546;")
        lines.append(f"UPDATE claims SET stated_at = {q(old_stated)} WHERE id = {STATED[0]};")
        lines.append("COMMIT;")
        ROLLBACK.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("rollback", ROLLBACK.name)
    elif mode == "--apply":
        assert ROLLBACK.exists()
        with db:
            for cid, old, new in plan:
                assert db.execute("UPDATE claims SET reasoning=? WHERE id=? AND reasoning=?",
                                  (new, cid, old)).rowcount == 1
            assert db.execute("UPDATE claims SET stance=? WHERE id=737546 AND stance=?",
                              (stance.replace(OLD_STANCE_PART, NEW_STANCE_PART), stance)).rowcount == 1
            assert db.execute("UPDATE claims SET stated_at=? WHERE id=?", (STATED[1], STATED[0])).rowcount == 1
        for cid in REVIEW:
            print(cid, db.execute("SELECT review_status, stated_at FROM claims WHERE id=?", (cid,)).fetchone())
    else:
        print(len(plan), "reasoning; stance 737546; stated_at 737562", old_stated, "→", STATED[1])


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "--dry")
