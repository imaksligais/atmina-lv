"""Rutīna 2026-11-07: @quality-reviewer 3. pārbaudes labojumi (1 bloķējošs + 3 ieteikumi).

  --write-rollback  uzraksta data/rollback_quality3_2026-11-07.sql
  --apply           izpilda forward (atsaka, ja rollback nav commitēts)

Pēc --apply: scripts/reembed_claims.py 753291; wiki_sync().
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from src.db import get_db  # noqa: E402

RB = Path("data/rollback_quality3_2026-11-07.sql")

STANCE = (753291, "bet nestu ap 130 miljonu gadā negatīvu ietekmi uz budžetu, tiesvedību risku un darbvietu zaudēšanas risku.",
          "bet budžetam izmaksātu ap 130 miljoniem eiro gadā un nestu tiesvedību risku un darbvietu zaudēšanas risku.")
VELPS = ("Andris Velps (ASL) — katrs vagons jāpārbauda, atsaucoties uz ES Muitas kodeksa 46. pantu",
         "Andris Velps (ASL) — atsaucas uz ES Muitas kodeksa 46. pantu un piedāvā pārbaudīt katru vagonu")
BRIEF = [
    STANCE[1:],
    VELPS,
    ("kritizē partneri JV migrantu izņēmumu dēļ", "kritizē partneri JV, jo Latvija nav starp izņēmumiem migrantu jautājumā"),
    ("pret Braži un Kozlovski (JV) migrantu izņēmumu dēļ", "pret Braži un Kozlovski (JV), jo Latvija nav starp izņēmumiem migrantu jautājumā"),
    ("par izteikumiem par Polijas prezidentu.", "par izteikumiem, ka Polijas prezidentam nevarot uzticēties."),
]


def _sql(s):
    return "'" + s.replace("'", "''") + "'"


def write_rollback(db):
    L = ["-- Rollback: rutīna 2026-11-07, kvalitātes labojumi 3 (scripts/_fix_quality3_2026-11-07.py)",
         "-- Forward: claims 753291 stance; context_notes 800 un 803 content. Apply date: 2026-11-07.",
         "-- Pēc rollback: scripts/reembed_claims.py 753291", "BEGIN;"]
    s = db.execute("SELECT stance FROM claims WHERE id=?", (STANCE[0],)).fetchone()[0]
    assert STANCE[1] in s
    L.append(f"UPDATE claims SET stance={_sql(s)} WHERE id={STANCE[0]};")
    for nid in (800, 803):
        c = db.execute("SELECT content FROM context_notes WHERE id=?", (nid,)).fetchone()[0]
        L.append(f"UPDATE context_notes SET content={_sql(c)} WHERE id={nid};")
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
    assert db.execute("UPDATE claims SET stance=replace(stance, ?, ?) WHERE id=? AND instr(stance, ?)>0",
                      (STANCE[1], STANCE[2], STANCE[0], STANCE[1])).rowcount == 1
    assert db.execute("UPDATE context_notes SET content=replace(content, ?, ?) WHERE id=800 AND instr(content, ?)>0",
                      (VELPS[0], VELPS[1], VELPS[0])).rowcount == 1
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
