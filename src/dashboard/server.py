"""Flask app factory for atmina ops dashboard.

The factory is the single entry point — `serve.py` at repo root calls
`create_app()` and runs it on 127.0.0.1:8080. Tests pass `db_path` to
swap in an in-memory or fixture DB without monkeypatching `src.db`.
"""
from __future__ import annotations

from flask import Flask, render_template, request

from src.dashboard.views._actions import action_response
from src.dashboard.views.activity import get_activity_context
from src.dashboard.views.backlog import get_backlog_context
from src.dashboard.views.brief import get_brief_context
from src.dashboard.views import deploy as deploy_view
from src.dashboard.views.deploy import DEPLOY_TIMEOUT_SECONDS
from src.dashboard.views.pending import get_pending_actions
from src.dashboard.views.routine import get_routine_context
from src.dashboard.views.slots import get_slot_snapshot
from src.dashboard.views.strategy import get_strategy_context
from src.db import get_db, log_action
from src.graphics.storage import approve_image, reject_image


def _parse_int_arg(name: str, default: int = 0) -> int:
    try:
        return int(request.args.get(name, default))
    except (TypeError, ValueError):
        return default


def create_app(db_path: str | None = None) -> Flask:
    """Return a configured Flask app for the operator dashboard.

    Args:
        db_path: Optional override forwarded to view helpers. Production
            callers leave it unset; tests pass a tmp_path fixture.
    """
    app = Flask(__name__)
    app.config["JSON_AS_ASCII"] = False
    app.config["DB_PATH"] = db_path

    @app.route("/")
    def index() -> str:
        db_path = app.config["DB_PATH"]
        brief_ctx = get_brief_context(db_path=db_path)
        routine_ctx = get_routine_context(db_path=db_path)
        slots_ctx = get_slot_snapshot()
        strategy_ctx = get_strategy_context(db_path=db_path)
        backlog_ctx = get_backlog_context(db_path=db_path)
        activity_ctx = get_activity_context(
            db_path=db_path,
            filter=request.args.get("filter"),
            offset=_parse_int_arg("offset", 0),
        )
        # Pending must run AFTER slots so the slot snapshot can be reused
        # without triggering a second probe (probe cost is ~5-10 s on cold).
        pending_ctx = get_pending_actions(db_path=db_path, slots=slots_ctx)
        return render_template(
            "index.html.j2",
            routine=routine_ctx,
            slots=slots_ctx,
            strategy=strategy_ctx,
            backlog=backlog_ctx,
            activity=activity_ctx,
            pending=pending_ctx,
            **brief_ctx,
        )

    def _refreshed_brief_panel_html() -> str:
        """Re-render the brief panel partial after an image mutation."""
        brief_ctx = get_brief_context(db_path=app.config["DB_PATH"])
        return render_template("partials/brief.html.j2", **brief_ctx)

    @app.route("/api/image/<int:image_id>/approve", methods=["POST"])
    def api_approve_image(image_id: int):
        """Approve a pending brief image. Returns 404 if missing, 400 if
        already approved (silent button-mashing hides operator intent)."""
        db_path = app.config["DB_PATH"]
        db = get_db(db_path) if db_path else get_db()
        try:
            row = db.execute(
                "SELECT approved FROM brief_images WHERE id=?", (image_id,)
            ).fetchone()
            if row is None:
                return ("image not found", 404)
            if row["approved"] == 1:
                return (f"image {image_id} already approved", 400)
            approve_image(db, image_id)
        finally:
            db.close()
        return action_response(
            _refreshed_brief_panel_html(),
            toast_level="success",
            toast_message=f"Image #{image_id} apstiprināts",
        )

    @app.route("/api/image/<int:image_id>/reject", methods=["POST"])
    def api_reject_image(image_id: int):
        """Reject a brief image with operator-supplied reason. The reason
        is persisted into `brief_images.error_message` so the audit trail
        is preserved for later @graphics-designer prompt tuning."""
        reason = (request.form.get("reason") or "").strip()
        if not reason:
            return ("reason required", 400)
        db_path = app.config["DB_PATH"]
        db = get_db(db_path) if db_path else get_db()
        try:
            row = db.execute(
                "SELECT approved FROM brief_images WHERE id=?", (image_id,)
            ).fetchone()
            if row is None:
                return ("image not found", 404)
            reject_image(db, image_id, reason)
        finally:
            db.close()
        return action_response(
            _refreshed_brief_panel_html(),
            toast_level="warning",
            toast_message=f"Image #{image_id} noraidīts",
        )

    @app.route("/api/keyboard-help")
    def api_keyboard_help():
        """Return the keyboard help modal HTML for HTMX to inject into <body>."""
        return render_template("modals/keyboard_help.html.j2")

    @app.route("/api/deploy/confirm")
    def api_deploy_confirm():
        """Return the deploy confirm modal HTML for HTMX to inject."""
        last = deploy_view.get_last_deploy(db_path=app.config["DB_PATH"])
        return render_template("modals/deploy_confirm.html.j2", last_deploy=last)

    @app.route("/api/deploy", methods=["POST"])
    def api_deploy():
        """Run ``scripts/deploy.sh`` and surface the result via toast.

        On success, persists a ``logs(action='deploy', status='success')``
        row so the activity timeline + last-deploy modal stay in sync.
        On non-zero exit, persists status='failed' with stderr tail; on
        timeout, status='timeout'. Endpoint always returns 200 — the toast
        carries failure details. The module-attribute call (rather than a
        direct symbol import) lets tests monkeypatch ``deploy_view.*``.
        """
        result = deploy_view.run_deploy_script()
        db_path = app.config["DB_PATH"]
        if result["exit_code"] == 0:
            stdout_tail = result["stdout"][-500:]
            log_action(
                "deploy",
                status="success",
                details={"stdout_tail": stdout_tail},
                db_path=db_path or "data/atmina.db",
            )
            return action_response(
                "",
                toast_level="success",
                toast_message="Deploy success",
            )
        if result["timed_out"]:
            log_action(
                "deploy",
                status="timeout",
                details={"timeout_seconds": DEPLOY_TIMEOUT_SECONDS},
                db_path=db_path or "data/atmina.db",
            )
            return action_response(
                "",
                toast_level="danger",
                toast_message=f"Deploy timeout ({DEPLOY_TIMEOUT_SECONDS}s)",
            )
        stderr_tail = (result["stderr"] or "")[-200:].replace("\n", " ").strip()
        log_action(
            "deploy",
            status="failed",
            error_message=stderr_tail[:200],
            details={"exit_code": result["exit_code"]},
            db_path=db_path or "data/atmina.db",
        )
        return action_response(
            "",
            toast_level="danger",
            toast_message=f"Deploy fail (exit {result['exit_code']}): {stderr_tail}",
        )

    @app.route("/api/slots/refresh", methods=["POST"])
    def api_refresh_slots():
        """Force-probe all cookie slots, return the refreshed slot panel.

        Bypasses the 60 s cache — the operator-triggered button is the
        explicit "I want a fresh read NOW" path. Toast level escalates to
        ``warning`` when the new probe shows the guardrail tripped, so the
        operator notices without scanning the panel itself.
        """
        snapshot = get_slot_snapshot(force=True)
        panel_html = render_template("partials/slots.html.j2", slots=snapshot)
        healthy = snapshot["healthy_search_count"]
        total = snapshot["total_slots"]
        level = "warning" if snapshot.get("guardrail_tripped") else "success"
        return action_response(
            panel_html,
            toast_level=level,
            toast_message=f"Slot probe: {healthy}/{total} healthy on search_tweet",
        )

    @app.route("/api/activity")
    def api_activity() -> str:
        """HTMX poll target — returns fragment of new activity rows.

        Each table cursor (``since_logs``, ``since_images``, …) carries the
        newest row id already on screen; this endpoint returns only rows
        strictly newer. Empty response when nothing new.
        """
        since = {
            "logs": _parse_int_arg("since_logs", 0),
            "brief_images": _parse_int_arg("since_images", 0),
            "context_notes": _parse_int_arg("since_notes", 0),
            "analyses": _parse_int_arg("since_analyses", 0),
        }
        ctx = get_activity_context(
            db_path=app.config["DB_PATH"],
            filter=request.args.get("filter"),
            since=since,
            limit=_parse_int_arg("limit", 20),
        )
        # Return only the row groups — no header/filter/poll-target wrapping.
        return render_template("partials/_activity_rows_only.html.j2", activity=ctx)

    return app
