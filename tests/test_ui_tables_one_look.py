"""Tabulas — viens izskats visā vietnē (plāns «Vienotas filtru pogas …», 2c
fāze, 2026-10-23).

Kļūme, ko šis fails ķer: vienai lomai (datu tabula) bija deviņi izskati —
markdown tabulas pārskatos ar centrētu galveni un pilnu režģi uz --surface2,
`.data-table` ar lielu galvenes etiķeti un rāmi uz aptvērēja, NVO `.tbl`,
partiju testa `.pt-sum` un statistikas `.stat-data-table` katra ar savu
inline <style>. Viena izmaiņa vienā vietā (style.css «Pamatelementi» `.tbl`)
nedarbojas, ja kāda lapa joprojām zīmē savu.

Mērījums pārlūkā (Chromium), gaišajā un tumšajā tēmā, 1280 un 390 px, katrai
redzamai <table> (pēc elementa, ne klases — ķer arī nākamo klaiņojošo tabulu):
- galvenes šūna: burti, svars, retinājums, lielie burti, atkāpes, apakšmala,
  fons, krāsa — viens paraksts tēmā+platumā (līdzināšana nav daļa no
  paraksta: skaitļu kolonnas pa labi);
- ķermeņa šūna (pirmā rinda, ja rindu ≥ 2): burti, atkāpes, apakšmala —
  viens paraksts (krāsa ne: blāvāka pirmā kolonna, zem-sliekšņa rinda ir nozīme);
- rāmis: tabulas mala + rādiuss; ritinātājam (aptvērējs, kurā ir tikai
  tabula) pašam rāmja nav — citādi dubults;
- neviena galvene nav centrēta, ja autors to nav prasījis (operatora 1. ekrāns);
- skaitļu šūnas (`align="right"`, `text-align: right`, `.num`) — pa labi un
  ar vienāda platuma cipariem.

Telefonā (≤768 px) pārskatu/sintēžu/atradumu tabulas apzināti kļūst par
kartītēm (`td[data-label]`, 2026-09-08), profila pozīcijas — arī. Kartīte nav
tabula, tāpēc 390 px skaita tikai tabulas, kurām galvene joprojām redzama un
`display: table`.

Izņēmumi ar citu lomu: `.syn-matrix` (divu asu matrica ar ķeksīšiem, lipīga
galvene un kolonna). Fikstūra: koplietotais `rendered_site` (īstais renderētājs
uz iesaldētās fikstūras DB + curated/ momentuzņēmumi). Katra lapa izdrukā
saucēju; tabulu kopskaits zem sliekšņa = fikstūra neko nepārbauda → kļūme.
"""
from __future__ import annotations

import functools
import threading
from collections import defaultdict
from http.server import ThreadingHTTPServer

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

PAGES = [
    "blog/2026-05-25.html",
    "sintezes/saeima-2026-04-30-balsojumi.html",
    "sintezes/airbaltic-2-starpfinansejums-25-procenti.html",
    "analizes/deklaracijas-2026.html",
    "analizes/vad-2026.html",
    "analizes/nvo-valsts-maksajumi.html",
    "analizes/partiju-tests.html",
    "likumi/satversme.html",
    "partijas.html",
    "partijas/as.html",
    "politiki/andris-kulbergs.html",
    "index.html",
    "finanses.html",
    "statistika/DSV010m.html",
]
EXCEPT_SEL = ".syn-matrix"

COLLECT = r"""(exceptSel) => {
  // Atver visu, kas slēpj tabulas: <details> un slēptas cilnes/paneļus.
  document.querySelectorAll('details').forEach(d => { d.open = true; });
  document.querySelectorAll('table').forEach(t => {
    for (let p = t.parentElement; p; p = p.parentElement) if (p.hidden) p.hidden = false;
  });
  const vis = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const S = (e, props) => { const s = getComputedStyle(e); return props.map(p => s[p]).join(' '); };
  const TH = ['fontSize', 'fontWeight', 'letterSpacing', 'textTransform', 'paddingTop',
              'paddingLeft', 'borderBottomWidth', 'borderBottomColor', 'backgroundColor', 'color'];
  const TD = ['fontSize', 'paddingTop', 'paddingLeft', 'borderBottomWidth', 'borderBottomColor'];
  const name = t => (t.className || '<table>') + ' «' +
    ((t.querySelector('th, td') || t).textContent || '').trim().slice(0, 18) + '»';
  const numeric = c => c.getAttribute('align') === 'right' || c.classList.contains('num')
    || /text-align:\s*right/.test(c.getAttribute('style') || '');
  const out = [];
  for (const t of document.querySelectorAll('table')) {
    if (t.matches(exceptSel) || !vis(t)) continue;
    const th = [...t.querySelectorAll('th')].find(vis);
    const tableLike = getComputedStyle(t).display === 'table';
    if (!tableLike) continue;           // telefona kartītes (data-label) nav tabula
    const rows = [...t.querySelectorAll('tbody tr')].filter(vis);
    const td = rows.length >= 2 ? [...rows[0].querySelectorAll('td')].find(vis) : null;
    const wrap = t.parentElement;
    const ws = getComputedStyle(wrap), ts = getComputedStyle(t);
    const centered = [...t.querySelectorAll('th')].filter(vis)
      .filter(c => getComputedStyle(c).textAlign === 'center' && !c.getAttribute('align')
                   && !/text-align/.test(c.getAttribute('style') || ''))
      .map(c => c.textContent.trim().slice(0, 14));
    const nums = [...t.querySelectorAll('td, th')].filter(vis).filter(numeric).map(c => {
      const s = getComputedStyle(c);
      return (s.textAlign === 'right' || s.textAlign === 'end') && s.fontVariantNumeric.includes('tabular-nums');
    });
    out.push({
      name: name(t),
      th: th ? S(th, TH) : null,
      td: td ? S(td, TD) : null,
      frame: [ts.borderTopWidth, ts.borderTopStyle, ts.borderTopColor, ts.borderTopLeftRadius,
              // Aptvērēja rāmis skaitās tikai, ja aptvērējs ir tabulas ritinātājs
              // (tabula — vienīgais bērns); kartīte ar tekstu un tabulu nav dubults rāmis.
              (wrap.children.length === 1 && parseFloat(ws.borderTopWidth) > 0 ? 'DUBULTS-RĀMIS' : 'viens-rāmis')].join(' '),
      centered, numsOk: nums.filter(Boolean).length, numsBad: nums.filter(x => !x).length,
    });
  }
  return out;
}"""


@pytest.fixture(scope="module")
def measured(rendered_site):
    from tests.test_multiselect_dropdown import _QuietHandler

    handler = functools.partial(_QuietHandler, directory=str(rendered_site))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    site = f"http://127.0.0.1:{server.server_address[1]}"
    results = {}
    try:
        with sync_api.sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except Exception as exc:  # pragma: no cover — nav instalēta pārlūka
                pytest.skip(f"Chromium nav pieejams: {exc}")
            for theme in ("light", "dark"):
                for width in (1280, 390):
                    ctx = browser.new_context(viewport={"width": width, "height": 900},
                                              color_scheme=theme, reduced_motion="reduce")
                    ctx.add_init_script(f"localStorage.setItem('atmina:theme', '{theme}')")
                    ctx.route("**/*", lambda r: r.abort()
                              if r.request.url.startswith("http")
                              and not r.request.url.startswith(site) else r.continue_())
                    page = ctx.new_page()
                    page.set_default_timeout(8000)
                    for path in PAGES:
                        page.goto(f"{site}/{path}", wait_until="domcontentloaded")
                        page.wait_for_selector("table", state="attached")
                        page.mouse.move(0, 0)
                        results[(theme, width, path)] = page.evaluate(COLLECT, EXCEPT_SEL)
                    ctx.close()
            browser.close()
    finally:
        server.shutdown()
    return results


def _by_view(measured, key):
    views = defaultdict(lambda: defaultdict(list))
    for (theme, width, path), tables in measured.items():
        for t in tables:
            if t[key] is not None:
                views[(theme, width)][t[key]].append(f"{path}: {t['name']}")
    return views


def test_denominators(measured):
    per_view = defaultdict(int)
    for (theme, width, path), tables in sorted(measured.items()):
        print(f"\n{theme} {width} {path}: tabulas {len(tables)},"
              f" ar galveni {sum(t['th'] is not None for t in tables)}")
        per_view[(theme, width)] += len(tables)
    print(f"\ntabulas skatā: {dict(per_view)}")
    # 2026-10-23: 48 tabulas datorā, 12 telefonā (pārējās tur ir kartītes).
    floor = {1280: 40, 390: 8}
    low = [f"{t}/{w}: {n}" for (t, w), n in per_view.items() if n < floor[w]]
    assert len(per_view) == 4 and not low, f"fikstūra neko nepārbauda: {low}"


@pytest.mark.parametrize("part", ["th", "td", "frame"])
def test_one_look_per_view(measured, part):
    bad = []
    for (theme, width), shapes in sorted(_by_view(measured, part).items()):
        n = sum(len(v) for v in shapes.values())
        print(f"\n{part} {theme} {width}: {len(shapes)} izskati / {n} tabulas")
        for s, who in sorted(shapes.items(), key=lambda x: -len(x[1])):
            print(f"   {len(who):3} × [{s}]  piem. {who[0]}")
        assert n > 0, f"{part} {theme} {width}: saucējs 0"
        if len(shapes) != 1:
            bad.append(f"{theme}/{width}: {len(shapes)} izskati")
    assert len(_by_view(measured, part)) == 4, "trūkst kāda skata (tēma × platums)"
    assert not bad, f"{part}: vairāk par vienu izskatu — {bad}"


def test_headers_not_centered_and_numbers_line_up(measured):
    centered, num_ok, num_bad = [], 0, []
    for (theme, width, path), tables in sorted(measured.items()):
        for t in tables:
            if t["centered"]:
                centered.append(f"{theme}/{width}/{path}: {t['name']} {t['centered'][:3]}")
            num_ok += t["numsOk"]
            if t["numsBad"]:
                num_bad.append(f"{theme}/{width}/{path}: {t['name']} ×{t['numsBad']}")
    print(f"\nskaitļu šūnas pa labi ar tabular-nums: {num_ok}, slikti: {len(num_bad)};"
          f" centrētas galvenes tabulās: {len(centered)}")
    assert num_ok > 0, "neviena skaitļu šūna — saucējs 0"
    assert not centered, f"centrētas galvenes: {centered[:6]}"
    assert not num_bad, f"skaitļi nav pa labi / bez tabular-nums: {num_bad[:6]}"
