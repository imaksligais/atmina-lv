"""Meklēšana bez garumzīmēm Personās, Likumos un X (2026-10-21).

Kļūme, ko šis tests ķer: lasītājs ieraksta «silina» (telefonā garumzīmes
liek reti), un Personas / X personu filtrs neatrod «Siliņa», jo šīs lapas
salīdzināja tikai ``toLowerCase()``. Pozīcijās un Balsojumos tas strādāja
(savs ``fold()``). Tagad visi lieto vienu ``window.atminaFold`` no
``assets/sgv1.js`` (ielādēts ar ``defer`` katrā lapā), un normalizē abas
salīdzinājuma puses. Likumos personu nav — tur to pašu uzvedību pārbauda
«velesanu» → «vēlēšanu».

Brauc īstas lapas pārlūkā (Playwright, Chromium) caur lokālu HTTP serveri.
"""
import functools
import shutil
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader

from src.db import get_db, init_db
from src.render._common import _safe_url_filter, lv_date, lv_date_short
from src.render._common.slugs import _party_short_name
from src.saeima import init_saeima_bills
from src.saeima.schema import init_saeima_tables

sync_api = pytest.importorskip("playwright.sync_api")

REPO = Path(__file__).resolve().parent.parent
# (id, vārds, partija, x rokturis) — Siliņa + divi, kuri «silina» NEdrīkst atrast.
PEOPLE = [
    (1, "Evika Siliņa", "Jaunā Vienotība", "silinaevika"),
    (2, "Anna Ozola", "Jaunā Vienotība", "anna_ozola"),
    (3, "Pēteris Kalns", "Nacionālā apvienība", "peteris_kalns"),
]
VISIBLE = """sel => [...document.querySelectorAll(sel)]
  .filter(el => el.getClientRects().length > 0).map(el => el.textContent)"""


class _Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def _env():
    env = Environment(loader=FileSystemLoader(str(REPO / "templates")), autoescape=True)
    env.filters["safe_url"] = _safe_url_filter
    env.filters["lv_date"] = lv_date
    env.filters["lv_date_short"] = lv_date_short
    env.filters["lv_plural"] = lambda n, one, many: one if n % 10 == 1 and n % 100 != 11 else many
    env.globals["assets_version"] = "test"
    env.globals["_party_short_name"] = _party_short_name
    return env


def _seed(db_path):
    init_db(db_path)
    init_saeima_tables(db_path)
    init_saeima_bills(db_path)
    db = get_db(db_path)
    doc_id = 10
    for pid, name, party, handle in PEOPLE:
        db.execute("INSERT INTO tracked_politicians (id,name,party,role,relationship_type) "
                   "VALUES (?,?,?,'Saeimas deputāts','tracked')", (pid, name, party))
        db.execute("INSERT INTO social_accounts (opponent_id,platform,handle,feed_type,active) "
                   "VALUES (?,'twitter',?,'first_party',1)", (pid, handle))
        doc_id += 1
        db.execute(
            "INSERT INTO documents (id,content,content_hash,platform,source_domain,"
            "source_url,scraped_at,published_at) "
            "VALUES (?,?,?,'twitter','x.com',?,'2026-10-10','2026-10-10T08:00:00')",
            (doc_id, f"{name} tvīts", f"h{doc_id}", f"https://x.com/{handle}/status/{doc_id}"))
        db.execute("INSERT INTO document_politicians (document_id,politician_id,role) "
                   "VALUES (?,?,'subject')", (doc_id, pid))
    db.commit()
    return db


def _site(tmp_path):
    from src.render.laws import render_laws
    from src.render.personas import render_personas
    from src.render.x import render_x

    out = tmp_path / "site"
    out.mkdir()
    env = _env()
    db = _seed(str(tmp_path / "t.db"))
    elected = tmp_path / "elected.yaml"
    elected.write_text("elected:\n" + "".join(
        f"- {{name: {name}, list_nr: 1, list_short: X, region: Rīga}}\n" for _, name, _, _ in PEOPLE),
        encoding="utf-8")
    cohort = tmp_path / "cohort.yaml"
    cohort.write_text("[]\n", encoding="utf-8")
    render_personas(env, db, out, elected_path=elected, cohort_path=cohort)
    render_x(env, db, out)
    render_laws(env, db, out)
    shutil.copytree(REPO / "assets", out / "assets", dirs_exist_ok=True)
    return out


def test_search_without_diacritics_finds_names(tmp_path, monkeypatch):
    monkeypatch.chdir(REPO)  # likumu katalogs no wiki/laws
    out = _site(tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Quiet, directory=str(out)))
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

            def personas():  # kartīšu meklētājs
                page.goto(f"{base}/personas.html")
                assert len(page.evaluate(VISIBLE, ".pnv1-card")) == len(PEOPLE)
                page.fill("#pnv1-search", "silina")
                shown = page.evaluate(VISIBLE, ".pnv1-card")
                assert len(shown) == 1 and "Siliņa" in shown[0], shown
                page.fill("#pnv1-search", "Siliņa")  # ar garumzīmēm arī
                assert len(page.evaluate(VISIBLE, ".pnv1-card")) == 1
                # Filtra čips rāda TO, ko lasītājs ierakstīja, ne locīto vaicājumu.
                chips = page.evaluate(VISIBLE, "#pnv1-active-chips .pnv1-chip")
                assert any("Siliņa" in c for c in chips), chips

            def x():  # personu filtra meklēšana nolaižamajā sarakstā
                page.goto(f"{base}/x.html")
                page.click("#xv1-persona-select .xv1-select-trigger")
                page.fill("#xv1-persona-select .xv1-select-search", "silina")
                shown = page.evaluate(VISIBLE, "#xv1-persona-select .xv1-select-option")
                assert [s.strip() for s in shown] == ["Evika Siliņa"], shown

            def likumi():  # nosaukuma meklētājs; personu nav — «velesanu» → «vēlēšanu»
                page.goto(f"{base}/likumi.html")
                total = len(page.evaluate(VISIBLE, "#laws-grid .bill-card"))
                page.fill("#law-search", "velesanu")
                shown = page.evaluate(VISIBLE, "#laws-grid .bill-card")
                assert 0 < len(shown) < total, (len(shown), total)
                assert all("vēlēšanu" in s.lower() for s in shown), shown

            failures = []
            for case in (personas, x, likumi):
                try:
                    case()
                except AssertionError as exc:
                    failures.append(f"{case.__name__}: {exc}")
            assert not failures, "\n".join(failures)
            assert errors == [], errors
            browser.close()
    finally:
        server.shutdown()
