"""Quality-reviewer labojumi 2026-10-31 (pārskats 772 pirms publicēšanas).

  752781 stance: «tiesu un policiju pārņem» → «tiesu ar policijas palīdzību pārņem» (avots 147498: «ar policiju»)
  752774 stance: «kādus lēmumus un kā pieņemtus» → «kurus lēmumus»
  note 770 (šīs rutīnas, nekad nav deployota — inv. #8 izņēmums): Zeltīta un Kiršteina rindas

  --write-rollback / --apply (atsaka bez commitēta rollback). Pēc --apply:
  scripts/reembed_claims.py 752781 752774
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from src.db import get_db  # noqa: E402

RB = Path("data/rollback_qr_fixes_2026-10-31.sql")
STANCE_SUBS = {
    752781: ("ka viss ir labi, ja konstitucionālo tiesu un policiju pārņem liberāļi",
             "ka viss ir labi, ja konstitucionālo tiesu ar policijas palīdzību pārņem liberāļi"),
    752774: ("kādus lēmumus un kā pieņemtus, tekstā nenosauc", "kurus lēmumus, tekstā nenosauc"),
}
NOTE_ID = 770
NOTE_SUBS = [
    ("ironiski kritizē viedokli, ka tiesu un policiju drīkst pārņemt liberāļi",
     "ironiski kritizē viedokli, ka liberāļi drīkst ar policijas palīdzību pārņemt konstitucionālo tiesu"),
    ("un jautā, kurā pusē ir Latvijas valdība un Kulbergs",
     "un saka, ka šodien redzēs, kurā pusē ir Latvijas valdība un Kulbergs"),
]


def q(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def committed(p: Path) -> bool:
    if subprocess.run(["git", "ls-files", "--error-unmatch", str(p)], capture_output=True).returncode:
        return False
    return subprocess.run(["git", "diff", "--quiet", "HEAD", "--", str(p)]).returncode == 0


def main() -> int:
    db = get_db()
    if "--write-rollback" in sys.argv:
        out = ["-- Forward: 2026-10-31 quality-reviewer labojumi: stance 752781, 752774; context_notes 770 saturs.",
               "-- Rollback atjauno sākotnējās vērtības; pēc tam scripts/reembed_claims.py 752781 752774.", "BEGIN;"]
        for cid, (old, _new) in STANCE_SUBS.items():
            st = db.execute("SELECT stance FROM claims WHERE id=?", (cid,)).fetchone()[0]
            assert old in st, cid
            out.append(f"UPDATE claims SET stance = {q(st)} WHERE id = {cid};")
        c = db.execute("SELECT content FROM context_notes WHERE id=?", (NOTE_ID,)).fetchone()[0]
        for old, _new in NOTE_SUBS:
            assert old in c, old
        out.append(f"UPDATE context_notes SET content = {q(c)} WHERE id = {NOTE_ID};")
        out.append("COMMIT;")
        RB.write_text("\n".join(out) + "\n", encoding="utf-8")
        print(f"rakstīts {RB}")
        return 0
    if "--apply" in sys.argv:
        if not committed(RB):
            print(f"ATSAKA: {RB} nav commitēts")
            return 1
        with db:
            for cid, (old, new) in STANCE_SUBS.items():
                st = db.execute("SELECT stance FROM claims WHERE id=?", (cid,)).fetchone()[0]
                db.execute("UPDATE claims SET stance=? WHERE id=?", (st.replace(old, new), cid))
            c = db.execute("SELECT content FROM context_notes WHERE id=?", (NOTE_ID,)).fetchone()[0]
            for old, new in NOTE_SUBS:
                c = c.replace(old, new)
            db.execute("UPDATE context_notes SET content=? WHERE id=?", (c, NOTE_ID))
        print("izpildīts: 2 stance, 1 piezīme")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
