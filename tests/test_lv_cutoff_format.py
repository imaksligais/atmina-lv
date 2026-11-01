"""Time cutoffs must be compared in the format timestamps are STORED.

Stored timestamps are ``"YYYY-MM-DD HH:MM:SS"`` (``now_lv()``, SQLite's
``CURRENT_TIMESTAMP``) and SQLite compares them as plain strings.
``datetime.isoformat()`` separates with ``"T"``, and ``" "`` (0x20) sorts
before ``"T"`` (0x54) — so any row landing on the cutoff's own DATE was
dropped regardless of its clock time, quietly shortening every window by up
to a day.

The bug hid from local runs because it only bites when the stored timestamp's
date EQUALS the cutoff date. On an LV machine "now" is a day ahead of a
`days=1` cutoff, so it never showed; on the public mirror's UTC CI runner
between 21:00 and 24:00 the dates line up and every fixture document
vanished. These tests pin a fixed clock instead of trusting wall time, so
they fail on any machine, at any hour, if the separator regresses.
"""
from __future__ import annotations

import os
import tempfile
from datetime import datetime, timedelta

import pytest

from src.db import get_db, init_db, lv_cutoff, now_lv


# A deliberately awkward moment: late evening, so a naive UTC/LV mix-up moves
# the DATE, which is exactly what the bug needed.
FIXED_NOW = datetime(2026, 7, 24, 23, 30, 0)

# Inside a days=1 window (15 minutes to spare) but sharing its DATE with the
# cutoff — the exact band the isoformat 'T' used to swallow whole.
BOUNDARY = FIXED_NOW - timedelta(hours=23, minutes=45)


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    try:
        os.unlink(path)
    except PermissionError:
        pass


def test_cutoff_uses_stored_separator_not_isoformat_t():
    cutoff = lv_cutoff(1)
    assert "T" not in cutoff, f"cutoff must not use the isoformat 'T': {cutoff}"
    assert len(cutoff) == 19
    # And it must sort correctly against a stored timestamp.
    assert now_lv() >= cutoff


def test_cutoff_string_orders_against_same_date_timestamp():
    """The exact comparison SQLite performs, on the boundary date."""
    cutoff = (FIXED_NOW - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    same_date_but_later = "2026-07-23 23:45:00"  # inside the window
    assert same_date_but_later >= cutoff

    # The regression, spelled out: with 'T' the very same row falls out.
    broken = (FIXED_NOW - timedelta(days=1)).isoformat()
    assert not (same_date_but_later >= broken)


def _seed(path, scraped_at):
    db = get_db(path)
    db.execute("INSERT INTO tracked_politicians (id, name, party) VALUES (1, 'Tests', 'X')")
    db.execute(
        """INSERT INTO documents (id, content, content_hash, scraped_at, platform)
           VALUES (1, 'saturs lorem ipsum', 'h1', ?, 'web')""",
        (scraped_at,),
    )
    db.execute(
        "INSERT INTO document_politicians (document_id, politician_id, role)"
        " VALUES (1, 1, 'subject')"
    )
    db.commit()
    db.close()


@pytest.fixture
def frozen_clock(monkeypatch):
    """Pin now_lv_dt() everywhere the cutoff helper reads it."""
    from src import db as db_module

    monkeypatch.setattr(db_module, "now_lv_dt", lambda: FIXED_NOW)


def test_pending_politicians_sees_document_on_the_cutoff_date(
    db_path, frozen_clock, monkeypatch
):
    """A document 23h45m old is inside a days=1 window — even though it
    shares its DATE with the cutoff. This is the case CI caught."""
    from src import analyze

    scraped = BOUNDARY.strftime("%Y-%m-%d %H:%M:%S")
    assert scraped[:10] == lv_cutoff(1)[:10], "fixture must sit ON the cutoff date"
    _seed(db_path, scraped)
    monkeypatch.setattr(analyze, "get_db", lambda: get_db(db_path))

    pending = analyze.get_pending_politicians(days=1)

    assert [p["name"] for p in pending] == ["Tests"]


def test_politician_documents_sees_document_on_the_cutoff_date(
    db_path, frozen_clock, monkeypatch
):
    from src import analyze

    scraped = BOUNDARY.strftime("%Y-%m-%d %H:%M:%S")
    _seed(db_path, scraped)
    monkeypatch.setattr(analyze, "get_db", lambda: get_db(db_path))

    docs = analyze.get_politician_documents(1, days=1)

    assert len(docs) == 1


def test_document_older_than_the_window_is_still_excluded(
    db_path, frozen_clock, monkeypatch
):
    """The fix must widen the window back to `days`, not remove the bound."""
    from src import analyze

    scraped = (FIXED_NOW - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
    _seed(db_path, scraped)
    monkeypatch.setattr(analyze, "get_db", lambda: get_db(db_path))

    assert analyze.get_pending_politicians(days=1) == []
    assert analyze.get_politician_documents(1, days=1) == []
