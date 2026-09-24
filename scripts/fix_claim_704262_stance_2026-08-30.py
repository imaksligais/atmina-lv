from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.db import get_db

CLAIM_ID = 704262
OLD = "Prasa mainīt veselības aprūpes finansējuma piešķiršanas kārtību — no manipulāciju kvantitātes uz kvalitāti, ieviešot vienoto rindu un nosakot medicīniski pamatotus gaidīšanas termiņus."
NEW = "Atbalsta veselības aprūpes finansējuma piešķiršanas kārtības maiņu — no manipulāciju kvantitātes uz kvalitāti, ieviešot vienoto rindu un nosakot medicīniski pamatotus gaidīšanas termiņus."

db = get_db()
row = db.execute("SELECT stance FROM claims WHERE id=?", (CLAIM_ID,)).fetchone()
if row is None or row["stance"] != OLD:
    raise SystemExit("pre-image mismatch; refusing update")
cur = db.execute("UPDATE claims SET stance=? WHERE id=? AND stance=?", (NEW, CLAIM_ID, OLD))
db.commit()
if cur.rowcount != 1:
    raise SystemExit(f"updated {cur.rowcount}, expected 1")
print(db.execute("SELECT id, stance, review_status FROM claims WHERE id=?", (CLAIM_ID,)).fetchone())
db.close()
