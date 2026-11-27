"""Meklētāja un dalīšanās kartītes identitāte: katrai lapas grupai sava galvene.

Viens end-to-end tests pret visu renderēto fixture vietni. Kļūmes, ko tas ķer:
- lapa renderēta garām ``_render_page`` → bez ``canonical``/``og:url``
  (likumprojekti/likumi, 627 lapas līdz 2026-11-25);
- profila kartīte rāda vispārīgo «atmina.lv — Politiskā atmiņa» un vietnes
  noklusējuma aprakstu;
- pārskata <title> ir noglabātais H1 «Dienas analīze — 2026-11-24», nav
  ``og:type=article`` vai ``dateModified`` nav ISO 8601 ar joslu;
- sitemap ar viltotu «šodien» ``<lastmod>`` katrai lapai.
"""

from __future__ import annotations

import re

from src.render._common.constants import BASE_URL

SITE_DEFAULT_DESC = "atmina.lv — Latvijas politiķu pozīcijas"  # base.html.j2 noklusējuma sākums


def _head(path) -> str:
    return path.read_text(encoding="utf-8").split("</head>", 1)[0]


def _meta(head: str, attr: str, key: str) -> str | None:
    m = re.search(rf'<meta {attr}="{re.escape(key)}" content="([^"]*)"', head)
    return m.group(1) if m else None


def test_page_heads_identify_each_page(rendered_site):
    # 1. Likumprojekti un likumi: canonical + og:url = pašas lapas adrese.
    for section in ("likumprojekti", "likumi"):
        pages = sorted((rendered_site / section).glob("*.html"))
        assert pages, f"{section}/: nav nevienas lapas"
        for page in pages:
            url = f"{BASE_URL}/{section}/{page.name}"
            head = _head(page)
            assert f'<link rel="canonical" href="{url}">' in head, f"nav canonical: {section}/{page.name}"
            assert _meta(head, "property", "og:url") == url, f"nav og:url: {section}/{page.name}"

    # 2. Profils: savs og:title un apraksts, ne vietnes noklusējums.
    profiles = sorted((rendered_site / "politiki").glob("*.html"))
    assert profiles, "politiki/: nav nevienas lapas"
    head = _head(profiles[0])
    name = re.search(r"<title>(.+?) — Politiskā atmiņa</title>", head).group(1)
    assert _meta(head, "property", "og:title") == f"{name} — atmina.lv"
    desc = _meta(head, "name", "description")
    assert desc and desc.startswith(name), f"profila apraksts: {desc!r}"
    assert _meta(head, "property", "og:description") == desc

    # Sākumlapa neatkārto zīmolu divreiz.
    home = _head(rendered_site / "index.html")
    assert _meta(home, "property", "og:title") == "atmina.lv — Politiskā atmiņa"

    # 3. Dienas pārskats: <title> no virsraksta + «Dienas pārskats, DD.MM.YYYY».
    dailies = sorted((rendered_site / "blog").glob("20??-??-??.html"))
    assert dailies, "blog/: nav neviena dienas pārskata"
    page = dailies[-1]
    head = _head(page)
    y, m, d = page.stem.split("-")
    title = re.search(r"<title>(.+?)</title>", head).group(1)
    assert title.endswith(f"Dienas pārskats, {d}.{m}.{y} — Politiskā atmiņa"), f"pārskata title: {title!r}"
    assert "analīze" not in title
    assert _meta(head, "property", "og:type") == "article"
    desc = _meta(head, "name", "description")
    assert desc and not desc.startswith(SITE_DEFAULT_DESC) and "..." not in desc, f"pārskata apraksts: {desc!r}"
    modified = re.search(r'"dateModified": "([^"]+)"', page.read_text(encoding="utf-8"))
    assert modified and re.fullmatch(
        r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\+0[23]:00", modified.group(1)
    ), f"dateModified nav ISO 8601 ar joslu: {modified and modified.group(1)!r}"

    # 4. Sitemap bez viltota <lastmod>.
    sitemap = (rendered_site / "sitemap.xml").read_text(encoding="utf-8")
    assert "<loc>" in sitemap and "<lastmod>" not in sitemap
