"""Blog posts (homepage «Jaunākie pārskati», blog index) are ordered by the
brief's CONTENT date, never by `created_at`.

2026-09-14: a factual correction to the published 09-08 and 09-10 dailies went
through the `store_context_note()` UPSERT, which refreshes `created_at` — and
the homepage grid, ordered by `created_at DESC`, promoted both corrected old
dailies above the 09-13 daily and pushed the freshly published weekly brief to
the third slot. A brief's identity is its subject date (CLAUDE.md § Schema
invariants); the listing order must follow the same identity. Weekly briefs
sort by their week END (the range's last day) and win a tie against the daily
for that day, because they are published after it and cover it.
"""

from __future__ import annotations

import os
import sqlite3
import tempfile


def _fixture() -> str:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE documents (id INTEGER PRIMARY KEY, scraped_at TEXT, platform TEXT, source_domain TEXT);
        CREATE TABLE tracked_politicians (id INTEGER PRIMARY KEY, name TEXT, party TEXT, relationship_type TEXT);
        CREATE TABLE claims (id INTEGER PRIMARY KEY, opponent_id INTEGER, document_id INTEGER, topic TEXT, stance TEXT,
                             source_url TEXT, stated_at TEXT, claim_type TEXT NOT NULL DEFAULT 'position');
        CREATE TABLE contradictions (id INTEGER PRIMARY KEY, opponent_id INTEGER, detected_at TEXT, confirmed INTEGER);
        CREATE TABLE saeima_votes (id INTEGER PRIMARY KEY, motif TEXT, vote_date TEXT);
        CREATE TABLE brief_images (id INTEGER PRIMARY KEY, note_id INTEGER, image_path TEXT, approved INTEGER);
        CREATE TABLE context_notes (id INTEGER PRIMARY KEY, opponent_id INTEGER, topic TEXT, note_type TEXT,
                                    content TEXT, source TEXT, created_at TEXT, expires_at TEXT,
                                    visual_brief_json TEXT);
        -- 09-12 daily, written on its day
        INSERT INTO context_notes (id, topic, note_type, content, created_at) VALUES
          (1, 'dienas analīze 2026-09-12', 'daily_brief', '# Dienas analīze — 2026-09-12' || char(10) || 'x', '2026-09-12 22:00:00');
        -- 09-13 daily, written on its day
        INSERT INTO context_notes (id, topic, note_type, content, created_at) VALUES
          (2, 'dienas analīze 2026-09-13', 'daily_brief', '# Dienas analīze — 2026-09-13' || char(10) || 'x', '2026-09-13 21:25:00');
        -- weekly 09-07..09-13, published the morning after
        INSERT INTO context_notes (id, topic, note_type, content, created_at) VALUES
          (3, 'nedēļas analīze 2026-09-07 līdz 2026-09-13', 'weekly_brief',
           '# Nedēļas analīze — 2026-09-07 līdz 2026-09-13' || char(10) || 'x', '2026-09-14 00:04:00');
        -- 09-08 daily CORRECTED on 09-14 → created_at is the newest of all
        INSERT INTO context_notes (id, topic, note_type, content, created_at) VALUES
          (4, 'dienas analīze 2026-09-08', 'daily_brief', '# Dienas analīze — 2026-09-08' || char(10) || 'x', '2026-09-14 07:20:00');
        """
    )
    db.commit()
    db.close()
    return path


def _slugs():
    from src.render.blog import _fetch_blog_posts

    path = _fixture()
    try:
        db = sqlite3.connect(path)
        db.row_factory = sqlite3.Row
        posts = _fetch_blog_posts(db)
        db.close()
    finally:
        os.unlink(path)
    return [p["slug"] for p in posts]


def test_corrected_old_daily_does_not_jump_to_the_top():
    slugs = _slugs()
    assert slugs[-1] == "2026-09-08", slugs
    assert slugs.index("2026-09-13") < slugs.index("2026-09-12") < slugs.index("2026-09-08"), slugs


def test_weekly_sorts_by_week_end_and_wins_the_tie_with_that_days_daily():
    slugs = _slugs()
    assert slugs[:2] == ["nedela-2026-09-07", "2026-09-13"], slugs
