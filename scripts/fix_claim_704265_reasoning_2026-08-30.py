from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.db import get_db
CLAIM_ID = 704265
OLD = "Paša tvīts 2026-08-30: brīdina politiķus priekšvēlēšanu laikā pirms publiskas VDD piesaukšanas apzināties dienesta pamatuzdevumu. Pirmās personas pozīcija par drošības dienesta lomu publiskajā telpā. Saglabāti ierobežojumi: 'priekšvēlēšanu laikā', 'pirms publiski piesaukt', 'pamatuzdevums', 'sevišķi smagus noziegumus'. Salīdzinājumā ar ±5 d claims nav dublikāta; 2026-08-20 pozitīvais VDD darba vērtējums nav pretrunā — tur vērtēts dienesta darbs, te aicinājums politiķiem."
NEW = "Paša tvīts 2026-08-30: brīdina politiķus priekšvēlēšanu laikā pirms publiskas VDD piesaukšanas apzināties dienesta pamatuzdevumu. Pirmās personas pozīcija par drošības dienesta lomu publiskajā telpā. Saglabāti ierobežojumi: 'priekšvēlēšanu laikā', 'pirms publiski piesaukt', 'pamatuzdevums', 'sevišķi smagus noziegumus'. Salīdzinājumā ar iepriekšējo piecu dienu pozīcijām dublikāta nav; 2026-08-20 pozitīvais VDD darba vērtējums nav pretrunā — tur vērtēts dienesta darbs, te aicinājums politiķiem."
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
