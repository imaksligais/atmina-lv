"""Balsojuma 8341 (1243/Lp14 3. las., priekšlikums Nr. 24) kopsavilkums jauca Nr. 23 (Kūtra) ar
Nr. 24 (Juridiskās komisijas, atbalstīts). Avots: 3. lasījuma tabula Nr. 5382 (1243_2.pdf, 75.–76. lpp.),
stenogramma vestnesis.lv/ta/id/371467. Labo saeima_votes.summary + 91 saeima_vote claim stance
(tiem vektoru nav). Rollback: data/rollback_vote_8341_2026-10-21.sql. --write-rollback | --apply"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")
from src.db import get_db  # noqa: E402

NEW = ("Juridiskās komisijas priekšlikums pārejas noteikumos noteiktu, ka advokāts aizskartā mantas "
       "īpašnieka uzdevumā kriminālprocesa atjaunošanu jaunatklātu apstākļu dēļ var pieteikt lietās, kurās "
       "tiesas nolēmums stājies spēkā pēc jaunās normas spēkā stāšanās, bet par agrāk spēkā stājušos "
       "nolēmumu — tikai tad, ja pamatlietā ir attaisnojošs spriedums vai process izbeigts pēc "
       "Kriminālprocesa likuma 377. panta 1. vai 2. punkta; Juridiskā komisija priekšlikumu atbalstīja. "
       "Šis balsojums bija par trešā lasījuma priekšlikumu Nr. 24, nevis par likumprojektu kopumā.")


def low(s):
    return s[0].lower() + s[1:]


def q(s):
    return "'" + s.replace("'", "''") + "'"


db = get_db()
old, url = db.execute("SELECT summary, url FROM saeima_votes WHERE id=8341").fetchone()
assert "2027. gada 31. august" in old, "jau labots?"
rows = db.execute("SELECT id, stance FROM claims WHERE claim_type='saeima_vote' AND source_url=?", (url,)).fetchall()
assert len(rows) == 91 and all(s.count(low(old)) == 1 for _, s in rows), len(rows)

if "--write-rollback" in sys.argv:
    out = ["-- Forward (apply 2026-10-21): saeima_votes 8341 summary Nr.23-teksts -> Nr.24 (Juridiskās komisijas) saturs;",
           "--   91 saeima_vote claims stance tas pats aizstājums (vektoru nav). Skripts: scripts/_fix_vote_8341_summary_2026-10-21.py",
           "BEGIN;", f"UPDATE saeima_votes SET summary={q(old)} WHERE id=8341;"]
    out += [f"UPDATE claims SET stance={q(s)} WHERE id={cid};" for cid, s in rows]
    out.append("COMMIT;")
    (ROOT / "data/rollback_vote_8341_2026-10-21.sql").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("rollback:", len(rows) + 1, "UPDATE")
elif "--apply" in sys.argv:
    db.execute("UPDATE saeima_votes SET summary=? WHERE id=8341", (NEW,))
    for cid, s in rows:
        db.execute("UPDATE claims SET stance=? WHERE id=?", (s.replace(low(old), low(NEW)), cid))
    db.commit()
    left = db.execute("SELECT COUNT(*) FROM claims WHERE stance LIKE '%2027. gada 31. august%'").fetchone()[0]
    print("labotas:", len(rows), "claims + 1 balsojums; vecā teksta paliek:", left)
