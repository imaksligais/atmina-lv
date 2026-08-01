"""Tests for src/briefs.py — daily/weekly brief generation with temp DB."""

import sqlite3
import tempfile
import os
import pytest
from src.briefs import generate_daily_brief, generate_weekly_brief


def _safe_unlink(path):
    """Windows WAL mode keeps files open; ignore PermissionError on cleanup."""
    try:
        os.unlink(path)
    except PermissionError:
        pass


class TestNoTruncationInDailyBriefTables:
    """2026-06-10 operatora noteikums: skeleta tabulu šūnās saturu NEgriež.
    Regresija: spriedzes apraksta [:120] publicēja '…nekavējoties ne' (vidū
    apgriezts, bez elipses); stance 220-elipse un pretrunu [:347] grieza
    teikumus. Pilnam tekstam jānonāk izvadē neizmainītam."""

    def test_long_tension_description_and_stance_survive_in_full(self, briefs_db):
        import sqlite3
        from src.briefs import generate_daily_brief

        long_desc = ("2026-04-07: Ainars Šlesers (LPV) publiski kritizē Eviku "
                     "Siliņu (JV) par to, ka valdība nekavējoties neatcēla "
                     "apstrīdēto lēmumu, un pieprasa pilnu skaidrojumu Saeimas "
                     "komisijā par katru no pieņemtajiem soļiem šajā jautājumā.")
        assert len(long_desc) > 120
        long_stance = ("Atbalsta vērienīgu un detalizēti pamatotu reformu "
                       "pieeju, kas paredz pakāpenisku pāreju, plašas "
                       "konsultācijas ar nozari, neatkarīgu ietekmes "
                       "izvērtējumu, pārejas perioda kompensācijas mazajiem "
                       "uzņēmumiem un ikgadēju publisku atskaiti Saeimai par "
                       "ieviešanas gaitu, rezultātiem un nepieciešamajām "
                       "korekcijām nākamajos posmos.")
        assert len(long_stance) > 220

        db = sqlite3.connect(briefs_db)
        db.execute("UPDATE claims SET stance = ? WHERE id = 1", (long_stance,))
        db.execute(
            "INSERT INTO political_tensions "
            "(id, source_pid, target_pid, tension_type, topic, description, source_url, created_at) "
            "VALUES (1, 2, 1, 'spriedze', 'Budžets un finanses', ?, 'https://x.lv/9', '2026-04-07')",
            (long_desc,),
        )
        db.commit()
        db.close()

        out = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        assert long_desc in out
        assert long_stance in out
        # Skelets pats elipses nepievieno (fixture dati "…" nesatur).
        assert "…" not in out


class TestDienasStatsPlatformCounts:
    """BACKLOG 2026-08-04: `x_count = doc_count - web_count` dumped every
    non-web platform into the Twitter/X bucket — the 08-03 brief reported
    "561 Twitter/X" where 24 were vestnesis. Counting must go per platform."""

    def test_vestnesis_counted_separately_not_as_twitter(self, briefs_db):
        db = sqlite3.connect(briefs_db)
        db.execute("INSERT INTO documents VALUES (4, '2026-04-07', 'vestnesis')")
        db.execute("INSERT INTO documents VALUES (5, '2026-04-07', 'x_mention')")
        db.commit()
        db.close()
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        assert "5 dokumenti (2 web + 2 Twitter/X + 1 vestnesis)" in brief

    def test_unknown_platform_reported_as_citi_not_swallowed(self, briefs_db):
        """A platform the buckets don't know must show up as `citi`, not
        vanish into an adjacent bucket — report the denominator."""
        db = sqlite3.connect(briefs_db)
        db.execute("INSERT INTO documents VALUES (4, '2026-04-07', 'web_scraper')")
        db.commit()
        db.close()
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        assert "4 dokumenti (2 web + 1 Twitter/X + 0 vestnesis + 1 citi)" in brief


@pytest.fixture
def briefs_db():
    """Create a temp DB with the schema needed for brief generation."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = sqlite3.connect(path)
    db.executescript("""
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY,
            scraped_at TEXT,
            platform TEXT
        );
        CREATE TABLE tracked_politicians (
            id INTEGER PRIMARY KEY,
            name TEXT,
            party TEXT,
            relationship_type TEXT
        );
        CREATE TABLE claims (
            id INTEGER PRIMARY KEY,
            opponent_id INTEGER,
            topic TEXT,
            stance TEXT,
            source_url TEXT,
            stated_at TEXT,
            created_at TEXT,
            salience REAL,
            claim_type TEXT NOT NULL DEFAULT 'position'
        );
        CREATE TABLE contradictions (
            id INTEGER PRIMARY KEY,
            opponent_id INTEGER,
            claim_old_id INTEGER,
            claim_new_id INTEGER,
            topic TEXT,
            severity TEXT,
            summary TEXT,
            detected_at TEXT,
            confirmed INTEGER DEFAULT 1
        );
        CREATE TABLE context_notes (
            id INTEGER PRIMARY KEY,
            note_type TEXT,
            content TEXT,
            topic TEXT,
            created_at TEXT
        );
        CREATE TABLE political_tensions (
            id INTEGER PRIMARY KEY,
            source_pid INTEGER,
            target_pid INTEGER,
            tension_type TEXT,
            topic TEXT,
            description TEXT,
            source_url TEXT,
            created_at TEXT
        );
        CREATE TABLE parties (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            short_name TEXT,
            coalition_status TEXT
        );
        CREATE TABLE saeima_votes (
            id INTEGER PRIMARY KEY,
            vote_date TEXT
        );

        INSERT INTO parties (name, short_name, coalition_status)
            VALUES ('Jaunā Vienotība', 'JV', 'coalition');
        INSERT INTO parties (name, short_name, coalition_status)
            VALUES ('Latvija Pirmajā Vietā', 'LPV', 'opposition');

        INSERT INTO tracked_politicians VALUES (1, 'Evika Siliņa', 'JV', 'coalition_partner');
        INSERT INTO tracked_politicians VALUES (2, 'Ainars Šlesers', 'LPV', 'opponent');

        INSERT INTO documents VALUES (1, '2026-04-07', 'web');
        INSERT INTO documents VALUES (2, '2026-04-07', 'web');
        INSERT INTO documents VALUES (3, '2026-04-07', 'twitter');

        INSERT INTO claims (id, opponent_id, topic, stance, source_url, stated_at)
            VALUES (1, 1, 'NATO', 'Atbalsta NATO finansējumu', 'https://x.lv/1', '2026-04-07');
        INSERT INTO claims (id, opponent_id, topic, stance, source_url, stated_at)
            VALUES (2, 1, 'Budžets un finanses', 'Par nulles budžetu', 'https://x.lv/2', '2026-04-07');
        INSERT INTO claims (id, opponent_id, topic, stance, source_url, stated_at)
            VALUES (3, 2, 'NATO', 'Pret NATO izdevumu palielināšanu', 'https://x.lv/3', '2026-04-07');

        INSERT INTO contradictions (id, opponent_id, claim_old_id, claim_new_id, topic, severity, summary, detected_at)
            VALUES (1, 1, 1, 3, 'NATO', 'minor_shift',
                    'Siliņa 5.apr. atbalsta; 7.apr. iebilst pret to pašu.',
                    '2026-04-07');
    """)
    db.commit()
    db.close()
    yield path
    _safe_unlink(path)


@pytest.fixture
def empty_briefs_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = sqlite3.connect(path)
    db.executescript("""
        CREATE TABLE documents (id INTEGER PRIMARY KEY, scraped_at TEXT, platform TEXT);
        CREATE TABLE tracked_politicians (id INTEGER PRIMARY KEY, name TEXT, party TEXT, relationship_type TEXT);
        CREATE TABLE claims (id INTEGER PRIMARY KEY, opponent_id INTEGER, topic TEXT, stance TEXT, source_url TEXT, stated_at TEXT, created_at TEXT, salience REAL, claim_type TEXT NOT NULL DEFAULT 'position');
        CREATE TABLE contradictions (id INTEGER PRIMARY KEY, opponent_id INTEGER, claim_old_id INTEGER, claim_new_id INTEGER, topic TEXT, severity TEXT, summary TEXT, detected_at TEXT, confirmed INTEGER DEFAULT 1);
        CREATE TABLE context_notes (id INTEGER PRIMARY KEY, note_type TEXT, content TEXT, topic TEXT, created_at TEXT);
        CREATE TABLE political_tensions (id INTEGER PRIMARY KEY, source_pid INTEGER, target_pid INTEGER, tension_type TEXT, topic TEXT, description TEXT, source_url TEXT, created_at TEXT);
        CREATE TABLE parties (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, short_name TEXT, coalition_status TEXT);
        CREATE TABLE saeima_votes (id INTEGER PRIMARY KEY, vote_date TEXT);
    """)
    db.commit()
    db.close()
    yield path
    _safe_unlink(path)


class TestGenerateDailyBrief:
    def test_contains_header(self, briefs_db):
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        assert "# Dienas analīze — 2026-04-07" in brief

    def test_galvenais_has_stats_comment(self, briefs_db):
        """Stats live in <!-- DIENAS STATS --> comment for agent context, not as
        a visible bullet. Comment is in DOM but not rendered to users."""
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        assert "<!-- DIENAS STATS" in brief
        assert "3 dokumenti" in brief  # still in comment
        assert "2 web" in brief  # still in comment
        assert "3 pozīcijas" in brief  # still in comment
        assert "1 pretruna" in brief  # still in comment

    def test_galvenais_has_no_visible_stats_bullet(self, briefs_db):
        """The old stats bullet is gone — agent's bullet-point narrative
        replaces it. Skeleton leaves ## Galvenais empty (except comment)."""
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        # No visible bullet with stats pattern
        assert "- **3 dokumenti**" not in brief
        assert "**3 jaunas pozīcijas**" not in brief

    def test_contains_politician_table(self, briefs_db):
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        assert "Evika Siliņa" in brief
        assert "Ainars Šlesers" in brief

    def test_empty_day_has_zero_stats_comment(self, briefs_db):
        brief = generate_daily_brief(db_path=briefs_db, date="2025-01-01")
        assert "<!-- DIENAS STATS" in brief
        assert "0 dokumenti" in brief

    def test_empty_db_renders(self, empty_briefs_db):
        brief = generate_daily_brief(db_path=empty_briefs_db, date="2026-04-07")
        assert "Dienas analīze" in brief
        assert "<!-- DIENAS STATS" in brief

    def test_recently_extracted_claim_appears(self, briefs_db):
        """Claim stated yesterday but extracted (created) today must appear in
        today's brief. A pure date(stated_at)=today filter silently dropped the
        common 'politician spoke yesterday, we extracted today' case (audit
        2026-06-08, feedback_brief_writer_scoping_gaps)."""
        db = sqlite3.connect(briefs_db)
        db.execute(
            "INSERT INTO claims (opponent_id, topic, stance, source_url, stated_at, created_at, claim_type) "
            "VALUES (1, 'Enerģētika', 'Atbalsta vēja parkus', 'https://x.lv/recent', "
            "'2026-04-06', '2026-04-07', 'position')"
        )
        db.commit()
        db.close()
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        # Surfaces as a topic subsection (by_topic + samples queries) and in the
        # politician leaderboard (active query) — all stated_at-scoped sites.
        assert "### Enerģētika" in brief
        assert "Atbalsta vēja parkus" in brief

    def test_old_claim_extracted_today_excluded(self, briefs_db):
        """The created_at arm has a 7-day floor on stated_at so a bulk historical
        backfill (stated years ago, created today) does NOT flood today's brief."""
        db = sqlite3.connect(briefs_db)
        db.execute(
            "INSERT INTO claims (opponent_id, topic, stance, source_url, stated_at, created_at, claim_type) "
            "VALUES (1, 'Vēsturisks', 'Sena pozīcija', 'https://x.lv/old', "
            "'2022-01-01', '2026-04-07', 'position')"
        )
        db.commit()
        db.close()
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        assert "### Vēsturisks" not in brief
        assert "Sena pozīcija" not in brief


class TestDailyBriefStructure:
    """Verify skeleton has all mandatory sections for @brief-writer."""

    def test_starts_with_h1(self, briefs_db):
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        assert brief.startswith("# "), "Brief must start with H1 (# ), not ##"

    def test_has_politician_table(self, briefs_db):
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        assert "## Aktīvākie politiķi" in brief
        assert "| Politiķis |" in brief

    def test_has_topic_subsections(self, briefs_db):
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        assert "## Galvenās tēmas" in brief
        assert "### " in brief, "Topics must use ### subsections"

    def test_has_coalition_section(self, briefs_db):
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        assert "## Koalīcija vs Opozīcija" in brief

    def test_has_synthesis_hints(self, briefs_db):
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        assert "<!-- SINTĒZE:" in brief, "Skeleton must include per-topic synthesis hints"

    def test_topics_ranked_by_interest(self, briefs_db):
        """Topics with tensions should rank higher than pure position count."""
        # Add a tension for NATO topic (which has 2 positions vs Budžets with 1)
        db = sqlite3.connect(briefs_db)
        db.execute(
            "INSERT INTO political_tensions (source_pid, target_pid, tension_type, topic, description, created_at) "
            "VALUES (1, 2, 'Uzbrukums', 'NATO', 'Test tension', '2026-04-07')"
        )
        db.commit()
        db.close()
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        nato_pos = brief.index("### NATO")
        # NATO should appear (it has positions + tension)
        assert nato_pos > 0


class TestTensionDayBoundaryTimezone:
    """Regression (2026-07-30): ``political_tensions.created_at`` is UTC — it
    relies on SQLite's ``DEFAULT CURRENT_TIMESTAMP``, unlike ``claims`` /
    ``context_notes`` which ``now_lv()`` writes in LV time (see src/schema.sql
    and TestEveningBoundaryTimezone in tests/test_routine.py, which fixes the
    mirror-image rule for the LV-stored columns).

    Until 2026-07-30 the three tension queries in ``briefs.py`` read the column
    bare (``date(created_at) = ?``) while ``routine.py`` read it correctly with
    ``'localtime'``. Between 21:00 and 23:59 UTC — exactly when the evening
    routine runs — the two disagree, so the same tension could appear in the
    brief for one day and be reported missing by the routine status for the
    other. Observed 2026-07-29 on tension #175.
    """

    STAMP = "2026-04-07 21:30:00"  # 00:30 LV on 2026-04-08 at UTC+3

    @staticmethod
    def _both_days(db_path, stamp):
        """Ask SQLite itself, so the test states no assumption about the host TZ."""
        db = sqlite3.connect(db_path)
        raw, lv = db.execute("SELECT date(?), date(?, 'localtime')", (stamp, stamp)).fetchone()
        db.close()
        return raw, lv

    def _seed(self, path):
        db = sqlite3.connect(path)
        db.execute("INSERT INTO tracked_politicians (id, name, party, relationship_type) "
                   "VALUES (1, 'Avota Politiķis', 'JV', 'tracked')")
        db.execute("INSERT INTO tracked_politicians (id, name, party, relationship_type) "
                   "VALUES (2, 'Mērķa Politiķis', 'LPV', 'tracked')")
        db.execute(
            "INSERT INTO political_tensions (source_pid, target_pid, tension_type, topic, "
            "description, source_url, created_at) "
            "VALUES (1, 2, 'spriedze', 'NATO', ?, 'https://x.com/a/status/1', ?)",
            ("Vakara spriedzes apraksts", self.STAMP),
        )
        db.commit()
        db.close()

    def test_evening_tension_belongs_to_its_lv_day(self, empty_briefs_db):
        self._seed(empty_briefs_db)
        raw_day, lv_day = self._both_days(empty_briefs_db, self.STAMP)
        if raw_day == lv_day:
            pytest.skip("host TZ is UTC — the UTC/LV day boundary is unobservable here")

        on_lv_day = generate_daily_brief(db_path=empty_briefs_db, date=lv_day)
        assert "Vakara spriedzes apraksts" in on_lv_day, (
            f"a tension stored at {self.STAMP} UTC must appear in the brief "
            f"for LV day {lv_day}"
        )

    def test_evening_tension_absent_from_the_utc_day(self, empty_briefs_db):
        """The half that actually failed before the fix."""
        self._seed(empty_briefs_db)
        raw_day, lv_day = self._both_days(empty_briefs_db, self.STAMP)
        if raw_day == lv_day:
            pytest.skip("host TZ is UTC — the UTC/LV day boundary is unobservable here")

        on_raw_day = generate_daily_brief(db_path=empty_briefs_db, date=raw_day)
        assert "Vakara spriedzes apraksts" not in on_raw_day, (
            f"bare date(created_at) leaked the tension into the previous "
            f"LV day ({raw_day})"
        )


class TestCoalitionTable:
    """Koalīcija vs Opozīcija tagad ir tabula, ne 3 paragrāfi."""

    def test_koalicija_section_uses_table(self, briefs_db):
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        assert "## Koalīcija vs Opozīcija" in brief
        # Tabula header ar kolonnām Bloks, Pozīcijas
        assert "| Bloks |" in brief
        assert "| Pozīcijas |" in brief

    def test_koalicija_has_coalition_row(self, briefs_db):
        """JV Siliņa fixturē ir coalition. Tabulai jāietver Koalīcija rinda."""
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        assert "| Koalīcija |" in brief
        assert "JV" in brief

    def test_koalicija_has_opposition_row(self, briefs_db):
        """LPV Šlesers fixturē ir opposition."""
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        assert "| Opozīcija |" in brief
        assert "LPV" in brief

    def test_koalicija_no_old_paragraph_format(self, briefs_db):
        """Vecās `**Koalīcija (N pozīcijas):**` formāts ir pagājis."""
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        assert "**Koalīcija (" not in brief
        assert "**Opozīcija (" not in brief

    def test_koalicija_neutral_row_disjoint_from_coalition(self, briefs_db):
        """Journalist/influencer politicians — tikai Neitrāli rindā, ne
        Koalīcija/Opozīcija rindās. Novērš double-counting."""
        import sqlite3
        db = sqlite3.connect(briefs_db)
        # Pievieno žurnālistu ar JV partiju (mākslīgs edge case)
        db.execute(
            "INSERT INTO tracked_politicians (id, name, party, relationship_type) "
            "VALUES (99, 'Jānis Žurnālists', 'Jaunā Vienotība', 'journalist')"
        )
        db.execute(
            "INSERT INTO claims (opponent_id, topic, stance, source_url, stated_at) "
            "VALUES (99, 'Mediji', 'Kritika par XYZ', 'https://x.lv/99', '2026-04-07')"
        )
        db.commit()
        db.close()
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        # Neitrāli rinda eksistē
        assert "| Neitrāli |" in brief
        # Koalīcija rindā Žurnālists NAV (skaits paliek 2, nekļūst 3)
        # Vecais fixturē Siliņa (JV) ir 2 pozīcijas; pēc inaktīvo exclusion,
        # koalīcija Žurnālistu neietver.
        koalicija_line = [l for l in brief.split("\n") if l.startswith("| Koalīcija |")]
        assert len(koalicija_line) == 1
        # Koalīcija rindā saskaita tikai politiskos — 2 Siliņas pozīcijas
        assert "| Koalīcija | 2 |" in brief
        # Neitrāli rinda satur Žurnālistu
        neitral_line = [l for l in brief.split("\n") if l.startswith("| Neitrāli |")]
        assert len(neitral_line) == 1
        assert "Žurnālists" in neitral_line[0]
        # Partijas aile Neitrāli rindā ir "—" — audience bloku definē
        # relationship_type, ne partija; residuāla partija (žurnālists ar JV
        # partiju, tāpat kā Seržanta journalist-guard ar 'Apvienotais saraksts')
        # nedrīkst noplūst un rādīt partijas tagu rindā ar bezpartijas runātājiem.
        neitral_cells = [c.strip() for c in neitral_line[0].split("|")]
        # kolonnas: ['', 'Neitrāli', cnt, partijas, runātāji, tēmas, '']
        assert neitral_cells[3] == "—", (
            f"Neitrāli Partijas ailei jābūt '—', nevis {neitral_cells[3]!r}"
        )
        assert "JV" not in neitral_cells[3]

    def test_bezpartejiskie_row_for_partyless_politician(self, briefs_db):
        """Tracked politiķis bez partijas (party IS NULL, piem. Valsts
        prezidents) nedrīkst izkrist cauri visiem blokiem — coalition_map.get
        (None) → None, tāpēc viņš nav ne Koalīcijā/Opozīcijā/Bez Saeimas frakcijas, ne
        Neitrāli (jo relationship_type='tracked', ne audience). Viņam jāparādās
        atsevišķā Bezpartejiskie rindā, citādi 'Pozīcijas' kopskaits klusi
        nesakrīt."""
        db = sqlite3.connect(briefs_db)
        db.execute(
            "INSERT INTO tracked_politicians (id, name, party, relationship_type) "
            "VALUES (50, 'Edgars Rinkēvičs', NULL, 'tracked')"
        )
        db.execute(
            "INSERT INTO claims (opponent_id, topic, stance, source_url, stated_at) "
            "VALUES (50, 'Ārpolitika', 'Atbalsta Ukrainu', 'https://x.lv/50', '2026-04-07')"
        )
        db.commit()
        db.close()
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        bezp_line = [l for l in brief.split("\n") if l.startswith("| Bezpartejiskie |")]
        assert len(bezp_line) == 1, "Bezpartejiskie rindai jāparādās, kad ir bezpartejisks politiķis ar pozīciju"
        assert "Rinkēvičs" in bezp_line[0]
        assert "| Bezpartejiskie | 1 |" in bezp_line[0]


class TestPretrunasSection:
    """Jauna ## Pretrunas sadaļa — tikai ja dienā ir contradictions.
    Fixtures provides severity='minor_shift' and summary — no ALTER TABLE
    hackery in tests."""

    def test_pretrunas_section_rendered(self, briefs_db):
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        assert "## Pretrunas" in brief

    def test_pretrunas_severity_is_lv(self, briefs_db):
        """minor_shift → 'neliela novirze' (nav raw enum)."""
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        assert "neliela novirze" in brief
        assert "minor_shift" not in brief

    def test_pretrunas_no_db_id_leak(self, briefs_db):
        """Raw DB ID #NN nav publiskā tekstā."""
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        assert "Pretruna #" not in brief

    def test_pretrunas_section_absent_on_empty_day(self, briefs_db):
        """Diena bez pretrunām — sadaļa nav."""
        brief = generate_daily_brief(db_path=briefs_db, date="2025-01-01")
        assert "## Pretrunas" not in brief


class TestFix1EmptyPartyParens:
    """Fix 1 — politiķim ar party IS NULL/tukšu iekavas NEemitē vispār.
    Regresija: 'Vārds ()' spriedžu tabulā (un citos emit punktos), kur
    GROUP_CONCAT ... '(' || COALESCE(party,'') || ')' radīja tukšas iekavas
    bezpartejiskiem (piem. Valsts prezidents)."""

    def test_tension_partyless_source_no_empty_parens(self, briefs_db):
        """Spriedze ar NULL-party avotu → 'Vārds' bez '()'."""
        db = sqlite3.connect(briefs_db)
        db.execute(
            "INSERT INTO tracked_politicians (id, name, party, relationship_type) "
            "VALUES (60, 'Edgars Rinkēvičs', NULL, 'tracked')"
        )
        # NARATĪVA MATERIĀLS bloks emitē top_tension_topics pairs ar (party).
        db.execute(
            "INSERT INTO political_tensions "
            "(source_pid, target_pid, tension_type, topic, description, source_url, created_at) "
            "VALUES (60, 1, 'Uzbrukums', 'Ārpolitika', 'Kritizē valdību', "
            "'https://x.lv/t60', '2026-04-07')"
        )
        db.commit()
        db.close()
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        assert "Rinkēvičs" in brief
        assert "Rinkēvičs ()" not in brief
        assert "()" not in brief, "Nekādas tukšas iekavas nekur izvadē"

    def test_tension_partyless_target_no_empty_parens(self, briefs_db):
        """Spriedze ar NULL-party mērķi → 'Vārds' bez '()' (Spriedžu tabula)."""
        db = sqlite3.connect(briefs_db)
        db.execute(
            "INSERT INTO tracked_politicians (id, name, party, relationship_type) "
            "VALUES (61, 'Edgars Rinkēvičs', NULL, 'tracked')"
        )
        db.execute(
            "INSERT INTO political_tensions "
            "(source_pid, target_pid, tension_type, topic, description, source_url, created_at) "
            "VALUES (1, 61, 'Uzbrukums', 'Ārpolitika', 'Kritizē prezidentu', "
            "'https://x.lv/t61', '2026-04-07')"
        )
        db.commit()
        db.close()
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        # Spriedžu tabulā mērķis '→ Rinkēvičs' bez tukšām iekavām
        assert "Rinkēvičs ()" not in brief
        assert "()" not in brief


class TestFix2StatsReconciliation:
    """Fix 2 — DIENAS STATS pozīciju skaitlis atbilst emitētajām pozīcijām.
    Regresija: STATS position_count izslēdza org/žurnālistu kontus, bet
    tas pats predikāts nebija koplietots ar ###-emisijas vaicājumu → skaitļi
    nesakrita. STATS pozīciju skaitam jāatspoguļo tieši emitēto politiķu
    pozīcijas (ar skaidru org marķējumu, ja org iesaistīti)."""

    def test_stats_position_count_matches_emitted(self, briefs_db):
        """Fixture: 3 position claims, visi politiķi (nav org) → STATS rāda 3."""
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        # Aktīvākie tabulā saskaita politiķu pozīcijas; STATS pozīciju skaitam
        # jāsakrīt ar politiķu daļu.
        assert "3 pozīcijas" in brief

    def test_stats_splits_audience_from_politicians(self, briefs_db):
        """Kad auditorijas konts ievieš pozīciju, STATS emitē abus ar marķējumu:
        'N pozīcijas (M politiķu + K auditorijas)' — nevis klusi izslēdz K un
        rāda skaitli, kas nesakrīt ar emisiju.

        Marķējums paplašināts 2026-08-03 no 'org' uz 'auditorijas': kopš
        auditorijas balsis iet tēmu tabulās, kopsummā jābūt VISAM emitētajam,
        un žurnālistu/neitrāļu rindas agrāk nebija ne vienā, ne otrā skaitā.
        Kopsumma tagad tiešām ir summa — to fiksē arī pati pārbaude zemāk.
        """
        db = sqlite3.connect(briefs_db)
        db.execute(
            "INSERT INTO tracked_politicians (id, name, party, relationship_type) "
            "VALUES (70, 'LDDK', NULL, 'organization')"
        )
        db.execute(
            "INSERT INTO claims (opponent_id, topic, stance, source_url, stated_at, claim_type) "
            "VALUES (70, 'Budžets un finanses', 'Org pozīcija', 'https://x.lv/70', "
            "'2026-04-07', 'position')"
        )
        db.commit()
        db.close()
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        # 3 politiķu pozīcijas + 1 auditorijas pozīcija = 4 emitētas.
        assert "4 pozīcijas (3 politiķu + 1 auditorijas)" in brief
        # Un org pozīcija tiešām parādās tabulā, nevis tikai skaitlī.
        assert "Org pozīcija" in brief


class TestFix3BackfillBriefedExclusion:
    """Fix 3 — 7-dienu loga otrais disjunkts izslēdz claim tikai tad, ja tā
    stated-diena JAU briefota un brief laika zīmogs ir PĒC claim created_at
    (t.i. claim jau bija DB, kad to dienu briefoja). Vēlāk ekstraktēti claim
    (created pēc brief) paliek; same-day stated claim vienmēr paliek."""

    def test_backfill_claim_briefed_before_created_excluded(self, briefs_db):
        """Claim stated=vakar, created=šodien, BET vakardienas brief jau
        publicēts PĒC claim created → jau redzēts → izslēgts no šodienas."""
        db = sqlite3.connect(briefs_db)
        # Backfill claim: stated 2026-04-06, created 2026-04-07 08:00
        db.execute(
            "INSERT INTO claims (opponent_id, topic, stance, source_url, stated_at, created_at, claim_type) "
            "VALUES (1, 'BackfillTēma', 'Backfill pozīcija', 'https://x.lv/bf', "
            "'2026-04-06', '2026-04-07 08:00:00', 'position')"
        )
        # 2026-04-06 dienas brief publicēts 2026-04-07 09:00 (PĒC claim created)
        db.execute(
            "INSERT INTO context_notes (note_type, topic, content, created_at) "
            "VALUES ('daily_brief', 'dienas analīze 2026-04-06', 'brief saturs', "
            "'2026-04-07 09:00:00')"
        )
        db.commit()
        db.close()
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        assert "### BackfillTēma" not in brief
        assert "Backfill pozīcija" not in brief

    def test_later_extracted_claim_created_after_brief_included(self, briefs_db):
        """Claim stated=vakar, created=šodien PĒC vakardienas brief zīmoga →
        nebija DB, kad briefoja → jāparādās šodien."""
        db = sqlite3.connect(briefs_db)
        # 2026-04-06 brief publicēts 2026-04-07 09:00
        db.execute(
            "INSERT INTO context_notes (note_type, topic, content, created_at) "
            "VALUES ('daily_brief', 'dienas analīze 2026-04-06', 'brief saturs', "
            "'2026-04-07 09:00:00')"
        )
        # Claim ekstraktēts 2026-04-07 15:00 — PĒC brief
        db.execute(
            "INSERT INTO claims (opponent_id, topic, stance, source_url, stated_at, created_at, claim_type) "
            "VALUES (1, 'VēlākTēma', 'Vēlāk ekstraktēts', 'https://x.lv/late', "
            "'2026-04-06', '2026-04-07 15:00:00', 'position')"
        )
        db.commit()
        db.close()
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        assert "### VēlākTēma" in brief
        assert "Vēlāk ekstraktēts" in brief

    def test_same_day_stated_claim_always_included(self, briefs_db):
        """Pirmais disjunkts (date(stated_at)=day) paliek neaiztikts, pat ja
        eksistē tās dienas brief zīmogs (same-day refresh)."""
        db = sqlite3.connect(briefs_db)
        # Šodienas brief jau publicēts (same-day refresh scenārijs)
        db.execute(
            "INSERT INTO context_notes (note_type, topic, content, created_at) "
            "VALUES ('daily_brief', 'dienas analīze 2026-04-07', 'brief saturs', "
            "'2026-04-07 09:00:00')"
        )
        # Claim stated=today, created pēc tā paša dienas brief
        db.execute(
            "INSERT INTO claims (opponent_id, topic, stance, source_url, stated_at, created_at, claim_type) "
            "VALUES (1, 'ŠodienTēma', 'Šodien teikts', 'https://x.lv/today', "
            "'2026-04-07', '2026-04-07 15:00:00', 'position')"
        )
        db.commit()
        db.close()
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        assert "### ŠodienTēma" in brief
        assert "Šodien teikts" in brief


class TestT7ParejasTemas:
    """T7 fix — full ### sections = top-5 by interest_score PLUS every topic with
    cnt>=3; all remaining topics land in one compact `### Pārējās tēmas` table.
    Regresija: skelets emitēja ### tikai top-5 by interest_score; augsti-salient
    solo tēmas un cnt>=3 tēmas ārpus top-5 klusi pazuda no skeleta (mērīts ~5
    tēmas/dienā, ieskaitot 5-pozīciju tēmu 2026-07-23)."""

    def _seed_five_high_interest_topics(self, db):
        """Seed 5 topics that each outrank a plain cnt-based 6th topic by adding
        tensions (interest_score = cnt + tensions*3). Each gets 1 position + 1
        tension → interest_score 4, beating a 3-position no-tension topic (3)."""
        for n in range(1, 6):
            topic = f"HighT{n}"
            db.execute(
                "INSERT INTO claims (opponent_id, topic, stance, source_url, stated_at, salience) "
                "VALUES (2, ?, ?, ?, '2026-04-07', 0.5)",
                (topic, f"Augstas intereses pozīcija {n}", f"https://x.lv/ht{n}"),
            )
            db.execute(
                "INSERT INTO political_tensions "
                "(source_pid, target_pid, tension_type, topic, description, created_at) "
                "VALUES (1, 2, 'Uzbrukums', ?, 'spriedze', '2026-04-07')",
                (topic,),
            )

    def test_cnt_ge_3_topic_beyond_rank5_gets_full_section(self, briefs_db):
        """A 6th topic with 3 positions (rank > 5 by interest_score) still gets a
        full `### {topic} (3 pozīcijas)` section, NOT the Pārējās table."""
        db = sqlite3.connect(briefs_db)
        self._seed_five_high_interest_topics(db)
        # 6th topic: 3 positions, no tension → interest_score 3, ranks below the 5.
        for i in range(3):
            db.execute(
                "INSERT INTO claims (opponent_id, topic, stance, source_url, stated_at, salience) "
                "VALUES (1, 'TrīsPoz', ?, ?, '2026-04-07', 0.5)",
                (f"Trīs pozīcijas {i}", f"https://x.lv/tp{i}"),
            )
        db.commit()
        db.close()
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        assert "### TrīsPoz (3 pozīcijas)" in brief
        # Must NOT be demoted into the Pārējās table.
        parejas_idx = brief.find("### Pārējās tēmas")
        trispoz_idx = brief.find("### TrīsPoz")
        if parejas_idx != -1:
            assert trispoz_idx < parejas_idx, "cnt>=3 topic must precede Pārējās section"

    def test_solo_topic_beyond_top5_lands_in_parejas_table(self, briefs_db):
        """A solo (1-position) topic ranked below top-5 lands in `### Pārējās
        tēmas` with politician name, topic, stance, and a markdown source link."""
        db = sqlite3.connect(briefs_db)
        self._seed_five_high_interest_topics(db)
        # 6th topic: 1 position, no tension → interest_score 1, below the 5.
        db.execute(
            "INSERT INTO claims (opponent_id, topic, stance, source_url, stated_at, salience) "
            "VALUES (1, 'SoloTēma', 'Solo pozīcija par tēmu', 'https://solo.lv/1', "
            "'2026-04-07', 0.5)"
        )
        db.commit()
        db.close()
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        assert "### Pārējās tēmas" in brief
        # Locate the Pārējās block and assert the row content lives inside it.
        parejas = brief[brief.index("### Pārējās tēmas"):]
        assert "SoloTēma" in parejas
        assert "Solo pozīcija par tēmu" in parejas
        assert "Evika Siliņa" in parejas
        assert "[solo.lv](https://solo.lv/1)" in parejas
        # Correct column header.
        assert "| Politiķis | Partija | Tēma | Pozīcija | Avots |" in parejas

    def test_parejas_ordering_by_max_salience(self, briefs_db):
        """Two rest-topics with different max salience → the higher-salience
        topic's row comes first in the Pārējās table."""
        db = sqlite3.connect(briefs_db)
        self._seed_five_high_interest_topics(db)
        db.execute(
            "INSERT INTO claims (opponent_id, topic, stance, source_url, stated_at, salience) "
            "VALUES (1, 'ZemaSal', 'Zema salience', 'https://z.lv/1', '2026-04-07', 0.2)"
        )
        db.execute(
            "INSERT INTO claims (opponent_id, topic, stance, source_url, stated_at, salience) "
            "VALUES (2, 'AugstaSal', 'Augsta salience', 'https://a.lv/1', '2026-04-07', 0.9)"
        )
        db.commit()
        db.close()
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        parejas = brief[brief.index("### Pārējās tēmas"):]
        assert parejas.index("AugstaSal") < parejas.index("ZemaSal"), (
            "Higher max_salience topic must come first"
        )

    def test_no_leftovers_no_parejas_section(self, briefs_db):
        """A day with ≤5 topics (the base fixture has 2) → no Pārējās section."""
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        assert "Pārējās tēmas" not in brief

    def test_parejas_plural_forms_singular(self, briefs_db):
        """A rest-set of exactly 1 claim in 1 topic renders `(1 pozīcija 1 tēmā)`."""
        db = sqlite3.connect(briefs_db)
        # Clear the base fixture claims/contradiction so the rest-set is exactly
        # what this test seeds (base NATO/Budžets would otherwise be leftovers).
        db.execute("DELETE FROM contradictions")
        db.execute("DELETE FROM claims")
        self._seed_five_high_interest_topics(db)
        db.execute(
            "INSERT INTO claims (opponent_id, topic, stance, source_url, stated_at, salience) "
            "VALUES (1, 'VienaTēma', 'Viena pozīcija', 'https://v.lv/1', '2026-04-07', 0.5)"
        )
        db.commit()
        db.close()
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        assert "### Pārējās tēmas (1 pozīcija 1 tēmā)" in brief

    def test_parejas_plural_forms_plural(self, briefs_db):
        """A rest-set of 3 claims across 2 topics renders `(3 pozīcijas 2 tēmās)`."""
        db = sqlite3.connect(briefs_db)
        db.execute("DELETE FROM contradictions")
        db.execute("DELETE FROM claims")
        self._seed_five_high_interest_topics(db)
        # Two rest topics: one with 2 positions, one with 1 → 3 rows / 2 topics.
        db.execute(
            "INSERT INTO claims (opponent_id, topic, stance, source_url, stated_at, salience) "
            "VALUES (1, 'RestA', 'A poz 1', 'https://ra.lv/1', '2026-04-07', 0.5)"
        )
        db.execute(
            "INSERT INTO claims (opponent_id, topic, stance, source_url, stated_at, salience) "
            "VALUES (2, 'RestA', 'A poz 2', 'https://ra.lv/2', '2026-04-07', 0.4)"
        )
        db.execute(
            "INSERT INTO claims (opponent_id, topic, stance, source_url, stated_at, salience) "
            "VALUES (1, 'RestB', 'B poz 1', 'https://rb.lv/1', '2026-04-07', 0.3)"
        )
        db.commit()
        db.close()
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        assert "### Pārējās tēmas (3 pozīcijas 2 tēmās)" in brief


class TestBriefValidation:
    """Test _validate_brief_structure from src/tools.py."""

    def test_rejects_h2_start(self):
        from src.tools import _validate_brief_structure
        bad = "## Dienas analīze — 2026-04-07\n\n## Aktīvākie politiķi\n| Politiķis |\n## Galvenās tēmas\n## Koalīcija vs Opozīcija\n" + "x" * 4000
        with pytest.raises(ValueError, match="H1"):
            _validate_brief_structure(bad, "daily_brief")

    def test_rejects_missing_sections(self):
        from src.tools import _validate_brief_structure
        bad = "# Dienas analīze — 2026-04-07\n\n| Politiķis |\n" + "x" * 4000
        with pytest.raises(ValueError, match="Trūkst sekcija"):
            _validate_brief_structure(bad, "daily_brief")

    def test_rejects_too_short(self):
        from src.tools import _validate_brief_structure
        bad = "# Dienas analīze\n\n## Aktīvākie politiķi\n| Politiķis |\n## Galvenās tēmas\n## Koalīcija vs Opozīcija\n"
        with pytest.raises(ValueError, match="Pārāk īss"):
            _validate_brief_structure(bad, "daily_brief")

    def test_accepts_valid_brief(self):
        from src.tools import _validate_brief_structure
        good = (
            "# Dienas analīze — 2026-04-07\n\n"
            "## Galvenais\n\nNaratīvs.\n\n"
            "## Aktīvākie politiķi\n\n| Politiķis | Partija |\n|---|---|\n| Test | JV |\n\n"
            "## Galvenās tēmas\n\n### NATO\n\nTeksts.\n\n"
            "## Koalīcija vs Opozīcija\n\nSintēze.\n\n"
        )
        good += "x" * (4000 - len(good))
        # Should not raise
        _validate_brief_structure(good, "daily_brief")


class TestGenerateWeeklyBrief:
    def test_contains_header(self, briefs_db, tmp_path):
        brief = generate_weekly_brief(db_path=briefs_db, week_start="2026-04-06",
                                      chart_dir=str(tmp_path))
        assert "Nedēļas analīze" in brief

    def test_covers_date_range(self, briefs_db, tmp_path):
        brief = generate_weekly_brief(db_path=briefs_db, week_start="2026-04-06",
                                      chart_dir=str(tmp_path))
        assert "2026-04-06" in brief
        assert "2026-04-12" in brief

    def test_counts_within_week(self, briefs_db, tmp_path):
        brief = generate_weekly_brief(db_path=briefs_db, week_start="2026-04-06",
                                      chart_dir=str(tmp_path))
        # New skeleton emits a deterministic WEEKLY_STATS marker; 3 position claims.
        assert "positions=3" in brief
        assert "## Nedēļa skaitļos" in brief

    def test_empty_week(self, empty_briefs_db, tmp_path):
        brief = generate_weekly_brief(db_path=empty_briefs_db, week_start="2026-04-06",
                                      chart_dir=str(tmp_path))
        assert "positions=0" in brief
        assert "## Nedēļas stāsts" in brief


class TestStripVisualBriefBlock:
    def test_removes_visual_block_and_html_comments(self):
        from src.briefs import strip_visual_brief_block
        content = (
            "# Dienas analīze — 2026-08-12\n\n"
            "## Galvenais\n\n"
            "<!-- DIENAS STATS (iekšēja piezīme): 610 dokumenti · 42 pozīcijas -->\n\n"
            "- Punkts viens.\n\n"
            "## Vizuālais brief\n\n"
            "- **Tēma:** Droni\n"
            "- **Galvenā tēze:** Tēze\n"
            "- **Skaitlis:** –\n"
            "- **Metaforas hint:** kaste\n"
        )
        out = strip_visual_brief_block(content)
        assert "DIENAS STATS" not in out
        assert "<!--" not in out
        assert "Vizuālais brief" not in out
        assert "- Punkts viens." in out

    def test_keeps_context_box_html(self):
        from src.briefs import strip_visual_brief_block
        content = (
            "# X\n\n"
            '<div class="context-box">\n<div class="context-label">Konteksts</div>\n'
            "Teksts.\n</div>\n"
        )
        out = strip_visual_brief_block(content)
        assert '<div class="context-box">' in out
        assert "Teksts." in out
