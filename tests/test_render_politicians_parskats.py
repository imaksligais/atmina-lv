"""Tests for Pārskats cilne data layer (Bloks 2 Commit 1).

Spec: ``docs/superpowers/specs/2026-05-14-profila-parskats-design.md`` § 3.

Covers:
- ``_format_relative_time_lv`` — Latvian relative time phrasing
- ``_top_contradiction_block`` — salience >= 0.5 + confirmed = 1 filter
- ``_dominant_topics_block`` — count >= 3 / 180d threshold
- ``_latest_activity_block`` — position vs vote picker (newer wins)
- ``_build_parskats_data`` — orchestrator omits below-threshold blocks
- ``_profile_tab_set`` — ``parskats`` inclusion gated on ``has_parskats``
"""

import sqlite3
from datetime import date

import pytest

from src.render.politicians import (
    PARSKATS_CONTRADICTION_SALIENCE_MIN,
    PARSKATS_TOPIC_COUNT_MIN,
    _build_parskats_data,
    _dominant_topics_block,
    _format_relative_time_lv,
    _latest_activity_block,
    _profile_tab_set,
    _top_contradiction_block,
)


# ── relative time formatting ────────────────────────────────────────


@pytest.mark.parametrize(
    "iso_date,today,expected",
    [
        ("2026-05-14", date(2026, 5, 14), "šodien"),
        ("2026-05-13", date(2026, 5, 14), "vakar"),
        ("2026-05-12", date(2026, 5, 14), "pirms 2 dienām"),
        ("2026-05-09", date(2026, 5, 14), "pirms 5 dienām"),
        ("2026-05-07", date(2026, 5, 14), "pirms nedēļas"),
        ("2026-04-23", date(2026, 5, 14), "pirms 3 nedēļām"),
        ("2026-04-10", date(2026, 5, 14), "pirms mēneša"),
        ("2026-02-13", date(2026, 5, 14), "pirms 3 mēnešiem"),
        ("2025-05-14", date(2026, 5, 14), "pirms gada"),
        ("2024-05-14", date(2026, 5, 14), "pirms 2 gadiem"),
        ("2026-05-14T18:00:00", date(2026, 5, 14), "šodien"),  # ISO timestamp
        ("", date(2026, 5, 14), ""),
        ("not-a-date", date(2026, 5, 14), ""),
    ],
)
def test_format_relative_time(iso_date, today, expected):
    assert _format_relative_time_lv(iso_date, today) == expected


# ── top contradiction filter ────────────────────────────────────────


def _ct(id, salience, confirmed=1, detected_at="2026-05-01", **extra):
    return {
        "id": id,
        "salience": salience,
        "confirmed": confirmed,
        "detected_at": detected_at,
        "topic": "Drošība",
        "summary": "...",
        "severity": "minor",
        "delta_days": 7,
        **extra,
    }


def test_top_contradiction_salience_boundary_below():
    """salience=0.49 → below threshold (PARSKATS_CONTRADICTION_SALIENCE_MIN=0.5)."""
    assert _top_contradiction_block([_ct(1, 0.49)]) is None


def test_top_contradiction_salience_boundary_at():
    """salience=0.50 → exactly meets threshold."""
    out = _top_contradiction_block([_ct(1, 0.50)])
    assert out is not None
    assert out["id"] == 1


def test_top_contradiction_unconfirmed_dropped():
    """confirmed=0 → dropped even with high salience."""
    assert _top_contradiction_block([_ct(1, 0.85, confirmed=0)]) is None


def test_top_contradiction_picks_highest_salience():
    cts = [_ct(1, 0.51), _ct(2, 0.82), _ct(3, 0.65)]
    out = _top_contradiction_block(cts)
    assert out["id"] == 2


def test_top_contradiction_tie_broken_by_detected_at():
    cts = [
        _ct(1, 0.70, detected_at="2026-04-01"),
        _ct(2, 0.70, detected_at="2026-05-01"),
    ]
    out = _top_contradiction_block(cts)
    assert out["id"] == 2


def test_top_contradiction_null_salience_dropped():
    assert _top_contradiction_block([_ct(1, None)]) is None


def test_top_contradiction_empty_input():
    assert _top_contradiction_block([]) is None


# ── dominant topics ─────────────────────────────────────────────────


def _pos(stated_at, topic):
    return {"stated_at": stated_at, "topic": topic, "stance": "...", "source_url": ""}


def test_dominant_topics_below_count_threshold():
    """count=2 → below PARSKATS_TOPIC_COUNT_MIN=3."""
    today = date(2026, 5, 14)
    positions = [
        _pos("2026-05-10", "Drošība"),
        _pos("2026-05-09", "Drošība"),
    ]
    assert _dominant_topics_block(positions, today) == []


def test_dominant_topics_at_count_threshold():
    today = date(2026, 5, 14)
    positions = [_pos("2026-05-10", "Drošība")] * 3
    out = _dominant_topics_block(positions, today)
    assert out == [{"topic": "Drošība", "count": 3}]


def test_dominant_topics_outside_180d_window_dropped():
    today = date(2026, 5, 14)
    # 181 days ago → outside 180d window
    positions = [_pos("2025-11-14", "Drošība")] * 5
    assert _dominant_topics_block(positions, today) == []


def test_dominant_topics_within_180d_window_kept():
    today = date(2026, 5, 14)
    # 179 days ago → inside window
    positions = [_pos("2025-11-16", "Drošība")] * 3
    out = _dominant_topics_block(positions, today)
    assert out == [{"topic": "Drošība", "count": 3}]


def test_dominant_topics_top_3_only():
    today = date(2026, 5, 14)
    positions = (
        [_pos("2026-05-10", "A")] * 5
        + [_pos("2026-05-10", "B")] * 4
        + [_pos("2026-05-10", "C")] * 3
        + [_pos("2026-05-10", "D")] * 3
    )
    out = _dominant_topics_block(positions, today)
    assert len(out) == 3
    assert [t["topic"] for t in out] == ["A", "B", "C"]


def test_dominant_topics_empty_topic_skipped():
    today = date(2026, 5, 14)
    positions = (
        [_pos("2026-05-10", "")] * 5
        + [_pos("2026-05-10", "Drošība")] * 3
    )
    out = _dominant_topics_block(positions, today)
    assert out == [{"topic": "Drošība", "count": 3}]


# ── latest activity (uses DB for votes) ─────────────────────────────


@pytest.fixture
def db_with_vote_schema():
    """In-memory DB with the minimum schema for _latest_activity_block:
    saeima_individual_votes + saeima_votes (joined for vote_date / topic / motif / url).
    """
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE saeima_individual_votes (
            id INTEGER PRIMARY KEY,
            vote_id INTEGER,
            politician_id INTEGER,
            faction TEXT,
            vote TEXT
        );
        CREATE TABLE saeima_votes (
            id INTEGER PRIMARY KEY,
            vote_date TEXT,
            vote_time TEXT,
            topic TEXT,
            motif TEXT,
            url TEXT
        );
    """)
    return db


def _add_vote(db, vote_id, pid, vote_date, vote="Par", topic="Drošība", motif="Likumprojekts X", url="https://saeima.lv/v/1"):
    db.execute(
        "INSERT INTO saeima_votes (id, vote_date, vote_time, topic, motif, url) VALUES (?,?,?,?,?,?)",
        (vote_id, vote_date, "12:00:00", topic, motif, url),
    )
    db.execute(
        "INSERT INTO saeima_individual_votes (vote_id, politician_id, vote) VALUES (?,?,?)",
        (vote_id, pid, vote),
    )


def test_latest_activity_neither_position_nor_vote(db_with_vote_schema):
    out = _latest_activity_block(db_with_vote_schema, pid=1, positions=[], today=date(2026, 5, 14))
    assert out is None


def test_latest_activity_only_position(db_with_vote_schema):
    positions = [_pos("2026-05-12", "Drošība")]
    positions[0]["stance"] = "Atbalstu X"
    out = _latest_activity_block(db_with_vote_schema, pid=1, positions=positions, today=date(2026, 5, 14))
    assert out["type"] == "position"
    assert out["date"] == "2026-05-12"
    assert out["relative"] == "pirms 2 dienām"
    assert out["topic"] == "Drošība"


def test_latest_activity_only_vote(db_with_vote_schema):
    _add_vote(db_with_vote_schema, vote_id=10, pid=1, vote_date="2026-05-13")
    out = _latest_activity_block(db_with_vote_schema, pid=1, positions=[], today=date(2026, 5, 14))
    assert out["type"] == "vote"
    assert out["date"] == "2026-05-13"
    assert out["relative"] == "vakar"


def test_latest_activity_position_newer_than_vote(db_with_vote_schema):
    _add_vote(db_with_vote_schema, vote_id=10, pid=1, vote_date="2026-05-10")
    positions = [_pos("2026-05-13", "Drošība")]
    positions[0]["stance"] = "Atbalstu X"
    out = _latest_activity_block(db_with_vote_schema, pid=1, positions=positions, today=date(2026, 5, 14))
    assert out["type"] == "position"


def test_latest_activity_vote_newer_than_position(db_with_vote_schema):
    _add_vote(db_with_vote_schema, vote_id=10, pid=1, vote_date="2026-05-13")
    positions = [_pos("2026-05-10", "Drošība")]
    positions[0]["stance"] = "Atbalstu X"
    out = _latest_activity_block(db_with_vote_schema, pid=1, positions=positions, today=date(2026, 5, 14))
    assert out["type"] == "vote"


def test_latest_activity_same_date_position_wins(db_with_vote_schema):
    """Tie → position wins (better content for a Pārskats lead)."""
    _add_vote(db_with_vote_schema, vote_id=10, pid=1, vote_date="2026-05-13")
    positions = [_pos("2026-05-13", "Drošība")]
    positions[0]["stance"] = "Atbalstu X"
    out = _latest_activity_block(db_with_vote_schema, pid=1, positions=positions, today=date(2026, 5, 14))
    assert out["type"] == "position"


# ── _build_parskats_data orchestrator ───────────────────────────────


def test_build_parskats_data_all_empty(db_with_vote_schema):
    """Politiķis bez claims, contradictions un votes → tukšs Pārskats."""
    out = _build_parskats_data(
        db_with_vote_schema, pid=1, positions=[], contradictions=[], today=date(2026, 5, 14)
    )
    assert out == {}


def test_build_parskats_data_only_activity(db_with_vote_schema):
    positions = [_pos("2026-05-13", "Drošība")]
    positions[0]["stance"] = "..."
    out = _build_parskats_data(
        db_with_vote_schema, pid=1, positions=positions, contradictions=[], today=date(2026, 5, 14)
    )
    assert "latest_activity" in out
    assert "top_contradiction" not in out
    assert "dominant_topics" not in out


def test_build_parskats_data_all_three_blocks(db_with_vote_schema):
    positions = (
        [_pos("2026-05-13", "Drošība")] * 3
        + [_pos("2026-05-10", "Drošība")] * 2
    )
    for p in positions:
        p["stance"] = "..."
    contradictions = [_ct(1, 0.70, confirmed=1)]
    out = _build_parskats_data(
        db_with_vote_schema, pid=1, positions=positions, contradictions=contradictions,
        today=date(2026, 5, 14),
    )
    assert "latest_activity" in out
    assert "top_contradiction" in out
    assert "dominant_topics" in out
    assert out["dominant_topics"] == [{"topic": "Drošība", "count": 5}]


# ── _profile_tab_set with has_parskats ──────────────────────────────


def test_profile_tab_set_deputy_with_parskats():
    tabs = _profile_tab_set("deputy", has_parskats=True)
    assert tabs[0] == "parskats"
    assert "timeline" in tabs


def test_profile_tab_set_deputy_without_parskats():
    """No Pārskata → tab_set[0] = 'timeline' (existing default)."""
    tabs = _profile_tab_set("deputy", has_parskats=False)
    assert tabs[0] == "timeline"
    assert "parskats" not in tabs


def test_profile_tab_set_journalist_never_has_parskats():
    """Žurnālisti un analītiķi nesaņem Pārskata cilni neatkarīgi no has_parskats."""
    tabs = _profile_tab_set("journalist", has_parskats=True)
    assert "parskats" not in tabs
    assert tabs[0] == "timeline"


def test_profile_tab_set_organization_never_has_parskats():
    tabs = _profile_tab_set("organization", has_parskats=True)
    assert "parskats" not in tabs


def test_profile_tab_set_inactive_with_parskats():
    """Inactive saņem Pārskatu kā vēsturisku skatu, ja kāds signāls eksistē."""
    tabs = _profile_tab_set("inactive", has_parskats=True)
    assert tabs[0] == "parskats"


def test_profile_tab_set_threshold_constants_exposed():
    """Konstantes ir eksponētas modulē — operatoram pieejamas vienā vietā."""
    assert PARSKATS_CONTRADICTION_SALIENCE_MIN == 0.5
    assert PARSKATS_TOPIC_COUNT_MIN == 3


def test_profile_tab_set_journalist_with_publikacijas_defaults_to_publikacijas():
    """Žurnālistam ar publikācijām default cilne ir Publikācijas, ne Laika līnija
    (spec § 4.1 — risina LETA/LTV/IR empty-timeline-default UX bug).
    """
    tabs = _profile_tab_set("journalist", has_publikacijas=True)
    assert tabs[0] == "publikacijas"


def test_profile_tab_set_journalist_without_publikacijas_defaults_to_timeline():
    tabs = _profile_tab_set("journalist", has_publikacijas=False)
    assert tabs[0] == "timeline"


def test_profile_tab_set_analyst_with_publikacijas_defaults_to_publikacijas():
    tabs = _profile_tab_set("analyst", has_publikacijas=True)
    assert tabs[0] == "publikacijas"


def test_profile_tab_set_organization_with_publikacijas_defaults_to_publikacijas():
    tabs = _profile_tab_set("organization", has_publikacijas=True)
    assert tabs[0] == "publikacijas"


def test_profile_tab_set_organization_with_only_saites_defaults_to_saites():
    """Organizācijai bez publikācijām, bet ar saišu saturu, default ir Saites."""
    tabs = _profile_tab_set("organization", has_publikacijas=False, has_saites_content=True)
    assert tabs[0] == "saites"


def test_profile_tab_set_organization_with_nothing_defaults_to_timeline():
    tabs = _profile_tab_set("organization", has_publikacijas=False, has_saites_content=False)
    assert tabs[0] == "timeline"


def test_profile_tab_set_former_with_parskats_keeps_saeima():
    """Former deputāts ar Pārskatu — Saeimā cilne paliek vēsturiskam arhīvam."""
    tabs = _profile_tab_set("former", has_parskats=True)
    assert tabs[0] == "parskats"
    assert "saeima" in tabs


# ── «Balso kopā ar savu frakciju» (faction_alignment_data) ──────────
# Plāns docs/plans/2026-10-09-parskats-frakcijas-sakritiba.md § Definīcija.


@pytest.fixture
def db_faction():
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE saeima_individual_votes (id INTEGER PRIMARY KEY, vote_id INTEGER,
            politician_id INTEGER, faction TEXT, vote TEXT);
        CREATE TABLE saeima_votes (id INTEGER PRIMARY KEY, vote_date TEXT);
    """)
    return db


def _fv(db, vote_id, rows, vote_date="2023-01-10"):
    """Viens balsojums: rows = [(politician_id, faction, vote), ...]."""
    db.execute("INSERT INTO saeima_votes (id, vote_date) VALUES (?, ?)", (vote_id, vote_date))
    db.executemany(
        "INSERT INTO saeima_individual_votes (vote_id, politician_id, faction, vote) VALUES (?,?,?,?)",
        [(vote_id, pid, faction, vote) for pid, faction, vote in rows],
    )


def test_faction_alignment_uses_per_vote_faction_and_cast_ballots_only(db_faction):
    """Sargā: (a) frakcija ņemta no TĀ balsojuma rindas, ne no deputāta
    «pašreizējās» (T6); (b) ārpusfrakciju balsojums izkrīt; (c) «Nebalsoja»
    neskaitās ne deputātam, ne citiem; (d) «Atturas» pret «Par» = nesakritība;
    (e) balsojumi pirms CURRENT_TERM_START izkrīt; (f) < 20 → nav ieraksta."""
    from src.render._common import faction_alignment_data

    a_par = [(2, "A", "Par"), (3, "A", "Par"), (4, "A", "Par")]
    for v in range(1, 11):  # frakcijā A, sakrīt
        _fv(db_faction, v, [(1, "A", "Par")] + a_par)
    for v in range(11, 20):  # pārgājis uz B, B citi «Pret» → nesakrīt (A citi «Par» nav viņa frakcija)
        _fv(db_faction, v, [(1, "B", "Par"), (5, "B", "Pret"), (6, "B", "Pret"), (7, "B", "Pret")] + a_par)
    # ārpus frakcijas — izkrīt, arī ja citi ārpusfrakciju balso tāpat
    for v, no_faction in ((20, None), (25, "")):
        _fv(db_faction, v, [(p, no_faction, "Pret") for p in (1, 8, 9, 10)] + a_par)
    _fv(db_faction, 21, [(1, "A", "Atturas")] + a_par)  # Atturas pret Par → nesakrīt
    _fv(db_faction, 22, [(1, "A", "Nebalsoja")] + a_par)  # nav nodota balss → izkrīt
    # citu «Nebalsoja» neveido vairākumu: nodotās balsis 3 × Par → sakrīt
    _fv(db_faction, 23, [(1, "A", "Par")] + a_par + [(p, "A", "Nebalsoja") for p in (11, 12, 13, 14)])
    _fv(db_faction, 24, [(1, "A", "Pret")] + a_par, vote_date="2022-10-31")  # 13. Saeima

    out = faction_alignment_data(db_faction)

    # sakrīt: 1–10, 23 = 11; nesakrīt: 11–19, 21 = 10
    assert out == {1: {"pct": 52, "agree": 11, "total": 21, "convocation": 14}}


def test_faction_alignment_majority_excludes_self_skips_ties_and_floors(db_faction):
    """Sargā: (a) deputāts neveido savu vairākumu; (b) < 3 citi balsotāji →
    izkrīt; (c) neizšķirts → izkrīt, nevis nejauši izvēlas pusi; (d) procents
    ir floor — 199 no 200 ir «99 %», nevis noapaļots «100 %» ar nesakritību."""
    from src.render._common import faction_alignment_data

    for v in range(1, 200):
        _fv(db_faction, v, [(1, "A", "Par"), (2, "A", "Par"), (3, "A", "Par"), (4, "A", "Par")])
    # citi 2 Par / 3 Pret → vairākums Pret, nesakrīt; ar sevi būtu 3:3 neizšķirts
    _fv(db_faction, 301, [(1, "A", "Par"), (2, "A", "Par"), (3, "A", "Par"),
                          (4, "A", "Pret"), (5, "A", "Pret"), (6, "A", "Pret")])
    _fv(db_faction, 302, [(1, "A", "Par"), (2, "A", "Pret"), (3, "A", "Pret")])  # tikai 2 citi
    _fv(db_faction, 303, [(1, "A", "Par"), (2, "A", "Par"), (3, "A", "Par"),  # 2:2 neizšķirts
                          (4, "A", "Pret"), (5, "A", "Pret"), (6, "A", "Atturas")])

    out = faction_alignment_data(db_faction)

    assert out[1] == {"pct": 99, "agree": 199, "total": 200, "convocation": 14}


def test_profile_shows_faction_alignment_block(tmp_path):
    """E2E: īsts DB → _fetch_politician_detail → politician.html.j2.
    Sargā, ka skaitlis nonāk lapā ar saucēju un ka bloks pats atver Pārskata
    cilni. Kolēģi bez politician_id (nesaskaņoti) skaitās «citos»."""
    from jinja2 import Environment, FileSystemLoader

    from src.db import get_db, init_db
    from src.render._common import _safe_json_filter, _safe_url_filter
    from src.render.politicians import _fetch_politician_detail
    from src.saeima import init_saeima_tables

    db_path = str(tmp_path / "fa.db")
    init_db(db_path)
    init_saeima_tables(db_path)
    db = get_db(db_path)
    db.execute("INSERT INTO tracked_politicians (name, party) VALUES (?, ?)", ("Ieva Tests", "JV"))
    pid = db.execute("SELECT id FROM tracked_politicians WHERE name='Ieva Tests'").fetchone()["id"]
    for v in range(1, 227):
        db.execute(
            "INSERT INTO saeima_votes (id, motif, vote_date, vote_time, url) VALUES (?, ?, ?, ?, ?)",
            (v, "Likumprojekts X", "2024-03-01", "10:00", f"https://titania.saeima.lv/v/{v}"),
        )
        mine = "Par" if v <= 212 else "Pret"  # 212 no 226 sakrīt
        rows = [("Ieva Tests", pid, mine)] + [(f"Kolēģis {k}", None, "Par") for k in range(3)]
        db.executemany(
            "INSERT INTO saeima_individual_votes (vote_id, deputy_name, politician_id, faction, vote)"
            " VALUES (?, ?, ?, 'JV', ?)",
            [(v, name, p, vote) for name, p, vote in rows],
        )
    db.commit()

    detail = _fetch_politician_detail(db, pid, profile_kind="deputy")
    db.close()
    assert "parskats" in detail["tab_set"]

    env = Environment(loader=FileSystemLoader("templates"))
    env.filters["safe_url"] = _safe_url_filter
    env.filters["safe_json"] = _safe_json_filter
    env.filters["lv_date"] = lambda s: s
    html = env.get_template("politician.html.j2").render(
        politician={"id": pid, "name": "Ieva Tests", "slug": "ieva-tests", "party": "JV",
                    "x_handle": None, "role": None, "profile_kind": "deputy"},
        tab_set=detail["tab_set"], parskats_data=detail["parskats_data"],
        saites_data=detail["saites_data"], bills_involved=detail["bills_involved"],
        timeline=[], positions=[], contradictions=[], votes=[], tensions=[],
        x_posts=[], news=[], commentary_about=[], external_profiles=[], syntheses=[],
        wiki_profile=None, has_photo=False, party_meta=None, claim_topics=[],
    )
    assert "Balso kopā ar savu frakciju" in html
    assert '<h3 class="parskats-headline">93 %</h3>' in html  # floor(93,8); round būtu 94
    assert "212 no 226 balsojumiem 14. Saeimā" in html
