import os
import sys
from pathlib import Path

os.chdir(r"E:\atmina")
sys.path.insert(0, r"E:\atmina")

from src.db import get_db
from src.graphics.storage import approve_image

CLAIM_IDS = [704201, 704202, 704243]
IMAGE_ID = 292
ROLLBACK = Path(r"E:\atmina\data\rollback_approve_20260828_brief_2026-08-29.sql")


def sql_value(value):
    if value is None:
        return "NULL"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


db = get_db()
claims = db.execute(
    "SELECT id, reasoning, review_status FROM claims WHERE id IN (?,?,?) ORDER BY id",
    CLAIM_IDS,
).fetchall()
image = db.execute(
    "SELECT id, approved FROM brief_images WHERE id=?",
    (IMAGE_ID,),
).fetchone()
if len(claims) != 3 or image is None:
    raise SystemExit("Approval targets missing")

rollback_lines = ["BEGIN;"]
for row in claims:
    rollback_lines.append(
        f"UPDATE claims SET reasoning={sql_value(row['reasoning'])} WHERE id={row['id']};"
    )
rollback_lines.append(
    f"UPDATE brief_images SET approved={sql_value(image['approved'])} WHERE id={IMAGE_ID};"
)
rollback_lines.append("COMMIT;")
ROLLBACK.write_text("\n".join(rollback_lines) + "\n", encoding="utf-8")

for row in claims:
    reasoning = row["reasoning"] or ""
    if reasoning.startswith("NEEDS_REVIEW:"):
        resolved = reasoning.replace("NEEDS_REVIEW:", "Izvērtēts 2026-08-29:", 1)
        db.execute("UPDATE claims SET reasoning=? WHERE id=?", (resolved, row["id"]))
    elif row["review_status"] != "reviewed":
        raise SystemExit(f"Claim {row['id']} lacks expected marker or reviewed state")
db.commit()
db.close()

approve_image(get_db(), IMAGE_ID)

check = get_db()
for cid in CLAIM_IDS:
    row = check.execute(
        "SELECT id, reasoning, review_status FROM claims WHERE id=?", (cid,)
    ).fetchone()
    if row["review_status"] != "reviewed" or "NEEDS_REVIEW" in (row["reasoning"] or ""):
        raise SystemExit(f"Claim {cid} resolution failed")
    print("CLAIM_APPROVED", cid, row["review_status"])
img = check.execute(
    "SELECT id, approved FROM brief_images WHERE id=?", (IMAGE_ID,)
).fetchone()
if img["approved"] != 1:
    raise SystemExit("Image approval failed")
print("IMAGE_APPROVED", IMAGE_ID)
print("ROLLBACK", ROLLBACK)
