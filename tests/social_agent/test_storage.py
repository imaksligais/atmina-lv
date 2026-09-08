import json
import os
import tempfile

import pytest

from src.db import init_db, get_db
from src.social_agent.storage import (
    create_draft,
    get_draft,
    list_pending_drafts,
    mark_approved,
    mark_rejected,
    mark_posted,
    mark_failed,
    mark_revising,
)


@pytest.fixture
def fresh_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    try:
        os.unlink(path)
    except OSError:
        pass


def test_create_draft_inserts_row(fresh_db):
    did = create_draft(
        pillar="pretrunas",
        text="Sample draft",
        image_path="/tmp/x.png",
        source_data={"contradiction_id": 100},
        score=0.87,
        db_path=fresh_db,
    )
    assert isinstance(did, int) and did > 0
    row = get_draft(did, db_path=fresh_db)
    assert row["pillar"] == "pretrunas"
    assert row["status"] == "pending"
    assert row["score"] == 0.87
    assert json.loads(row["source_data_json"])["contradiction_id"] == 100


def test_status_transitions(fresh_db):
    did = create_draft(
        pillar="stats", text="t", image_path=None, source_data={}, score=0.5, db_path=fresh_db
    )
    mark_approved(did, db_path=fresh_db)
    assert get_draft(did, db_path=fresh_db)["status"] == "approved"
    mark_posted(did, tweet_id="12345", db_path=fresh_db)
    row = get_draft(did, db_path=fresh_db)
    assert row["status"] == "posted"
    assert row["tweet_id"] == "12345"
    assert row["posted_at"] is not None


def test_mark_failed_records_error(fresh_db):
    did = create_draft(
        pillar="highlights", text="t", image_path=None, source_data={}, score=0.5, db_path=fresh_db
    )
    mark_failed(did, error_message="rate limit", db_path=fresh_db)
    row = get_draft(did, db_path=fresh_db)
    assert row["status"] == "failed"
    assert row["error_message"] == "rate limit"


def test_list_pending_drafts_returns_only_pending(fresh_db):
    ids = [
        create_draft(pillar="pretrunas", text=f"t{i}", image_path=None,
                     source_data={}, score=0.5, db_path=fresh_db)
        for i in range(3)
    ]
    mark_rejected(ids[0], db_path=fresh_db)
    pending = list_pending_drafts(db_path=fresh_db)
    pending_ids = {r["id"] for r in pending}
    assert ids[0] not in pending_ids
    assert ids[1] in pending_ids
    assert ids[2] in pending_ids


def test_mark_revising_creates_child_draft(fresh_db):
    parent_id = create_draft(
        pillar="pretrunas", text="original", image_path=None,
        source_data={"contradiction_id": 100}, score=0.8, db_path=fresh_db
    )
    child_id = mark_revising(parent_id, new_text="shorter", db_path=fresh_db)
    parent = get_draft(parent_id, db_path=fresh_db)
    child = get_draft(child_id, db_path=fresh_db)
    assert parent["status"] == "revising"
    assert child["parent_draft_id"] == parent_id
    assert child["revision_count"] == 1
    assert child["text"] == "shorter"
    assert child["status"] == "pending"
