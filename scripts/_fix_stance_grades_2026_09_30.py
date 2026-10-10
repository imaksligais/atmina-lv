"""Stance vērtējums 2026-09-30 (citātu triāžas 60 karogi, operatora lēmums «dari tā»).

A_WITHDRAW (9) → claims dzēsti (stance nav politiķa izteikums / izdomāts / cits runātājs /
dublikāts ar nepareizu avotu). C_LANGUAGE (21) → stance LV labojums tās pašas nozīmes robežās.
B_REWRITE (17) šeit NETIEK aiztikts. Ievade: docs/audits/2026-09-30-citatu-triaza/stance_grades.json.
Rollback: data/rollback_stance_grades_2026-09-30.sql (INSERT + stance atjaunošana; pēc tā
reembed_claims.py visiem ID). Pēc apply: reembed_claims.py C_LANGUAGE ID.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db import get_db  # noqa: E402

SRC = ROOT / "docs/audits/2026-09-30-citatu-triaza/stance_grades.json"
ROLLBACK = ROOT / "data/rollback_stance_grades_2026-09-30.sql"


def lit(v):
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return repr(v)
    return "'" + str(v).replace("'", "''") + "'"


def main(apply: bool) -> None:
    grades = json.loads(SRC.read_text(encoding="utf-8"))
    withdraw = tuple(g["id"] for g in grades if g["grade"] == "A_WITHDRAW")
    fixes = {g["id"]: g["proposed_stance"] for g in grades if g["grade"] == "C_LANGUAGE"}
    db = get_db(None)
    import sqlite_vec
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)

    cols = [r[1] for r in db.execute("PRAGMA table_info(claims)")]
    ph = ",".join("?" * len(withdraw))
    rows = db.execute(f"SELECT {','.join(cols)} FROM claims WHERE id IN ({ph})", withdraw).fetchall()
    refs = db.execute(
        f"SELECT count(*) FROM contradictions WHERE claim_old_id IN ({ph}) OR claim_new_id IN ({ph})",
        withdraw + withdraw,
    ).fetchone()[0]
    old = {i: db.execute("SELECT stance FROM claims WHERE id=?", (i,)).fetchone() for i in fixes}
    missing = [i for i, r in old.items() if r is None]
    bad = [i for i, s in fixes.items() if not s or not s.strip()]
    print(f"withdraw {len(rows)}/{len(withdraw)}, pretrunu atsauces {refs}; stance labojumi {len(fixes)}, "
          f"trūkst {missing}, tukši {bad}")
    if len(rows) != len(withdraw) or refs or missing or bad:
        sys.exit("STOP")
    if not apply:
        return

    ins_cols = [c for c in cols if c not in ("review_status", "review_status_at")]
    lines = ["-- Rollback: scripts/_fix_stance_grades_2026_09_30.py (apply 2026-09-30).",
             f"-- Atjauno {len(rows)} dzēstās claims un {len(fixes)} stance. Pēc tam: "
             ".venv/Scripts/python.exe scripts/reembed_claims.py " + " ".join(map(str, list(withdraw) + list(fixes))),
             "BEGIN;"]
    for r in rows:
        d = dict(zip(cols, r))
        lines.append(f"INSERT INTO claims ({', '.join(ins_cols)}) VALUES ({', '.join(lit(d[c]) for c in ins_cols)});")
    lines += [f"UPDATE claims SET stance = {lit(old[i][0])} WHERE id = {i};" for i in fixes]
    lines.append("COMMIT;")
    ROLLBACK.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with db:
        db.execute(f"DELETE FROM claim_vectors WHERE claim_id IN ({ph})", withdraw)
        db.execute(f"DELETE FROM claims WHERE id IN ({ph})", withdraw)
        for i, s in fixes.items():
            db.execute("UPDATE claims SET stance = ? WHERE id = ?", (s, i))
    left = db.execute(f"SELECT count(*) FROM claims WHERE id IN ({ph})", withdraw).fetchone()[0]
    ok = sum(db.execute("SELECT stance = ? FROM claims WHERE id = ?", (s, i)).fetchone()[0] for i, s in fixes.items())
    print(f"dzēsts {len(withdraw) - left}/{len(withdraw)}, stance {ok}/{len(fixes)}; rollback {ROLLBACK.relative_to(ROOT)}")
    print("REEMBED:", " ".join(map(str, fixes)))
    if left or ok != len(fixes):
        sys.exit("STOP: saglabāto skaits != plānotais")


if __name__ == "__main__":
    main("--apply" in sys.argv)
