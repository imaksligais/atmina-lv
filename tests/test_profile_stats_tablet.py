"""Profila skaitļu josla (4 kartītes) ietilpst 601–900 px (good-css 5. kārta,
recenzija M3; 2026-10-21).

Kļūme, ko tests ķer: dzīvajos datos 10–12 no 255 profiliem (arī Ministru
prezidentam) lapa 601 px izplūda par 21 px — četras kartītes ar lielām vērtībām
(«5 000» balsojumu, «9 383» dokumenti) un etiķeti blakus vērtībai neietilpa
`.pp-stats-4` rindā 601–760 px. Fikstūras profils ir mazs, tāpēc vērtības
iestatām tādas pašas kā premjeram dzīvajā vietnē (838 / 5 000 / 7 / 9 383).

Renders: komitētā fikstūra (tests/conftest.py `rendered_site`), īstais style.css.
"""
from __future__ import annotations

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

PAGE = "politiki/andris-kulbergs.html"
LIVE_VALUES = ["838", "5 000", "7", "9 383"]
WIDTHS = [601, 640, 700, 760, 800, 860, 900]

PROBE = """(vals) => {
  const vs = [...document.querySelectorAll('.pp-stats-4 .pp-stat-value')];
  vs.forEach((e, i) => { e.textContent = vals[i]; });
  const s = document.querySelector('.pp-stats-4');
  return {n: vs.length, page: document.documentElement.scrollWidth - innerWidth,
          row: s.scrollWidth - s.clientWidth};
}"""


def test_four_stat_row_fits_601_to_900(rendered_site):
    out = {}
    with sync_api.sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Exception as exc:  # pragma: no cover — nav instalēta pārlūka
            pytest.skip(f"Chromium nav pieejams: {exc}")
        page = browser.new_page()
        for w in WIDTHS:
            page.set_viewport_size({"width": w, "height": 900})
            page.goto((rendered_site / PAGE).as_uri())
            out[w] = page.evaluate(PROBE, LIVE_VALUES)
        browser.close()
    print("\n" + ", ".join(f"{w}: lapa +{g['page']} rinda +{g['row']}" for w, g in out.items()))
    assert all(g["n"] == 4 for g in out.values()), f"nav 4 kartīšu — gadījums tukšs: {out}"
    bad = {w: g for w, g in out.items() if g["page"] > 0 or g["row"] > 0}
    assert not bad, f"skaitļu josla neietilpst: {bad}"
