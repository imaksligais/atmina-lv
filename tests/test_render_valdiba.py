"""valdiba.html — Ministru kabinets ar katra ministra pozīcijām viņa nozarē.

Viens end-to-end tests: īsta DB shēma → render_valdiba() → HTML. Kļūmes, ko tas ķer:
- bijušais ministrs (``role`` = «bijušais …») parādās kā strādājošs;
- nozares skaitā iekļūst citas tēmas pozīcija vai ``saeima_vote`` rinda;
- ministrija bez mūsu datos esoša ministra klusi pazūd no saraksta;
- uzticības balsojuma skaitlis nav tas, kas DB, vai nav saites uz mūsu balsojuma kartīti;
- partijas saīsinājums ved uz neesošu partijas lapu («Bezp.»);
- ministrijas rindai nav enkura, uz kuru ved saeima.html bloks «Valdība».
"""

from __future__ import annotations

import re

from src.db import get_db, init_db
from src.render._orchestrator import _make_env
from src.render.valdiba import render_valdiba
from src.saeima.schema import init_saeima_tables

VOTE_URL = "https://titania.saeima.lv/LIVS15/SaeimaLIVS2_DK.nsf/0/test?OpenDocument"


def _seed(path: str):
    init_db(path)
    init_saeima_tables(path)
    db = get_db(path)
    pols = [
        (1, "Andris Kalns", "Apvienotais saraksts", "Ministru prezidents"),
        (2, "Ilze Lauka", "Nacionālā apvienība", "Labklājības ministre"),
        (3, "Juris Vecais", "Apvienotais saraksts", "Saeimas deputāts, bijušais Finanšu ministrs"),
        (4, "Pēteris Biedrs", "Apvienotais saraksts", "Ministru prezidenta biedrs"),
        (5, "Māris Brīvais", "Bezpartejisks", "Satiksmes ministrs"),
    ]
    # Partijas lapa ir tikai `parties` rindām — šeit tikai NA.
    db.execute("INSERT INTO parties (name, short_name) VALUES ('Nacionālā apvienība', 'NA')")
    for pid, name, party, role in pols:
        db.execute(
            "INSERT INTO tracked_politicians (id,name,party,role,relationship_type) "
            "VALUES (?,?,?,?,'tracked')", (pid, name, party, role))
    claims = [
        # (opponent, topic, claim_type, stance, stated_at)
        (2, "Sociālā politika", "position", "Atbalsta pabalsta celšanu", "2026-11-10"),
        (2, "Pensijas", "position", "Iebilst pret pensiju vecuma celšanu", "2026-10-01"),
        (2, "Izglītība", "position", "Par skolu tīklu", "2026-11-12"),
        (2, "Sociālā politika", "saeima_vote", "Par: likumprojekts", "2026-11-11"),
        (1, "Budžets un finanses", "position", "Par budžeta disciplīnu", "2026-11-14"),
    ]
    for i, (pid, topic, ctype, stance, day) in enumerate(claims):
        db.execute(
            "INSERT INTO claims (opponent_id,topic,stance,claim_type,source_url,stated_at) "
            "VALUES (?,?,?,?,?,?)",
            (pid, topic, stance, ctype, f"https://www.lsm.lv/raksts/{i}", day))
    db.execute(
        "INSERT INTO saeima_votes (motif,vote_date,vote_time,total_par,total_pret,"
        "total_atturas,total_nebalso,result,url) VALUES (?,?,?,?,?,?,?,?,?)",
        ("Uzticības izteikšana Ministru kabinetam", "2026-11-17", "16:05:00",
         51, 40, 0, 0, "Pieņemts", VOTE_URL))
    db.commit()
    return db


def _row(html: str, ministry: str) -> str:
    """Viena ministrijas rinda (<details> bloks), ko atrod pēc amata nosaukuma."""
    for m in re.finditer(r'<(details|div) class="vld-row[^"]*".*?</\1>', html, re.S):
        if ministry in m.group(0):
            return m.group(0)
    raise AssertionError(f"nav rindas: {ministry}")


def test_valdiba_page_lists_cabinet_with_portfolio_positions(tmp_path):
    db = _seed(str(tmp_path / "t.db"))
    out = tmp_path / "atmina"
    out.mkdir()

    render_valdiba(_make_env(), db, out)
    html = (out / "valdiba.html").read_text(encoding="utf-8")

    # Uzticības balsojums: skaitlis no DB, saite uz MŪSU balsojuma kartīti.
    assert ">51<" in html, "uzticības balsojuma «par» skaitlis nav lapā"
    vote_id = db.execute("SELECT id FROM saeima_votes").fetchone()[0]
    assert f'href="balsojumi.html#vote-{vote_id}"' in html, "nav saites uz balsojuma kartīti"
    assert VOTE_URL not in html, "galvene joprojām ved uz ārējo Saeimas vietni"

    # Partijas saīsinājums ved uz partijas lapu tikai tad, ja tāda lapa ir.
    assert 'href="partijas/na.html">NA</a>' in _row(html, "Labklājības ministr")
    sat = _row(html, "Satiksmes ministr")
    assert "Bezp." in sat and "partijas/" not in sat, "bezpartejiskajam saite uz neesošu lapu"

    # Labklājības ministre: nozarē 2 pozīcijas (Sociālā politika + Pensijas);
    # Izglītība un saeima_vote nav nozarē.
    lab = _row(html, "Labklājības ministr")
    assert "Ilze Lauka" in lab
    assert 'data-count="2"' in lab, "nozares pozīciju skaits nav 2"
    assert "Atbalsta pabalsta celšanu" in lab
    assert "Par skolu tīklu" not in lab, "citas nozares pozīcija rindā"
    assert "politiki/ilze-lauka.html" in lab
    assert lab.startswith('<details class="vld-row" id="labklajibas-ministrija"'), "rindai nav enkura"

    # Bijušais finanšu ministrs nav strādājošs: rinda paliek, bet bez viņa.
    fin = _row(html, "Finanšu ministr")
    assert "Juris Vecais" not in fin, "bijušais ministrs rādīts kā strādājošs"
    assert "Mūsu datos amatā neviena nav" in fin, "ministrija bez ministra pazudusi vai bez paskaidrojuma"

    # Premjera biedrs nav premjers, bet nepazūd: «Citi valdības locekļi».
    assert "Andris Kalns" in _row(html, "Ministru prezident")
    assert "Pēteris Biedrs" not in _row(html, "Ministru prezident"), "premjera biedrs rādīts kā premjers"
    others = html.split("Citi valdības locekļi", 1)
    assert len(others) == 2 and "Pēteris Biedrs" in others[1], "premjera biedrs pazudis no lapas"
    assert "Juris Vecais" not in html, "bijušais ministrs citu locekļu sarakstā"
