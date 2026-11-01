"""Garām analīzēm satura rādītājs, un tā saites nolaiž virsrakstu ZEM lipīgās nav
(good-css 5. kārta, C / I1; 2026-10-21).

Kļūme, ko tests ķer: analīzes (vad-2026 — 10 h2, vad-izmeklesana — 9) bija bez
satura rādītāja, lai gan sintēzēm tas jau bija (`_add_h2_anchors` → `.post-toc`).
Lēciena atkāpe bija fiksēti 4,5rem, nesaistīta ar nav augstumu.

Renders: komitētā fikstūra (tests/conftest.py `rendered_site`),
Playwright pret renderēto lapu ar īsto assets/style.css + chrome-v1.js.
"""
from __future__ import annotations

import re

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

PAGE = "analizes/vad-2026.html"


def test_long_analysis_has_toc_with_live_anchors(rendered_site):
    html = (rendered_site / PAGE).read_text(encoding="utf-8")
    assert '<nav class="post-toc"' in html, "analīzei ar 10 h2 nav satura rādītāja"
    hrefs = re.findall(r'<nav class="post-toc".*?</nav>', html, re.S)[0]
    targets = re.findall(r'href="#([^"]+)"', hrefs)
    ids = set(re.findall(r'<h2 id="([^"]+)"', html))
    print(f"\n{PAGE}: {len(targets)} saites, {len(ids)} h2 ar id")
    assert len(targets) >= 3
    assert set(targets) <= ids, f"saites bez mērķa: {set(targets) - ids}"


GEOM = """(id) => {
  const nav = document.querySelector('.nav');
  const h = document.getElementById(id);
  return {navBottom: nav.getBoundingClientRect().bottom,
          top: h.getBoundingClientRect().top, scrollY: window.scrollY};
}"""


@pytest.mark.parametrize("width", [390, 1280])
def test_toc_jump_lands_heading_below_sticky_nav(rendered_site, width):
    with sync_api.sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Exception as exc:  # pragma: no cover — nav instalēta pārlūka
            pytest.skip(f"Chromium nav pieejams: {exc}")
        ctx = browser.new_context(viewport={"width": width, "height": 800},
                                  reduced_motion="reduce")
        page = ctx.new_page()
        page.goto((rendered_site / PAGE).as_uri())
        links = page.locator(".post-toc a")
        assert links.count() >= 3
        # Telefonā saraksts ir aizvērts (neaizņem pirmo ekrānu), datorā atvērts.
        assert links.first.is_visible() == (width > 600), f"{width}px: redzamība"
        if width <= 600:
            page.click(".post-toc-head")
        link = links.nth(links.count() - 2)  # tālu lejā esošs virsraksts
        target = link.get_attribute("href")[1:]
        link.click()
        page.wait_for_function(
            """() => { const y = window.scrollY, p = window.__y; window.__y = y;
                       return y > 0 && p === y; }""", polling=150, timeout=8000)
        g = page.evaluate(GEOM, target)
        browser.close()
    assert g["scrollY"] > 300, f"lapa netika ritināta: {g}"
    assert g["top"] >= g["navBottom"] - 1, f"virsraksts zem nav: {g}"
    assert g["top"] <= g["navBottom"] + 32, f"virsraksts pārāk tālu no nav: {g}"
