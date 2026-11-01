"""Kolektīvo iesniegumu balsojumu polaritāte (backlog/saeima.md [FIX] 2026-10-07).

Nosauktā kļūme: Mandātu, ētikas un iesniegumu komisijas lēmumprojekts skan
«noraidīt iesniegumu», bet `summary` aprakstīja iesnieguma PRASĪBU. Stance
«Iebilst pret: <prasība>» tad tika uzrakstīts tam, kurš balsoja pret
NORAIDĪŠANU — t. i., iesnieguma pusē. Apgriezti 12 balsojumi, divas publicētas
pretrunas atsauktas.

1. tests — lēmumprojekta darbības vārda parsētājs uz īstiem titania tekstiem
   (`.scratch/petitions/drafts.json`, 2026-10-07 nolasījums).
2. tests — ielādes ceļš: `generate_claims_from_votes(petition_decision=…)` +
   Step 5 vārti `petition_votes_polarity()` pēc sēdes datuma.
"""
import pytest

from src.db import get_db, init_db
from src.saeima.schema import init_saeima_tables
from src.saeima.votes import (
    IndividualVote,
    VoteResult,
    generate_claims_from_votes,
    petition_votes_polarity,
    store_vote,
)
from src.saeima.petitions import petition_decision_verb


# Īsti «Lēmumprojekta teksts» fragmenti (sākot ar «nolemj»), saīsināti.
@pytest.mark.parametrize("text, expected", [
    # 937/Lm14 — parastais «noraidīt».
    ("Saeima nolemj: noraidīt 10 946 Latvijas pilsoņu kolektīvo iesniegumu “Par pensiju "
     "2. līmeņa brīvprātīgumu un 6% mazākiem nodokļiem”. Oriģinālais dokumenta saturs 937_Lm14.docx",
     "noraidīt"),
    # 936/Lm14 — lielais burts; virsraksts sākas ar «Nodrošināt» (nedrīkst nolasīt «nodot»).
    ("nolemj: Noraidīt 11 391 Latvijas pilsoņa kolektīvo iesniegumu “Nodrošināt iespēju "
     "brīvprātīgi izņemt 2. pensiju līmeņa uzkrāto kapitālu”. Oriģinālais dokumenta saturs",
     "noraidīt"),
    # 336/Lm14 — numurēts punkts.
    ("nolemj: 1) nodot 15 878 Latvijas pilsoņu kolektīvo iesniegumu “Bankām nepaaugstināt "
     "EURIBOR likmi pagātnē izsniegtiem kredītiem” Saeimas Budžeta un finanšu (nodokļu) komisijai",
     "nodot"),
    # 190/Lm14 — darbības vārds PĒC objekta.
    ("nolemj: 10 315 Latvijas pilsoņu kolektīvo iesniegumu “Par skaidras naudas aprites "
     "normu saglabāšanu” atstāt bez tālākas izskatīšanas. Oriģinālais dokumenta saturs",
     "atstāt bez virzības"),
    # 514/Lm14 — «atstāt … bez turpmākas virzības».
    ("nolemj: atstāt 10 817 Latvijas pilsoņu kolektīvo iesniegumu “Par Latvijas "
     "nepievienošanos pandēmijas līgumam” bez turpmākas virzības. Oriģinālais dokumenta saturs",
     "atstāt bez virzības"),
    # 190/Lm14 forma, bet virsraksts sākas ar «Nodot» — virsraksts stāv PIRMS
    # lēmuma darbības vārda un nedrīkst uzvarēt (sintētisks).
    ("nolemj: 10 000 Latvijas pilsoņu kolektīvo iesniegumu “Nodot ostas zemi "
     "pašvaldībai” atstāt bez tālākas izskatīšanas.",
     "atstāt bez virzības"),
    # Lēmumprojekta pielikums bez «nolemj» (121/Lm14 otrais fails).
    ("Oriģinālais dokumenta saturs 121_pielikums.docx", None),
    ("", None),
])
def test_petition_decision_verb(text, expected):
    assert petition_decision_verb(text) == expected


DEMAND = ('Nodrošināt iespēju brīvprātīgi izņemt 2. pensiju līmeņa uzkrāto kapitālu — '
          '11 391 pilsoņa kolektīvais iesniegums.')
OBJECT = ('Komisijas priekšlikums noraidīt 11 391 pilsoņa kolektīvo iesniegumu "Nodrošināt '
          'iespēju brīvprātīgi izņemt 2. pensiju līmeņa uzkrāto kapitālu".')
MOTIF = ('Par 11 391 Latvijas pilsoņa kolektīvā iesnieguma “Nodrošināt iespēju brīvprātīgi '
         'izņemt 2. pensiju līmeņa uzkrāto kapitālu” turpmāko virzību (936/Lm14)')


@pytest.fixture()
def petition_db(tmp_path, monkeypatch):
    path = str(tmp_path / "p.db")
    init_db(path)
    init_saeima_tables(path)
    monkeypatch.setattr("src.db.DB_PATH", path)
    db = get_db(path)
    db.execute("INSERT INTO tracked_politicians (id, name, party) VALUES (1, 'Test Deputāts', 'JV')")
    db.commit()
    db.close()
    return path


def _ingest(path, summary, decision, *, motif=MOTIF, time="10:00", url="u1"):
    vote = VoteResult(
        motif=motif, date="2026-05-21", time=time,
        total_par=34, total_pret=33, total_atturas=0, total_nebalso=33,
        result="Noraidīts", url=f"https://example.com/{url}",
        individual_votes=[IndividualVote(deputy_name="Test Deputāts", faction="JV",
                                         vote="Pret", politician_id=1)],
    )
    vid = store_vote(vote, db_path=path, summary=summary, document_nr="936/Lm14")
    generate_claims_from_votes(vote, vid, db_path=path, petition_decision=decision)
    return vid


def _gate(path):
    db = get_db(path)
    try:
        return petition_votes_polarity(db, "2026-05-21")
    finally:
        db.close()


def test_reject_draft_with_demand_summary_fails_gate(petition_db):
    vid = _ingest(petition_db, DEMAND, "noraidīt")
    checked, problems = _gate(petition_db)
    assert checked == 1
    assert [(p[0], p[2]) for p in problems] == [(vid, "object_unnamed")]


def test_reject_draft_naming_the_proposal_passes_gate(petition_db):
    _ingest(petition_db, OBJECT, "noraidīt")
    assert _gate(petition_db) == (1, [])
    db = get_db(petition_db)
    stance = db.execute("SELECT stance FROM claims").fetchone()["stance"]
    db.close()
    assert stance.startswith("Iebilst pret: komisijas priekšlikums noraidīt"), stance


def test_missing_decision_and_nodot_with_rejection_wording_fail_gate(petition_db):
    # Agents, kas lēmumprojektu nenolasīja (decision=None), un 973/Lm14 forma:
    # lēmumprojekts «nodot», bet summary «… turpmākā virzība noraidīta».
    a = _ingest(petition_db, OBJECT, None)
    b = _ingest(petition_db, "11 391 pilsoņa kolektīvā iesnieguma turpmākā virzība noraidīta.",
                "nodot", time="11:00", url="u2")
    # Procedurāls apakšbalsojums ar to pašu numuru nav lēmuma balsojums — nav saucējā.
    _ingest(petition_db, "Priekšlikums iekļaut nākamās sēdes darba kārtībā.", None,
            motif="Par iekļaušanu nākamās sēdes darba kārtībā . " + MOTIF,
            time="12:00", url="u3")
    checked, problems = _gate(petition_db)
    assert checked == 2
    assert sorted((p[0], p[2]) for p in problems) == [(a, "decision_missing"),
                                                      (b, "rejection_wording")]
