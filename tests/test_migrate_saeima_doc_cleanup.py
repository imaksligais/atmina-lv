"""Tests for scripts.migrate_saeima_doc_cleanup.

Covers:
  - Removes fake saeima docs + linked junctions
  - Nullifies claim.document_id only for affected claims
  - Idempotent: second run is no-op
  - Aborts if non-saeima_vote claim references a fake doc (safety guard)
  - Aborts if document_chunks point to fake docs
  - Dry-run reports counts without writing
"""
from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path

import pytest


def _build_fixture_db() -> str:
    """Minimal schema + seed: 3 fake saeima docs, 1 real news doc, claims, junctions."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = sqlite3.connect(path)
    db.executescript("""
        CREATE TABLE tracked_politicians (
            id INTEGER PRIMARY KEY, name TEXT, party TEXT, role TEXT,
            relationship_type TEXT DEFAULT 'tracked'
        );
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY, content TEXT, content_hash TEXT,
            source_url TEXT, platform TEXT, language TEXT, source_id INTEGER,
            scraped_at TIMESTAMP, source_domain TEXT, archive_path TEXT
        );
        CREATE TABLE document_politicians (
            document_id INTEGER, politician_id INTEGER, role TEXT,
            PRIMARY KEY (document_id, politician_id, role)
        );
        CREATE TABLE document_chunks (
            id INTEGER PRIMARY KEY, document_id INTEGER, chunk_text TEXT
        );
        CREATE TABLE claims (
            id INTEGER PRIMARY KEY, opponent_id INTEGER, document_id INTEGER,
            topic TEXT, stance TEXT, quote TEXT, confidence REAL, reasoning TEXT,
            salience REAL, source_url TEXT, stated_at TIMESTAMP,
            created_at TIMESTAMP, claim_type TEXT, speaker_id INTEGER
        );
    """)
    # politicians
    db.execute("INSERT INTO tracked_politicians (id, name) VALUES (1, 'A'), (2, 'B')")
    # 3 fake saeima docs
    for i in (101, 102, 103):
        db.execute(
            "INSERT INTO documents (id, platform, source_domain, source_url, content, content_hash) "
            "VALUES (?, 'saeima', 'titania.saeima.lv', ?, ?, ?)",
            (i, f"https://titania.saeima.lv/vote/{i}", f"vote {i}", f"hash{i}"),
        )
        db.execute(
            "INSERT INTO document_politicians (document_id, politician_id, role) "
            "VALUES (?, ?, 'subject')",
            (i, 1 if i % 2 else 2),
        )
        db.execute(
            "INSERT INTO claims (opponent_id, document_id, topic, stance, claim_type, source_url) "
            "VALUES (?, ?, ?, ?, 'saeima_vote', ?)",
            (1 if i % 2 else 2, i, "Budžets", "Par", f"https://titania.saeima.lv/vote/{i}"),
        )
    # 1 real news doc + claim — must be untouched
    db.execute(
        "INSERT INTO documents (id, platform, source_domain, source_url, content, content_hash) "
        "VALUES (200, 'web', 'lsm.lv', 'https://lsm.lv/x', 'real news', 'hashr')"
    )
    db.execute(
        "INSERT INTO document_politicians (document_id, politician_id, role) "
        "VALUES (200, 1, 'subject')"
    )
    db.execute(
        "INSERT INTO claims (opponent_id, document_id, topic, stance, claim_type, source_url) "
        "VALUES (1, 200, 'Aizsardzība', 'pro', 'position', 'https://lsm.lv/x')"
    )
    db.commit()
    db.close()
    return path


def _safe_unlink(path: str) -> None:
    try:
        Path(path).unlink()
    except OSError:
        pass


def test_migration_removes_fake_docs_and_nulls_claim_refs():
    from scripts.migrate_saeima_doc_cleanup import migrate
    path = _build_fixture_db()
    try:
        counts = migrate(path, dry_run=False)
        assert counts["fake_docs_pre"] == 3
        assert counts["claims_nulled"] == 3
        assert counts["junctions_deleted"] == 3
        assert counts["docs_deleted"] == 3
        assert counts["fake_docs_post"] == 0

        db = sqlite3.connect(path)
        # Real news doc + claim untouched
        assert db.execute("SELECT COUNT(*) FROM documents WHERE id=200").fetchone()[0] == 1
        assert db.execute("SELECT document_id FROM claims WHERE id=4").fetchone()[0] == 200
        # No saeima docs left
        assert db.execute("SELECT COUNT(*) FROM documents WHERE platform='saeima'").fetchone()[0] == 0
        # All saeima_vote claims have NULL document_id
        n = db.execute("SELECT COUNT(*) FROM claims WHERE claim_type='saeima_vote' AND document_id IS NOT NULL").fetchone()[0]
        assert n == 0
        # And those claims still EXIST (not deleted)
        n = db.execute("SELECT COUNT(*) FROM claims WHERE claim_type='saeima_vote'").fetchone()[0]
        assert n == 3
        db.close()
    finally:
        _safe_unlink(path)


def test_migration_idempotent_second_run_noop():
    from scripts.migrate_saeima_doc_cleanup import migrate
    path = _build_fixture_db()
    try:
        migrate(path, dry_run=False)
        counts2 = migrate(path, dry_run=False)
        assert counts2["fake_docs_pre"] == 0
        assert counts2["claims_nulled"] == 0
        assert counts2["junctions_deleted"] == 0
        assert counts2["docs_deleted"] == 0
    finally:
        _safe_unlink(path)


def test_migration_aborts_on_foreign_claim_reference():
    """If a non-saeima_vote claim references a fake doc, refuse to migrate."""
    from scripts.migrate_saeima_doc_cleanup import migrate
    path = _build_fixture_db()
    try:
        # Inject a foreign reference
        db = sqlite3.connect(path)
        db.execute(
            "INSERT INTO claims (opponent_id, document_id, topic, stance, claim_type, source_url) "
            "VALUES (1, 101, 'Other', 'x', 'position', 'https://elsewhere.lv')"
        )
        db.commit()
        db.close()

        with pytest.raises(RuntimeError, match="non-saeima_vote claims reference"):
            migrate(path, dry_run=False)

        # Verify nothing was deleted
        db = sqlite3.connect(path)
        assert db.execute("SELECT COUNT(*) FROM documents WHERE platform='saeima'").fetchone()[0] == 3
        db.close()
    finally:
        _safe_unlink(path)


def test_migration_aborts_on_chunk_reference():
    from scripts.migrate_saeima_doc_cleanup import migrate
    path = _build_fixture_db()
    try:
        db = sqlite3.connect(path)
        db.execute("INSERT INTO document_chunks (document_id, chunk_text) VALUES (101, 'chunk')")
        db.commit()
        db.close()

        with pytest.raises(RuntimeError, match="document_chunks point to saeima"):
            migrate(path, dry_run=False)

        db = sqlite3.connect(path)
        assert db.execute("SELECT COUNT(*) FROM documents WHERE platform='saeima'").fetchone()[0] == 3
        db.close()
    finally:
        _safe_unlink(path)


def test_dry_run_reports_counts_without_writing():
    from scripts.migrate_saeima_doc_cleanup import migrate
    path = _build_fixture_db()
    try:
        counts = migrate(path, dry_run=True)
        assert counts["dry_run"] is True
        assert counts["fake_docs_pre"] == 3
        assert counts["claims_nulled"] == 3
        assert counts["docs_deleted"] == 3

        # Nothing actually changed
        db = sqlite3.connect(path)
        assert db.execute("SELECT COUNT(*) FROM documents WHERE platform='saeima'").fetchone()[0] == 3
        assert db.execute("SELECT COUNT(*) FROM document_politicians").fetchone()[0] == 4  # 3 fake + 1 real
        db.close()
    finally:
        _safe_unlink(path)
