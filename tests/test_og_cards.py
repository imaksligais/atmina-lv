"""OG kartītes (sepija) profilam, partijai, tēmai un vietnes noklusējumam.

Caur ĪSTO orķestratoru uz komitētās render fikstūras DB; Playwright aizstāts ar
``og_render._shoot`` aizstājēju, kas uzraksta failu un pieglabā kartītes HTML.
Pretrunu kartīšu nemainīgums + hash invalidācija: tests/test_generate.py
(``test_og_cards_rerender_only_when_content_changes`` — tas pats kopējais modulis).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


BASE = "https://atmina.lv"


@pytest.fixture(scope="module")
def og_site(tmp_path_factory, render_fixture_db):
    import src.render._orchestrator as orch
    from src.render._common import og_render

    shots: dict[Path, str] = {}

    def _fake_shoot(todo):
        for out_path, html in todo:
            Path(out_path).write_bytes(b"png")
            shots[Path(out_path)] = html
            yield out_path

    out = tmp_path_factory.mktemp("og_site")
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(og_render, "_shoot", _fake_shoot)
        for name in ("_download_chart_js", "_download_annotation_plugin", "_download_d3"):
            mp.setattr(orch, name, lambda *a, **k: None)
        orch.generate_public_site(
            db_path=render_fixture_db, output_dir=str(out),
            only={"politiki", "partijas", "temas", "static"},
        )
    return out / "atmina", shots


def _og_image(html: str) -> str:
    m = re.search(r'<meta property="og:image" content="([^"]+)"', html)
    assert m, "lapā nav og:image"
    return m.group(1)


def _first(site: Path, sub: str) -> Path:
    pages = sorted((site / sub).glob("*.html"))
    assert pages, f"{sub}/ — nav nevienas lapas"  # saucējs
    return pages[0]


@pytest.mark.parametrize("kind", ["politiki", "partijas", "temas", "landing"])
def test_page_og_image_is_its_own_card(og_site, kind):
    """Lapas og:image (un twitter:image) ved uz SAVU kartīti, un PNG ir kokā."""
    site, _ = og_site
    if kind == "landing":
        page, expected = site / "about.html", "assets/og-atmina.png"
    else:
        page = _first(site, kind)
        expected = f"assets/og/{kind}/{page.stem}.png"
    html = page.read_text(encoding="utf-8")
    assert _og_image(html) == f"{BASE}/{expected}"
    assert f'<meta name="twitter:image" content="{BASE}/{expected}">' in html
    assert (site / expected).exists(), f"{expected} nav uzzīmēts"


def test_profile_card_stats_equal_profile_page(og_site):
    """Kartītes «N pozīcijas» / «N pretrunas» = lapas skaitļu joslas flīzes."""
    site, shots = og_site
    compared = 0
    for page in sorted((site / "politiki").glob("*.html")):
        html = page.read_text(encoding="utf-8")
        tiles = dict(
            (label.lower(), value)
            for value, label in re.findall(
                r'class="pp-stat-value">([^<]+)</span>\s*'
                r'<span class="pp-stat-text"><span class="pp-stat-label">([^<]+)<', html)
            if label.lower().startswith(("pozīcij", "pretrun"))
        )
        if len(tiles) < 2:
            continue
        card = shots[site / "assets" / "og" / "politiki" / f"{page.stem}.png"]
        card_stats = dict(
            (label, value) for value, label in
            re.findall(r'<div class="stat"><b>([^<]+)</b><span>([^<]+)</span>', card)
        )
        assert {k: card_stats.get(k) for k in tiles} == tiles, page.name
        compared += 1
    assert compared >= 1, "fikstūrā nav profila ar pozīcijām UN pretrunām — tests neko nepārbauda"
