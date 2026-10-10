"""Saeimā cilne aktīvam deputātam, kura loma satur «ministr…» — end-to-end.

Nosauktā kļūme (2026-10-07): derive_profile_kind() dod ``minister`` katram,
kura aktīvajā lomā ir «ministr» (piem., «Finanšu ministrijas parlamentārais
sekretārs»), un _profile_tab_set() Saeimā cilni deva tikai ``deputy`` /
``former``. 10 aktīviem deputātiem (Šuvajevam 701 balsojums) cilnes nebija.
Tā pati kind-vārtu kļūda slēpa Saites cilnes balsojumu sakritību; un
klātbūtnes reģistrācija (Data Contract 4b) nav balsojums — ne sarakstā, ne
cilnes skaitlī.
"""
import re
from src.db import get_db, init_db
from src.render.politicians import _fetch_politicians, render_politicians
from src.saeima.schema import init_saeima_bills, init_saeima_tables
from tests.test_render_saeima_activity import _env


def test_minister_kind_with_votes_gets_saeima_tab(tmp_path):
    db_path = str(tmp_path / "t.db")
    init_db(db_path)
    init_saeima_tables(db_path)
    init_saeima_bills(db_path)
    db = get_db(db_path)
    db.execute(
        "INSERT INTO tracked_politicians (id, name, party, role, relationship_type) VALUES "
        "(1, 'Anna Ozola', 'X', 'Finanšu ministre', 'tracked'),"
        "(2, 'Juris Bērzs', 'X', 'Saeimas deputāts', 'tracked')"
    )
    # 10 kopīgi balsojumi — _vote_alignment_for slieksnis sakritībai.
    for vid in range(1, 11):
        motif = "Par likumprojektu" if vid == 1 else f"Par grozījumiem {vid}"
        db.execute("INSERT INTO saeima_votes (id, motif, vote_date, vote_time) "
                   "VALUES (?, ?, '2026-06-05', ?)", (vid, motif, f"10:{vid:02d}"))
        for pid, name in ((1, "Ozola Anna"), (2, "Bērzs Juris")):
            db.execute("INSERT INTO saeima_individual_votes (vote_id, deputy_name, vote, politician_id)"
                       " VALUES (?, ?, 'Par', ?)", (vid, name, pid))
    db.execute("INSERT INTO saeima_votes (id, motif, vote_date, vote_time) "
               "VALUES (99, 'Deputātu klātbūtnes reģistrācija', '2026-06-05', '09:00')")
    db.execute("INSERT INTO saeima_individual_votes (vote_id, deputy_name, vote, politician_id)"
               " VALUES (99, 'Ozola Anna', 'Nereģistrējies', 1)")
    db.commit()

    politicians = _fetch_politicians(db)
    # Priekšnoteikums: bez tā tests ietu cauri pa ``deputy`` ceļu un neko nepierādītu.
    assert politicians[0]["profile_kind"] == "minister"

    out = tmp_path / "site" / "atmina"
    out.mkdir(parents=True)
    render_politicians(_env(), db, out, politicians, pid_to_syntheses={})
    html = (out / "politiki" / "anna-ozola.html").read_text(encoding="utf-8")

    assert 'data-tab="saeima"' in html
    assert "Par likumprojektu" in html
    # «Vēsturisks» piezīme ir tikai ``former`` profiliem.
    assert "Vēsturisks (bijušais deputāts)" not in html
    # Klātbūtnes reģistrācija nav balsojums: nav sarakstā, cilnes skaitlis = 10.
    assert "Deputātu klātbūtnes reģistrācija" not in html
    assert re.search(r'id="tab-btn-saeima"[^>]*>\s*<span class="pp-tab-label">Saeimā</span>'
                     r'<span class="pp-tab-count">10</span>', html)
    # Saites: balsojumu sakritība arī ``minister`` kind profilam ar balsojumiem.
    assert "Visbiežāk balso vienādi" in html and "Juris Bērzs" in html
