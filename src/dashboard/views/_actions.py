"""HTMX action response helper — keeps the panel-swap + toast wiring DRY.

Tasks 2.2–2.4 each return an updated panel fragment AND fire a toast on
success/failure. Per HTMX convention, the toast payload travels in the
``HX-Trigger`` response header as JSON; ``ops.js`` listens for the
``showToast`` custom event and pops a slide-in toast.

Two response shapes:

1. Plain panel swap (no toast):
       return action_response(panel_html)

2. Panel swap + toast:
       return action_response(panel_html,
                              toast_level="success",
                              toast_message="Image #N apstiprināts")
"""
from __future__ import annotations

import json

from flask import Response, make_response


def action_response(
    panel_html: str,
    *,
    toast_level: str = "success",
    toast_message: str = "",
) -> Response:
    """Build a Flask response combining a panel HTML body with an optional toast.

    Args:
        panel_html: rendered partial that HTMX will swap into the page.
        toast_level: one of ``success``, ``warning``, ``danger``, ``info``.
            Picks the CSS status palette in ``ops.css``.
        toast_message: visible toast text. When empty, no HX-Trigger header
            is emitted (the toast simply doesn't fire).
    """
    resp = make_response(panel_html)
    if toast_message:
        resp.headers["HX-Trigger"] = json.dumps({
            "showToast": {"level": toast_level, "message": toast_message}
        })
    return resp
