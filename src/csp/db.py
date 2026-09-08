"""SQLite schema for CSP data cache."""
import sqlite3


def init_db(db_path: str) -> sqlite3.Connection:
    """Create tables if needed, return connection."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS csp_data (
            table_id   TEXT NOT NULL,
            period     TEXT NOT NULL,
            freq       TEXT NOT NULL,
            geo        TEXT NOT NULL DEFAULT 'LV',
            breakdown  TEXT NOT NULL DEFAULT '_total_',
            value      REAL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (table_id, period, geo, breakdown)
        );

        CREATE TABLE IF NOT EXISTS csp_metadata (
            table_id    TEXT PRIMARY KEY,
            label_lv    TEXT NOT NULL,
            domain      TEXT NOT NULL,
            freq        TEXT NOT NULL,
            unit        TEXT NOT NULL,
            last_sync   TEXT,
            csp_updated TEXT
        );

        CREATE TABLE IF NOT EXISTS events (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            date     TEXT NOT NULL,
            label_lv TEXT NOT NULL,
            category TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS topic_links (
            table_id TEXT NOT NULL,
            topic    TEXT NOT NULL,
            keywords TEXT NOT NULL DEFAULT '',
            PRIMARY KEY (table_id, topic)
        );
    """)
    conn.commit()
    return conn
