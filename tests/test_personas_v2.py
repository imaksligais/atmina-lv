"""Tests for Personas V2 data helpers in src/generate.py."""

import sqlite3

from src.generate import _fetch_personas, _fetch_personas_metrics, _persona_category


class TestPersonaCategory:
    def test_deputy_when_has_votes(self):
        assert _persona_category(votes_count=5, relationship_type="tracked", party="JV", role="Saeimas deputāts") == "Deputāti"

    def test_journalist(self):
        assert _persona_category(0, "journalist", None, None) == "Žurnālisti"

    def test_influencer(self):
        assert _persona_category(0, "influencer", None, None) == "Ietekmētāji"

    def test_neutral_analyst(self):
        assert _persona_category(0, "neutral", None, None) == "Analītiķi"

    def test_non_saeima_party_member_is_amatpersona(self):
        # Kandidāti kategorija noņemta 2026-04-25 vakarā — non-Saeima
        # partiju biedri tagad arī Amatpersonas.
        assert _persona_category(0, "tracked", "MMN", "Biedrs") == "Amatpersonas"
        assert _persona_category(0, "tracked", "JKP", "JKP līdzpriekšsēdētājs") == "Amatpersonas"

    def test_party_official_without_votes(self):
        assert _persona_category(0, "tracked", "JV", "Ministru prezidente") == "Amatpersonas"

    def test_role_without_party(self):
        # Civil servants / board members land in Amatpersonas (per generate.py comment)
        assert _persona_category(0, "tracked", None, "Valdes priekšsēdētājs") == "Amatpersonas"

    def test_unclassified(self):
        assert _persona_category(0, "tracked", None, None) == "Citi"


def _build_personas_db() -> sqlite3.Connection:
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE tracked_politicians (
            id INTEGER PRIMARY KEY,
            name TEXT,
            party TEXT,
            relationship_type TEXT DEFAULT 'tracked',
            x_handle TEXT,
            role TEXT
        );
        CREATE TABLE parties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            short_name TEXT,
            coalition_status TEXT
        );
        CREATE TABLE claims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            opponent_id INTEGER,
            topic TEXT,
            source_url TEXT,
            stated_at TEXT,
            created_at TEXT,
            claim_type TEXT DEFAULT 'position'
        );
        CREATE TABLE contradictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            opponent_id INTEGER
        );
        CREATE TABLE document_politicians (
            document_id INTEGER,
            politician_id INTEGER,
            role TEXT
        );
        CREATE TABLE social_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            opponent_id INTEGER,
            platform TEXT,
            handle TEXT,
            feed_type TEXT
        );
        CREATE TABLE saeima_votes (id INTEGER PRIMARY KEY, vote_date TEXT, summary TEXT, topic TEXT);
        CREATE TABLE saeima_individual_votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vote_id INTEGER,
            politician_id INTEGER,
            vote TEXT
        );
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_url TEXT,
            scraped_at TEXT,
            published_at TEXT,
            platform TEXT,
            source_domain TEXT
        );
    """)
    db.execute("INSERT INTO parties (name, short_name, coalition_status) VALUES ('Jaunā Vienotība', 'JV', 'coalition')")
    db.execute("INSERT INTO parties (name, short_name, coalition_status) VALUES ('Latvija Pirmajā Vietā', 'LPV', 'opposition')")
    return db


class TestFetchPersonas:
    def test_shape_and_enrichment(self):
        db = _build_personas_db()
        db.execute(
            "INSERT INTO tracked_politicians (id, name, party, x_handle, role) VALUES (1, 'Evika Siliņa', 'Jaunā Vienotība', 'EvikaSilina', 'Ministru prezidente')"
        )
        db.execute("INSERT INTO claims (opponent_id, topic, stated_at) VALUES (1, 'Aizsardzība', '2026-04-17 10:00:00')")
        db.execute("INSERT INTO contradictions (opponent_id) VALUES (1)")
        db.execute("INSERT INTO contradictions (opponent_id) VALUES (1)")
        db.execute("INSERT INTO document_politicians (document_id, politician_id) VALUES (10, 1)")

        personas = _fetch_personas(db)

        assert len(personas) == 1
        p = personas[0]
        assert p["name"] == "Evika Siliņa"
        assert p["slug"] == "evika-silina"
        assert p["party"] == "Jaunā Vienotība"
        assert p["party_short"] == "JV"
        assert p["party_color"] == "#3b82f6"  # JV from PARTY_COLORS
        assert p["coalition_status"] == "coalition"
        assert p["category"] == "Amatpersonas"  # has party, no votes
        assert p["claims_count"] == 1
        assert p["contradictions_count"] == 2
        assert p["docs_count"] == 1
        assert p["votes_count"] == 0
        assert p["x_handle"] == "EvikaSilina"
        assert p["role"] == "Ministru prezidente"
        assert "has_photo" in p
        assert isinstance(p["has_photo"], bool)  # env-dependent; regression guard on key + type

    def test_excludes_inactive(self):
        db = _build_personas_db()
        db.execute(
            "INSERT INTO tracked_politicians (id, name, party, relationship_type) VALUES (1, 'A', 'JV', 'inactive')"
        )
        db.execute(
            "INSERT INTO tracked_politicians (id, name, party, relationship_type) VALUES (2, 'B', 'JV', 'tracked')"
        )
        personas = _fetch_personas(db)
        assert [p["name"] for p in personas] == ["B"]

    def test_coalition_status_unknown_party(self):
        db = _build_personas_db()
        db.execute("INSERT INTO tracked_politicians (id, name, party) VALUES (1, 'X', 'MMN')")
        personas = _fetch_personas(db)
        assert personas[0]["coalition_status"] == "other"
        assert personas[0]["category"] == "Amatpersonas"

    def test_coalition_status_not_in_saeima_collapses_to_other(self):
        # UI bucket: rail shows one 'Bez Saeimas frakcijas' group for both
        # non-Saeima parties (not_in_saeima) and parties absent from the table.
        db = _build_personas_db()
        db.execute(
            "INSERT INTO parties (name, short_name, coalition_status) VALUES ('Suverenā Vara', 'SV', 'not_in_saeima')"
        )
        db.execute("INSERT INTO tracked_politicians (id, name, party) VALUES (1, 'S', 'Suverenā Vara')")
        personas = _fetch_personas(db)
        assert personas[0]["coalition_status"] == "other"

    def test_null_party_is_other(self):
        db = _build_personas_db()
        db.execute(
            "INSERT INTO tracked_politicians (id, name, party, relationship_type, role) VALUES (1, 'Lato Lapsa', NULL, 'neutral', 'Žurnālists')"
        )
        personas = _fetch_personas(db)
        p = personas[0]
        assert p["coalition_status"] == "other"
        assert p["party_short"] == ""
        assert p["category"] == "Analītiķi"

    def test_votes_count_makes_deputy(self):
        db = _build_personas_db()
        db.execute("INSERT INTO tracked_politicians (id, name, party) VALUES (1, 'V', 'Jaunā Vienotība')")
        db.execute("INSERT INTO saeima_votes (id, vote_date, summary) VALUES (1, '2026-04-10', 's')")
        db.execute(
            "INSERT INTO saeima_individual_votes (vote_id, politician_id, vote) VALUES (1, 1, 'Par')"
        )
        personas = _fetch_personas(db)
        assert personas[0]["votes_count"] == 1
        assert personas[0]["category"] == "Deputāti"

    def test_sort_keys_present(self):
        db = _build_personas_db()
        db.execute("INSERT INTO tracked_politicians (id, name, party) VALUES (1, 'A', 'Jaunā Vienotība')")
        db.execute("INSERT INTO claims (opponent_id, topic, stated_at) VALUES (1, 'T', '2026-04-17 10:00:00')")
        personas = _fetch_personas(db)
        p = personas[0]
        # Iso yyyy-mm-dd for client-side sort; empty string sorts last naturally
        assert p["last_activity_iso"] == "2026-04-17"


class TestFetchPersonasMetrics:
    def test_empty(self):
        personas: list[dict] = []
        m = _fetch_personas_metrics(personas)
        assert m == {"total": 0, "deputies": 0, "with_contradictions": 0, "coalition": 0, "opposition": 0}

    def test_counts(self):
        # 2026-04-25: with_contradictions ir TOTAL pretrunu summa (matchojas
        # ar pretrunas.html headline), nevis personu skaits ar ≥1 pretrunām.
        # Iepriekš asserted '3' (=3 personas ar contradictions); tagad '6'
        # (=2+0+1+3+0). Lasītāji 6 versus 11 pretrunām atšķirību lasīja kā bug.
        personas = [
            {"category": "Deputāti", "contradictions_count": 2, "coalition_status": "coalition"},
            {"category": "Deputāti", "contradictions_count": 0, "coalition_status": "coalition"},
            {"category": "Amatpersonas", "contradictions_count": 1, "coalition_status": "coalition"},
            {"category": "Deputāti", "contradictions_count": 3, "coalition_status": "opposition"},
            {"category": "Žurnālisti", "contradictions_count": 0, "coalition_status": "other"},
        ]
        m = _fetch_personas_metrics(personas)
        assert m == {
            "total": 5,
            "deputies": 3,
            "with_contradictions": 6,  # 2+0+1+3+0
            "coalition": 3,
            "opposition": 1,
        }
