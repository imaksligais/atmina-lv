"""tests/conftest.py § 5 — the stale get_db binding guard must see a leak.

Failure it exists for (2026-10-01): a fixture patched src.db.get_db and then
first-imported src.social → src.matcher, which bound the stub for the rest of
the run; tests/test_matcher.py then failed 15 baseline cases, but only when
run after tests/test_social.py.
"""
from __future__ import annotations

import sys
import types

import src.db as db_mod
from tests.conftest import repair_stale_get_db_bindings


def test_guard_finds_and_repairs_a_module_bound_to_a_stub():
    real = db_mod.get_db
    fake = types.ModuleType("src._get_db_guard_probe")
    fake.get_db = lambda *a, **k: None  # a stub captured at first import
    sys.modules[fake.__name__] = fake
    try:
        assert repair_stale_get_db_bindings(real) == [fake.__name__]
        assert fake.get_db is real
        assert repair_stale_get_db_bindings(real) == []
    finally:
        del sys.modules[fake.__name__]


def test_guard_ignores_modules_outside_src_and_without_get_db():
    real = db_mod.get_db
    other = types.ModuleType("not_src_probe")
    other.get_db = lambda: None
    plain = types.ModuleType("src._no_get_db_probe")
    sys.modules[other.__name__] = other
    sys.modules[plain.__name__] = plain
    try:
        assert repair_stale_get_db_bindings(real) == []
    finally:
        del sys.modules[other.__name__], sys.modules[plain.__name__]
