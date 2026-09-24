from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.db import get_db

changes = {
    704271: (
        'Delfi raksts 2026-08-30: avots dod titulu "tieslietu ministrs" un partiju AS; Smiltēns Saeimā iesniedzis grozījumus Interešu konflikta novēršanas likumā, kam, viņaprāt, vajadzētu novērst neskaidrības par amatpersonu dalību balsojumos par savas institūcijas vadību. Konkrēts likumdošanas solis; rakstā nav tieša Smiltēna citāta, tāpēc quote=null.',
        'Delfi raksts 2026-08-30: avots dod titulu "tieslietu ministrs" un partiju AS; Smiltēns Saeimā iesniedzis grozījumus Interešu konflikta novēršanas likumā, kam, viņaprāt, vajadzētu novērst neskaidrības par amatpersonu dalību balsojumos par savas institūcijas vadību. Konkrēts likumdošanas solis; rakstā nav tieša Smiltēna citāta.',
    ),
    704272: (
        'TVNet raksts 2026-08-30 (pmo.ee saīsinātājs): Smiltēns tieši citēts — situācijā ir pārāk daudz formālisma; pārkāpums, kas ir absolūta formalitāte un nevienam nenodara kaitējumu, nedrīkst patērēt milzīgus resursus, jo soda mērķis vienmēr ir prevencija. Aicina tiesību piemērotājus izmantot visas tiesību interpretācijas metodes un skatīties uz lietām plašāk. Citāts verbatim no raksta.',
        'TVNet raksts 2026-08-30 (pmo.ee saīsinātājs): Smiltēns tieši citēts — situācijā ir pārāk daudz formālisma; pārkāpums, kas ir absolūta formalitāte un nevienam nenodara kaitējumu, nedrīkst patērēt milzīgus resursus, jo soda mērķis vienmēr ir prevencija. Aicina tiesību piemērotājus izmantot visas tiesību interpretācijas metodes un skatīties uz lietām plašāk. Citāts ir burtiski pārņemts no raksta.',
    ),
}
with get_db() as db:
    for claim_id, (old, new) in changes.items():
        row = db.execute("SELECT reasoning FROM claims WHERE id = ?", (claim_id,)).fetchone()
        if row is None or row["reasoning"] != old:
            raise SystemExit(f"Unexpected pre-image for claim {claim_id}")
        db.execute("UPDATE claims SET reasoning = ? WHERE id = ?", (new, claim_id))
    db.commit()
print("updated=2")
