-- Pre-refactor F2 schema dump captured 2026-04-29.
-- Source: built via init_db() before DDL extraction. Used by
-- tests/test_schema.py::test_schema_sql_matches_pre_refactor_dump
-- to ensure src/schema.sql refactor preserves DDL byte-identically.

CREATE INDEX idx_analyses_opponent ON analyses(opponent_id, created_at);
CREATE INDEX idx_brief_images_note_approved ON brief_images(note_id, approved, id DESC);
CREATE INDEX idx_chunks_document ON document_chunks(document_id);
CREATE INDEX idx_claims_claim_type ON claims(claim_type);
CREATE INDEX idx_claims_compound ON claims(opponent_id, topic, stated_at);
CREATE INDEX idx_claims_document_id ON claims(document_id);
CREATE INDEX idx_claims_opp_type_topic ON claims(opponent_id, claim_type, topic);
CREATE INDEX idx_claims_opponent_speaker ON claims(opponent_id, speaker_id);
CREATE INDEX idx_claims_opponent_topic ON claims(opponent_id, topic);
CREATE INDEX idx_claims_party ON claims(party_id);
CREATE INDEX idx_claims_speaker ON claims(speaker_id);
CREATE INDEX idx_claims_stated_at ON claims(stated_at);
CREATE INDEX idx_context_notes_opponent ON context_notes(opponent_id, topic);
CREATE INDEX idx_context_notes_type ON context_notes(note_type);
CREATE INDEX idx_contradictions_opponent ON contradictions(opponent_id, detected_at);
CREATE INDEX idx_documents_hash ON documents(content_hash);
CREATE INDEX idx_documents_simhash ON documents(simhash);
CREATE INDEX idx_dp_document ON document_politicians(document_id);
CREATE INDEX idx_dp_politician ON document_politicians(politician_id, role);
CREATE INDEX idx_external_profiles_opp ON external_profiles(opponent_id);
CREATE INDEX idx_knab_alerts_type ON knab_alerts(alert_type, severity);
CREATE INDEX idx_knab_declarations_party ON knab_declarations(party, year);
CREATE INDEX idx_knab_donations_date ON knab_donations(date);
CREATE INDEX idx_knab_donations_donor ON knab_donations(donor_id);
CREATE INDEX idx_knab_donations_party ON knab_donations(party);
CREATE INDEX idx_knab_donors_politician ON knab_donors(politician_id);
CREATE INDEX idx_logs_action ON logs(action, status);
CREATE INDEX idx_logs_timestamp ON logs(timestamp);
CREATE INDEX idx_mention_class_doc ON mention_classifications(document_id);
CREATE INDEX idx_mention_class_status ON mention_classifications(reply_status);
CREATE INDEX idx_parties_short ON parties(short_name);
CREATE UNIQUE INDEX idx_social_accounts_unique
    ON social_accounts(opponent_id, platform, handle);
CREATE INDEX idx_social_drafts_pillar ON social_drafts(pillar);
CREATE INDEX idx_social_drafts_status ON social_drafts(status);
CREATE INDEX idx_social_feed_type ON social_accounts(feed_type);
CREATE INDEX idx_social_opponent ON social_accounts(opponent_id);
CREATE TABLE analyses (
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
CREATE TABLE brief_images (
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
CREATE VIRTUAL TABLE claim_vectors
        USING vec0(claim_id INTEGER PRIMARY KEY, embedding float[384]);
CREATE TABLE "claim_vectors_chunks"(chunk_id INTEGER PRIMARY KEY AUTOINCREMENT,size INTEGER NOT NULL,validity BLOB NOT NULL,rowids BLOB NOT NULL);
CREATE TABLE "claim_vectors_info" (key text primary key, value any);
CREATE TABLE "claim_vectors_rowids"(rowid INTEGER PRIMARY KEY AUTOINCREMENT,id,chunk_id INTEGER,chunk_offset INTEGER);
CREATE TABLE "claim_vectors_vector_chunks00"(rowid PRIMARY KEY,vectors BLOB NOT NULL);
CREATE TABLE claims (
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE context_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opponent_id INTEGER REFERENCES tracked_politicians(id),
    topic TEXT,
    note_type TEXT,
    content TEXT NOT NULL,
    source TEXT,
    expires_at DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
, visual_brief_json TEXT);
CREATE TABLE contradictions (
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
CREATE TABLE document_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER REFERENCES documents(id),
    chunk_index INTEGER,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE document_politicians (
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    politician_id INTEGER NOT NULL REFERENCES tracked_politicians(id),
    role TEXT NOT NULL DEFAULT 'subject',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (document_id, politician_id, role)
);
CREATE VIRTUAL TABLE document_vectors
        USING vec0(chunk_id INTEGER PRIMARY KEY, embedding float[384]);
CREATE TABLE "document_vectors_chunks"(chunk_id INTEGER PRIMARY KEY AUTOINCREMENT,size INTEGER NOT NULL,validity BLOB NOT NULL,rowids BLOB NOT NULL);
CREATE TABLE "document_vectors_info" (key text primary key, value any);
CREATE TABLE "document_vectors_rowids"(rowid INTEGER PRIMARY KEY AUTOINCREMENT,id,chunk_id INTEGER,chunk_offset INTEGER);
CREATE TABLE "document_vectors_vector_chunks00"(rowid PRIMARY KEY,vectors BLOB NOT NULL);
CREATE TABLE documents (
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
, published_at TIMESTAMP, reviewed_at TIMESTAMP, reply_count INTEGER, retweet_count INTEGER, favorite_count INTEGER, title TEXT, summary TEXT, is_paywall BOOLEAN DEFAULT FALSE);
CREATE TABLE external_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            opponent_id INTEGER NOT NULL REFERENCES tracked_politicians(id),
            platform TEXT NOT NULL,
            url TEXT NOT NULL,
            handle TEXT,
            display_label TEXT,
            last_fetched TIMESTAMP,
            last_post_id TEXT,
            active BOOLEAN DEFAULT TRUE,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(opponent_id, platform, url)
        );
CREATE TABLE knab_alerts (
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
CREATE TABLE knab_declarations (
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
CREATE TABLE knab_donations (
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
CREATE TABLE knab_donors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    personal_id_masked TEXT,
    politician_id INTEGER REFERENCES tracked_politicians(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, personal_id_masked)
);
CREATE TABLE logs (
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
CREATE TABLE mention_classifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER REFERENCES documents(id),
    category TEXT NOT NULL,
    priority INTEGER DEFAULT 0,
    reply_draft TEXT,
    reply_status TEXT DEFAULT 'pending',
    notes TEXT,
    created_at TIMESTAMP
);
CREATE TABLE metadata (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE oppo_briefs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opponent_id INTEGER REFERENCES tracked_politicians(id),
    period_start DATE,
    period_end DATE,
    vulnerabilities TEXT,
    contradictions_cited TEXT,
    strongest_attacks TEXT,
    suggested_counters TEXT,
    narrative_frames TEXT,
    brief_markdown TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE parties (
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
CREATE TABLE political_tensions (
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
CREATE TABLE social_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opponent_id INTEGER REFERENCES tracked_politicians(id),
    platform TEXT,
    handle TEXT,
    api_tier TEXT DEFAULT 'free',
    last_fetched TIMESTAMP,
    last_post_id TEXT,
    active BOOLEAN DEFAULT TRUE
, feed_type TEXT DEFAULT 'first_party');
CREATE TABLE social_drafts (
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
CREATE TABLE sources (
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
CREATE TABLE sqlite_sequence(name,seq);
CREATE TABLE tracked_politicians (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    party TEXT,
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
, x_handle TEXT);
