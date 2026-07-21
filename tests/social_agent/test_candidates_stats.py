import os
import tempfile

import pytest

from src.db import init_db, get_db
from src.social_agent.candidates import fetch_stats_candidate


@pytest.fixture
def seeded_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    db = get_db(path)
    # Three politicians
    db.executemany(
        "INSERT INTO tracked_politicians (id, name, party) VALUES (?, ?, ?)",
        [(1, "A", "JV"), (2, "B", "NA"), (3, "C", "ZZS")],
    )
    # Claims within the last 7 days
    db.executemany(
        "INSERT INTO claims (opponent_id, topic, stance, quote, stated_at, claim_type, source_url) "
        "VALUES (?, 'x', 'par', 'q', ?, 'position', ?)",
        [
            (1, "2026-04-18 10:00:00", "https://example.com/1"),
            (1, "2026-04-17 10:00:00", "https://example.com/2"),
            (1, "2026-04-16 10:00:00", "https://example.com/3"),
            (2, "2026-04-18 10:00:00", "https://example.com/4"),
            (2, "2026-04-17 10:00:00", "https://example.com/5"),
            (3, "2026-04-18 10:00:00", "https://example.com/6"),
        ],
    )
    # Old claim that should NOT appear in weekly counts
    db.execute(
        "INSERT INTO claims (opponent_id, topic, stance, quote, stated_at, claim_type, source_url) "
        "VALUES (3, 'x', 'par', 'q', '2026-01-01 10:00:00', 'position', 'https://example.com/old')"
    )
    db.commit()
    yield path
    db.close()
    try:
        os.unlink(path)
    except OSError:
        pass


def test_fetch_stats_candidate_returns_top_politicians(seeded_db):
    result = fetch_stats_candidate(db_path=seeded_db, now_iso="2026-04-19 12:00:00")
    assert result is not None
    leaders = result["leaderboard"]
    # Must be sorted desc by count
    assert [l["name"] for l in leaders[:3]] == ["A", "B", "C"]
    assert leaders[0]["count"] == 3
    assert leaders[1]["count"] == 2
    assert leaders[2]["count"] == 1
    assert result["iso_week"] == "2026-W16"  # 2026-04-19 is in ISO week 16


def test_fetch_stats_candidate_skip_if_week_already_posted(seeded_db):
    db = get_db(seeded_db)
    db.execute(
        "INSERT INTO social_drafts (pillar, text, source_data_json, score, status) "
        "VALUES ('stats', 't', '{\"iso_week\": \"2026-W16\"}', 0.8, 'posted')"
    )
    db.commit()
    db.close()
    result = fetch_stats_candidate(db_path=seeded_db, now_iso="2026-04-19 12:00:00")
    assert result is None


def test_fetch_stats_candidate_excludes_audience_accounts():
    """Journalists / influencers / neutral accounts must not appear in the leaderboard.

    Matches brief-writer convention (CLAUDE.md): these relationship_types are tracked
    for document linking but excluded from activity rankings.
    """
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    db = get_db(path)
    db.executemany(
        "INSERT INTO tracked_politicians (id, name, party, relationship_type) VALUES (?, ?, ?, ?)",
        [
            (1, "Politiķis", "JV", "tracked"),
            (2, "Žurnālists", None, "journalist"),
            (3, "Influencers", None, "influencer"),
            (4, "Neitrāls", None, "neutral"),
            (5, "Pensionēts", "JV", "inactive"),
        ],
    )
    db.executemany(
        "INSERT INTO claims (opponent_id, topic, stance, quote, stated_at, claim_type, source_url) "
        "VALUES (?, 'x', 'par', 'q', ?, 'position', ?)",
        [
            (1, "2026-04-18 10:00:00", "https://example.com/pol"),
            (2, "2026-04-18 10:00:00", "https://example.com/jrn"),
            (3, "2026-04-18 10:00:00", "https://example.com/inf"),
            (4, "2026-04-18 10:00:00", "https://example.com/neu"),
            (5, "2026-04-18 10:00:00", "https://example.com/ina"),
        ],
    )
    db.commit()
    db.close()
    result = fetch_stats_candidate(db_path=path, now_iso="2026-04-19 12:00:00")
    assert result is not None
    names = [l["name"] for l in result["leaderboard"]]
    assert names == ["Politiķis"], f"unexpected leaderboard: {names}"
    try:
        os.unlink(path)
    except OSError:
        pass
