"""VAD DDL — table init for amatpersonu deklarācijas.

Spec: docs/superpowers/specs/2026-05-02-vad-deklaracijas-design.md § 4

Saskaņā ar saeima/schema.py precedentu — DDL paliek Python pusē, ne
src/schema.sql, jo pakete ir lazy-init (skat. spec § 4.5: nav daļa no
init_db()). Render layer guard ar try/except OperationalError.
"""

import sqlite3

from src.db import DB_PATH, get_db


def init_vad_tables(db_path: str | None = None) -> None:
    """Create VAD-specific tables if they don't exist. Idempotent."""
    # Resolve DB_PATH at CALL time so `monkeypatch.setattr(db, "DB_PATH", ...)`
    # is honored (a `db_path=DB_PATH` def-time default would bind the global's
    # value at import and silently ignore the patch).
    if db_path is None:
        db_path = DB_PATH
    # Bypass get_db() for test paths: avoids needing full production schema
    # (sqlite_vec extension, schema.sql tables). PRAGMA foreign_keys is set
    # explicitly on both branches.
    db = get_db(db_path) if db_path == DB_PATH else sqlite3.connect(db_path)
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS vad_declarations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            opponent_id INTEGER NOT NULL REFERENCES tracked_politicians(id),
            vad_uuid TEXT,
            declaration_type TEXT NOT NULL,
            declaration_kind TEXT NOT NULL,
            declaration_year INTEGER,
            institution TEXT,
            position_title TEXT,
            submitted_at TEXT,
            published_at TEXT,
            other_info TEXT,
            financial_instruments_text TEXT,
            other_benefits_text TEXT,
            trust_agreement_text TEXT,
            has_private_pension INTEGER,
            has_life_insurance INTEGER,
            source_url TEXT NOT NULL,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            raw_html TEXT,
            UNIQUE(opponent_id, declaration_kind, declaration_year, submitted_at, position_title)
        );
        CREATE INDEX IF NOT EXISTS idx_vad_decl_opponent ON vad_declarations(opponent_id);
        CREATE INDEX IF NOT EXISTS idx_vad_decl_year ON vad_declarations(declaration_year);
        CREATE INDEX IF NOT EXISTS idx_vad_decl_published ON vad_declarations(published_at);

        CREATE TABLE IF NOT EXISTS vad_positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            declaration_id INTEGER NOT NULL REFERENCES vad_declarations(id) ON DELETE CASCADE,
            position_title TEXT NOT NULL,
            entity_name TEXT NOT NULL,
            entity_reg_number TEXT,
            entity_address TEXT,
            is_individual INTEGER NOT NULL DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_vad_positions_decl ON vad_positions(declaration_id);
        CREATE INDEX IF NOT EXISTS idx_vad_positions_reg ON vad_positions(entity_reg_number);

        CREATE TABLE IF NOT EXISTS vad_real_estate (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            declaration_id INTEGER NOT NULL REFERENCES vad_declarations(id) ON DELETE CASCADE,
            property_type TEXT NOT NULL,
            location TEXT NOT NULL,
            ownership_status TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_vad_real_estate_decl ON vad_real_estate(declaration_id);

        CREATE TABLE IF NOT EXISTS vad_companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            declaration_id INTEGER NOT NULL REFERENCES vad_declarations(id) ON DELETE CASCADE,
            company_name TEXT NOT NULL,
            reg_number TEXT,
            address TEXT,
            capital_kind TEXT NOT NULL,
            units REAL,
            total_value REAL,
            currency TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_vad_companies_decl ON vad_companies(declaration_id);
        CREATE INDEX IF NOT EXISTS idx_vad_companies_reg ON vad_companies(reg_number);

        CREATE TABLE IF NOT EXISTS vad_vehicles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            declaration_id INTEGER NOT NULL REFERENCES vad_declarations(id) ON DELETE CASCADE,
            vehicle_type TEXT NOT NULL,
            brand TEXT NOT NULL,
            year_made INTEGER,
            year_registered INTEGER,
            ownership_status TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_vad_vehicles_decl ON vad_vehicles(declaration_id);

        CREATE TABLE IF NOT EXISTS vad_savings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            declaration_id INTEGER NOT NULL REFERENCES vad_declarations(id) ON DELETE CASCADE,
            savings_kind TEXT NOT NULL,
            amount REAL NOT NULL,
            currency TEXT NOT NULL,
            amount_in_words TEXT,
            holder_name TEXT,
            holder_reg_number TEXT,
            holder_address TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_vad_savings_decl ON vad_savings(declaration_id);

        CREATE TABLE IF NOT EXISTS vad_income (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            declaration_id INTEGER NOT NULL REFERENCES vad_declarations(id) ON DELETE CASCADE,
            source TEXT NOT NULL,
            source_reg_number TEXT,
            is_individual INTEGER NOT NULL DEFAULT 0,
            income_type TEXT NOT NULL,
            amount REAL NOT NULL,
            currency TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_vad_income_decl ON vad_income(declaration_id);

        CREATE TABLE IF NOT EXISTS vad_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            declaration_id INTEGER NOT NULL REFERENCES vad_declarations(id) ON DELETE CASCADE,
            transaction_description TEXT NOT NULL,
            amount REAL,
            currency TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_vad_transactions_decl ON vad_transactions(declaration_id);

        CREATE TABLE IF NOT EXISTS vad_debts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            declaration_id INTEGER NOT NULL REFERENCES vad_declarations(id) ON DELETE CASCADE,
            creditor_name TEXT NOT NULL,
            creditor_reg_number TEXT,
            creditor_address TEXT,
            amount REAL NOT NULL,
            currency TEXT NOT NULL,
            amount_in_words TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_vad_debts_decl ON vad_debts(declaration_id);

        CREATE TABLE IF NOT EXISTS vad_loans_given (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            declaration_id INTEGER NOT NULL REFERENCES vad_declarations(id) ON DELETE CASCADE,
            amount REAL NOT NULL,
            currency TEXT NOT NULL,
            amount_in_words TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_vad_loans_decl ON vad_loans_given(declaration_id);

        CREATE TABLE IF NOT EXISTS vad_family (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            declaration_id INTEGER NOT NULL REFERENCES vad_declarations(id) ON DELETE CASCADE,
            full_name TEXT NOT NULL,
            relation TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_vad_family_decl ON vad_family(declaration_id);
    """)
    db.commit()
    db.close()
