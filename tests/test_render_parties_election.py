"""partijas.html vēlēšanu bloks: nav YAML → nav bloka (bez kļūdas); LV formāti.

Nosauktās kļūmes: (1) trūkstošs data/cvk_sv2026_rezultati.yaml nogāž visu
partiju renderu; (2) 6,345 % parādās kā «6,34 %» (float apaļošana), un saraksts
ar 0 vietām tiek nosaukts «0 vietas» nevis «0 vietu».
"""

from __future__ import annotations

from src.render.parties import _build_election_context, load_election_results


def test_missing_yaml_means_no_block(tmp_path):
    assert load_election_results(tmp_path / "nav.yaml") is None


def test_context_formats_and_threshold():
    doc = {
        "source_url": "https://dati.cvk.lv/SV2026/velesanu-rezultati/",
        "provisional": True,
        "cvk_updated_at": "2026-10-04 08:22",
        "precincts_counted": 1024, "precincts_total": 1059,
        "eligible_voters": 1557615, "voted": 788154, "turnout_percent": 50.6,
        "seats_total": 100,
        "lists": [
            {"list_nr": 4, "cvk_name": "ZZS", "votes": 35130, "percent": 4.46, "seats": 0, "party_id": 3},
            {"list_nr": 9, "cvk_name": "JV", "votes": 49973, "percent": 6.345, "seats": 100, "party_id": 1},
        ],
    }
    parties = [
        {"id": 1, "name": "Jaunā Vienotība", "short_name": "JV", "color": "#2563eb"},
        {"id": 3, "name": "ZZS", "short_name": "ZZS", "color": None},
    ]
    ctx = _build_election_context(doc, parties)
    assert [r["list_nr"] for r in ctx["rows"]] == [9, 4]  # pēc balsīm
    assert ctx["rows"][0]["percent"] == "6,35 %"
    assert ctx["threshold_index"] == 1
    assert ctx["updated_text"] == "04.10. plkst. 08:22"
    assert ctx["voted"] == "788 154"
    assert parties[1]["election_result"]["seats_text"] == "0 vietu"
    assert ctx["rows"][1]["color"] == "var(--text-muted)"  # partijai nav krāsas



def test_card_names_keep_lv_case_and_order_by_votes(tmp_path, monkeypatch):
    """Nosauktā kļūme: kartītes rādīja angļu Title Case («Apvienotais Saraksts»),
    kamēr tās pašas lapas rezultātu tabula — «Apvienotais saraksts»; kartītes
    gāja `parties.id` secībā, ne pēc vēlēšanu rezultāta."""
    import re

    from jinja2 import Environment, FileSystemLoader

    from src.db import get_db, init_db
    from src.render import parties as parties_mod
    from src.render._common import TEMPLATES_DIR, _party_page_slug
    from src.saeima.schema import init_saeima_tables

    db_path = str(tmp_path / "t.db")
    init_db(db_path)
    init_saeima_tables(db_path)
    db = get_db(db_path)
    db.executemany(
        "INSERT INTO parties (id,name,short_name,coalition_status) VALUES (?,?,?,?)",
        [(1, "Zaļo un Zemnieku savienība", "ZZS", "coalition"),
         (2, "SARAUJ, LATGALE!", "SL", "not_in_saeima"),
         (3, "Apvienotais saraksts", "AS", "coalition")],
    )
    db.commit()
    doc = {
        "source_url": "u", "cvk_updated_at": "2026-10-04 23:08",
        "precincts_counted": 1, "precincts_total": 1, "eligible_voters": 2,
        "voted": 1, "turnout_percent": 50.0, "seats_total": 100,
        "lists": [
            {"list_nr": 4, "cvk_name": "ZZS", "votes": 100, "percent": 4.4, "seats": 0, "party_id": 1},
            {"list_nr": 7, "cvk_name": "AS", "votes": 900, "percent": 35.0, "seats": 41, "party_id": 3},
        ],
    }
    monkeypatch.setattr(parties_mod, "load_election_results", lambda *a, **k: doc)
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)
    env.filters["party_page_slug"] = _party_page_slug
    env.filters["lv_plural"] = lambda n, *a: ""
    env.globals["assets_version"] = "t"
    out = tmp_path / "out"
    out.mkdir()
    parties_mod.render_parties(env, db, out, parties_mod._fetch_parties_page(db))

    html = (out / "partijas.html").read_text(encoding="utf-8")
    cards = re.findall(r'class="party-card-header">\s*<h3>([^<]+)</h3>', html)
    # pēc balsīm (AS 900, ZZS 100), nestartējusī SL beigās; LV reģistrs saglabāts
    assert cards == ["Apvienotais saraksts", "Zaļo un Zemnieku savienība", "Sarauj, Latgale!"]
