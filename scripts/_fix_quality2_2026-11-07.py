"""Rutīna 2026-11-07: @quality-reviewer atkārtotās pārbaudes labojumi (1.–5.).

  --write-rollback  uzraksta data/rollback_quality2_2026-11-07.sql no pašreizējām DB vērtībām
  --apply           izpilda forward (atsaka, ja rollback nav commitēts)

Pēc --apply: scripts/reembed_claims.py 753290 753318 753330; wiki_sync().
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from src.db import get_db  # noqa: E402

RB = Path("data/rollback_quality2_2026-11-07.sql")

CLAIMS = {
    753290: ("Kozlovski un Bražu", "Kozlovski un Braži"),
    753318: ("konferencē un uzskata, ka nevar prasīt", "konferencē, un uzskata, ka nevar prasīt"),
    753330: ("ir brīdinājis, ka viņus audzinās.", "ir brīdinājis, ka viņš tos audzinās."),
}
TENSION = (610, "Liepnieks ironizē par Kulberga, viņa vārdiem, atklāsmēm",
           "Liepnieks ironizē par to, ko viņš sauc par Kulberga atklāsmēm")
BRIEF = [
    ("pret JV politiķiem Bražu un Kozlovski migrantu izņēmumu dēļ", "pret Braži un Kozlovski (JV) migrantu izņēmumu dēļ"),
    ("Braže (JV) atbalstu Ukrainai sauc par efektīvāko ceļu uz mieru, Rihards Kols (NA) aicina atbrīvot Tanzānijas opozīcijas līderi, bet Kiršteins",
     "Braže (JV) atbalstu Ukrainai sauc par efektīvāko ceļu uz mieru, un Rihards Kols (NA) aicina atbrīvot Tanzānijas opozīcijas līderi. Kiršteins"),
    CLAIMS[753290], CLAIMS[753318], CLAIMS[753330], TENSION[1:],
]


def _sql(s):
    return "'" + s.replace("'", "''") + "'"


def write_rollback(db):
    L = ["-- Rollback: rutīna 2026-11-07, kvalitātes labojumi 2 (scripts/_fix_quality2_2026-11-07.py)",
         "-- Forward: claims stance 753290/753318/753330; political_tensions 610; context_notes 803. Apply date: 2026-11-07.",
         "-- Pēc rollback: scripts/reembed_claims.py 753290 753318 753330", "BEGIN;"]
    for cid, (old, _) in CLAIMS.items():
        s = db.execute("SELECT stance FROM claims WHERE id=?", (cid,)).fetchone()[0]
        assert old in s, cid
        L.append(f"UPDATE claims SET stance={_sql(s)} WHERE id={cid};")
    d = db.execute("SELECT description FROM political_tensions WHERE id=610").fetchone()[0]
    L.append(f"UPDATE political_tensions SET description={_sql(d)} WHERE id=610;")
    c = db.execute("SELECT content FROM context_notes WHERE id=803").fetchone()[0]
    L.append(f"UPDATE context_notes SET content={_sql(c)} WHERE id=803;")
    L.append("COMMIT;")
    RB.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("rakstīts", RB)


def apply(db):
    from src.tools import store_context_note
    if subprocess.run(["git", "ls-files", "--error-unmatch", str(RB)], capture_output=True).returncode \
            or subprocess.run(["git", "diff", "--quiet", "HEAD", "--", str(RB)]).returncode:
        sys.exit(f"STOP: {RB} nav commitēts")
    content, topic, source = db.execute("SELECT content, topic, source FROM context_notes WHERE id=803").fetchone()
    for old, new in BRIEF:
        assert content.count(old) == 1, old[:50]
        content = content.replace(old, new)
    for cid, (old, new) in CLAIMS.items():
        assert db.execute("UPDATE claims SET stance=replace(stance, ?, ?) WHERE id=? AND instr(stance, ?)>0",
                          (old, new, cid, old)).rowcount == 1, cid
    assert db.execute("UPDATE political_tensions SET description=replace(description, ?, ?) WHERE id=610",
                      TENSION[1:]).rowcount == 1
    db.commit()
    print(store_context_note(topic=topic, note_type="daily_brief", content=content, source=source))


if __name__ == "__main__":
    db = get_db()
    if "--write-rollback" in sys.argv:
        write_rollback(db)
    elif "--apply" in sys.argv:
        apply(db)
    else:
        print(__doc__)
