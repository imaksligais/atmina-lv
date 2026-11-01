"""Task 1.8 — pending banner + footer + index composition."""
from __future__ import annotations

import os
import sqlite3
import tempfile
from datetime import datetime

import pytest

from src.db import init_db


@pytest.fixture
def pending_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    try:
        os.unlink(path)
    except PermissionError:
        pass


def _seed_brief(db, *, note_id: int, topic: str, ts: str = "2026-04-07 17:00:00"):
    db.execute(
        "INSERT INTO context_notes (id, note_type, topic, content, created_at) "
        "VALUES (?, 'daily_brief', ?, 'c', ?)",
        (note_id, topic, ts),
    )


def _seed_image(db, *, image_id: int, note_id: int, approved: int, cost: float = 0.039,
                ts: str = "2026-04-07 17:30:00"):
    db.execute(
        "INSERT INTO brief_images (id, note_id, image_path, prompt, model, "
        "generated_at, approved, cost_usd) VALUES (?, ?, 'p', 'p', 'gem', ?, ?, ?)",
        (image_id, note_id, ts, approved, cost),
    )


def test_pending_counts_unapproved_images_for_today(pending_db):
    from src.dashboard.views.pending import get_pending_actions

    db = sqlite3.connect(pending_db)
    _seed_brief(db, note_id=1, topic="dienas pārskats 2026-04-07")
    _seed_image(db, image_id=10, note_id=1, approved=0)  # pending
    _seed_image(db, image_id=11, note_id=1, approved=1)  # approved, ignored
    db.commit()
    db.close()

    ctx = get_pending_actions(
        date="2026-04-07",
        db_path=pending_db,
        now=datetime(2026, 4, 7, 18, 0),
    )
    msgs = " | ".join(a["message"] for a in ctx["actions"])
    assert any("image" in a["message"].lower() and "gaida" in a["message"].lower()
               for a in ctx["actions"]), f"missing pending-image action; got: {msgs}"


def test_pending_flags_brief_missing_after_15h(pending_db):
    from src.dashboard.views.pending import get_pending_actions

    ctx = get_pending_actions(
        date="2026-04-07",
        db_path=pending_db,
        now=datetime(2026, 4, 7, 16, 0),
    )
    msgs = [a["message"] for a in ctx["actions"]]
    assert any("brief" in m.lower() for m in msgs), \
        f"missing-brief warning should fire after 15h, got: {msgs}"


def test_pending_skips_brief_warning_before_15h(pending_db):
    from src.dashboard.views.pending import get_pending_actions

    ctx = get_pending_actions(
        date="2026-04-07",
        db_path=pending_db,
        now=datetime(2026, 4, 7, 10, 0),
    )
    msgs = [a["message"] for a in ctx["actions"]]
    assert not any("brief" in m.lower() for m in msgs), (
        "missing-brief is expected in the morning — no warning yet"
    )


def test_pending_flags_slot_health_below_4(pending_db):
    from src.dashboard.views.pending import get_pending_actions

    # Pass slots snapshot directly so we don't need to mock probing
    slots_ctx = {
        "healthy_search_count": 2,
        "total_slots": 6,
        "guardrail_min": 4,
        "guardrail_tripped": True,
    }
    ctx = get_pending_actions(
        date="2026-04-07",
        db_path=pending_db,
        now=datetime(2026, 4, 7, 12, 0),
        slots=slots_ctx,
    )
    msgs = [a["message"] for a in ctx["actions"]]
    assert any("slot" in m.lower() and "2/6" in m for m in msgs)


def test_pending_image_budget_aggregates_current_month(pending_db):
    from src.dashboard.views.pending import get_pending_actions

    db = sqlite3.connect(pending_db)
    _seed_brief(db, note_id=1, topic="t")
    _seed_image(db, image_id=1, note_id=1, approved=1, cost=0.5,
                ts="2026-04-02 10:00:00")
    _seed_image(db, image_id=2, note_id=1, approved=1, cost=0.3,
                ts="2026-04-10 10:00:00")
    _seed_image(db, image_id=3, note_id=1, approved=1, cost=2.0,
                ts="2026-03-15 10:00:00")  # previous month — excluded
    db.commit()
    db.close()

    ctx = get_pending_actions(
        date="2026-04-15",
        db_path=pending_db,
        now=datetime(2026, 4, 15, 12, 0),
    )
    assert ctx["image_budget"]["used_usd"] == pytest.approx(0.8)
    assert ctx["image_budget"]["max_usd"] > 0


def test_banner_hides_when_no_pending(pending_db):
    from src.dashboard.views.pending import get_pending_actions

    db = sqlite3.connect(pending_db)
    # Seed a brief so the "missing brief" warning doesn't fire
    _seed_brief(db, note_id=1, topic="dienas pārskats 2026-04-07")
    _seed_image(db, image_id=1, note_id=1, approved=1)
    db.commit()
    db.close()

    slots_ctx = {"healthy_search_count": 6, "total_slots": 6, "guardrail_tripped": False}
    ctx = get_pending_actions(
        date="2026-04-07",
        db_path=pending_db,
        now=datetime(2026, 4, 7, 18, 0),
        slots=slots_ctx,
    )
    assert ctx["actions"] == []
    assert ctx["count"] == 0


def test_build_sha_returns_short_hash():
    from src.dashboard.views.pending import get_build_sha

    sha = get_build_sha()
    # Real git short-sha is 7+ alnum chars, or fallback "unknown" when git fails
    assert sha == "unknown" or (len(sha) >= 7 and sha.isalnum())


def test_index_renders_banner_and_footer(pending_db):
    """End-to-end: banner appears when pending > 0, footer always present."""
    from src.dashboard.server import create_app

    db = sqlite3.connect(pending_db)
    _seed_brief(db, note_id=1, topic="dienas pārskats 2026-04-07")
    _seed_image(db, image_id=10, note_id=1, approved=0)  # forces pending
    db.commit()
    db.close()

    app = create_app(db_path=pending_db)
    html = app.test_client().get("/").get_data(as_text=True)

    # Footer always renders
    assert "build" in html.lower() or "M1" in html
    # Pending banner: either banner block visible OR pending count in <title>
    assert 'id="pending-banner"' in html
