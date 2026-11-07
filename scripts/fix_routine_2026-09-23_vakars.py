"""Vakara rutīnas 2026-09-23 labojumi pirms publicēšanas (nekas vēl nav deployots).

1. Tendence #637: «opozīcija vērtē arī nacionālo sankciju jēgu» — faktu kļūda
   (Valainis/ZZS un Dombrava/NA ir koalīcijā). Tā pati rutīnas diena, nav
   publicēta → labojums uz vietas (CLAUDE.md inv. 8, otrais izņēmums).
   Tas pats teikums nonāca dienas pārskatā #639 verbatim.
2. Spriedze #378: source/target apgriezti (uzbrukuma autore ir Braže, mērķis
   Kulbergs). Pārskata #639 spriedžu tabulas rinda tiek salabota līdzi.

Rollback: data/rollback_routine_2026-09-23_vakars.sql
"""
from src.db import get_db

OLD = "opozīcija vērtē arī nacionālo sankciju jēgu"
NEW = "arī koalīcijas partneri vērtē nacionālo sankciju iedarbību"
ROW_OLD = "| uzbrukums | Andris Kulbergs (Apvienotais saraksts) | Baiba Braže (Jaunā Vienotība) |"
ROW_NEW = "| uzbrukums | Baiba Braže (Jaunā Vienotība) | Andris Kulbergs (Apvienotais saraksts) |"

db = get_db()
with db:
    for nid, pairs in ((637, [(OLD, NEW)]), (639, [(OLD, NEW), (ROW_OLD, ROW_NEW)])):
        c = db.execute("SELECT content FROM context_notes WHERE id=?", (nid,)).fetchone()[0]
        for o, n in pairs:
            assert c.count(o) == 1, (nid, o, c.count(o))
            c = c.replace(o, n)
        db.execute("UPDATE context_notes SET content=? WHERE id=?", (c, nid))
    r = db.execute("SELECT source_pid, target_pid FROM political_tensions WHERE id=378").fetchone()
    assert tuple(r) == (10, 15), tuple(r)
    db.execute("UPDATE political_tensions SET source_pid=15, target_pid=10 WHERE id=378")
print("ok")
