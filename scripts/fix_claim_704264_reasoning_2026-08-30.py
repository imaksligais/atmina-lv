from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.db import get_db

CLAIM_ID = 704264
OLD = "Kulberga paša 2023. gada ieraksts skaidri piesaka viņa un Apvienotā saraksta iniciatīvu un norāda uz gatavotiem tiesību aktu grozījumiem. Stated_at saglabā avota vēsturisko datumu, ne šodienas atkārtotās ievākšanas dienu."
NEW = "Kulberga paša 2023. gada ieraksts skaidri piesaka viņa un Apvienotā saraksta iniciatīvu un norāda uz gatavotiem tiesību aktu grozījumiem. Pozīcijas datums saglabā avota vēsturisko datumu, ne šodienas atkārtotās ievākšanas dienu."

db = get_db()
row = db.execute("SELECT reasoning FROM claims WHERE id=?", (CLAIM_ID,)).fetchone()
if row is None or row["reasoning"] != OLD:
    raise SystemExit("pre-image mismatch; refusing update")
cur = db.execute("UPDATE claims SET reasoning=? WHERE id=? AND reasoning=?", (NEW, CLAIM_ID, OLD))
db.commit()
if cur.rowcount != 1:
    raise SystemExit(f"updated {cur.rowcount}, expected 1")
print("updated", CLAIM_ID)
db.close()
