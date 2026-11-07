from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.db import get_db
CLAIM_ID = 704266
OLD = "Iekšlietu ministrijas saimniecībā [esošā infrastruktūra] ilgstoši atstāta novārtā. Kamēr notiek pārejas periods, es ceru, ka mēs neizgaismosim šo infrastruktūru tiem, kas var mēģināt tur kaut ko sliktu sadarīt."
NEW = "Iekšlietu ministrijas saimniecībā [esošā infrastruktūra] ilgstoši atstāta novārtā. Kamēr notiek pārejas periods, es ceru, ka mēs neizgaismosim šo infrastruktūru tiem, kas var mēģināt tur kaut ko sliktu sadarīt,"
db = get_db()
row = db.execute("SELECT quote FROM claims WHERE id=?", (CLAIM_ID,)).fetchone()
if row is None or row["quote"] != OLD:
    raise SystemExit("pre-image mismatch")
cur = db.execute("UPDATE claims SET quote=? WHERE id=? AND quote=?", (NEW, CLAIM_ID, OLD))
db.commit()
if cur.rowcount != 1:
    raise SystemExit(f"updated {cur.rowcount}, expected 1")
print("updated", CLAIM_ID)
db.close()
