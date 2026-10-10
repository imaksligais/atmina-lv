import os
import tempfile
from unittest.mock import patch

import pytest

from src.db import init_db
from src.social_agent import cli
from src.social_agent.storage import create_draft, get_draft


@pytest.fixture
def fresh_db(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    try:
        os.unlink(path)
    except OSError:
        pass


def test_approve_cmd_posts_and_marks(fresh_db):
    did = create_draft(
        pillar="pretrunas", text="t", image_path=None,
        source_data={}, score=0.8, db_path=fresh_db,
    )
    with patch("src.social_agent.cli.publish_draft", return_value="tw-42"):
        rc = cli.approve_cmd(did, db_path=fresh_db)
    assert rc == 0
    row = get_draft(did, db_path=fresh_db)
    assert row["status"] == "posted"
    assert row["tweet_id"] == "tw-42"


def test_approve_cmd_marks_failed_on_error(fresh_db):
    did = create_draft(
        pillar="pretrunas", text="t", image_path=None,
        source_data={}, score=0.8, db_path=fresh_db,
    )
    with patch("src.social_agent.cli.publish_draft", side_effect=RuntimeError("boom")):
        rc = cli.approve_cmd(did, db_path=fresh_db)
    assert rc != 0
    row = get_draft(did, db_path=fresh_db)
    assert row["status"] == "failed"
    assert "boom" in row["error_message"]


def test_skip_cmd(fresh_db):
    did = create_draft(
        pillar="stats", text="t", image_path=None,
        source_data={}, score=0.5, db_path=fresh_db,
    )
    rc = cli.skip_cmd(did, db_path=fresh_db)
    assert rc == 0
    assert get_draft(did, db_path=fresh_db)["status"] == "rejected"


def test_revise_cmd_creates_child_and_sends(fresh_db):
    did = create_draft(
        pillar="pretrunas", text="original long version",
        image_path=None, source_data={"contradiction_id": 100}, score=0.8,
        db_path=fresh_db,
    )
    with patch("src.social_agent.cli.send_draft", return_value="mid-77") as send, \
         patch("src.social_agent.cli.llm_rewrite", return_value="short version") as llm:
        rc = cli.revise_cmd(did, instruction="pārraksti īsāk", db_path=fresh_db)
    assert rc == 0
    llm.assert_called_once()
    send.assert_called_once()
    # Parent is 'revising'; child exists with new text
    parent = get_draft(did, db_path=fresh_db)
    assert parent["status"] == "revising"


def test_main_dispatches_brainstorm():
    with patch("src.social_agent.cli.brainstorm_cmd", return_value=0) as bs:
        cli.main(argv=["brainstorm"])
        bs.assert_called_once()


def test_main_dispatches_approve():
    with patch("src.social_agent.cli.approve_cmd", return_value=0) as ap:
        cli.main(argv=["approve", "42"])
        ap.assert_called_once_with(42)
