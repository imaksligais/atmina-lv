"""Saites lapa: noklusējuma skats bez JS, pilnais tīkls tikai pēc pogas (2026-10-18).

Kļūme A3: lapa uzreiz zīmēja 216 mezglu D3 kamolu; telefonā pirmajā ekrānā
nebija nekā saprotama, un vecas `?party=` saites veda uz tabulu, ko vairs
neturam. Tagad: ievads + meklētājs + partijas (`<details>`) → nevirzīti pāri
ar dziļo saiti uz profila Saites cilni; pāris redzams ABU partiju sarakstos.
Kļūme A4: D3 + grafa JSON ielādējās vienmēr; «Balsojumi» poga ar 0 saitēm,
«Nostāju konflikts» bez pogas; leģenda pārklāja grafu.
Kļūme A5: tabula dublēja spriedzes.html.

Vietne tiek būvēta vienreiz (īstā `render_links`), katrs tests atver savu
pārlūka lapu — citādi A4 grafa ielāde «saindētu» A3 «D3 netiek ielādēts».
"""
import functools
import shutil
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from src.db import get_db, init_db
from src.render._common.filters import _lv_plural
from src.render.links import render_links
from src.render.tensions import _fetch_tensions
from src.saeima.schema import init_saeima_bills, init_saeima_tables
from tests.test_balsojumi_client_render import _env

sync_api = pytest.importorskip("playwright.sync_api")

_D3 = Path("output/atmina/assets/d3.v7.min.js")  # orķestrators to lejupielādē; repo nav

# 4 politiķi 3 partijās. Pāris Ābele↔Bērziņš (JV↔AS) ir 2 rindas (abos virzienos),
# lai pārim būtu jāparādās gan JV, gan AS sarakstā un skaitam jābūt 2.
_SQL = """
INSERT INTO tracked_politicians (id, name, party, role, relationship_type) VALUES
  (1, 'Anna Ābele', 'JV', 'deputāte', 'tracked'),
  (2, 'Bruno Bērziņš', 'AS', 'deputāts', 'tracked'),
  (3, 'Cilda Cīrule', 'ZZS', 'deputāte', 'tracked'),
  (4, 'Dace Dārziņa', 'JV', 'deputāte', 'tracked');
INSERT INTO political_tensions (id, source_pid, target_pid, topic, description, tension_type, source_url, created_at) VALUES
  (1, 1, 2, 'Imigrācija', 'Ābele kritizē Bērziņu.', 'uzbrukums', 'https://ex.lv/1', '2026-10-01 10:00:00'),
  (2, 2, 1, 'Imigrācija', 'Bērziņš atbild Ābelei.', 'spriedze', 'https://ex.lv/2', '2026-10-03 10:00:00'),
  (3, 3, 4, 'Budžets un finanses', 'Cīrule atbalsta Dārziņu.', 'atbalsts', 'https://ex.lv/3', '2026-10-02 10:00:00'),
  (4, 4, 3, 'Enerģētika', 'Dārziņa iebilst Cīrules nostājai.', 'politikas nostāju konflikts', 'https://ex.lv/4', '2026-10-04 10:00:00');
"""
# ZZS iegūst 14 pārus (Cīrule ar 13 partijas biedriem) → redzami 12, pārējie
# aiz «Rādīt vēl 2 pārus» (saraksts neizplūst pa visu lapu, 2026-10-18).
_SQL += "".join(
    f"INSERT INTO tracked_politicians (id, name, party, role, relationship_type) VALUES"
    f" ({10 + i}, 'Biedrs {i}', 'ZZS', 'deputāts', 'tracked');"
    f"INSERT INTO political_tensions (id, source_pid, target_pid, topic, description,"
    f" tension_type, source_url, created_at) VALUES ({10 + i}, {10 + i}, 3, 'Izglītība',"
    f" 'Biedrs kritizē Cīruli.', 'spriedze', 'https://ex.lv/b{i}', '2026-09-{10 + i:02d} 10:00:00');"
    for i in range(13)
)


class _Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


@pytest.fixture(scope="module")
def saites_server(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("saites")
    out = tmp / "site"
    out.mkdir()
    path = str(tmp / "t.db")
    init_db(path)
    init_saeima_tables(path)
    init_saeima_bills(path)
    db = get_db(path)
    db.executescript(_SQL)
    db.commit()
    env = _env()
    env.filters["lv_plural"] = _lv_plural
    try:
        render_links(env, db, out, _fetch_tensions(db))   # īstā render funkcija
    finally:
        db.close()
    shutil.copytree("assets", out / "assets", dirs_exist_ok=True)
    if _D3.exists():
        shutil.copy(_D3, out / "assets" / "d3.v7.min.js")
    server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Quiet, directory=str(out)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with sync_api.sync_playwright() as pw:
            browser = pw.chromium.launch()
            yield browser, f"http://127.0.0.1:{server.server_address[1]}", out
            browser.close()
    finally:
        server.shutdown()


@pytest.fixture
def saites_site(saites_server):
    """Svaiga 390 px lapa uz saites.html; `requested` = visi pieprasītie URL."""
    browser, base, _out = saites_server
    page = browser.new_page(viewport={"width": 390, "height": 844})
    requested: list[str] = []
    page.on("request", lambda r: requested.append(r.url))
    page.goto(base + "/saites.html")
    yield page, requested, base
    page.close()


def test_default_view_is_readable_without_graph(saites_site):
    page, requested, base = saites_site
    assert page.locator("#saites-search").is_visible()
    first = page.locator("details.saites-party").first
    assert first.bounding_box()["y"] < 844                      # pirmajā ekrānā
    assert not any("d3.v7" in r for r in requested)
    assert not any("saites-graph.json" in r for r in requested)
    # Partijas alfabētiski: AS, JV, ZZS.
    assert page.locator("details.saites-party > summary .saites-party-name").all_inner_texts() == [
        "AS", "JV", "ZZS"]
    first.locator("summary").click()
    link = first.locator("a.saites-pair").first
    href = link.get_attribute("href")
    assert href.startswith("politiki/") and "#saites-" in href
    row = first.locator(".saites-pair-row").first
    assert row.locator(".saites-pair-n").inner_text() == "2"    # pāra 2 ieraksti saskaitīti
    # Rinda saka, PAR KO ir saikne (jaunākā ieraksta apraksts) un tās veidu pēc krāsas.
    assert row.locator(".saites-pair-desc").inner_text() == "Bērziņš atbild Ābelei."
    assert row.get_attribute("data-tone") == "spriedze"
    # Starppartiju pāris ir ABU partiju sarakstos (AS un JV).
    for party in ("AS", "JV"):
        box = page.locator("details.saites-party", has=page.locator(
            ".saites-party-name", has_text=party))
        pair = box.locator("a.saites-pair", has_text="Ābele").filter(has_text="Bērziņš")
        assert pair.count() == 1, party
    # A5: tabula + 3 filtri aizstāti ar saiti uz spriedzes.html (saucējs = visas 4 rindas).
    assert page.locator("#saites-table").count() == 0
    assert page.locator(".saites-overview .multi-select").count() == 0
    assert page.locator("#table-type-select, #party-select, #person-select").count() == 0
    to_list = page.locator("a.saites-to-list")
    assert to_list.get_attribute("href") == "spriedzes.html"
    assert to_list.inner_text() == "Visu saikņu saraksts ar filtriem →"
    # Meklētājs → profila Saites cilne.
    page.fill("#saites-search", "Anna Ābele")
    page.dispatch_event("#saites-search", "change")
    page.wait_for_url("**/politiki/anna-abele.html#saites")
    page.goto(base + "/saites.html?party=AS")                   # veca filtra saite
    page.wait_for_url("**/spriedzes.html?party=AS")


def test_full_graph_loads_only_on_demand_and_buttons_are_honest(saites_site):
    page, requested, _base = saites_site
    if not _D3.exists():
        pytest.skip(f"{_D3} nav — palaid pilno renderu, kas lejupielādē D3")
    assert page.locator("#graph-svg circle").count() == 0
    assert page.locator("[data-link-type='vote']").count() == 0          # 0 balsojumu saišu
    assert page.locator("[data-link-type='politikas nostāju konflikts']").count() == 1
    assert page.locator(
        "[data-link-type='politikas nostāju konflikts'] .filter-count").inner_text() == "1"
    page.click("#saites-open-graph")
    page.wait_for_selector("#graph-svg circle")
    assert any("d3.v7" in r for r in requested)
    assert any("saites-graph.json" in r for r in requested)
    legend, svg = page.locator("#graph-legend").bounding_box(), page.locator("#graph-svg").bounding_box()
    assert legend["y"] >= svg["y"] + svg["height"] - 1                   # leģenda zem grafa


def test_pair_link_opens_the_profile_that_shows_the_pair(monkeypatch):
    """Kļūme: pāra saite veda uz autora profilu, bet profils rāda tikai jaunākās
    TENSIONS_CAP kartītes — vecāks pāris tur nav, `#saites-<pid>` neko neatrod
    (2026-10-18 prod: 29 no 288 pāriem). Saitei jāved uz otra politiķa profilu,
    kur šis pāris IR redzams."""
    import src.render.links as links_mod

    monkeypatch.setattr(links_mod, "TENSIONS_CAP", 1)
    row = dict(source_party="AS", target_party="JV", tension_type="spriedze")
    tensions = [  # jaunākā pirmā, kā _fetch_tensions
        dict(row, source_pid=1, source_name="X", source_slug="x",
             target_pid=2, target_name="Y", target_slug="y", date="2026-10-02"),
        dict(row, source_pid=1, source_name="X", source_slug="x",
             target_pid=3, target_name="Z", target_slug="z", date="2026-10-01"),
    ]
    pairs = {(r["a_slug"], r["anchor"]) for p in links_mod._party_pairs(tensions) for r in p["pairs"]}
    assert ("z", "saites-1") in pairs   # X profilā rādīts tikai X–Y → X–Z saite ved uz Z

    # Pāris, kas neietilpst NEVIENĀ profilā → saite atver tikai cilni, ne
    # `#saites-<pid>` bez elementa (Astra 2. kārta, prod 6 pāri).
    newer_p = dict(row, source_pid=10, source_name="P", source_slug="p",
                   target_pid=20, target_name="Q", target_slug="q", date="2026-10-05")
    newer_w = dict(row, source_pid=98, source_name="V", source_slug="v",
                   target_pid=99, target_name="W", target_slug="w", date="2026-10-09")
    hidden = dict(row, source_pid=10, source_name="P", source_slug="p",
                  target_pid=99, target_name="W", target_slug="w", date="2026-08-01")
    rows = links_mod._party_pairs([newer_w, newer_p, hidden])
    anchors = {frozenset((r["a_name"], r["b_name"])): r["anchor"] for p in rows for r in p["pairs"]}
    assert anchors[frozenset(("P", "W"))] == "saites", anchors


def test_party_less_people_are_grouped_by_kind_not_lumped():
    """Kļūme: «Bez partijas» grupā nonāca žurnālisti un organizācijas (prod
    2026-10-18: 69 rindas, no tām 29 žurnālistu un 6 organizāciju galapunkti) —
    lasītājs to uztvēra kā bezpartejiskus politiķus."""
    from src.render.links import _party_pairs

    base = dict(tension_type="spriedze", date="2026-10-01", source_party="AS",
                source_pid=1, source_name="A", source_slug="a", source_rel="tracked")
    rows = _party_pairs([
        dict(base, target_pid=2, target_name="Ž", target_slug="z", target_party=None, target_rel="journalist"),
        dict(base, target_pid=3, target_name="O", target_slug="o", target_party=None, target_rel="organization"),
        dict(base, target_pid=4, target_name="B", target_slug="b", target_party=None, target_rel="tracked"),
    ])
    assert [p["party"] for p in rows] == ["AS", "Žurnālisti", "Organizācijas", ""]


def test_long_party_list_shows_12_pairs_and_folds_the_rest(saites_site):
    """Kļūme: atvērta lielā partija (JV 105 pāri) izplūda ~8 300 px garumā un
    izstiepa partiju režģa kolonnu. Tagad redzami 12 jaunākie, pārējie aiz
    «Rādīt vēl N pārus»; atvērtā partija aizņem visu rindu."""
    page, _requested, _base = saites_site
    zzs = page.locator("details.saites-party", has_text="ZZS")
    zzs.locator("summary").first.click()
    visible = zzs.locator(".saites-party-body > .saites-pairs > li")
    assert visible.count() == 12
    more = zzs.locator("details.saites-more")
    assert more.locator("summary").inner_text().strip() == "Rādīt vēl 2 pārus"
    assert not more.locator("li").first.is_visible()
    more.locator("summary").click()
    assert more.locator("li").count() == 2 and more.locator("li").first.is_visible()
    page.set_viewport_size({"width": 1200, "height": 900})          # ≥2 kolonnas
    grid = page.locator(".saites-parties").bounding_box()
    assert abs(zzs.bounding_box()["width"] - grid["width"]) < 2      # pilna rinda
