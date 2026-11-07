"""Tests for scripts.audit_vad_intra_decl_dups — finding must carry a denominator."""

import sqlite3

from scripts.audit_vad_intra_decl_dups import audit_intra_decl_dups


def _init_income(con: sqlite3.Connection) -> None:
    con.execute(
        """
        CREATE TABLE vad_income (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            declaration_id INTEGER NOT NULL,
            source TEXT NOT NULL,
            source_reg_number TEXT,
            is_individual INTEGER NOT NULL DEFAULT 0,
            income_type TEXT NOT NULL,
            amount REAL NOT NULL,
            currency TEXT NOT NULL
        )
        """
    )


def _add(con, decl, source, itype, amount, currency):
    con.execute(
        "INSERT INTO vad_income (declaration_id, source, source_reg_number, "
        "income_type, amount, currency) VALUES (?, ?, NULL, ?, ?, ?)",
        (decl, source, itype, amount, currency),
    )


def test_reports_denominator_with_no_dups():
    con = sqlite3.connect(":memory:")
    _init_income(con)
    _add(con, 1, "Alga", "alga", 1000.0, "EUR")
    _add(con, 2, "Pensija", "pensija", 500.0, "EUR")

    result = audit_intra_decl_dups(con)
    assert result["dups"] == []
    assert result["rows_scanned"] == 2
    assert result["decls_scanned"] == 2


def test_finds_intra_decl_dup_and_reports_denominator():
    con = sqlite3.connect(":memory:")
    _init_income(con)
    _add(con, 1, "Alga", "alga", 1000.0, "EUR")
    _add(con, 1, "Alga", "alga", 1000.0, "EUR")  # intra-decl dup
    _add(con, 2, "Pensija", "pensija", 500.0, "EUR")

    result = audit_intra_decl_dups(con)
    assert len(result["dups"]) == 1
    assert result["rows_scanned"] == 3
    assert result["decls_scanned"] == 2


def test_same_amount_across_decls_is_not_a_dup():
    """The dup key includes declaration_id — cross-decl repeats are not flagged."""
    con = sqlite3.connect(":memory:")
    _init_income(con)
    _add(con, 1, "Alga", "alga", 1000.0, "EUR")
    _add(con, 2, "Alga", "alga", 1000.0, "EUR")

    result = audit_intra_decl_dups(con)
    assert result["dups"] == []
    assert result["rows_scanned"] == 2
    assert result["decls_scanned"] == 2
