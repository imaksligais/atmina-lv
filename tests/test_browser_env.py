"""Pārlūka testu vide: viens savienojums uz serveri un izslēgtas animācijas.

Kļūme 1: `SimpleHTTPRequestHandler` pēc noklusējuma runā HTTP/1.0, tātad katram
failam atver jaunu savienojumu; šajā datorā daļa pazūd, un `Page.goto` beidzas ar
noildzi. Mērījums 2026-11-05: 50 no 400 ielādēm pret 0–1 no 400 ar HTTP/1.1.
Kļūme 2: `<details>` izvēršanas pārejas laikā `inner_text()` atgriež tukšu tekstu,
tāpēc tests krīt vai iziet atkarībā no datora slodzes.
"""

import functools
import http.client
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest

sync_api = pytest.importorskip("playwright.sync_api")


@pytest.fixture
def server(tmp_path):
    (tmp_path / "a.html").write_text("<!doctype html><title>a</title>", encoding="utf-8")
    srv = ThreadingHTTPServer(("127.0.0.1", 0),
                              functools.partial(SimpleHTTPRequestHandler, directory=str(tmp_path)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv.server_address[1]
    srv.shutdown()
    srv.server_close()


def test_static_server_reuses_one_connection(server):
    conn = http.client.HTTPConnection("127.0.0.1", server, timeout=5)
    conn.request("GET", "/a.html")
    first = conn.getresponse()
    first.read()
    sock = conn.sock
    conn.request("GET", "/a.html")
    second = conn.getresponse()
    second.read()
    still_same = sock is not None and conn.sock is sock   # HTTP/1.0 te aizver savienojumu
    conn.close()
    assert (first.status, second.status) == (200, 200)
    assert still_same


def test_goto_retries_once_and_a_truly_broken_page_still_fails(server):
    url = f"http://127.0.0.1:{server}/a.html"
    calls = []

    def lose(n):
        def handler(route):
            calls.append(route.request.url)
            if len(calls) <= n:
                route.abort("connectionreset")
            else:
                route.continue_()
        return handler

    with sync_api.sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Exception as exc:  # pragma: no cover — nav instalēta pārlūka
            pytest.skip(f"Chromium nav pieejams: {exc}")
        try:
            page = browser.new_page()
            page.route("**/a.html", lose(1))
            with pytest.warns(UserWarning, match="atkārtots"):
                assert page.goto(url).status == 200
            assert len(calls) == 2

            calls.clear()
            page.unroute("**/a.html")
            page.route("**/a.html", lose(2))
            with pytest.warns(UserWarning, match="atkārtots"), pytest.raises(sync_api.Error):
                page.goto(url)
            assert len(calls) == 2                     # tikai viens atkārtojums
        finally:
            browser.close()


def test_plain_server_is_served_from_disk_and_custom_server_stays_real(tmp_path):
    (tmp_path / "a.html").write_text(
        '<!doctype html><link rel=stylesheet href="s.css"><title>a</title>', encoding="utf-8")
    (tmp_path / "s.css").write_text("title{color:red}", encoding="utf-8")

    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    class WithHeader(Quiet):
        def end_headers(self):
            self.send_header("X-Pazime", "ir")
            super().end_headers()

    plain = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(tmp_path)))
    plain_port = plain.server_address[1]
    plain.server_close()                                   # neviens vairs neklausās
    real = ThreadingHTTPServer(("127.0.0.1", 0),
                               functools.partial(WithHeader, directory=str(tmp_path)))
    threading.Thread(target=real.serve_forever, daemon=True).start()
    with sync_api.sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Exception as exc:  # pragma: no cover — nav instalēta pārlūka
            pytest.skip(f"Chromium nav pieejams: {exc}")
        try:
            page = browser.new_page()
            seen = []
            page.on("response", lambda r: seen.append((r.url.rsplit("/", 1)[1], r.status)))
            assert page.goto(f"http://127.0.0.1:{plain_port}/a.html").status == 200
            assert ("s.css", 200) in seen
            assert page.goto(f"http://127.0.0.1:{plain_port}/nav.html").status == 404
            custom = page.goto(f"http://127.0.0.1:{real.server_address[1]}/a.html")
            assert custom.status == 200 and custom.headers.get("x-pazime") == "ir"
        finally:
            browser.close()
            real.shutdown()
            real.server_close()


def test_server_queue_is_long_enough_for_a_browser(server):
    from http.server import HTTPServer
    assert HTTPServer.request_queue_size >= 64


def test_browser_contexts_default_to_reduced_motion_but_can_opt_out():
    query = "matchMedia('(prefers-reduced-motion: reduce)').matches"
    with sync_api.sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Exception as exc:  # pragma: no cover — nav instalēta pārlūka
            pytest.skip(f"Chromium nav pieejams: {exc}")
        try:
            assert browser.new_page().evaluate(query) is True
            assert browser.new_context().new_page().evaluate(query) is True
            opted = browser.new_context(reduced_motion="no-preference").new_page()
            assert opted.evaluate(query) is False
        finally:
            browser.close()
