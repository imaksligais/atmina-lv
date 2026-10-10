"""Filtru pogas paziņo ekrāna lasītājam, kura ir ieslēgta (2026-10-09).

Kļūme, ko šis tests ķer: Pozīciju rail rindas un Balsojumu filtri/apakšcilnes
mainīja tikai vizuālo klasi (``is-active`` / ``active``), bet ne
``aria-pressed`` — ekrāna lasītājs nezināja, kurš filtrs ieslēgts.

Brauc īstas lapas pārlūkā (Playwright, Chromium) caur lokālu HTTP serveri
(``pzv1.js`` ielādē ``pozicijas-data.json`` ar fetch, ko file:// bloķē):
Pozīcijas renderē ``render_positions()`` no fikstūras DB, Balsojumus —
``balsojumi.html.j2`` ar minimālo kontekstu. Pēc klikšķa nospiestajai pogai
``aria-pressed="true"``, iepriekš aktīvajai — ``"false"``, un atribūts
sakrīt ar klasi visā grupā.
"""
import functools
import shutil
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest

from src.render.positions import render_positions
from tests.test_balsojumi_client_render import _render as render_balsojumi
from tests.test_profile_topic_deeplink import OTHER_TOPIC, _env, _seed

sync_api = pytest.importorskip("playwright.sync_api")

GROUP_STATE = """([sel, cls]) => [...document.querySelectorAll(sel)].map(
  b => [b.classList.contains(cls), b.getAttribute('aria-pressed')])"""


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def _assert_group_in_sync(page, sel, cls):
    state = page.evaluate(GROUP_STATE, [sel, cls])
    assert state, f"{sel}: nav nevienas pogas"
    for active, pressed in state:
        assert pressed == ("true" if active else "false"), (sel, state)


def test_filter_buttons_expose_pressed_state(tmp_path):
    out = tmp_path / "site"
    out.mkdir()
    db = _seed(str(tmp_path / "t.db"))
    render_positions(_env(), db, out)
    (out / "balsojumi.html").write_text(render_balsojumi(), encoding="utf-8")
    shutil.copytree("assets", out / "assets")

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

            # Pozīcijas: tēmas rail rinda.
            page.goto(f"{base}/pozicijas.html")
            topic_sel = '.pzv1-rail-row[data-axis="topic"]'
            _assert_group_in_sync(page, topic_sel, "is-active")
            page.click(f'{topic_sel}[data-value="{OTHER_TOPIC}"]')
            assert page.get_attribute(
                f'{topic_sel}[data-value="{OTHER_TOPIC}"]', "aria-pressed") == "true"
            assert page.get_attribute(
                f'{topic_sel}[data-value="visas"]', "aria-pressed") == "false"
            _assert_group_in_sync(page, topic_sel, "is-active")

            # ?tema= ar neesošu tēmu/partiju: paliek noklusējums, nevis neviena
            # atzīmēta rinda un 0 rezultātu.
            page.goto(f"{base}/pozicijas.html?tema=Neesoša&partija=Neesoša")
            for axis, default in (("topic", "visas"), ("party", "Visas")):
                assert page.get_attribute(
                    f'.pzv1-rail-row[data-axis="{axis}"][data-value="{default}"]',
                    "aria-pressed") == "true", axis
            assert page.inner_text("#pzv1-shown") == page.inner_text("#pzv1-total")

            # Balsojumi: likumprojektu statusa filtrs + apakšcilnes.
            page.goto(f"{base}/balsojumi.html")
            status_sel = ".bill-status-filter .link-filter-btn"
            _assert_group_in_sync(page, status_sel, "active")
            page.click('.subtab-btn[data-tab="bills-list"]')
            page.click(f'{status_sel}[data-status="procesā"]')
            assert page.get_attribute(
                f'{status_sel}[data-status="procesā"]', "aria-pressed") == "true"
            assert page.get_attribute(
                f'{status_sel}[data-status=""]', "aria-pressed") == "false"
            _assert_group_in_sync(page, status_sel, "active")
            _assert_group_in_sync(page, ".subtab-btn", "active")
            browser.close()
    finally:
        server.shutdown()
