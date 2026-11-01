"""Labo divas nedeplojotas 2026-10-21 konteksta piezīmes (CLAUDE.md inv #8 izņēmums).
Rollback: data/rollback_context_notes_2026-10-21.sql (komitēts pirms apply). --write-rollback | --apply"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.db import get_db
FIX = {732: ("kā nebija anotācijā", "kas nebija anotācijā"),
       733: ("iesniegumu iesniegusi; informāciju tikai saņēmusi un nodevusi tālāk",
             "vērsusies komisijā; pati klāt nav bijusi, informāciju tikai saņēmusi un nodevusi tālāk")}
db = get_db()
def q(s):
    return "'" + s.replace("'", "''") + "'"
if "--write-rollback" in sys.argv:
    out = ["-- Forward (apply 2026-10-21): context_notes 732, 733 — valodas labojums nedeplojotās šodienas piezīmēs.",
           "--   Skripts: scripts/_fix_context_notes_2026-10-21.py", "BEGIN;"]
    for nid in FIX:
        out.append(f"UPDATE context_notes SET content={q(db.execute('SELECT content FROM context_notes WHERE id=?', (nid,)).fetchone()[0])} WHERE id={nid};")
    out.append("COMMIT;")
    (ROOT / "data/rollback_context_notes_2026-10-21.sql").write_text("\n".join(out) + "\n", encoding="utf-8")
elif "--apply" in sys.argv:
    for nid, (a, b) in FIX.items():
        (c,) = db.execute("SELECT content FROM context_notes WHERE id=?", (nid,)).fetchone()
        assert c.count(a) == 1, nid
        db.execute("UPDATE context_notes SET content=? WHERE id=?", (c.replace(a, b), nid))
    db.commit()
    print("labotas:", len(FIX))
