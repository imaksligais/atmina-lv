"""Task 2.4 — deploy trigger with confirm modal."""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import tempfile

import pytest

from src.db import init_db


@pytest.fixture
def deploy_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    try:
        os.unlink(path)
    except PermissionError:
        pass


# -------------------------------------------------------- last-deploy helper


def test_get_last_deploy_returns_none_when_empty(deploy_db):
    from src.dashboard.views.deploy import get_last_deploy
    assert get_last_deploy(db_path=deploy_db) is None


def test_get_last_deploy_returns_latest_deploy_row(deploy_db):
    from src.dashboard.views.deploy import get_last_deploy

    db = sqlite3.connect(deploy_db)
    db.execute(
        "INSERT INTO logs (timestamp, action, status, details) "
        "VALUES (?, ?, ?, ?)",
        ("2026-05-16 17:35:00", "deploy", "success",
         '{"bytes_transferred": 1782000}'),
    )
    db.execute(
        "INSERT INTO logs (timestamp, action, status, details) "
        "VALUES (?, ?, ?, ?)",
        ("2026-05-15 21:00:00", "deploy", "success",
         '{"bytes_transferred": 2300000}'),
    )
    db.commit()
    db.close()

    last = get_last_deploy(db_path=deploy_db)
    assert last is not None
    assert last["timestamp"] == "2026-05-16 17:35:00"
    assert last["status"] == "success"


# -------------------------------------------------------- confirm-modal endpoint


def test_deploy_confirm_modal_renders_last_deploy_timestamp(deploy_db):
    from src.dashboard.server import create_app

    db = sqlite3.connect(deploy_db)
    db.execute(
        "INSERT INTO logs (timestamp, action, status) VALUES (?, ?, ?)",
        ("2026-05-16 17:35:00", "deploy", "success"),
    )
    db.commit()
    db.close()

    app = create_app(db_path=deploy_db)
    resp = app.test_client().get("/api/deploy/confirm")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "2026-05-16 17:35:00" in html
    # The fragment must contain the form submit
    assert "Apstiprin" in html


def test_deploy_confirm_modal_renders_first_deploy_copy_when_no_history(deploy_db):
    from src.dashboard.server import create_app

    app = create_app(db_path=deploy_db)
    html = app.test_client().get("/api/deploy/confirm").get_data(as_text=True)
    # Empty-history copy should make it clear this is the first deploy
    assert "pirmais" in html.lower() or "nav iepriekš" in html.lower() or "no history" in html.lower()


# ---------------------------------------------------------- deploy executor


def test_run_deploy_script_returns_success_on_exit_zero(monkeypatch):
    from src.dashboard.views import deploy

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(args=cmd, returncode=0,
                                            stdout="rsync OK\n1.7 MB\n",
                                            stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = deploy.run_deploy_script(timeout=5)
    assert result["exit_code"] == 0
    assert "rsync OK" in result["stdout"]
    assert result["timed_out"] is False


def test_run_deploy_script_surfaces_timeout(monkeypatch):
    from src.dashboard.views import deploy

    def fake_run(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=kwargs.get("timeout", 1))

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = deploy.run_deploy_script(timeout=1)
    assert result["timed_out"] is True
    assert result["exit_code"] != 0


def test_run_deploy_script_propagates_stderr_on_failure(monkeypatch):
    from src.dashboard.views import deploy

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(args=cmd, returncode=2,
                                            stdout="",
                                            stderr="rsync: connection refused\n")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = deploy.run_deploy_script(timeout=5)
    assert result["exit_code"] == 2
    assert "connection refused" in result["stderr"]


# ----------------------------------------------------------- POST /api/deploy


def test_deploy_endpoint_logs_action_on_success(deploy_db, monkeypatch):
    from src.dashboard.server import create_app
    from src.dashboard.views import deploy

    monkeypatch.setattr(
        deploy, "run_deploy_script",
        lambda timeout=300: {
            "exit_code": 0,
            "stdout": "rsync OK · 1700000 bytes",
            "stderr": "",
            "timed_out": False,
        },
    )

    app = create_app(db_path=deploy_db)
    resp = app.test_client().post("/api/deploy")
    assert resp.status_code == 200

    # Persisted to logs
    db = sqlite3.connect(deploy_db)
    row = db.execute(
        "SELECT status, details FROM logs WHERE action='deploy' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    db.close()
    assert row[0] == "success"

    trigger = json.loads(resp.headers["HX-Trigger"])
    assert trigger["showToast"]["level"] == "success"
    assert "deploy" in trigger["showToast"]["message"].lower()


def test_deploy_endpoint_returns_stderr_tail_on_failure(deploy_db, monkeypatch):
    from src.dashboard.server import create_app
    from src.dashboard.views import deploy

    monkeypatch.setattr(
        deploy, "run_deploy_script",
        lambda timeout=300: {
            "exit_code": 2,
            "stdout": "",
            "stderr": "rsync: connection unexpectedly closed (123 bytes received so far) [sender]\nrsync error: error in rsync protocol data stream (code 12) at io.c(228)",
            "timed_out": False,
        },
    )

    app = create_app(db_path=deploy_db)
    resp = app.test_client().post("/api/deploy")
    assert resp.status_code == 200  # endpoint succeeded, deploy failed
    trigger = json.loads(resp.headers["HX-Trigger"])
    assert trigger["showToast"]["level"] == "danger"
    # Toast carries enough context that operator can diagnose
    assert "exit 2" in trigger["showToast"]["message"] or "rsync" in trigger["showToast"]["message"].lower()


def test_deploy_endpoint_marks_timeout_status(deploy_db, monkeypatch):
    from src.dashboard.server import create_app
    from src.dashboard.views import deploy

    monkeypatch.setattr(
        deploy, "run_deploy_script",
        lambda timeout=300: {
            "exit_code": -1,
            "stdout": "",
            "stderr": "",
            "timed_out": True,
        },
    )

    app = create_app(db_path=deploy_db)
    resp = app.test_client().post("/api/deploy")
    trigger = json.loads(resp.headers["HX-Trigger"])
    assert "timeout" in trigger["showToast"]["message"].lower() or "300" in trigger["showToast"]["message"]


def test_index_renders_deploy_button(deploy_db):
    """The dashboard must surface a deploy entry point with the keyboard hook."""
    from src.dashboard.server import create_app

    app = create_app(db_path=deploy_db)
    html = app.test_client().get("/").get_data(as_text=True)
    assert "/api/deploy/confirm" in html
    assert 'data-shortcut="D"' in html


# ------------------------------------------------- additive-deploy guarantee
#
# CLAUDE.md standing decision: "Deploy is additive. `deploy.sh --no-delete`
# always; `finanses` + `statistika` remote dirs are curated — never delete
# remote trees."
#
# Until 2026-08-01 scripts/deploy.sh defaulted to DELETE_FLAG="--delete" and
# this view invoked it with no flag at all, so the dashboard button was the one
# caller in the repo running a destructive sync. Every runbook, skill and
# workflow passed --no-delete; only the button did not. These two tests lock
# both halves of the fix — the caller and the script default — because either
# one alone silently restores the hazard.


def test_dashboard_deploy_invokes_script_additively(monkeypatch):
    """The button must pass --no-delete explicitly, not rely on the default."""
    from src.dashboard.views import deploy

    seen = {}

    def fake_run(cmd, **kwargs):
        seen["cmd"] = cmd
        return subprocess.CompletedProcess(args=cmd, returncode=0,
                                            stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    deploy.run_deploy_script(timeout=5)

    assert "--no-delete" in seen["cmd"], (
        f"dashboard deploy button must run additively; got {seen['cmd']}"
    )
    assert "--delete" not in seen["cmd"]


def test_deploy_script_defaults_to_additive():
    """scripts/deploy.sh must not enable rsync --delete unless asked."""
    import pathlib
    import re

    script = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "deploy.sh"
    text = script.read_text(encoding="utf-8")

    # The default assignment must be empty. Comments mentioning --delete are
    # fine; the assignment is what reaches rsync.
    defaults = re.findall(r'^\s*DELETE_FLAG=(.*)$', text, re.MULTILINE)
    assert defaults, "DELETE_FLAG assignment not found in scripts/deploy.sh"
    assert defaults[0].strip() in ('""', "''"), (
        f"deploy.sh must default to additive; DELETE_FLAG={defaults[0]!r}"
    )

    # ...and destruction must still be reachable deliberately.
    assert "--delete)" in text, "deploy.sh should still offer an opt-in --delete"
