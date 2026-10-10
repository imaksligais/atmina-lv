"""Vakara atlikumi 2026-09-27 — izdarīti, nevis atstāti handoffā.

1. quality-reviewer neobligātie § H labojumi: piezīme #649 + pārskats #652 + wiki/dailies
   («neatrisinātu» → «neuzlabotu», «liek» → «uzliek», L9 atkārtojums).
2. Bartaševičs (pid=181) `role`: «Bijušais Rēzeknes mērs» → pašreizējais amats + saraksts.
   `party` = «Kopā Latvijai» paliek — viņš ir tās priekšsēdētājs; partija kandidē kopā ar LPV
   (LSM 06.06.2026), saraksts ≠ biedrība (T6).

Lietojums: .venv/Scripts/python.exe scripts/fix_evening_2026-09-27.py [--apply]
Rollback: data/rollback_evening_2026-09-27.sql
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.db import get_db  # noqa: E402

ROLLBACK = Path("data/rollback_evening_2026-09-27.sql")
WIKI = Path("wiki/dailies/2026-09-27.md")

NOTE_FIX = ("Saeimas darba kvalitāti tas neatrisinātu", "Saeimas darba kvalitāti tas neuzlabotu")
BRIEF_FIXES = [
    NOTE_FIX,
    ("atbildību par riskantiem ārvalstu investoriem liek dienestiem",
     "atbildību par riskantiem ārvalstu investoriem uzliek dienestiem"),
    ("sešu frakciju pārstāvji deputātu skaita samazināšanu no 100 uz 70 neizvirza",
     "sešu frakciju pārstāvji samazinājumu no 100 uz 70 deputātiem neizvirza"),
]
ROLE_OLD = "Bijušais Rēzeknes mērs"
ROLE_NEW = "Rēzeknes domes deputāts, bijušais mērs; LPV saraksta līderis (Latgale)"


def q(s):
    return "'" + s.replace("'", "''") + "'"


def fix(t):
    for old, new in BRIEF_FIXES:
        assert t.count(old) == 1, old
        t = t.replace(old, new)
    return t


def main():
    db = get_db()
    note = db.execute("SELECT content FROM context_notes WHERE id = 649").fetchone()[0]
    assert note.count(NOTE_FIX[0]) == 1
    brief = db.execute("SELECT content FROM context_notes WHERE id = 652").fetchone()[0]
    brief2, wiki2 = fix(brief), fix(WIKI.read_bytes().decode("utf-8"))
    assert brief2 == wiki2
    role = db.execute("SELECT role FROM tracked_politicians WHERE id = 181").fetchone()[0]
    assert role == ROLE_OLD, role
    if "--apply" not in sys.argv:
        print("sausā palaide OK")
        return
    ROLLBACK.write_text("\n".join([
        "-- ROLLBACK: vakara atlikumi 2026-09-27 (piezīme #649, pārskats #652, pid=181 role)",
        "-- Atceļ: scripts/fix_evening_2026-09-27.py --apply. Piemērots: 2026-09-27.",
        "-- wiki/dailies/2026-09-27.md (gitignored) pārraksta no context_notes #652.",
        "BEGIN;",
        f"UPDATE context_notes SET content = {q(note)} WHERE id = 649;",
        f"UPDATE context_notes SET content = {q(brief)} WHERE id = 652;",
        f"UPDATE tracked_politicians SET role = {q(role)} WHERE id = 181;",
        "COMMIT;", ""]), encoding="utf-8")
    with db:
        db.execute("UPDATE context_notes SET content = ? WHERE id = 649", (note.replace(*NOTE_FIX),))
        db.execute("UPDATE context_notes SET content = ? WHERE id = 652", (brief2,))
        db.execute("UPDATE tracked_politicians SET role = ? WHERE id = 181", (ROLE_NEW,))
    WIKI.write_bytes(wiki2.encode("utf-8"))
    print("applied; rollback:", ROLLBACK)


if __name__ == "__main__":
    main()
