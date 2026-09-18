"""Task 1.3 — routine panel view wrapper + partial smoke."""
from __future__ import annotations

import os
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from src.db import init_db


@pytest.fixture
def empty_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    try:
        os.unlink(path)
    except PermissionError:
        pass


def test_routine_view_passes_through_to_check_routine(empty_db):
    from src.dashboard.views.routine import get_routine_context

    ctx = get_routine_context(
        date="2026-04-07",
        db_path=empty_db,
        now=datetime(2026, 4, 7, 10, 0),
    )
    assert ctx["date"] == "2026-04-07"
    assert "steps" in ctx
    # Step list view must preserve insertion order from check_routine
    assert list(ctx["steps"].keys())[0] == "ingest"


def test_routine_view_includes_step_labels_and_icons(empty_db):
    from src.dashboard.views.routine import get_routine_context

    ctx = get_routine_context(
        date="2026-04-07",
        db_path=empty_db,
        now=datetime(2026, 4, 7, 10, 0),
    )
    # Each step augmented with `label` (LV human-readable) + `icon` (glyph)
    for key, step in ctx["steps"].items():
        assert "label" in step, f"step {key} missing label"
        assert "icon" in step, f"step {key} missing icon"
        assert "status" in step
    # Waiting glyph must be distinguishable from missing/done
    assert ctx["steps"]["daily_brief"]["status"] == "waiting"
    assert ctx["steps"]["daily_brief"]["icon"] not in ("✓", "✗")


def test_index_renders_routine_panel_with_all_steps(empty_db):
    from src.dashboard.server import create_app

    app = create_app(db_path=empty_db)
    html = app.test_client().get("/").get_data(as_text=True)
    # Panel ID must be present
    assert 'id="routine-panel"' in html
    # All 10 step labels render somewhere in the page (loose substring check)
    for token in ("Ielāde", "analīze", "Pretrunu", "pārskats", "Wiki"):
        assert token in html, f"missing routine step label fragment: {token}"


def test_index_routine_shows_waiting_chip_in_morning(empty_db, monkeypatch):
    """When current time is before 15:00 LV, daily_brief must surface 'waiting',
    not 'missing'. Tested end-to-end through the index template."""
    from src.dashboard.views import routine as routine_view
    from src.dashboard.server import create_app

    monkeypatch.setattr(
        routine_view, "_default_now", lambda: datetime(2026, 4, 7, 10, 0)
    )
    monkeypatch.setattr(
        routine_view, "today_lv", lambda: __import__("datetime").date(2026, 4, 7)
    )

    app = create_app(db_path=empty_db)
    html = app.test_client().get("/").get_data(as_text=True)
    # "waiting" status renders distinctive glyph (hourglass) and LV detail copy
    assert "gaida pēcpusdienu" in html or "Gaida" in html or "⏳" in html
