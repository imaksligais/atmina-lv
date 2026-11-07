"""Rutīnas 2026-11-05 kvalitātes pārbaudes labojumi datos.

  --write-rollback  raksta data/rollback_quality_review_2026-11-05.sql
  --apply           izpilda forward (atsaka, ja rollback nav commitēts)

Pēc --apply: scripts/reembed_claims.py 753198 (stance mainīts).
Vītola atbilde Švinkam pārbaudīta pret X publiskajiem datiem: 2118333597295706326,
in_reply_to 2118246327775555810, 2026-11-05 13:24 UTC.
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from src.db import get_db, store_tension  # noqa: E402

RB = Path("data/rollback_quality_review_2026-11-05.sql")
VITOLS_URL = "https://x.com/guntarsv/status/2118333619726876717"
VITOLS_DESC = ("Vītols Švinkas tekstu par izdevumu pārskatīšanu sauc par «manipulatīvu retoriku» "
               "un skaidro, ka tā nav izdevumu griešana.")

NOTE = {792: ("Pēc budžeta taupības sarunām politiķi runā par deputātu kompensācijām",
              "Politiķi runā par deputātu kompensācijām")}
TENSION = {
    596: ("ka tā grasās atņemt sabiedriskā transporta atvieglojumus",
          "ka tā grasās atņemt 100 % sabiedriskā transporta atvieglojumus"),
    600: ("Švinka atgādina Kučinska solīto «pamatīgo budžeta revīziju» un norāda, ka",
          "Švinka atgādina, ka Kučinskis solīja «pamatīgu budžeta revīziju», un norāda, ka"),
}
STANCE = {753198: ("pamācījusi Egilu Helmani nebraukt uz Ukrainu, uzskata, ka @ltvdefacto prasība ir",
                   "savulaik pamācījusi Egilu Helmani nebraukt uz Ukrainu un nevest palīdzības kravas uz fronti, "
                   "uzskata, ka raidījuma «de facto» prasība ir")}
REASONING = {753243: ("Skaidrojums ir patstāvīgs, lai gan raksts, uz kuru viņš reaģē, nav redzams; stance raksta nosaukumu neizmanto.",
                      "Oriģināls ir atbilde Švinkam 05.11., raksts ir viņa saitētais LSM materiāls; stance raksta nosaukumu neizmanto.")}

TABLES = [("context_notes", "content", NOTE), ("political_tensions", "description", TENSION),
          ("claims", "stance", STANCE), ("claims", "reasoning", REASONING)]


def q(s) -> str:
    return "'" + str(s).replace("'", "''") + "'"


def write_rollback(db) -> None:
    lines = ["-- Rollback: rutīnas 2026-11-05 kvalitātes pārbaudes labojumi datos.",
             "-- Forward: scripts/_fix_quality_review_2026-11-05.py --apply, 2026-11-05.",
             "-- Pēc stance atjaunošanas: scripts/reembed_claims.py 753198.",
             "BEGIN;"]
    for table, col, items in TABLES:
        for rid in items:
            old = db.execute(f"SELECT {col} FROM {table} WHERE id=?", (rid,)).fetchone()[0]
            lines.append(f"UPDATE {table} SET {col}={q(old)} WHERE id={rid};")
    lines.append(f"DELETE FROM political_tensions WHERE source_url={q(VITOLS_URL)} AND source_pid=64 AND target_pid=26;")
    lines.append("COMMIT;")
    RB.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"uzrakstīts {RB}")


def apply(db) -> None:
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", str(RB)], capture_output=True)
    dirty = subprocess.run(["git", "status", "--porcelain", "--", str(RB)], capture_output=True, text=True)
    if tracked.returncode or dirty.stdout.strip():
        sys.exit(f"rollback nav commitēts: {RB}")
    changed = 0
    for table, col, items in TABLES:
        for rid, (a, b) in items.items():
            old = db.execute(f"SELECT {col} FROM {table} WHERE id=?", (rid,)).fetchone()[0]
            assert old.count(a) == 1, (table, rid, old)
            db.execute(f"UPDATE {table} SET {col}=? WHERE id=?", (old.replace(a, b), rid))
            changed += 1
    db.commit()
    tid = store_tension(64, 26, "Budžets un finanses", VITOLS_DESC, tension_type="spriedze", source_url=VITOLS_URL)
    print(f"labotas {changed} rindas; jauna spriedze #{tid}")


if __name__ == "__main__":
    conn = get_db()
    if "--write-rollback" in sys.argv:
        write_rollback(conn)
    elif "--apply" in sys.argv:
        apply(conn)
    else:
        sys.exit(__doc__)
