"""D2: noņem 9 junction rindas, ko ingest/matcher atjaunoja pēc 10-05b un doc90310 labojumiem.

Pirms tam uzstāda apspiešanas shēmu (tā pati, ko nākamais init_db), lai trigeris
dzēsumus ieraksta un tie vairs neatgriežas. Rollback:
data/rollback_d2_revived_links_2026-10-14.sql, data/rollback_dp_suppressions_schema_2026-10-14.sql.
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.db import PRODUCTION_DB_PATH  # noqa: E402
from src.db_migrations import _apply_dp_suppressions  # noqa: E402

ROWS = [(124191, 6, "subject"), (124191, 69, "mentioned"), (124191, 18, "mentioned"),
        (124191, 24, "mentioned"), (124191, 72, "mentioned"), (124191, 183, "mentioned"),
        (124194, 3, "mentioned"), (124194, 69, "mentioned"), (90310, 225, "subject")]

db = sqlite3.connect(PRODUCTION_DB_PATH)
db.execute("PRAGMA foreign_keys = ON")
_apply_dp_suppressions(db)
deleted = sum(db.execute("DELETE FROM document_politicians WHERE document_id=? AND politician_id=? AND role=?", r).rowcount for r in ROWS)
reason = "fix_d2_revived_links_2026-10-14"
for d, p, r in ROWS:
    db.execute("UPDATE document_politician_suppressions SET reason=? WHERE document_id=? AND politician_id=? AND role=?", (reason, d, p, r))
active = db.execute(
    "SELECT COUNT(*) FROM document_politician_suppressions WHERE reason=? AND lifted_at IS NULL", (reason,)).fetchone()[0]
print(f"deleted {deleted}/{len(ROWS)}, suppressions active {active}/{len(ROWS)}")
if deleted != len(ROWS) or active != len(ROWS):
    db.rollback()
    sys.exit("MISMATCH — rolled back, nothing written")
db.commit()
