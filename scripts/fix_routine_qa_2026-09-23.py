"""Rutīnas 2026-09-23 orķestratora QA labojumi jaunajiem claims (pirms publicēšanas).

- #717986, #717995: stance «N%» -> «N %» (lint no-space-before-percent; mūsu teksts, ne citāts) + re-embed.
- #717982: automātiskais NEEDS_REVIEW kļūdains (frāze «tikai pieminēta» attiecās uz Braži, Šmits runā pats) -> Izvērtēts.
- #717996: tēmas robežas NEEDS_REVIEW -> Izvērtēts (Pilsētvide paliek; Pašvaldības šim dokam aizņemta ar #717993).
Rollback: data/rollback_routine_qa_2026-09-23.sql (pēc tam reembed 717986 717995).
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "atmina.db"
RB = ROOT / "data" / "rollback_routine_qa_2026-09-23.sql"
IDS = [717986, 717995, 717982, 717996]


def lit(v):
    return "NULL" if v is None else "'" + str(v).replace("'", "''") + "'"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    db = sqlite3.connect(DB)
    old = {r[0]: r[1:] for r in db.execute(
        f"SELECT id, stance, reasoning FROM claims WHERE id IN ({','.join(map(str, IDS))})")}
    assert len(old) == 4, old.keys()
    RB.write_text(
        "-- Rollback: scripts/fix_routine_qa_2026-09-23.py (piemērots 2026-09-23)\n"
        "-- PĒC TAM: .venv/Scripts/python.exe scripts/reembed_claims.py 717986 717995\nBEGIN;\n"
        + "".join(f"UPDATE claims SET stance={lit(s)}, reasoning={lit(r)} WHERE id={i};\n" for i, (s, r) in old.items())
        + "COMMIT;\n", encoding="utf-8")
    with db:
        for i, frm, to in [(717986, "2–3%", "2–3 %"), (717995, "10%", "10 %")]:
            s = old[i][0]
            assert frm in s, (i, frm)
            db.execute("UPDATE claims SET stance=? WHERE id=?", (s.replace(frm, to), i))
        r = old[717982][1]
        new = "Izvērtēts 2026-09-23: automātiskais karodziņš kļūdains — «tikai pieminēta» attiecas uz Braži; Šmits runā pats savā tvītā. " + r.split("Original reasoning: ", 1)[1]
        db.execute("UPDATE claims SET reasoning=? WHERE id=?", (new, 717982))
        r = old[717996][1]
        db.execute("UPDATE claims SET reasoning=? WHERE id=?",
                   (r.replace("NEEDS_REVIEW: tēmas robeža", "Izvērtēts 2026-09-23 (tēmas robeža pieņemta)", 1), 717996))
    for i in IDS:
        print(i, db.execute("SELECT review_status, substr(stance,1,120) FROM claims WHERE id=?", (i,)).fetchone())


if __name__ == "__main__":
    main()
