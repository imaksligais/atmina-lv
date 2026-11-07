"""Pretrunu saraksts telefonā: dziļā saite `pretrunas.html#pretruna-N` rāda
rindas galvu zem nav, ne zem tās (good-css 5. kārta, A2; 2026-10-21).

Kļūme, ko šis tests ķer: `prv1.js` ritina mērķa rindu ar
`scrollIntoView({block: 'start'})`, bet `.prv2-row` nebija `scroll-margin`,
tāpēc rinda apstājās pie y=0 — zem lipīgās nav (69 px pie 390 px). Lasītājs,
kas atnāk no publicēta pārskata saites, redzēja tikai datumus, ne vārdu,
smagumu un tēmu. Audits: docs/audits/2026-10-21-good-css-5/pretrunas.md § 1.

Tā pati fikstūra pārbauda detaļu lapas virsrakstu «Citas šī politiķa
pretrunas» (A10): agrāk «Citas Andris Kulbergs pretrunas» — nominatīvs.

Renders caur ĪSTO orķestratoru (kā tests/test_withdraw_contradiction.py),
Playwright pret renderēto lapu ar īstajiem assets/*.
"""
from __future__ import annotations

import re
import shutil
from datetime import timedelta
from pathlib import Path

import pytest

from src.db import get_db, init_db, today_lv
from src.saeima.schema import init_saeima_bills, init_saeima_tables

sync_api = pytest.importorskip("playwright.sync_api")

REPO = Path(__file__).resolve().parent.parent
N_ROWS = 14          # pietiekami gara lapa, lai mērķi var aizritināt līdz augšai
TARGET = 3           # zemākā rinda sarakstā (jaunākās augšā) ir tālu lejā
DIRECT = N_ROWS      # jaunākā rinda — saraksta augšā, tiešā pretruna


def _seed(path: str) -> None:
    init_db(path)
    init_saeima_tables(path)
    init_saeima_bills(path)
    db = get_db(path)
    day = (today_lv() - timedelta(days=30)).strftime("%Y-%m-%d")
    new_day = (today_lv() - timedelta(days=1)).strftime("%Y-%m-%d")
    db.executescript(f"""
        INSERT INTO parties (id, name, short_name) VALUES (1, 'Jaunā Vienotība', 'JV');
        INSERT INTO tracked_politicians (id, name, party, role, relationship_type)
            VALUES (1, 'Testa Politiķis', 'Jaunā Vienotība', 'Saeimas deputāts', 'tracked');
        INSERT INTO documents (id, source_url, title, content, content_hash, platform, scraped_at)
            VALUES (1, 'https://example.lv/a', 'A', 'teksts', 'h1', 'web', '{day} 10:00:00');
        INSERT INTO claims (id, opponent_id, document_id, topic, stance, source_url, stated_at, claim_type)
            VALUES (1, 1, 1, 'Budžets un finanses', 'Atbalsta deficītu', 'https://example.lv/a', '{day} 10:00:00', 'position'),
                   (2, 1, 1, 'Budžets un finanses', 'Iebilst deficītam', 'https://example.lv/a', '{new_day} 11:00:00', 'position');
    """)
    for i in range(1, N_ROWS + 1):
        db.execute(
            "INSERT INTO contradictions (id, opponent_id, claim_old_id, claim_new_id, topic,"
            " summary, headline, severity, salience, reviewed, confirmed, detected_at)"
            " VALUES (?, 1, 1, 2, 'Budžets un finanses', ?, ?, ?, 0.8, 1, 1, ?)",
            # Viena tiešā pretruna — tumšās tēmas sarkanās birkas kontrastam (A8).
            (i, "Mainīta nostāja par budžeta deficītu."
             + (" [Izteikumi attiecas uz budžeta deficītu.]" if i == 5 else ""),
             f"Budžeta deficīts — priekšlikums Nr. {i}",
             "direct_contradiction" if i == DIRECT else "reversal",
             f"{day} {i:02d}:00:00"),
        )
    db.commit()
    db.close()


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    import src.render._orchestrator as orch
    import src.render.contradictions as contra_mod
    from src.render._common import og_render

    base = tmp_path_factory.mktemp("pretrunas_mobile")
    db_path = str(base / "p.db")
    _seed(db_path)
    with pytest.MonkeyPatch.context() as mp:
        mp.chdir(REPO)
        mp.setattr(orch, "_download_chart_js", lambda *a, **k: None)
        mp.setattr(orch, "_download_annotation_plugin", lambda *a, **k: None)
        mp.setattr(contra_mod, "_render_og_cards", lambda *a, **k: 0)
        mp.setattr(og_render, "render_og_images", lambda jobs, root: 0)
        orch.generate_public_site(
            db_path=db_path, output_dir=str(base / "site"), only={"pretrunas", "static"},
        )
    out = base / "site" / "atmina"
    shutil.copytree(REPO / "assets", out / "assets", dirs_exist_ok=True)
    return out


ROW_GEOMETRY = """(id) => {
  const nav = document.querySelector('.nav');
  const row = document.getElementById('pretruna-' + id);
  return {navPos: getComputedStyle(nav).position,
          navBottom: nav.getBoundingClientRect().bottom,
          rowTop: row.getBoundingClientRect().top,
          headTop: row.querySelector('.prv2-row-head').getBoundingClientRect().top,
          scrollY: window.scrollY};
}"""


def test_deeplink_row_head_below_nav(site):
    page_path = site / "pretrunas.html"
    assert f'id="pretruna-{TARGET}"' in page_path.read_text(encoding="utf-8")
    with sync_api.sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Exception as exc:  # pragma: no cover — nav instalēta pārlūka
            pytest.skip(f"Chromium nav pieejams: {exc}")
        ctx = browser.new_context(viewport={"width": 390, "height": 700},
                                  reduced_motion="reduce")
        page = ctx.new_page()
        page.goto(page_path.as_uri() + f"#pretruna-{TARGET}")
        # prv1.js ritina ar behavior:'smooth' — gaida, līdz pozīcija nostājas.
        page.wait_for_function(
            """(id) => { const r = document.getElementById('pretruna-' + id);
                 const t = r.getBoundingClientRect().top;
                 const prev = window.__lastTop; window.__lastTop = t;
                 return r.classList.contains('open') && prev === t; }""",
            arg=TARGET, polling=150, timeout=8000)
        g = page.evaluate(ROW_GEOMETRY, TARGET)
        browser.close()
    assert g["navPos"] == "sticky", "stili nav ielādēti vai nav nav lipīga"
    assert g["scrollY"] > 200, f"lapa netika ritināta (scrollY={g['scrollY']}) — gadījums tukšs"
    assert g["headTop"] >= g["navBottom"] - 1, (
        f"rindas galva {g['headTop']:.0f}px ir zem nav (apakša {g['navBottom']:.0f}px)")


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_detail_card_has_one_surface_and_severity_bar(site, theme):
    """Card sections must not reintroduce stacked fills or a party-coloured bar."""
    with sync_api.sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto((site / "pretrunas" / "5.html").as_uri())
        page.evaluate("theme => document.documentElement.dataset.theme = theme", theme)
        styles = page.locator(".prv2-card").evaluate("""card => {
            const style = e => getComputedStyle(e);
            const probe = document.createElement('i');
            probe.style.backgroundColor = 'var(--prv2-sev)';
            card.append(probe);
            const severity = style(probe).backgroundColor;
            probe.remove();
            return {
                backgrounds: Object.fromEntries(
                    ['.prv2-head', '.prv2-foot', '.prv2-context', '.prv2-pane-new']
                    .map(s => [s, style(card.querySelector(s)).backgroundColor])),
                bar: style(card.querySelector('.prv2-partybar')).backgroundColor,
                severity,
            };
        }""")
        browser.close()
    assert styles == {
        "backgrounds": {s: "rgba(0, 0, 0, 0)" for s in
                        (".prv2-head", ".prv2-foot", ".prv2-context", ".prv2-pane-new")},
        "bar": styles["severity"],
        "severity": styles["severity"],
    }, f"{theme}: card sections must be transparent and the bar must match severity"


def test_detail_related_heading_does_not_inflect_name(site):
    html = (site / "pretrunas" / "5.html").read_text(encoding="utf-8")
    assert "prv2-detail-related" in html, "saistīto pretrunu bloks nav renderēts — gadījums tukšs"
    assert "<h2>Citas šī politiķa pretrunas</h2>" in html
    assert "Citas Testa Politiķis pretrunas" not in html


def test_detail_related_distinguishes_same_topic_with_headlines_and_dates(site):
    """Repeated topics and summaries must not hide which contradiction a link opens."""
    html = (site / "pretrunas" / "5.html").read_text(encoding="utf-8")
    related = re.search(r'<section class="prv2-detail-related">(.*?)</section>', html, re.S)
    assert related, "Related contradictions are missing"
    links = re.findall(r'<a\b[^>]*href="(\d+)\.html"[^>]*>(.*?)</a>', related[1], re.S)
    assert {int(id_) for id_, _ in links} == {N_ROWS, N_ROWS - 1, N_ROWS - 2}
    for id_, body in links:
        assert f"Budžeta deficīts — priekšlikums Nr. {id_}" in body
        dates = re.findall(r'<time datetime="([^"]+)">([^<]+)</time>', body)
        expected = [today_lv() - timedelta(days=days) for days in (30, 1)]
        assert dates == [(d.isoformat(), d.strftime("%d.%m.%Y")) for d in expected]
        assert "→" in body


DARK_CONTRAST = r"""() => {
  const rgb = c => c.match(/[\d.]+/g).map(Number);
  const lum = a => { const [r, g, b] = a.slice(0, 3).map(v => { v /= 255;
      return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); });
    return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
  const bg = e => { for (let a = e; a; a = a.parentElement) {
      const c = rgb(getComputedStyle(a).backgroundColor);
      if (c.length < 4 || c[3] > 0.5) return c; }
    return rgb(getComputedStyle(document.body).backgroundColor); };
  const ratio = (f, b) => { const x = lum(f), y = lum(b);
    return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const sel = ['.prv2-row-dates', '.prv2-chip:not(.active) .prv2-chip-n',
               '.sev-direct_contradiction .prv2-sevbadge',
               '.sev-direct_contradiction .prv2-kicker-sev'];
  const out = [];
  for (const s of sel) for (const e of document.querySelectorAll(s)) {
    const r = e.getBoundingClientRect(); if (!r.width || !r.height) continue;
    out.push([s, +ratio(rgb(getComputedStyle(e).color), bg(e)).toFixed(2)]); }
  const root = getComputedStyle(document.documentElement);
  const tok = n => { const d = document.createElement('i'); d.style.color = `var(${n})`;
    document.body.append(d); const c = rgb(getComputedStyle(d).color); d.remove(); return lum(c); };
  return {theme: document.documentElement.dataset.theme || 'dark', out,
          dimLum: tok('--text-dim'), mutedLum: tok('--text-muted')};
}"""


def test_dark_theme_dim_text_and_red_badge_are_readable(site):
    """A8 (2026-10-21): tumšajā tēmā `--text-dim` #5e6478 bija 2,96:1 uz
    `--surface` — rindu datumi, čipu skaitļi un desmitiem citu vietu visā
    vietnē; «Tiešā pretruna» sarkanais #dc2626 — 3,03:1 uz `--surface2`.
    Pēc labojuma ≥ 4,5:1, un `--text-dim` paliek blāvāks par `--text-muted`
    (hierarhija nesaplūst)."""
    with sync_api.sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Exception as exc:  # pragma: no cover — nav instalēta pārlūka
            pytest.skip(f"Chromium nav pieejams: {exc}")
        ctx = browser.new_context(viewport={"width": 390, "height": 900},
                                  reduced_motion="reduce")
        ctx.add_init_script("localStorage.setItem('atmina:theme', 'dark')")
        page = ctx.new_page()
        page.goto((site / "pretrunas.html").as_uri() + f"#pretruna-{DIRECT}")
        page.wait_for_selector(f"#pretruna-{DIRECT}.open .prv2-sevbadge", timeout=8000)
        g = page.evaluate(DARK_CONTRAST)
        browser.close()
    found = {s for s, _ in g["out"]}
    print(f"\ntumšā tēma: {len(g['out'])} teksta elementi, {len(found)}/4 selektori")
    assert len(found) == 4, f"ne visi elementi atrasti — gadījums nepilns: {found}"
    low = [x for x in g["out"] if x[1] < 4.5]
    assert not low, f"tumšajā tēmā kontrasts < 4,5:1: {low}"
    assert g["dimLum"] < g["mutedLum"], "--text-dim nav blāvāks par --text-muted"


TARGET_STYLE = """(id) => {
  const s = e => getComputedStyle(e);
  const row = document.getElementById('pretruna-' + id);
  const other = document.getElementById('pretruna-' + (id + 1));
  const sev = s(row).getPropertyValue('--prv2-sev').trim();
  const probe = document.createElement('i'); probe.style.color = sev; row.append(probe);
  const sevRgb = s(probe).color; probe.remove();
  return {style: s(row).outlineStyle, color: s(row).outlineColor, sevRgb,
          otherStyle: s(other).outlineStyle, anim: s(row).animationName,
          pulseClass: row.classList.contains('prv2-card-pulse')};
}"""


@pytest.mark.parametrize("motion", ["reduce", "no-preference"])
def test_deeplink_row_is_marked_by_target_not_js_pulse(site, motion):
    """C (2026-10-21): mērķa rindu iezīmē CSS `.prv2-row:target` smaguma krāsā,
    nevis prv1.js `prv2-card-pulse` klase ar setTimeout (kas 2 s vēlāk
    iezīmējumu izdzēsa — lasītājs, kas ritināja lēnāk, to neredzēja).
    Uzplaiksnījuma animācija tikai, ja kustība atļauta."""
    with sync_api.sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Exception as exc:  # pragma: no cover — nav instalēta pārlūka
            pytest.skip(f"Chromium nav pieejams: {exc}")
        ctx = browser.new_context(viewport={"width": 390, "height": 700}, reduced_motion=motion)
        page = ctx.new_page()
        page.goto((site / "pretrunas.html").as_uri() + f"#pretruna-{TARGET}")
        page.wait_for_selector(f"#pretruna-{TARGET}.open", timeout=8000)
        page.wait_for_timeout(2300)  # vecais setTimeout (2000 ms) būtu jau notīrījis
        g = page.evaluate(TARGET_STYLE, TARGET)
        browser.close()
    assert g["style"] == "solid", f"mērķa rindai nav :target kontūras: {g}"
    assert g["color"] == g["sevRgb"], f"kontūra nav smaguma krāsā: {g}"
    assert g["otherStyle"] == "none", f"kontūra arī ne-mērķa rindai: {g}"
    assert not g["pulseClass"], "prv1.js joprojām liek prv2-card-pulse klasi"
    assert (g["anim"] == "prv2-target-flash") == (motion == "no-preference"), g


COPY_PROBE = """(sel) => {
  const b = document.querySelector(sel);
  const r = b.getBoundingClientRect(), a = getComputedStyle(b, '::after');
  return {h: r.height, hitTop: parseFloat(a.top), hitBottom: parseFloat(a.bottom),
          url: b.dataset.copyUrl};
}"""


@pytest.mark.parametrize("page_name", ["pretrunas/5.html", "pretrunas.html"])
def test_copy_link_button_copies_contradiction_url(site, page_name):
    """C (2026-10-21): pretrunas kājenē blakus «𝕏 Dalīties» — «Kopēt saiti»
    ar esošo chrome-v1.js kopēšanas apstrādi (bez jauna JS). Kopē pretrunas
    pastāvīgo adresi /pretrunas/<id>.html; telefonā pieskāriena laukums ≥ 44 px;
    sarakstā klikšķis neaizver atvērto rindu."""
    with sync_api.sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Exception as exc:  # pragma: no cover — nav instalēta pārlūka
            pytest.skip(f"Chromium nav pieejams: {exc}")
        ctx = browser.new_context(viewport={"width": 390, "height": 800}, reduced_motion="reduce")
        ctx.grant_permissions(["clipboard-read", "clipboard-write"])
        page = ctx.new_page()
        hash_ = f"#pretruna-{TARGET}" if page_name == "pretrunas.html" else ""
        page.goto((site / page_name).as_uri() + hash_)
        scope = f"#pretruna-{TARGET} " if hash_ else ""
        sel = scope + ".prv2-foot-share .share-btn-copy"
        if hash_:
            page.wait_for_selector(f"#pretruna-{TARGET}.open", timeout=8000)
        g = page.evaluate(COPY_PROBE, sel)
        page.locator(sel).click()
        page.wait_for_function("(s) => document.querySelector(s).textContent === 'Nokopēts!'",
                               arg=sel, timeout=3000)
        copied = page.evaluate("navigator.clipboard.readText()")
        still_open = page.evaluate(f"!!document.querySelector('#pretruna-{TARGET}.open')") if hash_ else True
        browser.close()
    want_id = TARGET if hash_ else 5
    assert g["url"].endswith(f"/pretrunas/{want_id}.html"), g
    assert copied == g["url"], f"starpliktuvē {copied!r}, gaidīts {g['url']!r}"
    assert g["h"] - g["hitTop"] - g["hitBottom"] >= 44 - 0.5, f"pieskāriena laukums < 44 px: {g}"
    assert still_open, "klikšķis uz «Kopēt saiti» aizvēra rindu"



def test_share_button_opens_phone_share_sheet(site):
    """2026-10-23: telefonā «Dalīties» atver sistēmas dalīšanās izvēlni
    (navigator.share) ar pretrunas adresi, nevis X logu. Kļūme, ko ķer:
    klikšķis aiziet uz x.com vai izvēlnei nonāk tukša / nepareiza adrese."""
    with sync_api.sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Exception as exc:  # pragma: no cover — nav instalēta pārlūka
            pytest.skip(f"Chromium nav pieejams: {exc}")
        ctx = browser.new_context(viewport={"width": 390, "height": 800},
                                  has_touch=True, is_mobile=True)
        ctx.add_init_script("""Object.defineProperty(navigator, 'share', {configurable: true,
          value: (d) => { window.__shared = d; return Promise.resolve(); }});""")
        page = ctx.new_page()
        page.goto((site / "pretrunas/5.html").as_uri())
        page.locator(".prv2-foot-share .share-btn-x").click()
        page.wait_for_function("!!window.__shared", timeout=3000)
        shared = page.evaluate("window.__shared")
        pages = len(ctx.pages)
        browser.close()
    assert shared["url"].endswith("/pretrunas/5.html"), shared
    assert pages == 1, "atvērās X logs blakus dalīšanās izvēlnei"

@pytest.mark.parametrize(("motion", "want"), [("reduce", "auto"), ("no-preference", "smooth")])
def test_deeplink_scroll_respects_reduced_motion(site, motion, want):
    """Recenzija M5: prv1.js ritināja ar behavior:'smooth' arī tad, ja lasītājs
    lūdzis samazinātu kustību. Ieraksta scrollIntoView argumentus."""
    with sync_api.sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Exception as exc:  # pragma: no cover — nav instalēta pārlūka
            pytest.skip(f"Chromium nav pieejams: {exc}")
        ctx = browser.new_context(viewport={"width": 390, "height": 700}, reduced_motion=motion)
        ctx.add_init_script("""(() => { const orig = Element.prototype.scrollIntoView;
          window.__siv = [];
          Element.prototype.scrollIntoView = function (o) {
            if (this.id && this.id.startsWith('pretruna-')) window.__siv.push(o && o.behavior);
            return orig.call(this, o); }; })();""")
        page = ctx.new_page()
        page.goto((site / "pretrunas.html").as_uri() + f"#pretruna-{TARGET}")
        page.wait_for_selector(f"#pretruna-{TARGET}.open", timeout=8000)
        calls = page.evaluate("window.__siv")
        browser.close()
    assert calls, "prv1.js neizsauca scrollIntoView — gadījums tukšs"
    assert set(calls) == {want}, f"{motion}: behavior {calls}, gaidīts {want}"
