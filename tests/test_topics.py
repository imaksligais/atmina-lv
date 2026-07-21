"""Tests for the Tēmas (topic) destination pages — ``src.render.topics``.

Builds the committed render fixture DB (same pattern as
``tests/test_render_chars.py``), wires a minimal Jinja env with the same
filters/globals the orchestrator registers, runs ``render_topics`` into a
tmp dir, and asserts the directory page + one detail page per non-empty
canonical topic group.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader

from src.image_variants import variant_filename as _brief_image_variant
from src.render import _common
from src.render._common import (
    _autolink_bills_filter,
    _lv_plural,
    _party_short_name,
    _safe_json_filter,
    _safe_url_filter,
)
from src.render.topics import _fetch_topics, render_topics

FIXTURE_SQL = Path(__file__).parent / "fixtures" / "render_fixture_data.sql"


@pytest.fixture
def fixture_db(tmp_path_factory):
    """Build a tmp DB from the committed fixture SQL.

    Mirrors ``tests/test_render_chars.py::fixture_db`` — static schema from
    init_db + Saeima tables, plus the three live-only columns added so the
    test DB faithfully mirrors prod, then the data-only INSERTs.
    """
    from src.db import get_db, init_db
    from src.saeima.schema import init_saeima_bills, init_saeima_tables

    db_path = str(tmp_path_factory.mktemp("topics_fixture_db") / "fixture.db")
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
        except Exception:  # noqa: BLE001 — column already present if schema is later synced
            pass
    conn.executescript(FIXTURE_SQL.read_text(encoding="utf-8"))
    conn.commit()
    return conn


def _build_env() -> Environment:
    """Jinja env with the same filters/globals the orchestrator registers
    (src/render/_orchestrator.py ~lines 286-299)."""
    env = Environment(
        loader=FileSystemLoader(_common.TEMPLATES_DIR),
        autoescape=True,
    )
    env.filters["lv_date"] = lambda s: (
        f"{s[8:10]}.{s[5:7]}.{s[:4]}" if s and len(s) >= 10 and "-" in s else s or ""
    )
    env.filters["safe_json"] = _safe_json_filter
    env.filters["safe_url"] = _safe_url_filter
    env.filters["autolink_bills"] = _autolink_bills_filter
    env.filters["image_variant"] = _brief_image_variant
    env.filters["lv_plural"] = _lv_plural
    env.globals["_party_short_name"] = _party_short_name
    env.globals["bill_slugs"] = set()
    env.globals["assets_version"] = "test"
    return env


def test_render_topics_emits_directory_and_detail_pages(fixture_db, tmp_path):
    env = _build_env()
    atmina_dir = tmp_path / "atmina"
    atmina_dir.mkdir(parents=True)

    count = render_topics(env, fixture_db, atmina_dir)

    non_empty = _fetch_topics(fixture_db)
    assert non_empty, "fixture should yield at least one non-empty topic group"

    # Directory page exists.
    temas_index = atmina_dir / "temas.html"
    assert temas_index.exists()

    # One detail page per non-empty group; returned count == 1 + groups.
    detail_files = sorted((atmina_dir / "temas").glob("*.html"))
    assert len(detail_files) == len(non_empty)
    assert count == 1 + len(non_empty)

    # Each non-empty group's slug has a corresponding detail file.
    rendered_slugs = {p.stem for p in detail_files}
    assert rendered_slugs == {t["slug"] for t in non_empty}


def test_topic_detail_page_contains_topic_name(fixture_db, tmp_path):
    env = _build_env()
    atmina_dir = tmp_path / "atmina"
    atmina_dir.mkdir(parents=True)

    render_topics(env, fixture_db, atmina_dir)

    # "Koalīcija un partijas" is the busiest fixture topic (45 positions).
    from src.render._common import _slugify

    slug = _slugify("Koalīcija un partijas")
    page = atmina_dir / "temas" / f"{slug}.html"
    assert page.exists()
    text = page.read_text(encoding="utf-8")
    assert "Koalīcija un partijas" in text


def test_directory_page_lists_topic_cards(fixture_db, tmp_path):
    env = _build_env()
    atmina_dir = tmp_path / "atmina"
    atmina_dir.mkdir(parents=True)

    render_topics(env, fixture_db, atmina_dir)

    text = (atmina_dir / "temas.html").read_text(encoding="utf-8")
    non_empty = _fetch_topics(fixture_db)
    # Directory links to each non-empty topic's detail page.
    for t in non_empty:
        assert f'href="temas/{t["slug"]}.html"' in text


def test_fetch_topics_only_non_empty_groups(fixture_db):
    topics = _fetch_topics(fixture_db)
    for t in topics:
        assert t["position_count"] >= 1 or t["contradiction_count"] >= 1
        # Required keys per the interface contract.
        assert set(t) >= {
            "name", "slug", "color", "position_count",
            "contradiction_count", "politician_count",
        }
    # Sorted non-increasing by position_count.
    counts = [t["position_count"] for t in topics]
    assert counts == sorted(counts, reverse=True)
