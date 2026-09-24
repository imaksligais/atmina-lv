"""Latvia time follows Europe/Riga DST (2026-09-24, before the 2026-10-25 switch).

Until 2026-09-24 `now_lv()` added a fixed `timedelta(hours=3)`, so from the last
Sunday of October every LV timestamp, the 05:00 routine-day cut and
`claims.review_status_at` would have run one hour ahead.
"""
from datetime import datetime, timezone
import sqlite3

import pytest

from src.db import utc_to_lv


@pytest.mark.parametrize("utc,lv", [
    ("2026-09-23 10:00:00", "2026-09-23 13:00:00"),  # EEST +3
    ("2026-10-25 00:59:59", "2026-10-25 03:59:59"),  # pēdējā vasaras sekunde
    ("2026-10-25 01:00:00", "2026-10-25 03:00:00"),  # EET +2 (pāreja 04:00 LV → 03:00)
    ("2026-12-01 10:00:00", "2026-12-01 12:00:00"),
    ("2027-03-28 01:00:00", "2027-03-28 04:00:00"),  # atpakaļ uz EEST
])
def test_utc_to_lv_follows_riga_dst(utc, lv):
    got = utc_to_lv(datetime.fromisoformat(utc))
    assert got.strftime("%Y-%m-%d %H:%M:%S") == lv
    assert got.tzinfo is None


def test_utc_to_lv_accepts_aware():
    dt = datetime(2026, 12, 1, 10, tzinfo=timezone.utc)
    assert utc_to_lv(dt).hour == 12


@pytest.mark.parametrize("utc", ["2026-07-01 10:00:00", "2026-12-01 10:00:00"])
def test_sqlite_localtime_matches_riga(utc):
    """Trigeris un routine.py lieto SQLite 'localtime' — tas ir pareizs TIKAI,
    ja mašīnas TZ ir Europe/Riga. Ja šis tests krīt, mašīnas laika josla nav
    Rīga un review_status_at / analīzes soļa salīdzinājums ir nobīdīts."""
    got = sqlite3.connect(":memory:").execute(
        "SELECT datetime(?, 'localtime')", (utc,)).fetchone()[0]
    assert got == utc_to_lv(datetime.fromisoformat(utc)).strftime("%Y-%m-%d %H:%M:%S"), (
        "Mašīnas TZ nav Europe/Riga — SQLite 'localtime' neatbilst LV laikam")


def test_review_status_at_expr_is_localtime():
    from src.db import _REVIEW_STATUS_AT_EXPR
    assert "localtime" in _REVIEW_STATUS_AT_EXPR and "+3" not in _REVIEW_STATUS_AT_EXPR
