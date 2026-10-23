"""OG kartīte «Vārdi pret darbiem»: `saeima_vote` pusē — balsojums, ne likumprojekta apraksts.

Kļūme, ko tests sargā (2026-10-15, pretruna #56): `saeima_vote` claim stance ir
likumprojekta kopsavilkums (T20 — apzināti), tāpēc kartītes balsojuma pusē
stāvēja «Atbalsta: valdības … jauns likums …», nevis tas, kā politiķis balsoja.
Kartītei jārāda šī politiķa balsis no `saeima_individual_votes` un kopskaits no
`saeima_votes`. «Atturas» ir «Atturējās», nekad «Balsoja «Pret»» (CLAUDE.md).

Ceļš: fikstūras DB → `_fetch_contradictions` → `_og_card_context` → `og-card.html.j2`
(tas pats, ko `_render_og_cards` nodod Playwright).
"""

from __future__ import annotations

import os
import tempfile

import pytest
from jinja2 import Environment, FileSystemLoader

from src.db import get_db, init_db
from src.saeima.schema import init_saeima_bills, init_saeima_tables

VOTE_URL = "https://titania.saeima.lv/LIVS14/SaeimaLIVS2_DK.nsf/0/ABC?OpenDocument"
BILL_SUMMARY = "valdības jauns likums, kas vienuviet regulētu arhitektūras nozari"
MOTIF = "Par likumprojekta atzīšanu par steidzamu. Arhitektūras likums (1549/Lp14), 1.lasījums"


@pytest.fixture
def make_db():
    paths = []

    def _make(ballot: str | None, vote_pid: int = 1, pos_date: str = '2026-09-16'):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        paths.append(path)
        init_db(path)
        init_saeima_tables(path)
        init_saeima_bills(path)
        db = get_db(path)
        db.executescript(f"""
            INSERT INTO parties (id, name, short_name) VALUES (1, 'Jaunā Vienotība', 'JV');
            INSERT INTO tracked_politicians (id, name, party, role, relationship_type)
                VALUES (1, 'Testa Politiķe', 'Jaunā Vienotība', 'Saeimas deputāte', 'tracked'),
                       (2, 'Otrs Deputāts', 'Jaunā Vienotība', 'Saeimas deputāts', 'tracked');
            INSERT INTO documents (id, source_url, title, content, content_hash, platform, scraped_at)
                VALUES (1, 'https://x.com/t/status/1', 'A', 'teksts', 'h1', 'x', '2026-09-16 10:00:00');
            INSERT INTO claims (id, opponent_id, document_id, topic, stance, quote, source_url, stated_at, claim_type)
                VALUES (1, 1, 1, 'Būvniecība', 'Iebilst birokrātijai', 'Nesabojāt ar birokrātiju.',
                        'https://x.com/t/status/1', '{pos_date} 10:00:00', 'position'),
                       (2, {vote_pid}, NULL, 'Būvniecība', 'Atbalsta: {BILL_SUMMARY}', NULL,
                        '{VOTE_URL}', '2026-10-08 10:00:00', 'saeima_vote');
            INSERT INTO saeima_votes (id, motif, vote_date, total_par, total_pret, total_atturas, result, url)
                VALUES (7, '{MOTIF}', '2026-10-08', 47, 8, 18, 'Pieņemts', '{VOTE_URL}');
            INSERT INTO contradictions (id, opponent_id, claim_old_id, claim_new_id, topic, summary,
                                        severity, salience, reviewed, confirmed, detected_at)
                VALUES (56, 1, 1, 2, 'Būvniecība', 'Pretruna', 'minor_shift', 0.5, 1, 1, '2026-10-09 12:00:00');
        """)
        if ballot is not None:
            db.execute(
                "INSERT INTO saeima_individual_votes (vote_id, deputy_name, faction, vote, politician_id)"
                " VALUES (7, 'Deputāts', 'JV', ?, ?)", (ballot, vote_pid))
        db.commit()
        return db

    yield _make
    for p in paths:
        try:
            os.remove(p)
        except OSError:
            pass


def _card_html(db) -> str:
    from src.render.contradictions import _fetch_contradictions, _og_card_context
    env = Environment(loader=FileSystemLoader("templates"), autoescape=True)
    (c,) = _fetch_contradictions(db)
    return env.get_template("og-card.html.j2").render(card=_og_card_context(c), fonts={})


def test_vote_side_shows_ballot_and_totals_not_bill_summary(make_db):
    html = _card_html(make_db("Par"))
    assert "Balsoja «Par»" in html
    assert "(47:8:18)" in html
    assert "Arhitektūras likums (1549/Lp14)" in html
    assert BILL_SUMMARY not in html
    # Pozīcijas puse nemainās.
    assert "«Nesabojāt ar birokrātiju.»" in html


def test_abstention_is_never_called_voting_against(make_db):
    html = _card_html(make_db("Atturas"))
    assert "Atturējās" in html
    assert "Pret»" not in html
    assert "(47:8:18)" in html


def test_unresolved_ballot_falls_back_to_stance(make_db):
    html = _card_html(make_db(None))
    assert BILL_SUMMARY in html
    assert "Balsoja" not in html


def test_non_voting_is_stated_as_recorded(make_db):
    html = _card_html(make_db("Nebalsoja"))
    assert "Nebalsoja" in html
    assert "Balsoja «" not in html
    assert "(47:8:18)" in html


@pytest.mark.parametrize("pos_date", ["2026-09-16", "2026-10-20"])
def test_ballot_comes_from_the_vote_claims_own_politician(make_db, pos_date):
    """Partijas pretruna (`scripts/partiju_pretrunas.py`): pretrunas `opponent_id`
    ir saraksta līderis, bet balsojuma claim pieder citam deputātam — balss
    jāmeklē tam, kura claim tas ir, citādi kartīte atkrīt uz likumprojekta aprakstu.

    Otrais gadījums: pozīcija vēlāka par balsojumu — enrich samaina puses, un
    politiķim jāpārceļas līdzi balsojuma claim."""
    html = _card_html(make_db("Pret", vote_pid=2, pos_date=pos_date))
    assert "Balsoja «Pret»" in html
    assert BILL_SUMMARY not in html
