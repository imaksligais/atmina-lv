"""Landing «/ 7d» windows must span exactly 7 calendar days (today-6 … today).

Failure (2026-09-28): ``today - timedelta(days=7)`` with ``stated_at >= cutoff``
counted EIGHT calendar days, so «+N / 7d», «Šonedēļ … jaunas pozīcijas»,
«balsojumi» and «Visaktīvākie (7 dienās)» all over-counted by one day, while
the contradiction count beside them (``series[-7:]``) already used 7.
"""

from __future__ import annotations

import os
import tempfile
from datetime import timedelta

import pytest

from src.db import get_db, init_db, today_lv
from src.saeima.schema import init_saeima_tables


def _day(n: int) -> str:
    return (today_lv() - timedelta(days=n)).isoformat()


@pytest.fixture
def db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    init_saeima_tables(path)
    conn = get_db(path)
    conn.execute(
        "INSERT INTO tracked_politicians (id, name, relationship_type) VALUES (1, 'Deputāts', 'tracked')"
    )
    # One claim + one vote on the 7th day back (inside), one on the 8th (outside).
    for i, age in enumerate((6, 7), start=1):
        ts = _day(age) + " 10:00:00"
        conn.execute(
            "INSERT INTO documents (id, source_url, title, content, content_hash, platform, scraped_at) "
            "VALUES (?, ?, 't', 'c', ?, 'web', ?)",
            (i, f"https://example.lv/{i}", f"h{i}", ts),
        )
        conn.execute(
            "INSERT INTO claims (opponent_id, document_id, topic, stance, source_url, stated_at, "
            "created_at, claim_type) VALUES (1, ?, 'Budžets un finanses', 's', ?, ?, ?, 'position')",
            (i, f"https://example.lv/{i}", ts, ts),
        )
        conn.execute(
            "INSERT INTO saeima_votes (id, motif, vote_date, vote_time, total_par, total_pret, "
            "total_atturas, result, url) VALUES (?, 'm', ?, '10:00:00', 1, 0, 0, 'Pieņemts', ?)",
            (i, _day(age), f"u{i}"),
        )
    conn.commit()
    yield conn
    conn.close()
    try:
        os.remove(path)
    except OSError:
        pass


def test_landing_stats_count_seven_calendar_days(db):
    from src.render.dashboard import _fetch_stats

    stats = _fetch_stats(db)
    assert stats["claims_7d"] == 1  # 6 days old counted, 7 days old not
    assert stats["votes_7d"] == 1


def test_most_active_7d_uses_the_same_window(db):
    from src.render.rankings import _most_active_7d

    rows = _most_active_7d(db, 5)
    assert [(r["name"], r["count"]) for r in rows] == [("Deputāts", 1)]


def test_contradiction_series_window_is_also_seven_days(db):
    """The neighbouring «jaunas pretrunas» count sums ``series[-7:]``; a
    contradiction detected 7 days ago must stay outside it too."""
    from src.render.dashboard import _fetch_hero_v2_data

    for i, age in enumerate((6, 7), start=1):
        db.execute(
            "INSERT INTO contradictions (id, opponent_id, topic, summary, severity, detected_at, confirmed) "
            "VALUES (?, 1, 't', 's', 'minor_shift', ?, 1)",
            (i, _day(age) + " 10:00:00"),
        )
    db.commit()
    assert _fetch_hero_v2_data(db)["contradictions_7d"] == 1
