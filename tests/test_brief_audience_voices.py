"""Audience voices belong in the daily brief's topic tables (operator, 2026-08-03).

`briefs.py` excluded `journalist` / `influencer` / `neutral` / `organization`
from the topic-table queries. On 2026-07-31 that silently dropped 11 of 50
positions — including all four Valsts kontrole audit findings, plus LDDK and
several commentators — and brief-writer re-added the rows by hand. It is the T7
mechanism (loss by construction) on the `relationship_type` axis rather than the
topic axis, and it contradicted seeding.md's Institucionālā balss convention:
Valsts kontrole's audit finding is exactly the content the entity was seeded to
capture.

Scope of the change, deliberately narrow — only the three queries that build the
topic tables (`by_topic` ranking, per-topic `samples`, `Pārējās tēmas`
`rest_rows`) plus the DIENAS STATS counter that must agree with them. NOT
changed: the Aktīvākie leaderboard (a politician ranking), the cross-party
narrative hint (party-based, and audience accounts carry no party), the
Koalīcija vs Opozīcija table (which already handles audience explicitly via its
disjoint Neitrāli row), and the weekly / telegram briefs (separate surfaces).

`inactive` stays excluded everywhere — it hides sentinel and retired rows and is
not an audience type.
"""
from __future__ import annotations

import os
import re
import sqlite3
import tempfile

import pytest

from src.briefs import generate_daily_brief

DAY = "2026-08-03"


def _safe_unlink(path):
    try:
        os.unlink(path)
    except PermissionError:
        pass


@pytest.fixture
def db(tmp_path):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    con = sqlite3.connect(path)
    con.executescript("""
        CREATE TABLE documents (id INTEGER PRIMARY KEY, scraped_at TEXT, platform TEXT);
        CREATE TABLE tracked_politicians (id INTEGER PRIMARY KEY, name TEXT, party TEXT, relationship_type TEXT);
        CREATE TABLE claims (id INTEGER PRIMARY KEY, opponent_id INTEGER, topic TEXT, stance TEXT,
                             source_url TEXT, stated_at TEXT, created_at TEXT, salience REAL,
                             claim_type TEXT NOT NULL DEFAULT 'position');
        CREATE TABLE contradictions (id INTEGER PRIMARY KEY, opponent_id INTEGER, claim_old_id INTEGER,
                             claim_new_id INTEGER, topic TEXT, severity TEXT, summary TEXT,
                             detected_at TEXT, confirmed INTEGER DEFAULT 1);
        CREATE TABLE context_notes (id INTEGER PRIMARY KEY, note_type TEXT, content TEXT, topic TEXT, created_at TEXT);
        CREATE TABLE political_tensions (id INTEGER PRIMARY KEY, source_pid INTEGER, target_pid INTEGER,
                             tension_type TEXT, topic TEXT, description TEXT, source_url TEXT, created_at TEXT);
        CREATE TABLE parties (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, short_name TEXT, coalition_status TEXT);
        CREATE TABLE saeima_votes (id INTEGER PRIMARY KEY, vote_date TEXT);
    """)
    con.execute("INSERT INTO parties (name, short_name, coalition_status) VALUES ('JV','JV','coalition')")
    con.executemany(
        "INSERT INTO tracked_politicians (id, name, party, relationship_type) VALUES (?,?,?,?)",
        [
            (1, "Elektu Politiķis", "JV", "tracked"),
            (2, "Valsts kontrole", None, "organization"),
            (3, "Kritiskais Žurnālists", None, "journalist"),
            (4, "Pensionētais Deputāts", "JV", "inactive"),
        ],
    )
    con.executemany(
        """INSERT INTO claims (id, opponent_id, topic, stance, source_url, stated_at, created_at,
                               salience, claim_type)
           VALUES (?,?,?,?,?,?,?,?, 'position')""",
        [
            (1, 1, "Budžets un finanses", "Atbalsta budžeta grozījumus.",
             "https://lsm.lv/a", DAY, DAY, 0.8),
            # Only speaker on this topic is an institution — the Valsts kontrole shape.
            (2, 2, "Valsts pārvalde", "Ogres novada revīzijā konstatēti pārkāpumi.",
             "https://lrvk.gov.lv/r", DAY, DAY, 0.7),
            (3, 3, "Mediju politika", "Vērtē sabiedrisko mediju finansējuma modeli.",
             "https://nra.lv/z", DAY, DAY, 0.6),
            (4, 4, "Tieslietas", "Neredzama pozīcija no neaktīva profila.",
             "https://x.lv/i", DAY, DAY, 0.9),
        ],
    )
    con.commit()
    con.close()
    yield path
    _safe_unlink(path)


def _table_rows(brief: str) -> list[str]:
    """Markdown body rows of every emitted table (skips headers/separators)."""
    return [
        ln for ln in brief.splitlines()
        if ln.startswith("|") and not ln.startswith("|--") and "| Politiķis |" not in ln
    ]


def test_organization_only_topic_appears_in_the_brief(db):
    """Valsts kontrole's audit finding is the content the entity was seeded for."""
    brief = generate_daily_brief(db_path=db, date=DAY)
    assert "Valsts pārvalde" in brief
    assert "Ogres novada revīzijā" in brief


def test_journalist_position_appears_in_the_brief(db):
    brief = generate_daily_brief(db_path=db, date=DAY)
    assert "Mediju politika" in brief
    assert "sabiedrisko mediju finansējuma" in brief


def test_inactive_politician_stays_excluded(db):
    """`inactive` is not an audience type — it hides sentinels and retired rows."""
    brief = generate_daily_brief(db_path=db, date=DAY)
    assert "Neredzama pozīcija" not in brief
    assert "Pensionētais Deputāts" not in brief


def test_stats_position_count_matches_the_emitted_tables(db):
    """The honesty invariant: the STATS number must equal what the tables show.

    The old code counted organization positions into the STATS total while the
    tables excluded them, so the brief announced more positions than it listed
    (40 vs 47/48 on 2026-07-31) — and journalist/neutral rows were in neither.
    """
    brief = generate_daily_brief(db_path=db, date=DAY)
    stats = re.search(r"DIENAS STATS.*?-->", brief, re.S).group(0)
    declared = int(re.search(r"(\d+) pozīcij", stats).group(1))

    topic_rows = [
        r for r in _table_rows(brief)
        if "| Bloks |" not in r and not r.startswith("| Koalīcija |")
        and not r.startswith("| Opozīcija |") and not r.startswith("| Neitrāli |")
        and not r.startswith("| Bezpartejiskie |") and not r.startswith("| Ārpus Saeimas |")
    ]
    # 3 visible positions (elected + organization + journalist); inactive hidden.
    assert declared == 3
    assert len([r for r in topic_rows if "https" in r or "—" in r]) >= 3


def test_coalition_table_keeps_audience_in_its_own_neutral_row(db):
    """Regression: bloc classification must stay disjoint from audience voices."""
    brief = generate_daily_brief(db_path=db, date=DAY)
    assert "Koalīcija vs Opozīcija" in brief
    neutral_line = [ln for ln in brief.splitlines() if ln.startswith("| Neitrāli |")]
    assert neutral_line, "Neitrāli row missing"
    # Both audience positions land here and nowhere else in the bloc split.
    # Personas rāda ar uzvārdu; institūcijas ar PILNO nosaukumu — "kontrole"
    # viena pati runātāju kolonnā bija BACKLOG kosmētikas defekts (slēgts).
    assert neutral_line[0].startswith("| Neitrāli | 2 |")
    assert "Valsts kontrole (1)" in neutral_line[0]
    assert "Žurnālists (1)" in neutral_line[0]
    assert "Valsts pārvalde" in neutral_line[0]
    assert "Mediju politika" in neutral_line[0]
    koa = [ln for ln in brief.splitlines() if ln.startswith("| Koalīcija |")]
    assert koa and koa[0].startswith("| Koalīcija | 1 |"), "audience leaked into a bloc"


def test_bloc_summary_full_name_for_institutions_surname_for_people():
    """Uzvārda ekstrakcija `name.split()[-1]` institūcijai atstāj sugasvārdu
    ("Valsts kontrole" → "kontrole") — organizācijām jārāda pilnais nosaukums."""
    from src.briefs import _bloc_summary

    rows = [
        {"name": "Valsts kontrole", "party": None, "topic": "Valsts pārvalde",
         "relationship_type": "organization"},
        {"name": "Anna Kalniņa", "party": None, "topic": "Veselība",
         "relationship_type": "journalist"},
    ]
    cnt, _parties, people, _topics = _bloc_summary(rows, show_parties=False)
    assert cnt == 2
    items = [p.strip() for p in people.split(",")]
    assert "Valsts kontrole (1)" in items
    assert "kontrole (1)" not in items
    assert "Kalniņa (1)" in items


def test_active_politicians_ordering_is_deterministic():
    """`Aktīvākie politiķi` nedrīkst kārtot pēc seedošanas svaiguma.

    Ar `ORDER BY cnt DESC` vien neizšķirtos (parastā dienā to ir vairākums)
    šķīra `GROUP BY p.id` secība, tāpēc 2026-08-07 viena partija ieņēma 3 no 7
    rindām ar 4 no 18 pozīcijām. Vaicājumam jānes `p.name` kā otrais kritērijs.
    """
    import re
    from pathlib import Path

    src = Path(__file__).resolve().parents[1] / "src" / "briefs.py"
    text = src.read_text(encoding="utf-8")
    # Vaicājums ar relationship_type izslēgšanu ir "Aktīvākie politiķi" bloks.
    block = re.search(
        r"FROM claims c\s+JOIN tracked_politicians p ON c\.opponent_id = p\.id"
        r".*?LIMIT 7",
        text,
        flags=re.DOTALL,
    )
    assert block, "neatradu Aktīvākie politiķi vaicājumu — tests jāatjaunina"
    assert "ORDER BY cnt DESC, p.name ASC" in block.group(0), (
        "trūkst deterministiska tie-break: " + block.group(0)[-120:]
    )


def test_bloc_summary_disambiguates_shared_surname():
    """Divi DAŽĀDI cilvēki ar vienu uzvārdu vienā blokā nedrīkst saplūst.

    2026-08-07 dienas pārskatā "Bez Saeimas frakcijas" rindā stāvēja
    "Hermanis (1), Hermanis (1)" — Alvis (id=29) un Jānis (id=13), abi MMN,
    tāpēc arī partijas tags tos nešķīra. Kolīzijas gadījumā jārāda pilnais
    vārds; nekolidējošiem uzvārds paliek.
    """
    from src.briefs import _bloc_summary

    rows = [
        {"name": "Alvis Hermanis", "party": "MMN", "topic": "Vēlēšanas",
         "relationship_type": "tracked"},
        {"name": "Jānis Hermanis", "party": "MMN", "topic": "Veselības aprūpe",
         "relationship_type": "tracked"},
        {"name": "Andris Velps", "party": "ASL", "topic": "Aizsardzība un drošība",
         "relationship_type": "tracked"},
        {"name": "Andris Velps", "party": "ASL", "topic": "Imigrācija",
         "relationship_type": "tracked"},
    ]
    _cnt, _parties, people, _topics = _bloc_summary(rows)
    items = [p.strip() for p in people.split(",")]
    assert "Alvis Hermanis (1)" in items
    assert "Jānis Hermanis (1)" in items
    assert "Hermanis (1)" not in items
    # Unikāls uzvārds paliek uzvārds — labojums nedrīkst pārtaisīt visu tabulu.
    assert "Velps (2)" in items
