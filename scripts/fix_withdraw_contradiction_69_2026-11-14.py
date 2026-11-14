"""Atsauc publicēto pretrunu #69 (Krištopans, Rail Baltica).

Pēc Krištopana iebilduma 14.11. (x.com/Chapis/status/2121539599151292486, doc 158160)
pārbaudīta visa 1149/Lp14 ķēde: 16.04. viņš balsoja «Par» apturēšanas priekšlikumiem
Nr. 1, 17–20 un ir viens no pieciem pārvaldības priekšlikuma Nr. 10 iesniedzējiem
(iekļauts Nr. 11). Publicētais teksts šos balsojumus izlaida (T14). @devils-advocate:
ATSAUKT. Faktu lapa: docs/tweet_bank/2026-11-14-pretrunas-rail-baltica-social.md.
Claims 20702 un 21177 paliek (abas ir pareizas).

    .venv/Scripts/python.exe scripts/fix_withdraw_contradiction_69_2026-11-14.py           # dry-run
    .venv/Scripts/python.exe scripts/fix_withdraw_contradiction_69_2026-11-14.py --apply

Rollback: data/rollback_withdraw_contradiction_69_2026-11-14.sql
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.db import get_db, withdraw_contradiction  # noqa: E402

CONTRA_ID = 69
NOTE = (
    "Pretruna atsaukta 2026-11-14. Otrajā lasījumā 2026. gada 16. aprīlī Krištopans balsoja «Par» priekšlikumiem apturēt Rail Baltica un Latvijai izstāties no projekta, bet Saeima tos noraidīja. Galīgajā lasījumā viņš atbalstīja grozījumus, kuros daļēji iekļauts arī priekšlikums par projekta pārvaldību, ko viņš iesniedza kopā ar četriem deputātiem. Tāpēc šis balsojums nav pretrunā ar viņa aicinājumu projektu apturēt."
)


def main(apply: bool) -> None:
    db = get_db(None)
    row = db.execute("SELECT confirmed, withdrawn_at FROM contradictions WHERE id=?", (CONTRA_ID,)).fetchone()
    if row is None or row["confirmed"] != 1:
        sys.exit(f"STOP: negaidīts stāvoklis {dict(row) if row else None}")
    print(f"#{CONTRA_ID}: confirmed=1 → -1\nPiezīme: {NOTE}")
    if not apply:
        print("dry-run — nekas nav mainīts")
        return
    with db:
        withdraw_contradiction(CONTRA_ID, NOTE, db=db)
    after = db.execute("SELECT confirmed, withdrawn_at FROM contradictions WHERE id=?", (CONTRA_ID,)).fetchone()
    print("PĒC:", dict(after))
    if after["confirmed"] != -1:
        sys.exit("KĻŪDA: confirmed nav -1")


if __name__ == "__main__":
    main("--apply" in sys.argv)
