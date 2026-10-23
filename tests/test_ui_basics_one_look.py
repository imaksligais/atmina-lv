"""Filtru čipi, meklēšanas lauki un segmentu slēdži — viens izskats visā vietnē
(plāns «Vienotas filtru pogas, segmentu slēdži un meklēšanas lauki», 1. fāze,
2026-10-23).

Kļūme, ko šis fails ķer: tai pašai lomai bija seši dažādi izskati — čipi ar
rādiusu 4/10/20/32/999 px, burtiem 12–15 px, aktīvais stāvoklis = sarkans
pildījums vienā lapā, zils rgba otrā, tikai rāmis trešajā; meklēšanas lauki
ar rādiusu 0/4/6/10 px. Viena izmaiņa vienā vietā (style.css «Pamatelementi»)
nedarbojas, ja kāda lapa joprojām zīmē savu.

Mērījums pārlūkā (Chromium), gaišajā un tumšajā tēmā, 1280 un 390 px:
- čipi (``.chip`` + vēsturiskās klases, lai fails krīt arī uz veco koku):
  formas paraksts (rādiuss, augstums, burti, atkāpes, rāmja platums) — tieši
  viens visās lapās kopā; neaktīvajiem čipiem viens krāsu paraksts tēmā;
  aktīvais fons atšķiras no neaktīvā (redzams stāvoklis);
- lauki (``.field`` vai vecais ievadlauks / nolaižamā saraksta poga):
  rādiuss, augstums, rāmja platums, burti — viens paraksts;
- segmentu slēdži (``.seg-ctl-btn`` + vecās klases): viens formas paraksts.

2. fāze (2026-10-23): redakcionālās lapas (Pozīcijas, Personas, X) lieto tos
pašus čipus un laukus — telefonā arī ar atvērtu filtru paneli. Kompaktā
saime (``.field--compact``, ``.multi-select--compact`` poga, X nolaižamie
saraksti, personu meklētājs filtru sānjoslā): viens paraksts, augstums =
čipa augstums. Un tieši tas, ko lasītājs redz: nolaižamā saraksta poga, kas
stāv vienā rindā ar čipiem, ir tikpat augsta kā čipi (agrāk 44 px pret 32 px).

Katra lapa izdrukā saucēju (cik elementu pārbaudīts); 0 kādā gaidītā saimē =
fikstūra neko nepārbauda → kļūme. Fikstūras: īstais renderētājs uz sintētiskas
DB (``generate_public_site``), balsojumi — ``test_phone_tap_targets`` paraugs,
statistikas apakšlapa — iesaldētais ``curated/`` momentuzņēmums (tas tiek
publicēts, ne veidne).
"""
from __future__ import annotations

import functools
import shutil
import threading
from collections import defaultdict
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from src.db import get_db

sync_api = pytest.importorskip("playwright.sync_api")

REPO = Path(__file__).resolve().parent.parent

# Vēsturiskās klases paliek blakus jaunajām (JS tās meklē), tāpēc tās te ir
# tikai, lai vecais koks krīt. `.topic-filter-btn` (pasvītrojuma cilne) un
# `#votes-archive-more` («Rādīt vairāk» — poga) apzināti nav čipi.
CHIP_SEL = (".chip, .filter-btn:not(.topic-filter-btn), .link-filter-btn:not(#votes-archive-more),"
            " .prv2-chip, .vote-split-toggle, .parskats-topic-chip, .stat-event-chip, .vote-sort-btn,"
            " .pzv1-chip, .pnv1-chip, .xv1-chip, .xv1-topic-chip, .pzv1-mobile-toggle,"
            " .pnv1-mobile-toggle, .pzv1-clear-chip, .pnv1-clear-chip, .pzv1-mobile-clearall,"
            " .pnv1-clearall")
# Kompaktā saime (čipa augstumā): sānjoslas meklētājs, X nolaižamie saraksti un
# nolaižamie saraksti, kas stāv rindā ar čipiem. Pārējie lauki — pilnais augstums.
COMPACT_SEL = (".field--compact, .pzv1-rail-search-input, .xv1-select-trigger,"
               " .multi-select--compact .multi-select-trigger")
FIELD_SEL = (".field, .bill-search-input, #saites-search, .multi-select-trigger,"
             " .pzv1-search-input, .pnv1-search-input")
SEG_SEL = ".seg-ctl-btn, .prv2-seg-btn, .slv-lens"
TRIGGER_SEL = ".multi-select-trigger, .xv1-select-trigger"

COLLECT = r"""([chipSel, fieldSel, segSel, compactSel, triggerSel]) => {
  const vis = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const shape = (e, props) => { const s = getComputedStyle(e); return props.map(p => s[p]).join(' '); };
  const CHIP = ['borderTopLeftRadius', 'height', 'fontSize', 'fontWeight', 'paddingLeft',
                'paddingTop', 'borderTopWidth'];
  const FIELD = ['borderTopLeftRadius', 'height', 'borderTopWidth'];
  const name = e => (e.className && typeof e.className === 'string' ? e.className : e.tagName)
                    + ' «' + (e.textContent || e.placeholder || '').trim().slice(0, 16) + '»';
  const on = e => e.classList.contains('active') || e.getAttribute('aria-pressed') === 'true'
                  || e.getAttribute('aria-expanded') === 'true';
  const chips = [...document.querySelectorAll(chipSel)].filter(vis).map(e => {
    const s = getComputedStyle(e);
    return {name: name(e), shape: shape(e, CHIP), on: on(e),
            paint: [s.color, s.backgroundColor, s.borderTopColor].join(' '), bg: s.backgroundColor};
  });
  // Lauka redzamā kaste: `.field` aptvērējs, ja tāds ir, citādi pats elements.
  const box = e => e.closest('.field') || e;
  const compactBoxes = new Set([...document.querySelectorAll(compactSel)].map(box));
  const boxes = new Set([...document.querySelectorAll(fieldSel)].map(box)
                          .filter(e => !compactBoxes.has(e)));
  const measure = e => {
    const text = e.matches('input, button') ? e : (e.querySelector('input') || e);
    return {name: name(e), shape: shape(e, FIELD) + ' ' + getComputedStyle(text).fontSize,
            h: e.getBoundingClientRect().height};
  };
  const fields = [...boxes].filter(vis).map(measure);
  const compact = [...compactBoxes].filter(vis).map(measure);
  const segs = [...document.querySelectorAll(segSel)].filter(vis).map(e =>
    ({name: name(e), shape: shape(e, CHIP)}));
  // Nolaižamā saraksta poga un čipi, kas stāv tajā pašā vizuālajā rindā
  // (čipa vidus poga augstumā) — lasītājs tos redz kā vienu rīkjoslu.
  const chipEls = [...document.querySelectorAll(chipSel)].filter(vis);
  const rows = [...document.querySelectorAll(triggerSel)].filter(vis).map(t => {
    const r = t.getBoundingClientRect();
    const mates = chipEls.map(c => c.getBoundingClientRect())
      .filter(c => { const y = c.top + c.height / 2; return y > r.top && y < r.bottom; })
      .map(c => c.height);
    return {name: name(t), h: r.height, chips: mates};
  }).filter(x => x.chips.length);
  return {chip: chips, field: fields, seg: segs, compact: compact, row: rows};
}"""


# ── Fikstūra ──────────────────────────────────────────────────────────────


def _seed(path: str) -> None:
    """Pretrunu lapas DB + likumprojekts + 3 pozīcijas vienā tēmā (pārskata
    tēmu čipi, PARSKATS_TOPIC_COUNT_MIN) + saikne (Saišu lapas tipu filtri)."""
    from tests.test_pretrunas_mobile import _seed as seed_pretrunas

    seed_pretrunas(path)
    db = get_db(path)
    db.executescript("""
        INSERT INTO tracked_politicians (id, name, party, role, relationship_type)
            VALUES (2, 'Otra Politiķe', 'Jaunā Vienotība', 'Saeimas deputāte', 'tracked');
        INSERT INTO saeima_bills (document_nr, bill_type, title, topic, base_law_slug,
                                  current_stage, current_status, first_seen_at, last_updated_at)
            VALUES ('1288/Lp14', 'Lp14', 'Grozījums Saeimas vēlēšanu likumā', 'Tieslietas',
                    'saeimas-velesanu-likums', '1.lasījums', 'procesā',
                    '2026-04-01 10:00:00', '2026-04-15 14:00:00');
        INSERT INTO political_tensions (source_pid, target_pid, topic, description,
                                        tension_type, source_url)
            VALUES (1, 2, 'Budžets un finanses', 'Kritizē budžetu.', 'uzbrukums',
                    'https://example.lv/t');
        -- X plūsmas ieraksts ar tēmu (tēma = pozīcija ar to pašu source_url):
        -- ieraksta tēmas čips un, ar ?tema=, noņemamais tēmas čips joslā.
        INSERT INTO social_accounts (opponent_id, platform, handle, feed_type, active)
            VALUES (1, 'twitter', 'testa_pol', 'first_party', 1);
        INSERT INTO documents (id, source_url, content, content_hash, platform, source_domain,
                               scraped_at, published_at)
            VALUES (50, 'https://x.com/testa_pol/status/50', 'Ieraksts par budžetu.', 'h50',
                    'twitter', 'x.com', '2026-10-20 09:00:00', '2026-10-20T09:00:00');
        INSERT INTO document_politicians (document_id, politician_id, role)
            VALUES (50, 1, 'subject');
    """)
    day = db.execute("SELECT stated_at FROM claims WHERE id = 1").fetchone()[0]
    for i in range(3, 6):
        db.execute("INSERT INTO claims (id, opponent_id, document_id, topic, stance, source_url,"
                   " stated_at, claim_type) VALUES (?, 1, 1, 'Budžets un finanses', 'Pozīcija.',"
                   " ?, ?, 'position')", (i, f"https://example.lv/c{i}", day))
    db.execute("INSERT INTO claims (id, opponent_id, document_id, topic, stance, source_url,"
               " stated_at, claim_type) VALUES (6, 1, 50, 'Budžets un finanses', 'Pozīcija X.',"
               " 'https://x.com/testa_pol/status/50', ?, 'position')", (day,))
    db.commit()
    db.close()


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    import src.render._orchestrator as orch
    import src.render.contradictions as contra_mod
    from src.render._common import og_render
    from tests.test_multiselect_dropdown import _QuietHandler
    from tests.test_phone_tap_targets import _balsojumi

    base = tmp_path_factory.mktemp("ui_basics")
    db_path = str(base / "u.db")
    _seed(db_path)
    with pytest.MonkeyPatch.context() as mp:
        mp.chdir(REPO)
        mp.setattr(orch, "_download_chart_js", lambda *a, **k: None)
        mp.setattr(orch, "_download_annotation_plugin", lambda *a, **k: None)
        mp.setattr(contra_mod, "_render_og_cards", lambda *a, **k: 0)
        mp.setattr(og_render, "render_og_images", lambda jobs, root: 0)
        orch.generate_public_site(
            db_path=db_path, output_dir=str(base / "site"),
            only={"pretrunas", "likumi", "bills", "partijas", "saites", "saeima", "politiki",
                  "pozicijas", "personas", "x", "static"},
        )
    out = base / "site" / "atmina"
    _balsojumi(out)
    # Statistikas apakšlapa: iesaldētais momentuzņēmums, ko būvējums kopē uz vietni.
    stat = out / "statistika"
    stat.mkdir(exist_ok=True)
    shutil.copy(REPO / "curated" / "atmina" / "statistika" / "IBE010.html", stat / "IBE010.html")
    shutil.copytree(REPO / "assets", out / "assets", dirs_exist_ok=True)
    handler = functools.partial(_QuietHandler, directory=str(out))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def _open_saites_graph(page):
    # Tīkla bloks atveras ar pogu, kas ielādē D3 (bez tīkla testā) — filtru
    # pogas ir servera HTML, tāpēc pietiek atklāt bloku.
    page.evaluate("document.getElementById('saites-graph-block').hidden = false")


def _open_vote_tracked(page):
    page.locator("details.vote-tracked > summary").first.click()
    page.wait_for_selector(".vote-sort-btn")


def _open_mobile_filters(page, prefix):
    """Telefonā atver filtru paneli («Filtri (n)»); datorā tas jau redzams."""
    toggle = page.locator(f".{prefix}-mobile-toggle")
    if toggle.is_visible():
        toggle.click()
        page.wait_for_selector(f'.{prefix}-grid[data-mobile-filter-open="true"]')


def _pozicijas_filters(page):
    # Divi aktīvi filtri → noņemamie čipi + «Notīrīt visu» (telefonā) un
    # «Notīrīt ✕» meklētāja rindā; personu saraksts atvērts — redzams tā meklētājs.
    page.wait_for_selector(".pzv1-row")
    _open_mobile_filters(page, "pzv1")
    page.locator('.pzv1-rail-row[data-axis="topic"]:not([data-value="visas"])').first.click()
    page.locator('.pzv1-rail-row[data-axis="party"]:not([data-value="Visas"])').first.click()
    page.evaluate("document.getElementById('pzv1-rail-persons').open = true")


def _personas_filters(page):
    # Noklusējumā jau viens čips (15. Saeimā ievēlētie); meklējums pievieno otru
    # un «Notīrīt visus».
    _open_mobile_filters(page, "pnv1")
    page.fill("#pnv1-search", "Testa")
    page.wait_for_selector(".pnv1-clearall")


# (nosaukums, ceļš, gaidāmais selektors, darbība pirms mērīšanas, gaidāmās saimes)
PAGES = [
    ("likumi", "likumi.html", ".likumi-has-bills", None, {"chip", "field", "compact"}),
    ("likumprojekti", "likumprojekti.html", ".bill-status-filter", None,
     {"chip", "field", "compact"}),
    ("balsojumi", "balsojumi.html", ".vote-card", _open_vote_tracked,
     {"chip", "field", "compact"}),
    ("saites", "saites.html", "#saites-search", _open_saites_graph, {"chip", "field"}),
    ("pretrunas", "pretrunas.html", "#severity-chips", None, {"chip", "compact", "seg"}),
    ("pozicijas", "pozicijas.html", ".pzv1-grid", _pozicijas_filters,
     {"chip", "field", "compact"}),
    ("personas", "personas.html", ".pnv1-card", _personas_filters, {"chip", "field"}),
    ("x", "x.html?tema=Bud%C5%BEets%20un%20finanses", ".xv1-item", None, {"chip", "compact"}),
    ("partijas", "partijas.html", ".parties-grid", None, {"chip"}),
    ("politikis", "politiki/testa-politikis.html", ".parskats-topic-chip", None, {"chip"}),
    ("saeima", "saeima.html", ".slv-lenses:not([hidden])", None, {"seg"}),
    ("statistika", "statistika/IBE010.html", ".stat-event-filter", None, {"chip"}),
]


@pytest.fixture(scope="module")
def measured(site):
    with sync_api.sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Exception as exc:  # pragma: no cover — nav instalēta pārlūka
            pytest.skip(f"Chromium nav pieejams: {exc}")
        results = {}
        for theme in ("light", "dark"):
            for width in (1280, 390):
                ctx = browser.new_context(viewport={"width": width, "height": 900},
                                          color_scheme=theme, reduced_motion="reduce")
                ctx.add_init_script(f"localStorage.setItem('atmina:theme', '{theme}')")
                ctx.route("**/*", lambda r: r.abort()
                          if r.request.url.startswith("http") and not r.request.url.startswith(site)
                          else r.continue_())
                page = ctx.new_page()
                page.set_default_timeout(8000)
                for name, path, ready, action, _fam in PAGES:
                    page.goto(f"{site}/{path}", wait_until="domcontentloaded")
                    page.wait_for_selector(ready, state="attached")
                    if action:
                        action(page)
                    # Pele prom no čipiem (citādi :hover vai pusē pārejas) un
                    # krāsu pārejas līdz galam.
                    page.mouse.move(0, 0)
                    page.wait_for_timeout(350)
                    results[(theme, width, name)] = page.evaluate(
                        COLLECT, [CHIP_SEL, FIELD_SEL, SEG_SEL, COMPACT_SEL, TRIGGER_SEL])
                ctx.close()
        browser.close()
    return results


def test_denominators_per_page(measured):
    missing = []
    for (theme, width, name), found in sorted(measured.items()):
        fams = next(p[4] for p in PAGES if p[0] == name)
        counts = {k: len(v) for k, v in found.items()}
        print(f"\n{theme} {width} {name}: čipi {counts['chip']}, lauki {counts['field']},"
              f" kompaktie {counts['compact']}, segmenti {counts['seg']},"
              f" saraksts+čipi rindā {counts['row']}")
        missing += [f"{theme}/{width}/{name}: {f}=0" for f in fams if counts[f] == 0]
    assert not missing, f"fikstūra neko nepārbauda: {missing}"


@pytest.mark.parametrize("family", ["chip", "field", "compact", "seg"])
def test_one_shape_per_family(measured, family):
    bad = []
    for theme in ("light", "dark"):
        for width in (1280, 390):
            shapes = defaultdict(list)
            for (t, w, name), found in measured.items():
                if (t, w) == (theme, width):
                    for el in found[family]:
                        shapes[el["shape"]].append(f"{name}: {el['name']}")
            total = sum(len(v) for v in shapes.values())
            print(f"\n{family} {theme} {width}: {len(shapes)} izskati / {total} elementi")
            for s, who in sorted(shapes.items(), key=lambda x: -len(x[1])):
                print(f"   {len(who):3} × [{s}]  piem. {who[0]}")
            assert total > 0, f"{family} {theme} {width}: saucējs 0"
            if len(shapes) != 1:
                bad.append(f"{theme}/{width}: {len(shapes)} formas")
    assert not bad, f"{family}: vairāk par vienu izskatu — {bad}"


def test_chip_states_read_the_same_everywhere(measured):
    bad = []
    for theme in ("light", "dark"):
        idle_paint = defaultdict(list)
        idle_bg = set()
        active = []
        for (t, _w, name), found in measured.items():
            if t != theme:
                continue
            for el in found["chip"]:
                if el["on"]:
                    active.append((name, el))
                else:
                    idle_paint[el["paint"]].append(f"{name}: {el['name']}")
                    idle_bg.add(el["bg"])
        print(f"\n{theme}: neaktīvo krāsu paraksti {len(idle_paint)}, aktīvie {len(active)}")
        for s, who in idle_paint.items():
            print(f"   {len(who):3} × [{s}]  piem. {who[0]}")
        if len(idle_paint) != 1:
            bad.append(f"{theme}: {len(idle_paint)} neaktīvo krāsu paraksti")
        flat = [f"{n}: {e['name']}" for n, e in active if e["bg"] in idle_bg]
        if flat:
            bad.append(f"{theme}: aktīvais fons = neaktīvais: {flat[:4]}")
        assert active, f"{theme}: neviena aktīva čipa — saucējs 0"
    assert not bad, bad


def test_compact_controls_are_chip_height(measured):
    """Kompaktā saime (sānjoslas meklētājs, X un rīkjoslu nolaižamie saraksti) ir
    tieši čipa augstumā — citādi tā ir trešā izmēra pakāpe starp 32 un 44 px."""
    bad = []
    for theme in ("light", "dark"):
        for width in (1280, 390):
            comp_h = {round(el["h"]) for (t, w, _n), f in measured.items() if (t, w) == (theme, width)
                      for el in f["compact"]}
            chips = {float(el["shape"].split()[1][:-2]) for (t, w, _n), f in measured.items()
                     if (t, w) == (theme, width) for el in f["chip"]}
            print(f"\n{theme} {width}: kompakto augstumi {sorted(comp_h)}, čipu {sorted(chips)}")
            assert comp_h and chips, f"{theme} {width}: saucējs 0"
            if comp_h != {round(c) for c in chips}:
                bad.append(f"{theme}/{width}: kompaktie {sorted(comp_h)} ≠ čipi {sorted(chips)}")
    assert not bad, bad


def test_dropdown_in_a_chip_row_is_chip_height(measured):
    """Ko lasītājs redz: nolaižamā saraksta poga vienā rindā ar čipiem ir tikpat
    augsta kā tie (pretrunas, likumprojekti, balsojumi, X)."""
    bad, total = [], 0
    for (theme, width, name), found in sorted(measured.items()):
        for row in found["row"]:
            total += 1
            print(f"\n{theme} {width} {name}: {row['name']} {row['h']:.0f} px,"
                  f" čipi rindā {sorted({round(c) for c in row['chips']})}")
            if any(abs(row["h"] - c) > 0.5 for c in row["chips"]):
                bad.append(f"{theme}/{width}/{name}: {row['name']} {row['h']:.0f} px"
                           f" pret čipiem {sorted({round(c) for c in row['chips']})}")
    print(f"\nnolaižamie saraksti rindā ar čipiem: {total}")
    assert total >= 8, f"tikai {total} saraksti rindā ar čipiem — fikstūra neko nepārbauda"
    assert not bad, bad
