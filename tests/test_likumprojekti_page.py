"""likumprojekti.html — likumprojektu katalogs savā lapā (2026-10-16).

Kļūmes, ko ķer: (1) meklēšana bez garumzīmēm neatrada neko; (2) pogas un
kartītes rādīja iekšējos kodus (Lp14, «tiesneša_amats»); (3) nebija redzams,
cik rezultātu palika («Rāda N no M»); (4) filtri nefiltrēja. Renderē caur
īsto render_bills_index() un atver Chromium."""

import functools
import shutil
import threading
from http.server import ThreadingHTTPServer

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

from src.db import get_db
from src.render.bills import (
    _fetch_bills,
    _stage_bucket,
    _stage_label,
    amended_law_name,
    card_status,
    render_bills_index,
)
from tests.test_generate_bills import db_with_bills  # noqa: F401 — fixture
from tests.test_multiselect_dropdown import _QuietHandler
from tests.test_profile_topic_deeplink import _env


def _serve(out):
    handler = functools.partial(_QuietHandler, directory=str(out))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


def _visible_nrs(page):
    return page.eval_on_selector_all(
        "#bills-grid .bill-card",
        "els => els.filter(e => e.offsetParent !== null)"
        ".map(e => e.querySelector('.badge').textContent.trim())")


def test_bills_page(db_with_bills, tmp_path):  # noqa: F811
    out = tmp_path / "site"
    out.mkdir()
    db = get_db(db_with_bills)
    bills = _fetch_bills(db)
    db.close()
    # Cita sasaukuma Lp + nezināma stadija (Review Focus 4, 5).
    bills.append(dict(bills[0], id=999, document_nr="1/Lp15", slug="1-lp15",
                      bill_type="Lp15", title="Jauns likums", topic=None,
                      current_stage="jauna_stadija", stage_label=_stage_label("jauna_stadija"),
                      current_status="procesā", bucket="nav", law=None,
                      card_status=card_status("Lp15", "jauna_stadija", "procesā")))
    # Trīs grozījumi vienam likumam → «Testa likums» nonāk «Biežāk grozītajos».
    for i in range(3):
        title = "Grozījumi Testa likumā"
        bills.append(dict(bills[0], id=900 + i, document_nr=f"{90 + i}/Lp14",
                          slug=f"{90 + i}-lp14", bill_type="Lp14", title=title,
                          current_stage="1.lasījums", stage_label=_stage_label("1.lasījums"),
                          current_status="procesā",
                          bucket=_stage_bucket("Lp14", "1.lasījums", "procesā"),
                          law=amended_law_name(title),
                          card_status=card_status("Lp14", "1.lasījums", "procesā")))
    render_bills_index(_env(), bills, 33, out)
    shutil.copytree("assets", out / "assets", dirs_exist_ok=True)

    html = (out / "likumprojekti.html").read_text(encoding="utf-8")
    # Lp no diviem sasaukumiem → ar sasaukumu; Lm/P tikai no viena → bez.
    assert 'data-bill-type="Lp14">Likumprojekti (14. Saeima)<' in html
    assert 'data-bill-type="Lp15">Likumprojekti (15. Saeima)<' in html
    assert 'data-bill-type="Lm14">Lēmumu projekti<' in html
    assert 'data-bill-type="P14">Pieprasījumi<' in html
    order = [html.index(f'data-bill-type="{t}"') for t in ("Lp15", "Lp14", "Lm14", "P14")]
    assert order == sorted(order)
    assert "tiesneša_amats" not in html and "lēmums par tiesneša amatu" in html
    assert "paziņojuma_balsojums" not in html and "balsojums par pieprasījumu" in html
    assert "jauna_stadija" in html  # nezināmu rāda, kā ir

    server, base = _serve(out)
    try:
        with sync_api.sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except Exception as exc:  # pragma: no cover
                pytest.skip(f"Chromium nav pieejams: {exc}")
            page = browser.new_page(viewport={"width": 390, "height": 844})
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"{base}/likumprojekti.html")
            n = len(bills)
            assert page.inner_text("#bills-count") == f"Rāda {n} no {n}"

            # Meklēšana bez garumzīmēm.
            page.fill("#bill-search", "aizsardzibas likuma")
            assert _visible_nrs(page) == ["1315/Lp14"]
            assert page.inner_text("#bills-count") == f"Rāda 1 no {n}"
            page.fill("#bill-search", "zzzz-nav-tada")
            assert page.inner_text("#bills-count") == f"Rāda 0 no {n}"
            assert page.is_visible("#bills-empty-state")
            page.fill("#bill-search", "")

            # Statuss.
            page.click('.bill-status-filter [data-status="noraidīts"]')
            want = {b["document_nr"] for b in bills if b["current_status"] == "noraidīts"}
            assert set(_visible_nrs(page)) == want
            page.click('.bill-status-filter [data-status=""]')

            # Tips: izslēdz Lp14.
            page.click('.bill-type-filter [data-bill-type="Lp14"]')
            assert not any(nr.endswith("/Lp14") for nr in _visible_nrs(page))
            page.click('.bill-type-filter [data-bill-type="Lp14"]')
            assert page.inner_text("#bills-count") == f"Rāda {n} no {n}"

            # Posmu josla: «Kļuvuši par likumu» atstāj tikai pieņemtos Lp;
            # otrs klikšķis izvēli noņem.
            page.click('.lpv1-stages [data-bucket="pienemts"]')
            want = {b["document_nr"] for b in bills
                    if b["bill_type"].startswith("Lp") and b["current_status"] == "pieņemts"}
            assert want and set(_visible_nrs(page)) == want
            assert page.get_attribute('.lpv1-stages [data-bucket="pienemts"]', "aria-pressed") == "true"
            page.click('.lpv1-stages [data-bucket="pienemts"]')
            assert page.inner_text("#bills-count") == f"Rāda {n} no {n}"

            # Biežāk grozītie likumi: aizvērts <details>; likums atstāj tikai
            # savus grozījumus, otrs klikšķis izvēli noņem.
            assert not page.is_visible('.lpv1-laws [data-law="Testa likums"]')
            page.click(".lpv1-laws summary")
            page.click('.lpv1-laws [data-law="Testa likums"]')
            assert sorted(_visible_nrs(page)) == ["90/Lp14", "91/Lp14", "92/Lp14"]
            assert page.inner_text("#bills-count") == f"Rāda 3 no {n}"
            # Ar izvēlētu likumu <details> neaizveras (filtrs nepaslēpjas).
            page.click(".lpv1-laws summary")
            page.wait_for_timeout(100)
            assert page.evaluate("document.querySelector('.lpv1-laws').open")
            page.click('.lpv1-laws [data-law="Testa likums"]')
            assert page.inner_text("#bills-count") == f"Rāda {n} no {n}"
            page.click(".lpv1-laws summary")
            page.wait_for_function("!document.querySelector('.lpv1-laws').open")

            # Sadaļas josla: šī lapa aktīva, saite uz pamatlikumiem.
            assert page.get_attribute('nav.likumi-tabs a[href="likumprojekti.html"]', "aria-current") == "page"
            assert page.inner_text('nav.likumi-tabs a[href="likumi.html"]') == "Pamatlikumi (33)"
            assert page.inner_text('nav.likumi-tabs a[href="likumprojekti.html"]') == f"Likumprojekti ({n})"
            assert errors == [], errors
            browser.close()
    finally:
        server.shutdown()
