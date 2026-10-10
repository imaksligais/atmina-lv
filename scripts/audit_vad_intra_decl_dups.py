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

DUP_QUERY = """
    SELECT declaration_id, source, source_reg_number, income_type, amount, currency,
           COUNT(*) AS n
    FROM vad_income
    GROUP BY declaration_id, source, source_reg_number, income_type, amount, currency
    HAVING n > 1
    ORDER BY n DESC, declaration_id
"""


def audit_intra_decl_dups(con: sqlite3.Connection) -> dict:
    """Return dup tuples plus the denominator (rows and declarations examined)."""
    rows = con.execute(DUP_QUERY).fetchall()
    total_rows = con.execute("SELECT COUNT(*) FROM vad_income").fetchone()[0]
    total_decls = con.execute(
        "SELECT COUNT(DISTINCT declaration_id) FROM vad_income"
    ).fetchone()[0]
    return {"dups": rows, "rows_scanned": total_rows, "decls_scanned": total_decls}


def main() -> int:
    con = sqlite3.connect("data/atmina.db")
    try:
        result = audit_intra_decl_dups(con)
    finally:
        con.close()

    rows = result["dups"]
    print(
        f"Atrasti {len(rows)} intra-decl dubulti income tuples "
        f"no {result['rows_scanned']} ienākumu rindām / "
        f"{result['decls_scanned']} deklarācijām"
    )
    if rows:
        print("\nTop 50:")
        for r in rows[:50]:
            print(r)
        distinct_decls = {r[0] for r in rows}
        print(f"\nUnikāli decl_id ar dubultiem: {len(distinct_decls)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
