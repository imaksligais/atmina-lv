"""Lapu cilnes ievēro profila cilņu ARIA kontraktu (2026-10-11).

Kļūme, ko šis tests ķer: profila cilnēm (``pp-tabs``) ir pilns WAI-ARIA
cilņu kontrakts — ``role=tablist/tab/tabpanel``, ``aria-selected``,
``aria-controls``, roving ``tabindex`` un bultas/Home/End —, bet Analīzēs,
Balsojumos un partijas lapā cilnes bija tikai ar peli: ekrāna lasītājs
nezināja, kura cilne atvērta, un ar tastatūru starp tām nevarēja pārvietoties.
Kopīgo tastatūras loģiku nes ``assets/tabs-v1.js``.

Brauc īstas lapas pārlūkā (Playwright, Chromium) caur lokālu HTTP serveri:
``analizes.html`` un ``balsojumi.html`` no veidnes ar minimālo kontekstu,
``partijas/jv.html`` no ``render_parties()`` ar fikstūras DB. Uz katras:
fokuss uz pirmās cilnes → ArrowRight → fokuss un atlase pāriet uz otro,
tās panelis redzams, pirmās — paslēpts; End/Home → pēdējā/pirmā.
"""
import functools
import shutil
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest

from src.db import get_db, init_db
from src.render._common import _party_page_slug
from src.render.parties import _fetch_parties_page, render_parties
from src.saeima.schema import init_saeima_tables
from tests.test_balsojumi_client_render import _env as _balsojumi_env
from tests.test_balsojumi_client_render import _render as render_balsojumi

sync_api = pytest.importorskip("playwright.sync_api")

# Katras cilnes stāvoklis: [aria-selected, tabindex, vai fokusā, vai panelis redzams].
TABS_STATE = """() => {
  const list = document.querySelector('[role="tablist"]');
  if (!list) return null;
  return [...list.querySelectorAll('[role="tab"]')].map(t => {
    const panel = document.getElementById(t.getAttribute('aria-controls') || '');
    return [t.getAttribute('aria-selected'), t.getAttribute('tabindex'),
            document.activeElement === t,
            !!panel && panel.getAttribute('role') === 'tabpanel'
              && getComputedStyle(panel).display !== 'none'];
  });
}"""


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def _render_site(tmp_path):
    out = tmp_path / "site"
    out.mkdir()
    env = _balsojumi_env()
    (out / "balsojumi.html").write_text(render_balsojumi(), encoding="utf-8")
    (out / "analizes.html").write_text(env.get_template("analizes.html.j2").render(
        analyses=[], syntheses=[], posts=[], trends_data={}, context_notes=[],
        metrics={"daily": 0, "weekly": 0, "tematic": 0, "sintezes": 0}), encoding="utf-8")

    db_path = str(tmp_path / "t.db")
    init_db(db_path)
    init_saeima_tables(db_path)
    db = get_db(db_path)
    db.execute("INSERT INTO parties (id,name,short_name,coalition_status) "
               "VALUES (1,'Jaunā Vienotība','JV','coalition')")
    db.commit()
    env.filters["party_page_slug"] = _party_page_slug
    env.filters["lv_plural"] = lambda n, *a: ""
    render_parties(env, db, out, _fetch_parties_page(db))
    shutil.copytree("assets", out / "assets")
    return out


def _expect(state, selected, path):
    """Tieši ``selected`` cilne: atlasīta, tabulācijas secībā, fokusā, panelis redzams."""
    for i, (aria, tabindex, focused, visible) in enumerate(state):
        on = i == selected
        assert aria == ("true" if on else "false"), (path, i, state)
        assert tabindex == ("0" if on else "-1"), (path, i, state)
        assert focused == on, (path, i, state)
        assert visible == on, (path, i, state)


def test_tabs_follow_profile_aria_contract(tmp_path):
    out = _render_site(tmp_path)
    handler = functools.partial(_QuietHandler, directory=str(out))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        with sync_api.sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except Exception as exc:  # pragma: no cover — nav instalēta pārlūka
                pytest.skip(f"Chromium nav pieejams: {exc}")
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))

            for path in ("analizes.html", "balsojumi.html", "partijas/jv.html"):
                page.goto(f"{base}/{path}")
                state = page.evaluate(TABS_STATE)
                assert state is not None, f"{path}: nav role=tablist"
                assert len(state) >= 3, f"{path}: tikai {len(state)} cilnes — vārti nevar krist"

                page.focus('[role="tablist"] [role="tab"]')
                page.keyboard.press("ArrowRight")
                _expect(page.evaluate(TABS_STATE), 1, path)
                page.keyboard.press("End")
                _expect(page.evaluate(TABS_STATE), len(state) - 1, path)
                page.keyboard.press("Home")
                _expect(page.evaluate(TABS_STATE), 0, path)

            assert errors == [], errors
            browser.close()
    finally:
        server.shutdown()
