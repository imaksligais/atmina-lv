"""Profila cilnes telefonā: pēc pieskāriena cilnes saturs sākas uzreiz zem
cilņu joslas (2026-10-07).

Kļūme, ko šis tests ķer: starp cilņu joslu un paneli stāvēja nemainīgi bloki
(skaitļu josla, «Saistītās sintēzes»), tāpēc pie 390 px pēc pieskāriena bija
jāritina 222–667 px, lai ieraudzītu saturu. Otrā puse: ja lasītājs ir dziļi
garā panelī un pārslēdz cilni, ``ppv1.js`` ritina atpakaļ līdz jaunā paneļa
sākumam — citādi skatā paliek tukšums vai kājene.

Brauc īstu lapu pārlūkā (Playwright, Chromium) pret renderētu fikstūru ar
īstajiem ``assets/style.css`` + ``assets/ppv1.js``. Priekšnoteikums
(``position: sticky``) pierāda, ka stili tiešām ielādēti — bez tiem lapa
varētu izturēt ģeometrijas pārbaudi nejauši.
"""
import shutil
from pathlib import Path

import pytest

from tests.test_profile_tabs_keyboard import _render

sync_api = pytest.importorskip("playwright.sync_api")

# Pēc labojuma paneļa augša == joslas apakša (0 px); bez labojuma te stāv
# skaitļu josla (≥ 60 px telefonā). Robeža atstāj vietu subpikseļiem.
MAX_GAP = 16

GEOMETRY = """(tab) => {
  const bar = document.querySelector('.pp-tabs');
  const b = bar.getBoundingClientRect();
  const p = document.getElementById('tab-' + tab).getBoundingClientRect();
  const stuckTop = parseFloat(getComputedStyle(bar).top) || 0;
  return {position: getComputedStyle(bar).position, gap: p.top - b.bottom,
          stuckGap: p.top - (stuckTop + b.height),
          pageW: document.documentElement.scrollWidth};
}"""


def test_mobile_tab_panel_starts_right_under_the_tab_bar(tmp_path):
    _render(tmp_path)
    out = tmp_path / "site" / "atmina"
    shutil.copytree("assets", out / "assets")
    page_path = out / "politiki" / "a-kalns.html"
    html = page_path.read_text(encoding="utf-8")
    # Fikstūras env nedod assets_prefix → ppv1.js ceļš ir relatīvs politiki/.
    if 'src="assets/ppv1.js' in html:
        shutil.copytree("assets", out / "politiki" / "assets")

    with sync_api.sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Exception as exc:  # pragma: no cover — nav instalēta pārlūka
            pytest.skip(f"Chromium nav pieejams: {exc}")
        ctx = browser.new_context(viewport={"width": 390, "height": 700},
                                  reduced_motion="reduce")
        page = ctx.new_page()
        page.goto(Path(page_path).as_uri())
        tabs = page.eval_on_selector_all(
            ".pp-tabs [data-tab]", "els => els.map(e => [e.dataset.tab, e.classList.contains('active')])")
        default = next(t for t, active in tabs if active)
        others = [t for t, active in tabs if not active]
        assert len(others) >= 1, tabs

        # 1) No lapas augšas: pieskāriens ne-noklusētajai cilnei.
        page.click(f'.pp-tabs [data-tab="{others[0]}"]')
        g = page.evaluate(GEOMETRY, others[0])
        assert g["position"] == "sticky", "stili nav ielādēti vai josla nav sticky"
        assert g["pageW"] <= 390, f"lapai horizontāla ritjosla: {g['pageW']}px"
        assert -2 <= g["gap"] <= MAX_GAP, f"starp joslu un paneli {g['gap']:.0f}px"

        # 2) Dziļi garā panelī → cits panelis: lapa ritina līdz tā sākumam.
        page.click(f'.pp-tabs [data-tab="{default}"]')
        page.add_style_tag(content=f"#tab-{default} {{ min-height: 4000px; }}")
        page.evaluate("window.scrollTo({top: 3000, behavior: 'instant'})")
        page.click(f'.pp-tabs [data-tab="{others[0]}"]')
        page.wait_for_timeout(100)
        g = page.evaluate(GEOMETRY, others[0])
        assert -2 <= g["stuckGap"] <= MAX_GAP, (
            f"pēc pārslēgšanas dziļumā paneļa sākums {g['stuckGap']:.0f}px no joslas")
        browser.close()


CARD_GEOMETRY = """() => {
  const t = document.getElementById('claims-table');
  const row = t.querySelector('tbody tr');
  const [topic, stance, date, src] = row.querySelectorAll('td');
  const r = el => el.getBoundingClientRect();
  return {theadShown: getComputedStyle(t.querySelector('thead')).display !== 'none',
          dateBesideTopic: Math.abs(r(date).top - r(topic).top) < 8,
          stanceBelow: r(stance).top >= r(topic).bottom - 1,
          srcRight: r(src.querySelector('a')).right,
          pageW: document.documentElement.scrollWidth};
}"""


def test_mobile_positions_table_rows_are_cards(tmp_path):
    """Pozīciju tabula telefonā (2026-10-09): četras kolonnas 360 px ekrānā
    nogrieza datumu («2026-10-0») un «Avots» paslēpa aiz horizontālās
    ritināšanas. Rinda = kartīte: tēma + datums augšā, pozīcija zem tiem."""
    from tests.test_profile_positions_quote import _render as render_quote
    render_quote(tmp_path)
    out = tmp_path / "site" / "atmina"
    shutil.copytree("assets", out / "assets")
    page_path = out / "politiki" / "a-kalns.html"
    if 'src="assets/ppv1.js' in page_path.read_text(encoding="utf-8"):
        shutil.copytree("assets", out / "politiki" / "assets")
    with sync_api.sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Exception as exc:  # pragma: no cover — nav instalēta pārlūka
            pytest.skip(f"Chromium nav pieejams: {exc}")
        page = browser.new_page(viewport={"width": 360, "height": 700})
        page.goto(Path(page_path).as_uri())
        page.click('.pp-tabs [data-tab="pozicijas"]')
        g = page.evaluate(CARD_GEOMETRY)
        browser.close()
    assert not g["theadShown"], "telefonā tabulas galva joprojām redzama"
    assert g["dateBesideTopic"] and g["stanceBelow"], g
    assert g["srcRight"] <= 360 and g["pageW"] <= 360, g
