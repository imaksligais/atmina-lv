"""Ritināmas joslas malas izbalē TIKAI, ja ir kur ritināt (good-css 5. kārta, C / I2–I3;
2026-10-21).

Kļūmes, ko tests ķer:
- Analīžu apakšcilnes telefonā (390 px) — 2 cilnes aiz malas, «SINTĒZ» nogriezts
  bez norādes, ka josla ritinās.
- «Par mums» shēma telefonā bija saspiesta 1100 → ~356 px (teksts ~3 px).
Paņēmiens — profila `.pp-tabs` (`animation-timeline: scroll(self inline)` +
`mask-image`): ja josla neritinās, laika līnija neaktīva → `--fade-*` = 0px.
Firefox bez scroll timeline — josla ritinās bez izbalēšanas.
"""
from __future__ import annotations

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

PROBE = """(sel) => {
  const el = document.querySelector(sel);
  const s = getComputedStyle(el);
  const svg = el.querySelector('svg');
  return {scrolls: el.scrollWidth > el.clientWidth + 1,
          start: s.getPropertyValue('--fade-start').trim(),
          end: s.getPropertyValue('--fade-end').trim(),
          mask: s.maskImage || s.webkitMaskImage,
          svgWidth: svg ? svg.getBoundingClientRect().width : null,
          pageOverflow: document.documentElement.scrollWidth > window.innerWidth};
}"""

CASES = [("analizes.html", ".pagehead-tabs"), ("about.html", ".anim-pipeline-scroll")]


def _probe(site, page_name, sel, width):
    with sync_api.sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Exception as exc:  # pragma: no cover — nav instalēta pārlūka
            pytest.skip(f"Chromium nav pieejams: {exc}")
        page = browser.new_page(viewport={"width": width, "height": 800})
        page.goto((site / page_name).as_uri())
        page.wait_for_selector(sel)
        g = page.evaluate(PROBE, sel)
        browser.close()
    return g


@pytest.mark.parametrize(("page_name", "sel"), CASES)
def test_phone_row_scrolls_and_fades_only_the_far_edge(rendered_site, page_name, sel):
    g = _probe(rendered_site, page_name, sel, 390)
    assert g["scrolls"], f"{page_name} {sel} neritinās 390 px — gadījums tukšs: {g}"
    assert g["start"] == "0px" and g["end"] == "32px", f"izbalēšana nepareiza: {g}"
    assert "gradient" in g["mask"], g
    assert not g["pageOverflow"], f"lapa izplūst pāri ekrānam: {g}"
    if g["svgWidth"] is not None:
        assert g["svgWidth"] >= 900, f"shēma joprojām saspiesta: {g}"


@pytest.mark.parametrize(("page_name", "sel"), CASES)
def test_desktop_row_without_overflow_has_no_fade(rendered_site, page_name, sel):
    g = _probe(rendered_site, page_name, sel, 1280)
    assert not g["scrolls"], g
    assert g["start"] == "0px" and g["end"] == "0px", f"izbalē arī neritināmu joslu: {g}"


def test_about_diagram_scroll_is_keyboard_reachable(rendered_site):
    """Recenzija M7: Safari ritināmu apgabalu pats Tab secībā neieliek —
    vajag tabindex="0" + role="region" ar latvisku nosaukumu un redzamu fokusu.
    Telefonā Tab līdz shēmai, → ritina to."""
    with sync_api.sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Exception as exc:  # pragma: no cover — nav instalēta pārlūka
            pytest.skip(f"Chromium nav pieejams: {exc}")
        page = browser.new_page(viewport={"width": 390, "height": 800}, reduced_motion="reduce")
        page.goto((rendered_site / "about.html").as_uri())
        tabs = 0
        for tabs in range(1, 80):
            page.keyboard.press("Tab")
            if page.evaluate("document.activeElement.classList.contains('anim-pipeline-scroll')"):
                break
        g = page.evaluate("""() => { const e = document.activeElement, s = getComputedStyle(e);
          return {hit: e.classList.contains('anim-pipeline-scroll'), role: e.getAttribute('role'),
                  label: e.getAttribute('aria-label'), outline: s.outlineStyle}; }""")
        page.keyboard.press("ArrowRight")
        page.wait_for_timeout(200)
        left = page.evaluate("document.querySelector('.anim-pipeline-scroll').scrollLeft")
        browser.close()
    print(f"\nTab spiedieni līdz shēmai: {tabs}; {g}; scrollLeft pēc → {left}")
    assert g["hit"], f"Tab nesasniedz shēmu ({tabs} spiedieni)"
    assert g["role"] == "region" and g["label"], g
    assert g["outline"] == "solid", f"fokuss nav redzams: {g}"
    assert left > 0, "→ neritina shēmu"
