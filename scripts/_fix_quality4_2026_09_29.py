"""Vienreizējs labojums 2026-09-29 (4): atsauc _fix_quality3 725080 lielos burtus.
Avotos «Latvija pirmajā vietā» 614× pret «Latvija Pirmajā Vietā» 22×; LV normā organizācijas
nosaukumā ar lielo burtu tikai pirmais vārds. Operatora atļauja 2026-09-29. Rollback
data/rollback_quality4_2026-09-29.sql.
"""
import sys
from pathlib import Path
from src.db import get_db

CLAIMS = {
    725080: [("ar partiju «Latvija Pirmajā Vietā» (LPV)", "ar partiju «Latvija pirmajā vietā» (LPV)")],
}
NOTES = {}
BRIEF_EXTRA = []
BRIEF_ID = 660
WIKI = Path("wiki/dailies/2026-09-29.md")
ROLLBACK = Path("data/rollback_quality4_2026-09-29.sql")


def q(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def sub(text, pairs, label, expect_min=1):
    for old, new in pairs:
        n = text.count(old)
        if n < expect_min:
            sys.exit(f"STOP: {label}: nav atrasts {old[:60]!r} (trāpījumi {n})")
        text = text.replace(old, new)
    return text


def main(apply: bool):
    db = get_db(None)
    claims = {i: db.execute("SELECT stance FROM claims WHERE id=?", (i,)).fetchone()[0] for i in CLAIMS}
    notes = {i: db.execute("SELECT content FROM context_notes WHERE id=?", (i,)).fetchone()[0] for i in list(NOTES) + [BRIEF_ID]}
    assert WIKI.read_text(encoding="utf-8") == notes[BRIEF_ID], "wiki/dailies != DB — STOP"

    new_claims = {i: sub(claims[i], CLAIMS[i], f"claim {i}") for i in CLAIMS}
    new_notes = {i: sub(notes[i], NOTES[i], f"note {i}") for i in NOTES}
    brief = notes[BRIEF_ID]
    for i in CLAIMS:
        brief = sub(brief, CLAIMS[i], f"brief/claim {i}")
    for i in NOTES:
        brief = sub(brief, NOTES[i], f"brief/note {i}")
    brief = sub(brief, BRIEF_EXTRA, "brief/extra")
    for old, _ in [p for ps in list(CLAIMS.values()) + list(NOTES.values()) for p in ps] + BRIEF_EXTRA:
        assert old not in brief, f"atlikums pārskatā: {old[:50]!r}"

    if not apply:
        print("dry-run OK:", len(new_claims), "claims,", len(new_notes), "notes, brief", len(notes[BRIEF_ID]), "->", len(brief))
        return

    lines = ["-- Rollback: scripts/_fix_quality4_2026_09_29.py (apply 2026-09-29).",
             "-- Atjauno claims 725080 stance, context_notes 660 content.",
             "-- Pēc rollback: scripts/reembed_claims.py 725080; wiki/dailies/2026-09-29.md no 660.",
             "BEGIN;"]
    lines += [f"UPDATE claims SET stance = {q(claims[i])} WHERE id = {i};" for i in CLAIMS]
    lines += [f"UPDATE context_notes SET content = {q(notes[i])} WHERE id = {i};" for i in notes]
    lines.append("COMMIT;")
    ROLLBACK.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with db:
        for i, s in new_claims.items():
            db.execute("UPDATE claims SET stance=? WHERE id=?", (s, i))
        for i, s in new_notes.items():
            db.execute("UPDATE context_notes SET content=? WHERE id=?", (s, i))
        db.execute("UPDATE context_notes SET content=? WHERE id=?", (brief, BRIEF_ID))
    WIKI.write_text(brief, encoding="utf-8")
    print("applied; rollback ->", ROLLBACK)


if __name__ == "__main__":
    main("--apply" in sys.argv)
