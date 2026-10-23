import os
import tempfile

import pytest

from src.db import init_db, get_db
from src.social_agent.candidates import fetch_highlights_candidates


@pytest.fixture
def seeded_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    db = get_db(path)
    db.execute("INSERT INTO tracked_politicians (id, name, party) VALUES (1, 'A', 'JV')")
    db.execute("INSERT INTO tracked_politicians (id, name, party) VALUES (2, 'B', 'NA')")
    # A political tension row
    db.execute(
        "INSERT INTO political_tensions (id, source_pid, target_pid, topic, description, "
        "tension_type, created_at) VALUES "
        "(1, 1, 2, 'drošība', 'A uzbrūk B par drošības politiku', 'uzbrukums', datetime('now','-2 days'))"
    )
    db.commit()
    yield path
    db.close()
    try:
        os.unlink(path)
    except OSError:
        pass


def test_fetch_highlights_returns_tensions(seeded_db):
    rows = fetch_highlights_candidates(db_path=seeded_db)
    assert {r["kind"] for r in rows} == {"tension"}

    tension_row = rows[0]
    assert tension_row["source_name"] == "A"
    assert tension_row["target_name"] == "B"
    assert tension_row["topic"] == "drošība"


def test_fetch_highlights_respects_lookback_days(seeded_db):
    rows = fetch_highlights_candidates(db_path=seeded_db, lookback_days=0)
    assert rows == []
