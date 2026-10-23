"""Saraksta lapas ar filtriem — X plūsmas platums un tukšais stāvoklis
(good-css 5. kārta A4, A9; 2026-10-21).

Kļūme 1 (X, A4): garš tēmturis («#JaEsiPretStambulasKonvencijuTadPutinists»)
ar `white-space: pre-wrap` izstiepa `1fr` kolonnu — `.xv1-main` 358 → 427 px,
un VISA plūsma labajā malā nogriezās (`html { overflow-x: clip }` slēpj
ritjoslu, tāpēc `scrollWidth` vien defektu neredz — mēra `.xv1-main` malu).

Kļūme 2 (A9): filtrs bez rezultātiem rādīja tukšu lapu līdz kājenei un
galvenē palika kopskaits. Tagad: «Nekas neatbilst izvēlētajiem filtriem.» +
skaitītājs «Rāda N no M …». Spriedzēm tas pats pārbaudīts
tests/test_spriedzes_url_filters.py (tur jau ir Playwright fikstūra).

Audits: docs/audits/2026-10-21-good-css-5/saraksti.md § X 1, § Ziņas 1.
"""
import functools
import shutil
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest

from src.db import get_db, init_db
from src.render._orchestrator import _party_short_name
from src.render.news import render_news
from src.render.x import render_x
from src.saeima.schema import init_saeima_tables
from tests.test_balsojumi_client_render import _env

sync_api = pytest.importorskip("playwright.sync_api")

LONG_TAG = "#" + "JaEsiPretStambulasKonvencijuTadPutinists" * 2   # 81 zīme bez atstarpes


class _Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def _seed(path):
    init_db(path)
    init_saeima_tables(path)
    db = get_db(path)
    db.executescript(f"""
        INSERT INTO tracked_politicians (id, name, party, relationship_type) VALUES
          (1, 'Anna Ābele', 'Jaunā Vienotība', 'tracked'),
          (2, 'Bruno Bērziņš', 'Nacionālā apvienība', 'tracked');
        INSERT INTO social_accounts (opponent_id, platform, handle, feed_type, active) VALUES
          (1, 'twitter', 'anna_abele', 'first_party', 1);
        INSERT INTO documents (id, content, content_hash, platform, source_domain, source_url,
                               scraped_at, published_at, title, word_count, language) VALUES
          (10, 'Īss ieraksts.', 'h10', 'twitter', 'x.com', 'https://x.com/anna_abele/status/10',
           '2026-10-20', '2026-10-20T09:00:00', NULL, 2, 'lv'),
          (11, 'Garš tēmturis: {LONG_TAG} un vēl teksts.', 'h11', 'twitter', 'x.com',
           'https://x.com/anna_abele/status/11', '2026-10-20', '2026-10-20T08:00:00', NULL, 6, 'lv'),
          (20, 'saturs', 'h20', 'web', 'lsm.lv', 'https://lsm.lv/a', '2026-10-19', '2026-10-19',
           'Pirmā ziņa', 100, 'lv'),
          (21, 'saturs', 'h21', 'web', 'nra.lv', 'https://nra.lv/b', '2026-10-18', '2026-10-18',
           'Otrā ziņa', 100, 'lv');
        INSERT INTO document_politicians (document_id, politician_id, role) VALUES
          (10, 1, 'subject'), (11, 1, 'subject'), (20, 1, 'subject'), (21, 2, 'subject');
    """)
    db.commit()
    return db


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    base = tmp_path_factory.mktemp("saraksti")
    out = base / "site"
    out.mkdir()
    db = _seed(str(base / "s.db"))
    env = _env()
    env.globals["_party_short_name"] = _party_short_name
    try:
        render_x(env, db, out)
        render_news(env, db, out)
    finally:
        db.close()
    shutil.copytree("assets", out / "assets", dirs_exist_ok=True)
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


def test_x_long_hashtag_does_not_widen_feed(site, browser):
    base, out = site
    assert LONG_TAG in (out / "x.html").read_text(encoding="utf-8")
    page = browser.new_page(viewport={"width": 390, "height": 800})
    page.goto(f"{base}/x.html")
    item = page.locator(".xv1-item", has_text="Garš tēmturis")
    item.scroll_into_view_if_needed()       # content-visibility: auto → izklājas tikai skatā
    page.wait_for_timeout(100)
    g = page.evaluate("""() => ({
      grid: getComputedStyle(document.querySelector('.xv1-grid')).display,
      main: document.querySelector('.xv1-main').getBoundingClientRect().right,
      text: Math.max(...[...document.querySelectorAll('.xv1-item-text')]
                       .map(e => e.getBoundingClientRect().right)),
      // vārds, kas neietilpst savā kastē (pārplūst pāri tās malai)
      spill: Math.max(...[...document.querySelectorAll('.xv1-item-text')]
                        .map(e => e.scrollWidth - e.clientWidth)),
      sw: document.documentElement.scrollWidth, vw: window.innerWidth})""")
    page.close()
    assert g["grid"] == "grid", f"stili nav ielādēti: {g}"
    assert g["main"] <= g["vw"] + 0.5, f"plūsma platāka par ekrānu: {g}"
    assert g["text"] <= g["vw"] + 0.5, f"ieraksta teksts aiz ekrāna malas: {g}"
    assert g["sw"] <= g["vw"], f"lapai horizontāla pārplūde: {g}"
    assert g["spill"] <= 0, f"garais tēmturis pārplūst pāri ieraksta malai: {g}"


def _count_and_empty(page, count_id, empty_id):
    return page.evaluate(
        "([c, e]) => ({count: document.getElementById(c).textContent.trim(),"
        " emptyShown: !document.getElementById(e).hidden"
        " && document.getElementById(e).offsetParent !== null})",
        [count_id, empty_id])


def test_x_filter_without_results_shows_message_and_count(site, browser):
    base, out = site
    html = (out / "x.html").read_text(encoding="utf-8")
    assert "Filtrēt pēc" not in html   # A10
    # Bez JS skaitītājs nav tukšs: serveris jau ieraksta sākuma tekstu (visi redzami).
    assert ('id="xv1-count" role="status" aria-live="polite">'
            "Rāda 2 no 2 jaunākajiem ierakstiem un pieminējumiem.</p>") in html
    page = browser.new_page()
    page.goto(f"{base}/x.html")
    assert _count_and_empty(page, "xv1-count", "xv1-empty") == {
        "count": "Rāda 2 no 2 jaunākajiem ierakstiem un pieminējumiem.", "emptyShown": False}
    page.click('.xv1-tab[data-type="mention"]')       # fikstūrā 0 pieminējumu
    assert _count_and_empty(page, "xv1-count", "xv1-empty") == {
        "count": "Rāda 0 no 2 jaunākajiem ierakstiem un pieminējumiem.", "emptyShown": True}
    page.close()


def test_zinas_filter_without_results_shows_message_and_count(site, browser):
    base, out = site
    # Bez JS skaitītājs nav tukšs (kā X): serveris ieraksta sākuma tekstu.
    assert ('id="news-count" role="status" aria-live="polite">'
            "Rāda 2 no 2 publikācijām.</p>") in (out / "zinas.html").read_text(encoding="utf-8")
    page = browser.new_page()
    page.goto(f"{base}/zinas.html")
    assert _count_and_empty(page, "news-count", "news-empty") == {
        "count": "Rāda 2 no 2 publikācijām.", "emptyShown": False}
    assert page.inner_text("#mentioned-person-trigger span").strip() == "Visas personas"
    assert page.inner_text("#mentioned-party-trigger span").strip() == "Visas partijas"
    page.goto(f"{base}/zinas.html?persona=Neesoša%20Persona")
    assert _count_and_empty(page, "news-count", "news-empty") == {
        "count": "Rāda 0 no 2 publikācijām.", "emptyShown": True}
    page.close()
