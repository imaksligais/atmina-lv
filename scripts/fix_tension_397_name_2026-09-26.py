"""Spriedze #397: kails «Hermanis» → «Alvis Hermanis» (avots @AlvisHermanis1, source_pid 29);
tas pats labojums dienas pārskatā #648 (UPSERT caur store_context_note) un wiki/dailies failā.
Neviens no tiem vēl nav publicēts. Raksta rollback PIRMS piemērošanas; --apply raksta DB."""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")

DB = "data/atmina.db"
ROLLBACK = "data/rollback_tension_397_name_2026-09-26.sql"
WIKI = "wiki/dailies/2026-09-26.md"
OLD = "Hermanis aicina Kulberga atbalstītājus"
NEW = "Alvis Hermanis aicina Kulberga atbalstītājus"
BRIEF_OLD = "| " + OLD
BRIEF_NEW = "| " + NEW


def q(v):
    return "'" + str(v).replace("'", "''") + "'"


db = sqlite3.connect(DB)
db.row_factory = sqlite3.Row
t = db.execute("SELECT description, source_pid FROM political_tensions WHERE id = 397").fetchone()
assert t["source_pid"] == 29 and t["description"].startswith(OLD), dict(t)
b = db.execute("SELECT id, content FROM context_notes WHERE id = 648 AND note_type = 'daily_brief'").fetchone()
assert b["content"].count(BRIEF_OLD) == 1, b["content"].count(BRIEF_OLD)

with open(ROLLBACK, "w", encoding="utf-8") as f:
    f.write("-- Rollback: spriedzes #397 apraksts «Hermanis» → «Alvis Hermanis» + tas pats pārskatā #648.\n")
    f.write("-- Forward: scripts/fix_tension_397_name_2026-09-26.py, piemērots 2026-09-26.\n")
    f.write("BEGIN;\n")
    f.write(f"UPDATE political_tensions SET description = {q(t['description'])} WHERE id = 397;\n")
    f.write(f"UPDATE context_notes SET content = {q(b['content'])} WHERE id = 648;\n")
    f.write("COMMIT;\n")
print("rollback uzrakstīts:", ROLLBACK)

if "--apply" in sys.argv:
    with db:
        db.execute("UPDATE political_tensions SET description = ? WHERE id = 397",
                   (t["description"].replace(OLD, NEW, 1),))
    db.close()
    from src.tools import store_context_note
    new_content = b["content"].replace(BRIEF_OLD, BRIEF_NEW)
    print(store_context_note(topic="dienas analīze 2026-09-26", note_type="daily_brief", content=new_content))
    with open(WIKI, "w", encoding="utf-8", newline="") as f:
        f.write(new_content)
    db = sqlite3.connect(DB)
    print(db.execute("SELECT description FROM political_tensions WHERE id = 397").fetchone()[0])
    stored = db.execute("SELECT id, content FROM context_notes WHERE note_type='daily_brief' "
                        "AND topic='dienas analīze 2026-09-26'").fetchall()
    print("pārskata rindas:", len(stored), "id:", [s[0] for s in stored])
    print("wiki == DB:", open(WIKI, encoding="utf-8", newline="").read() == stored[0][1])
    print("kails «| Hermanis aicina» atlicis:", stored[0][1].count(BRIEF_OLD))
