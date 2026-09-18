"""Task 1.7 — activity timeline (memory layer)."""
from __future__ import annotations

import os
import sqlite3
import tempfile
from datetime import datetime, timedelta

import pytest

from src.db import init_db


@pytest.fixture
def activity_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    try:
        os.unlink(path)
    except PermissionError:
        pass


def _seed_log(db, *, action: str, status: str = "success", details: str | None = None,
              ts: str | None = None):
    if ts:
        db.execute(
            "INSERT INTO logs (timestamp, action, status, details) VALUES (?, ?, ?, ?)",
            (ts, action, status, details),
        )
    else:
        db.execute(
            "INSERT INTO logs (action, status, details) VALUES (?, ?, ?)",
            (action, status, details),
        )


def _seed_context_note(db, *, note_type: str, topic: str, content: str = "x", ts: str):
    db.execute(
        "INSERT INTO context_notes (note_type, topic, content, created_at) VALUES (?, ?, ?, ?)",
        (note_type, topic, content, ts),
    )


def _seed_brief_image(db, *, note_id: int, approved: int, ts: str, image_path: str = "p"):
    db.execute(
        "INSERT INTO brief_images (note_id, image_path, prompt, model, generated_at, "
        "approved, cost_usd) VALUES (?, ?, 'p', 'gem', ?, ?, 0.039)",
        (note_id, image_path, ts, approved),
    )


def _seed_analysis(db, *, opponent_id: int, ts: str):
    db.execute(
        "INSERT INTO analyses (opponent_id, period_start, period_end, sentiment_score, "
        "key_topics, notable_quotes, brief_markdown, confidence, created_at) "
        "VALUES (?, '2026-04-07', '2026-04-07', 0.0, '[]', '[]', 'b', 0.9, ?)",
        (opponent_id, ts),
    )


# --------------------------------------------------------- view helper tests


def test_activity_aggregates_from_4_sources(activity_db):
    from src.dashboard.views.activity import get_activity_context

    db = sqlite3.connect(activity_db)
    _seed_log(db, action="ingest", details='{"documents_stored": 5}', ts="2026-04-07 10:00:00")
    _seed_context_note(db, note_type="daily_brief", topic="dienas pārskats 2026-04-07",
                       ts="2026-04-07 11:00:00")
    _seed_brief_image(db, note_id=1, approved=1, ts="2026-04-07 12:00:00")
    _seed_analysis(db, opponent_id=1, ts="2026-04-07 13:00:00")
    db.commit()
    db.close()

    ctx = get_activity_context(db_path=activity_db, now=datetime(2026, 4, 7, 14, 0))
    kinds = {row["kind"] for row in ctx["rows"]}
    # At least one row from each of the 4 sources
    assert "ingest" in kinds
    assert "daily_brief" in kinds
    assert "image_approved" in kinds  # approved=1
    assert "analysis" in kinds


def test_activity_handles_superseded_and_unknown_image_state(activity_db):
    """approved=-1 (operator 'superseded' marker) and any unexpected value must
    not crash the activity feed. Regression for dashboard `/` -> 500 KeyError: -1
    (4 live brief_images rows carry approved=-1 'superseded by id=N')."""
    from src.dashboard.views.activity import _summary_for_image, get_activity_context

    # Unit: -1 resolves to a distinct kind; unknown value falls back; canonicals hold.
    kind, summary = _summary_for_image(-1, 224, 0.039, "superseded by id=100")
    assert kind == "image_superseded"
    assert "aizstāts" in summary and "#224" in summary
    assert _summary_for_image(99, 1, 0.0, None)[0] == "image_generated"  # fallback, no KeyError
    assert _summary_for_image(1, 5, 0.0, None)[0] == "image_approved"
    assert _summary_for_image(2, 5, 0.0, "x")[0] == "image_rejected"

    # Integration: the feed builds with a superseded row present.
    db = sqlite3.connect(activity_db)
    _seed_brief_image(db, note_id=224, approved=-1, ts="2026-05-24 20:41:41")
    db.commit()
    db.close()
    ctx = get_activity_context(db_path=activity_db, now=datetime(2026, 5, 25, 0, 0))
    assert "image_superseded" in {row["kind"] for row in ctx["rows"]}


def test_activity_orders_chronologically_newest_first(activity_db):
    from src.dashboard.views.activity import get_activity_context

    db = sqlite3.connect(activity_db)
    _seed_log(db, action="ingest", ts="2026-04-07 09:00:00")
    _seed_log(db, action="ingest", ts="2026-04-07 14:00:00")
    _seed_log(db, action="ingest", ts="2026-04-07 11:00:00")
    db.commit()
    db.close()

    ctx = get_activity_context(db_path=activity_db, now=datetime(2026, 4, 7, 15, 0))
    timestamps = [r["ts"] for r in ctx["rows"]]
    assert timestamps == sorted(timestamps, reverse=True), "must be newest-first"


def test_activity_supports_filter_param(activity_db):
    from src.dashboard.views.activity import get_activity_context

    db = sqlite3.connect(activity_db)
    _seed_log(db, action="ingest", ts="2026-04-07 10:00:00")
    _seed_log(db, action="mentions_fetch", ts="2026-04-07 11:00:00")
    _seed_context_note(db, note_type="daily_brief", topic="t",
                       ts="2026-04-07 12:00:00")
    db.commit()
    db.close()

    ctx = get_activity_context(
        db_path=activity_db, filter="brief", now=datetime(2026, 4, 7, 15, 0)
    )
    kinds = {r["kind"] for r in ctx["rows"]}
    assert kinds == {"daily_brief"}, f"filter=brief should isolate brief writes, got {kinds}"


def test_activity_filter_ingest_includes_mentions_and_social(activity_db):
    from src.dashboard.views.activity import get_activity_context

    db = sqlite3.connect(activity_db)
    _seed_log(db, action="ingest", ts="2026-04-07 10:00:00")
    _seed_log(db, action="mentions_fetch", ts="2026-04-07 11:00:00")
    _seed_log(db, action="social_fetch_all", ts="2026-04-07 12:00:00")
    db.commit()
    db.close()

    ctx = get_activity_context(
        db_path=activity_db, filter="ingest", now=datetime(2026, 4, 7, 15, 0)
    )
    actions = {r["kind"] for r in ctx["rows"]}
    assert actions == {"ingest", "mentions_fetch", "social_fetch_all"}


def test_activity_surfaces_saeima_summary_missing(activity_db):
    """saeima_summary_missing warning (Step 3.5 skipped — bill-like vote stored
    without a summary) must surface in the activity timeline. The log was being
    written by votes.py but never shown — no consumer read it (audit 2026-06-08)."""
    from src.dashboard.views.activity import get_activity_context

    db = sqlite3.connect(activity_db)
    _seed_log(db, action="saeima_summary_missing", status="warning",
              details='{"vote_db_id": 42}', ts="2026-06-04 18:00:00")
    db.commit()
    db.close()

    ctx = get_activity_context(db_path=activity_db, now=datetime(2026, 6, 4, 20, 0))
    kinds = {r["kind"] for r in ctx["rows"]}
    assert "saeima_summary_missing" in kinds, (
        f"saeima_summary_missing warning not surfaced in timeline: {kinds}"
    )


def test_activity_pagination_offset(activity_db):
    from src.dashboard.views.activity import get_activity_context

    db = sqlite3.connect(activity_db)
    for i in range(25):
        _seed_log(db, action="ingest",
                  ts=f"2026-04-07 {i:02d}:00:00" if i < 24 else "2026-04-06 23:00:00")
    db.commit()
    db.close()

    ctx_page1 = get_activity_context(
        db_path=activity_db, limit=20, offset=0,
        now=datetime(2026, 4, 8, 0, 0),
    )
    ctx_page2 = get_activity_context(
        db_path=activity_db, limit=20, offset=20,
        now=datetime(2026, 4, 8, 0, 0),
    )
    assert len(ctx_page1["rows"]) == 20
    assert len(ctx_page2["rows"]) == 5
    # No row overlap between pages
    ids_p1 = {(r["table"], r["source_id"]) for r in ctx_page1["rows"]}
    ids_p2 = {(r["table"], r["source_id"]) for r in ctx_page2["rows"]}
    assert ids_p1.isdisjoint(ids_p2)


def test_activity_since_id_returns_only_newer(activity_db):
    """The /api/activity?since=<id> endpoint must skip rows already on screen.

    Activity polling fires every 30 s; we don't want to re-render the existing
    100 rows. `since` carries the newest visible row id-as-a-tuple.
    """
    from src.dashboard.views.activity import get_activity_context

    db = sqlite3.connect(activity_db)
    _seed_log(db, action="ingest", ts="2026-04-07 10:00:00")  # log id=1
    _seed_log(db, action="ingest", ts="2026-04-07 11:00:00")  # log id=2
    _seed_log(db, action="ingest", ts="2026-04-07 12:00:00")  # log id=3
    db.commit()
    db.close()

    # Snap the "newest visible" cursor: log id=1, the oldest entry
    ctx = get_activity_context(
        db_path=activity_db,
        since={"logs": 1},
        now=datetime(2026, 4, 7, 15, 0),
    )
    log_ids = [r["source_id"] for r in ctx["rows"] if r["table"] == "logs"]
    assert log_ids == [3, 2], f"expected ids >1 only, got {log_ids}"


# ----------------------------------------------------- LV relative time tests


def test_lv_relative_time_seconds_minutes_hours():
    from src.dashboard.views.activity import lv_relative_time

    now = datetime(2026, 4, 7, 12, 0, 0)
    assert lv_relative_time(datetime(2026, 4, 7, 11, 59, 30), now) == "tikko"
    assert lv_relative_time(datetime(2026, 4, 7, 11, 53, 0), now) == "pirms 7 min"
    assert lv_relative_time(datetime(2026, 4, 7, 10, 0, 0), now) == "pirms 2 h"


def test_lv_relative_time_yesterday_and_older():
    from src.dashboard.views.activity import lv_relative_time

    now = datetime(2026, 4, 7, 12, 0, 0)
    assert lv_relative_time(datetime(2026, 4, 6, 20, 0, 0), now) == "vakar"
    older = datetime(2026, 3, 30, 10, 0, 0)
    # Older than yesterday → ISO date
    assert lv_relative_time(older, now) == "2026-03-30"


# ---------------------------------------------------------- integration tests


def test_index_renders_activity_panel(activity_db):
    from src.dashboard.server import create_app

    db = sqlite3.connect(activity_db)
    _seed_log(db, action="ingest", details='{"documents_stored": 5}',
              ts=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    db.commit()
    db.close()

    app = create_app(db_path=activity_db)
    html = app.test_client().get("/").get_data(as_text=True)
    assert 'id="activity-panel"' in html
    # Day-group header for today
    assert "Šodien" in html
    # Row visible
    assert "5" in html  # documents_stored value


def test_api_activity_endpoint_returns_html_fragment(activity_db):
    """POST/GET /api/activity returns just rows (for HTMX swap), not full page."""
    from src.dashboard.server import create_app

    db = sqlite3.connect(activity_db)
    _seed_log(db, action="ingest", ts="2026-04-07 10:00:00")
    db.commit()
    db.close()

    app = create_app(db_path=activity_db)
    resp = app.test_client().get("/api/activity")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    # Fragment, not full page
    assert "<!doctype" not in html.lower()
    assert "<html" not in html.lower()
