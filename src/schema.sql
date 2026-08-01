-- atmina static schema — extracted from src/db.py::init_db() in Phase 2 of
-- refactor-plan-2026-04-29.md. This file contains the idempotent CREATE TABLE,
-- CREATE INDEX statements plus per-DB PRAGMAs for the static (non-vec0) DDL.
--
-- Migrations (PRAGMA-conditional ALTER TABLE etc.) remain in src/db.py because
-- sqlite < 3.35 lacks "ALTER TABLE ADD COLUMN IF NOT EXISTS"; the Python
-- conditional pattern is portable and explicit.
--
-- Loaded by src/db.py::init_db() via conn.executescript(). The vec0 virtual
-- tables (document_vectors, claim_vectors) are NOT in this file — see the
-- carve-out comment at the bottom for why and how they are handled.

PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA busy_timeout=5000;

CREATE TABLE IF NOT EXISTS tracked_politicians (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    party TEXT,
    -- role iekavu piedēkļi ir FAKTU nesēji, ne brīvs stils (konvencija
    -- fiksēta 2026-08-12): "(demisionējis/-usi)" = amats beidzās ar valdības
    -- kolektīvo demisiju; "(atkāpies/-usies)" = individuāla atkāpšanās no
    -- amata (piem., Sprūds 2026-05-10 pēc Siliņas ultimāta, PIRMS valdības
    -- krišanas — sk. wiki/synthesis/silinas-valdibas-krisana-2026-05.md).
    -- Neizlīdzināt uz vienu formu: tas dzēstu atšķirību starp abiem faktiem.
    role TEXT,
    name_forms TEXT DEFAULT '[]',
    keywords TEXT DEFAULT '[]',
    negative_patterns TEXT DEFAULT '[]',
    -- LEGACY: per-politician tracking role, not a coalition flag.
    -- Only 'inactive' and the audience values (journalist,
    -- influencer, neutral) drive behavior — 'tracked' is the
    -- semantically neutral default for new rows. Historical rows
    -- may still hold opponent/coalition_partner/potential_ally
    -- from the platform's MMN-centric origin; those values are
    -- treated identically to 'tracked' everywhere. Coalition
    -- membership lives in parties.coalition_status; use
    -- src.coalition.party_status() to classify.
    relationship_type TEXT DEFAULT 'tracked',
    tracking_config TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE NOT NULL,
    name TEXT,
    tier INTEGER,
    fetcher_mode TEXT DEFAULT 'fetcher',
    rate_limit_seconds INTEGER DEFAULT 60,
    legal_status TEXT,
    legal_notes TEXT,
    last_tos_review DATE,
    last_scraped TIMESTAMP,
    consecutive_failures INTEGER DEFAULT 0,
    fallback_source_id INTEGER REFERENCES sources(id),
    active BOOLEAN DEFAULT TRUE
);

-- NB: at runtime, src/db.py + scripts/migrate_external_profiles.py add to this
-- table `feed_type TEXT DEFAULT 'first_party'` (idempotent ALTER) and a
-- `UNIQUE INDEX idx_social_accounts_unique(opponent_id, platform, handle)`.
-- They are intentionally NOT in this base CREATE: test_migrate_external_profiles.py
-- exercises the pre-migration, dup-tolerant state. The deployed DB has both —
-- this is the `UNIQUE (opponent_id, platform, handle)` referenced by CLAUDE.md #11.
CREATE TABLE IF NOT EXISTS social_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opponent_id INTEGER REFERENCES tracked_politicians(id),
    platform TEXT,
    handle TEXT,
    api_tier TEXT DEFAULT 'free',
    last_fetched TIMESTAMP,
    last_post_id TEXT,
    active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    content_hash TEXT NOT NULL UNIQUE,
    simhash INTEGER,
    source_id INTEGER REFERENCES sources(id),
    platform TEXT DEFAULT 'web',
    is_auto_caption BOOLEAN DEFAULT FALSE,
    near_dupe_of INTEGER REFERENCES documents(id),
    source_domain TEXT,
    source_url TEXT,
    archive_path TEXT,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    word_count INTEGER,
    language TEXT DEFAULT 'lv'
);

CREATE TABLE IF NOT EXISTS document_politicians (
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    politician_id INTEGER NOT NULL REFERENCES tracked_politicians(id),
    role TEXT NOT NULL DEFAULT 'subject',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (document_id, politician_id, role)
);

CREATE TABLE IF NOT EXISTS document_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER REFERENCES documents(id),
    chunk_index INTEGER,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opponent_id INTEGER REFERENCES tracked_politicians(id),
    period_start DATE,
    period_end DATE,
    sentiment_score REAL,
    key_topics TEXT,
    notable_quotes TEXT,
    position_shifts TEXT,
    brief_markdown TEXT,
    confidence REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS claims (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opponent_id INTEGER REFERENCES tracked_politicians(id),
    document_id INTEGER REFERENCES documents(id),
    topic TEXT NOT NULL,
    stance TEXT NOT NULL,
    quote TEXT,
    confidence REAL,
    reasoning TEXT,
    salience REAL DEFAULT 0.5,
    source_url TEXT,
    stated_at TIMESTAMP,
    claim_type TEXT NOT NULL DEFAULT 'position',
    -- speaker_id attributes authorship separately from the subject
    -- (opponent_id). NULL / = opponent_id => first-party; non-NULL and
    -- != opponent_id => third-party commentary (CLAUDE.md #5). Added to
    -- the live DB via the ALTER migration in src/db.py (idempotent,
    -- PRAGMA-guarded) ahead of schema.sql; declared here so fresh DBs
    -- built from schema.sql alone match prod.
    speaker_id INTEGER REFERENCES tracked_politicians(id),
    -- party_id attributes a claim to a PARTY rather than an individual.
    -- Used for party election-program promises (claim_type='program_promise'):
    -- party_id = the party, opponent_id = the list leader (program is grouped
    -- to the party by party_id, kept OUT of the leader's personal positions by
    -- claim_type filtering). NULL for all ordinary politician claims. Added to
    -- the live DB via the ALTER migration in src/db.py (idempotent,
    -- PRAGMA-guarded) ahead of schema.sql; declared here so fresh DBs match prod.
    party_id INTEGER REFERENCES parties(id),
    -- review_status is DERIVED from `reasoning` by the two triggers below —
    -- never write it by hand. 'needs_review' | 'reviewed' | NULL. It exists
    -- because the review flag used to live only inside the reasoning prose,
    -- where its FORM drifted (REVIEWED -> Izvērtēts -> REVIEWED) and its
    -- POSITION drifted (20 of 119 open rows prefixed, so the anchored
    -- `LIKE 'NEEDS_REVIEW%'` saw 17 % of the queue). Added to the live DB via
    -- the ALTER migration in src/db.py (idempotent, PRAGMA-guarded); declared
    -- here so fresh DBs match prod.
    review_status TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS contradictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opponent_id INTEGER REFERENCES tracked_politicians(id),
    claim_old_id INTEGER REFERENCES claims(id),
    claim_new_id INTEGER REFERENCES claims(id),
    topic TEXT NOT NULL,
    summary TEXT NOT NULL,
    severity TEXT,
    salience REAL DEFAULT 0.5,
    reviewed BOOLEAN DEFAULT FALSE,
    confirmed BOOLEAN DEFAULT FALSE,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- created_at here is UTC, NOT LV — the odd one out. `claims`, `context_notes`
-- and friends are written explicitly with now_lv(); this column relies on
-- SQLite's DEFAULT CURRENT_TIMESTAMP, which is UTC. So every DATE-scoped read
-- must pass 'localtime' to get the Latvian day:
--     DATE(created_at, 'localtime') = ?     -- correct
--     DATE(created_at) = ?                  -- off by a day for 21:00-23:59 UTC
-- Between 21:00 and 23:59 UTC (= 00:00-02:59 LV next day) the two disagree,
-- which is exactly when the evening routine runs. src/briefs.py read it bare
-- until 2026-07-30 and would have attributed such a tension to the previous
-- LV day; src/routine.py read it correctly, so the daily brief and the routine
-- status could disagree about the same row. Readers that only ORDER BY it
-- (render/politicians.py, render/parties.py, wiki.py) need no modifier.
CREATE TABLE IF NOT EXISTS political_tensions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_pid INTEGER REFERENCES tracked_politicians(id),
    target_pid INTEGER REFERENCES tracked_politicians(id),
    topic TEXT NOT NULL,
    description TEXT NOT NULL,
    tension_type TEXT DEFAULT 'spriedze',
    source_url TEXT,
    target_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS social_drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pillar TEXT NOT NULL CHECK(pillar IN ('pretrunas', 'stats', 'highlights')),
    text TEXT NOT NULL,
    image_path TEXT,
    source_data_json TEXT NOT NULL,
    score REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK(status IN ('pending', 'approved', 'rejected', 'revising', 'posted', 'failed')),
    telegram_msg_id TEXT,
    telegram_chat_id TEXT,
    revision_count INTEGER NOT NULL DEFAULT 0,
    parent_draft_id INTEGER REFERENCES social_drafts(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    posted_at TIMESTAMP,
    tweet_id TEXT,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_social_drafts_status ON social_drafts(status);
CREATE INDEX IF NOT EXISTS idx_social_drafts_pillar ON social_drafts(pillar);

-- oppo_briefs un mention_classifications (politracker mantojums) izmestas 2026-07-29 —
-- sk. data/migrate_drop_politracker_tables_2026-07-29.sql un CHANGELOG.

CREATE TABLE IF NOT EXISTS context_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opponent_id INTEGER REFERENCES tracked_politicians(id),
    topic TEXT,
    note_type TEXT,
    content TEXT NOT NULL,
    source TEXT,
    expires_at DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- brief_images: pārskatu plakātu ģenerēšanas audita rindas (note_id →
-- context_notes). DDL 2026-08-21 promovēts no db.py migrācijas bloka, lai
-- kolonnu konvencijas stāvētu pie deklarācijas; db.py bloks paliek kā
-- bezdarbības sargs vecākām DB, kurām tabulas vēl nav.
--
-- image_path konvencija (normalizēta 2026-08-21, data/fix_brief_image_paths_2026-08-21.sql):
--   SITE-relatīvs ceļs pret deploy sakni (= output/atmina/), t.i. tieši tas,
--   kas kļūst par URL: "images/briefs/<fails>.png", "images/synthesis/<fails>.png".
--   Vēsturiskās izņēma klases, apzināti NAV migrētas:
--   - tukšs image_path = save_error_row() API-kļūdas audita rinda (approved=2,
--     cost_usd=0.0) — neceļu rādītājs;
--   - atsevišķas rindas var rādīt uz repo ceļu ārpus output koka
--     (piem. docs/tweet_bank/... — avots aukstajā arhīvā).
-- approved domēns:
--   -1 = aizstāts (error_message "superseded by id=N")
--    0 = gaida lēmumu — TOSTARP operatora atsaukts 1→0 (dabiskā atcelšanas
--        darbība; ja tajā pašā notē ir approved=1 brālis, vārts
--        _rejected_brief_stems() to ārstē kā noraidītu)
--    1 = apstiprināts (renderējamais hero)
--    2 = noraidīts / aizstāts kandidāts; ARĪ API-kļūdu rindas (tukšs ceļs)
--   Noraidījuma vārti lasa VISUS trīs kodējumus (-1, 2, 0-ar-brāli) —
--   sk. src/render/_orchestrator.py::_rejected_brief_stems.
CREATE TABLE IF NOT EXISTS brief_images (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    note_id       INTEGER NOT NULL REFERENCES context_notes(id),
    image_path    TEXT    NOT NULL,
    prompt        TEXT    NOT NULL,
    model         TEXT    NOT NULL,
    seed          INTEGER,
    aspect        TEXT    NOT NULL DEFAULT '16:9',
    width         INTEGER,
    height        INTEGER,
    generated_at  TEXT    NOT NULL,
    cost_usd      REAL    NOT NULL DEFAULT 0.039,
    approved      INTEGER NOT NULL DEFAULT 0,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_brief_images_note_approved
    ON brief_images(note_id, approved, id DESC);

CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    action TEXT NOT NULL,
    source_id INTEGER,
    opponent_id INTEGER,
    status TEXT DEFAULT 'success',
    duration_ms INTEGER,
    error_message TEXT,
    details TEXT,
    claude_model TEXT,
    prompt_hash TEXT
);

CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_dp_politician ON document_politicians(politician_id, role);
CREATE INDEX IF NOT EXISTS idx_dp_document ON document_politicians(document_id);
CREATE INDEX IF NOT EXISTS idx_claims_opponent_topic ON claims(opponent_id, topic);
CREATE INDEX IF NOT EXISTS idx_claims_stated_at ON claims(stated_at);
CREATE INDEX IF NOT EXISTS idx_claims_compound ON claims(opponent_id, topic, stated_at);
-- Lookups by source document (e.g. Ziņas render: topics-per-document). Without
-- this, WHERE document_id=? full-scans claims; after the 2026-05 saeima_vote
-- backfill grew claims to ~514k rows, render_news regressed from ~5s to ~16min.
CREATE INDEX IF NOT EXISTS idx_claims_document_id ON claims(document_id);
-- Present on the live DB but previously created by no code path (orphaned —
-- added in an ad-hoc session). Declared here so fresh + test DBs match prod.
-- idx_claims_opp_type_topic backs per-politician claim_type+topic filters
-- (contradiction checks, render facets); idx_claims_claim_type backs
-- claim_type COUNT/filter queries.
CREATE INDEX IF NOT EXISTS idx_claims_claim_type ON claims(claim_type);
CREATE INDEX IF NOT EXISTS idx_claims_opp_type_topic ON claims(opponent_id, claim_type, topic);
-- speaker_id lookups (commentator self-consistency, COALESCE(speaker_id,
-- opponent_id) resolution). Previously created only by the speaker_id ALTER
-- migration in src/db.py, so fresh DBs built from schema.sql alone lacked
-- them. Declared here so fresh + test DBs match prod.
CREATE INDEX IF NOT EXISTS idx_claims_speaker ON claims(speaker_id);
CREATE INDEX IF NOT EXISTS idx_claims_opponent_speaker ON claims(opponent_id, speaker_id);
-- NB: idx_claims_party (on party_id) is created only by the ALTER migration in
-- src/db.py, NOT here — this executescript runs before that migration, so an
-- index referencing party_id would fail on a live DB that predates the column.
-- Once every DB carries party_id it can move here (as speaker_id's index did).
CREATE INDEX IF NOT EXISTS idx_contradictions_opponent ON contradictions(opponent_id, detected_at);
CREATE INDEX IF NOT EXISTS idx_analyses_opponent ON analyses(opponent_id, created_at);
CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_logs_action ON logs(action, status);
CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(content_hash);
CREATE INDEX IF NOT EXISTS idx_documents_simhash ON documents(simhash);
CREATE INDEX IF NOT EXISTS idx_chunks_document ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_social_opponent ON social_accounts(opponent_id);
-- Load-bearing: store-social-account idempotency dedups on this triple
-- (CLAUDE.md #11). Previously created only by scripts/migrate_external_profiles.py,
-- so fresh/test DBs lacked it. Declared here so fresh + test DBs match prod.
CREATE UNIQUE INDEX IF NOT EXISTS idx_social_accounts_unique
    ON social_accounts(opponent_id, platform, handle);
CREATE INDEX IF NOT EXISTS idx_context_notes_opponent ON context_notes(opponent_id, topic);
CREATE INDEX IF NOT EXISTS idx_context_notes_type ON context_notes(note_type);

-- KNAB: Donors (unique persons)
CREATE TABLE IF NOT EXISTS knab_donors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    personal_id_masked TEXT,
    politician_id INTEGER REFERENCES tracked_politicians(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, personal_id_masked)
);

-- KNAB: Donations
CREATE TABLE IF NOT EXISTS knab_donations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    knab_id TEXT UNIQUE,
    donor_id INTEGER REFERENCES knab_donors(id),
    party TEXT NOT NULL,
    donation_type TEXT NOT NULL,
    amount_eur REAL NOT NULL,
    currency TEXT DEFAULT 'EUR',
    original_amount TEXT,
    donor_name TEXT NOT NULL,
    donor_pid_masked TEXT,
    date TEXT NOT NULL,
    detail_url TEXT,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- KNAB: Declarations (annual reports + election declarations)
CREATE TABLE IF NOT EXISTS knab_declarations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    knab_id TEXT UNIQUE,
    party TEXT NOT NULL,
    declaration_type TEXT NOT NULL,
    year INTEGER NOT NULL,
    date TEXT,
    detail_url TEXT,
    income_total REAL,
    income_donations REAL,
    income_membership REAL,
    income_state_budget REAL,
    expenses_total REAL,
    expenses_advertising REAL,
    expenses_salaries REAL,
    raw_data TEXT,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- KNAB: Alerts (anomalies detected by cross-referencing)
CREATE TABLE IF NOT EXISTS knab_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_type TEXT NOT NULL,
    severity TEXT DEFAULT 'info',
    party TEXT,
    donor_id INTEGER REFERENCES knab_donors(id),
    politician_id INTEGER REFERENCES tracked_politicians(id),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    data TEXT,
    reviewed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_knab_donations_party ON knab_donations(party);
CREATE INDEX IF NOT EXISTS idx_knab_donations_donor ON knab_donations(donor_id);
CREATE INDEX IF NOT EXISTS idx_knab_donations_date ON knab_donations(date);
CREATE INDEX IF NOT EXISTS idx_knab_donors_politician ON knab_donors(politician_id);
CREATE INDEX IF NOT EXISTS idx_knab_declarations_party ON knab_declarations(party, year);
CREATE INDEX IF NOT EXISTS idx_knab_alerts_type ON knab_alerts(alert_type, severity);

CREATE TABLE IF NOT EXISTS parties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    short_name TEXT NOT NULL UNIQUE,
    x_handle TEXT,
    website TEXT,
    ideology TEXT,
    coalition_status TEXT DEFAULT 'opposition',
    color TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_parties_short ON parties(short_name);

-- sqlite-vec virtual tables are NOT in this file — they are created via
-- separate db.execute() calls in src/db.py::init_db(). This is a CI mock
-- compatibility carve-out: tests/test_knab.py wraps the connection in
-- _SafeConnection to skip "vec0"-containing SQL when sqlite_vec is mocked
-- to a no-op. _SafeConnection only intercepts .execute(), not
-- .executescript() — so vec0 DDL must stay in db.execute calls.
