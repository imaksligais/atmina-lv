"""Viens balsu skaitīšanas noteikums visām virsmām (`src.scope`).

Kļūme, ko šis tests ķer: «bals.» skaitlis vienam deputātam atšķiras pa lapām,
jo katrs renderētājs savu predikātu raksta pats (2026-10-11 arhitektūras
pārskats § 4: piecas formulas). Noteikums: klātbūtnes stāvokļi
`Reģistrējies`/`Nereģistrējies` nav balsojums (Data Contract 4b); `Nebalsoja`
skaitās (klātesošs, nenobalsoja).

Divi deputāti: A ar 55 Par / 1 Pret / 1 Atturas / 1 Nebalsoja + 2 klātbūtnes
rindām (noteikums: 58), B tikai ar Nebalsoja + 2 klātbūtnes rindām
(noteikums: 1). B ir šķīrējs — virsma, kas izmet `Nebalsoja`, rāda 0.

Profils, Personas un partijas lapa tiek nolasītas no RENDERĒTĀ HTML
(`generate_public_site(only=...)`). Saeimas pusloks, reitingi un bio sargs
tiek nolasīti no datu funkcijām, ko veidnes drukā: to lapām vajag 15. Saeimas
sastāva failus vai visu sākumlapas kompozītu, ko sīka DB nespēj pabarot.

Reitingi apzināti skaita tikai Par/Pret/Atturas (`rankings.py`
docstring) — tā ir otra konvencija, ne kopija; kamēr operators nav izlēmis,
tā virsma ir `xfail(strict=True)`.
"""

from __future__ import annotations

import re
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pytest

from src.scope import CAST_BALLOTS, NOT_ATTENDANCE_SQL

PARTY = "Testa partija"
A_ID, B_ID, C_ID = 901, 902, 903
A_NAME, B_NAME, C_NAME = "Anna Balsotāja", "Bruno Klātesošais", "Cits Vecais"
A_SLUG, B_SLUG, C_SLUG = "anna-balsotaja", "bruno-klatesosais", "cits-vecais"
A_BALLOTS = ["Par"] * 55 + ["Pret", "Atturas", "Nebalsoja", "Reģistrējies", "Nereģistrējies"]
B_BALLOTS = ["Nebalsoja", "Reģistrējies", "Nereģistrējies"]
KNOWN_VOTE_VALUES = {"Par", "Pret", "Atturas", "Nebalsoja", "Reģistrējies", "Nereģistrējies"}


def _build_db(path: str) -> None:
    from src.db import get_db, init_db
    from src.saeima.schema import init_saeima_bills, init_saeima_tables

    init_db(path)
    init_saeima_tables(path)
    init_saeima_bills(path)
    db = get_db(path)
    for ddl in (
        "ALTER TABLE tracked_politicians ADD COLUMN x_handle TEXT",
        "ALTER TABLE documents ADD COLUMN is_paywall BOOLEAN DEFAULT FALSE",
        "ALTER TABLE documents ADD COLUMN summary TEXT",
    ):
        try:
            db.execute(ddl)
        except sqlite3.OperationalError:
            pass
    db.execute(
        "INSERT INTO parties (name, short_name, coalition_status) VALUES (?, 'TP', 'opposition')",
        (PARTY,),
    )
    for pid, name, role in (
        (A_ID, A_NAME, "Saeimas deputāte"),
        (B_ID, B_NAME, "Saeimas deputāts"),
        (C_ID, C_NAME, None),
    ):
        db.execute(
            "INSERT INTO tracked_politicians (id, name, party, role, relationship_type)"
            " VALUES (?, ?, ?, ?, 'opponent')",
            (pid, name, PARTY, role),
        )
    base = date(2026, 1, 5)
    for i in range(len(A_BALLOTS)):
        db.execute(
            "INSERT INTO saeima_votes (id, motif, vote_date, vote_time, result, url)"
            " VALUES (?, ?, ?, '10:00:00', 'Pieņemts', ?)",
            (i + 1, f"Testa likums {i}, 2.lasījums", (base + timedelta(days=i)).isoformat(),
             f"https://example.test/v{i}"),
        )
    ballots = [(i + 1, A_ID, A_NAME, v) for i, v in enumerate(A_BALLOTS)]
    ballots += [(i + 1, B_ID, B_NAME, v) for i, v in enumerate(B_BALLOTS)]
    # C: viens balsojums PIRMS sasaukuma sākuma (fikstūra to pārbīda, sk. zemāk).
    ballots.append((1, C_ID, C_NAME, "Par"))
    db.executemany(
        "INSERT INTO saeima_individual_votes (vote_id, politician_id, deputy_name, vote)"
        " VALUES (?, ?, ?, ?)",
        ballots,
    )
    db.commit()
    db.close()


def _rule_count(db: sqlite3.Connection, pid: int) -> int:
    return db.execute(
        f"SELECT COUNT(*) FROM saeima_individual_votes siv "
        f"WHERE siv.politician_id = ? AND {NOT_ATTENDANCE_SQL}",
        (pid,),
    ).fetchone()[0]


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    """Sīka DB + profila/Personas/partiju renders ar fiksētu pulksteni."""
    from _pytest.monkeypatch import MonkeyPatch
    from freezegun import freeze_time

    from src.render import generate_public_site
    from src.render._common import og_render

    root = tmp_path_factory.mktemp("vote_rule")
    db_path = str(root / "t.db")
    _build_db(db_path)

    def _fake_download(dest, *a, **k):
        Path(dest).write_text("/* stub */", encoding="utf-8")

    def _fake_shoot(todo):
        for out_path, _html in todo:
            Path(out_path).write_bytes(b"png")
            yield out_path

    mp = MonkeyPatch()
    import importlib
    orch = importlib.import_module("src.render._orchestrator")
    for attr in ("_download_chart_js", "_download_annotation_plugin", "_download_d3"):
        if hasattr(orch, attr):
            mp.setattr(orch, attr, _fake_download)
    mp.setattr(og_render, "_shoot", _fake_shoot)
    mp.setenv("ATMINA_ASSETS_VERSION", "test")
    # Sasaukuma sākums pēc C vienīgā balsojuma: C šajā sasaukumā nebalsoja.
    import src.profile_kind as pk
    mp.setattr(pk, "CURRENT_TERM_START", "2026-01-06")
    fixtures = Path(__file__).parent / "fixtures"
    import src.render.personas as _personas
    mp.setattr(_personas, "ELECTED_PATH", fixtures / "cvk_sv2026_ievēlētie.yaml")
    mp.setattr(_personas, "COHORT_PATH", fixtures / "15saeima_kohorta.yaml")
    import src.render.parties as _parties
    mp.setattr(_parties, "ELECTION_RESULTS_PATH", fixtures / "cvk_sv2026_rezultati.yaml")
    try:
        with freeze_time("2026-06-01 12:00:00"):
            generate_public_site(
                db_path=db_path, output_dir=str(root / "out"),
                only={"politiki", "personas", "partijas"},
            )
        db = sqlite3.connect(db_path)
        db.row_factory = sqlite3.Row
        yield {"db": db, "html": root / "out" / "atmina"}
        db.close()
    finally:
        mp.undo()


def _read(site, rel: str) -> str:
    return (site["html"] / rel).read_text(encoding="utf-8")


def test_rule_values_cover_every_known_ballot():
    """SQL forma (NOT IN klātbūtne) un saraksta forma (CAST_BALLOTS) ir viens
    noteikums tikai tad, ja vērtību kopa ir tieši šī; 7. vērtība → izlem."""
    attendance = KNOWN_VOTE_VALUES - set(CAST_BALLOTS)
    assert attendance == {"Reģistrējies", "Nereģistrējies"}
    assert all(f"'{v}'" in NOT_ATTENDANCE_SQL for v in attendance)
    from src.saeima.votes import _BALLOT_VALUES_THAT_ARE_POSITIONS
    assert set(CAST_BALLOTS) == set(_BALLOT_VALUES_THAT_ARE_POSITIONS)


def test_rule_counts(site):
    assert _rule_count(site["db"], A_ID) == 58
    assert _rule_count(site["db"], B_ID) == 1


@pytest.mark.parametrize("pid,slug", [(A_ID, A_SLUG), (B_ID, B_SLUG)])
def test_profile_saeima_tab_count(site, pid, slug):
    html = _read(site, f"politiki/{slug}.html")
    m = re.search(r'id="tab-btn-saeima".*?<span class="pp-tab-count">(\d+)</span>', html, re.S)
    assert m, "Saeimā cilnes skaitlis nav atrasts"
    assert int(m.group(1)) == _rule_count(site["db"], pid)


@pytest.mark.parametrize("pid,name", [(A_ID, A_NAME), (B_ID, B_NAME)])
def test_personas_card_count(site, pid, name):
    html = _read(site, "personas.html")
    card = html[html.index(name):]
    m = re.search(r'pnv1-card-stat-n">([^<]+)</span><span class="pnv1-card-stat-l">bals\.', card)
    assert m
    shown = 0 if m.group(1) == "—" else int(m.group(1))  # veidne 0 rāda kā «—»
    assert shown == _rule_count(site["db"], pid)


@pytest.mark.parametrize("pid,name", [(A_ID, A_NAME), (B_ID, B_NAME)])
def test_party_page_member_count(site, pid, name):
    page = next((site["html"] / "partijas").glob("*.html"))
    html = page.read_text(encoding="utf-8")
    m = re.search(re.escape(name) + r".*?<span>(\d+) bals\.</span>", html, re.S)
    assert m
    assert int(m.group(1)) == _rule_count(site["db"], pid)


def test_saeima_voted_flag(site):
    from src.render.saeima import _fetch_people

    people = _fetch_people(site["db"], [A_NAME, B_NAME])
    assert people[B_NAME]["voted14"] is (_rule_count(site["db"], B_ID) > 0)


def test_bio_mandate_guard(site, tmp_path, monkeypatch):
    """Sargs slēpj teikumu, ja PĒC `since` ir nodota balss pēc noteikuma.
    B vienīgā nodotā balss (Nebalsoja) ir 2026-01-05."""
    import src.render.bio as bio

    y = tmp_path / "m.yaml"
    y.write_text(
        f"entries:\n  - pid: {B_ID}\n    kind: pilnvaras_beidzas\n    since: '2026-01-01'\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(bio, "SAEIMA_MANDATE_PATH", y)
    notes = bio.load_mandate_notes(site["db"], [B_ID])
    assert (B_ID in notes) is (_rule_count(site["db"], B_ID) == 0)


@pytest.mark.xfail(strict=True, reason="Nebalsoja — divas apzinātas konvencijas, C1")
def test_rankings_sample(site):
    from src.render.rankings import _vote_alignment_outliers

    rows = {r["name"]: r for r in _vote_alignment_outliers(site["db"], 10)}
    assert rows[A_NAME]["sample"] == _rule_count(site["db"], A_ID)


def test_profile_kind_uses_current_term(site):
    """Profila tips = tas pats sasaukuma skaits kā Personas/meklētājam
    (`current_term_vote_counts`). C balsoja tikai pirms sasaukuma sākuma."""
    from src.profile_kind import current_term_vote_counts, derive_profile_kind

    want = derive_profile_kind("opponent", None, current_term_vote_counts(site["db"]).get(C_ID, 0))
    assert want == "politician"
    html = _read(site, f"politiki/{C_SLUG}.html")
    assert f'pp-role pp-role-{want}"' in html
