"""Izvēršana: pārlūka trijstūri un gadu taisnstūri nedrīkst atgriezties.

Īstais renderētājs, astoņas lapas, sintētiska DB (produkcijas DB nelasa).
Katrs summary, arī slēptajās profila cilnēs: kopīgs bultiņas paraksts abos
stāvokļos, nav otra marķiera, 44 px telefonā. Gadi = čipi, ritināma rinda.
DISCLOSURE_TEST_CSS ļauj pierādīt kļūmi ar veco CSS, nemainot darba koku.
"""
from __future__ import annotations

import functools
import os
import shutil
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

sync_api = pytest.importorskip("playwright.sync_api")
REPO = Path(__file__).resolve().parent.parent
PAGES = (
    "politiki/agnese-krasta.html", "blog/2026-10-22.html", "likumprojekti.html",
    "saites.html", "about.html", "analizes/kanans-visvanats-nopelni-2023.html",
    "kontakti.html", "statistika/IBE010.html",
)
EXPECTED = {
    "profile-bio-more", "pp-chart-table", "pp-quote", "vad-year-more", "vad-section",
    "brief-topic-details", "lpv1-laws", "saites-party", "classless", "post-more",
    "claim-card", "post-toc-box", "stat-data-table-wrap",
}


@pytest.fixture(scope="module")
def disclosure_site(tmp_path_factory):
    import src.render._orchestrator as orch
    from src.db import get_db
    from src.render._common import og_render
    from src.vad.schema import init_vad_tables
    from tests.test_multiselect_dropdown import _QuietHandler
    from tests.test_ui_basics_one_look import _seed
    from tests.test_vad_render import _insert_declaration

    base = tmp_path_factory.mktemp("disclosures")
    db_path = str(base / "fixture.db")
    _seed(db_path)
    init_vad_tables(db_path)
    db = get_db(db_path)
    # Šis ir sintētisks UI paraugs, ne apgalvojumi par īsto personu.
    db.execute("UPDATE tracked_politicians SET name='Agnese Krasta' WHERE id=1")
    db.execute("UPDATE claims SET quote='Sintētisks testa citāts.'")
    for number in (1289, 1290):
        db.execute("INSERT INTO saeima_bills(document_nr, bill_type, title, current_stage)"
                   " VALUES (?, 'Lp14', 'Grozījums Saeimas vēlēšanu likumā', '1.lasījums')",
                   (f"{number}/Lp14",))
    for year in range(2018, 2026):
        decl = _insert_declaration(db, 1, year, f"ui-{year}", submitted=f"{year+1}-03-27")
        db.execute("INSERT INTO vad_positions(declaration_id, position_title, entity_name)"
                   " VALUES (?, 'Deputāte', 'Testa iestāde')", (decl,))
        db.execute("INSERT INTO vad_income(declaration_id, source, income_type, amount, currency)"
                   " VALUES (?, 'Testa iestāde', 'Alga', 1000, 'EUR')", (decl,))
    db.execute("INSERT INTO context_notes(topic, note_type, content, created_at) VALUES"
               " ('2026-10-22', 'daily_brief', ?, '2026-10-22 17:00:00')", (
                   "# Dienas pārskats — 2026-10-22\n\n## Galvenās tēmas\n\n"
                   "### Budžets un finanses\n\n| Politiķis | Pozīcija |\n| --- | --- |\n"
                   "| Testa persona | Testa pozīcija |\n",))
    db.commit()
    db.close()
    with pytest.MonkeyPatch.context() as mp:
        mp.chdir(REPO)
        mp.setattr(orch, "_download_chart_js", lambda *a, **k: None)
        mp.setattr(orch, "_download_annotation_plugin", lambda *a, **k: None)
        mp.setattr(og_render, "render_og_images", lambda jobs, root: 0)
        orch.generate_public_site(db_path=db_path, output_dir=str(base / "site"),
                                  only={"politiki", "blog", "bills", "saites", "static", "analizes"})
    out = base / "site" / "atmina"
    (out / "statistika").mkdir(exist_ok=True)
    shutil.copyfile(REPO / "curated/atmina/statistika/IBE010.html", out / "statistika/IBE010.html")
    shutil.copytree(REPO / "assets", out / "assets", dirs_exist_ok=True)
    if css := os.environ.get("DISCLOSURE_TEST_CSS"):
        shutil.copyfile(css, out / "assets/style.css")
    server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_QuietHandler, directory=str(out)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


COLLECT = r"""(opened) => {
  const shape = (s, props) => props.map(p => s[p]).join('|');
  const chevron = ['inlineSize', 'blockSize', 'borderInlineEndWidth', 'borderInlineEndStyle',
    'borderInlineEndColor', 'borderBlockEndWidth', 'borderBlockEndStyle', 'borderBlockEndColor',
    'rotate', 'translate'];
  const result = [];
  // Mēra katru īsto kontroles elementu arī paneļos, kuri sākumā slēpti.
  for (const s of document.querySelectorAll('summary, .profile-bio-trigger')) {
    for (let p = s.parentElement; p; p = p.parentElement) {
      if (p.matches('details')) { p.removeAttribute('name'); p.open = true; }
      if (p.hidden) p.hidden = false;
      if (getComputedStyle(p).display === 'none') p.style.display = 'block';
    }
    const popover = s.matches('.profile-bio-trigger');
    const d = popover ? document.getElementById(s.getAttribute('popovertarget')) : s.parentElement;
    if (popover) {
      if (opened) d.showPopover({source: s});
      else d.hidePopover();
    } else d.open = opened;
    const cs = getComputedStyle(s), after = getComputedStyle(s, '::after');
    const before = getComputedStyle(s, '::before'), content = popover ? getComputedStyle(d) : getComputedStyle(d, '::details-content');
    const desktopToc = d.matches('.post-toc-box') && innerWidth > 600;
    result.push({family: d.classList[0] || 'classless',
      marker: cs.listStyleType, before: before.content,
      chevron: shape(after, chevron), content: after.content, display: after.display,
      height: s.getBoundingClientRect().height, desktopToc,
      collapsed: popover ? !d.matches(':popover-open') : content.blockSize === '0px', transition: content.transitionDuration});
  }
  return result;
}"""
CHIPS = r"""() => {
  const props = ['borderRadius', 'minBlockSize', 'height', 'fontSize', 'fontWeight',
    'paddingInlineStart', 'paddingBlockStart', 'borderTopWidth', 'color', 'backgroundColor', 'borderTopColor'];
  const shape = e => { const s = getComputedStyle(e); return props.map(p => s[p]).join('|'); };
  const rows = [...document.querySelectorAll('.vad-year-tabs')];
  const chips = [...document.querySelectorAll('.vad-year-tab')];
  const ref = document.createElement('button');
  ref.style.transition = 'none';
  ref.className = 'chip'; ref.textContent = '2025'; rows[0].after(ref);
  const idle = shape(ref); ref.classList.add('active'); const active = shape(ref); ref.remove();
  return {idle, active, chips: chips.map(e => ({shape: shape(e), active: e.classList.contains('active')})),
    rows: rows.map(r => ({wrap: getComputedStyle(r).flexWrap, overflow: getComputedStyle(r).overflowX,
      tops: [...r.children].map(e => Math.round(e.getBoundingClientRect().top)),
      scroll: r.scrollWidth, width: r.clientWidth}))};
}"""


def test_disclosures_and_declaration_years_share_one_look(disclosure_site):
    bad, total = [], 0
    with sync_api.sync_playwright() as pw:
        browser = pw.chromium.launch()
        for theme in ("light", "dark"):
            for width in (390, 1280):
                ctx = browser.new_context(viewport={"width": width, "height": 900},
                                          color_scheme=theme, reduced_motion="reduce")
                ctx.route("**/*", lambda r: r.continue_() if r.request.url.startswith(disclosure_site)
                          else r.abort())
                page = ctx.new_page()
                families, signatures = set(), {False: set(), True: set()}
                for path in PAGES:
                    page.goto(f"{disclosure_site}/{path}")
                    page.evaluate("t => document.documentElement.setAttribute('data-theme', t)", theme)
                    assert page.locator("summary").count(), f"{path}: saucējs 0"
                    for opened in (False, True):
                        found = page.evaluate(COLLECT, opened)
                        total += len(found)
                        for item in found:
                            family = item["family"]
                            families.add(family)
                            if item["marker"] != "none" or item["before"] not in ("none", "normal"):
                                bad.append(f"{path}/{family}: marķieris {item['marker']}, pirms {item['before']}")
                            if item["desktopToc"]:
                                if item["display"] != "none" or item["collapsed"]:
                                    bad.append("datora satura rādītājs nav pastāvīgi redzams bez bultiņas")
                                continue
                            signatures[opened].add(item["chevron"])
                            if item["content"] != '\"\"' or item["display"] == "none":
                                bad.append(f"{path}/{family}: nav bultiņas")
                            geometry = item["chevron"].split("|")
                            if (not geometry[0].endswith("px") or float(geometry[0][:-2]) <= 0
                                    or geometry[2:4] != ["2px", "solid"]
                                    or geometry[5:7] != ["2px", "solid"]):
                                bad.append(f"{path}/{family}: bultiņai nav redzamu malu")
                            if width == 390 and item["height"] < 44:
                                bad.append(f"{path}/{family}: {item['height']} px < 44 px")
                            if not opened and not item["collapsed"]:
                                bad.append(f"{path}/{family}: saturs nav aizvērts")
                            assert item["transition"] == "0s", "reduce režīmā saturs animējas"
                    if path.startswith("politiki/"):
                        chips = page.evaluate(CHIPS)
                        assert len(chips["chips"]) == 8
                        for chip in chips["chips"]:
                            if chip["shape"] != chips["active" if chip["active"] else "idle"]:
                                bad.append(f"{theme}/{width}: gada poga {chip['shape']} ≠ čips "
                                           f"{chips['active' if chip['active'] else 'idle']}")
                        if width == 390:
                            assert chips["rows"][0]["scroll"] > chips["rows"][0]["width"]
                            for row in chips["rows"]:
                                if row["wrap"] != "nowrap" or row["overflow"] != "auto" or len(set(row["tops"])) != 1:
                                    bad.append("gadu čipi nav vienā ritināmā rindā")
                        # Saglabātais JS āķis pārslēdz arī agrāko deklarāciju.
                        last = page.locator(".vad-year-tab").last
                        decl_id = last.get_attribute("data-decl-id")
                        last.click()
                        assert "active" in last.get_attribute("class")
                        assert page.locator(f"#vad-decl-{decl_id}").is_visible()
                print(f"\n{theme}/{width}: {len(families)} saimes; bultiņu paraksti "
                      f"{len(signatures[False])}/{len(signatures[True])}")
                assert EXPECTED <= families, f"nav pārbaudītas: {EXPECTED - families}"
                if any(len(values) != 1 for values in signatures.values()):
                    bad.append(f"{theme}/{width}: atšķirīgas bultiņas {signatures}")
                assert signatures[False] != signatures[True], "bultiņa neatspoguļo atvēršanu"
                ctx.close()
        browser.close()
    print(f"\nPārbaudīti {total} summary stāvokļi")
    assert not bad, "\n".join(sorted(set(bad)))
