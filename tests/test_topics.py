"""Tests for the Tēmas (topic) destination pages — ``src.render.topics``.

Builds the committed render fixture DB (same pattern as
``tests/test_render_chars.py``), wires a minimal Jinja env with the same
filters/globals the orchestrator registers, runs ``render_topics`` into a
tmp dir, and asserts the directory page + one detail page per non-empty
canonical topic group.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import quote

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
    _slugify,
)
from src.render.syntheses import _normalize_synthesis_topics
from src.render.topics import RELATED_TOPICS, _fetch_topics, render_topics
from src.topic_map import TOPIC_GROUPS

# Fikstūra glabājas gzipēta (6.3, 2026-09-05); atspiestais teksts ir
# baitu-identisks iepriekš komitētajam .sql — sk. tests/fixture_sql.py.
from tests.fixture_sql import load_render_fixture_sql


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
    conn.executescript(load_render_fixture_sql())
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


# ── A3: sintēžu piesaiste tēmas lapai (slug vai kanoniskais nosaukums) ──


def _synthesis(topics, slug="test-sinteze", title="Testa sintēze"):
    """Minimāla sintēzes vārdnīca render_topics(syntheses=...) formā."""
    return {
        "slug": slug,
        "title": title,
        "description": "Apraksts",
        "created": "2026-04-22",
        "politicians": [],
        "topics": topics,
        "content_html": "",
        "toc": [],
        "image_filename": None,
        "image_light_filename": None,
        "og_image_version": None,
    }


def _render_topic_page(fixture_db, tmp_path, name, syntheses=None):
    env = _build_env()
    atmina_dir = tmp_path / "atmina"
    atmina_dir.mkdir(parents=True, exist_ok=True)
    render_topics(env, fixture_db, atmina_dir, syntheses=syntheses)
    return (atmina_dir / "temas" / f"{_slugify(name)}.html").read_text(encoding="utf-8")


def test_slug_form_synthesis_topics_attach_to_topic_page(fixture_db, tmp_path):
    """Frontmatter slugs (``koalicija-un-partijas``) ir jāatrisina uz
    kanonisko nosaukumu — pirms 2026-09-06 8 no 9 sintēzēm nepiesaistījās
    nevienai tēmas lapai."""
    syn = _synthesis(_normalize_synthesis_topics(
        ["koalicija-un-partijas"], "test.md"
    ))
    assert syn["topics"] == ["Koalīcija un partijas"]
    html = _render_topic_page(
        fixture_db, tmp_path, "Koalīcija un partijas", syntheses=[syn]
    )
    assert "Saistītās sintēzes" in html
    assert "Testa sintēze" in html
    assert 'href="../sintezes/test-sinteze.html"' in html


def test_canonical_name_form_still_attaches(fixture_db, tmp_path):
    """Nosaukuma forma (``airBaltic``) strādāja jau iepriekš — nesalauzt."""
    syn = _synthesis(_normalize_synthesis_topics(["Koalīcija un partijas"], "test.md"))
    assert syn["topics"] == ["Koalīcija un partijas"]
    html = _render_topic_page(
        fixture_db, tmp_path, "Koalīcija un partijas", syntheses=[syn]
    )
    assert "Testa sintēze" in html


def test_unknown_synthesis_topic_warns_and_does_not_attach(
    fixture_db, tmp_path, capsys
):
    """Neatpazīta vērtība: brīdinājums uz stderr, vērtība paliek sarakstā
    (nekas netiek klusi izmests), bet nevienai tēmas lapai nepiesaistās."""
    topics = _normalize_synthesis_topics(["nav-tadas-temas"], "test.md")
    err = capsys.readouterr().err
    assert "nav-tadas-temas" in err
    assert "test.md" in err
    assert topics == ["nav-tadas-temas"]  # saglabāts, ne izmests

    syn = _synthesis(topics)
    html = _render_topic_page(
        fixture_db, tmp_path, "Koalīcija un partijas", syntheses=[syn]
    )
    assert "Testa sintēze" not in html


def test_repo_syntheses_all_resolve_to_canonical_topics():
    """Denominatora vārti: VISAS wiki/synthesis/*.md tēmu vērtības atrisinās
    uz kanonisku grupu. Tukšs saraksts = salūzuši vārti, ne tīrs rezultāts."""
    from src.render._common import _parse_frontmatter

    files = sorted(Path("wiki/synthesis").glob("*.md"))
    assert len(files) >= 9, "sintēžu mape tukša → vārti nav pierādījums"
    total = 0
    for md in files:
        fm, _ = _parse_frontmatter(md.read_text(encoding="utf-8"))
        raw = fm.get("topics") or []
        for value in _normalize_synthesis_topics(raw, md.name):
            total += 1
            assert value in TOPIC_GROUPS, f"{md.name}: neatrisināta tēma {value!r}"
    assert total >= 27


# ── A4: saistīto tēmu karte ──


def test_related_topics_map_is_canonical():
    """Katra RELATED_TOPICS atslēga un vērtība ir kanonisks TOPIC_GROUPS
    nosaukums — drukas kļūda te nozīmētu klusi ignorētu ierakstu."""
    assert RELATED_TOPICS, "tukša karte = nepārbaudāmi vārti"
    for key, values in RELATED_TOPICS.items():
        assert key in TOPIC_GROUPS, f"nekanoniska atslēga: {key!r}"
        assert values, f"{key}: tukšs saistīto tēmu saraksts"
        for value in values:
            assert value in TOPIC_GROUPS, f"{key}: nekanoniska vērtība {value!r}"
            assert value != key


def test_mapped_related_topics_lead_the_citas_temas_column(fixture_db, tmp_path):
    """Kartētās tēmas iet pa priekšu top-5 aizpildījumam, un kolonna paliek
    5 ierakstu gara."""
    from src.render.topics import _fetch_topic_detail, _fetch_topics

    # all_topics tiek papildināts ar kartes tēmām, ja fikstūrā to nav —
    # citādi vārti klusi izlaistu (0 denominators nav tīrs rezultāts).
    all_topics = _fetch_topics(fixture_db)
    have = {t["name"] for t in all_topics}
    for extra in ["airBaltic", *RELATED_TOPICS["airBaltic"]]:
        if extra not in have:
            all_topics.append({
                "name": extra, "slug": _slugify(extra), "color": "#8b8fa3",
                "position_count": 1, "contradiction_count": 0,
                "politician_count": 1,
            })
            have.add(extra)
    names = have
    detail = _fetch_topic_detail(
        fixture_db, "airBaltic", syntheses=[], all_topics=all_topics
    )
    column = next(
        c for c in detail["keep_digging"]["columns"] if c["title"] == "Citas tēmas"
    )
    labels = [link["label"] for link in column["links"]]
    expected = [t for t in RELATED_TOPICS["airBaltic"] if t in names]
    assert labels[:len(expected)] == expected
    assert len(labels) == min(5, len(names) - 1)
    assert "airBaltic" not in labels
    assert len(labels) == len(set(labels))


# ── A1/A2: arhīva saite + ?tema= uz profiliem ──


def test_positions_archive_link_uses_encoded_canonical_topic(fixture_db, tmp_path):
    """Saite uz pozicijas.html nes URL-kodētu KANONISKO nosaukumu — pzv1.js
    dekodē un salīdzina precīzi (reģistrjutīgi)."""
    from src.render.topics import _fetch_topics

    name = "Koalīcija un partijas"
    count = next(t["position_count"] for t in _fetch_topics(fixture_db)
                 if t["name"] == name)
    html = _render_topic_page(fixture_db, tmp_path, name)
    enc = quote(name, safe="/")
    assert f'href="../pozicijas.html?tema={enc}"' in html
    if count > 15:
        assert f"Skatīt visas {count} pozīcijas arhīvā" in html
        assert "Rādītas jaunākās 15 pozīcijas" in html
    else:
        assert f"Skatīt {count} pozīcijas ar filtriem" in html
        assert "Rādītas jaunākās 15 pozīcijas" not in html
    # Nekodēta diakritika adresē būtu bojāta saite.
    assert f"?tema={name}" not in html


def test_profile_links_carry_the_tema_param_and_pozicijas_hash(fixture_db, tmp_path):
    """Personu saites tēmas lapā nes ?tema= UN #pozicijas — ppv1.js cilni ņem
    no hash, filtru no parametra. Bez hash profils atvērtos Pārskatā ar
    iezīmētu tēmu, bet nepareizā cilnē (operatora novērojums 2026-09-07)."""
    name = "Koalīcija un partijas"
    enc = quote(name, safe="/")
    html = _render_topic_page(fixture_db, tmp_path, name)
    assert 'class="tema-politiks" href="../politiki/' in html
    assert f'.html?tema={enc}#pozicijas"' in html
    # Neviena profila saite bez parametra un bez hash — arī "Turpini rakt".
    links = re.findall(r'href="\.\./politiki/([^"]+)"', html)
    assert len(links) >= 2, links
    for href in links:
        assert href.endswith(f".html?tema={enc}#pozicijas"), href


def test_synthesis_card_shows_a_formatted_date(fixture_db, tmp_path):
    syn = _synthesis(_normalize_synthesis_topics(["koalicija-un-partijas"], "t.md"))
    html = _render_topic_page(
        fixture_db, tmp_path, "Koalīcija un partijas", syntheses=[syn]
    )
    assert '<time datetime="2026-04-22">22.04.2026</time>' in html


def test_top_politicians_label_renamed(fixture_db, tmp_path):
    html = _render_topic_page(fixture_db, tmp_path, "Koalīcija un partijas")
    assert "Visvairāk fiksēto pozīciju" in html
    assert "Top politiķi par tēmu" not in html
    assert "Visvairāk pozīciju" in html  # "Turpini rakt" kolonna
