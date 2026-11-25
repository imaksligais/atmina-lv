"""Saites lapa: noklusējuma skats bez D3, pilnais tīkls tikai pēc pogas (2026-10-18).

Saites v2 (2026-11-22): augšā jaunākās saiknes (vienam cilvēkam ≤2 rindas),
partiju kastu vietā tabula, kuras rinda atver pārus; tīklā izcelšana uz
klikšķa/pieskāriena, partiju leģenda, panelis atveras uz «Saites», un
balsojumu sakritības līnijas tikai izvēlētajam mezglam.

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
# Ābele un Bērziņš 100 kopīgos balsojumos balso vienādi (VOTE_ALIGN_MIN_SHARED).
_SQL += "".join(
    f"INSERT INTO saeima_votes (id, motif, vote_date, vote_time) VALUES ({v}, 'Par grozījumiem {v}',"
    f" '2026-06-05', '{10 + v // 60}:{v % 60:02d}');"
    f"INSERT INTO saeima_individual_votes (vote_id, deputy_name, vote, politician_id) VALUES"
    f" ({v}, 'Ābele Anna', 'Par', 1), ({v}, 'Bērziņš Bruno', 'Par', 2);"
    for v in range(1, 101)
)
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
    assert not any("d3.v7" in r for r in requested)
    assert not any("saites-graph.json" in r for r in requested)
    # Jaunākās saiknes: jaunākais pāris pirmais un pirmajā ekrānā. Cīrule ir
    # 14 pāros, bet sarakstā ne vairāk kā divreiz — viena cilvēka vakars
    # nepiepilda visu sarakstu.
    rows = page.locator(".saites-newest-row")
    assert rows.first.bounding_box()["y"] < 844
    names = rows.locator(".saites-newest-names").all_inner_texts()
    assert len(names) == 3, names
    assert "Dārziņa" in names[0] and "Ābele" in names[1], names
    assert sum("Cīrule" in n for n in names) == 2, names
    lead = rows.first
    assert "saites-newest-lead" in lead.get_attribute("class")
    assert lead.locator(".saites-newest-type").inner_text() == "Nostāju konflikts"
    assert lead.locator("a").get_attribute("href").startswith("politiki/")
    # Partiju tabula: alfabētiski; četri veidi saskaitās līdz «Saiknes».
    party_rows = page.locator(".saites-party-row")
    assert party_rows.locator(".saites-party-name").all_inner_texts() == ["AS", "JV", "ZZS"]
    as_cells = party_rows.first.locator("td").all_inner_texts()
    assert as_cells == ["2", "1", "1", "–", "–"], as_cells
    # Rinda pati ir vadīkla: atver savus pārus; cita rinda tos aizver.
    as_pairs = page.locator(".saites-party-pairs").first
    assert not as_pairs.is_visible()
    party_rows.first.locator("td").first.click()
    assert as_pairs.is_visible()
    row = as_pairs.locator(".saites-pair-row").first
    assert row.locator(".saites-pair-n").inner_text() == "2"    # pāra 2 ieraksti saskaitīti
    assert row.locator(".saites-pair-desc").inner_text() == "Bērziņš atbild Ābelei."
    href = row.locator("a.saites-pair").get_attribute("href")
    assert href.startswith("politiki/") and "#saites-" in href
    party_rows.nth(1).click()
    assert not as_pairs.is_visible()
    # Starppartiju pāris ir ABU partiju sarakstos (AS un JV).
    for i in (0, 1):
        pair = page.locator(".saites-party-pairs").nth(i).locator(
            "a.saites-pair", has_text="Ābele").filter(has_text="Bērziņš")
        assert pair.count() == 1, i
    # A5: tabula ar filtriem aizstāta ar saiti uz spriedzes.html.
    assert page.locator("#saites-table").count() == 0
    to_list = page.locator("a.saites-to-list")
    assert to_list.get_attribute("href") == "spriedzes.html"
    # Meklētājs → profila Saites cilne.
    page.fill("#saites-search", "Anna Ābele")
    page.dispatch_event("#saites-search", "change")
    page.wait_for_url("**/politiki/anna-abele.html#saites")
    page.goto(base + "/saites.html?party=AS")                   # veca filtra saite
    page.wait_for_url("**/spriedzes.html?party=AS")


def test_full_graph_loads_only_on_demand_and_selection_works_by_tap(saites_site):
    page, requested, _base = saites_site
    if not _D3.exists():
        pytest.skip(f"{_D3} nav — palaid pilno renderu, kas lejupielādē D3")
    assert page.locator("#graph-svg circle").count() == 0
    assert page.locator("[data-link-type='vote']").count() == 0          # balsojumi nav filtrs
    assert page.locator(
        "[data-link-type='politikas nostāju konflikts'] .filter-count").inner_text() == "1"
    page.click("#saites-open-graph")
    page.wait_for_selector("#graph-svg circle")
    assert any("d3.v7" in r for r in requested)
    assert any("saites-graph.json" in r for r in requested)
    legend, svg = page.locator("#graph-legend").bounding_box(), page.locator("#graph-svg").bounding_box()
    assert legend["y"] >= svg["y"] + svg["height"] - 1                   # leģenda zem grafa
    page.wait_for_timeout(1500)                                          # simulācija nosēžas
    dimmed = "[...document.querySelectorAll('#graph-svg g[opacity]')].filter(g => g.getAttribute('opacity') === '0.15').length"
    # Izvēle ar klikšķi (telefonā nav hover): Ābele + kaimiņš Bērziņš paliek,
    # pārējie nobālē; balsojumu līnija uz Bērziņu; panelis atveras uz «Saites».
    page.evaluate("d3.selectAll('#graph-svg g').filter(d => d && d.id === 1 && d.name).dispatch('click')")
    assert page.evaluate(dimmed) == 15
    assert page.locator(".vote-line.vote-top").count() == 1
    assert page.locator(".detail-stat-btn.active").get_attribute("data-section") == "saites"
    assert "Visbiežāk balso vienādi" in page.locator("#detail-content").text_content()
    assert "100 %" in page.locator(".detail-vote-list").inner_text()
    # Partiju leģenda: JV izceļ 2 JV mezglus, otrs spiediens noņem.
    jv = page.locator(".graph-party-btn[data-party='JV']")
    jv.click()
    assert jv.get_attribute("aria-pressed") == "true"
    assert page.evaluate(dimmed) == 15
    assert page.locator(".vote-line").count() == 0
    jv.click()
    assert page.evaluate(dimmed) == 0


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
    """Kļūme: atvērta lielā partija (JV 105 pāri) izplūda ~8 300 px garumā.
    Tagad redzami 12 jaunākie, pārējie aiz «Rādīt vēl N pārus»."""
    page, _requested, _base = saites_site
    page.locator(".saites-party-row", has_text="ZZS").click()
    zzs = page.locator(".saites-party-pairs").nth(2)
    visible = zzs.locator("td > .saites-pairs > li")
    assert visible.count() == 12
    more = zzs.locator("details.saites-more")
    assert more.locator("summary").inner_text().strip() == "Rādīt vēl 2 pārus"
    # Abas vadīklas (rinda un «Rādīt vēl») telefonā ≥ 44 px (§0; saites.html
    # vairs nav test_ui_disclosures_one_look lapu sarakstā).
    assert more.locator("summary").bounding_box()["height"] >= 44
    assert page.locator(".saites-party-toggle").first.bounding_box()["height"] >= 44
    assert not more.locator("li").first.is_visible()
    more.locator("summary").click()
    assert more.locator("li").count() == 2 and more.locator("li").first.is_visible()
