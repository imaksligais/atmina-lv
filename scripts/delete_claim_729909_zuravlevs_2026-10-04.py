"""Dzēš claims #729909 (Žuravļevs) — operatora lēmums 2026-10-04.

Rollback: data/rollback_delete_claim_729909_zuravlevs_2026-10-04.sql
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import sqlite_vec

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
DB_PATH = ROOT / "data" / "atmina.db"

claim_id = 729909
db = sqlite3.connect(DB_PATH)
db.enable_load_extension(True)
sqlite_vec.load(db)
row = db.execute("SELECT opponent_id, document_id FROM claims WHERE id = ?", (claim_id,)).fetchone()
if row is None:
    raise SystemExit("claim 729909 is already absent")
if row != (187, 124339):
    raise SystemExit(f"unexpected row {row}")
db.execute("DELETE FROM claim_vectors WHERE claim_id = ?", (claim_id,))
db.execute("DELETE FROM claims WHERE id = ?", (claim_id,))
db.commit()
remaining = db.execute("SELECT COUNT(*) FROM claims WHERE id = ?", (claim_id,)).fetchone()[0]
db.close()
if remaining:
    raise SystemExit("delete verification failed")
print("deleted=729909")
