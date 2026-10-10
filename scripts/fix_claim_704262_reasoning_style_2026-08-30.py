from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.db import get_db

new_reasoning = (
    "NEEDS_REVIEW: Kails partijas MMN konta retvīts viņa profilā. "
    "Partijas ierakstā ir nosaukts Jāzeps Baško un pieteikts video par veselības aprūpes sistēmu, "
    "taču retvīts ir netieša forma; pozīcijas saturs nāk no partijas ieraksta, nevis politiķa paša pievienota komentāra."
)
with get_db() as db:
    cursor = db.execute("UPDATE claims SET reasoning=? WHERE id=704262", (new_reasoning,))
    if cursor.rowcount != 1:
        raise SystemExit("claim 704262 update failed")
    db.commit()
    print("updated=704262")
