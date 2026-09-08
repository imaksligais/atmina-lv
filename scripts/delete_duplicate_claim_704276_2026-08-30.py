from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import sqlite_vec

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
DB_PATH = ROOT / "data" / "atmina.db"

claim_id = 704276
db = sqlite3.connect(DB_PATH)
db.enable_load_extension(True)
sqlite_vec.load(db)
row = db.execute("SELECT id FROM claims WHERE id = ?", (claim_id,)).fetchone()
if row is None:
    raise SystemExit("claim 704276 is already absent")
db.execute("DELETE FROM claim_vectors WHERE claim_id = ?", (claim_id,))
db.execute("DELETE FROM claims WHERE id = ?", (claim_id,))
db.commit()
remaining = db.execute("SELECT COUNT(*) FROM claims WHERE id = ?", (claim_id,)).fetchone()[0]
db.close()
if remaining:
    raise SystemExit("delete verification failed")
print("deleted=704276")
