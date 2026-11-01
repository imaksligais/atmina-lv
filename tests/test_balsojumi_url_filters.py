"""Balsojumu saraksta filtri dzīvo URL adresē, lai rezultātu var nosūtīt (2026-10-16).

Kļūme, ko šis tests ķer: lasītājs atrod balsojumus («izglitibas», augusts,
tikai dalītie), nokopē adresi un nosūta — saņēmējs redz visu sarakstu, jo
filtri bija tikai lapas atmiņā. Otrā puse: neesoša vērtība adresē (vecā
saite, pārrakstīts tēmas nosaukums) nedrīkst dot «0 balsojumu».

Brauc īstu lapu pārlūkā (Playwright, Chromium): ``balsojumi.html.j2`` ar
filtru opcijām + ``tests.test_balsojumi_readability::_FIXTURE`` kā matricas JSON.
"""
import functools
import json
import shutil
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import pytest

from tests.test_balsojumi_client_render import _MINIMAL_CTX, _env
from tests.test_balsojumi_readability import _FIXTURE

sync_api = pytest.importorskip("playwright.sync_api")


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def _site(tmp_path):
    out = tmp_path / "site"
    (out / "data").mkdir(parents=True)
    ctx = dict(
        _MINIMAL_CTX,
        vote_topics=["Valsts pārvalde"],
        deputies=[{"name": "Anna Ābele", "faction": "JV"},
                  {"name": "Cilda Cīrule", "faction": "ZZS"}],
        vote_months=["2026-08"],
        vote_sessions=["2026-08-20", "2026-08-13"],
        metrics=dict(_MINIMAL_CTX["metrics"], total=7),
    )
    html = _env().get_template("balsojumi.html.j2").render(**ctx)
    (out / "balsojumi.html").write_text(html, encoding="utf-8")
    blob = json.dumps(_FIXTURE, ensure_ascii=False)
    for name in ("balsojumi-matrica.json", "balsojumi-matrica-recent.json"):
        (out / "data" / name).write_text(blob, encoding="utf-8")
    shutil.copytree("assets", out / "assets", dirs_exist_ok=True)
    return out


def _info(page):
    page.wait_for_function(
        "() => !document.getElementById('votes-archive-info').textContent.includes('Ielādē')")
    return page.inner_text("#votes-archive-info")


def _params(page):
    return parse_qs(urlparse(page.url).query)


def test_vote_filters_round_trip_through_the_url(tmp_path):
    out = _site(tmp_path)
    handler = functools.partial(_QuietHandler, directory=str(out))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}/balsojumi.html"
    try:
        with sync_api.sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except Exception as exc:  # pragma: no cover — nav instalēta pārlūka
                pytest.skip(f"Chromium nav pieejams: {exc}")
            page = browser.new_page(viewport={"width": 1280, "height": 900})

            # Saucējs: bez filtriem redzami visi 7 — citādi vārti nevar krist.
            page.goto(base)
            assert _info(page) == "Rāda 7 no 7 balsojumiem."
            assert urlparse(page.url).query == "", "ielāde pati nedrīkst rakstīt adresi"

            # Lietotājs filtrē → adrese seko.
            page.fill("#vote-search", "izglitibas")
            page.wait_for_function("() => location.search.includes('q=')")
            page.click("#vote-split-toggle")
            page.click("#month-trigger")
            page.click('#month-select .multi-select-option[data-value="2026-08"]')
            assert _info(page) == "Rāda 1 no 1 balsojumiem."
            shared = page.url
            assert _params(page) == {"q": ["izglitibas"], "menesis": ["2026-08"],
                                     "dalitie": ["1"]}

            # Saņēmējs atver nosūtīto adresi → tas pats rezultāts un tie paši vadīklas.
            page2 = browser.new_page(viewport={"width": 1280, "height": 900})
            page2.goto(shared)
            assert _info(page2) == "Rāda 1 no 1 balsojumiem."
            assert page2.input_value("#vote-search") == "izglitibas"
            assert page2.get_attribute("#vote-split-toggle", "aria-pressed") == "true"
            assert page2.inner_text("#month-trigger span").strip() == "2026. g. augusts"

            # Filtra noņemšana izņem to arī no adreses.
            page2.click("#vote-split-toggle")
            assert "dalitie" not in _params(page2)
            assert _info(page2) == "Rāda 2 no 2 balsojumiem."

            # Vairākas vērtības + vecais ?deputats= + ?tab paliek.
            page.goto(base + "?sede=2026-08-13&sede=2026-08-20&deputats=Cilda%20C%C4%ABrule")
            assert _info(page) == "Rāda 5 no 5 balsojumiem.", "Cildai 13.08 nav ieraksta"
            assert "has-selection" in page.get_attribute("#deputy-trigger", "class")

            # Neesoša vērtība → noklusējums, ne 0 rezultātu.
            page.goto(base + "?tema=Neeso%C5%A1a&sede=1999-01-01")
            assert _info(page) == "Rāda 7 no 7 balsojumiem."
            assert page.inner_text("#topic-trigger span").strip() == "Visas tēmas"
            browser.close()
    finally:
        server.shutdown()
