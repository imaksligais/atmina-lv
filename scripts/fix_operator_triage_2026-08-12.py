# -*- coding: utf-8 -*-
"""Operatora triāžas lēmumi 2026-08-12 vakarā (rollback: data/rollback_operator_triage_2026-08-12.sql).

1. Dzēš pretrunu #25 — karājošā atsauce uz dzēstu claim 14391 (vienīgā lauztā
   atsauce tabulā; nepublicēta, confirmed=0).
2. #689552 quote pēdējā rakstzīme '.' -> ',' — verbatim pret avotu (dok. 85810:
   «...ko nevaram," uzsvēra Kulbergs»). Tēma/stance nemainās, pārembedings nav vajadzīgs.
3. Slēdz 6 marķierus ar Izvērtēts 2026-08-12 (teksts bez burtiskā marķiera vārda;
   kolonnu klasificē trigeris):
   - A grupa (tēmu robežas, tēma paliek): 689534, 689543
   - B grupa (smagi apgalvojumi; operatora lēmums — atstāt caurspīdīguma dēļ,
     «lai cilvēku vārdus atceras»; 689559 paliek profilā, tikai ne dienas
     pārskatā): 689517, 689527, 689557, 689559
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"E:\atmina")
from src.db import get_db

db = get_db()

# 1) pretruna #25
row = db.execute("SELECT id FROM contradictions WHERE id=25 AND confirmed=0").fetchone()
assert row, "pretruna #25 nav atrasta vai ir confirmed — STOP"
db.execute("DELETE FROM contradictions WHERE id=25")
print("pretruna #25 dzēsta")

# 2) 689552 quote
q = db.execute("SELECT quote FROM claims WHERE id=689552").fetchone()["quote"]
assert q.endswith("ko nevaram."), f"negaidīts citāta nobeigums: {q[-30:]!r}"
db.execute("UPDATE claims SET quote=? WHERE id=689552", (q[:-1] + ",",))
print("689552 quote: '.' -> ','")

# 3) marķieru slēgšana — prefiksa aizstāšana + lēmuma pieraksts
DECISIONS = {
    689534: "tēmas robeža Tieslietas/Vide izlemta — paliek Tieslietas pēc instrumenta un Topic Boundary Rule; ",
    689543: "tēmas robeža Veselības aprūpe/Tieslietas izlemta — paliek Veselības aprūpe (medicīniska prakse); ",
    689517: "operatora lēmums — pozīcija paliek: žurnālista slota pejoratīvs vērtējums par iestādi, korekti atribuēts; ",
    689527: "operatora lēmums — pozīcija paliek: jautājuma forma saglabāta, korekti atribuēts; ",
    689557: "operatora lēmums — pozīcija paliek: kampaņas rīcības kritika ar pārbaudāmu faktu pamatu; ",
    689559: "operatora lēmums — pozīcija paliek profilā caurspīdīguma dēļ (izteikuma fakts ir publiski fiksējams), bet dienas pārskatā netiek rādīta; ",
}
for cid, decision in DECISIONS.items():
    r = db.execute("SELECT reasoning FROM claims WHERE id=?", (cid,)).fetchone()["reasoning"]
    assert "NEEDS_REVIEW:" in r, f"{cid}: marķieris nav atrasts"
    new = r.replace("NEEDS_REVIEW:", f"Izvērtēts 2026-08-12: {decision}sākotnējais pamatojums —", 1)
    db.execute("UPDATE claims SET reasoning=? WHERE id=?", (new, cid))

db.commit()

# verifikācija
left = db.execute(
    "SELECT COUNT(*) c FROM claims WHERE review_status='needs_review' AND id IN (689534,689543,689517,689527,689557,689559)"
).fetchone()["c"]
total = db.execute("SELECT COUNT(*) c FROM claims WHERE review_status='needs_review'").fetchone()["c"]
dangling = db.execute("SELECT COUNT(*) c FROM contradictions WHERE id=25").fetchone()["c"]
print(f"slēgtie ar atlikušu karogu: {left} (jābūt 0); kopā atvērtas: {total}; pretruna #25 paliek: {dangling}")
assert left == 0 and dangling == 0
print("OK")
