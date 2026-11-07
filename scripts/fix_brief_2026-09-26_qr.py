"""@quality-reviewer atradumi pārskatam 2026-09-26 (pirms publicēšanas):
piezīme #647 (tā pati rutīnas diena, nepublicēta — inv 8 otrais izņēmums), spriedze #395,
pārskats #648 (UPSERT caur store_context_note) + wiki/dailies fails.
Raksta rollback PIRMS piemērošanas; --apply raksta DB."""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")

DB = "data/atmina.db"
ROLLBACK = "data/rollback_brief_2026-09-26_qr.sql"
WIKI = "wiki/dailies/2026-09-26.md"

# Piezīmes #647 teksts: datums «21. septembrī … Saeimas komisijā» bija nepareizs
# (21.09. komisija tikai paziņoja, ka vērtēs — doc 112771), «utopija» ir 21.09. izteikums.
NOTE_REPL = [
    ("21. septembrī iecere nonāca Saeimas komisijā, šodien to apšauba paša mēra koalīcijas partneri. ",
     "Mēra pagaidu tilta iecere kļūst par Rīgas domes koalīcijas iekšēju jautājumu. "),
    ("— sauc aptuveni 20 miljonu eiro ieceri par utopiju, saista to ar vēlēšanu tuvumu un aicina naudu ieguldīt citur Rīgā",
     "— iecerē nav iesaistīta «Rīgas satiksme»; saista to ar vēlēšanu tuvumu un aicina aptuveni 20 miljonus eiro ieguldīt citur Rīgā"),
]

T395_NEW = ("Vicemērs Sprindžuks norāda, ka mēra Kleinberga pagaidu tilta iecerē nav iesaistīta «Rīgas satiksme», "
            "un saista to ar vēlēšanu tuvumu; Kleinbergs norāda, ka paļaujas uz ekspertiem, kuri pagaidu tiltu "
            "uzskata par labāko risinājumu.")

# Skelets kastītē rindkopas sākuma «21.» eskeipo kā «21\.» (markdown <ol> slazds).
BRIEF_REPL = [("21\\. " + NOTE_REPL[0][0][len("21. "):], NOTE_REPL[0][1]), NOTE_REPL[1]] + [
    ("- **Vanšu tilts Rīgas domes koalīcijā:** vicemērs Sprindžuks (AS) mēra Kleinberga (PRO) ieceri par aptuveni 20 miljonu eiro pagaidu tiltu sauc par utopiju, bet Ratnieks (NA) norāda, ka koalīcijā tā nav apspriesta; Kleinbergs paļaujas uz ekspertiem.",
     "- **Vanšu tilts Rīgas domes koalīcijā:** vicemēri Ratnieks (NA) un Sprindžuks (AS) norāda, ka mēra Kleinberga (PRO) pagaidu tilta iecere koalīcijā nav apspriesta; Sprindžuks piebilst, ka tajā nav iesaistīta «Rīgas satiksme». Kleinbergs paļaujas uz ekspertiem."),
    ("Stepaņenko tēva iekļaušana sarakstā būtu pirmsvēlēšanu cīņas elements",
     "Stepaņenko tēva iekļaušana sarakstā būtu tikai pirmsvēlēšanu cīņas elements"),
    ("Rīgas domē, kur koalīcijā kopā strādā valdības partijas AS un NA un opozīcijas Progresīvie, domstarpības dienā redzamas ap mēra Kleinberga pagaidu tilta ieceri.",
     "Rīgas domē, kur mēra Kleinberga (PRO) koalīcijā ir arī valdības partijas AS, NA un JV, domstarpības dienā redzamas ap viņa pagaidu tilta ieceri."),
    ("- Krusts (MMN) — iebilst pret imigrāciju no trešajām valstīm, ko attaisno ar ekonomiskiem argumentiem.",
     "- Krusts (MMN) — iebilst pret imigrāciju no trešajām valstīm, ko citi attaisno ar ekonomiskiem argumentiem."),
    ("**Budžeta tēmā dienā ir divas līnijas:", "**Budžeta tēmā izceļas divas līnijas:"),
]


def q(v):
    return "'" + str(v).replace("'", "''") + "'"


db = sqlite3.connect(DB)
db.row_factory = sqlite3.Row
note = db.execute("SELECT content, created_at FROM context_notes WHERE id = 647 AND note_type='context'").fetchone()
assert note["created_at"].startswith("2026-09-26")
t395 = db.execute("SELECT description FROM political_tensions WHERE id = 395").fetchone()["description"]
old_t395 = t395
brief = db.execute("SELECT content FROM context_notes WHERE id = 648 AND note_type='daily_brief'").fetchone()["content"]
for old, _ in NOTE_REPL:
    assert note["content"].count(old) == 1, ("piezīme", old)
for old, _ in BRIEF_REPL:
    assert brief.count(old) == 1, ("pārskats", old)
assert brief.count(old_t395) == 1

with open(ROLLBACK, "w", encoding="utf-8") as f:
    f.write("-- Rollback: @quality-reviewer labojumi 2026-09-26 — piezīme #647, spriedze #395, pārskats #648.\n")
    f.write("-- Forward: scripts/fix_brief_2026-09-26_qr.py, piemērots 2026-09-26.\n")
    f.write("BEGIN;\n")
    f.write(f"UPDATE context_notes SET content = {q(note['content'])} WHERE id = 647;\n")
    f.write(f"UPDATE political_tensions SET description = {q(old_t395)} WHERE id = 395;\n")
    f.write(f"UPDATE context_notes SET content = {q(brief)} WHERE id = 648;\n")
    f.write("COMMIT;\n")
print("rollback uzrakstīts:", ROLLBACK)

if "--apply" in sys.argv:
    from src.lv_style import lint_lv_style
    new_note = note["content"]
    for old, new in NOTE_REPL:
        new_note = new_note.replace(old, new)
    new_brief = brief
    for old, new in BRIEF_REPL:
        new_brief = new_brief.replace(old, new)
    new_brief = new_brief.replace(old_t395, T395_NEW)
    assert "\n" not in T395_NEW and "|" not in T395_NEW
    print("lint piezīme:", lint_lv_style(new_note))
    print("lint pārskats:", lint_lv_style(new_brief))
    with db:
        db.execute("UPDATE context_notes SET content = ? WHERE id = 647", (new_note,))
        db.execute("UPDATE political_tensions SET description = ? WHERE id = 395", (T395_NEW,))
    db.close()
    from src.tools import store_context_note
    print(store_context_note(topic="dienas analīze 2026-09-26", note_type="daily_brief", content=new_brief))
    with open(WIKI, "w", encoding="utf-8", newline="") as f:
        f.write(new_brief)
    db = sqlite3.connect(DB)
    stored = db.execute("SELECT id, content FROM context_notes WHERE note_type='daily_brief' "
                        "AND topic='dienas analīze 2026-09-26'").fetchall()
    print("pārskata rindas:", [s[0] for s in stored])
    print("wiki == DB:", open(WIKI, encoding="utf-8", newline="").read() == stored[0][1])
    print("piezīme #647:\n" + db.execute("SELECT content FROM context_notes WHERE id=647").fetchone()[0])
