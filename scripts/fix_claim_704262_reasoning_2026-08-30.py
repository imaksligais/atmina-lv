from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db import get_db

CLAIM_ID = 704262
OLD = "RT no partijas MMN oficiālā konta ar pašattribūcijas formu «Jāzeps Baško par veselības aprūpes sistēmu» + video saite — tā pati forma kā 2026-08-10 pid=13 precedenta claim (RT @partijaMMN ar «vārds par tēmu» + video, quote=None). Pozīcija nodota caur paša partijas kanālu, nevis mediju citātu; glabāts ar samazinātu confidence atbilstoši formai."
NEW = "NEEDS_REVIEW: Kails partijas MMN konta retvīts Baško profilā. Partijas ieraksts atribūcijā nosauc Baško un piesaka video par veselības aprūpes sistēmu, taču retvīts ir netieša forma; pozīcijas saturs nāk no partijas ieraksta, nevis Baško paša pievienota komentāra."


def main() -> None:
    db = get_db()
    row = db.execute("SELECT reasoning FROM claims WHERE id=?", (CLAIM_ID,)).fetchone()
    if row is None or row["reasoning"] != OLD:
        raise SystemExit("pre-image mismatch; refusing update")
    cur = db.execute("UPDATE claims SET reasoning=? WHERE id=? AND reasoning=?", (NEW, CLAIM_ID, OLD))
    db.commit()
    if cur.rowcount != 1:
        raise SystemExit(f"updated {cur.rowcount}, expected 1")
    check = db.execute("SELECT reasoning, review_status FROM claims WHERE id=?", (CLAIM_ID,)).fetchone()
    print({"id": CLAIM_ID, "reasoning": check["reasoning"], "review_status": check["review_status"]})
    if check["review_status"] != "needs_review":
        raise SystemExit("review_status trigger did not classify row")
    db.close()


if __name__ == "__main__":
    main()
