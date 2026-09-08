"""Sākumlapas sākumpunkti un etiķetes (T2, 2026-09-05).

Pārbauda tikai to, ko maina T2:
  1. zem meklētāja ir trīs parastas saites uz jau esošajām indeksa lapām;
  2. meklēšanas forma ar ``q`` un typeahead avotu paliek neskarta (jaunā
     navigācija NAV otrs meklētājs);
  3. hero kickers ir "No politiskās atmiņas", un "Uzmanības centrā"
     sākumlapā paliek tikai vienu reizi — kompozīta sekcijas H2;
  4. "Visvairāk pretrunu" kartītē ir konteksta atruna.

Renderē ``index.html.j2`` tieši ar minimālu kontekstu (Jinja ``Undefined``
klusē pārējos blokus) — šablona līgums, ne pilna vietnes ģenerēšana.
Atstarpēm un izkārtojumam virkņu testus nerakstām.
"""

from __future__ import annotations

import re

from jinja2 import Environment, FileSystemLoader

from src.render._common import _safe_json_filter, _safe_url_filter

ENTRY_LINKS = [
    ("temas.html", "Izpēti tēmu"),
    ("personas.html", "Atrodi personu"),
    ("partijas.html", "Partiju programmas"),
]

DISCLAIMER = (
    "Skaits attiecas uz mūsu apkopotajiem avotiem un periodu; "
    "tas nav politiķu godīguma vērtējums."
)


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


def _render() -> str:
    """Minimāls konteksts: hero karuselis un pretrunu rangs ieslēgti, pārējais
    tukšs. Rangam vajag divas rindas, lai izrenderētos gan līderis, gan rinda."""
    rank_rows = [
        {"slug": "a-berzins", "name": "A Bērziņš", "count": 5,
         "party_color": "#112233", "has_photo": False},
        {"slug": "b-kalnina", "name": "B Kalniņa", "count": 3,
         "party_color": "#445566", "has_photo": False},
    ]
    return _env().get_template("index.html.j2").render(
        stats={},
        days_until_election=10,
        focus={},
        # Tukšs ``item``: karuseļa kartītes lauki nav šī testa priekšmets —
        # svarīgi tikai, ka hero bloks (un tā kickers) vispār renderējas.
        hero_items=[{"kind": "contradiction", "item": {}}],
        rankings={"most_contradictions": rank_rows},
        week_summary={},
        recent_votes=[],
        recent_briefs=[],
        trends_data={},
        BASE_URL="https://atmina.lv",
    )


def _entry_nav(html: str) -> str:
    m = re.search(r'<nav class="hero-entry".*?</nav>', html, re.S)
    assert m, "sākumpunktu saišu grupa nav izrenderēta"
    return m.group(0)


def test_three_entry_links_present_with_exact_hrefs():
    nav = _entry_nav(_render())
    for href, label in ENTRY_LINKS:
        assert f'href="{href}"' in nav, f"trūkst saites uz {href}"
        assert label in nav, f"trūkst etiķetes “{label}”"


def test_entry_links_work_without_js():
    """Parasti <a href> — bez inline handleriem un bez JS-atkarīgiem atribūtiem.

    CSP jau aizliedz inline JS visā šablonā (tests/test_no_inline_js.py); šeit
    svarīgs ir šaurākais fakts: šīs trīs saites nav pogas, kam vajag skriptu.
    """
    nav = _entry_nav(_render())
    assert not re.search(r"""\son[a-z]+\s*=\s*["']""", nav, re.I)
    assert "<button" not in nav
    assert nav.count("<a ") == len(ENTRY_LINKS)


def test_search_form_survives_next_to_the_new_links():
    """Regresija: jaunā grupa nedrīkst aizstāt meklētāju vai ``q`` parametru."""
    html = _render()
    assert '<form class="hero-search" action="pozicijas.html" method="get"' in html
    assert 'name="q"' in html
    assert 'data-sg-index="data/sg-index.json"' in html  # typeahead avots


def test_hero_kicker_is_no_politiskas_atminas():
    html = _render()
    m = re.search(r'<div class="hero-feature-kicker">(.*?)</div>', html, re.S)
    assert m, "hero kickers nav izrenderēts"
    assert "No politiskās atmiņas" in m.group(1)


def test_uzmanibas_centra_paliek_tikai_kompozita_virsraksta():
    """Viena lieta = viens nosaukums (orķestratora lēmums 2026-09-05)."""
    html = _render()
    assert html.count("Uzmanības centrā") == 1
    assert '<h2 class="section-head-title">Uzmanības centrā</h2>' in html


def test_most_contradictions_card_carries_the_disclaimer():
    html = _render()
    start = html.index("Visvairāk pretrunu")
    end = html.find('<div class="rank-card">', start)
    card = html[start:] if end == -1 else html[start:end]
    assert DISCLAIMER in card, "atruna nav “Visvairāk pretrunu” kartītē"
