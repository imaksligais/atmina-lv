from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.db import get_db

with get_db() as db:
    row = db.execute("SELECT opponent_id, source_url FROM claims WHERE id = 704281").fetchone()
    if row is None:
        raise SystemExit("claim 704281 missing")
    collision = db.execute(
        "SELECT id FROM claims WHERE opponent_id=? AND source_url=? AND topic='ES politika' AND id<>704281",
        (row["opponent_id"], row["source_url"]),
    ).fetchone()
    if collision:
        raise SystemExit(f"topic collision with claim {collision['id']}")

    changes = {
        704278: ("quote", "Es gribētu šo jautājumu patiešām atrisināt un pie šī neatgriezties, jo tā regularitāte, ar kādu mēs pie kompensācijām atgriežamies, nu ja ne reizi mēnesī, tad noteikti vairākas reizes gadā. Nu, būtu svētīgi tiešām izrunāt, atrunāt, atrast kompromisu un pie tā neatgriezties,"),
        704279: ("reasoning", "TV24 diskusijā Liepiņa pirmajā personā apgalvo, ka devīze «viens likums, viena taisnība visiem» Latvijā nedarbojas, jo sabiedrībā valda neuzticēšanās tam, ka likums pret visiem tiek piemērots vienādi, un ka likumi jāpiemēro konsekventi un vienādi neatkarīgi no personas statusa. Pieminētie 90 % iedzīvotāju ir pašas vērtējums, nevis sabiedriskās domas pētījuma atsauce."),
        704281: ("topic", "ES politika"),
    }
    for claim_id, (column, value) in changes.items():
        cursor = db.execute(f"UPDATE claims SET {column}=? WHERE id=?", (value, claim_id))
        if cursor.rowcount != 1:
            raise SystemExit(f"claim {claim_id} update failed")
    db.commit()
    print("updated=3 collision=0")
