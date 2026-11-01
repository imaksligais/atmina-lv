"""#724971 Kulbergs «Vilkatis»: «Re:Check» verdikts stance tekstā (operatora lēmums 2026-09-27).

Precedenti: 09-16 Jurēvics (Re:Check aprēķins iekavās), 08-11 Stankevics. Maina claims.stance,
pārskatu #652 un wiki/dailies/2026-09-27.md. Pēc --apply OBLIGĀTI
`scripts/reembed_claims.py 724971`.
Rollback: data/rollback_vilkatis_724971_2026-09-27.sql
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.db import get_db  # noqa: E402

ROLLBACK = Path("data/rollback_vilkatis_724971_2026-09-27.sql")
WIKI = Path("wiki/dailies/2026-09-27.md")
OLD_END = "Aizsardzības ministrija sadarbojas ar Iekšlietu ministriju."
NEW_END = ("Aizsardzības ministrija sadarbojas ar Iekšlietu ministriju («Re:Check» to vērtē kā nepatiesu: "
           "Nacionālie bruņotie spēki robežsardzei palīdz kopš 2021. gada).")
NOTE = (" Operatora lēmums 2026-09-27: «Re:Check» verdikts pievienots stance tekstā iekavās "
        "(precedenti — 09-16 Jurēvics, 08-11 Stankevics).")


def q(s):
    return "'" + s.replace("'", "''") + "'"


def main():
    db = get_db()
    c = db.execute("SELECT stance, reasoning FROM claims WHERE id = 724971").fetchone()
    assert c["stance"].endswith(OLD_END), c["stance"]
    stance2 = c["stance"][: -len(OLD_END)] + NEW_END
    brief = db.execute("SELECT content FROM context_notes WHERE id = 652").fetchone()[0]
    wiki = WIKI.read_bytes().decode("utf-8")
    for t in (brief, wiki):
        assert t.count(c["stance"]) == 1
    if "--apply" not in sys.argv:
        print("sausā palaide OK")
        return
    ROLLBACK.write_text("\n".join([
        "-- ROLLBACK: #724971 «Re:Check» verdikts stance tekstā (2026-09-27)",
        "-- Atceļ: scripts/fix_vilkatis_724971_2026-09-27.py --apply. Pēc tam: scripts/reembed_claims.py 724971",
        "-- wiki/dailies/2026-09-27.md (gitignored) pārraksta no context_notes #652.",
        "BEGIN;",
        f"UPDATE claims SET stance = {q(c['stance'])}, reasoning = {q(c['reasoning'])} WHERE id = 724971;",
        f"UPDATE context_notes SET content = {q(brief)} WHERE id = 652;",
        "COMMIT;", ""]), encoding="utf-8")
    with db:
        db.execute("UPDATE claims SET stance = ?, reasoning = ? WHERE id = 724971", (stance2, c["reasoning"] + NOTE))
        db.execute("UPDATE context_notes SET content = ? WHERE id = 652", (brief.replace(c["stance"], stance2),))
    WIKI.write_bytes(wiki.replace(c["stance"], stance2).encode("utf-8"))
    print("applied; rollback:", ROLLBACK)


if __name__ == "__main__":
    main()
