"""P1 site-perf: cap the inline per-deputy Saeima vote ledger.

The Saeimā tab rendered one <tr> per individual vote with NO limit (up to
~5700 rows on active deputies) — ~82% of each heavy deputy page, ~105 MB
site-wide. `_fetch_politician_detail` now caps the inline list at
VOTE_DISPLAY_CAP most-recent rows and exposes `votes_total` (the true count)
so the profile stat chip stays honest and the template can link the full
history to the filterable Balsojumu matrica (balsojumi.html).
"""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta


def _db_with_votes(tmp_path, pid: int, n_votes: int):
    from src.db import init_db, get_db

    db_path = str(tmp_path / "atmina.db")
    init_db(db_path)
    db = get_db(db_path)
    db.executescript(
        "CREATE TABLE IF NOT EXISTS saeima_individual_votes ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, vote_id INTEGER, politician_id INTEGER, vote TEXT);"
        "CREATE TABLE IF NOT EXISTS saeima_votes ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, motif TEXT, vote_date TEXT, vote_time TEXT, result TEXT, topic TEXT, url TEXT);"
    )
    # x_handle is a live ad-hoc migration absent from init_db's schema; the
    # commentary subquery in _fetch_politician_detail selects it.
    try:
        db.execute("ALTER TABLE tracked_politicians ADD COLUMN x_handle TEXT")
    except sqlite3.OperationalError:
        pass
    db.execute("INSERT INTO tracked_politicians (id, name) VALUES (?, ?)", (pid, "Deputāts Test"))
    base = date(2026, 1, 1)
    for i in range(n_votes):
        vd = (base + timedelta(days=i)).isoformat()  # vote i+(n-1) is newest
        db.execute(
            "INSERT INTO saeima_votes (motif, vote_date, vote_time, result) VALUES (?, ?, ?, ?)",
            (f"Jautājums {i}", vd, "10:00", "Pieņemts"),
        )
        vote_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.execute(
            "INSERT INTO saeima_individual_votes (vote_id, politician_id, vote) VALUES (?, ?, ?)",
            (vote_id, pid, "Par"),
        )
    db.commit()
    return db


def test_vote_ledger_capped_and_total_preserved(tmp_path):
    from src.render.politicians import _fetch_politician_detail, VOTE_DISPLAY_CAP

    db = _db_with_votes(tmp_path, pid=900, n_votes=150)
    try:
        detail = _fetch_politician_detail(db, 900)
    finally:
        db.close()

    assert detail["votes_total"] == 150, "stat chip must reflect the TRUE vote count"
    assert len(detail["votes"]) == VOTE_DISPLAY_CAP == 100, "inline ledger capped"
    dates = [v["vote_date"] for v in detail["votes"]]
    assert dates == sorted(dates, reverse=True), "newest-first ordering preserved"
    assert dates[0] == (date(2026, 1, 1) + timedelta(days=149)).isoformat(), (
        "cap keeps the most-recent votes, not the oldest"
    )


def test_vote_ledger_below_cap_unchanged(tmp_path):
    """A non-deputy / light voter (< cap) keeps every row; total == shown."""
    from src.render.politicians import _fetch_politician_detail

    db = _db_with_votes(tmp_path, pid=901, n_votes=30)
    try:
        detail = _fetch_politician_detail(db, 901)
    finally:
        db.close()

    assert detail["votes_total"] == 30
    assert len(detail["votes"]) == 30, "below cap → all rows, byte-identical to pre-change"


def test_vote_ledger_zero_votes(tmp_path):
    from src.render.politicians import _fetch_politician_detail

    db = _db_with_votes(tmp_path, pid=902, n_votes=0)
    try:
        detail = _fetch_politician_detail(db, 902)
    finally:
        db.close()
    assert detail["votes_total"] == 0
    assert detail["votes"] == []
