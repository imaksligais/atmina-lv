"""Atsauc 5 pozīcijas, kuru stance avots neatbalsta (citātu triāža 2026-09-30, operatora lēmums).

#275 Braže — avots: prezidents atļauj nēsāt apbalvojumu, ne viņas pozīcija;
#7514 Briškens — raidījuma anotācija, pats nerunā;
#6978 Dombrava — stance apgalvo pretējo tvītam («apziņošana nenostrādāja»);
#6929 Pūpols — tvītā nav nekā par stāvvietām;
#6951 A. Hermanis — stance izdomāta, tvīts par migrāciju, ne aizsardzību.
Avota dokumenti paliek (paša tvīti ir X apakšcilnē kā spogulis; CLAUDE.md § Deleting a claim).
Pretrunu atsauču 0 (pārbaudīts). Rollback: data/rollback_withdraw_unsound_2026-09-30.sql
(INSERT; pēc tā `scripts/reembed_claims.py 275 7514 6978 6929 6951`).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db import get_db  # noqa: E402

IDS = (275, 7514, 6978, 6929, 6951)
ROLLBACK = ROOT / "data/rollback_withdraw_unsound_2026-09-30.sql"


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

    ph = ",".join("?" * len(IDS))
    cols = [r[1] for r in db.execute("PRAGMA table_info(claims)")]
    rows = db.execute(f"SELECT {','.join(cols)} FROM claims WHERE id IN ({ph})", IDS).fetchall()
    refs = db.execute(
        f"SELECT count(*) FROM contradictions WHERE claim_old_id IN ({ph}) OR claim_new_id IN ({ph})", IDS + IDS
    ).fetchone()[0]
    nvec = db.execute(f"SELECT count(*) FROM claim_vectors WHERE claim_id IN ({ph})", IDS).fetchone()[0]
    print(f"claims {len(rows)}/{len(IDS)}, vektori {nvec}, pretrunu atsauces {refs}")
    if len(rows) != len(IDS) or refs:
        sys.exit("STOP: trūkst rindu vai ir pretrunu atsauces")
    if not apply:
        return

    # review_status/_at atvasina trigeri no reasoning — INSERT tos neraksta.
    ins_cols = [c for c in cols if c not in ("review_status", "review_status_at")]
    lines = ["-- Rollback: scripts/_fix_withdraw_unsound_2026_09_30.py (apply 2026-09-30).",
             f"-- Atjauno {len(rows)} dzēstās claims; pēc tam: .venv/Scripts/python.exe scripts/reembed_claims.py "
             + " ".join(map(str, IDS)),
             "BEGIN;"]
    for r in rows:
        d = dict(zip(cols, r))
        lines.append(f"INSERT INTO claims ({', '.join(ins_cols)}) VALUES ({', '.join(lit(d[c]) for c in ins_cols)});")
    lines.append("COMMIT;")
    ROLLBACK.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with db:
        db.execute(f"DELETE FROM claim_vectors WHERE claim_id IN ({ph})", IDS)
        db.execute(f"DELETE FROM claims WHERE id IN ({ph})", IDS)
    left = db.execute(f"SELECT count(*) FROM claims WHERE id IN ({ph})", IDS).fetchone()[0]
    print(f"dzēsts {len(IDS) - left}/{len(IDS)}; rollback {ROLLBACK.relative_to(ROOT)}")
    if left:
        sys.exit("STOP: ne visas rindas dzēstas")


if __name__ == "__main__":
    main("--apply" in sys.argv)
