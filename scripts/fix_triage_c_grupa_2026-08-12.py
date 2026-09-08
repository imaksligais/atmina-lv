# -*- coding: utf-8 -*-
"""Operatora lēmums 2026-08-12 nakts: slēgt 3 C grupas marķierus "atstāt kā ir"
(rollback: data/rollback_triage_c_grupa_2026-08-12.sql).

689518 Madžiņš — skepse par NEPLP depolitizāciju pašpietiekama arī bez atbildes
ķēdes; 689542 Baško — stance jau šaurāks par avota hiperbolu; 689558 Melnis —
konkrēta apņemšanās, ne protokola frāze. 689554 Kulbergs PALIEK atvērts
(gaida labāku avotu par TUA modeli).
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"E:\atmina")
from src.db import get_db

DECISIONS = {
    689518: "operatora lēmums — paliek kā ir: skepse par NEPLP depolitizāciju partiju kvotu dēļ ir pašpietiekams izteikums arī bez atbildes ķēdes konteksta; zemā ticamība to jau atspoguļo; ",
    689542: "operatora lēmums — paliek kā ir: stance jau formulēts šaurāk par avota hiperbolu, platuma kļūdas nav; ",
    689558: "operatora lēmums — paliek kā ir: apņemšanās ir konkrēta (industrijas sadarbība, modernizācija) un ļaus vēlāk salīdzināt solīto ar darīto; ",
}

db = get_db()
for cid, decision in DECISIONS.items():
    r = db.execute("SELECT reasoning FROM claims WHERE id=?", (cid,)).fetchone()["reasoning"]
    assert r.startswith("NEEDS_REVIEW:"), f"{cid}: marķieris nav prefiksā"
    new = r.replace("NEEDS_REVIEW:", f"Izvērtēts 2026-08-12: {decision}sākotnējais pamatojums —", 1)
    db.execute("UPDATE claims SET reasoning=? WHERE id=?", (new, cid))
db.commit()

left = db.execute("SELECT id FROM claims WHERE review_status='needs_review' ORDER BY id").fetchall()
print("atvērti paliek:", [r["id"] for r in left])
assert [r["id"] for r in left] == [689554]
print("OK")
