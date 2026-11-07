"""Atrisina 2 NEEDS_REVIEW pozīcijas no 2026-10-21 Vēstneša stenogrammu sweep.
Rollback: data/rollback_review_sweep_2026-10-21.sql (komitēts pirms apply)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.db import get_db
NEW = {743320: ('Izvērtēts 2026-10-21: stenogramma (doc 122684) tieši saka «tas jau nav atkarīgs no tā, ko mēs te spriežam. Mums nav jājaucas ne tirgus sistēmā, ne šeit» — nostāja skaidra, garāmejot teikta, bet paša vārdiem; citāts pievienots. Sākotnēji: ', 'Mums nav jājaucas ne tirgus sistēmā, ne šeit.'), 743343: ('Izvērtēts 2026-10-21: «Imigrācija» ir iedibinātā tēma pilsonības jautājumiem (30 pozīcijas); runā kā referents, bet ar paša vērtējumu «Tas nav labi! Tas nav pareizi!» un «manuprāt». Sākotnēji: ', None)}
db = get_db()
for cid, (prefix, quote) in NEW.items():
    (r,) = db.execute("SELECT reasoning FROM claims WHERE id=?", (cid,)).fetchone()
    assert r.startswith("NEEDS_REVIEW"), cid
    if quote is None:
        db.execute("UPDATE claims SET reasoning=? WHERE id=?", (prefix + r.removeprefix("NEEDS_REVIEW: "), cid))
    else:
        db.execute("UPDATE claims SET reasoning=?, quote=? WHERE id=?", (prefix + r.removeprefix("NEEDS_REVIEW: "), quote, cid))
db.commit()
for cid in NEW:
    print(cid, db.execute("SELECT review_status FROM claims WHERE id=?", (cid,)).fetchone()[0])
