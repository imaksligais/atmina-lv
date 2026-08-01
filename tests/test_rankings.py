"""Tests for src.render.rankings.fetch_rankings — site-wide discovery ranks.

Builds a tmp DB from the committed render fixture (same pattern as
tests/test_render_chars.py::fixture_db), enriches contradictions via
``src.render.contradictions._fetch_contradictions``, then asserts the
four-key shape + ordering invariants of ``fetch_rankings``. Robust to
empty fixture lists (ordering asserts skipped when fewer than 2 items).
"""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURE_SQL = Path(__file__).parent / "fixtures" / "render_fixture_data.sql"

RANK_KEYS = (
    "most_contradictions",
    "biggest_reversals",
    "most_active_7d",
    "vote_alignment_outliers",
)


@pytest.fixture(scope="module")
def fixture_db(tmp_path_factory):
    """Tmp DB: init_db + Saeima tables + the three prod-drift ALTER shims,
    then load the committed data-only fixture SQL."""
    from src.db import get_db, init_db
    from src.saeima.schema import init_saeima_bills, init_saeima_tables

    db_path = str(tmp_path_factory.mktemp("rankings_fixture_db") / "fixture.db")
    init_db(db_path)
    init_saeima_tables(db_path)
    init_saeima_bills(db_path)
    conn = get_db(db_path)
    for ddl in (
        "ALTER TABLE tracked_politicians ADD COLUMN x_handle TEXT",
        "ALTER TABLE documents ADD COLUMN is_paywall BOOLEAN DEFAULT FALSE",
        "ALTER TABLE documents ADD COLUMN summary TEXT",
    ):
        try:
            conn.execute(ddl)
        except Exception:  # noqa: BLE001 — column already present if schema synced
            pass
    conn.executescript(FIXTURE_SQL.read_text(encoding="utf-8"))
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture(scope="module")
def rankings(fixture_db):
    from src.db import get_db
    from src.render.contradictions import _fetch_contradictions
    from src.render.rankings import fetch_rankings

    db = get_db(fixture_db)
    contradictions = _fetch_contradictions(db)
    return fetch_rankings(db, contradictions)


def test_four_keys_present(rankings):
    assert set(rankings.keys()) == set(RANK_KEYS)


def test_each_value_is_a_list(rankings):
    for key in RANK_KEYS:
        assert isinstance(rankings[key], list), f"{key} must be a list"


def test_every_item_has_slug_and_party_color(rankings):
    for key in RANK_KEYS:
        for item in rankings[key]:
            assert "slug" in item, f"{key} item missing 'slug': {item}"
            assert "party_color" in item, f"{key} item missing 'party_color': {item}"


def test_most_contradictions_non_increasing_by_count(rankings):
    items = rankings["most_contradictions"]
    if len(items) < 2:
        pytest.skip("fewer than 2 items — ordering not testable")
    counts = [i["count"] for i in items]
    assert counts == sorted(counts, reverse=True), counts


def test_biggest_reversals_non_increasing_by_delta_days(rankings):
    items = rankings["biggest_reversals"]
    if len(items) < 2:
        pytest.skip("fewer than 2 items — ordering not testable")
    deltas = [i["delta_days"] for i in items]
    assert deltas == sorted(deltas, reverse=True), deltas


def test_biggest_reversals_items_have_expected_fields(rankings):
    for item in rankings["biggest_reversals"]:
        for field in ("id", "name", "topic", "delta_days", "severity_lv", "severity_glyph"):
            assert field in item, f"biggest_reversals item missing {field!r}: {item}"
        assert item["delta_days"] is not None


def test_every_item_has_bool_has_photo(rankings):
    for key in RANK_KEYS:
        for item in rankings[key]:
            assert "has_photo" in item, f"{key} item missing 'has_photo': {item}"
            assert isinstance(item["has_photo"], bool), f"{key} has_photo not bool: {item}"


def test_has_photo_derivation(tmp_path, monkeypatch):
    """`_has_photo` is True only when assets/photos/<slug>.jpg exists.

    Hermetic: points ASSETS_DIR at a tmp dir and drops a single photo, so
    the derivation is exercised without touching the real assets tree."""
    import src.render.rankings as rankings_mod

    photos = tmp_path / "photos"
    photos.mkdir()
    (photos / "janis-berzins.jpg").write_bytes(b"x")
    monkeypatch.setattr(rankings_mod, "ASSETS_DIR", tmp_path)

    assert rankings_mod._has_photo("janis-berzins") is True
    assert rankings_mod._has_photo("nav-tada-slug") is False


def test_vote_alignment_outliers_non_increasing_agreement(rankings):
    items = rankings["vote_alignment_outliers"]
    if len(items) < 2:
        pytest.skip("fewer than 2 items — ordering not testable")
    # Lowest agreement first.
    pcts = [i["agree_pct"] for i in items]
    assert pcts == sorted(pcts), pcts
    for item in items:
        assert item["sample"] >= 50
