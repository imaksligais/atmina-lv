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
            "VALUES (1, 2, 1, 'spriedze', 'Budžets un finanses', ?, 'https://x.lv/9', '2026-04-07 12:00:00')",
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
        db.execute("INSERT INTO documents (id, scraped_at, platform) VALUES (4, '2026-04-07', 'vestnesis')")
        db.execute("INSERT INTO documents (id, scraped_at, platform) VALUES (5, '2026-04-07', 'x_mention')")
        db.commit()
        db.close()
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        assert "5 dokumenti (2 web + 2 Twitter/X + 1 vestnesis)" in brief

    def test_unknown_platform_reported_as_citi_not_swallowed(self, briefs_db):
        """A platform the buckets don't know must show up as `citi`, not
        vanish into an adjacent bucket — report the denominator."""
        db = sqlite3.connect(briefs_db)
        db.execute("INSERT INTO documents (id, scraped_at, platform) VALUES (4, '2026-04-07', 'web_scraper')")
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
            platform TEXT,
            source_domain TEXT
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
            document_id INTEGER,
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

        INSERT INTO documents (id, scraped_at, platform) VALUES (1, '2026-04-07', 'web');
        INSERT INTO documents (id, scraped_at, platform) VALUES (2, '2026-04-07', 'web');
        INSERT INTO documents (id, scraped_at, platform) VALUES (3, '2026-04-07', 'twitter');

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
        CREATE TABLE documents (id INTEGER PRIMARY KEY, scraped_at TEXT, platform TEXT, source_domain TEXT);
        CREATE TABLE tracked_politicians (id INTEGER PRIMARY KEY, name TEXT, party TEXT, relationship_type TEXT);
        CREATE TABLE claims (id INTEGER PRIMARY KEY, opponent_id INTEGER, document_id INTEGER, topic TEXT, stance TEXT, source_url TEXT, stated_at TEXT, created_at TEXT, salience REAL, claim_type TEXT NOT NULL DEFAULT 'position');
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
            "VALUES (1, 2, 'Uzbrukums', 'NATO', 'Test tension', '2026-04-07 12:00:00')"
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
    bare while ``routine.py`` read it shifted to LV. Between 21:00 and 23:59 UTC
    — exactly when the evening routine runs — the two disagree, so the same
    tension could appear in the brief for one day and be reported missing by the
    routine status for the other. Observed 2026-07-29 on tension #175.

    **Restamped 2026-08-27, and the reason matters.** The original STAMP was
    21:30 UTC (= 00:30 LV next day). Under the routine-day window introduced
    that day (``src.briefs.routine_day_window``), that stamp no longer
    DISCRIMINATES: both the correct LV reading and the buggy bare reading land
    on routine day 2026-04-07, because the window's 05:00 cut swallows the
    difference. A test that cannot tell the two apart is not a timezone gate any
    more, it is decoration — the exact class ``CLAUDE.md`` forbids.

    The stamps that still discriminate are those the +3h shift carries across
    the 05:00 cut, i.e. UTC 02:00–05:00. 03:00 UTC = 06:00 LV → routine day
    2026-04-07; read bare, 03:00 falls before the cut and lands on 2026-04-06.
    Same defect, same direction, still observable. The subject-day question this
    class does NOT cover now lives in ``TestRoutineDayWindow`` below.
    """

    # 06:00 LV on 2026-04-07 at UTC+3 → routine day 04-07.
    # Read bare (03:00 treated as LV) it falls before the 05:00 cut → 04-06.
    STAMP = "2026-04-07 03:00:00"

    @staticmethod
    def _both_days(db_path, stamp):
        """The ROUTINE day under each reading — correct (shifted) and bare.

        Asks SQLite for the two wall-clocks so the test states no assumption
        about the host TZ, then applies the 05:00 cut itself. Comparing calendar
        days here would be the decoration trap described in the class docstring:
        at this stamp both calendar days are 2026-04-07 and the test would
        skip itself into permanent green.
        """
        from datetime import datetime as _dt, timedelta as _td

        from src.briefs import ROUTINE_DAY_START_HOUR

        db = sqlite3.connect(db_path)
        raw, lv = db.execute(
            "SELECT datetime(?), datetime(?, 'localtime')", (stamp, stamp)
        ).fetchone()
        db.close()

        def routine_day(wall: str) -> str:
            moment = _dt.strptime(wall, "%Y-%m-%d %H:%M:%S")
            if moment.hour < ROUTINE_DAY_START_HOUR:
                moment -= _td(days=1)
            return moment.date().isoformat()

        return routine_day(raw), routine_day(lv)

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

    def test_tension_belongs_to_the_routine_day_of_its_LV_moment(self, empty_briefs_db):
        self._seed(empty_briefs_db)
        raw_day, lv_day = self._both_days(empty_briefs_db, self.STAMP)
        if raw_day == lv_day:
            pytest.skip("host TZ is UTC — the UTC/LV routine-day split is unobservable here")

        on_lv_day = generate_daily_brief(db_path=empty_briefs_db, date=lv_day)
        assert "Vakara spriedzes apraksts" in on_lv_day, (
            f"a tension stored at {self.STAMP} UTC (= 06:00 LV) must appear in the "
            f"brief for routine day {lv_day}"
        )

    def test_tension_absent_from_the_unshifted_day(self, empty_briefs_db):
        """The half that actually failed before the fix."""
        self._seed(empty_briefs_db)
        raw_day, lv_day = self._both_days(empty_briefs_db, self.STAMP)
        if raw_day == lv_day:
            pytest.skip("host TZ is UTC — the UTC/LV day boundary is unobservable here")

        on_raw_day = generate_daily_brief(db_path=empty_briefs_db, date=raw_day)
        assert "Vakara spriedzes apraksts" not in on_raw_day, (
            "reading the UTC column without shifting it to LV leaked the tension "
            f"into the previous routine day ({raw_day})"
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
            "'https://x.lv/t60', '2026-04-07 12:00:00')"
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
            "'https://x.lv/t61', '2026-04-07 12:00:00')"
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
                "VALUES (1, 2, 'Uzbrukums', ?, 'spriedze', '2026-04-07 12:00:00')",
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


class TestSkeletonEmitsItsDenominators:
    """A section that simply isn't there cannot be told apart from one that found
    nothing — and on 2026-08-26 the difference was real.

    Tensions #244/#245 (created 00:16 LV, i.e. with the NEXT day's `created_at`)
    and context notes #503/#504 never reached the skeleton, and there was no
    empty table, no zero row and no warning to say so. `@brief-writer` restored
    them by hand ONLY because the orchestrator explicitly said they'd be missing.
    Without that warning the agent had no way to know anything was absent.

    The zero goes in an HTML comment, not a rendered table: the skeleton's agent
    reads raw markdown (same shape as the DIENAS STATS block), while an empty
    "Spriedzes" table on the published page would be noise.
    """

    def test_zero_tensions_is_stated_not_implied(self, empty_briefs_db):
        out = generate_daily_brief(db_path=empty_briefs_db, date="2026-04-07")
        assert "SPRIEDZES: 0" in out, (
            "a day with no tensions must SAY so — silence is what hid the "
            "2026-08-26 omission"
        )

    def test_context_note_denominator_is_always_emitted(self, empty_briefs_db):
        out = generate_daily_brief(db_path=empty_briefs_db, date="2026-04-07")
        assert "KONTEKSTA PIEZĪMES: 0" in out, out[-800:]

    def test_the_zero_note_stays_out_of_the_rendered_page(self, empty_briefs_db):
        """It must be a comment, so the public render strips it (F3f.4 path)."""
        from src.briefs import strip_visual_brief_block

        out = generate_daily_brief(db_path=empty_briefs_db, date="2026-04-07")
        public = strip_visual_brief_block(out)
        assert "SPRIEDZES: 0" not in public
        assert "KONTEKSTA PIEZĪMES" not in public

    def test_a_real_tension_still_renders_its_table(self, briefs_db):
        """The denominator must not replace the section when there IS something."""
        db = sqlite3.connect(briefs_db)
        db.execute(
            "INSERT INTO political_tensions (source_pid, target_pid, tension_type, "
            "topic, description, source_url, created_at) "
            "VALUES (1, 2, 'Uzbrukums', 'NATO', 'Reāls spriedzes apraksts', "
            "'https://ex.lv/t', ?)",
            (_utc_stamp_for_lv_day(briefs_db, "2026-04-07"),),
        )
        db.commit()
        db.close()
        out = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        assert "## Spriedzes" in out
        assert "Reāls spriedzes apraksts" in out
        assert "SPRIEDZES: 0" not in out


def _utc_stamp_for_lv_day(db_path, lv_day):
    """A UTC `created_at` whose 'localtime' date is `lv_day`, asked of SQLite itself.

    political_tensions.created_at is UTC (schema.sql) and the brief reads it with
    'localtime'. Hard-coding a stamp would make the test assert the host TZ.
    """
    db = sqlite3.connect(db_path)
    stamp = db.execute(
        "SELECT datetime(? || ' 12:00:00', 'utc')", (lv_day,)
    ).fetchone()[0]
    db.close()
    return stamp


class TestRoutineDayWindow:
    """A routine day is not a calendar day (2026-08-27).

    The evening routine routinely finishes after midnight — 26 of 130 stored
    briefs did — so a tension written at 00:16 LV is the output of the PREVIOUS
    day's work. `brief_subject_date()` settled this for the brief's own identity
    long ago; `political_tensions` and `context_notes` never followed, and the
    gap was a SILENT omission: on 2026-08-26 tensions #244/#245 and notes
    #503/#504 simply were not in the skeleton, with no error and no empty table.

    The 05:00 cut is measured, not chosen: in the LV-hour histogram of every row
    these queries read there are 2 tension rows of 226 in 03:00–05:00, 2 context
    notes, and 0 daily briefs — and all of those are themselves late-night
    sessions, i.e. on the correct side of the cut.
    """

    def test_window_is_half_open_and_starts_at_the_cut(self):
        from src.briefs import routine_day_window

        start, end = routine_day_window("2026-08-26")
        assert start == "2026-08-26 05:00:00"
        assert end == "2026-08-27 05:00:00"

    def test_every_moment_maps_to_exactly_one_routine_day(self):
        """Total function: no double-counting, no gap — which is why this needs
        no `already_briefed` guard of the kind the claims side carries."""
        from src.briefs import routine_day_window

        prev_end = routine_day_window("2026-08-25")[1]
        start, _ = routine_day_window("2026-08-26")
        assert prev_end == start, "consecutive windows must abut exactly"

    def test_after_midnight_tension_lands_on_the_previous_routine_day(
        self, empty_briefs_db
    ):
        """The case that cost the 2026-08-26 skeleton its Spriedzes table."""
        stamp = _utc_stamp_for_lv_moment(empty_briefs_db, "2026-08-27 00:16:00")
        _seed_tension(empty_briefs_db, "Pēcpusnakts spriedzes apraksts", stamp)

        on_work_day = generate_daily_brief(db_path=empty_briefs_db, date="2026-08-26")
        assert "Pēcpusnakts spriedzes apraksts" in on_work_day, (
            "a tension written at 00:16 LV is the previous routine day's output"
        )

    def test_after_midnight_tension_is_not_also_on_the_calendar_day(
        self, empty_briefs_db
    ):
        """The other half — a window that overlaps would double-publish."""
        stamp = _utc_stamp_for_lv_moment(empty_briefs_db, "2026-08-27 00:16:00")
        _seed_tension(empty_briefs_db, "Pēcpusnakts spriedzes apraksts", stamp)

        on_calendar_day = generate_daily_brief(db_path=empty_briefs_db, date="2026-08-27")
        assert "Pēcpusnakts spriedzes apraksts" not in on_calendar_day

    def test_morning_block_row_stays_on_its_own_day(self, empty_briefs_db):
        """06:00 LV is the next day's ingest block, not the previous night."""
        stamp = _utc_stamp_for_lv_moment(empty_briefs_db, "2026-08-27 06:00:00")
        _seed_tension(empty_briefs_db, "Rīta spriedzes apraksts", stamp)

        assert "Rīta spriedzes apraksts" in generate_daily_brief(
            db_path=empty_briefs_db, date="2026-08-27")
        assert "Rīta spriedzes apraksts" not in generate_daily_brief(
            db_path=empty_briefs_db, date="2026-08-26")

    def test_after_midnight_context_note_lands_on_the_previous_routine_day(
        self, empty_briefs_db
    ):
        """context_notes.created_at is LV — same rule, no 'localtime' shift."""
        db = sqlite3.connect(empty_briefs_db)
        db.execute(
            "INSERT INTO context_notes (note_type, topic, content, created_at) "
            "VALUES ('context', 'NATO', ?, '2026-08-27 00:24:00')",
            ("Pēcpusnakts tendences teksts",),
        )
        db.commit()
        db.close()

        out = generate_daily_brief(db_path=empty_briefs_db, date="2026-08-26")
        assert "Pēcpusnakts tendences teksts" in out


def _seed_tension(db_path, description, created_at):
    db = sqlite3.connect(db_path)
    db.execute("INSERT OR IGNORE INTO tracked_politicians (id, name, party, relationship_type) "
               "VALUES (1, 'Avota Politiķis', 'JV', 'tracked')")
    db.execute("INSERT OR IGNORE INTO tracked_politicians (id, name, party, relationship_type) "
               "VALUES (2, 'Mērķa Politiķis', 'LPV', 'tracked')")
    db.execute(
        "INSERT INTO political_tensions (source_pid, target_pid, tension_type, topic, "
        "description, source_url, created_at) "
        "VALUES (1, 2, 'spriedze', 'NATO', ?, 'https://x.com/a/status/1', ?)",
        (description, created_at),
    )
    db.commit()
    db.close()


def _utc_stamp_for_lv_moment(db_path, lv_moment):
    """The UTC value whose 'localtime' rendering is `lv_moment`, per SQLite.

    Computed, never hard-coded: `political_tensions.created_at` is UTC and the
    brief reads it shifted, so a literal stamp would silently assert the host TZ
    instead of the rule under test.
    """
    db = sqlite3.connect(db_path)
    stamp = db.execute("SELECT datetime(?, 'utc')", (lv_moment,)).fetchone()[0]
    db.close()
    return stamp


class TestBlocTableExplainer:
    """«Koalīcija vs Opozīcija» tabulai seko pastāvīga viena rinda, kas
    paskaidro, pēc kā blokus dala (2026-09-05, r/atminaLV jautājums pie 09-01
    pārskata: intuitīvi «visi ārpus koalīcijas = opozīcija»). Trīs nesēji —
    dienas skelets, nedēļas skelets un renderis (glabātajiem pārskatiem)."""

    def _after_table(self, brief):
        from src.briefs import BLOC_TABLE_EXPLAINER
        head = brief.index("## Koalīcija vs Opozīcija")
        tail = brief[head:]
        assert BLOC_TABLE_EXPLAINER in tail
        table_end = tail.rindex("|", 0, tail.index(BLOC_TABLE_EXPLAINER))
        assert "\n" in tail[table_end:tail.index(BLOC_TABLE_EXPLAINER)]
        return tail

    def test_daily_skeleton_carries_explainer_once(self, briefs_db):
        from src.briefs import BLOC_TABLE_EXPLAINER
        brief = generate_daily_brief(db_path=briefs_db, date="2026-04-07")
        self._after_table(brief)
        assert brief.count(BLOC_TABLE_EXPLAINER) == 1

    def test_weekly_skeleton_carries_explainer_once(self, briefs_db):
        from src.briefs import BLOC_TABLE_EXPLAINER
        brief = generate_weekly_brief(db_path=briefs_db, week_start="2026-04-06",
                                      chart_dir="output/images/briefs")
        self._after_table(brief)
        assert brief.count(BLOC_TABLE_EXPLAINER) == 1

    def test_stored_brief_without_explainer_gets_it_at_render_time(self):
        from src.briefs import BLOC_TABLE_EXPLAINER, add_bloc_table_explainer
        from src.render.blog import _brief_markdown_to_html
        stored = (
            "# Dienas analīze — 2026-08-01\n\n## Koalīcija vs Opozīcija\n\n"
            "| Bloks | Pozīcijas |\n|-------|-----------|\n| Koalīcija | 3 |\n\n"
            "Sintēzes rindkopa zem tabulas.\n"
        )
        once = add_bloc_table_explainer(stored)
        assert once.count(BLOC_TABLE_EXPLAINER) == 1
        assert once.index(BLOC_TABLE_EXPLAINER) < once.index("Sintēzes rindkopa")
        assert add_bloc_table_explainer(once) == once, "nav idempotents"
        html = _brief_markdown_to_html(stored)
        assert "Bez Saeimas frakcijas" in html and html.count("bloc-explainer") == 1

    def test_no_table_no_explainer(self):
        from src.briefs import BLOC_TABLE_EXPLAINER, add_bloc_table_explainer
        text = "# Dienas analīze — 2026-08-01\n\n## Galvenais\n\n- x\n"
        assert BLOC_TABLE_EXPLAINER not in add_bloc_table_explainer(text)
