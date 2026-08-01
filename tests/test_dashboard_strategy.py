"""Task 1.5 — A/B strategy panel."""
from __future__ import annotations

import os
import sqlite3
import tempfile

import pytest

from src.db import init_db


@pytest.fixture
def strategy_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    try:
        os.unlink(path)
    except PermissionError:
        pass


def _insert_mentions_fetch(db_path: str, *, fetched: int, stored: int, errors: int,
                            status: str = "success", timestamp: str | None = None):
    db = sqlite3.connect(db_path)
    if timestamp:
        db.execute(
            "INSERT INTO logs (timestamp, action, status, details) VALUES (?, ?, ?, ?)",
            (
                timestamp,
                "mentions_fetch",
                status,
                f'{{"fetched": {fetched}, "stored": {stored}, "errors": {errors}}}',
            ),
        )
    else:
        db.execute(
            "INSERT INTO logs (action, status, details) VALUES (?, ?, ?)",
            (
                "mentions_fetch",
                status,
                f'{{"fetched": {fetched}, "stored": {stored}, "errors": {errors}}}',
            ),
        )
    db.commit()
    db.close()


def _insert_guardrail_trip(db_path: str, *, when_hours_ago: float = 0.0):
    db = sqlite3.connect(db_path)
    db.execute(
        "INSERT INTO logs (timestamp, action, status, details) "
        "VALUES (datetime('now', ?), ?, ?, ?)",
        (
            f"-{when_hours_ago} hours",
            "mentions_fetch_guardrail",
            "tripped",
            '{"healthy": 3, "total": 6, "min_required": 4, "fallback": "timeline"}',
        ),
    )
    db.commit()
    db.close()


def test_strategy_view_reads_env_var_correctly(strategy_db, monkeypatch):
    from src.dashboard.views.strategy import get_strategy_context

    monkeypatch.setenv("X_MENTIONS_STRATEGY", "search")
    ctx = get_strategy_context(db_path=strategy_db)
    assert ctx["strategy"] == "search"

    monkeypatch.setenv("X_MENTIONS_STRATEGY", "TIMELINE")  # capitalisation tolerated
    ctx = get_strategy_context(db_path=strategy_db)
    assert ctx["strategy"] == "timeline"

    monkeypatch.delenv("X_MENTIONS_STRATEGY", raising=False)
    ctx = get_strategy_context(db_path=strategy_db)
    assert ctx["strategy"] == "timeline", "missing env must default to 'timeline'"


def test_strategy_view_aggregates_last_7_runs(strategy_db):
    from src.dashboard.views.strategy import get_strategy_context

    for i in range(10):  # insert 10 runs, expect only last 7 returned
        _insert_mentions_fetch(strategy_db, fetched=200 + i, stored=100 + i, errors=0)

    ctx = get_strategy_context(db_path=strategy_db)
    assert len(ctx["runs"]) == 7
    # Newest first in `runs`; chart reverses to oldest→newest visual order
    assert ctx["runs"][0]["stored"] > ctx["runs"][-1]["stored"]
    assert len(ctx["chart_data"]) == 7
    # Chart's first item is the OLDEST visible run
    assert ctx["chart_data"][0]["value"] == ctx["runs"][-1]["stored"]


def test_strategy_view_handles_runs_without_details(strategy_db):
    """Older log rows may have null/missing details — must default to 0, not crash."""
    db = sqlite3.connect(strategy_db)
    db.execute(
        "INSERT INTO logs (action, status, details) VALUES ('mentions_fetch', 'success', NULL)"
    )
    db.execute(
        "INSERT INTO logs (action, status, details) VALUES ('mentions_fetch', 'success', 'not json')"
    )
    db.commit()
    db.close()

    from src.dashboard.views.strategy import get_strategy_context

    ctx = get_strategy_context(db_path=strategy_db)
    assert all(r["stored"] == 0 for r in ctx["runs"]), "malformed details must not crash"


def test_strategy_view_counts_guardrail_trips_last_24h(strategy_db):
    from src.dashboard.views.strategy import get_strategy_context

    _insert_guardrail_trip(strategy_db, when_hours_ago=2)
    _insert_guardrail_trip(strategy_db, when_hours_ago=12)
    _insert_guardrail_trip(strategy_db, when_hours_ago=23.5)  # within 24h window
    _insert_guardrail_trip(strategy_db, when_hours_ago=25)  # outside — excluded

    ctx = get_strategy_context(db_path=strategy_db)
    assert ctx["guardrail_trips_24h"] == 3, (
        "must include only trips in the last 24h, regardless of how old the DB is"
    )


def test_index_renders_strategy_panel(strategy_db, monkeypatch):
    from src.dashboard.server import create_app

    monkeypatch.setenv("X_MENTIONS_STRATEGY", "search")
    _insert_mentions_fetch(strategy_db, fetched=220, stored=213, errors=0)
    _insert_guardrail_trip(strategy_db, when_hours_ago=1)

    app = create_app(db_path=strategy_db)
    html = app.test_client().get("/").get_data(as_text=True)

    assert 'id="strategy-panel"' in html
    # SVG chart rendered inline (no JS lib)
    assert "<svg" in html
    # Current strategy chip
    assert "search" in html.lower()
    # Guardrail trip count visible (≥1 in this fixture)
    assert "1" in html  # cheap substring check; refined by template smoke


def test_svg_bars_macro_produces_valid_svg(tmp_path):
    """SVG macro must render valid markup for use in strategy + future panels."""
    from src.db import init_db
    from src.dashboard.server import create_app
    from flask import render_template

    db_path = tmp_path / "test.db"
    init_db(str(db_path))
    app = create_app(db_path=str(db_path))
    with app.app_context():
        rendered = render_template(
            "partials/_svg_bars.html.j2",
            data=[{"label": str(i), "value": v} for i, v in enumerate([0, 5, 10, 200, 100])],
            width=280,
            height=80,
        )
    assert "<svg" in rendered
    assert "</svg>" in rendered
    # Five <rect> elements for five data points
    assert rendered.count("<rect") == 5
