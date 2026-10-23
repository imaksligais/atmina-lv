"""Sākumlapas josla „Jaunākais" (spec 2026-09-20-landing-jaunakais-design.md).

Tīrā funkcija ``latest_strip`` + šablona līgums: joslas pārskats neatkārtojas
sadaļā „Jaunākie pārskati", joslas analīze — sadaļā „Vairāk analīžu".
"""

from __future__ import annotations

from jinja2 import Environment, FileSystemLoader

from src.render._common import _safe_json_filter, _safe_url_filter
from src.render.dashboard import analysis_items, latest_strip

TODAY = "2026-09-20"

BRIEFS = [
    {"slug": "2026-09-20", "date": "2026-09-20", "note_type": "daily_brief", "type_label": "Dienas pārskats",
     "headline": "Virsraksts A", "title": "Dienas pārskats 2026-09-20", "image_filename": "a.png",
     "preview": "Pirmais Galvenais punkts kā kopsavilkums."},
    {"slug": "2026-09-19", "date": "2026-09-19", "note_type": "daily_brief", "type_label": "Dienas pārskats",
     "headline": None, "title": "Dienas pārskats 2026-09-19", "image_filename": None},
    {"slug": "nedela-2026-09-14", "date": "2026-09-14", "note_type": "weekly_brief", "type_label": "Nedēļas pārskats",
     "headline": "Nedēļa", "title": "Nedēļas pārskats", "image_filename": "w.png"},
    {"slug": "2026-09-13", "date": "2026-09-13", "note_type": "daily_brief", "type_label": "Dienas pārskats",
     "headline": "Vecs", "title": "Dienas pārskats 2026-09-13", "image_filename": None},
]
ANALYSES = [{"url": "analizes/vad.html", "title": "VID izmeklēšana", "description": "Apraksts", "date": "2026-09-19",
             "image_filename": "vad.png", "image_light_filename": "vad-light.png"}]
SYNTHESES = [{"slug": "sint", "title": "Sintēze S", "description": "", "created": "2026-08-01 10:00",
              "image_filename": None, "image_light_filename": None}]


def test_analysis_items_sorted_by_date_across_types():
    items = analysis_items(ANALYSES, SYNTHESES)
    assert [i["title"] for i in items] == ["VID izmeklēšana", "Sintēze S"]
    assert items[0]["kind"] == "analysis" and items[1]["kind"] == "synthesis"


def test_latest_strip_takes_first_brief_and_first_analysis_with_is_new():
    s = latest_strip(BRIEFS, analysis_items(ANALYSES, SYNTHESES), TODAY)
    assert s["brief"]["slug"] == "2026-09-20" and s["brief"]["is_new"] is True
    assert s["brief"]["headline"] == "Virsraksts A"
    assert s["analysis"]["title"] == "VID izmeklēšana" and s["analysis"]["is_new"] is True


def test_latest_strip_is_new_boundary_is_seven_days():
    old_brief = [dict(BRIEFS[0], date="2026-09-12", slug="2026-09-12")]
    s = latest_strip(old_brief, analysis_items(ANALYSES, []), TODAY)
    assert s["brief"]["is_new"] is False
    s7 = latest_strip([dict(BRIEFS[0], date="2026-09-13")], [], TODAY)
    assert s7["brief"]["is_new"] is True


def test_latest_strip_brief_without_headline_falls_back_to_title():
    s = latest_strip(BRIEFS[1:], [], TODAY)
    assert s["brief"]["headline"] == "Dienas pārskats 2026-09-19"


def test_latest_strip_analysis_only_and_empty():
    s = latest_strip([], analysis_items(ANALYSES, []), TODAY)
    assert s["brief"] is None and s["analysis"]["title"] == "VID izmeklēšana"
    assert latest_strip([], [], TODAY) is None


def test_latest_strip_does_not_mutate_inputs():
    items = analysis_items(ANALYSES, [])
    latest_strip(BRIEFS, items, TODAY)
    assert "is_new" not in BRIEFS[0] and "is_new" not in items[0]


# ── šablona līgums ───────────────────────────────────────────────────────

def _env() -> Environment:
    env = Environment(loader=FileSystemLoader("templates"), autoescape=True)
    env.filters["safe_json"] = _safe_json_filter
    env.filters["safe_url"] = _safe_url_filter
    env.filters["lv_date"] = lambda s: s or ""
    env.filters["lv_plural"] = lambda n, *a, **k: ""
    env.filters["autolink_bills"] = lambda s, *a, **k: s
    env.filters["image_variant"] = lambda s, *a, **k: s
    env.globals["assets_version"] = "test"
    return env


def _render(**ctx) -> str:
    base = dict(stats={}, days_until_election=10, focus={}, hero_items=[], rankings={},
                week_summary={}, recent_votes=[], recent_briefs=[], trends_data={},
                BASE_URL="https://atmina.lv", latest=None, more_analyses=[])
    base.update(ctx)
    return _env().get_template("index.html.j2").render(**base)


def _block(html: str, cls: str) -> str:
    """Bloka HTML no atverošā taga līdz zināmajam nākamajam blokam
    (nestingu nelasām — robeža pie nākamā bloka pietiek)."""
    stops = {"latest-strip": ('class="hero-feature"', 'class="hero-v2-metrics'),
             "brief-featured-grid": ("</section>",),
             "analysis-feed": ("</section>",)}[cls]
    i = html.find(f'class="{cls}')
    assert i >= 0, f"bloks {cls} nav izrenderēts"
    ends = [e for e in (html.find(s, i) for s in stops) if e >= 0]
    return html[i:min(ends)] if ends else html[i:]


def test_strip_renders_between_entry_nav_and_carousel_and_dedups_sections():
    items = analysis_items(ANALYSES, SYNTHESES)
    latest = latest_strip(BRIEFS, items, TODAY)
    html = _render(latest=latest, recent_briefs=BRIEFS[1:4], more_analyses=items[1:3],
                   hero_items=[{"kind": "contradiction", "item": {}}])
    strip = _block(html, "latest-strip")
    assert 'href="blog/2026-09-20.html"' in strip and "Virsraksts A" in strip
    assert "Pirmais Galvenais punkts kā kopsavilkums." in strip  # pārskatam ir kopsavilkums kā analīzei
    assert 'href="analizes/vad.html"' in strip and "VID izmeklēšana" in strip
    assert strip.count("Jauns") == 2
    assert html.index('class="hero-entry"') < html.index('class="latest-strip"') < html.index('class="hero-feature"')
    grid = _block(html, "brief-featured-grid")
    assert "blog/2026-09-20.html" not in grid and "blog/2026-09-19.html" in grid
    more = _block(html, "analysis-feed")
    assert "VID izmeklēšana" not in more and "Sintēze S" in more
    assert "Vairāk analīžu" in html and "fresh-strip" not in html


def test_strip_analysis_only_and_absent():
    items = analysis_items(ANALYSES, [])
    html = _render(latest=latest_strip([], items, TODAY))
    strip = _block(html, "latest-strip")
    assert "latest-card-brief" not in strip and "VID izmeklēšana" in strip
    assert "latest-strip" not in _render(latest=None)
    assert "Vairāk analīžu" not in _render(latest=None, more_analyses=[])
