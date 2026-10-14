from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.db import get_db
CLAIM_ID = 704266
OLD = "Raidījuma 'Nekā Personīga' atstāstā (TV3/tvnet.lv) iekšlietu ministrs Jānis Dombrava tiešā citātā atzīst, ka ministrijas datu infrastruktūra ilgstoši atstāta novārtā, un pauž cerību, ka pārejas periodā tā netiks izgaismota ļaunprātīgiem mēģinājumiem. Rakstā minētā LVRTC pārceļšanas apspriešana nav viņa tiešs citāts, tāpēc stance balstīta tikai uz paša teikto. Temats: kiberdrošība un valsts datu infrastruktūras gatavība. Dublikātu ±5 d logā nav; pretrunu nav."
NEW = "Raidījuma 'Nekā Personīga' atstāstā (TV3/tvnet.lv) iekšlietu ministrs Jānis Dombrava tiešā citātā atzīst, ka ministrijas datu infrastruktūra ilgstoši atstāta novārtā, un pauž cerību, ka pārejas periodā tā netiks izgaismota ļaunprātīgiem mēģinājumiem. Rakstā minētā LVRTC pārceļšanas apspriešana nav viņa tiešs citāts, tāpēc pozīcijas formulējums balstīts tikai uz paša teikto. Tēma — kiberdrošība un valsts datu infrastruktūras gatavība. Iepriekšējo piecu dienu pozīcijās dublikāta nav; pretrunu nav."
db = get_db()
row = db.execute("SELECT reasoning FROM claims WHERE id=?", (CLAIM_ID,)).fetchone()
if row is None or row["reasoning"] != OLD:
    raise SystemExit("pre-image mismatch")
cur = db.execute("UPDATE claims SET reasoning=? WHERE id=? AND reasoning=?", (NEW, CLAIM_ID, OLD))
db.commit()
if cur.rowcount != 1:
    raise SystemExit(f"updated {cur.rowcount}, expected 1")
print("updated", CLAIM_ID)
db.close()
