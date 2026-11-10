"""Smoke tests for the atmina ops dashboard scaffold (Task 1.1).

Covers app factory shape, localhost-only bind, panel skeleton on `/`.
JS-level theme persistence is not asserted here — it's verified by manual
browser smoke per plan Task 1.1 acceptance.
"""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def seeded_db(tmp_path_factory) -> str:
    """A schema-complete but empty temp DB so the index view's panel context
    helpers read real (empty) tables instead of the live, gitignored
    data/atmina.db (absent in CI). Panels render empty → page still 200s."""
    from src.db import init_db

    path = str(tmp_path_factory.mktemp("dash") / "ops.db")
    init_db(path)
    return path


def test_app_factory_returns_flask_instance() -> None:
    from flask import Flask

    from src.dashboard.server import create_app

    app = create_app()
    assert isinstance(app, Flask), "create_app() must return a Flask app"


def test_serve_py_binds_localhost_only() -> None:
    """`serve.py` must call app.run with host='127.0.0.1'; never 0.0.0.0.

    Asserted at source level because we cannot start the server during tests
    (it would block). The launcher is a 4-line script — text scan is enough.
    """
    serve_py = Path(__file__).resolve().parents[1] / "serve.py"
    assert serve_py.exists(), "serve.py launcher missing at repo root"
    text = serve_py.read_text(encoding="utf-8")
    assert "127.0.0.1" in text, "serve.py must bind to 127.0.0.1"
    assert "0.0.0.0" not in text, "serve.py must NOT bind to 0.0.0.0 (localhost only)"


def test_root_returns_200_with_panel_grid(seeded_db: str) -> None:
    """GET / renders the 5 M1 panel containers (brief, routine, slot, strategy, backlog).

    Activity panel is Task 1.7; not required here yet.
    """
    from src.dashboard.server import create_app

    app = create_app(db_path=seeded_db)
    client = app.test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    for panel_id in (
        "brief-panel",
        "routine-panel",
        "slot-panel",
        "strategy-panel",
        "backlog-panel",
    ):
        assert f'id="{panel_id}"' in html, (
            f"missing panel container #{panel_id} in index.html"
        )


def test_root_includes_theme_toggle_control(seeded_db: str) -> None:
    """Theme toggle button is present in the header (JS persistence is browser-tested)."""
    from src.dashboard.server import create_app

    app = create_app(db_path=seeded_db)
    client = app.test_client()
    html = client.get("/").get_data(as_text=True)
    assert 'id="theme-toggle"' in html, "theme toggle button missing in header"


@pytest.mark.parametrize("asset", ["ops.css", "ops.js"])
def test_static_assets_served(asset: str) -> None:
    from src.dashboard.server import create_app

    app = create_app()
    client = app.test_client()
    resp = client.get(f"/static/{asset}")
    assert resp.status_code == 200, f"/static/{asset} did not return 200"


# --- Cross-site POST guard (2026-11-09) --------------------------------------
# Failure named: docs/audits/2026-11-07-koda-parskats/README.md § 1 (4) — a
# POST with `Origin: evil.example` reached the deploy runner with 200, so any
# web page open while serve.py runs could trigger a deploy.


def test_cross_site_post_cannot_trigger_deploy(seeded_db, monkeypatch) -> None:
    from src.dashboard.server import create_app
    from src.dashboard.views import deploy

    calls: list[int] = []

    def fake_deploy(timeout=300):
        calls.append(1)
        return {"exit_code": 0, "stdout": "", "stderr": "", "timed_out": False}

    monkeypatch.setattr(deploy, "run_deploy_script", fake_deploy)
    client = create_app(db_path=seeded_db).test_client()

    # A plain HTML form on another site: no HTMX header, foreign Origin.
    assert client.post("/api/deploy",
                       headers={"Origin": "https://evil.example"}).status_code == 403
    # Even with the header forged, a foreign Origin is refused.
    assert client.post("/api/deploy", headers={
        "Origin": "https://evil.example", "HX-Request": "true"}).status_code == 403
    # DNS rebinding: a foreign Host never reaches a route.
    assert client.post("/api/deploy", headers={"HX-Request": "true"},
                       base_url="http://evil.example").status_code == 400
    assert calls == []

    # The dashboard's own HTMX button still works.
    resp = client.post("/api/deploy", headers={
        "Origin": "http://localhost", "HX-Request": "true"})
    assert resp.status_code == 200
    assert calls == [1]
