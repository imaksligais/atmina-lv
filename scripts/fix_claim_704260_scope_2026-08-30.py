from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db import get_db

CLAIM_ID = 704260
OLD = "Kritizē līdzšinējo varas partiju īstenoto integrācijas politiku — pēc viņa novērojuma imigranti Latvijā savā starpā sazinās krievu valodā, kas liecina par integrācijas neveiksmi."
NEW = "Kritizē līdzšinējo varas partiju īstenoto integrācijas politiku, par neveiksmes piemēru minot četru «Wolt» kurjeru savstarpējo saziņu krievu valodā."


def main() -> None:
    db = get_db()
    row = db.execute("SELECT stance FROM claims WHERE id=?", (CLAIM_ID,)).fetchone()
    if row is None:
        raise SystemExit(f"claim {CLAIM_ID} not found")
    if row["stance"] != OLD:
        raise SystemExit("pre-image mismatch; refusing update")
    cur = db.execute("UPDATE claims SET stance=? WHERE id=? AND stance=?", (NEW, CLAIM_ID, OLD))
    db.commit()
    if cur.rowcount != 1:
        raise SystemExit(f"updated {cur.rowcount}, expected 1")
    check = db.execute("SELECT stance FROM claims WHERE id=?", (CLAIM_ID,)).fetchone()[0]
    if check != NEW:
        raise SystemExit("read-back mismatch")
    print(f"updated claim {CLAIM_ID}")
    db.close()


if __name__ == "__main__":
    main()
