from __future__ import annotations

import json
import sys
from pathlib import Path

import sqlite_vec

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.db import get_db

CLAIM_ID = 704262
ROLLBACK = ROOT / "data" / "rollback_delete_bare_rt_claim_704262_and_briefs_2026-08-31.sql"


def sql_quote(db, value):
    return db.execute("SELECT quote(?)", (value,)).fetchone()[0]


with get_db() as db:
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    claim = db.execute("SELECT * FROM claims WHERE id=?", (CLAIM_ID,)).fetchone()
    if claim is None:
        raise SystemExit("claim 704262 missing before mutation")
    notes = db.execute("SELECT * FROM context_notes WHERE id IN (516,517) ORDER BY id").fetchall()
    if len(notes) != 2:
        raise SystemExit(f"expected 2 brief rows, got {len(notes)}")

    claim_cols = [r[1] for r in db.execute("PRAGMA table_info(claims)").fetchall() if r[1] != "review_status"]
    claim_vals = [sql_quote(db, claim[col]) for col in claim_cols]
    lines = [
        "-- Reverses deletion of bare-RT claim 704262 and restores pre-refresh briefs 516/517.",
        "-- Forward change applied 2026-08-31.",
        "-- After applying this SQL, run: .venv/Scripts/python.exe scripts/reembed_claims.py 704262",
        "BEGIN;",
        f"INSERT INTO claims ({', '.join(claim_cols)}) VALUES ({', '.join(claim_vals)});",
    ]
    for note in notes:
        lines.append(
            "UPDATE context_notes SET "
            f"content={sql_quote(db, note['content'])}, "
            f"visual_brief_json={sql_quote(db, note['visual_brief_json'])} "
            f"WHERE id={note['id']};"
        )
    lines.append("COMMIT;")
    ROLLBACK.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if not ROLLBACK.exists() or ROLLBACK.stat().st_size < 1000:
        raise SystemExit("rollback not safely written")

    before = db.execute("SELECT COUNT(*) FROM claim_vectors WHERE claim_id=?", (CLAIM_ID,)).fetchone()[0]
    db.execute("DELETE FROM claim_vectors WHERE claim_id=?", (CLAIM_ID,))
    db.execute("DELETE FROM claims WHERE id=?", (CLAIM_ID,))
    db.commit()
    after_claim = db.execute("SELECT COUNT(*) FROM claims WHERE id=?", (CLAIM_ID,)).fetchone()[0]
    after_vector = db.execute("SELECT COUNT(*) FROM claim_vectors WHERE claim_id=?", (CLAIM_ID,)).fetchone()[0]

result = {
    "rollback": str(ROLLBACK),
    "rollback_bytes": ROLLBACK.stat().st_size,
    "vector_rows_before": before,
    "claim_rows_after": after_claim,
    "vector_rows_after": after_vector,
}
print(json.dumps(result, ensure_ascii=False, indent=2))
raise SystemExit(0 if after_claim == 0 and after_vector == 0 else 1)
