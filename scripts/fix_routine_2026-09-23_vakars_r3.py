"""@quality-reviewer 3. kārta (2026-09-23 vakars) — labojumi pirms publicēšanas.

1. Pozīcija #718020 (Braže) stance: tas pats saplūdinājums, kas labots spriedzē
   #370 — premjera uzskats jāatzīmē kā viņas atstāsts. Pēc tam reembed
   (scripts/reembed_claims.py 718020).
2. Spriedze #370: 41 vārda teikums sadalīts divos (joprojām viena rinda).
3. Pārskats #639 § Koalīcija vs Opozīcija: Patmalnieka apsūdzībai tēma.

Rollback: data/rollback_routine_2026-09-23_vakars_r3.sql (+ reembed 718020).
"""
from src.db import get_db

S_OLD = ("Iebilst premjera TV3 paustajam pārmetumam Ārlietu ministrijai, ka Latvijai vajadzēja ātrāk, kā pārējām "
         "Baltijas valstīm, piekrist divu oligarhu izņemšanai no ES sankciju saraksta; Latvijas rīcību raksturo kā "
         "savu drošības interešu aizstāvēšanu ES līdz galam, ieskaitot iespēju uzlikt veto, un premjera nostāju sauc "
         "par sev nepatīkamu jaunumu.")
S_NEW = ("Iebilst premjera TV3 paustajiem pārmetumiem Ārlietu ministrijai; pēc viņas atstāsta, premjers uzskata, ka "
         "Latvijai tāpat kā pārējām Baltijas valstīm vajadzēja ātrāk piekrist divu oligarhu izņemšanai no ES sankciju "
         "saraksta. Latvijas rīcību raksturo kā drošības interešu aizstāvēšanu ES līdz galam, ieskaitot iespēju uzlikt "
         "veto, un premjera nostāju sauc par sev nepatīkamu jaunumu.")
T_OLD = ("Braže X ierakstā iebilst premjera Kulberga TV3 paustajiem pārmetumiem Ārlietu ministrijai; pēc viņas "
         "atstāsta, premjers uzskata, ka Latvijai tāpat kā pārējām Baltijas valstīm vajadzēja ātrāk piekrist divu "
         "oligarhu izņemšanai no ES sankciju saraksta, un to viņa sauc par sev nepatīkamu jaunumu.")
T_NEW = ("Braže X ierakstā iebilst premjera Kulberga TV3 paustajiem pārmetumiem Ārlietu ministrijai. Pēc viņas "
         "atstāsta, premjers uzskata, ka Latvijai tāpat kā pārējām Baltijas valstīm vajadzēja ātrāk piekrist divu "
         "oligarhu izņemšanai no sankciju saraksta; tas viņai ir nepatīkams jaunums.")
P_OLD = ("Valainis (ZZS) nacionālās sankcijas sauc par politisku žestu, bet Patmalnieks (JV) apsūdz Kulbergu "
         "maldināšanā.")
P_NEW = ("Valainis (ZZS) nacionālās sankcijas sauc par politisku žestu. Patmalnieks (JV) atsevišķi apsūdz Kulbergu "
         "maldināšanā viendzimuma laulību jautājumā.")

db = get_db()
with db:
    s = db.execute("SELECT stance FROM claims WHERE id=718020").fetchone()[0]
    assert s == S_OLD, s
    db.execute("UPDATE claims SET stance=? WHERE id=718020", (S_NEW,))
    d = db.execute("SELECT description FROM political_tensions WHERE id=370").fetchone()[0]
    assert d == T_OLD, d
    db.execute("UPDATE political_tensions SET description=? WHERE id=370", (T_NEW,))
    b = db.execute("SELECT content FROM context_notes WHERE id=639").fetchone()[0]
    for o, n in ((S_OLD, S_NEW), (T_OLD, T_NEW), (P_OLD, P_NEW)):
        assert b.count(o) == 1, (o[:40], b.count(o))
        b = b.replace(o, n)
    db.execute("UPDATE context_notes SET content=? WHERE id=639", (b,))
print("ok")
