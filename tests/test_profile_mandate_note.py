"""Saeimā cilnes mandāta piezīme — end-to-end caur render_politicians.

Plāns: docs/plans/2026-10-09-saeima-mandata-piezime.md. Nosauktā kļūme: bez
teikuma lasītājs, redzot, ka ministra balsojumi beidzas maijā, var domāt, ka
trūkst datu vai ka politiķis neiet uz darbu. Sargs: ja pēc ``since`` ir nodota
balss (15. Saeimā atgriezies deputāts), teikums vairs nav patiess → slēpj un
ziņo stderr (Silent success).
"""
from src.db import get_db, init_db
from src.render.politicians import render_politicians
from src.saeima.schema import init_saeima_tables
from tests.test_render_own_pubs import _env, _politician

SENTENCE = ("Ir iekšlietu ministrs. Deputāta mandātu nolika 04.06.2026 uz amata laiku, "
            "tāpēc Saeimā nebalso.")

MANDATE_YAML = """\
entries:
  - pid: 6
    name: Jānis Dombrava
    kind: ministrs
    since: "2026-06-04"
    office: iekšlietu ministrs
    source_url: https://example.lv/avots
"""


def _render(tmp_path, monkeypatch, vote_dates):
    db_path = str(tmp_path / "t.db")
    init_db(db_path)
    init_saeima_tables(db_path)
    db = get_db(db_path)
    db.execute("INSERT INTO tracked_politicians (id, name, relationship_type) "
               "VALUES (6, 'Jānis Dombrava', 'tracked')")
    for vid, (vote_date, vote) in enumerate(vote_dates, start=1):
        db.execute("INSERT INTO saeima_votes (id, motif, vote_date, vote_time) "
                   "VALUES (?, ?, ?, '10:00')", (vid, f"Likumprojekts {vid}", vote_date))
        db.execute("INSERT INTO saeima_individual_votes (vote_id, deputy_name, vote, politician_id)"
                   " VALUES (?, 'Dombrava Jānis', ?, 6)", (vid, vote))
    db.commit()
    mandate = tmp_path / "saeima_mandats.yaml"
    mandate.write_text(MANDATE_YAML, encoding="utf-8")
    monkeypatch.setattr("src.render.bio.SAEIMA_MANDATE_PATH", mandate)

    out = tmp_path / "site" / "atmina"
    out.mkdir(parents=True)
    render_politicians(_env(), db, out, [_politician(6, "Jānis Dombrava", "janis-dombrava", "deputy")],
                       pid_to_syntheses={})
    html = (out / "politiki" / "janis-dombrava.html").read_text(encoding="utf-8")
    start = html.index('id="tab-saeima"')
    return html[start:html.index('class="profile-tab"', start)]


def test_mandate_note_under_vote_range_in_saeima_tab(tmp_path, monkeypatch):
    # «Nereģistrējies» pēc since nav nodota balss — sargs to neskaita.
    tab = _render(tmp_path, monkeypatch, [("2026-05-20", "Par"), ("2026-06-10", "Nereģistrējies")])

    assert f'<p class="pp-vote-note">{SENTENCE}</p>' in tab
    assert tab.index("Balsojumu ieraksti:") < tab.index(SENTENCE)


def test_mandate_note_hidden_when_cast_vote_after_since(tmp_path, monkeypatch, capsys):
    tab = _render(tmp_path, monkeypatch, [("2026-05-20", "Par"), ("2026-06-10", "Atturas")])

    assert "Balsojumu ieraksti:" in tab  # cilne ir; trūkst tikai teikuma
    assert "uz amata laiku" not in tab
    err = capsys.readouterr().err
    assert "pid 6" in err and "2026-06-10" in err
