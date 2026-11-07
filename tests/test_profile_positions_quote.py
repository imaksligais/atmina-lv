"""Profila Pozīciju cilne rāda verbatim citātu; Saeimā cilne skaidro «Atturas».

Plāns `docs/plans/2026-07-26-profila-ux-tier2.md` 1. un 3. punkts. Citāts
(`claims.quote`) bija DB un renderī, bet profilā redzams tikai komentāru
blokā — lasītājs neredzēja pierādījumu, uz kā balstīta parafrāze. Citāts ir
VERBATIM: pilns, escapēts, bez pēdiņu ietinuma; bez citāta — nekādas kontroles.
"""
from datetime import date, timedelta

from tests.test_profile_topic_deeplink import _env

from src.db import get_db, init_db
from src.render.politicians import render_politicians
from src.saeima.schema import init_saeima_tables

QUOTE = 'Mēs teicām "nē" <nodoklim> & to arī darīsim'


def _render(tmp_path) -> str:
    db_path = str(tmp_path / "t.db")
    init_db(db_path)
    init_saeima_tables(db_path)
    db = get_db(db_path)
    db.execute("INSERT INTO tracked_politicians (id,name,party,relationship_type) "
               "VALUES (1,'A Kalns','JV','tracked')")
    for i, quote in ((1, QUOTE), (2, None)):
        stated = (date.today() - timedelta(days=i)).isoformat()
        db.execute(
            "INSERT INTO documents (id,content,content_hash,platform,source_domain,"
            "source_url,scraped_at,published_at) VALUES (?,?,?,'web','delfi.lv',?,?,?)",
            (i, f"Teksts {i}", f"h{i}", f"https://delfi.lv/{i}", stated, stated),
        )
        db.execute(
            "INSERT INTO claims (id,opponent_id,document_id,topic,stance,quote,confidence,"
            "source_url,stated_at,claim_type) VALUES (?,1,?,'Nodokļi',?,?,0.9,?,?,'position')",
            (i, i, f"Pozīcija {i}", quote, f"https://delfi.lv/{i}", stated),
        )
    motif = "Grozījumi likumā " + "ļoti garš nosaukums " * 6
    db.execute("INSERT INTO saeima_votes (id,motif,vote_date,vote_time,result) "
               "VALUES (1,?,?,'10:00','pieņemts')", (motif, date.today().isoformat()))
    db.execute("INSERT INTO saeima_individual_votes (vote_id,deputy_name,faction,vote,politician_id) "
               "VALUES (1,'A Kalns','JV','Atturas',1)")
    db.commit()
    out = tmp_path / "site" / "atmina"
    out.mkdir(parents=True)
    render_politicians(_env(), db, out, [{
        "id": 1, "name": "A Kalns", "slug": "a-kalns",
        "profile_kind": "politician", "role_label": "deputāts",
        "party": "JV", "x_handle": None,
    }], pid_to_syntheses={})
    return (out / "politiki" / "a-kalns.html").read_text(encoding="utf-8")


def test_positions_show_verbatim_quote_and_votes_explain_abstention(tmp_path):
    html = _render(tmp_path)
    table = html.split('id="claims-table"', 1)[1].split("</table>", 1)[0]
    rows = {r.split("<td>", 3)[2].split("<", 1)[0].strip(): r
            for r in table.split("<tr ")[1:]}
    with_quote, without = rows["Pozīcija 1"], rows["Pozīcija 2"]
    assert "<details" in with_quote and "<blockquote" in with_quote
    assert "Mēs teicām &#34;nē&#34; &lt;nodoklim&gt; &amp; to arī darīsim" in with_quote
    assert "<details" not in without

    saeima = html.split('id="tab-saeima"', 1)[1]
    assert "pp-vote-note" in saeima
    assert 'title="Atturējās — priekšlikumu neatbalstīja"' in saeima
    # Motīvs griezts uz vārda robežas ar «…», ne vārda vidū.
    cell = saeima.split("<td>", 2)[1].split("</td>", 1)[0]
    assert cell.endswith("…") and cell[:-1].endswith(("nosaukums", "garš", "ļoti"))
