# -*- coding: utf-8 -*-
"""@quality-reviewer 2026-08-12 FAIL labojumi (rollback: data/rollback_qr_daily_2026-08-12.sql).

1. Dzēš krossavota dublikātus 689553 / 689555 (tā pati 2026-08-11 valdības sēde,
   jau glabāta kā 689475 / 689507 no leta.lv; diena.lv atkārtojums ielaists, jo
   idempotences atslēgā ir source_url).
2. Atrisina viltus pozitīvo NEEDS_REVIEW uz 689540 — automātiskais vārts noķēra
   frāzi «tikai pieminēts», kas apraksta CITU dokumentu; pats claim ir pirmās
   personas tvīts ar verbatim citātu (QR pārbaudīts). Marķieri aizstāj ar
   Izvērtēts-formu; kolonnu uztur trigeris.
3. Spriedze 209: target_url noņemts (NRA raksts neapliecina Velpa rosinājumu),
   apraksts pārformulēts kā vienpusējs.
4. Spriedze 210: apraksts sašaurināts līdz tam, ko apliecina source_url tvīts.
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"E:\atmina")
from src.db import get_db

db = get_db()

import sqlite_vec
db.enable_load_extension(True)
sqlite_vec.load(db)
db.enable_load_extension(False)

# 1) dublikāti
for cid in (689553, 689555):
    n = db.execute("SELECT COUNT(*) c FROM contradictions WHERE claim_old_id=? OR claim_new_id=?", (cid, cid)).fetchone()["c"]
    assert n == 0, f"claim {cid} ir pretrunu atsauces — STOP"
    db.execute("DELETE FROM claim_vectors WHERE claim_id=?", (cid,))
    db.execute("DELETE FROM claims WHERE id=?", (cid,))
    print(f"dzēsts claim {cid}")

# 2) 689540 marķiera atrisināšana (rakstām tekstu, kolonnu klasificē trigeris)
# NB: tekstā nedrīkst parādīties burtiskais marķiera vārds — trigeris klasificē
# pēc apakšvirknes, un pirmā šī skripta versija ar to atkārtoti karogoja rindu.
new_reasoning = (
    "Izvērtēts 2026-08-12: automātiskā vārta marķieris bija viltus pozitīvs — "
    "frāze «tikai pieminēts» pamatojumā aprakstīja CITU dokumentu (85859), ne šo claim; "
    "claim avots ir Sprūda paša pirmās personas tvīts ar verbatim citātu. "
    "Sākotnējais pamatojums: Pirmās personas tvīts 12.08., kurā Sprūds tieši atspēko premjera "
    "Kulberga publiski pausto (NRA doc 85859). Izteikuma kodols ir pārtvērējdronu iepirkums un "
    "integrācija, tāpēc tēma ir Droni, nevis Aizsardzība un drošība. Doc 85859 ir Kulberga "
    "intervija, kurā runā Kulbergs, ne Sprūds — tas atzīmēts kā tukšs."
)
db.execute("UPDATE claims SET reasoning=? WHERE id=?", (new_reasoning, 689540))
print("689540 reasoning atjaunināts")

# 3) spriedze 209
db.execute(
    "UPDATE political_tensions SET target_url=NULL, description=? WHERE id=209",
    ("Velps rosina jautājumu, vai VDD un Ģenerālprokuratūrai nebūtu jāvērtē Progresīvo rīcība "
     "Aizsardzības ministrijā pēc Krimināllikuma (avota jautājuma forma saglabāta; Sprūds ir "
     "attiecīgā perioda aizsardzības ministrs; vienpusējs izteikums — Sprūda atbilde uz šo "
     "rosinājumu nav fiksēta).",),
)
print("spriedze 209 sašaurināta")

# 4) spriedze 210
db.execute(
    "UPDATE political_tensions SET description=? WHERE id=210",
    ("Valainis (ZZS) publiski vērtē Kulberga valdību kā stabilu, bet tehnisku un sagaida no tās "
     "daudz aktīvāku rīcību lielajos jautājumos — koalīcijas iekšēja spriedze par darba tempu.",),
)
print("spriedze 210 sašaurināta")

db.commit()

# verifikācija
assert db.execute("SELECT COUNT(*) c FROM claims WHERE id IN (689553,689555)").fetchone()["c"] == 0
rs = db.execute("SELECT review_status FROM claims WHERE id=689540").fetchone()["review_status"]
print("689540 review_status:", rs)
t209 = db.execute("SELECT target_url FROM political_tensions WHERE id=209").fetchone()["target_url"]
print("209 target_url:", t209)
print("OK")
