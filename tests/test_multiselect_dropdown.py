"""Filtru nolaižamie saraksti (multi-select) uzvedas vienādi abās saimēs (2026-10-11).

Kļūme, ko šis tests ķer: sešas lapas (balsojumi, pretrunas, saites,
spriedzes, x, zinas) nesa katra savu ``setupMultiSelect`` kopiju; tās
apvieno ``assets/msv1.js``. Ja kopīgajā kodā salūzt viens solis — atvēršana,
atlase, filtrēšana, cita saraksta aizvēršana, klikšķis ārpusē, notīrīšana —
filtrs lapā vairs nestrādā, un neviens cits tests to neredz.

Brauc īstas lapas pārlūkā (Playwright, Chromium) caur lokālu HTTP serveri:
``spriedzes.html`` (``.multi-select`` saime) no ``render_tensions()`` un
``x.html`` (``.xv1-select`` saime) no ``render_x()`` ar fikstūras DB.
"""
import functools
import shutil
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest

from src.db import get_db, init_db
from src.render._common.slugs import _party_short_name
from src.render.tensions import render_tensions
from src.render.x import render_x
from src.saeima.schema import init_saeima_tables
from tests.test_profile_topic_deeplink import _env

sync_api = pytest.importorskip("playwright.sync_api")

VISIBLE = """sel => [...document.querySelectorAll(sel)]
  .filter(el => getComputedStyle(el).display !== 'none').length"""

# (id, vārds, partija, x rokturis)
POLITICIANS = [
    (1, "Anna Ozola", "Partija A", "anna_ozola"),
    (2, "Jānis Bērzs", "Partija A", "janis_berzs"),
    (3, "Pēteris Kalns", "Partija B", "peteris_kalns"),
]


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def _seed_x(db_path):
    init_db(db_path)
    init_saeima_tables(db_path)
    db = get_db(db_path)
    doc_id = 10
    for pid, name, party, handle in POLITICIANS:
        db.execute("INSERT INTO tracked_politicians (id,name,party,relationship_type) "
                   "VALUES (?,?,?,'tracked')", (pid, name, party))
        db.execute("INSERT INTO social_accounts (opponent_id,platform,handle,feed_type,active) "
                   "VALUES (?,'twitter',?,'first_party',1)", (pid, handle))
        for k in range(2):
            doc_id += 1
            db.execute(
                "INSERT INTO documents (id,content,content_hash,platform,source_domain,"
                "source_url,scraped_at,published_at) "
                "VALUES (?,?,?,'twitter','x.com',?,'2026-10-10',?)",
                (doc_id, f"{name} tvīts {k}", f"h{doc_id}",
                 f"https://x.com/{handle}/status/{doc_id}", f"2026-10-10T0{k + 8}:00:00"))
            db.execute("INSERT INTO document_politicians (document_id,politician_id,role) "
                       "VALUES (?,?,'subject')", (doc_id, pid))
    db.commit()
    return db


def _tensions():
    def t(src, tgt, src_party, ttype):
        return {"source_name": src, "target_name": tgt, "source_party": src_party,
                "target_party": "", "tension_type": ttype, "type_lv": ttype.title(),
                "source_slug": "a", "target_slug": "b", "topic": "Ekonomika",
                "description": "Apraksts", "date": "2026-10-10"}
    return [
        t("Anna Ozola", "Jānis Bērzs", "Partija A", "uzbrukums"),
        t("Jānis Bērzs", "Pēteris Kalns", "Partija A", "spriedze"),
        t("Pēteris Kalns", "Anna Ozola", "Partija B", "atbalsts"),
    ]


def _exercise(page, *, first, second, option, label, item, all_label, selection_on):
    """Atver → atlasa → filtrē → otrs saraksts aizver pirmo → klikšķis ārpusē
    aizver → notīrīšana atjauno etiķeti un visas rindas."""
    total = page.evaluate(VISIBLE, item)
    assert total >= 3, f"{item}: fikstūrā tikai {total} rindas — vārti nevar krist"

    page.click(f"{first} {option[0]}")  # trigger
    assert "open" in page.get_attribute(first, "class")

    page.click(f'{first} {option[1]}[data-value="{option[2]}"]')
    assert "selected" in page.get_attribute(
        f'{first} {option[1]}[data-value="{option[2]}"]', "class")
    assert page.text_content(f"{first} {label}").strip() == option[2]
    assert "has-selection" in page.get_attribute(selection_on, "class")
    shown = page.evaluate(VISIBLE, item)
    assert 0 < shown < total, f"{item}: pēc atlases redzamas {shown} no {total}"

    page.click(f"{second} {option[0]}")
    assert "open" in page.get_attribute(second, "class")
    assert "open" not in page.get_attribute(first, "class"), "otrs saraksts neaizvēra pirmo"

    page.mouse.click(5, 5)
    assert "open" not in page.get_attribute(second, "class"), "klikšķis ārpusē neaizvēra"

    page.click(f"{first} {option[0]}")
    page.click(f"{first} {option[3]}")  # clear
    assert page.text_content(f"{first} {label}").strip() == all_label
    assert "has-selection" not in page.get_attribute(selection_on, "class")
    assert page.evaluate(VISIBLE, item) == total


def test_multiselect_open_select_close_clear(tmp_path):
    out = tmp_path / "site"
    out.mkdir()
    env = _env()
    env.globals["_party_short_name"] = _party_short_name
    db = _seed_x(str(tmp_path / "t.db"))
    render_x(env, db, out)
    render_tensions(env, db, out, _tensions())
    shutil.copytree("assets", out / "assets", dirs_exist_ok=True)

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

            page.goto(f"{base}/spriedzes.html")
            _exercise(
                page, first="#person-select", second="#party-select",
                option=(".multi-select-trigger", ".multi-select-option",
                        "Pēteris Kalns", ".multi-select-clear"),
                label=".multi-select-trigger > span:first-child",
                item="#tensions-grid .card", all_label="Visas personas",
                selection_on="#person-trigger")

            page.goto(f"{base}/x.html")
            _exercise(
                page, first="#xv1-persona-select", second="#xv1-party-select",
                option=(".xv1-select-trigger", ".xv1-select-option",
                        "Pēteris Kalns", ".xv1-select-clear"),
                label=".xv1-select-label",
                item="#xv1-feed .xv1-item", all_label="Visas personas",
                selection_on="#xv1-persona-select")

            assert errors == [], errors
            browser.close()
    finally:
        server.shutdown()


def test_bill_topic_select_updates_label(tmp_path):
    """Likumprojektu tēmu filtrs (``likumprojekti.html``, ``#bill-topic-select``)
    bija vienīgais roku rakstītais dropdown: etiķete palika «Visas tēmas», lai ko
    atlasītu. Tagad tas iet caur ``msv1.js`` kā pārējie — un atlase arī filtrē."""
    from src.render.bills import render_bills_index

    out = tmp_path / "site"
    out.mkdir()
    bills = [dict(id=i, document_nr=f"{i}/Lp14", slug=f"{i}-lp14", bill_type="Lp14",
                  title=f"Likums {i}", summary=None, topic=t, current_stage="iesniegts",
                  stage_label="iesniegts", current_status="procesā", bucket="iesniegts", law=None,
                  institutional_submitter=None, submitter_count=0, first_seen_at="2026-05-01")
             for i, t in enumerate(["Ekonomika", "Izglītība", "Veselība"], 1)]
    render_bills_index(_env(), bills, 0, out)
    shutil.copytree("assets", out / "assets", dirs_exist_ok=True)

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
            page.goto(f"{base}/likumprojekti.html")

            root, label = "#bill-topic-select", "#bill-topic-trigger > span:first-child"
            page.click("#bill-topic-trigger")
            assert "open" in page.get_attribute(root, "class")
            page.click(f'{root} .multi-select-option[data-value="Izglītība"]')
            assert page.text_content(label).strip() == "Izglītība"
            assert "has-selection" in page.get_attribute("#bill-topic-trigger", "class")
            assert page.inner_text("#bills-count") == "Rāda 1 no 3"

            page.mouse.click(5, 5)
            assert "open" not in page.get_attribute(root, "class"), "klikšķis ārpusē neaizvēra"

            page.click("#bill-topic-trigger")
            page.click(f"{root} .multi-select-clear")
            assert page.text_content(label).strip() == "Visas tēmas"
            assert page.inner_text("#bills-count") == "Rāda 3 no 3"
            assert errors == [], errors
            browser.close()
    finally:
        server.shutdown()


def test_spriedzes_names_fourth_tension_type(tmp_path):
    """``politikas nostāju konflikts`` (9 rindas DB) bija bez etiķetes filtrā un
    bez žetona krāsas kartītē — lasītājs redzēja izejas vērtību."""
    out = tmp_path / "site"
    out.mkdir()
    env = _env()
    env.globals["_party_short_name"] = _party_short_name
    db = _seed_x(str(tmp_path / "t.db"))
    rows = _tensions()
    rows[0] = dict(rows[0], tension_type="politikas nostāju konflikts",
                   type_lv="Politikas nostāju konflikts")
    render_tensions(env, db, out, rows)
    html = (out / "spriedzes.html").read_text(encoding="utf-8")
    assert "Nostāju konflikts" in html
    assert 'badge badge-blue' in html or 'badge-blue' in html
    assert ">politikas nostāju konflikts<" not in html


def test_fourth_tension_type_named_on_saites_and_profile(tmp_path):
    """Saites lapas panelis (sav1.js) un profila mini-grafs agrāk paši kartēja
    3 tipus — ceturtais gāja neapstrādāts. Tagad abi lasa ``TENSION_TYPE_LV``."""
    import json
    import re

    from src.render.links import render_links
    from src.render.politicians_tabs import _fetch_saites_for_profile

    out = tmp_path / "site"
    out.mkdir()
    env = _env()
    db = _seed_x(str(tmp_path / "t.db"))
    rows = _tensions()
    rows[0] = dict(rows[0], tension_type="politikas nostāju konflikts")
    render_links(env, db, out, rows)
    html = (out / "saites.html").read_text(encoding="utf-8")
    data = json.loads(re.search(
        r'<script type="application/json" id="saites-data">(.*?)</script>', html, re.S).group(1))
    assert data["tensionLabels"]["politikas nostāju konflikts"] == "Nostāju konflikts"
    assert data["tensionBadges"]["politikas nostāju konflikts"] == "badge-blue"

    tension = {"tension_type": "politikas nostāju konflikts", "source_pid": 1,
               "target_pid": 2, "source_name": "Anna Ozola", "target_name": "Jānis Bērzs",
               "source_party": "Partija A", "target_party": "Partija A"}
    saites = _fetch_saites_for_profile(db, 1, "politician", [tension], [])
    n = saites["mini_graph"]["neighbors"][0]
    assert n["type_label"] == "Nostāju konflikts"
    assert n["link_class"] == "konflikts"
