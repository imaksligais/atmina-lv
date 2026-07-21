"""View helpers for atmina ops dashboard panels.

Each view module exposes pure functions that return panel context dicts —
no Flask coupling, no template rendering. Server routes compose contexts
and hand them off to Jinja partials.
"""
