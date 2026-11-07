"""JS zīmētie datumi = `16.10.2026`, ne ISO / «10-20» (good-css 5. kārta, D1 + recenzija I2;
2026-10-21).

Kļūme, ko tests ķer: Python veidnes jau rāda `lv_date`, bet klienta pusē zīmētie
datumi palika vecā formā — Pozīciju saraksts (`assets/pzv1.js`, katra rinda
ISO «2026-10-20») un Saišu tīkla detaļu panelis (`assets/sav1.js`: pozīcijas,
balsojumi, pretrunas «10-20» BEZ gada; spriedzes un kopīgās tēmas — ISO).
Abi faili tagad lieto vietējo `lvDate()` ar to pašu līgumu kā Python `lv_date`;
dati (kārtošana, filtri) paliek ISO.

Renders: komitētā fikstūra (tests/conftest.py `rendered_site`), lapas pa HTTP
(fetch no file:// nestrādā). Saitēm D3 grafs nav vajadzīgs: sav1.js ielādē ar
minimālu d3 aizstājēju un detaļu paneli atver tieši (`showNodeDetail`).
"""
from __future__ import annotations

import functools
import json
import re
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

ISO = re.compile(r"\b20\d\d-\d\d-\d\d(?!\d)")
MONTH_DAY = re.compile(r"^\d\d-\d\d$")          # vecais sav1 `substring(5)`
LV = re.compile(r"^\d\d\.\d\d\.20\d\d$")


class _Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def base_url(rendered_site):
    handler = functools.partial(_Quiet, directory=str(rendered_site))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def _browser(pw):
    try:
        return pw.chromium.launch()
    except Exception as exc:  # pragma: no cover — nav instalēta pārlūka
        pytest.skip(f"Chromium nav pieejams: {exc}")


def _verdict(texts):
    iso = [t for t in texts if ISO.search(t) or MONTH_DAY.match(t)]
    lv = [t for t in texts if LV.match(t)]
    return iso, lv


def test_pozicijas_rows_show_lv_dates(base_url):
    with sync_api.sync_playwright() as pw:
        browser = _browser(pw)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"{base_url}/pozicijas.html")
        page.wait_for_selector(".pzv1-row-date", timeout=10000)
        texts = page.eval_on_selector_all(".pzv1-row-date", "els => els.map(e => e.textContent.trim())")
        browser.close()
    iso, lv = _verdict(texts)
    print(f"\npozicijas.html: {len(texts)} .pzv1-row-date, LV {len(lv)}, ISO/MM-DD {len(iso)}")
    assert texts, "nav nevienas rindas — gadījums tukšs"
    assert not iso, f"ISO / «MM-DD» datumi: {iso[:5]}"
    assert len(lv) == len(texts), [t for t in texts if t not in lv][:5]


D3_SHIM = """window.d3 = { select: function () { var s = { node: function () { return null; },
  selectAll: function () { return s; }, remove: function () { return s; } }; return s; } };"""

PANEL_DATES = """() => [...document.querySelectorAll('#detail-content span')]
  .map(e => e.textContent.trim())
  .filter(t => /^\\d{2}[.-]\\d{2}([.-]\\d{2,4})?$|^20\\d\\d-\\d\\d-\\d\\d$/.test(t))"""


def test_saites_panel_shows_lv_dates(base_url, rendered_site):
    graph = json.loads((rendered_site / "data" / "saites-graph.json").read_text(encoding="utf-8"))
    nodes = graph["graph"]["nodes"]
    # Mezgls ar pozīcijām, pretrunām un balsojumiem — visas sekcijas ar datumiem.
    node = max(nodes, key=lambda n: (n.get("contradictions", 0) > 0, n.get("claims", 0)))
    sections = ["pozicijas", "saites", "balsojumi", "pretrunas"]
    found: dict[str, list[str]] = {}
    with sync_api.sync_playwright() as pw:
        browser = _browser(pw)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"{base_url}/saites.html")
        page.add_script_tag(content=D3_SHIM)
        page.add_script_tag(url=f"{base_url}/assets/sav1.js")
        page.evaluate("(g) => window.atminaSaitesGraph.open({graph: {nodes: [], links: []},"
                      " tensions: g.tensions, contrasByPid: g.contrasByPid})", graph)
        page.evaluate("(n) => window.showNodeDetail(n, 'pozicijas')", node)
        page.wait_for_selector("#detail-section-content .detail-link-card", state="attached",
                               timeout=10000)
        for sec in sections:
            page.evaluate("(s) => window.renderNodeSection(s)", sec)
            if sec == "balsojumi":  # balsojumu reģistrs ielādējas atsevišķi
                page.wait_for_function(
                    "() => !/Ielādē/.test(document.getElementById('detail-section-content').textContent)",
                    timeout=10000)
            found[sec] = page.evaluate(PANEL_DATES)
        browser.close()
    texts = [t for v in found.values() for t in v]
    iso, lv = _verdict(texts)
    print(f"\nsaites.html «{node['name']}»: "
          + ", ".join(f"{k} {len(v)}" for k, v in found.items())
          + f" → LV {len(lv)}, ISO/MM-DD {len(iso)}")
    assert found["pozicijas"] and found["pretrunas"], f"sekcijās nav datumu — gadījums tukšs: {found}"
    assert not iso, f"ISO / «MM-DD» datumi: {iso[:5]}"
    assert len(lv) == len(texts), texts


def test_js_date_and_count_helpers_live_once_in_sgv1():
    """Viena kopija (final-review Minor 2): `lvDate` regulārā izteiksme un tūkstošu
    atstarpes formatētājs agrāk bija kopēti 3–4 failos (bmv1, pzv1, sav1; spv1,
    znv1, x-v1, pzv1) — labojums vienā vietā nesasniedza pārējās. Tagad tie ir
    tikai `assets/sgv1.js` (window.atminaLvDate / atminaFmtN / atminaShowCount)."""
    from pathlib import Path
    assets = Path(__file__).resolve().parent.parent / "assets"
    needles = {"lvDate": r"(\d{4})-(\d{2})-(\d{2})(?=", "fmtN": r"\B(?=(\d{3})+(?!\d))",
               "showCount": "function showCount("}
    hits = {k: [f.name for f in sorted(assets.glob("*.js"))
                for _ in range(f.read_text(encoding="utf-8").count(n))]
            for k, n in needles.items()}
    print(f"\n{len(list(assets.glob('*.js')))} JS faili: {hits}")
    assert hits["lvDate"] == ["sgv1.js"], hits
    assert hits["fmtN"] == ["sgv1.js"], hits
    assert hits["showCount"] == ["sgv1.js"], hits
