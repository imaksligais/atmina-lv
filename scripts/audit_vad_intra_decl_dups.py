"""Audit: detect intra-declaration duplicate income rows.

VAD Phase 2 — parser dup signāls. Persona C (Inese Kalniņa Tiesu adm 2024)
deklarācijas 3429 saturēja Tiesu adm alga + VSAA pensija dublētas vienā
HTML tabulā. Pēc T2 cleanup šī decl ir dzēsta, bet defekts var pastāvēt
citur. Skripts atklāj.
"""

import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

con = sqlite3.connect("data/atmina.db")
cur = con.cursor()
cur.execute("""
    SELECT declaration_id, source, source_reg_number, income_type, amount, currency,
           COUNT(*) AS n
    FROM vad_income
    GROUP BY declaration_id, source, source_reg_number, income_type, amount, currency
    HAVING n > 1
    ORDER BY n DESC, declaration_id
""")
rows = cur.fetchall()
print(f"Atrasti {len(rows)} intra-decl dubulti income tuples")
if rows:
    print("\nTop 50:")
    for r in rows[:50]:
        print(r)
    # Group by decl_id to see span
    cur.execute("""
        SELECT COUNT(DISTINCT declaration_id), COUNT(DISTINCT
            (SELECT opponent_id FROM vad_declarations WHERE id = declaration_id)
        )
        FROM vad_income
        GROUP BY declaration_id, source, source_reg_number, income_type, amount, currency
        HAVING COUNT(*) > 1
    """)
    # Simpler version
    print(f"\nUnikāli decl_id ar dubultiem: ?")
    distinct_decls = set(r[0] for r in rows)
    print(f"Unikāli decl_id ar dubultiem: {len(distinct_decls)}")
