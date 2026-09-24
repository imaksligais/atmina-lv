import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from src.db import init_db
from src.social_agent import cli


@pytest.fixture
def fresh_db(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    monkeypatch.setattr("src.social_agent.storage.DB_PATH", path, raising=False)
    monkeypatch.setattr("src.social_agent.candidates.DB_PATH", path, raising=False)
    yield path
    try:
        os.unlink(path)
    except OSError:
        pass


def test_brainstorm_empty_db_exits_cleanly(fresh_db, capsys):
    with patch("src.social_agent.cli.send_draft") as send:
        rc = cli.brainstorm_cmd(db_path=fresh_db)
    assert rc == 0
    send.assert_not_called()
    out = capsys.readouterr().out
    assert "No candidates" in out or "nav kandidātu" in out.lower()


def test_brainstorm_with_seeded_contradictions_sends_drafts(fresh_db):
    # Seed one contradiction
    from src.db import get_db
    db = get_db(fresh_db)
    db.execute("INSERT INTO tracked_politicians (id, name, party) VALUES (1, 'X', 'JV')")
    db.execute(
        "INSERT INTO claims (id, opponent_id, topic, stance, quote, stated_at, source_url) "
        "VALUES (10, 1, 't', 'par', 'A', '2026-04-01', 'u1'), "
        "       (11, 1, 't', 'pret', 'B', '2026-04-18', 'u2')"
    )
    db.execute(
        "INSERT INTO contradictions (id, opponent_id, claim_old_id, claim_new_id, topic, "
        "summary, severity, salience, detected_at) "
        "VALUES (100, 1, 10, 11, 't', 's', 'critical', 0.9, '2026-04-18 10:00:00')"
    )
    db.commit()
    db.close()

    with patch("src.social_agent.cli.send_draft", return_value="777") as send, \
         patch("src.social_agent.cli.render_quote_card") as qc, \
         patch("src.social_agent.cli.render_chart"), \
         patch("src.social_agent.cli.render_illustration"):
        qc.side_effect = lambda payload, out_path: out_path.parent.mkdir(
            parents=True, exist_ok=True
        ) or out_path.write_bytes(b"PNG") or out_path
        rc = cli.brainstorm_cmd(db_path=fresh_db)
    assert rc == 0
    assert send.call_count == 1
