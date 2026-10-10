"""Labo claim #704226 stated_at uz LV kalendāro dienu (2026-08-28).

Claim izveidots no tvīta (doc 96612), kas publicēts 2026-08-28T08:58:56+00:00
(UTC) = 2026-08-28 plkst. 11:58 pēc Latvijas laika. `stated_at` tika
aizpildīts automātiski no `documents.scraped_at` (2026-08-29 07:45), jo
ekstrakcijas skripts to nebija nodevis eksplicīti — rezultātā claim būtu
iekritis 08-29 dienas pārskatā, nevis 08-28 pārskatā, kuram tas pieder.

Konvencija (2026-08-25): stated_at = notikuma LATVIJAS kalendārā diena;
tvīta UTC publicēšanas laiks jāpārvērš pirms glabāšanas.

`store_claim()` ir first-write-wins uz (opponent_id, source_url, topic), tāpēc
atkārtota save_analysis ar stated_at datumu NEPĀRRAKSTA rindu — datuma
atsvaidzināšanai nepieciešams eksplicīts UPDATE (store_claim docstring:
"callers that need to refresh fields should UPDATE explicitly").

Rollback: data/rollback_claim_704226_stated_at_2026-08-29.sql
"""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

CLAIM_ID = 704226
OLD_STATED_AT = "2026-08-29 07:45:00"
NEW_STATED_AT = "2026-08-28 00:00:00"

conn = sqlite3.connect(r"E:\atmina\data\atmina.db")
conn.row_factory = sqlite3.Row

before = conn.execute(
    "SELECT id, stated_at, source_url, topic FROM claims WHERE id=?", (CLAIM_ID,)
).fetchone()
assert before is not None, f"claim {CLAIM_ID} not found"
print("BEFORE:", dict(before))
assert before["stated_at"] == OLD_STATED_AT, (
    f"stated_at mismatch: {before['stated_at']!r} != {OLD_STATED_AT!r} — aborting"
)

conn.execute(
    "UPDATE claims SET stated_at=? WHERE id=?", (NEW_STATED_AT, CLAIM_ID)
)
conn.commit()

after = conn.execute(
    "SELECT id, stated_at FROM claims WHERE id=?", (CLAIM_ID,)
).fetchone()
print("AFTER:", dict(after))
assert after["stated_at"] == NEW_STATED_AT
conn.close()
print("OK: stated_at corrected")
