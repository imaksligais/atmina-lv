"""Regression test for the preflight DB-path default.

The old default was the legacy ``politracker.db``: ``preflight_check()`` ran
``init_db()`` on it (creating an empty legacy file) and then validated the
tables it had just created, never inspecting the real operational DB. Because
``src/ingest.py`` calls ``preflight_check()`` with no argument, a no-arg call
must resolve the canonical ``DB_PATH`` (``data/atmina.db``).

The signature default is now ``None`` (late-bound, resolved at CALL time via
``get_db`` — so ``monkeypatch.setattr(db, "DB_PATH", ...)`` is honored rather
than baked in at import). This test therefore asserts the *behavior* — a
no-arg call targets whatever ``DB_PATH`` resolves to at call time, and never
the legacy ``politracker.db`` — instead of the def-time default value.
"""
from __future__ import annotations

import inspect

from src import preflight as preflight_module
from src.db import DB_PATH
from src.preflight import preflight_check


def test_preflight_default_is_late_bound_none():
    # Default is None (call-time resolution), NOT a baked-in path.
    default = inspect.signature(preflight_check).parameters["db_path"].default
    assert default is None
    # The canonical target is still atmina.db, never the legacy file.
    assert DB_PATH == "data/atmina.db"
    assert "politracker" not in DB_PATH


def test_preflight_no_arg_targets_monkeypatched_db(tmp_path, monkeypatch):
    """A no-arg preflight_check() must init/read the resolved DB_PATH, not a
    legacy politracker.db. Patching DB_PATH must take effect (late binding)."""
    from src import db as db_module

    db_path = tmp_path / "atmina.db"
    monkeypatch.setattr(db_module, "DB_PATH", str(db_path))

    # No db_path argument — exercises the late-bound default.
    preflight_check()

    # init_db ran against the patched path, creating THAT file (and never a
    # legacy politracker.db in cwd).
    assert db_path.exists()
    assert not (tmp_path / "politracker.db").exists()
