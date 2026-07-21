import json
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
    # strongest_attacks JSON from oppo_briefs
    attacks = json.dumps([
        {"text": "A ir pretrunā pats ar sevi par budžetu"},
        {"text": "A maina viedokli par drošību"},
    ], ensure_ascii=False)
    db.execute(
        "INSERT INTO oppo_briefs (id, opponent_id, strongest_attacks, period_start, period_end, created_at) "
        "VALUES (1, 1, ?, '2026-04-12', '2026-04-19', datetime('now','-2 days'))",
        (attacks,),
    )
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


def test_fetch_highlights_returns_attacks_and_tensions(seeded_db):
    rows = fetch_highlights_candidates(db_path=seeded_db)
    kinds = {r["kind"] for r in rows}
    assert kinds == {"attack", "tension"}

    attack_row = next(r for r in rows if r["kind"] == "attack")
    assert attack_row["politician_name"] == "A"
    assert "pretrunā" in attack_row["text"]

    tension_row = next(r for r in rows if r["kind"] == "tension")
    assert tension_row["source_name"] == "A"
    assert tension_row["target_name"] == "B"
    assert tension_row["topic"] == "drošība"


def test_fetch_highlights_respects_lookback_days(seeded_db):
    # Very short lookback → only the 2026-04-19 brief remains (if within window)
    rows = fetch_highlights_candidates(db_path=seeded_db, lookback_days=0)
    assert rows == []
