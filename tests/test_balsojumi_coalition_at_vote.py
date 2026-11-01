"""Balsojuma kartīte grupē frakcijas pēc TĀ BRĪŽA valdības, ne šodienas (2026-10-16).

Kļūme, ko šis tests ķer: kartīte lasīja `DATA.factions[].cs` (šodienas
`parties.coalition_status`), tāpēc Siliņas laika balsojumā PRO stāvēja zem
«Opozīcija», AS zem «Koalīcija» — otrādi nekā bija. Kad 15. Saeima sanāks,
pārkrāsotos visas 14. Saeimas kartītes. Plāns:
docs/superpowers/plans/archive/2026-10-16-koalicija-balsojuma-diena.md.

Fikstūrā `DATA.factions` apzināti nes ŠODIENAS statusu (AS koalīcijā, PRO
opozīcijā), bet balsojumam `co` norāda uz Siliņas valdību — tātad vecā
grupēšana dod pretējo atbildi abām frakcijām.

Brauc īstu lapu pārlūkā (Playwright, Chromium), tas pats harness kā
``tests/test_balsojumi_url_filters.py``.
"""
import copy
import functools
import json
import threading
from http.server import ThreadingHTTPServer

import pytest

from tests.test_balsojumi_readability import _FIXTURE
from tests.test_balsojumi_url_filters import _QuietHandler, _info, _site

sync_api = pytest.importorskip("playwright.sync_api")

_FB = [
    {"f": "JV", "p": 20, "n": 0, "a": 0, "x": 1},
    {"f": "PRO", "p": 9, "n": 0, "a": 0, "x": 0},
    {"f": "AS", "p": 0, "n": 14, "a": 0, "x": 1},
    {"f": "ārpusfrakciju", "p": 1, "n": 1, "a": 0, "x": 0},
]


def _data():
    data = copy.deepcopy(_FIXTURE)
    data["coalitions"] = [["JV", "PRO", "ZZS"], ["AS", "JV", "NA", "ZZS"]]
    data["factions"] = [
        {"f": "JV", "c": "#3b82f6", "cs": "coalition", "m": [1]},
        {"f": "ZZS", "c": "#84cc16", "cs": "coalition", "m": [2]},
        {"f": "AS", "c": "#1e3a8a", "cs": "coalition", "m": []},
        {"f": "PRO", "c": "#e11d48", "cs": "opposition", "m": []},
    ]
    for v in data["votes"]:
        v["co"] = 1
    data["votes"][0].update(d="2024-03-14", co=0, f=_FB)     # Siliņas laiks (vid 1000)
    data["votes"][2].update(co=None, f=_FB)                  # pirms pirmā perioda (vid 1002)
    data["votes"][5].update(f=_FB)                           # pēc 2026-05-28 (vid 1005)
    data["meta"]["all_dates"] = ["2026-08-20", "2026-08-13", "2024-03-14"]
    return data


_GROUPS_JS = """(id) => Array.from(document.querySelectorAll('#' + id + ' .vote-fgroup')).map(
  g => [g.querySelector('.vote-fglabel').textContent,
        Array.from(g.querySelectorAll('.vote-fname')).map(n => n.textContent)])"""


def test_vote_card_groups_by_the_coalition_in_office_that_day(tmp_path):
    out = _site(tmp_path)
    blob = json.dumps(_data(), ensure_ascii=False)
    for name in ("balsojumi-matrica.json", "balsojumi-matrica-recent.json"):
        (out / "data" / name).write_text(blob, encoding="utf-8")
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
            page.goto(base)
            assert _info(page) == "Rāda 7 no 7 balsojumiem."

            groups = lambda vid: dict(page.evaluate(_GROUPS_JS, f"vote-{vid}"))  # noqa: E731

            silina = groups(1000)
            assert "PRO" in silina["Koalīcija"], silina
            assert "AS" in silina["Opozīcija"], silina
            assert silina["Ārpus frakcijām"] == ["ārpus"]

            now = groups(1005)
            assert "AS" in now["Koalīcija"] and "PRO" in now["Opozīcija"], now

            # Pirms pirmā zināmā perioda: viena grupa, bez koalīcijas/opozīcijas.
            before = groups(1002)
            assert list(before) == ["Frakcijas"], before
            assert before["Frakcijas"] == ["JV", "PRO", "AS", "ārpus"]
            browser.close()
    finally:
        server.shutdown()
