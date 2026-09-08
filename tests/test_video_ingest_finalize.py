import json
import sqlite3
from pathlib import Path
import pytest

from src.video_ingest.finalize import (
    build_labelled_transcript, validate_speakers, finalize_to_db,
)


def test_build_labelled_transcript_basic():
    aligned = [
        {"start": 0.0, "end": 2.0, "speaker": "A", "text": "Sveicināti."},
        {"start": 2.0, "end": 5.0, "speaker": "B", "text": "Paldies, vadītāj."},
    ]
    speakers = {
        "A": {"pid": None, "handle": "host"},
        "B": {"pid": 3, "handle": "SlesersAinars"},
    }
    md = build_labelled_transcript(aligned, speakers)
    assert "[00:00] @host: Sveicināti." in md
    assert "[00:02] @SlesersAinars: Paldies, vadītāj." in md


def test_validate_speakers_rejects_missing_pid(tmp_path):
    db = sqlite3.connect(":memory:")
    db.executescript("""
        CREATE TABLE tracked_politicians (id INTEGER PRIMARY KEY, relationship_type TEXT);
        INSERT INTO tracked_politicians VALUES (3, 'tracked');
    """)
    speakers = {
        "A": {"pid": 999, "handle": "ghost"},
    }
    with pytest.raises(ValueError) as exc:
        validate_speakers(speakers, db)
    assert "999" in str(exc.value)


def test_validate_speakers_rejects_inactive(tmp_path):
    db = sqlite3.connect(":memory:")
    db.executescript("""
        CREATE TABLE tracked_politicians (id INTEGER PRIMARY KEY, relationship_type TEXT);
        INSERT INTO tracked_politicians VALUES (5, 'inactive');
    """)
    speakers = {"A": {"pid": 5, "handle": "x"}}
    with pytest.raises(ValueError) as exc:
        validate_speakers(speakers, db)
    assert "inactive" in str(exc.value).lower()


def test_validate_speakers_accepts_null_pid(tmp_path):
    db = sqlite3.connect(":memory:")
    db.executescript("CREATE TABLE tracked_politicians (id INTEGER PRIMARY KEY, relationship_type TEXT);")
    speakers = {"A": {"pid": None, "handle": "host"}}
    validate_speakers(speakers, db)  # no raise


def test_finalize_idempotence(tmp_path, monkeypatch):
    """Running finalize twice on the same workspace yields one document row."""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "metadata.json").write_text(json.dumps({
        "url": "https://www.youtube.com/watch?v=abc",
        "title": "Test",
        "uploader": "Test",
        "published_at": "2026-04-15",
        "language": "lv",
        "duration_seconds": 60,
        "source_domain": "youtube.com",
    }), encoding="utf-8")
    (workspace / "aligned.json").write_text(json.dumps([
        {"start": 0.0, "end": 2.0, "speaker": "A", "text": "Sveiki."},
    ]), encoding="utf-8")
    (workspace / "speakers.json").write_text(json.dumps({
        "A": {"pid": None, "handle": "host", "confidence": 0.7, "evidence": "first speaker"},
    }), encoding="utf-8")
    (workspace / "audio.wav").write_bytes(b"fake")

    db = sqlite3.connect(":memory:")
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
        CREATE TABLE tracked_politicians (id INTEGER PRIMARY KEY, relationship_type TEXT);
    """)
    db.commit()

    doc_id_1 = finalize_to_db(workspace, db)
    doc_id_2 = finalize_to_db(workspace, db)
    assert doc_id_1 == doc_id_2

    rows = db.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    assert rows == 1

    # audio.wav deleted after first finalize
    assert not (workspace / "audio.wav").exists()
    # labelled_transcript.md created
    assert (workspace / "labelled_transcript.md").exists()
