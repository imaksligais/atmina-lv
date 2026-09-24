"""Profila cilņu joslas klaviatūras un fokusa līgums (T3, 2026-09-05).

Josla ir WAI-ARIA ``tablist``: bultas un Home/End pārvieto starp cilnēm, un
tabulācijas secībā ir tikai VIENA cilne (roving tabindex). Šeit pārbaudāms
tas, ko dod Jinja puse — renderētajā HTML tieši viena cilne ir
``tabindex="0"`` un tā pati ir ``aria-selected="true"`` — plus ``ppv1.js``
avota līguma punkti, kas šo stāvokli uztur (bultu taustiņi, tabindex maiņa
kopā ar aria-selected, joslas ritināšana bez lapas lēciena).

Abi profila veidi: politiķis (pilna cilņu kopa) un žurnālists (ierobežota
kopa — ``src/render/politicians.py::_profile_tab_set``).

Renderēšanas fikstūras paterns aizgūts no ``tests/test_profile_topic_deeplink.py``.
"""
import re
from datetime import date, timedelta
from pathlib import Path

from src.db import get_db, init_db
from src.render.politicians import render_politicians
from src.saeima.schema import init_saeima_tables
from tests.test_profile_topic_deeplink import _env

TAB_BUTTON_RE = re.compile(r'<button class="profile-stat[^"]*"[^>]*role="tab"[^>]*>')


def _seed(db_path):
    """Politiķis (id=1) ar pozīcijām + žurnālists (id=2), kas komentē
    politiķi — žurnālista profilam tā ir ``komentari-by`` cilne."""
    init_db(db_path)
    init_saeima_tables(db_path)
    db = get_db(db_path)
    db.execute("INSERT INTO tracked_politicians (id,name,party,relationship_type) "
               "VALUES (1,'A Kalns','JV','tracked')")
    db.execute("INSERT INTO tracked_politicians (id,name,party,relationship_type) "
               "VALUES (2,'B Ozols',NULL,'journalist')")
    for i in range(1, 4):
        stated = (date.today() - timedelta(days=i)).isoformat()
        db.execute(
            "INSERT INTO documents (id,content,content_hash,platform,source_domain,"
            "source_url,scraped_at,published_at) VALUES (?,?,?,'web','delfi.lv',?,?,?)",
            (i, f"Teksts {i}", f"h{i}", f"https://delfi.lv/{i}", stated, stated),
        )
        db.execute(
            "INSERT INTO claims (id,opponent_id,document_id,topic,stance,confidence,"
            "source_url,stated_at,claim_type) VALUES (?,1,?,'Ekonomika',?,0.9,?,?,'position')",
            (i, i, f"Pozīcija {i}", f"https://delfi.lv/{i}", stated),
        )
    stated = (date.today() - timedelta(days=4)).isoformat()
    db.execute(
        "INSERT INTO documents (id,content,content_hash,platform,source_domain,"
        "source_url,scraped_at,published_at) VALUES (9,'Komentārs','h9','web','delfi.lv',"
        "'https://delfi.lv/9',?,?)", (stated, stated),
    )
    db.execute(
        "INSERT INTO claims (id,opponent_id,speaker_id,document_id,topic,stance,confidence,"
        "source_url,stated_at,claim_type) VALUES (9,1,2,9,'Ekonomika','Vērtējums',0.9,"
        "'https://delfi.lv/9',?,'commentary')", (stated,),
    )
    db.commit()
    return db


def _render(tmp_path) -> dict[str, str]:
    db = _seed(str(tmp_path / "t.db"))
    out = tmp_path / "site" / "atmina"
    out.mkdir(parents=True)
    render_politicians(_env(), db, out, [
        {"id": 1, "name": "A Kalns", "slug": "a-kalns",
         "profile_kind": "politician", "role_label": "deputāts",
         "party": "JV", "x_handle": None},
        {"id": 2, "name": "B Ozols", "slug": "b-ozols",
         "profile_kind": "journalist", "role_label": "žurnālists",
         "party": None, "x_handle": None},
    ], pid_to_syntheses={})
    return {
        "politician": (out / "politiki" / "a-kalns.html").read_text(encoding="utf-8"),
        "journalist": (out / "politiki" / "b-ozols.html").read_text(encoding="utf-8"),
    }


def _tab_buttons(html: str) -> list[str]:
    bar = html.split('class="profile-stats-bar"', 1)[1].split("</div>", 1)[0]
    return TAB_BUTTON_RE.findall(bar)


# ── renderētais HTML: roving tabindex + tablist semantika ────────────


def test_exactly_one_tab_in_the_tab_order(tmp_path):
    """Roving tabindex: tieši viena cilne ``tabindex="0"``, pārējās ``-1``.
    Divas nulles nozīmētu, ka Tab taustiņš staigā pa joslu, nevis pāri tai."""
    for kind, html in _render(tmp_path).items():
        btns = _tab_buttons(html)
        assert btns, f"{kind}: cilņu joslā nav nevienas role=tab pogas"
        zeros = [b for b in btns if 'tabindex="0"' in b]
        assert len(zeros) == 1, f"{kind}: tabindex=0 pogu skaits {len(zeros)}"
        assert all('tabindex="-1"' in b for b in btns if b not in zeros)


def test_tab_in_tab_order_is_the_selected_one(tmp_path):
    """Tabulācijā esošā cilne = aktīvā cilne; abas atzīmes vienā pogā."""
    for kind, html in _render(tmp_path).items():
        btns = _tab_buttons(html)
        selected = [b for b in btns if 'aria-selected="true"' in b]
        assert len(selected) == 1, f"{kind}: aria-selected=true skaits {len(selected)}"
        assert 'tabindex="0"' in selected[0], kind
        assert "active" in selected[0], kind


def test_tablist_semantics_survive_for_both_profile_kinds(tmp_path):
    """Katra poga paliek role=tab ar aria-controls; josla — role=tablist.
    Žurnālista kopa ir mazāka, bet ne tukša."""
    pages = _render(tmp_path)
    for kind, html in pages.items():
        assert '<div class="profile-stats-bar" role="tablist"' in html, kind
        for btn in _tab_buttons(html):
            assert "aria-controls=" in btn, f"{kind}: {btn}"
            assert "data-tab=" in btn, f"{kind}: {btn}"
    assert len(_tab_buttons(pages["journalist"])) < len(_tab_buttons(pages["politician"]))


# ── ppv1.js avota līgums ────────────────────────────────────────────


def _ppv1() -> str:
    return Path("assets/ppv1.js").read_text(encoding="utf-8")


def test_ppv1_moves_between_tabs_with_arrows_and_home_end():
    js = _ppv1()
    for key in ('"ArrowRight"', '"ArrowLeft"', '"Home"', '"End"'):
        assert key in js, key
    assert 'addEventListener("keydown"' in js


def test_ppv1_rolls_tabindex_together_with_aria_selected():
    """Ja tabindex netiek pārslēgts līdz ar aria-selected, pēc pirmās
    pārslēgšanas tabulācijas secībā paliktu nepareizā cilne."""
    js = _ppv1()
    assert 'b.setAttribute("tabindex", "-1");' in js
    assert 'btn.setAttribute("tabindex", "0");' in js


def test_ppv1_scrolls_only_the_strip_not_the_page():
    """Aktīvo cilni ieritina, mainot joslas scrollLeft — ``scrollIntoView``
    pavilktu arī lapu, un hash-ielāde telefonā lēktu."""
    js = _ppv1()
    assert "statsBar.scrollLeft +=" in js
    assert ".scrollIntoView(" not in js
    assert "preventScroll: true" in js
