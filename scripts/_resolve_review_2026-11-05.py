"""Rutīnas 2026-11-05 solis 2c, četri stance precizējumi un Mežala role (T6).

  --write-rollback  raksta data/rollback_needs_review_2026-11-05.sql ar sākotnējām vērtībām
  --apply           izpilda forward (atsaka, ja rollback nav commitēts)

Pēc --apply: scripts/reembed_claims.py 753204 753222 753226 753227 (stance mainīts).
Atstāts operatoram: 753195 (conf 0,45; tvīta konteksts nav atrodams, nevar pierādīt,
uz kuru gadījumu tas attiecas).
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from src.db import get_db  # noqa: E402

DAY = "2026-11-05"
RB = Path("data/rollback_needs_review_2026-11-05.sql")
MARK = "NEEDS_REVIEW:"

EVIDENCE = {
    753218: "paša tvīts; vērtējums par imigrācijas likumu ir burtisks citātā un nav atkarīgs no nenosauktās personas, stance to nenosauc",
    753219: "paša tvīts; abi apgalvojumi burtiski, persona nav nosaukta, asais apzīmējums ietīts «ko raksturo kā»",
    753224: "paša tvīts; stance atkārto tikai trīs avota teikumus un nepievieno notikumu",
    753225: "paša atbilde pirmajā personā; fakti par saviem amatiem burtiski, otras puses apsūdzības stance neatkārto",
    753233: "paša tvīts; vērtējums burtisks, apzīmējums ietīts atribūcijā, konkrēta darbība Kulbergam nav piedēvēta",
    753235: "paša atbilde ar konkrētu tehnisku priekšlikumu; visi elementi burtiski avotā, iela nav nosaukta arī stance",
    753238: "RT ar NATO pavēlniecības tvītu, kurā citēti Bražes pašas pirmās personas vārdi, ko viņa pati pārpublicējusi; citāts burtisks",
    753239: "Hermanis pats pārsūta TV24 atstāstu par savu teikto; atruna «varētu» saglabāta, citāta nav, un confidence 0,55 to atspoguļo",
}

# (vecā apakšvirkne, jaunā): aizstāj tikai šo fragmentu, lai pārējais teksts nemainās.
STANCE = {
    753204: ("identificēt šādus satiksmes gadījumus", "identificēt agresīvas braukšanas gadījumus"),
    753222: ("dalībvalstu un ieinteresēto pušu atbalstu noteikumu īstenošanā",
             "atbalstu dalībvalstīm un ieinteresētajām pusēm noteikumu īstenošanā"),
    753226: ("iecere jānoraida, jo 6,91 miljona eiro gada ekonomija būtu «cilvēku dzīves cena»",
             "iecere jānoraida, un vērtē, ka 6,91 miljona eiro gada ekonomija būtu «cilvēku dzīves cena»"),
    753227: ("joprojām nav izmērāma darba un rezultātu", "joprojām nav izmērāmu darbu un rezultātu"),
}

ROLE = {163: ("EP deputāta palīgs", "Rīgas domes deputāts")}


def q(s) -> str:
    return "NULL" if s is None else "'" + str(s).replace("'", "''") + "'"


def new_reasoning(old: str, ev: str) -> str:
    assert old.startswith(MARK), old[:40]
    rest = old[len(MARK):].strip().replace("NEEDS_REVIEW", "marķieris")
    return f"Izvērtēts {DAY}: {ev}. Sākotnēji: {rest}"


def write_rollback(db) -> None:
    lines = [f"-- Rollback: rutīnas {DAY} solis 2c, stance precizējumi un Mežala role.",
             f"-- Forward: scripts/_resolve_review_2026-11-05.py --apply, {DAY}.",
             "-- Pēc stance atjaunošanas: scripts/reembed_claims.py 753204 753222 753226 753227.",
             "BEGIN;"]
    for cid in sorted(EVIDENCE):
        r = db.execute("SELECT reasoning FROM claims WHERE id=?", (cid,)).fetchone()
        lines.append(f"UPDATE claims SET reasoning={q(r[0])} WHERE id={cid};")
    for cid in sorted(STANCE):
        r = db.execute("SELECT stance FROM claims WHERE id=?", (cid,)).fetchone()
        lines.append(f"UPDATE claims SET stance={q(r[0])} WHERE id={cid};")
    for pid, (old, _) in ROLE.items():
        lines.append(f"UPDATE tracked_politicians SET role={q(old)} WHERE id={pid};")
    lines.append("COMMIT;")
    RB.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"uzrakstīts {RB}")


def apply(db) -> None:
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", str(RB)], capture_output=True)
    dirty = subprocess.run(["git", "status", "--porcelain", "--", str(RB)], capture_output=True, text=True)
    if tracked.returncode or dirty.stdout.strip():
        sys.exit(f"rollback nav commitēts: {RB}")
    for cid, ev in EVIDENCE.items():
        old = db.execute("SELECT reasoning FROM claims WHERE id=?", (cid,)).fetchone()[0]
        n = db.execute("UPDATE claims SET reasoning=? WHERE id=?", (new_reasoning(old, ev), cid)).rowcount
        assert n == 1, cid
    for cid, (a, b) in STANCE.items():
        old = db.execute("SELECT stance FROM claims WHERE id=?", (cid,)).fetchone()[0]
        assert old.count(a) == 1, (cid, old)
        db.execute("UPDATE claims SET stance=? WHERE id=?", (old.replace(a, b), cid))
    for pid, (old, new) in ROLE.items():
        n = db.execute("UPDATE tracked_politicians SET role=? WHERE id=? AND role=?", (new, pid, old)).rowcount
        assert n == 1, pid
    db.commit()
    ids = ",".join(map(str, EVIDENCE))
    still = db.execute(f"SELECT COUNT(*) FROM claims WHERE id IN ({ids}) AND review_status='needs_review'").fetchone()[0]
    print(f"izvērtēti {len(EVIDENCE)}, needs_review palika {still}; stance {len(STANCE)}; role {len(ROLE)}")
    assert still == 0


if __name__ == "__main__":
    conn = get_db()
    if "--write-rollback" in sys.argv:
        write_rollback(conn)
    elif "--apply" in sys.argv:
        apply(conn)
    else:
        sys.exit(__doc__)
