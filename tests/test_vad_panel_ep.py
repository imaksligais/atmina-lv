"""Deklarāciju cilne: EP deputāta piezīme, amata nosaukuma maiņa, meta rinda.

Kļūmes, ko šis tests ķer (Vaideres profils, 2026-10-26):
- EP deputātam jaunākā VID deklarācija ir 20 gadus veca, un lapa nepaskaidro,
  kāpēc — izskatās pēc datu roba;
- tas pats amats tajā pašā iestādē ar citu nosaukumu («Eiropas Parlamenta
  deputāte» → «Deputāts») rādīts kā «jauns» + «vairs nav»;
- tukša iestāde un trūkstošs publicēšanas datums dod «Deputāts · · … publicēts ?».

Īstais renderētājs, sintētiska DB (produkcijas DB nelasa).
"""
from __future__ import annotations

import re

import pytest


@pytest.fixture(scope="module")
def profiles(tmp_path_factory):
    import src.render._orchestrator as orch
    import src.render.bio as bio
    from src.db import get_db
    from src.render._common import og_render
    from src.vad.schema import init_vad_tables
    from tests.test_ui_basics_one_look import _seed
    from tests.test_vad_render import _insert_declaration

    base = tmp_path_factory.mktemp("vad_ep")
    db_path = str(base / "fixture.db")
    _seed(db_path)
    init_vad_tables(db_path)
    db = get_db(db_path)
    db.execute("UPDATE tracked_politicians SET name='Ieva Eiropiete' WHERE id=1")
    db.execute("UPDATE tracked_politicians SET name='Otra Politiķe' WHERE id=2")
    # pid 1 — EP deputāte: divas deklarācijas, amats tajā pašā iestādē pārdēvēts,
    # iestāde tukša, publicēšanas datuma nav.
    for year, title in ((2004, "Eiropas Parlamenta deputāte"), (2005, "Deputāts")):
        decl = _insert_declaration(db, 1, year, f"ep-{year}", position="Deputāts",
                                   submitted=f"{year + 1}-06-16")
        db.execute("UPDATE vad_declarations SET institution='', published_at=NULL WHERE id=?", (decl,))
        db.execute("INSERT INTO vad_positions(declaration_id, position_title, entity_name, is_individual)"
                   " VALUES (?, ?, 'Eiropas Parlaments', 1)", (decl, title))
    # pid 2 — nav EP deputāte.
    decl = _insert_declaration(db, 2, 2024, "lv-2024")
    db.execute("INSERT INTO vad_positions(declaration_id, position_title, entity_name)"
               " VALUES (?, 'Deputāte', 'Saeima')", (decl,))
    db.commit()
    db.close()
    ep_yaml = base / "ep.yaml"
    ep_yaml.write_text(
        "- politician_id: 1\n  name: Ieva Eiropiete\n  ep_id: 1\n"
        "  source_url: https://www.europarl.europa.eu/meps/lv/1/IEVA_EIROPIETE/home\n"
        "  status: ok\n", encoding="utf-8")
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(bio, "EP_BIO_PATH", ep_yaml)
        mp.setattr(orch, "_download_chart_js", lambda *a, **k: None)
        mp.setattr(orch, "_download_annotation_plugin", lambda *a, **k: None)
        mp.setattr(og_render, "render_og_images", lambda jobs, root: 0)
        orch.generate_public_site(db_path=db_path, output_dir=str(base / "site"), only={"politiki"})
    out = base / "site" / "atmina" / "politiki"
    pages = {key: (out / f"{slug}.html").read_text(encoding="utf-8")
             for key, slug in (("ep", "ieva-eiropiete"), ("lv", "otra-politike"))}
    for html in pages.values():
        assert 'id="tab-deklaracijas"' in html
    return pages


def _panel(html: str) -> str:
    return html[html.index('id="tab-deklaracijas"'):]


def test_ep_deputy_gets_note_with_declarations_link(profiles):
    panel = _panel(profiles["ep"])
    assert "https://www.europarl.europa.eu/meps/lv/1/IEVA_EIROPIETE/declarations" in panel
    assert "4. pantā" in panel
    assert "europarl.europa.eu" not in _panel(profiles["lv"])


def test_renamed_position_same_entity_is_modified_not_new_and_removed(profiles):
    panel = _panel(profiles["ep"])
    newest = panel[:panel.index('class="vad-decl"', panel.index('class="vad-decl"') + 1)]
    assert "vairs nav" not in newest
    assert ">jauns<" not in newest
    assert "mainījies" in newest
    assert "amats: Eiropas Parlamenta deputāte → Deputāts" in newest


def test_meta_line_has_no_empty_parts(profiles):
    for html in profiles.values():
        metas = re.findall(r'class="vad-decl-meta"[^>]*>(.*?)</div>', html, re.S)
        assert metas
        for m in metas:
            text = " ".join(m.split())
            assert "· ·" not in text and "?" not in text, text
