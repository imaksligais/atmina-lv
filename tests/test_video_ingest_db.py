import sqlite3
import pytest

from src.video_ingest.db import (
    insert_video_document,
    link_subjects,
    find_existing_by_hash,
)


@pytest.fixture
def tmp_db(tmp_path):
    db_path = tmp_path / "test.db"
    db = sqlite3.connect(str(db_path))
    # Minimal schema for documents + document_politicians
    db.executescript("""
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT, content_hash TEXT, simhash INTEGER,
            source_id INTEGER, platform TEXT, is_auto_caption INTEGER,
            near_dupe_of INTEGER, source_domain TEXT, source_url TEXT,
            archive_path TEXT, scraped_at TEXT, word_count INTEGER,
            language TEXT, published_at TEXT, is_paywall INTEGER,
            summary TEXT, title TEXT, reviewed_at TEXT,
            reply_count INTEGER, retweet_count INTEGER, favorite_count INTEGER
        );
        CREATE TABLE document_politicians (
            document_id INTEGER, politician_id INTEGER, role TEXT,
            UNIQUE(document_id, politician_id, role)
        );
    """)
    db.commit()
    yield db
    db.close()


def test_insert_video_document_returns_id(tmp_db):
    doc_id = insert_video_document(
        tmp_db,
        content="[00:00] @host: Sveicināti.",
        content_hash="abc123",
        simhash=42,
        source_url="https://www.youtube.com/watch?v=test",
        source_domain="youtube.com",
        title="Test debate",
        published_at="2026-04-15",
        archive_path="videos/2026-04-15-test/",
        word_count=2,
        summary="Test summary.",
    )
    assert doc_id == 1
    row = tmp_db.execute("SELECT platform, source_url FROM documents WHERE id=?", (doc_id,)).fetchone()
    assert row[0] == "video"
    assert row[1] == "https://www.youtube.com/watch?v=test"


def test_find_existing_returns_id(tmp_db):
    doc_id = insert_video_document(
        tmp_db, content="x", content_hash="h1", simhash=0,
        source_url="u", source_domain="d", title="t",
        published_at="2026-04-15", archive_path="x", word_count=1, summary="",
    )
    found = find_existing_by_hash(tmp_db, "h1")
    assert found == doc_id


def test_find_existing_returns_none_when_absent(tmp_db):
    assert find_existing_by_hash(tmp_db, "nope") is None


def test_link_subjects_inserts_rows(tmp_db):
    doc_id = insert_video_document(
        tmp_db, content="x", content_hash="h", simhash=0,
        source_url="u", source_domain="d", title="t",
        published_at="2026-04-15", archive_path="x", word_count=1, summary="",
    )
    link_subjects(tmp_db, doc_id, [3, 12])
    rows = tmp_db.execute(
        "SELECT politician_id, role FROM document_politicians WHERE document_id=?",
        (doc_id,),
    ).fetchall()
    assert sorted(rows) == [(3, "subject"), (12, "subject")]


def test_link_subjects_idempotent(tmp_db):
    doc_id = insert_video_document(
        tmp_db, content="x", content_hash="h", simhash=0,
        source_url="u", source_domain="d", title="t",
        published_at="2026-04-15", archive_path="x", word_count=1, summary="",
    )
    link_subjects(tmp_db, doc_id, [3])
    link_subjects(tmp_db, doc_id, [3])  # second call must not duplicate
    count = tmp_db.execute(
        "SELECT COUNT(*) FROM document_politicians WHERE document_id=? AND politician_id=3",
        (doc_id,),
    ).fetchone()[0]
    assert count == 1
