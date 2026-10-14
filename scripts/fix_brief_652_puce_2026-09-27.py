"""Pārskats #652 (dienas analīze 2026-09-27): pievieno Pūces pozīciju #724990 (saglabāta pēc pārskata).

Tās pašas dienas pirms-publicēšanas labojums: rinda «Pārējās tēmas» tabulā, virsraksta skaits,
bloku tabulas «Bez Saeimas frakcijas» skaits + LA, iekšējā statistikas piezīme.
Maina DB rindu un wiki/dailies/2026-09-27.md.

Lietojums: .venv/Scripts/python.exe scripts/fix_brief_652_puce_2026-09-27.py [--apply]
Rollback: data/rollback_brief_652_puce_2026-09-27.sql (raksta pirms --apply)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.db import get_db  # noqa: E402

ROLLBACK = Path("data/rollback_brief_652_puce_2026-09-27.sql")
WIKI = Path("wiki/dailies/2026-09-27.md")
ROW_AFTER = "| [x.com](https://x.com/poznaks/status/2103954721337675856) |\n"


def new_row(db):
    s = db.execute("SELECT stance, source_url FROM claims WHERE id = 724990").fetchone()
    return (f"| Juris Pūce | Latvijas attīstībai | Degviela un enerģētika | {s['stance']} "
            f"| [x.com]({s['source_url']}) |\n")


def transform(c, row):
    reps = [
        ("· 42 pozīcijas (40 politiķu + 2 auditorijas)", "· 43 pozīcijas (41 politiķu + 2 auditorijas)"),
        ("### Pārējās tēmas (9 pozīcijas 8 tēmās)", "### Pārējās tēmas (10 pozīcijas 9 tēmās)"),
        ("| Bez Saeimas frakcijas | 8 | MMN, SC, SV-AJ |", "| Bez Saeimas frakcijas | 9 | MMN, SC, SV-AJ, LA |"),
    ]
    for old, new in reps:
        assert c.count(old) == 1, old
        c = c.replace(old, new)
    i = c.find("### Pārējās tēmas")
    j = c.find(ROW_AFTER, i)
    assert j > i and c.count(ROW_AFTER) >= 1, "tabulas pēdējā rinda nav atrasta"
    j += len(ROW_AFTER)
    return c[:j] + row + c[j:]


def main():
    db = get_db()
    c = db.execute("SELECT content FROM context_notes WHERE id = 652").fetchone()[0]
    assert "Juris Pūce" not in c, "jau pievienots"
    row = new_row(db)
    c2 = transform(c, row)
    w = WIKI.read_bytes().decode("utf-8")
    w2 = transform(w, row)
    if "--apply" not in sys.argv:
        print("sausā palaide OK; +", len(c2) - len(c), "zīmes")
        return
    ROLLBACK.write_text(
        "-- ROLLBACK: pārskata #652 Pūces pozīcijas (#724990) pievienošana\n"
        "-- Atceļ: scripts/fix_brief_652_puce_2026-09-27.py --apply. Piemērots: 2026-09-27.\n"
        "-- wiki/dailies/2026-09-27.md (gitignored) atjauno, ar to pašu skriptu apgriežot izmaiņas vai pārrakstot no DB.\n"
        "BEGIN;\nUPDATE context_notes SET content = '" + c.replace("'", "''") + "' WHERE id = 652;\nCOMMIT;\n",
        encoding="utf-8")
    with db:
        db.execute("UPDATE context_notes SET content = ? WHERE id = 652", (c2,))
    WIKI.write_bytes(w2.encode("utf-8"))
    print("applied; rollback:", ROLLBACK)


if __name__ == "__main__":
    main()
