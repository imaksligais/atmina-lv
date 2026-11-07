"""Galvenā izvēlne planšetes platumā — viena rinda vai izvēlnes poga (2026-10-20).

Kļūme, ko ķer: 769–1149 px saites aplauzās 2–3 rindās (nav 117–177 px augsta),
izvēlne aizņēma pusi planšetes ekrāna. Pēc labojuma: līdz 960 px — izvēlnes
poga kā telefonā; no 961 px saites, atstarpes un meklētājs saspiežas, un viss
ietilpst vienā rindā (57 px).
Brauc īstu lapu pārlūkā ar īsto ``base.html.j2`` + ``assets/style.css``.
"""
import shutil
from pathlib import Path

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_render_saeima import fixture_db  # noqa: E402, F401 — pytest fixture

ONE_ROW_MAX = 70  # viena rinda = 57 px; divas rindas ≥ 117 px


def _render(tmp_path):
    from src.db import get_db, init_db
    from src.render.positions import render_positions
    from src.saeima.schema import init_saeima_tables
    from tests.test_profile_topic_deeplink import _env

    db_path = str(tmp_path / "t.db")
    init_db(db_path)
    init_saeima_tables(db_path)
    out = tmp_path / "site"
    out.mkdir()
    render_positions(_env(), get_db(db_path), out)
    shutil.copytree("assets", out / "assets", dirs_exist_ok=True)
    return out / "pozicijas.html"


NAV = """() => {
  const nav = document.querySelector('.nav');
  const burger = document.getElementById('nav-burger');
  const links = document.getElementById('nav-menu');
  return {navH: nav.getBoundingClientRect().height,
          burger: getComputedStyle(burger).display !== 'none',
          links: getComputedStyle(links).display !== 'none',
          pageW: document.documentElement.scrollWidth};
}"""


def test_nav_is_one_row_or_burger_at_tablet_widths(tmp_path):
    page_path = _render(tmp_path)
    with sync_api.sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Exception as exc:  # pragma: no cover
            pytest.skip(f"Chromium nav pieejams: {exc}")
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(Path(page_path).as_uri())
        page.evaluate("document.fonts.ready")
        for width in (800, 900, 960, 961, 1024, 1100, 1149, 1280):
            page.set_viewport_size({"width": width, "height": 800})
            g = page.evaluate(NAV)
            assert g["pageW"] <= width, f"{width}px: lapa platāka par ekrānu ({g['pageW']})"
            assert g["navH"] <= ONE_ROW_MAX, f"{width}px: izvēlne {g['navH']:.0f}px augsta (aplauzta)"
            if width <= 960:
                assert g["burger"] and not g["links"], f"{width}px: jābūt izvēlnes pogai, {g}"
            else:
                assert g["links"] and not g["burger"], f"{width}px: saitēm jābūt redzamām, {g}"
        browser.close()


LENS = """() => {
  const bar = document.querySelector('.slv-lenses');
  const nav = document.querySelector('.nav');
  window.scrollTo(0, 0);
  const natural = bar.getBoundingClientRect().top;
  // 40 px aiz pielipšanas punkta — josla jau lipīga, vecāks vēl redzams.
  window.scrollTo(0, natural - nav.getBoundingClientRect().bottom - 8 + 40);
  return {navBottom: nav.getBoundingClientRect().bottom, scrolled: window.scrollY,
          barTop: bar.getBoundingClientRect().top, hidden: bar.hidden};
}"""


def test_saeima_lens_bar_sticks_8px_below_nav(tmp_path, monkeypatch, fixture_db):
    """Saeimas lēcu josla pielīp 8 px zem nav visos platumos (2026-10-21).

    Kļūme, ko ķer: josla lieto savu nav augstuma mērījumu, kas atšķiras no
    kopīgā ``--nav-block-size`` (izvēlnes poga ≤960 px, cits fallback) —
    tad josla paslīd zem nav vai atstāj spraugu.
    """
    from tests.test_render_saeima import ELECTED
    from tests.test_render_saeima import _render as render_saeima_site

    render_saeima_site(tmp_path, monkeypatch, fixture_db, ELECTED)
    page_path = tmp_path / "site" / "atmina" / "saeima.html"
    with sync_api.sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Exception as exc:  # pragma: no cover
            pytest.skip(f"Chromium nav pieejams: {exc}")
        # reduce: html { scroll-behavior: smooth } citādi scrollTo animē
        page = browser.new_page(viewport={"width": 1280, "height": 800}, reduced_motion="reduce")
        page.goto(page_path.as_uri())
        page.evaluate("document.fonts.ready")
        for width in (390, 600, 768, 960, 961, 1280):
            page.set_viewport_size({"width": width, "height": 800})
            page.wait_for_timeout(100)  # ResizeObserver → --nav-block-size
            g = page.evaluate(LENS)
            assert not g["hidden"], "slv1.js neatklāja lēcu joslu"
            assert abs(g["barTop"] - (g["navBottom"] + 8)) <= 0.5, (
                f"{width}px: josla {g['barTop']:.1f}px, nav apakša {g['navBottom']:.1f}px (+8 gaidīts)")
        browser.close()
