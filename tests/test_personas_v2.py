"""Tests for Personas V2 data helpers in src/render/personas.py."""

import sqlite3

from src.render._common import _persona_category
from src.render.personas import _fetch_personas, _fetch_personas_metrics, _persona_sort_name


class TestPersonaSortName:
    """Alfabētiskā kārtošana pēc UZVĀRDA personām, pilna nosaukuma — orgām."""

    def test_person_flipped_to_surname_first(self):
        assert _persona_sort_name("Juris Viļums", "Deputāti") == "Viļums Juris"
        assert _persona_sort_name("Evika Siliņa", "Valdība") == "Siliņa Evika"

    def test_multi_token_name(self):
        assert _persona_sort_name("Dāvis Mārtiņš Daugavietis", "Deputāti") == "Daugavietis Dāvis Mārtiņš"
        assert _persona_sort_name("Zanda Kalniņa-Lukaševica", "Deputāti") == "Kalniņa-Lukaševica Zanda"

    def test_journalists_and_analysts_are_persons(self):
        assert _persona_sort_name("Lato Lapsa", "Žurnālisti") == "Lapsa Lato"
        assert _persona_sort_name("Filips Rajevskis", "Analītiķi") == "Rajevskis Filips"

    def test_organizations_keep_full_name(self):
        assert _persona_sort_name("Latvijas armija (NBS)", "Iestādes") == "Latvijas armija (NBS)"
        assert _persona_sort_name("LETA", "Mediji") == "LETA"
        assert _persona_sort_name("Krustpunktā", "Mediji") == "Krustpunktā"

    def test_citi_and_single_word_untouched(self):
        # Citi ir jauktā kategorija — konservatīvi bez uzvārda flipa.
        assert _persona_sort_name("Jānis Bērziņš", "Citi") == "Jānis Bērziņš"
        assert _persona_sort_name("Madona", "Deputāti") == "Madona"


class TestPersonaCategory:
    """Pēdējais arguments = current_term_vote_count (derive_profile_kind ievade)."""

    def test_deputy_when_has_votes(self):
        # Balsojumi uzvar lomu, izņemot strādājošu ministru — tas ir «Valdība».
        assert _persona_category(5, "tracked", "JV", "Saeimas deputāts", 5) == "Deputāti"
        assert _persona_category(5, "tracked", "JV", "Aizsardzības ministrs", 5) == "Valdība"

    def test_journalist(self):
        assert _persona_category(0, "journalist", None, None, 0) == "Žurnālisti"

    def test_influencer(self):
        assert _persona_category(0, "influencer", None, None, 0) == "Ietekmētāji"

    def test_neutral_analyst(self):
        assert _persona_category(0, "neutral", None, None, 0) == "Analītiķi"

    def test_role_groups_follow_profile_kind(self):
        # Bijušās «Amatpersonas» (2026-10-07) sadalītas pēc derive_profile_kind.
        assert _persona_category(0, "tracked", "JV", "Ministru prezidente", 0) == "Valdība"
        assert _persona_category(0, "tracked", None, "Valsts prezidents", 0) == "Citi politiķi"
        assert _persona_category(0, "tracked", "NA", "EP deputāts", 0) == "EP deputāti"
        assert _persona_category(0, "tracked", None, "Rīgas domes priekšsēdētājs", 0) == "Pašvaldības"
        assert _persona_category(0, "tracked", "MMN", "Biedrs", 0) == "Citi politiķi"
        assert _persona_category(0, "tracked", None, "Bijušais labklājības ministrs", 0) == "Citi politiķi"

    def test_attendance_only_is_not_deputy(self):
        # Tikai klātbūtnes ieraksti (votes_count=0, termiņa skaits > 0): Deputāti
        # noteikums nemainās, profile_kind 'deputy' iet «Citi politiķi».
        assert _persona_category(0, "tracked", "JV", "Biedrs", 3) == "Citi politiķi"

    def test_unclassified(self):
        assert _persona_category(0, "tracked", None, None, 0) == "Citi"


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
            opponent_id INTEGER,
            confirmed INTEGER
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
        assert p["category"] == "Valdība"  # ministru prezidente, no votes
        assert p["claims_count"] == 1
        assert p["contradictions_count"] == 2
        assert p["docs_count"] == 1
        assert p["votes_count"] == 0
        assert p["x_handle"] == "EvikaSilina"
        assert p["role"] == "Ministru prezidente"
        assert p["sort_name"] == "Siliņa Evika"
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
        assert personas[0]["category"] == "Citi politiķi"

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
            {"category": "Valdība", "contradictions_count": 1, "coalition_status": "coalition"},
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


class TestSaeima15Flags:
    """personas.html «15. Saeima» rails.

    Nosauktā kļūme: kartīte netiek atzīmēta (vai atzīmēta ne tā) pēc datu
    failiem, vai raila skaitlis atšķiras no atzīmēto kartīšu skaita — lasītājs
    klikšķina «Ievēlētie (N)» un redz citu skaitu. Otra kļūme: ievēlēts bez
    balsojumiem paliek savā lomu grupā, nevis «Deputāti». Trešā: lomu grupas (Valdība /
    EP deputāti / Pašvaldības / Citi politiķi) nesakrīt ar profile_kind vai
    sliedē parādās tukša grupa.
    """

    def _render(self, tmp_path):
        import re

        from jinja2 import Environment, FileSystemLoader

        from src.render._orchestrator import _safe_url_filter
        from src.render.personas import render_personas

        db = _build_personas_db()
        db.executemany(
            "INSERT INTO tracked_politicians (id, name, party, role) VALUES (?, ?, ?, ?)",
            [
                (1, "Jauna Deputāte", "Jaunā Vienotība", "15. Saeimā ievēlēta"),
                (2, "Atkal Ievēlētais", "Jaunā Vienotība", "Saeimas deputāts"),
                (3, "Neievēlētais", "Latvija Pirmajā Vietā", "Saeimas deputāts"),
                (4, "Ministrs Bez Mandāta", "Jaunā Vienotība", "Ministrs"),
                (5, "Eiropas Deputāts", "Jaunā Vienotība", "EP deputāts"),
                (6, "Novada Mērs", None, "Novada domes priekšsēdētājs"),
                (7, "Partijas Biedrs", "Latvija Pirmajā Vietā", "Valdes loceklis"),
            ],
        )
        db.execute("INSERT INTO saeima_votes (id, vote_date, summary) VALUES (1, '2026-04-10', 's')")
        db.executemany(
            "INSERT INTO saeima_individual_votes (vote_id, politician_id, vote) VALUES (1, ?, 'Par')",
            [(2,), (3,)],
        )
        elected = tmp_path / "elected.yaml"
        elected.write_text(
            "elected:\n"
            "- {name: Jauna Deputāte, list_nr: 9, list_short: JV, region: Rīga}\n"
            "- {name: Atkal Ievēlētais, list_nr: 9, list_short: JV, region: Rīga}\n"
            "- {name: Nav DB, list_nr: 9, list_short: JV, region: Rīga}\n",
            encoding="utf-8",
        )
        cohort = tmp_path / "cohort.yaml"
        cohort.write_text("- name: Jauna Deputāte\n- name: Arī Nav DB\n", encoding="utf-8")

        env = Environment(loader=FileSystemLoader("templates"), autoescape=True)
        env.filters["safe_url"] = _safe_url_filter
        env.globals["assets_version"] = "test"
        render_personas(env, db, tmp_path, elected_path=elected, cohort_path=cohort)
        html = (tmp_path / "personas.html").read_text(encoding="utf-8")

        cards = {
            m.group(1): m.group(0)
            for m in re.finditer(r'<article class="pnv1-card"[^>]*data-name="([^"]+)"[^>]*>', html)
        }
        rail = dict(re.findall(
            r'data-axis="saeima15" data-value="(\w+)">.*?pnv1-rail-count">(\d+)<', html, re.S
        ))
        return html, cards, rail

    def test_cards_flagged_from_data_files(self, tmp_path):
        _, cards, _ = self._render(tmp_path)
        assert 'data-saeima15="jauns"' in cards["jauna deputāte"]
        assert 'data-saeima15="ievēlēts"' in cards["atkal ievēlētais"]
        assert 'data-saeima15=""' in cards["neievēlētais"]
        assert 'data-saeima15=""' in cards["ministrs bez mandāta"]

    def test_rail_counts_equal_flagged_cards(self, tmp_path):
        _, cards, rail = self._render(tmp_path)
        n_new = sum('data-saeima15="jauns"' in c for c in cards.values())
        n_elected = n_new + sum('data-saeima15="ievēlēts"' in c for c in cards.values())
        assert (n_elected, n_new) == (2, 1)
        assert rail == {"visi": "7", "ieveleti": str(n_elected), "jauni": str(n_new)}

    def test_default_filter_is_elected_in_template_and_js(self, tmp_path):
        # Lapa atveras ar «Ievēlētie» (2026-10-05). Ja JS sākuma stāvoklis un veidnes
        # is-active poga nesakrīt, filtrs rāda vienu, bet izcelta ir cita poga.
        import re
        from pathlib import Path
        html, _, _ = self._render(tmp_path)
        active = re.findall(
            r'class="pnv1-rail-row is-active"[^>]* data-axis="saeima15" data-value="(\w+)"', html
        )
        js = (Path(__file__).resolve().parent.parent / "assets" / "pnv1.js").read_text(encoding="utf-8")
        js_default = re.search(r'^\s*saeima15: "(\w+)",', js, re.M).group(1)
        assert active == ["ieveleti"]
        assert js_default == "ieveleti"

    def test_active_chips_live_in_main_column(self, tmp_path):
        # Nosauktā kļūme (2026-10-05): čipi bija tikai mobilajā joslā (darbvirsmā
        # paslēpti), tāpēc noklusējuma filtrs «Ievēlētie» nebija ne redzams, ne
        # noņemams. Tagad viens konteiners .pnv1-main iekšpusē visiem platumiem.
        html, _, _ = self._render(tmp_path)
        main_start = html.index('<main class="pnv1-main">')
        main_end = html.index("</main>", main_start)
        assert html.count('id="pnv1-active-chips"') == 1
        assert main_start < html.index('id="pnv1-active-chips"') < main_end
        assert "pnv1-mobile-chips" not in html

    def test_saeima15_rail_group_comes_first(self, tmp_path):
        import re
        html, _, _ = self._render(tmp_path)
        titles = re.findall(r'<div class="pnv1-rail-title">([^<]+)</div>', html)
        assert titles == ["15. Saeima", "Kategorija", "Partija", "Koalīcija"]

    def test_elected_without_votes_is_deputy_with_marker(self, tmp_path):
        html, cards, _ = self._render(tmp_path)
        assert 'data-category="Deputāti"' in cards["jauna deputāte"]
        assert 'data-category="Valdība"' in cards["ministrs bez mandāta"]
        assert 'Deputāti · <span title="Jaunā Vienotība">JV</span> · 15. Saeima</div>' in html

    def test_category_rail_splits_role_groups(self, tmp_path):
        import re
        html, cards, _ = self._render(tmp_path)
        rail = re.findall(
            r'data-axis="category" data-value="([^"]+)">.*?pnv1-rail-count">(\d+)<', html, re.S
        )
        # Kanoniskā secība, tukšās grupas (Žurnālisti, Mediji …) nerāda.
        assert rail == [
            ("visas", "7"), ("Deputāti", "3"), ("Valdība", "1"), ("EP deputāti", "1"),
            ("Pašvaldības", "1"), ("Citi politiķi", "1"),
        ]
        assert 'data-category="EP deputāti"' in cards["eiropas deputāts"]
        assert 'data-category="Pašvaldības"' in cards["novada mērs"]
        assert 'data-category="Citi politiķi"' in cards["partijas biedrs"]

    def test_missing_data_file_fails_loudly(self, tmp_path):
        import pytest

        from src.render.personas import _load_saeima15_names

        with pytest.raises(FileNotFoundError):
            _load_saeima15_names(tmp_path / "nav.yaml", tmp_path / "nav2.yaml")

    def test_every_card_has_four_stat_slots(self, tmp_path):
        # Nosauktā kļūme (2026-10-09): ne-balsotājam «bals.» šūna izkrita, un
        # kartītes kolonnas nelīdzinājās ar kaimiņiem (Braže: 3 šūnas pret 4).
        # «—» = nav attiecināms, nevis maldinošs «0».
        import re
        html, _, _ = self._render(tmp_path)
        blocks = re.findall(r'<div class="pnv1-card-stats">(.*?)\n          </div>', html, re.S)
        assert len(blocks) == 7
        assert all(len(re.findall(r'class="pnv1-card-stat[ "]', b)) == 4 for b in blocks)
        assert sum('stat-n">—<' in b for b in blocks) == 5  # 2 balsotāji no 7
