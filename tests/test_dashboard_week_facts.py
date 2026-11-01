"""Šonedēļ joslas fakti: 0 vietā rāda pēdējās aktivitātes datumu (nevis mirušu nulli).

Tīri pure-function testi — nav atkarības no ``data/atmina.db``.
Palīgs saņem pilnu etiķetes frāzi (``pēdējie balsojumi`` / ``pēdējās pretrunas``),
lai locījums saskanētu ar dzimti — fiksēts ``pēdējie`` prefikss to nespētu.
"""
from src.render.dashboard import week_fact


def test_week_fact_zero_uses_last_date():
    assert week_fact(0, "2026-06-11", "pēdējie balsojumi") == {"label": "pēdējie balsojumi", "date": "11.06.2026"}


def test_week_fact_feminine_label():
    assert week_fact(0, "2026-06-11", "pēdējās pretrunas") == {"label": "pēdējās pretrunas", "date": "11.06.2026"}


def test_week_fact_datetime_with_time():
    assert week_fact(0, "2026-06-11 14:32:00", "pēdējie balsojumi") == {"label": "pēdējie balsojumi", "date": "11.06.2026"}


def test_week_fact_nonzero_returns_none():
    assert week_fact(5, "2026-06-11", "pēdējie balsojumi") is None


def test_week_fact_zero_without_date():
    assert week_fact(0, None, "pēdējie balsojumi") is None
