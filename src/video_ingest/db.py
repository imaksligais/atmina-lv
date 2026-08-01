"""SQL helpers for video document persistence."""
from __future__ import annotations

import sqlite3

from src.db import now_lv


def find_existing_by_hash(db: sqlite3.Connection, content_hash: str) -> int | None:
    row = db.execute(
        "SELECT id FROM documents WHERE content_hash = ?",
        (content_hash,),
    ).fetchone()
    return row[0] if row else None


def insert_video_document(
    db: sqlite3.Connection,
    *, content: str, content_hash: str, simhash: int,
    source_url: str, source_domain: str, title: str,
    published_at: str, archive_path: str, word_count: int, summary: str,
    language: str = "lv",
) -> int:
    """Insert a row with platform='video'. Returns inserted document_id."""
    cur = db.execute(
        """
        INSERT INTO documents (
            content, content_hash, simhash,
            source_id, platform, is_auto_caption, near_dupe_of,
            source_domain, source_url, archive_path,
            scraped_at, word_count, language, published_at,
            is_paywall, summary, title, reviewed_at,
            reply_count, retweet_count, favorite_count
        ) VALUES (?, ?, ?, ?, 'video', 0, NULL, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, NULL, NULL, NULL, NULL)
        """,
        (
            content, content_hash, simhash,
            None,                              # source_id
            source_domain, source_url, archive_path,
            now_lv(), word_count, language, published_at,
            summary, title,
        ),
    )
    db.commit()
    return cur.lastrowid


def link_subjects(db: sqlite3.Connection, document_id: int, pids: list[int]) -> None:
    for pid in set(pids):
        db.execute(
            "INSERT OR IGNORE INTO document_politicians (document_id, politician_id, role) "
            "VALUES (?, ?, 'subject')",
            (document_id, pid),
        )
    db.commit()
