"""Saeima DDL — table init for sessions, votes, individual votes, agenda items, bills.

F4.2 izvilkts no src/saeima.py. Divas idempotentas funkcijas, kas izveido visu
Saeimas datu modeli (sessions / agenda_items / votes / individual_votes /
bills / bill_stages / bill_politicians + indeksi). Atdalītas tāpēc, ka Phase 1A
bills atveda jaunu init pasi, ko ne visi vēsturiskie skripti vēlas izsaukt
kopā ar vote-only setup-u.

Saskaņā ar F2 (schema.sql carve-out) loģiku — Saeimas DDL paliek Python pusē,
ne `src/schema.sql`, jo `init_saeima_bills` satur `ALTER TABLE ADD COLUMN IF
NOT EXISTS` pattern, ko sqlite < 3.35 neatbalsta. Tas pats arguments kā vec0
virtual tables un brief_images columns, sk. wiki/CHANGELOG 2026-04-29 § Fāze 2.
"""

from src.db import get_db


def init_saeima_tables(db_path: str | None = None) -> None:
    """Create Saeima-specific tables if they don't exist."""
    db = get_db(db_path)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS saeima_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            date TEXT,
            title TEXT,
            url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS saeima_agenda_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_db_id INTEGER REFERENCES saeima_sessions(id),
            item_number INTEGER,
            title TEXT NOT NULL,
            document_nr TEXT,
            document_nrs TEXT,
            commission TEXT,
            submitter TEXT,
            result TEXT,
            vote_summary TEXT,
            document_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS saeima_votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agenda_item_id INTEGER REFERENCES saeima_agenda_items(id),
            motif TEXT NOT NULL,
            vote_date TEXT,
            vote_time TEXT,
            total_par INTEGER DEFAULT 0,
            total_pret INTEGER DEFAULT 0,
            total_atturas INTEGER DEFAULT 0,
            total_nebalso INTEGER DEFAULT 0,
            result TEXT,
            url TEXT UNIQUE,
            summary TEXT,
            document_nr TEXT,
            document_url TEXT,
            topic TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS saeima_individual_votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vote_id INTEGER REFERENCES saeima_votes(id),
            deputy_name TEXT NOT NULL,
            faction TEXT,
            vote TEXT NOT NULL,
            politician_id INTEGER REFERENCES tracked_politicians(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_saeima_sessions_date
            ON saeima_sessions(date);
        CREATE INDEX IF NOT EXISTS idx_saeima_votes_date
            ON saeima_votes(vote_date);
        CREATE INDEX IF NOT EXISTS idx_saeima_indiv_politician
            ON saeima_individual_votes(politician_id);
        CREATE INDEX IF NOT EXISTS idx_saeima_indiv_vote_id
            ON saeima_individual_votes(vote_id);
    """)
    db.commit()
    db.close()


def init_saeima_bills(db_path: str | None = None) -> None:
    """Create Saeima Bills tracker tables (Phase 1A schema).

    Creates saeima_bills, saeima_bill_stages, saeima_bill_politicians tables
    plus indexes. Adds bill_id column to saeima_votes if not present.

    Idempotent: safe to call multiple times. Distinct from init_saeima_tables()
    so existing code that initializes vote-only tables continues to work.

    See docs/superpowers/specs/2026-04-22-saeima-bills-design.md § 3.1.
    """
    db = get_db(db_path)

    # Add bill_id column to saeima_votes if not present
    cols = [row[1] for row in db.execute("PRAGMA table_info(saeima_votes)").fetchall()]
    if "bill_id" not in cols:
        db.execute(
            "ALTER TABLE saeima_votes ADD COLUMN bill_id INTEGER REFERENCES saeima_bills(id)"
        )

    db.executescript("""
        CREATE TABLE IF NOT EXISTS saeima_bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_nr TEXT UNIQUE NOT NULL,
            bill_type TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT,
            topic TEXT,
            base_law_slug TEXT,
            institutional_submitter TEXT,
            current_stage TEXT,
            current_status TEXT,
            first_seen_at TIMESTAMP,
            last_updated_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS saeima_bill_stages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_id INTEGER NOT NULL REFERENCES saeima_bills(id),
            stage_name TEXT NOT NULL,
            stage_result TEXT,
            stage_date TEXT,
            vote_id INTEGER REFERENCES saeima_votes(id),
            session_id INTEGER REFERENCES saeima_sessions(id),
            amendment_nr TEXT,
            stage_kind TEXT NOT NULL DEFAULT 'vote',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS saeima_bill_politicians (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_id INTEGER NOT NULL REFERENCES saeima_bills(id),
            politician_id INTEGER NOT NULL REFERENCES tracked_politicians(id),
            role TEXT NOT NULL,
            amendment_nr TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(bill_id, politician_id, role, amendment_nr)
        );

        CREATE INDEX IF NOT EXISTS idx_bills_document_nr ON saeima_bills(document_nr);
        CREATE INDEX IF NOT EXISTS idx_bills_topic ON saeima_bills(topic);
        CREATE INDEX IF NOT EXISTS idx_bills_status ON saeima_bills(current_status);
        CREATE INDEX IF NOT EXISTS idx_bills_base_law_slug ON saeima_bills(base_law_slug);
        CREATE INDEX IF NOT EXISTS idx_bill_stages_bill_id ON saeima_bill_stages(bill_id);
        CREATE INDEX IF NOT EXISTS idx_bill_stages_vote_id ON saeima_bill_stages(vote_id);
        CREATE INDEX IF NOT EXISTS idx_bill_stages_kind ON saeima_bill_stages(stage_kind);
        CREATE INDEX IF NOT EXISTS idx_bill_politicians_bill_id ON saeima_bill_politicians(bill_id);
        CREATE INDEX IF NOT EXISTS idx_bill_politicians_politician_id ON saeima_bill_politicians(politician_id);
        CREATE INDEX IF NOT EXISTS idx_saeima_votes_bill_id ON saeima_votes(bill_id);
    """)
    db.commit()
    db.close()
