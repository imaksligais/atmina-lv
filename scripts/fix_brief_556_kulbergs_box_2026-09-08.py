"""#556 kastītes precizējums: Kulbergs nav «Archer» strīda dalībnieks.

@quality-reviewer otrā pase: Aizsardzības konteksta kastīte ar virsrakstu par
«Archer» iepirkuma strīdu uzskaitīja arī Kulbergu, kura pozīcija ir par
INFORMĀCIJAS TEHNOLOĢIJU iepirkumu prioritātēm pēc vētras. Salikums varēja
likt lasītājam piedēvēt viņam artilērijas iepirkuma kritiku.

Labojums iet TIKAI publicētajā pārskatā (#556). Konteksta piezīme #551 paliek
neskarta — tā ir append-only (CLAUDE.md inv #8), un tās teksts ir tā dienas
ieraksts, ne publicējamā redakcija.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.db import get_db

NOTE_ID = 556
WIKI = ROOT / "wiki" / "dailies" / "2026-09-07.md"
ROLLBACK = ROOT / "data" / "rollback_brief_556_kulbergs_box_2026-09-08.sql"

OLD = "- Andris Kulbergs (Apvienotais saraksts) — nosauc negatavību krīzēm un nepareizas iepirkumu prioritātes."
NEW = "- Andris Kulbergs (Apvienotais saraksts) — ārpus «Archer» strīda: nosauc negatavību energokrīzēm un nepareizas prioritātes informācijas tehnoloģiju iepirkumos."


def sql_quote(db, value):
    return db.execute("SELECT quote(?)", (value,)).fetchone()[0]


with get_db() as db:
    old_content = db.execute(
        "SELECT content FROM context_notes WHERE id=?", (NOTE_ID,)
    ).fetchone()[0]
    if WIKI.read_text(encoding="utf-8") != old_content:
        raise SystemExit("DB un wiki atšķiras JAU PIRMS labojuma — apstājos")
    if old_content.count(OLD) != 1:
        raise SystemExit(f"gaidīts 1 trāpījums, atrasti {old_content.count(OLD)}")

    ROLLBACK.write_text(
        "\n".join([
            "-- ROLLBACK for: #556 Aizsardzības kastītes Kulberga aizzīmes precizējums 2026-09-08.",
            "-- Uz priekšu vērstās izmaiņas piemērošanas datums: 2026-09-08.",
            "-- NB: pēc šī SQL jāatjauno wiki/dailies/2026-09-07.md un jāpārrenderē blog.",
            "BEGIN;",
            f"UPDATE context_notes SET content={sql_quote(db, old_content)} WHERE id={NOTE_ID};",
            "COMMIT;",
        ]) + "\n",
        encoding="utf-8",
    )
    if ROLLBACK.stat().st_size < 1000:
        raise SystemExit("rollback nav droši uzrakstīts")

    new_content = old_content.replace(OLD, NEW, 1)
    db.execute("UPDATE context_notes SET content=? WHERE id=?", (new_content, NOTE_ID))
    db.commit()
    stored = db.execute(
        "SELECT content FROM context_notes WHERE id=?", (NOTE_ID,)
    ).fetchone()[0]

WIKI.write_text(stored, encoding="utf-8")

print(json.dumps({
    "rollback": ROLLBACK.name,
    "replacements": 1,
    "chars_before": len(old_content),
    "chars_after": len(stored),
    "db_matches_expected": stored == new_content,
    "wiki_matches_db": WIKI.read_text(encoding="utf-8") == stored,
    "note_551_untouched": True,
}, ensure_ascii=False, indent=2))
raise SystemExit(0 if stored == new_content and WIKI.read_text(encoding="utf-8") == stored else 1)
