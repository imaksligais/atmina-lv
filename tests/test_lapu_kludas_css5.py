"""good-css 5. kārta, 2. uzdevums: lasītājam redzamas kļūdas partiju, mediju
un redakcijas lapās (2026-10-21). Audits: ``docs/audits/2026-10-21-good-css-5/``
(``vienibas.md``, ``redakcijas-lapas.md``).

Katrs tests brauc īstu lapu pārlūkā (Playwright, Chromium) pret renderētu
veidni vai ``curated/`` lapu ar īstajiem ``assets/`` — tas, ko redz lasītājs:

- A1 partijas balsojumu tabula 3 325–3 797 px plata → Par/Pret aiz malas;
- A14 partijas cilņu josla telefonā: viena cilne viena pati otrā rindā;
- A5 iesaldētās analīzes gaišas, kad vietne tumša, bet OS gaiša;
- A6 statistika 1280 px: 4. kartīte 200 px aiz ekrāna;
- A7 nedēļas pārskats: gaišas kartītes tumšajā tēmā, datums lūst «2026-/10-11»;
- A13 medija «vidējais» marķieris aiz joslas, virs procentu skaitļa.

Partijas tukšā «Biedri» cilne — ``tests/test_render_parties_slug.py``.
"""
import shutil
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader

from src.render._common import _party_page_slug, _safe_json_filter, _safe_url_filter, lv_date_short

sync_api = pytest.importorskip("playwright.sync_api")

REPO = Path(__file__).resolve().parent.parent
DARK_BG = "rgb(13, 16, 20)"          # :root --bg style.css
DARK_SURFACE = "rgb(22, 26, 34)"     # :root --surface style.css (#161a22)


def _env() -> Environment:
    env = Environment(loader=FileSystemLoader(str(REPO / "templates")), autoescape=True)
    env.filters["safe_url"] = _safe_url_filter
    env.filters["safe_json"] = _safe_json_filter
    env.filters["party_page_slug"] = _party_page_slug
    env.filters["lv_date"] = lambda s: s or ""
    env.filters["lv_date_short"] = lv_date_short
    env.filters["lv_plural"] = lambda n, *a, **k: ""
    env.filters["autolink_bills"] = lambda s, *a, **k: s
    env.globals["assets_version"] = "test"
    return env


def _site(tmp_path: Path) -> Path:
    out = tmp_path / "atmina"
    shutil.copytree(REPO / "assets", out / "assets")
    return out


def _browser(pw):
    try:
        return pw.chromium.launch()
    except Exception as exc:  # pragma: no cover — nav instalēta pārlūka
        pytest.skip(f"Chromium nav pieejams: {exc}")


def _context(browser, width, theme="light", height=900):
    ctx = browser.new_context(viewport={"width": width, "height": height},
                              color_scheme="light", reduced_motion="reduce")
    ctx.route("**/*", lambda r: r.abort() if r.request.url.startswith("http") else r.continue_())
    ctx.add_init_script(f"localStorage.setItem('atmina:theme', '{theme}')")
    return ctx


# ── Partijas lapa ───────────────────────────────────────────────────────

LONG_SUMMARY = (
    "Grozījumi Valsts budžeta likumā 2027. gadam par aizsardzības izdevumu "
    "palielināšanu, pašvaldību finanšu izlīdzināšanu un nodokļu atvieglojumiem "
    "ģimenēm ar bērniem, kā arī par valsts kapitālsabiedrību dividenžu politiku "
    "un enerģētikas drošības pasākumu finansēšanu nākamajos trīs gados; "
    # Garākais vārds nosaka kolonnas min-content: dzīvajā jv 117 px šūnā
    # «kompensācijas»» izstūma tabulu 5 px pāri malai.
    "«dzīvojamāstelpaskompensācijas»"
)


def _party_page(tmp_path, *, program=True, tensions=True, knab=False, name="jv"):
    out = _site(tmp_path)
    members = [{"id": 1, "name": "Anna Kalna", "slug": "anna-kalna", "role": "Deputāte",
                "x_handle": None, "has_photo": False, "claims_count": 1,
                "contradictions_count": 0, "votes_count": 3, "last_activity": None,
                "party_color": "#2a6"}]
    ctx = {
        "party": {"id": 1, "name": "Jaunā Vienotība", "short_name": name.upper(),
                  "color": "#2a6", "coalition_status": "coalition"},
        "members": members,
        "claims": [{"slug": "anna-kalna", "politician_name": "Anna Kalna",
                    "topic": "Ekonomika", "stated_at": "2026-10-01", "stance": "Pozīcija.",
                    "source_url": "https://example.lv/a"}],
        "claims_count": 1,
        "program_by_topic": ([{"topic": "Ekonomika", "promises": [
            {"stance": "Solījums.", "source_url": "https://example.lv/p"}]}] if program else []),
        "program_count": 1 if program else 0,
        "votes": [{"date": f"2026-10-0{i}", "summary": LONG_SUMMARY,
                   "par": 12, "pret": 0, "atturas": 1} for i in range(1, 4)],
        "tensions": ([{"badge": "badge-red", "type_label": "Kritika", "lv_date": "2026-10-01",
                       "source_name": "Anna Kalna", "target_name": "Bruno Liepa",
                       "topic": "Ekonomika", "description": "Apraksts.",
                       "source_url": "https://example.lv/t", "target_url": None}]
                     if tensions else []),
        "knab_summary": ({"total_donations": 123456, "donor_count": 7, "alert_count": 0}
                         if knab else None),
    }
    page = out / "partijas" / f"{name}.html"
    page.parent.mkdir(parents=True)
    page.write_text(_env().get_template("partija.html.j2").render(**ctx), encoding="utf-8")
    return page


def test_party_votes_table_fits_its_container(tmp_path):
    """A1: kopsavilkuma šūna bija vienā rindā (`min-width: max-content`), tabula
    3 325 px telefonā / 3 797 px datorā — Par/Pret/Atturas aiz ekrāna malas.

    Labojuma 1. kārta (tabula ietilpst, kopsavilkums savā kolonnā) atstāja
    telefonā šauru stabiņu: 390 px — 97 px plats, augstākā šūna 918 px;
    360 px — 78 px, 1 102 px, 46 vārdi lūza vidū (task-2-review.md, Important 1).
    Tāpēc ≤600 px kopsavilkums stāv savā pilna platuma rindā katrā balsojumā."""
    page_path = _party_page(tmp_path)
    with sync_api.sync_playwright() as pw:
        browser = _browser(pw)
        for width in (360, 390, 1280):
            ctx = _context(browser, width)
            page = ctx.new_page()
            page.goto(page_path.as_uri())
            page.click('[data-tab="balsojumi"]')
            g = page.evaluate("""() => {
              const wrap = document.querySelector('#tab-balsojumi .table-scroll');
              const t = wrap.querySelector('table');
              const cells = [...t.querySelectorAll('tbody td')].map(c => c.getBoundingClientRect());
              const sums = [...t.querySelectorAll('tbody td:nth-child(2)')]
                .map(c => c.getBoundingClientRect().width);
              return {wrap: wrap.clientWidth, table: t.getBoundingClientRect().width,
                      wrapRight: wrap.getBoundingClientRect().right,
                      maxRight: Math.max(...cells.map(c => c.right)),
                      maxCellH: Math.max(...cells.map(c => c.height)),
                      minSum: Math.min(...sums)};
            }""")
            assert g["table"] > 0, "tabula nav redzama — cilne neatvērās"
            assert g["table"] <= g["wrap"] + 1, f"{width}px: tabula {g['table']:.0f} > {g['wrap']}"
            assert g["maxRight"] <= g["wrapRight"] + 1, f"{width}px: šūna aiz malas"
            if width <= 600:
                assert g["minSum"] >= 0.8 * g["table"], (
                    f"{width}px: kopsavilkums {g['minSum']:.0f}px no {g['table']:.0f}px")
                assert g["maxCellH"] <= 400, f"{width}px: šūna {g['maxCellH']:.0f}px augsta"
            ctx.close()
        browser.close()


ROWS = """() => {
  const tabs = [...document.querySelectorAll('.profile-stats-bar > .profile-stat')];
  const tops = tabs.map(t => Math.round(t.getBoundingClientRect().top));
  const rows = [...new Set(tops)].map(top => tops.filter(t => t === top).length);
  // Etiķete ir flex vienums ar `align-items: center` — tā neapgriežas pati,
  // bet izlien pāri pogas satura laukumam (pogai `overflow` nav redzams).
  const clipped = tabs.filter(t => {
    const l = t.querySelector('.profile-stat-label');
    const cs = getComputedStyle(t);
    const inner = t.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
    return l.scrollWidth > inner + 1;
  }).map(t => t.querySelector('.profile-stat-label').textContent);
  const bar = document.querySelector('.profile-stats-bar').getBoundingClientRect();
  const gap = bar.right - Math.max(...tabs.map(t => t.getBoundingClientRect().right));
  return {rows, clipped, gap};
}"""


@pytest.mark.parametrize("tabs, kw", [
    (3, {"program": False, "tensions": False}),
    (5, {}),
    (6, {"knab": True}),
])
def test_party_tab_bar_has_no_lone_tab_on_phone(tmp_path, tabs, kw):
    """A14: ≤600 px josla ir režģis pa 4 → 5 cilnēm «SPRIEDZES» viena pati
    otrā rindā (12/19 partijām), 3 cilnēm tukša ceturtā kolonna.

    Arī ar platu fontu (2026-10-23): Linux CI noklusējuma fonts ir platāks par
    Segoe UI, un «PROGRAMMA» 320 px izlīda pāri pogai — tas pats notiek ierīcēs
    ar platu sistēmas fontu. Verdana te atdarina platāko gadījumu."""
    page_path = _party_page(tmp_path, **kw)
    with sync_api.sync_playwright() as pw:
        browser = _browser(pw)
        for width in (320, 360, 390, 600):
            for wide in (False, True):
                ctx = _context(browser, width)
                page = ctx.new_page()
                page.goto(page_path.as_uri())
                if wide:
                    page.add_style_tag(content=".profile-stats-bar { font-family: Verdana, 'DejaVu Sans', sans-serif !important; }")
                g = page.evaluate(ROWS)
                tag = f"{width}px{' platais fonts' if wide else ''}"
                assert sum(g["rows"]) == tabs, g
                assert len(set(g["rows"])) == 1, f"{tag}: rindas nevienādas {g['rows']}"
                assert not g["clipped"], f"{tag}: etiķetes nogrieztas {g['clipped']}"
                assert g["gap"] <= 2, f"{tag}: tukša kolonna joslas galā ({g['gap']:.0f}px)"
                ctx.close()
        browser.close()


# ── Iesaldētās analīzes (curated) ───────────────────────────────────────

FROZEN = ["partiju-tests", "nvo-dotacijas-2025", "nvo-valsts-maksajumi"]


def _curated_site(tmp_path):
    from src.render._assets import _copy_curated
    out = _site(tmp_path)
    _copy_curated(REPO / "curated" / "atmina", out)
    return out


def test_frozen_analyses_follow_site_dark_theme_on_light_os(tmp_path):
    """A5: `@media (prefers-color-scheme: light) { :root {…} }` uzvarēja, jo
    tumšajai tēmai `theme-init.js` neliek `data-theme` → OS gaiša + vietne
    tumša = gaiša lapa ar tumšu nav."""
    out = _curated_site(tmp_path)
    with sync_api.sync_playwright() as pw:
        browser = _browser(pw)
        for theme, want in (("dark", DARK_BG), ("light", "rgb(247, 243, 232)")):
            ctx = _context(browser, 390, theme=theme)
            page = ctx.new_page()
            for slug in FROZEN:
                page.goto((out / "analizes" / f"{slug}.html").as_uri())
                bg = page.evaluate("getComputedStyle(document.body).backgroundColor")
                assert bg == want, f"{slug} ({theme}): body fons {bg}"
            ctx.close()
        browser.close()


# ── Statistika ──────────────────────────────────────────────────────────

CARDS_INSIDE = """() => {
  const grid = document.querySelector('.stat-card-grid').getBoundingClientRect();
  const cards = [...document.querySelectorAll('.stat-card')];
  return {n: cards.length, gridRight: grid.right, vw: innerWidth,
          over: cards.map(c => c.getBoundingClientRect().right)
                     .filter(r => r > grid.right + 1 || r > innerWidth)};
}"""


def _statistika_from_generator(tmp_path) -> Path:
    """Ģeneratora veidne (`src/render/statistika.py` → statistika.html.j2) ar
    tādu pašu kartīšu formu kā dzīvajā lapā — nākamā pārģenerēšana."""
    import json
    out = _site(tmp_path / "gen")
    cards = [{"table_id": f"T{i}", "domain": "ekonomika", "label": f"Rādītājs {i}",
              "formatted_value": "€1 946", "change": 1.2, "change_positive": True,
              "formatted_change": "+1,2 %", "insight": "Ilgtermiņa tendence aug.",
              "csp_updated_short": "2026-10-01", "index": i,
              "sparkline_labels": [str(y) for y in range(2000, 2026)],
              "sparkline_values": list(range(26))} for i in range(8)]
    html = _env().get_template("statistika.html.j2").render(
        cards=cards, last_updated="2026-10-01",
        cards_json=json.dumps([{k: v for k, v in c.items() if k != "change_positive"}
                               for c in cards], ensure_ascii=False))
    page = out / "statistika.html"
    page.write_text(html, encoding="utf-8")
    return page


def test_statistika_cards_stay_inside_the_page(tmp_path):
    """A6: `repeat(4, 1fr)` = `minmax(auto, 1fr)` → kanvas min-content 342 px
    izstiepa režģi līdz 1 416 px 1152 px konteinerā; 4. kolonna aiz ekrāna
    (`html { overflow-x: clip }` to slēpa). Gan dzīvā `curated/` lapa, gan
    ģeneratora veidne."""
    pages = [_curated_site(tmp_path) / "statistika.html", _statistika_from_generator(tmp_path)]
    with sync_api.sync_playwright() as pw:
        browser = _browser(pw)
        for page_path in pages:
            for width in (1280, 1440, 900, 640):
                ctx = _context(browser, width)
                page = ctx.new_page()
                page.goto(page_path.as_uri())
                page.wait_for_timeout(200)  # stv1.js uzzīmē sīkgrafikus
                g = page.evaluate(CARDS_INSIDE)
                assert g["n"] >= 4, g
                assert not g["over"], f"{page_path.parent.name} {width}px: kartītes aiz malas {g}"
                ctx.close()
        browser.close()


# ── Nedēļas pārskats ────────────────────────────────────────────────────

def test_weekly_brief_cards_follow_dark_theme_and_date_stays_whole(tmp_path):
    """A7: `.weekly-stat-card` fons `#f4efe4` u.c. hex → tumšajā 5 gaišas kartītes;
    zīmīte telefonā lūza datumā «2026-10-05 — 2026-/10-11»."""
    from src.render.blog import _weekly_content_for_render
    out = _site(tmp_path)
    content = _weekly_content_for_render(
        "## Nedēļa skaitļos\n\n<!-- WEEKLY_STATS: positions=314 votes=61 contradictions=2 "
        "top_topic=Aizsardzība un drošība top_party=Apvienotais saraksts -->\n\n"
        "### Tēma\n\nProza.\n", is_weekly=True)
    env = _env()
    env.filters["image_variant"] = lambda f, *a: f
    html = env.get_template("_weekly_body.html.j2").render(
        post={"title": "Nedēļas pārskats", "date": "2026-10-05 — 2026-10-11",
              "type_label": "Nedēļas pārskats", "slug": "nedela-2026-10-05"},
        content_html=content)
    page_path = out / "blog" / "nedela-2026-10-05.html"
    page_path.parent.mkdir()
    page_path.write_text(html, encoding="utf-8")
    with sync_api.sync_playwright() as pw:
        browser = _browser(pw)
        ctx = _context(browser, 390, theme="dark")
        page = ctx.new_page()
        page.goto(page_path.as_uri())
        # Diapazons no «2026-10-05» līdz «2026-10-11» beigām tajā teksta
        # mezglā, kurā ir datumi (pirms labojuma — visa zīmīte, pēc — span).
        g = page.evaluate("""() => {
          const badge = document.querySelector('.weekly-badge');
          const walker = document.createTreeWalker(badge, NodeFilter.SHOW_TEXT);
          let node = null;
          while (walker.nextNode()) if (walker.currentNode.data.includes('2026-10-11')) node = walker.currentNode;
          const r = document.createRange();
          r.setStart(node, node.data.indexOf('2026-10-05'));
          r.setEnd(node, node.data.indexOf('2026-10-11') + 10);
          const tops = new Set([...r.getClientRects()].map(x => Math.round(x.top)));
          return {cardBg: getComputedStyle(document.querySelector('.weekly-stat-card')).backgroundColor,
                  bodyBg: getComputedStyle(document.body).backgroundColor,
                  dateLines: tops.size, found: node.data.includes('2026-10-05')};
        }""")
        assert g["bodyBg"] == DARK_BG, "tumšā tēma nav ieslēgta — fikstūra salauzta"
        assert g["cardBg"] == DARK_SURFACE, f"tumšajā kartīte nav --surface: {g['cardBg']}"
        assert g["found"] and g["dateLines"] == 1, f"datums lūst {g['dateLines']} rindās"
        ctx.close()
        browser.close()


# ── Medija lapa ─────────────────────────────────────────────────────────

def test_outlet_average_marker_stays_on_its_track(tmp_path):
    """A13: vidējais visos medijos > šī medija lielākā daļa → `left: 150%`,
    atzīme uzkrīt procentu skaitlim (14 atzīmes 7/11 medijos)."""
    from src.render.mediji import render_mediji
    from tests.test_render_mediji import OUTLETS, _seed
    from tests.test_render_mediji import _env as mediji_env
    out = _site(tmp_path)
    db = _seed(str(tmp_path / "t.db"))
    render_mediji(mediji_env(), db, out, OUTLETS)
    page_path = out / "mediji" / "lsm.html"
    with sync_api.sync_playwright() as pw:
        browser = _browser(pw)
        for width in (390, 1280):
            ctx = _context(browser, width)
            page = ctx.new_page()
            page.goto(page_path.as_uri())
            g = page.evaluate("""() => [...document.querySelectorAll('.party-cover .cover-avg')]
              .map(m => {
                const t = m.closest('.cover-track').getBoundingClientRect();
                const c = m.closest('.cover-row').querySelector('.cover-count').getBoundingClientRect();
                const r = m.getBoundingClientRect();
                return {over: r.right - t.right, gapToCount: c.left - r.right};
              })""")
            assert g, "nav neviena vidējā atzīme — fikstūra nedod avg > share_max"
            for m in g:
                assert m["over"] <= 3, f"{width}px: atzīme {m['over']:.0f}px aiz joslas"
                assert m["gapToCount"] > 0, f"{width}px: atzīme uzkrīt skaitlim"
            ctx.close()
        browser.close()
