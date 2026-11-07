"""Task 1.2 — today's brief panel view + template smoke."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest


# --------------------------------------------------------------------- fixture


def _make_test_db(tmp_path: Path) -> Path:
    """Spin up a full production-shaped DB via `init_db`.

    Earlier this helper hand-rolled a minimal schema for brief tables only,
    but once the index route started composing multiple panel contexts
    (routine queries `documents`, `tracked_politicians`, etc.), the partial
    schema caused integration tests to fail with OperationalError. Using
    the canonical initializer is cheaper than maintaining a hand-curated
    subset and keeps tests in sync with the real schema for free.
    """
    from src.db import init_db

    db_path = tmp_path / "test.db"
    init_db(str(db_path))
    return db_path


SAMPLE_CONTENT = """# Dienas analīze — 2026-05-16

## Galvenais

<!-- DIENAS STATS (iekšēja piezīme): 627 docs, 14 pozīcijas -->

- **Pirmais punkts:** Rinkēvičs nominē Kulbergu. Cited: #20383, #20384.
- **Otrais punkts:** Sprūda demisija atstāj Aizsardzības resoru bez ministra. Cited: #20395.

## Konteksts

Plašāks raksts… cf. #20399.
"""


# --------------------------------------------------- view helper unit tests


def test_brief_context_returns_today_brief_when_exists(tmp_path: Path) -> None:
    from src.dashboard.views.brief import get_brief_context

    db_path = _make_test_db(tmp_path)
    db = sqlite3.connect(str(db_path))
    db.execute(
        "INSERT INTO context_notes(id, topic, note_type, content, source, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            42,
            "dienas pārskats 2026-05-16",
            "daily_brief",
            SAMPLE_CONTENT,
            "atmina.lv analīze 2026-05-16",
            "2026-05-16 18:08:02",
        ),
    )
    db.commit()
    db.close()

    ctx = get_brief_context("2026-05-16", db_path=str(db_path))
    assert ctx["brief"] is not None, "brief should resolve when daily_brief row exists for date"
    assert ctx["brief"]["id"] == 42
    assert ctx["brief"]["topic"] == "dienas pārskats 2026-05-16"
    assert ctx["brief"]["title"] == "Dienas analīze — 2026-05-16"
    assert ctx["brief"]["char_count"] == len(SAMPLE_CONTENT)
    assert ctx["wiki_path"].endswith("wiki/dailies/2026-05-16.md")
    assert ctx["atmina_url"] == "https://atmina.lv/blog/2026-05-16.html"


def test_brief_context_returns_none_when_no_brief_for_date(tmp_path: Path) -> None:
    from src.dashboard.views.brief import get_brief_context

    db_path = _make_test_db(tmp_path)
    ctx = get_brief_context("2026-05-17", db_path=str(db_path))
    assert ctx["brief"] is None
    assert ctx["image"] is None
    assert ctx["cited_claim_ids"] == []
    assert ctx["lede"] == ""


def test_brief_context_includes_image_approval_state(tmp_path: Path) -> None:
    from src.dashboard.views.brief import get_brief_context

    db_path = _make_test_db(tmp_path)
    db = sqlite3.connect(str(db_path))
    db.execute(
        "INSERT INTO context_notes(id, topic, note_type, content, created_at) "
        "VALUES (212, 'dienas pārskats 2026-05-16', 'daily_brief', ?, ?)",
        (SAMPLE_CONTENT, "2026-05-16 18:08:02"),
    )
    db.execute(
        "INSERT INTO brief_images"
        "(id, note_id, image_path, prompt, model, generated_at, approved, cost_usd) "
        "VALUES (85, 212, 'images/briefs/2026-05-16-x.png', 'p', 'gemini', "
        "'2026-05-16 18:26:01', 1, 0.039)"
    )
    db.commit()
    db.close()

    ctx = get_brief_context("2026-05-16", db_path=str(db_path))
    assert ctx["image"] is not None
    assert ctx["image"]["id"] == 85
    assert ctx["image"]["approved"] == 1
    assert ctx["image"]["image_path"] == "images/briefs/2026-05-16-x.png"


def test_brief_context_extracts_cited_claim_ids_from_content(tmp_path: Path) -> None:
    from src.dashboard.views.brief import get_brief_context

    db_path = _make_test_db(tmp_path)
    db = sqlite3.connect(str(db_path))
    db.execute(
        "INSERT INTO context_notes(id, topic, note_type, content) "
        "VALUES (1, 'dienas pārskats 2026-05-16', 'daily_brief', ?)",
        (SAMPLE_CONTENT,),
    )
    db.commit()
    db.close()

    ctx = get_brief_context("2026-05-16", db_path=str(db_path))
    # Must capture #20383, #20384, #20395, #20399 — but NOT the `# ` heading
    # marker or the `## Galvenais` separator.
    assert ctx["cited_claim_ids"] == [20383, 20384, 20395, 20399]


def test_brief_context_lede_strips_html_comments_and_markdown(tmp_path: Path) -> None:
    from src.dashboard.views.brief import get_brief_context

    db_path = _make_test_db(tmp_path)
    db = sqlite3.connect(str(db_path))
    db.execute(
        "INSERT INTO context_notes(id, topic, note_type, content) "
        "VALUES (1, 'dienas pārskats 2026-05-16', 'daily_brief', ?)",
        (SAMPLE_CONTENT,),
    )
    db.commit()
    db.close()

    ctx = get_brief_context("2026-05-16", db_path=str(db_path))
    lede = ctx["lede"]
    assert "DIENAS STATS" not in lede, "HTML comment must be stripped"
    assert "<!--" not in lede
    assert "**" not in lede, "bold markdown markers must be stripped from preview"
    assert lede.startswith("Pirmais punkts"), f"unexpected lede start: {lede[:60]!r}"
    # Subsequent bullets must NOT bleed into the preview — the panel is for
    # the first key point only. If this regresses, the panel will spill.
    assert "Otrais punkts" not in lede, (
        "lede must contain only the first bullet — second bullet leaked"
    )


# ------------------------------------------------ partial rendering smoke


def test_index_renders_empty_state_when_no_brief(tmp_path: Path) -> None:
    """When DB has no brief for today, the brief panel shows friendly empty copy."""
    from src.dashboard.server import create_app

    db_path = _make_test_db(tmp_path)
    app = create_app(db_path=str(db_path))
    client = app.test_client()
    html = client.get("/").get_data(as_text=True)
    assert "Brief vēl nav uzrakstīts" in html or "Brief vēl nav" in html, (
        "empty state copy missing from index.html"
    )


def test_index_renders_active_brief_when_present(tmp_path: Path, monkeypatch) -> None:
    """When a daily_brief exists for today_lv(), the panel shows its title."""
    from src.dashboard.server import create_app
    from src.dashboard.views import brief as brief_view

    db_path = _make_test_db(tmp_path)
    db = sqlite3.connect(str(db_path))
    db.execute(
        "INSERT INTO context_notes(id, topic, note_type, content, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            7,
            "dienas pārskats 2099-01-01",
            "daily_brief",
            SAMPLE_CONTENT,
            "2099-01-01 18:08:02",
        ),
    )
    db.commit()
    db.close()

    # Freeze today_lv() to the date we inserted.
    import datetime as _dt

    monkeypatch.setattr(brief_view, "today_lv", lambda: _dt.date(2099, 1, 1))

    app = create_app(db_path=str(db_path))
    html = app.test_client().get("/").get_data(as_text=True)
    assert "Dienas analīze" in html, "brief title missing from active state"
    assert "8091" not in html or "char_count" not in html, (
        "char count should render via template, not raw key"
    )


@pytest.mark.parametrize("state", ["loading", "error"])
def test_brief_partial_supports_loading_and_error_state(state: str, tmp_path: Path) -> None:
    """Loading + error markup must be reachable via the `state` partial argument."""
    from flask import render_template

    from src.dashboard.server import create_app

    app = create_app(db_path=str(_make_test_db(tmp_path)))
    with app.app_context():
        html = render_template("partials/brief.html.j2", brief=None, lede="", state=state)
    if state == "loading":
        assert "animate-pulse" in html
    if state == "error":
        assert "retry" in html.lower() or "Atkārtot" in html


# -------------------------------------------- Task 2.2: image approve / reject


def _seed_brief_with_image(tmp_path: Path, *, approved: int = 0) -> tuple[Path, int]:
    """Insert a daily_brief + image for today; returns (db_path, image_id)."""
    import sqlite3

    from src.db import today_lv

    db_path = _make_test_db(tmp_path)
    db = sqlite3.connect(str(db_path))
    today = today_lv().isoformat()
    db.execute(
        "INSERT INTO context_notes (id, note_type, topic, content, created_at) "
        "VALUES (1, 'daily_brief', ?, 'c', ?)",
        (f"dienas pārskats {today}", f"{today} 18:00:00"),
    )
    db.execute(
        "INSERT INTO brief_images (id, note_id, image_path, prompt, model, "
        "generated_at, approved, cost_usd) "
        "VALUES (?, 1, 'images/briefs/x.png', 'p', 'gem', ?, ?, 0.039)",
        (85, f"{today} 18:30:00", approved),
    )
    db.commit()
    db.close()
    return db_path, 85


def test_approve_endpoint_persists_approval(tmp_path: Path) -> None:
    import sqlite3

    from src.dashboard.server import create_app

    db_path, image_id = _seed_brief_with_image(tmp_path, approved=0)
    app = create_app(db_path=str(db_path))
    resp = app.test_client().post(f"/api/image/{image_id}/approve")

    assert resp.status_code == 200
    db = sqlite3.connect(str(db_path))
    row = db.execute("SELECT approved FROM brief_images WHERE id=?", (image_id,)).fetchone()
    db.close()
    assert row[0] == 1


def test_approve_returns_refreshed_brief_panel_html(tmp_path: Path) -> None:
    import json as _json

    from src.dashboard.server import create_app

    db_path, image_id = _seed_brief_with_image(tmp_path, approved=0)
    app = create_app(db_path=str(db_path))
    resp = app.test_client().post(f"/api/image/{image_id}/approve")

    html = resp.get_data(as_text=True)
    assert 'id="brief-panel"' in html, "response must be the refreshed brief panel partial"
    assert "HX-Trigger" in resp.headers
    trigger = _json.loads(resp.headers["HX-Trigger"])
    assert trigger["showToast"]["level"] == "success"
    assert "apstiprin" in trigger["showToast"]["message"].lower()


def test_approve_refuses_already_approved_image(tmp_path: Path) -> None:
    from src.dashboard.server import create_app

    db_path, image_id = _seed_brief_with_image(tmp_path, approved=1)
    app = create_app(db_path=str(db_path))
    resp = app.test_client().post(f"/api/image/{image_id}/approve")
    # 400 because the action is a no-op — surface the redundancy
    assert resp.status_code == 400


def test_approve_404_on_missing_image(tmp_path: Path) -> None:
    from src.dashboard.server import create_app

    app = create_app(db_path=str(_make_test_db(tmp_path)))
    resp = app.test_client().post("/api/image/999/approve")
    assert resp.status_code == 404


def test_reject_requires_reason_form_field(tmp_path: Path) -> None:
    from src.dashboard.server import create_app

    db_path, image_id = _seed_brief_with_image(tmp_path, approved=0)
    app = create_app(db_path=str(db_path))

    resp_no_reason = app.test_client().post(f"/api/image/{image_id}/reject")
    assert resp_no_reason.status_code == 400

    resp_empty = app.test_client().post(
        f"/api/image/{image_id}/reject", data={"reason": "   "}
    )
    assert resp_empty.status_code == 400, "whitespace-only reason is not a real reason"


def test_reject_persists_reason_and_returns_panel(tmp_path: Path) -> None:
    import sqlite3

    from src.dashboard.server import create_app

    db_path, image_id = _seed_brief_with_image(tmp_path, approved=0)
    app = create_app(db_path=str(db_path))
    resp = app.test_client().post(
        f"/api/image/{image_id}/reject",
        data={"reason": "Pārāk tumšs"},
    )
    assert resp.status_code == 200
    assert 'id="brief-panel"' in resp.get_data(as_text=True)

    db = sqlite3.connect(str(db_path))
    row = db.execute(
        "SELECT approved, error_message FROM brief_images WHERE id=?", (image_id,)
    ).fetchone()
    db.close()
    assert row[0] == 2
    assert row[1] == "Pārāk tumšs"


def test_brief_panel_renders_approve_reject_buttons_for_pending(tmp_path: Path) -> None:
    """When image.approved == 0, the panel surfaces both action buttons."""
    from src.dashboard.server import create_app

    db_path, _ = _seed_brief_with_image(tmp_path, approved=0)
    app = create_app(db_path=str(db_path))
    html = app.test_client().get("/").get_data(as_text=True)
    assert "hx-post" in html
    assert "/api/image/85/approve" in html
    assert "Noraid" in html or "/api/image/85/reject" in html
