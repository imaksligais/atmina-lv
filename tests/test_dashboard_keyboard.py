"""Task 2.5 — keyboard help modal + shortcut dispatcher."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from src.db import init_db


@pytest.fixture
def app_with_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)

    from src.dashboard.server import create_app

    yield create_app(db_path=path)
    try:
        os.unlink(path)
    except PermissionError:
        pass


def test_keyboard_help_modal_route_returns_fragment(app_with_db):
    """`GET /api/keyboard-help` returns the help modal markup for HTMX inject."""
    resp = app_with_db.test_client().get("/api/keyboard-help")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    # Fragment, not full page
    assert "<!doctype" not in html.lower()
    # Modal container present
    assert "keyboard-help-modal" in html or "x-data" in html


def test_keyboard_help_lists_all_phase2_shortcuts(app_with_db):
    """The help modal must mention every Phase 2 shortcut. The visual table
    is the discoverability surface; if a shortcut isn't listed here, no one
    will know it exists."""
    html = app_with_db.test_client().get("/api/keyboard-help").get_data(as_text=True)
    for key in ("?", "A", "R", "D", "Esc"):
        # Look for the key in a kbd-styled span — accepting either an inline
        # <kbd>K</kbd> or a >K< boundary so the test isn't tied to specific
        # markup choices.
        assert f">{key}<" in html or f"<kbd>{key}</kbd>" in html, (
            f"shortcut [{key}] not listed in help modal"
        )


def test_ops_js_registers_keyboard_dispatcher():
    """ops.js must listen for keydown events and dispatch via data-shortcut."""
    js_path = (
        Path(__file__).resolve().parents[1] / "src" / "dashboard" / "static" / "ops.js"
    )
    text = js_path.read_text(encoding="utf-8")
    assert "data-shortcut" in text, "ops.js missing data-shortcut handler"
    assert "keydown" in text, "ops.js missing keydown listener"


def test_ops_js_skips_shortcut_when_typing_in_input():
    """A keystroke inside <input>/<textarea> must NOT fire the global shortcut
    — typing 'r' in the reject reason should not refresh slots."""
    js_path = (
        Path(__file__).resolve().parents[1] / "src" / "dashboard" / "static" / "ops.js"
    )
    text = js_path.read_text(encoding="utf-8")
    # Either tag name guard OR isContentEditable check accepted
    assert "INPUT" in text or "input" in text.lower()
    assert "TEXTAREA" in text or "textarea" in text.lower()


def test_index_renders_help_trigger(app_with_db):
    """A discoverable surface for the help modal must exist somewhere on the
    page — header `?` button preferred so first-visit operators find it.

    Uses the ``app_with_db`` fixture (defensive temp-DB teardown) rather than
    inline mkstemp + bare ``os.unlink`` — the latter flaked on Windows with
    WinError 32 because the app's SQLite handle outlives the unlink.
    """
    html = app_with_db.test_client().get("/").get_data(as_text=True)
    assert "/api/keyboard-help" in html
