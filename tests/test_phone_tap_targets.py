"""Telefonā (390 px) atsevišķās saites un pogas ir ≥ 44 px pieskāriena mērķi;
partiju un mediju kartītes ir īstas saites (good-css 5. kārta, 4. uzdevums:
A11/B9, A12, D7; 2026-10-21).

Kļūmes, ko šis fails ķer (audits ``docs/audits/2026-10-21-good-css-5/``):

- A12 — pirksts netrāpa saitēm, kas vizuāli 14–40 px augstas: balsojumi
  998/1 005 mērķu, X 4 595/4 595, personas 484/590, partijas biedri 134/140,
  pozīcijas/programma/spriedzes «Avots ↗» 17–26 px, rakstu atpakaļsaites
  18 px. D7 — sākumlapas meta saites (24 px) telefonā 44 px, bet izskats
  nemainās (neredzama ``::after`` zona).
- Pārklāšanās: paplašinātā zona nedrīkst nozagt blakus mērķa centru —
  ``elementFromPoint(centrs)`` katram mērķim jātrāpa tieši tajā.
- A11 — partiju (19) un mediju (11) kartītes bija ``div`` + JS klikšķis:
  ar tastatūru nesasniedzamas. Tagad virsraksts ir ``<a>``, kura ``::after``
  pārklāj kartīti; iekšējās saites (X, mājaslapa) paliek klikšķināmas.

Pārlūkā (Playwright, Chromium) pret veidnēm, kas renderētas ar sintētisku
kontekstu vai īsto renderētāju, ar īstajiem ``assets/*``. Katrs gadījums
izdrukā «mazie/saucējs» — saucējs 0 nozīmē, ka fikstūra neko nepārbauda.
Paraugs: ``tests/test_profile_tabs_mobile.py`` (TAP_TARGETS).
"""
from __future__ import annotations

import functools
import json
import shutil
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from src.db import get_db, init_db
from src.saeima.schema import init_saeima_tables

sync_api = pytest.importorskip("playwright.sync_api")

REPO = Path(__file__).resolve().parent.parent


class _Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


# ── Fikstūras lapas ───────────────────────────────────────────────────────


def _tpl_env():
    from tests.test_lapu_kludas_css5 import _env
    env = _env()
    env.filters["lv_plural"] = lambda n, one, many=None, *a, **k: one if n == 1 else (many or one)
    return env


def _write(path: Path, html: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


def _parties(out: Path, base: Path) -> None:
    """partijas.html + partijas/<slug>.html caur īsto renderētāju (Enter vajag mērķi)."""
    from src.render.parties import _fetch_parties_page, render_parties
    from tests.test_render_parties_slug import _env

    db_path = str(base / "p.db")
    init_db(db_path)
    init_saeima_tables(db_path)
    db = get_db(db_path)
    db.executescript("""
        INSERT INTO parties (id, name, short_name, coalition_status, x_handle, website) VALUES
          (1, 'Jaunā Vienotība', 'JV', 'coalition', 'jaunavienotiba', 'https://vienotiba.lv'),
          (2, 'Suverēnā vara/Jaunlatvieši', 'SV/AJ', 'opposition', NULL, NULL);
    """)
    db.commit()
    render_parties(_env(), db, out, _fetch_parties_page(db))
    db.close()


def _party_detail(out: Path) -> None:
    """Partijas lapa ar visām cilnēm un biedru pēdējo aktivitāti."""
    act = {"display": "10-20 17:13", "href": "politiki/anna-kalna.html", "icon": "✎",
           "label": "Pozīcija par budžetu", "source_url": "https://example.lv/s"}
    members = [{"id": i, "name": n, "slug": s, "role": "Deputāte", "x_handle": h,
                "has_photo": False, "claims_count": 3, "contradictions_count": 0,
                "votes_count": 3, "last_activity": act, "party_color": "#2a6"}
               for i, (n, s, h) in enumerate([("Anna Kalna", "anna-kalna", "anna_k"),
                                               ("Bruno Liepa", "bruno-liepa", None)], 1)]
    claim = {"slug": "anna-kalna", "politician_name": "Anna Kalna", "topic": "Ekonomika",
             "stated_at": "2026-10-01", "stance": "Pozīcija.", "source_url": "https://example.lv/a"}
    ctx = {
        "party": {"id": 1, "name": "Jaunā Vienotība", "short_name": "JV", "color": "#2a6",
                  "coalition_status": "coalition", "x_handle": "jaunavienotiba",
                  "website": "https://vienotiba.lv"},
        "last_news": {"url": "https://example.lv/n", "politician": "Anna Kalna",
                      "title": "Ziņa", "title_full": "Ziņa", "date": "2026-10-20"},
        "last_x": {"url": "https://x.com/a/1", "politician": "Anna Kalna",
                   "title": "Ieraksts", "title_full": "Ieraksts", "date": "2026-10-20"},
        "members": members,
        "claims": [claim, dict(claim, topic="Budžets")], "claims_count": 2,
        "program_by_topic": [{"topic": "Ekonomika", "promises": [
            {"stance": "Solījums.", "source_url": "https://example.lv/p"}]}],
        "program_count": 1,
        "votes": [],
        "tensions": [{"badge": "badge-red", "type_label": "Kritika", "lv_date": "2026-10-01",
                      "source_name": "Anna Kalna", "target_name": "Bruno Liepa",
                      "topic": "Ekonomika", "description": "Apraksts.",
                      "source_url": "https://example.lv/t", "target_url": "https://example.lv/u"}],
        "knab_summary": None,
    }
    _write(out / "partijas" / "tap.html",
           _tpl_env().get_template("partija.html.j2").render(**ctx))


def _mediji(out: Path) -> None:
    outlets = [{"slug": s, "name": n, "type_label": "Sabiedriskais", "language": "lv",
                "website": f"https://{s}.lv", "volume_phrase": "1 874 raksti",
                "top_party": "JV", "top_party_color": "#2a6"} for s, n in [("lsm", "LSM"), ("nra", "NRA")]]
    _write(out / "mediji.html", _tpl_env().get_template("mediji.html.j2").render(
        outlets=outlets, metrics={"total": 2, "total_articles": 3748}))
    for s in ("lsm", "nra"):
        _write(out / "mediji" / f"{s}.html", "<!doctype html><title>medijs</title>")


def _personas(out: Path) -> None:
    act = {"href": "politiki/a.html", "label": "Pozīcija", "display": "10-20 20:07",
           "icon": "✎", "source_url": "https://example.lv/s"}
    personas = [{"slug": f"p{i}", "name": f"Persona {i}", "sort_name": f"Persona {i}",
                 "has_photo": False, "category": "Deputāti", "party": "Jaunā Vienotība",
                 "party_short": "JV", "saeima15": "ieveleti", "role": "Deputāts",
                 "party_color": "#2a6", "coalition_status": "coalition",
                 "last_activity_iso": "2026-10-20", "claims_count": c, "votes_count": c,
                 "contradictions_count": c, "docs_count": 5,
                 "x_handle": "persona_x" if c else None, "last_activity": act}
                for i, c in enumerate([4, 0, 2], 1)]
    _write(out / "personas.html", _tpl_env().get_template("personas.html.j2").render(
        personas=personas, metrics={"total": 3, "deputies": 3, "with_contradictions": 2,
                                    "coalition": 3, "opposition": 0},
        category_counts={"Deputāti": 3}, parties_with_counts=[("Jaunā Vienotība", "JV", "#2a6", 3)],
        saeima15_counts={"ieveleti": 3, "jauni": 0}))


def _x(out: Path, base: Path) -> None:
    from src.render._orchestrator import _party_short_name
    from src.render.x import render_x
    from tests.test_balsojumi_client_render import _env
    from tests.test_saraksti_mobile import _seed

    db = _seed(str(base / "x.db"))
    db.execute("UPDATE documents SET content = content || ' #Budžets' WHERE id = 10")
    db.execute("INSERT INTO claims (opponent_id, document_id, topic, stance, source_url,"
               " stated_at, claim_type) VALUES (1, 10, 'Budžets un finanses', 'Atbalsta.',"
               " 'https://x.com/anna_abele/status/10', '2026-10-20', 'position')")
    db.commit()
    env = _env()
    env.globals["_party_short_name"] = _party_short_name
    render_x(env, db, out)
    db.close()


def _balsojumi(out: Path) -> None:
    from tests.test_balsojumi_client_render import _MINIMAL_CTX, _env
    from tests.test_balsojumi_readability import _FIXTURE

    _write(out / "balsojumi.html", _env().get_template("balsojumi.html.j2").render(
        **dict(_MINIMAL_CTX, metrics=dict(_MINIMAL_CTX["metrics"], total=7))))
    data = json.loads(json.dumps(_FIXTURE))
    for v in data["votes"]:
        v["url"] = f"https://titania.saeima.lv/v/{v['vid']}"
    for name in ("balsojumi-matrica.json", "balsojumi-matrica-recent.json"):
        _write(out / "data" / name, json.dumps(data, ensure_ascii=False))


def _blog(out: Path) -> None:
    from tests.test_blog_brief_presentation import _daily_post, _template_env

    env = _template_env()
    env.filters.setdefault("safe_url", lambda u: u or "")
    _write(out / "blog" / "2026-08-14.html", env.get_template("blog-post.html.j2").render(
        post=_daily_post(), content="<p>Saturs.</p>",
        prev_post={"slug": "2026-08-13", "date": "2026-08-13"},
        next_post={"slug": "2026-08-15", "date": "2026-08-15"}))
    # Gara analīze ar «Saturs» (vad-2026 — 10 h2): rindas cieši viena zem otras,
    # tāpēc `::after` zona pārklātos — vajag īstu augstumu (final-review I3).
    titles = ["Kopsavilkums", "Metode", "Kas ir VAD un kāpēc tās svarīgas",
              "Amatpersonas, kuru deklarācijās ir neatbilstības starp gadiem", "Dati",
              "Partiju salīdzinājums", "Ierobežojumi", "Ko darīt tālāk", "Avoti", "Pielikums"]
    toc = [{"id": f"h{i}", "title": t} for i, t in enumerate(titles)]
    body = "".join(f'<h2 id="h{i}">{t}</h2><p>Teksts.</p>' for i, t in enumerate(titles))
    _write(out / "blog" / "analize.html", env.get_template("blog-post.html.j2").render(
        post=_daily_post(), content_html=body, toc=toc, prev_post=None, next_post=None))


def _index(out: Path) -> None:
    from tests.test_index_focus_layout import CONTRA, QUOTE, TENSION, _focus, _render

    _write(out / "index.html", _render(_focus(
        {"kind": "contradiction", "item": CONTRA},
        [{"kind": "tension", "item": TENSION}, {"kind": "tension", "item": dict(TENSION)},
         {"kind": "quote", "item": QUOTE}])))


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    base = tmp_path_factory.mktemp("tap")
    out = base / "site"
    out.mkdir()
    for build in (_parties, _x):
        build(out, base)
    for build in (_party_detail, _mediji, _personas, _balsojumi, _blog, _index):
        build(out)
    shutil.copytree(REPO / "assets", out / "assets", dirs_exist_ok=True)
    # Lapas apakšmapēs (partijas/, blog/) atsaucas uz ../assets — jau ir.
    server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Quiet, directory=str(out)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}", out
    server.shutdown()


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as pw:
        try:
            b = pw.chromium.launch()
        except Exception as exc:  # pragma: no cover — nav instalēta pārlūka
            pytest.skip(f"Chromium nav pieejams: {exc}")
        yield b
        b.close()


# ── Mērījums ──────────────────────────────────────────────────────────────

# Katram redzamam mērķim — EFEKTĪVAIS pieskāriena augstums: no centra uz augšu
# un leju ik pa 0,5 px, kamēr `elementFromPoint` vēl trāpa šajā mērķī. Tas
# ieskaita `::after` zonu UN visu, kas to samazina: vecāka `overflow`/
# `content-visibility` apgriezumu, blakus mērķa zonu virsū. `own` — vai mērķa
# vizuālais centrs vispār trāpa tajā (nav pilnībā nosegts).
MEASURE = r"""(sel) => [...document.querySelectorAll(sel)].filter(e => {
    const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0;
  }).map(e => {
    e.scrollIntoView({block: 'center', inline: 'nearest', behavior: 'instant'});
    const r = e.getBoundingClientRect();
    const x = r.left + r.width / 2, cy = r.top + r.height / 2;
    const mine = y => { const h = document.elementFromPoint(x, y); return !!h && (h === e || e.contains(h)); };
    let up = 0, down = 0;
    while (up < 120 && mine(cy - (up + 1) / 2)) up++;
    while (down < 120 && mine(cy + (down + 1) / 2)) down++;
    const name = (typeof e.className === 'string' && e.className ? e.className.split(' ')[0]
                  : e.tagName.toLowerCase()) + ' «' + e.textContent.trim().slice(0, 18) + '»';
    return {name, h: Math.round((up + down + 1) / 2), own: mine(cy)};
  })"""

# (lapa, cilne vai None, gaidāmais selektors pirms mērīšanas, mērķu selektori, min. saucējs)
CASES = [
    ("balsojumi", "balsojumi.html", None, ".vote-card .vote-who",
     ".vote-links a, .vote-who", 20),
    ("x", "x.html", None, ".xv1-item",
     ".xv1-item-at, .xv1-item-party, .xv1-item-topic, .xv1-item-link, .xv1-tab", 9),
    ("personas", "personas.html", None, ".pnv1-card",
     "a.pnv1-card-stat, a.pnv1-card-x, .pnv1-card-activity, .pnv1-card-source,"
     " .pnv1-search-input", 14),
    ("partijas", "partijas.html", None, ".party-card",
     ".party-card-link, .party-card-social a, .filter-btn", 8),
    ("mediji", "mediji.html", None, ".party-card", ".party-card-link", 2),
    ("partija-biedri", "partijas/tap.html", "biedri", ".politician-card",
     ".back-link, .profile-links a, .party-activity-item, .politician-card-name,"
     " .x-icon-link, .activity-label, .activity-source", 12),
    ("partija-pozicijas", "partijas/tap.html", "pozicijas", "#tab-pozicijas .card",
     "#tab-pozicijas a", 4),
    ("partija-programma", "partijas/tap.html", "programma", "#tab-programma .card",
     "#tab-programma a", 1),
    ("partija-spriedzes", "partijas/tap.html", "spriedzes", "#tab-spriedzes .card",
     "#tab-spriedzes a", 2),
    ("raksts", "blog/2026-08-14.html", None, ".brief-back",
     ".brief-back, .brief-footnav-link", 4),
    ("saturs", "blog/analize.html", ".post-toc-head", ".post-toc",
     ".post-toc-head, .post-toc-list a", 11),
    ("sakumlapa", "index.html", None, ".focus-grid",
     ".focus-quote-who a, .focus-quote-meta a, .focus-duel-name, .focus-duel-meta a,"
     " .prv2-pane-meta a", 12),
]


@pytest.mark.parametrize("case", CASES, ids=[c[0] for c in CASES])
def test_phone_tap_targets_are_44px_and_do_not_overlap(site, browser, case):
    name, path, tab, ready, selector, min_total = case
    base, _ = site
    ctx = browser.new_context(viewport={"width": 390, "height": 800}, reduced_motion="reduce")
    ctx.route("**/*", lambda r: r.abort()
              if r.request.url.startswith("http") and not r.request.url.startswith(base)
              else r.continue_())
    page = ctx.new_page()
    page.set_default_timeout(8000)
    page.goto(f"{base}/{path}", wait_until="domcontentloaded")
    if tab:
        # Cilne (`data-tab`) vai izvēršama rinda (selektors, piem. «Saturs»).
        page.click(tab if tab[0] in ".#" else f'[data-tab="{tab}"]')
    page.wait_for_selector(ready)
    page.evaluate("document.fonts.ready.then(() => true)")
    found = page.evaluate(MEASURE, selector)
    ctx.close()
    small = [(t["name"], t["h"]) for t in found if t["h"] < 44]
    stolen = [t["name"] for t in found if not t["own"]]
    low = min((t["h"] for t in found), default=0)
    print(f"\n{name}: <44 px {len(small)}/{len(found)}; centrs nozagts "
          f"{len(stolen)}/{len(found)}; mazākais efektīvais {low} px")
    assert len(found) >= min_total, f"{name}: atrasti {len(found)} mērķi — fikstūra nepilna"
    assert not small, f"{name}: pieskāriena mērķi < 44 px: {small}"
    assert not stolen, f"{name}: blakus zona pārklāj mērķa centru: {stolen}"


# ── Kartīte-saite (A11) ───────────────────────────────────────────────────

CARD_STATE = r"""() => {
  const a = document.activeElement;
  const card = a && a.closest('.party-card');
  return {cls: a ? a.className : '', href: a ? a.getAttribute('href') : '',
          ring: card ? parseFloat(getComputedStyle(card).outlineWidth) : 0,
          ringStyle: card ? getComputedStyle(card).outlineStyle : ''};
}"""


def test_party_card_is_a_keyboard_link_and_inner_links_still_click(site, browser):
    base, out = site
    html = (out / "partijas.html").read_text(encoding="utf-8")
    assert "data-card-href" not in html
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.set_default_timeout(8000)
    page.goto(f"{base}/partijas.html")
    # Tab līdz pirmajai kartītes saitei (lapas sākumā — nav, filtri, sintēzes kartīte).
    state = {}
    for _ in range(60):
        page.keyboard.press("Tab")
        state = page.evaluate(CARD_STATE)
        if "party-card-link" in state["cls"]:
            break
    assert "party-card-link" in state["cls"], f"Tab nesasniedza kartītes saiti: {state}"
    assert state["ring"] >= 2 and state["ringStyle"] != "none", f"fokuss kartītē nav redzams: {state}"
    target = state["href"]
    assert (out / target).exists(), f"saites mērķis neeksistē: {target}"

    # Iekšējā X saite joprojām virs kartītes pārklājuma: tās centrs trāpa tajā.
    inner = page.evaluate("""() => { const a = document.querySelector('.party-card-social a');
        a.scrollIntoView({block: 'center', behavior: 'instant'}); const r = a.getBoundingClientRect();
        const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
        return !!hit && (hit === a || a.contains(hit)); }""")
    assert inner, "kartītes pārklājums nosedz iekšējo saiti"

    page.keyboard.press("Enter")
    page.wait_for_url(f"**/{target}")
    page.close()


def test_mediji_card_is_a_link(site, browser):
    base, out = site
    assert "data-card-href" not in (out / "mediji.html").read_text(encoding="utf-8")
    page = browser.new_page(viewport={"width": 390, "height": 800})
    page.set_default_timeout(8000)
    page.goto(f"{base}/mediji.html")
    # Klikšķis kartītes apakšā (ne virsrakstā) atver medija lapu bez JS apstrādātāja.
    box = page.locator(".party-card").first.bounding_box()
    page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] - 8)
    page.wait_for_url("**/mediji/lsm.html")
    page.close()
