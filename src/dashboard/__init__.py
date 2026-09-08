"""atmina ops — localhost operator dashboard.

Flask app at http://127.0.0.1:8080. Read-only telemetry + a small set of
write actions (image approve/reject, slot probe refresh, deploy) wired
behind confirm modals. See `wiki/operations/atmina-ops.md` for the runbook.
"""

from src.dashboard.server import create_app

__all__ = ["create_app"]
