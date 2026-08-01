"""Regression tests for compact, neutral daily/weekly brief presentation."""

from jinja2 import Environment, FileSystemLoader

from src.image_variants import variant_filename as _brief_image_variant
from src.render._common import _lv_plural
from src.render import blog


def _template_env() -> Environment:
    env = Environment(loader=FileSystemLoader("templates"), autoescape=True)
    env.filters["image_variant"] = _brief_image_variant
    env.filters["lv_plural"] = _lv_plural
    env.globals["assets_version"] = "test"
    return env


def _daily_post(**overrides):
    post = {
        "title": "Dienas analīze — 2026-08-14",
        "display_title": "Dienas analīze",
        "headline": None,
        "type_label": "Dienas pārskats",
        "date": "2026-08-14",
        "date_slug": "2026-08-14",
        "created_at": "2026-08-14 23:00:00",
        "image_filename": None,
        "preview": "",
        "footer": {
            "doc_count": 3,
            "web": 1,
            "twitter": 1,
            "mentions": 1,
            "positions": 2,
            "votes": 0,
            "contradictions": 0,
            "updated": "14.08.2026 23:00",
        },
    }
    post.update(overrides)
    return post


def test_daily_stats_marker_is_canonical_position_count():
    plural = (
        "# Dienas analīze — 2026-08-14\n\n"
        "<!-- DIENAS STATS: 840 dokumenti · 40 pozīcijas "
        "(33 politiķu + 7 auditorijas) · 0 pretrunas -->\n\n"
        "## Galvenās tēmas\n"
    )
    singular = "<!-- DIENAS STATS: 3 dokumenti · 1 pozīcija · 0 pretrunas -->"
    singular_with_later_plural = singular + "\n<p>Citur · 5 pozīcijas.</p>"

    assert blog._parse_daily_position_count(plural) == 40
    assert blog._parse_daily_position_count(singular) == 1
    assert blog._parse_daily_position_count(singular_with_later_plural) == 1
    assert blog._parse_daily_position_count("# Vecs pārskats bez marķiera") is None


def test_brief_tables_are_wrapped_in_local_scroll_containers():
    table = "<table><tr><td>Garš saturs</td></tr></table>"

    for is_weekly in (False, True):
        html = blog._prepare_brief_html(table, is_weekly=is_weekly)
        assert html == f'<div class="table-scroll">{table}</div>'


def test_daily_topic_tables_are_collapsed_but_summary_tables_stay_open():
    content = (
        "<h2>Aktīvākie politiķi</h2><table><tr><td>A</td></tr></table>"
        "<h2>Galvenās tēmas</h2>"
        "<h3>airBaltic (2 pozīcijas)</h3>"
        "<table><tr><td>Pozīcija</td></tr></table>"
        "<p>Īsa sintēze.</p>"
        "<table><tr><td>Otrs avotu bloks</td></tr></table>"
        "<h2>Koalīcija vs Opozīcija</h2>"
        "<table><tr><td>Bloks</td></tr></table>"
    )

    html = blog._prepare_brief_html(content, is_weekly=False)

    assert html.count('class="brief-topic-details"') == 2
    assert "Visas pozīcijas un avoti" in html
    details_start = html.index('class="brief-topic-details"')
    assert html.index("Īsa sintēze.") < details_start
    details_end = html.index("</details>", details_start)
    assert "Pozīcija" in html[details_start:details_end]
    assert "Aktīvākie politiķi" not in html[details_start:details_end]
    assert "Bloks" not in html[details_start:details_end]


def test_weekly_tables_are_not_collapsed():
    content = (
        "<h2>Galvenās tēmas</h2>"
        "<table><tr><td>Nedēļas dati</td></tr></table>"
    )

    html = blog._prepare_brief_html(content, is_weekly=True)

    assert "brief-topic-details" not in html
    assert 'class="table-scroll"' in html


def test_daily_footer_labels_canonical_visible_position_count():
    """Footer states that the count covers the positions shown in the brief."""
    html = _template_env().get_template("blog-post.html.j2").render(
        post=_daily_post(),
        content_html="<p>Saturs.</p>",
        toc=None,
        prev_post=None,
        next_post=None,
        latest_analysis=None,
        BASE_URL="https://atmina.lv",
    )

    assert "Pārskatā iekļautās pozīcijas:</strong> 2" in html
    assert "2 pārskatā iekļautās pozīcijas" not in html
    assert "2 jaunas pozīcijas" not in html
    assert "2 politiķu pozīcijas" not in html
