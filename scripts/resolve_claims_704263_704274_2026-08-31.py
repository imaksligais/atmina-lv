from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.db import get_db

IDS = (704263, 704274)
ROLLBACK = ROOT / "data" / "rollback_resolve_claims_704263_704274_2026-08-31.sql"


def q(db, value):
    return db.execute("SELECT quote(?)", (value,)).fetchone()[0]


with get_db() as db:
    rows = db.execute(
        "SELECT id, reasoning, review_status FROM claims WHERE id IN (?,?) ORDER BY id",
        IDS,
    ).fetchall()
    if len(rows) != 2 or any(r["review_status"] != "needs_review" for r in rows):
        raise SystemExit(f"unexpected pre-state: {[dict(r) for r in rows]}")
    rollback_lines = [
        "-- Reverses operator-approved NEEDS_REVIEW resolution for claims 704263 and 704274.",
        "-- Forward change applied 2026-08-31.",
        "BEGIN;",
    ]
    for row in rows:
        rollback_lines.append(f"UPDATE claims SET reasoning={q(db, row['reasoning'])} WHERE id={row['id']};")
    rollback_lines.append("COMMIT;")
    ROLLBACK.write_text("\n".join(rollback_lines) + "\n", encoding="utf-8")
    if not ROLLBACK.exists() or ROLLBACK.stat().st_size < 300:
        raise SystemExit("rollback was not safely written")

    for row in rows:
        old = row["reasoning"]
        if not old.startswith("NEEDS_REVIEW: "):
            raise SystemExit(f"claim {row['id']} marker shape unexpected")
        new = "Izvērtēts 2026-08-31: " + old.removeprefix("NEEDS_REVIEW: ")
        db.execute("UPDATE claims SET reasoning=? WHERE id=?", (new, row["id"]))
    db.commit()
    after = [dict(r) for r in db.execute(
        "SELECT id, reasoning, review_status FROM claims WHERE id IN (?,?) ORDER BY id",
        IDS,
    ).fetchall()]

valid = all(
    r["review_status"] == "reviewed"
    and r["reasoning"].startswith("Izvērtēts 2026-08-31: ")
    and "NEEDS_REVIEW" not in r["reasoning"]
    for r in after
)
print(json.dumps({
    "rollback": str(ROLLBACK),
    "rollback_bytes": ROLLBACK.stat().st_size,
    "claims": after,
    "valid": valid,
}, ensure_ascii=False, indent=2))
raise SystemExit(0 if valid else 1)
