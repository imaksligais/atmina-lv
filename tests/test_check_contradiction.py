"""End-to-end test for scripts/check_contradiction.py (pretrunas faktu pārbaude).

Failures named first (both were live on atmina.lv until 2026-11-13):
1. A summary states something the vote table contradicts and still passes —
   «visa frakcija atturējās» when the faction split (#8, #13), or the
   politician's abstention is not mentioned at all.
2. Words in quotation marks that the politician never wrote pass as a quote
   (#37, #34) — or a real quote relayed in another document is refused, which
   would teach the caller to drop the quotation marks.
"""

import json

import pytest

import src.db
from scripts import check_contradiction as cc
from src.db import get_db, init_db
from src.saeima.schema import init_saeima_bills, init_saeima_tables

VOTE_URL = "https://titania.saeima.lv/LIVS14/vote1"
TRUE = (
    "Saeima 26. martā balsoja par uzdevumu valdībai publicēt importētāju sarakstu. Politiķis atturējās. "
    "13. martā viņš rakstīja: «sankciju mīkstināšana būtu milzīga kļūda». "
    "[Konteksts: frakcija sadalījās: seši atturējās, viens balsoja «Par», viens «Pret».]"
)
WRONG_FACTION = TRUE.replace("frakcija sadalījās: seši atturējās, viens balsoja «Par», viens «Pret».", "visa frakcija atturējās.")
WRONG_QUOTE = TRUE.replace("«sankciju mīkstināšana būtu milzīga kļūda»", "«sankcijas jāatceļ nekavējoties»")
RELAYED = TRUE.replace("[Konteksts:", "[Konteksts: 20. martā viņš rakstīja: «publicēt vajag visu».")


@pytest.fixture
def draft(tmp_path, monkeypatch):
    path = str(tmp_path / "t.db")
    init_db(path)
    init_saeima_tables(path)
    init_saeima_bills(path)
    db = get_db(path)
    db.execute("INSERT INTO tracked_politicians (id, name, party) VALUES (1, 'Test Politiķis', 'Partija')")
    db.execute(
        "INSERT INTO documents (id, title, content, content_hash, published_at) VALUES "
        "(10, 'Tvīts', 'Jebkāda sankciju mīkstināšana būtu milzīga kļūda.', 'h10', '2026-03-13T10:00:00Z')"
    )
    # Cita autora retvīts ar paša vārdiem — burtisks citāts, bet ne pretrunas avots.
    db.execute(
        "INSERT INTO documents (id, title, content, content_hash, published_at) VALUES "
        "(11, '', 'RT @test: Manuprāt, publicēt vajag visu.', 'h11', '2026-03-20T10:00:00Z')"
    )
    db.execute("INSERT INTO document_politicians (document_id, politician_id, role) VALUES (11, 1, 'mentioned')")
    db.execute(
        "INSERT INTO saeima_votes (id, motif, vote_date, vote_time, total_par, total_pret, total_atturas, result, url, summary, document_nr) "
        "VALUES (5, 'Par uzdevumu Ministru kabinetam (929/Lm14)', '2026-03-26', '10:00:00', 40, 20, 25, 'Noraidīts', ?, 'Uzdevums publicēt sarakstu.', '929/Lm14')",
        (VOTE_URL,),
    )
    ballots = [("Test Politiķis", "Atturas", 1)] + [(f"Kolēģis {i}", "Atturas", None) for i in range(5)]
    ballots += [("Kolēģis Par", "Par", None), ("Kolēģis Pret", "Pret", None)]
    for name, vote, pid in ballots:
        db.execute(
            "INSERT INTO saeima_individual_votes (vote_id, deputy_name, faction, vote, politician_id) VALUES (5, ?, 'PRO', ?, ?)",
            (name, vote, pid),
        )
    db.execute(
        "INSERT INTO claims (id, opponent_id, document_id, claim_type, topic, stance, quote, source_url, stated_at) VALUES "
        "(101, 1, 10, 'position', 'Ārpolitika', 'Iebilst pret sankciju mīkstināšanu.', "
        "'Jebkāda sankciju mīkstināšana būtu milzīga kļūda.', 'https://x/101', '2026-03-13 10:00:00')"
    )
    db.execute(
        "INSERT INTO claims (id, opponent_id, claim_type, topic, stance, source_url, stated_at) VALUES "
        "(102, 1, 'saeima_vote', 'Ārpolitika', 'Atturas: uzdevums publicēt sarakstu.', ?, '2026-03-26 10:00:00')",
        (VOTE_URL,),
    )
    db.commit()
    db.close()
    monkeypatch.setattr(src.db, "DB_PATH", path)

    def write(summary):
        f = tmp_path / "draft.json"
        f.write_text(json.dumps({
            "opponent_id": 1, "claim_old_id": 101, "claim_new_id": 102, "severity": "minor_shift",
            "headline": "Sankcijas un importētāju saraksts", "summary": summary,
        }, ensure_ascii=False), encoding="utf-8")
        return ["--draft", str(f)]

    return write


def test_summary_that_contradicts_the_vote_table_is_refused(draft, capsys):
    assert cc.main(draft(TRUE)) == 0, capsys.readouterr().out
    sheet = capsys.readouterr().out
    assert "paša balss: Atturas" in sheet and "frakcija PRO: Atturas 6, Par 1, Pret 1" in sheet

    assert cc.main(draft(WRONG_FACTION)) == 1
    assert "KĻŪDA [frakcija]" in capsys.readouterr().out

    assert cc.main(draft(TRUE.replace("Politiķis atturējās. ", "").replace("seši atturējās", "seši nebalsoja «Par»"))) == 1
    assert "teksts atturēšanos nemin" in capsys.readouterr().out


def test_invented_quote_is_refused_and_a_relayed_one_is_only_flagged(draft, capsys):
    assert cc.main(draft(WRONG_QUOTE)) == 1
    assert "KĻŪDA [citāts]" in capsys.readouterr().out

    assert cc.main(draft(RELAYED)) == 0
    out = capsys.readouterr().out
    assert "PĀRBAUDI [citāts]" in out and "dokumentā 11" in out


def test_store_refuses_a_wrong_fact_and_returns_what_the_machine_cannot_judge(draft):
    """3. kļūme: pārbaude ir tikai prompta solis, un aģents zem slodzes to izlaiž —
    kļūdains fakts nonāk DB. Vārtiem jābūt glabāšanas funkcijā."""
    from src import tools

    row = dict(opponent_id=1, old_claim_id=101, new_claim_id=102, topic="Ārpolitika",
               severity="minor_shift", salience=0.4, headline="Sankcijas un importētāju saraksts")
    refused = json.loads(tools.store_contradiction(summary=WRONG_FACTION, **row))
    assert refused["status"] == "error" and "KĻŪDA [frakcija]" in refused["message"]
    db = get_db()
    assert db.execute("SELECT COUNT(*) FROM contradictions").fetchone()[0] == 0
    db.close()

    stored = json.loads(tools.store_contradiction(summary=RELAYED, **row))
    assert stored["status"] == "success", stored
    assert any("PĀRBAUDI [citāts]" in p for p in stored["fact_check"])
