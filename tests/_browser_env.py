"""Vienots pārlūka testu iestatījums, tikai testu procesam.

Izmaiņas vienā vietā, lai nav jāpārraksta ap 35 pārlūka testu faili. Šajā datorā
daļa lokālo savienojumu pazūd, tāpēc mazāk savienojumu nozīmē mazāk kļūmju.
Mērījums 2026-11-05 (`saites.html`, 400 ielādes, 8 s limits; `.scratch/testdiag/`):
HTTP/1.0 50 noildzes, HTTP/1.1 0 un 1, bez tīkla 0.

* **Bez tīkla.** Vienkārša statisko failu servera atbildes pārlūks saņem tieši no
  diska. Serveris ar savu loģiku (piem., CSP galvenes) paliek īsts un runā HTTP/1.1.
* **Rinda 128, ne 5.** Pilna rinda Windows atbild ar `ERR_CONNECTION_RESET`.
* **`reduced_motion="reduce"` pēc noklusējuma.** `assets/style.css` pārejas ir zem
  `no-preference`, tāpēc izvērstais saturs ir nolasāms uzreiz. Tests, kam vajag
  animāciju, padod `reduced_motion="no-preference"`.
* **`Page.goto` vienreiz atkārto** zudušu savienojumu vai noildzi. Lapa, kas tiešām
  neielādējas, krīt arī otrreiz; katrs atkārtojums redzams pytest brīdinājumos.
"""

from __future__ import annotations

import functools
import mimetypes
import os
import re
import warnings
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote, urlparse

_LOCAL = re.compile(r"^http://127\.0\.0\.1:\d+/")
_CONTENT_TYPES = {".js": "text/javascript", ".css": "text/css", ".json": "application/json",
                  ".html": "text/html", ".svg": "image/svg+xml", ".webp": "image/webp",
                  ".woff2": "font/woff2"}
_static_servers: dict[int, str | None] = {}


def _static_directory(handler) -> tuple[bool, str | None]:
    """(vai šis ir vienkāršs failu serveris, tā mape; None = pašreizējā mape)."""
    directory = None
    if isinstance(handler, functools.partial):
        if handler.args or set(handler.keywords) - {"directory"}:
            return False, None
        directory = handler.keywords.get("directory")
        handler = handler.func
    if not (isinstance(handler, type) and issubclass(handler, SimpleHTTPRequestHandler)):
        return False, None
    for cls in handler.__mro__:
        if cls is SimpleHTTPRequestHandler:
            return True, directory
        if any(callable(v) and n not in {"log_message"} and not n.startswith("__")
               or n == "__init__" for n, v in vars(cls).items()):
            return False, None
    return False, None


def _remember_static_server(method):
    @functools.wraps(method)
    def wrapper(self):
        method(self)
        static, directory = _static_directory(self.RequestHandlerClass)
        if static:
            _static_servers[self.server_address[1]] = directory
        else:
            _static_servers.pop(self.server_address[1], None)

    return wrapper


def _fulfill_from_disk(route) -> bool:
    request = route.request
    url = urlparse(request.url)
    if url.hostname != "127.0.0.1" or url.port not in _static_servers:
        return False
    if request.method not in ("GET", "HEAD"):
        return False
    root = Path(_static_servers[url.port] or os.getcwd())
    path = root / unquote(url.path).lstrip("/")
    if path.is_dir():
        path = path / "index.html"
    if not path.is_file():
        route.fulfill(status=404, body=b"")
        return True
    content_type = (_CONTENT_TYPES.get(path.suffix.lower())
                    or mimetypes.guess_type(path.name)[0] or "application/octet-stream")
    body = b"" if request.method == "HEAD" else path.read_bytes()
    route.fulfill(status=200, body=body, content_type=content_type)
    return True


def _serve_static(route) -> None:
    if not _fulfill_from_disk(route):
        route.fallback()


def _continue_from_disk(method):
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        if not args and not kwargs and _fulfill_from_disk(self):
            return None
        return method(self, *args, **kwargs)

    return wrapper


def _new_context(method):
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        kwargs.setdefault("reduced_motion", "reduce")
        context = method(self, *args, **kwargs)
        context.route(_LOCAL, _serve_static)
        return context

    return wrapper


def _new_page(method):
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        kwargs.setdefault("reduced_motion", "reduce")
        page = method(self, *args, **kwargs)
        page.context.route(_LOCAL, _serve_static)
        return page

    return wrapper


def _retry_lost_navigation(method, playwright_error):
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except playwright_error as exc:
            text = str(exc)
            if "net::ERR_CONNECTION" not in text and "Timeout" not in text:
                raise
            warnings.warn(f"Page.goto atkārtots pēc zuduša savienojuma: {text.splitlines()[0]}",
                          stacklevel=2)
            self.wait_for_timeout(300)   # lai beidzas pārlūka kļūdas lapas pāreja
            return method(self, *args, **kwargs)

    return wrapper


def install() -> None:
    SimpleHTTPRequestHandler.protocol_version = "HTTP/1.1"
    HTTPServer.request_queue_size = 128
    HTTPServer.server_bind = _remember_static_server(HTTPServer.server_bind)
    try:
        from playwright.sync_api import Browser, Error, Page, Route
    except ImportError:  # Playwright nav obligāts
        return
    Browser.new_context = _new_context(Browser.new_context)
    Browser.new_page = _new_page(Browser.new_page)
    Route.continue_ = _continue_from_disk(Route.continue_)
    Page.goto = _retry_lost_navigation(Page.goto, Error)
