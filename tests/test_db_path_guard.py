"""The production DB must be unreachable from tests unless named explicitly.

tests/conftest.py § 4 points every default DB path into a nonexistent
directory. These tests prove the guard is live: if it is removed, a no-arg
get_db() here would open data/atmina.db locally and pass — the exact silent
read that failed only in DB-less public CI (2026-09-13, 09-23, 09-24).
"""
from __future__ import annotations

import sqlite3

import pytest

import src.db as db
import src.render._common.constants as render_constants
import src.wiki_format as wiki_format
from tests.conftest import BLOCKED_DB_PATH


def test_default_paths_point_at_the_blocked_location():
    assert db.DB_PATH == BLOCKED_DB_PATH
    assert render_constants.DEFAULT_DB_PATH == BLOCKED_DB_PATH
    assert wiki_format.DEFAULT_DB_PATH == BLOCKED_DB_PATH
    assert db.PRODUCTION_DB_PATH == "data/atmina.db"


def test_no_arg_get_db_fails_loudly():
    with pytest.raises(sqlite3.OperationalError):
        db.get_db().execute("SELECT 1 FROM claims")


def test_code_reading_the_default_db_fails_instead_of_reading_production():
    # check_confidence_drift kept its own path until 2026-09-24 and read the
    # live DB here while failing in CI. With the guard, a no-arg call fails.
    from src.confidence_drift import check_confidence_drift

    with pytest.raises(sqlite3.OperationalError):
        check_confidence_drift(days=7)
