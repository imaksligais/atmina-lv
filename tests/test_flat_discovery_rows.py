"""Regression: discovery/list items must not become filled, rounded boxes again.

Existing test_index_focus_layout covers grid order; test_pretrunas_mobile covers
opening/deep links, but neither checks the row surface or nested card frame.
"""
from pathlib import Path

import pytest

sync_api = pytest.importorskip("playwright.sync_api")
CSS = Path(__file__).resolve().parents[1] / "assets/style.css"


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("width", [390, 1280])
def test_flat_discovery_rows_and_single_evidence_surface(theme, width):
    with sync_api.sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": 900})
        page.set_content(f'''<html data-theme="{theme}"><body>
          <div class="rank-card"><a class="rank-leader">Leader</a>
          <a class="rank-row">Row</a></div>
          <div class="focus-slot"><blockquote class="focus-quote-card">Quote</blockquote>
          <article class="prv2-card">Evidence</article></div>
          <a class="tema-card">Topic</a><a class="tema-politiks">Person</a>
          <article class="tema-pozicija">Position</article>
          <a class="tema-sinteze">Synthesis</a>
          <div class="prv2-detail-related"><a class="prv2-related-card">Related</a></div>
          <article class="prv2-row open"><button class="prv2-row-head">Open</button>
          <div class="prv2-row-body"><div class="prv2-row-body-inner">
          <article class="prv2-card">Evidence</article></div></div></article>
        </body></html>''')
        page.add_style_tag(content=CSS.read_text(encoding="utf-8"))
        rows = page.locator(
            ".rank-leader, .rank-row, .focus-quote-card, .tema-card, "
            ".tema-politiks, .tema-pozicija, .tema-sinteze, .prv2-related-card, .prv2-row"
        ).evaluate_all('''els => els.map(el => {
          const s = getComputedStyle(el);
          return {start: s.borderInlineStartWidth, end: s.borderBlockEndWidth,
            top: s.borderBlockStartWidth, radius: s.borderStartStartRadius,
            shadow: s.boxShadow, background: s.backgroundColor};
        })''')
        assert len(rows) == 9
        for row in rows:
            assert row["start"] == "3px", row
            assert row["end"] == "1px", row
            assert row["top"] == "0px", row
            assert row["radius"] == "0px", row
            assert row["shadow"] == "none", row
        for card in page.locator(".prv2-card").all():
            assert card.evaluate('''el => {
              const s=getComputedStyle(el);
              return s.borderInlineStartWidth === '0px' && s.boxShadow === 'none'
                && s.backgroundColor === 'rgba(0, 0, 0, 0)';
            }''')
        browser.close()
