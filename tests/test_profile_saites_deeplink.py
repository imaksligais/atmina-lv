"""Dziļā saite ``politiki/<slug>.html#saites-<pid>`` atver Saites cilni un
ritina uz pāra kartīti (Saites redizains, Task A2, 2026-10-18).

Kļūme, ko šis tests ķer: Saites lapa (A3) ved lasītāju uz profila kartīti
ar ``#saites-<pid>``, bet ``ppv1.js`` hash pazina tikai cilņu vārdus —
``saites-12`` nav cilne, tāpēc atvērās noklusētā cilne, un kartīte palika
paslēptā panelī. Lasītājs redz profila sākumu, nevis saikni, uz kuru
klikšķināja.

Review Focus 3: pārim ir divas kartītes, ``id`` ir tikai pirmajai — saite
ved uz to. Nezināms pid → cilne tomēr atveras, bez kļūdas.

Brauc īstu profila lapu pārlūkā (Playwright, Chromium), renderētu ar
``render_politicians`` no sīkas DB.
"""
import functools
import shutil
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest

from src.db import get_db, init_db
from src.render.politicians import render_politicians
from src.saeima.schema import init_saeima_bills, init_saeima_tables
from tests.test_profile_topic_deeplink import _env

sync_api = pytest.importorskip("playwright.sync_api")

VIEWPORT = {"width": 390, "height": 640}


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def _site(tmp_path):
    db_path = str(tmp_path / "t.db")
    init_db(db_path)
    init_saeima_tables(db_path)
    init_saeima_bills(db_path)
    db = get_db(db_path)
    db.executescript("""
        INSERT INTO tracked_politicians (id, name, party, relationship_type) VALUES
            (1, 'A Kalns', 'JV', 'tracked'),
            (2, 'B Ozols', 'ZZS', 'tracked'),
            (3, 'C Liepa', 'AS', 'tracked');
        -- Trīs uzbrukumi ar C Liepu stāv pirms spriedzēm → B Ozola kartīte
        -- ir zem pirmā ekrāna; pārim A–B divas kartītes (id tikai pirmajai).
        INSERT INTO political_tensions
            (source_pid, target_pid, topic, description, tension_type, created_at) VALUES
            (1, 3, 'Ekonomika', 'Uzbrukums viens', 'uzbrukums', '2026-10-10 10:00:00'),
            (1, 3, 'Ekonomika', 'Uzbrukums divi', 'uzbrukums', '2026-10-09 10:00:00'),
            (3, 1, 'Ekonomika', 'Uzbrukums trīs', 'uzbrukums', '2026-10-08 10:00:00'),
            (1, 2, 'Budžets', 'Spriedze viena', 'spriedze', '2026-10-07 10:00:00'),
            (2, 1, 'Budžets', 'Spriedze otrā', 'spriedze', '2026-10-06 10:00:00');
    """)
    db.commit()
    out = tmp_path / "site" / "atmina"
    out.mkdir(parents=True)
    try:
        render_politicians(_env(), db, out, [
            {"id": 1, "name": "A Kalns", "slug": "a-kalns",
             "profile_kind": "politician", "role_label": "deputāts",
             "party": "JV", "x_handle": None},
        ], pid_to_syntheses={})
    finally:
        db.close()
    shutil.copytree("assets", out / "assets", dirs_exist_ok=True)
    return out


def _settle(page):
    """Gaida, līdz scrollY 300 ms nemainās (pārlūka fragmenta + mūsu ritināšana)."""
    last = None
    for _ in range(40):
        page.wait_for_timeout(300)
        y = page.evaluate("scrollY")
        if y == last:
            return
        last = y
    raise AssertionError("lapa neapstājās ritināties")


def _in_viewport(page, selector):
    box = page.locator(selector).bounding_box()
    return box is not None and 0 <= box["y"] < VIEWPORT["height"]


def test_saites_hash_opens_tab_and_scrolls_to_pair_card(tmp_path):
    out = _site(tmp_path)
    html = (out / "politiki" / "a-kalns.html").read_text(encoding="utf-8")
    # Pārim A–B tieši viens enkurs, lai gan kartītes ir divas.
    assert html.count('id="saites-2"') == 1
    assert html.count("Spriedze viena") == 1 and html.count("Spriedze otrā") == 1

    handler = functools.partial(_QuietHandler, directory=str(out))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}/politiki/a-kalns.html"
    try:
        with sync_api.sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except Exception as exc:  # pragma: no cover — nav instalēta pārlūka
                pytest.skip(f"Chromium nav pieejams: {exc}")
            errors: list[str] = []

            def _page(url):
                page = browser.new_page(viewport=VIEWPORT)
                page.on("pageerror", lambda e: errors.append(str(e)))
                page.goto(url)
                page.wait_for_load_state("load")
                return page

            # Saucējs: bez kartītes pid cilne atveras, bet kartīte ir zem
            # ekrāna — citādi «redzama skatlogā» neko nepierāda.
            page = _page(base + "#saites")
            assert page.get_attribute("#tab-btn-saites", "aria-selected") == "true"
            assert not _in_viewport(page, "#saites-2"), "kartīte jau pirmajā ekrānā"

            # Dziļā saite uz pāri: cilne atvērta, kartīte skatlogā.
            page = _page(base + "#saites-2")
            assert page.get_attribute("#tab-btn-saites", "aria-selected") == "true"
            assert "active" in page.get_attribute("#tab-btn-saites", "class")
            assert page.is_visible("#saites-2")
            # Kartīte skatlogā UN nav paslēpta zem sticky cilņu joslas (390 px
            # josla pielīp pie top:69px; pārlūka paša :target ritināšana to
            # pārklātu).
            # Ritināšana ir gluda (scroll-behavior) — vērtē tikai, kad tā
            # apstājusies, citādi pārbaude var trāpīt starpstāvoklī.
            _settle(page)
            assert _in_viewport(page, "#saites-2")
            bar = page.locator(".pp-tabs").bounding_box()
            assert page.locator("#saites-2").bounding_box()["y"] >= bar["y"] + bar["height"]
            assert page.evaluate("location.hash") == "#saites-2", "dziļā saite jāsaglabā adresē"

            # Nezināms pid: cilne tomēr atveras, bez JS kļūdas.
            page = _page(base + "#saites-999")
            assert page.get_attribute("#tab-btn-saites", "aria-selected") == "true"

            # Cita hash uzvedība nemainās: nezināma vērtība → noklusētā cilne.
            page = _page(base + "#neesoša")
            assert page.get_attribute("#tab-btn-saites", "aria-selected") == "false"

            assert errors == []
            browser.close()
    finally:
        server.shutdown()
