"""Spriedzes filtri dzīvo URL; partija atbilst autoram VAI adresātam (2026-10-18).

Kļūme 1: `data-party` glabāja tikai autora partiju → «AS» filtrs slēpa spriedzes,
kur AS deputāts ir adresāts. Kļūme 2: filtri bija tikai lapas atmiņā → nosūtīta
saite atvēra visu sarakstu. Kļūme 3: nezināma vērtība adresē nedrīkst dot 0 kartīšu.
Kļūme 4 (2026-10-21): 0 rezultātu rādīja tukšu lapu bez ziņas un skaitītāja.
"""
import functools
import shutil
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlparse

import pytest

from src.db import get_db, init_db
from src.render.tensions import _fetch_tensions, render_tensions
from tests.test_balsojumi_client_render import _env

sync_api = pytest.importorskip("playwright.sync_api")

_SQL = """
INSERT INTO tracked_politicians (id, name, party, role, relationship_type) VALUES
  (1, 'Anna Ābele', 'JV', 'deputāte', 'tracked'),
  (2, 'Bruno Bērziņš', 'AS', 'deputāts', 'tracked'),
  (3, 'Cilda Cīrule', 'ZZS', 'deputāte', 'tracked');
INSERT INTO political_tensions (id, source_pid, target_pid, topic, description, tension_type, source_url, created_at) VALUES
  (1, 1, 2, 'Imigrācija', 'Ābele kritizē Bērziņu.', 'uzbrukums', 'https://ex.lv/1', '2026-10-01 10:00:00'),
  (2, 3, 1, 'Budžets un finanses', 'Cīrule atbalsta Ābeli.', 'atbalsts', 'https://ex.lv/2', '2026-10-02 10:00:00');
"""


class _Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def _site(tmp_path):
    out = tmp_path / "site"
    out.mkdir()
    path = str(tmp_path / "t.db")
    init_db(path)
    db = get_db(path)
    db.executescript(_SQL)
    db.commit()
    try:
        render_tensions(_env(), db, out, _fetch_tensions(db))   # īstā render funkcija
    finally:
        db.close()
    shutil.copytree("assets", out / "assets", dirs_exist_ok=True)
    return out


def _visible(page):
    return page.eval_on_selector_all(
        "#tensions-grid .card", "els => els.filter(e => e.offsetParent !== null).length")


def test_spriedzes_filters_round_trip_and_match_either_party(tmp_path):
    out = _site(tmp_path)
    # Bez JS skaitītājs nav tukšs (kā X, final-review Minor 3): serveris ieraksta sākuma tekstu.
    assert ('id="tensions-count" role="status" aria-live="polite">'
            "Rāda 2 no 2 spriedzēm.</p>") in (out / "spriedzes.html").read_text(encoding="utf-8")
    server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Quiet, directory=str(out)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}/spriedzes.html"
    try:
        with sync_api.sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page()
            page.goto(base + "?party=AS")              # AS ir TIKAI adresāts
            assert _visible(page) == 1
            page.goto(base + "?party=JV")              # JV ir autors (1) un adresāts (2)
            assert _visible(page) == 2
            page.goto(base + "?party=Neesoša")         # nezināma vērtība → ignorē
            assert _visible(page) == 2
            page.goto(base)
            page.click("#type-select .multi-select-trigger")
            page.click("#type-select .multi-select-option[data-value='atbalsts']")
            assert parse_qs(urlparse(page.url).query) == {"type": ["atbalsts"]}
            assert _visible(page) == 1
            assert page.inner_text("#tensions-count").strip() == "Rāda 1 no 2 spriedzēm."
            # Kļūme 4 (good-css 5. kārta A9): 0 rezultātu → ziņa, ne tukša lapa.
            assert page.is_hidden("#tensions-empty")
            page.goto(base + "?type=atbalsts&person=" + quote("Bruno Bērziņš"))
            assert _visible(page) == 0
            assert page.inner_text("#tensions-count").strip() == "Rāda 0 no 2 spriedzēm."
            assert page.is_visible("#tensions-empty")
            assert "Nekas neatbilst" in page.inner_text("#tensions-empty")
            browser.close()
    finally:
        server.shutdown()
