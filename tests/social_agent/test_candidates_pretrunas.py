import os
import tempfile

import pytest

from src.db import init_db, get_db
from src.social_agent.candidates import fetch_pretrunas_candidates


@pytest.fixture
def seeded_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    db = get_db(path)
    # Politician
    db.execute(
        "INSERT INTO tracked_politicians (id, name, party) VALUES (1, 'A Kariņš', 'JV')"
    )
    # Two claims (old + new) forming a contradiction
    db.execute(
        "INSERT INTO claims (id, opponent_id, topic, stance, quote, stated_at, source_url) "
        "VALUES (10, 1, 'budget', 'pret', 'Nekad', '2026-03-01', 'https://example.com/1'), "
        "       (11, 1, 'budget', 'par', 'Jā', '2026-04-15', 'https://example.com/2')"
    )
    db.execute(
        "INSERT INTO contradictions (id, opponent_id, claim_old_id, claim_new_id, topic, "
        "summary, severity, salience, detected_at) VALUES "
        "(100, 1, 10, 11, 'budget', 'Reverse position', 'critical', 0.9, '2026-04-18 10:00:00')"
    )
    # Minor-severity contradiction should also be returned but sorted lower
    db.execute(
        "INSERT INTO claims (id, opponent_id, topic, stance, quote, stated_at, source_url) "
        "VALUES (20, 1, 'health', 'par', 'Jā', '2026-02-01', 'https://example.com/3'), "
        "       (21, 1, 'health', 'pret', 'Nē', '2026-04-17', 'https://example.com/4')"
    )
    db.execute(
        "INSERT INTO contradictions (id, opponent_id, claim_old_id, claim_new_id, topic, "
        "summary, severity, salience, detected_at) VALUES "
        "(101, 1, 20, 21, 'health', 'minor flip', 'minor', 0.4, '2026-04-16 10:00:00')"
    )
    db.commit()
    yield path
    db.close()
    try:
        os.unlink(path)
    except OSError:
        pass


def test_fetch_pretrunas_returns_hydrated_rows(seeded_db):
    rows = fetch_pretrunas_candidates(db_path=seeded_db)
    assert len(rows) == 2
    row = next(r for r in rows if r["contradiction_id"] == 100)
    assert row["politician_name"] == "A Kariņš"
    assert row["topic"] == "budget"
    assert row["severity"] == "critical"
    assert row["salience"] == 0.9
    assert row["old_quote"] == "Nekad"
    assert row["new_quote"] == "Jā"
    assert row["old_stated_at"] == "2026-03-01"
    assert row["new_stated_at"] == "2026-04-15"


def test_fetch_pretrunas_excludes_already_posted(seeded_db):
    db = get_db(seeded_db)
    # Mark contradiction 100 as posted
    db.execute(
        "INSERT INTO social_drafts (pillar, text, source_data_json, score, status) "
        "VALUES ('pretrunas', 't', '{\"contradiction_id\": 100}', 0.8, 'posted')"
    )
    db.commit()
    db.close()
    rows = fetch_pretrunas_candidates(db_path=seeded_db)
    ids = {r["contradiction_id"] for r in rows}
    assert 100 not in ids
    assert 101 in ids
