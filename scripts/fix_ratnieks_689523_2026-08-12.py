# -*- coding: utf-8 -*-
"""Operatora lēmums 2026-08-12 vēlu vakarā: slēgt claim #689523 marķieri
(rollback: data/rollback_ratnieks_689523_2026-08-12.sql).

Lēmums: aicinājums, ne pozīcija — intervijas pilnteksts ir aiz lasi.lv maksas
sienas (ingests doc 86399 deva 402 zīmju stubu), tāpēc claim paliek tāds, kāds
ir (vispārīgs aicinājums, conf 0.5); ja pilnteksts kādreiz kļūst pieejams,
URL-first dedup ļauj doc 86399 pāringestēt un ekstrakciju atkārtot.
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"E:\atmina")
from src.db import get_db

db = get_db()
r = db.execute("SELECT reasoning FROM claims WHERE id=689523").fetchone()["reasoning"]
assert r.startswith("NEEDS_REVIEW:"), "marķieris nav atrasts prefiksā"
new = r.replace(
    "NEEDS_REVIEW:",
    "Izvērtēts 2026-08-12: operatora lēmums — aicinājums, ne pozīcija; claim paliek kā ir. "
    "Intervijas pilnteksts aiz lasi.lv maksas sienas (doc 86399, 402 zīmju stubs); ja teksts "
    "kļūst pieejams, doc pāringestējams un ekstrakcija atkārtojama. Sākotnējais pamatojums —",
    1,
)
db.execute("UPDATE claims SET reasoning=? WHERE id=689523", (new,))
db.commit()
print("review_status:", db.execute("SELECT review_status FROM claims WHERE id=689523").fetchone()["review_status"])
