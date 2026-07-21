"""P1 build-perf: batched daily-brief footer stats (replaces the N+1).

`_fetch_blog_posts` previously ran a 7-subquery footer block per daily brief
(blog.py:197-211), each subquery wrapping date(scraped_at)/date(stated_at)/
date(detected_at) so SQLite could not use an index — 54 briefs over the 33k-row
documents + 514k-row claims tables cost ~12.6s. `_compute_brief_footers(db)`
computes the same counts ONCE via four GROUP BY date(...) scans, keyed by
subject date. This locks per-date keying (a batching bug would cross-contaminate
counts between dates) and the journalist/saeima exclusions.
"""

from __future__ import annotations

import os
import sqlite3
import tempfile


def _two_date_fixture() -> str:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE documents (id INTEGER PRIMARY KEY, scraped_at TEXT, platform TEXT);
        CREATE TABLE tracked_politicians (id INTEGER PRIMARY KEY, name TEXT, party TEXT, relationship_type TEXT);
        CREATE TABLE claims (id INTEGER PRIMARY KEY, opponent_id INTEGER, topic TEXT, stance TEXT,
                             source_url TEXT, stated_at TEXT, claim_type TEXT NOT NULL DEFAULT 'position');
        CREATE TABLE contradictions (id INTEGER PRIMARY KEY, opponent_id INTEGER, detected_at TEXT);
        CREATE TABLE saeima_votes (id INTEGER PRIMARY KEY, vote_date TEXT);

        -- A tracked politician (counts) + a journalist (must be excluded from positions).
        INSERT INTO tracked_politicians VALUES (1, 'Tracked', 'JV', 'tracked');
        INSERT INTO tracked_politicians VALUES (2, 'Journo', NULL, 'journalist');

        -- Date A = 2026-05-01: 2 web + 1 twitter + 1 x_mention (+ 1 'saeima' excluded),
        --   3 tracked positions (+ 1 journalist position excluded), 2 votes, 1 contradiction.
        INSERT INTO documents VALUES (10, '2026-05-01', 'web');
        INSERT INTO documents VALUES (11, '2026-05-01', 'web');
        INSERT INTO documents VALUES (12, '2026-05-01', 'twitter');
        INSERT INTO documents VALUES (13, '2026-05-01', 'x_mention');
        INSERT INTO documents VALUES (14, '2026-05-01', 'saeima');
        INSERT INTO claims (opponent_id, stated_at, claim_type) VALUES (1, '2026-05-01', 'position');
        INSERT INTO claims (opponent_id, stated_at, claim_type) VALUES (1, '2026-05-01', 'position');
        INSERT INTO claims (opponent_id, stated_at, claim_type) VALUES (1, '2026-05-01', 'position');
        INSERT INTO claims (opponent_id, stated_at, claim_type) VALUES (2, '2026-05-01', 'position');
        INSERT INTO saeima_votes (vote_date) VALUES ('2026-05-01'), ('2026-05-01');
        INSERT INTO contradictions (opponent_id, detected_at) VALUES (1, '2026-05-01 09:00:00');

        -- Date B = 2026-05-02: 1 web + 2 x_mention, 1 position, 5 votes, 0 contradictions.
        INSERT INTO documents VALUES (20, '2026-05-02', 'web');
        INSERT INTO documents VALUES (21, '2026-05-02', 'x_mention');
        INSERT INTO documents VALUES (22, '2026-05-02', 'x_mention');
        INSERT INTO claims (opponent_id, stated_at, claim_type) VALUES (1, '2026-05-02', 'position');
        INSERT INTO saeima_votes (vote_date) VALUES
            ('2026-05-02'), ('2026-05-02'), ('2026-05-02'), ('2026-05-02'), ('2026-05-02');
        """
    )
    db.commit()
    db.close()
    return path


def test_compute_brief_footers_keys_counts_per_date():
    from src.render.blog import _compute_brief_footers

    path = _two_date_fixture()
    try:
        db = sqlite3.connect(path)
        db.row_factory = sqlite3.Row
        footers = _compute_brief_footers(db)
        db.close()
    finally:
        os.unlink(path)

    a = footers["2026-05-01"]
    assert a["web"] == 2
    assert a["twitter"] == 1
    assert a["mentions"] == 1
    assert a["doc_count"] == 4, "doc_count = web+twitter+mentions, excludes 'saeima'"
    assert a["positions"] == 3, "journalist position must be excluded"
    assert a["votes"] == 2
    assert a["contradictions"] == 1

    b = footers["2026-05-02"]
    assert b["web"] == 1
    assert b["twitter"] == 0
    assert b["mentions"] == 2
    assert b["doc_count"] == 3
    assert b["positions"] == 1
    assert b["votes"] == 5
    assert b["contradictions"] == 0


def test_compute_brief_footers_unknown_date_absent():
    """A date with no activity is simply absent from the map (caller .get → 0)."""
    from src.render.blog import _compute_brief_footers

    path = _two_date_fixture()
    try:
        db = sqlite3.connect(path)
        db.row_factory = sqlite3.Row
        footers = _compute_brief_footers(db)
        db.close()
    finally:
        os.unlink(path)
    assert "2026-04-30" not in footers
