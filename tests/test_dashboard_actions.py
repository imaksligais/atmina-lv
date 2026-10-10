"""Task 2.1 — HTMX action infrastructure + toast system."""
from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path

from src.db import init_db


def _make_app_with_schema():
    """Build a Flask app backed by a temp SQLite with full schema.

    `:memory:` doesn't work here because Flask reopens the connection per
    request and SQLite's :memory: isn't shared across connections.
    """
    from src.dashboard.server import create_app

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    return create_app(db_path=path)


# --------------------------------------------------------- helper unit tests


def test_action_response_includes_panel_html_and_hx_trigger():
    """Action helper builds a Flask response with panel HTML body + HX-Trigger
    JSON for the client-side toast handler.
    """
    from flask import Flask

    from src.dashboard.views._actions import action_response

    app = Flask(__name__)
    with app.app_context():
        resp = action_response(
            "<div id='brief-panel'>updated</div>",
            toast_level="success",
            toast_message="Image #85 apstiprināts",
        )
    assert b"updated" in resp.data
    trigger = json.loads(resp.headers["HX-Trigger"])
    assert trigger["showToast"]["level"] == "success"
    assert trigger["showToast"]["message"] == "Image #85 apstiprināts"


def test_action_response_omits_trigger_when_no_toast():
    """If no toast message is requested, no HX-Trigger header is set."""
    from flask import Flask

    from src.dashboard.views._actions import action_response

    app = Flask(__name__)
    with app.app_context():
        resp = action_response("<div>panel</div>")
    assert "HX-Trigger" not in resp.headers


# ----------------------------------------------------- template render tests


def test_toast_partial_renders_with_level_and_text():
    """Toast partial accepts {level, message} and emits a single status node."""
    from flask import render_template

    from src.dashboard.server import create_app

    app = _make_app_with_schema()
    with app.app_context():
        html = render_template("partials/_toast.html.j2",
                               level="success", message="Done.")
    assert 'role="status"' in html
    assert "status-success" in html
    assert "Done." in html


def test_toast_partial_supports_all_severity_levels():
    """Each level renders a distinct status class so the visual cue is unique."""
    from flask import render_template

    from src.dashboard.server import create_app

    app = _make_app_with_schema()
    for level in ("success", "warning", "danger", "info"):
        with app.app_context():
            html = render_template("partials/_toast.html.j2",
                                   level=level, message="x")
        assert f"status-{level}" in html, f"missing status-{level} class"


# ------------------------------------------------- HTMX wiring smoke tests


def test_all_hx_targets_in_index_resolve_to_existing_ids(tmp_path: Path):
    """No hx-target may reference an id that doesn't actually exist in the
    rendered page. Catches typos and stale refactors before they reach
    the browser (where they'd silently no-op).
    """
    fd_path = tmp_path / "test.db"
    init_db(str(fd_path))

    from src.dashboard.server import create_app

    app = create_app(db_path=str(fd_path))
    html = app.test_client().get("/").get_data(as_text=True)

    hx_targets = set(re.findall(r'hx-target="#([\w-]+)"', html))
    ids_present = set(re.findall(r'id="([\w-]+)"', html))

    missing = hx_targets - ids_present
    assert not missing, (
        f"hx-target refers to non-existent ids: {missing}"
    )


def test_actions_helper_default_level_is_success(tmp_path: Path):
    """Default level when caller forgets to specify."""
    from flask import Flask

    from src.dashboard.views._actions import action_response

    app = Flask(__name__)
    with app.app_context():
        resp = action_response("<p>panel</p>", toast_message="Saglabāts")
    trigger = json.loads(resp.headers["HX-Trigger"])
    assert trigger["showToast"]["level"] == "success"


def test_ops_js_contains_show_toast_listener():
    """ops.js must register a showToast event listener for HTMX HX-Trigger."""
    js_path = (
        Path(__file__).resolve().parents[1] / "src" / "dashboard" / "static" / "ops.js"
    )
    text = js_path.read_text(encoding="utf-8")
    assert "showToast" in text, "ops.js missing showToast event handler"
    assert "addEventListener" in text or "body.addEventListener" in text


def test_base_template_has_toast_container():
    """The base layout must include the toast container that ops.js targets."""
    from src.dashboard.server import create_app

    app = _make_app_with_schema()
    html = app.test_client().get("/").get_data(as_text=True)
    # ops.js looks up document.getElementById('toast-container')
    assert 'id="toast-container"' in html
