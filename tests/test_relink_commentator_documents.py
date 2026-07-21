"""Tests for scripts/relink_commentator_documents.py — verify subject links removed
and link_politicians_to_documents re-scans for mentioned politicians."""
import sqlite3
from pathlib import Path

import pytest

from scripts.relink_commentator_documents import remove_subject_links_for_demoted


@pytest.fixture
def temp_db(tmp_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(tmp_path / "test.db")
    con.executescript("""
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY, content TEXT, source_url TEXT,
            platform TEXT, scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE document_politicians (
            document_id INTEGER, politician_id INTEGER, role TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    con.executescript("""
        INSERT INTO documents (id, content, source_url, platform) VALUES
            (101, 'Lūgums @ltvzinas par Melni', 'https://x.com/Heinrih5/status/1', 'twitter'),
            (102, 'Cits tvīts', 'https://x.com/Heinrih5/status/2', 'twitter'),
            (103, 'Vēl viens', 'https://x.com/Heinrih5/status/3', 'twitter');
        INSERT INTO document_politicians (document_id, politician_id, role) VALUES
            (101, 171, 'subject'),
            (101, 157, 'mentioned'),
            (102, 171, 'subject'),
            (103, 171, 'subject');
    """)
    con.commit()
    return con


def test_removes_subject_links_for_demoted_pids(temp_db: sqlite3.Connection):
    removed = remove_subject_links_for_demoted(temp_db, demoted_pids=[171])
    assert removed == 3
    rows = temp_db.execute(
        "SELECT COUNT(*) FROM document_politicians WHERE politician_id=171 AND role='subject'"
    ).fetchone()
    assert rows[0] == 0


def test_preserves_other_role_links_for_demoted(temp_db: sqlite3.Connection):
    """If demoted commentator was tagged 'mentioned' on some doc, that link survives —
    only role='subject' is the structural lie we want to undo."""
    temp_db.execute(
        "INSERT INTO document_politicians (document_id, politician_id, role) VALUES (101, 171, 'mentioned')"
    )
    temp_db.commit()
    remove_subject_links_for_demoted(temp_db, demoted_pids=[171])
    rows = temp_db.execute(
        "SELECT COUNT(*) FROM document_politicians WHERE politician_id=171 AND role='mentioned'"
    ).fetchone()
    assert rows[0] == 1


def test_preserves_other_politicians_subject_links(temp_db: sqlite3.Connection):
    """Mentioned politician (157) on doc 101 must remain after demotion."""
    remove_subject_links_for_demoted(temp_db, demoted_pids=[171])
    rows = temp_db.execute(
        "SELECT COUNT(*) FROM document_politicians WHERE politician_id=157 AND role='mentioned'"
    ).fetchone()
    assert rows[0] == 1


def test_idempotent(temp_db: sqlite3.Connection):
    remove_subject_links_for_demoted(temp_db, demoted_pids=[171])
    removed_again = remove_subject_links_for_demoted(temp_db, demoted_pids=[171])
    assert removed_again == 0
