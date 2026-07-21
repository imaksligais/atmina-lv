# atmina — Architecture Documentation

_Auto-generated: 2026-04-14 by autoresearch:learn_

## Overview

atmina is a Latvian political transparency platform that scrapes news and social media, extracts political positions (pozīcijas) and contradictions (pretrunas) per politician, and renders an interactive public HTML site at atmina.lv.

**Key numbers (2026-04-14):** 147 politicians, 858 positions + 5458 Saeima votes, 10 contradictions, 13032 documents, 26 topics, 34 bills.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                         │
│  RSS/Web (26 sources)  │  X/Twitter (twikit)  │  Saeima    │
│  KNAB Finance          │  CSP Statistics       │            │
└──────────┬─────────────┴──────────┬────────────┴────────────┘
           │                        │
           ▼                        ▼
┌──────────────────────┐  ┌─────────────────────┐
│   INGESTION LAYER    │  │   SCRAPING LAYER    │
│  ingest.py           │  │  x_scraper.py       │
│  social.py           │  │  x_mentions.py      │
│  saeima.py           │  │  x_pool.py (5-slot) │
│  knab.py             │  │  csp/sync.py        │
└──────────┬───────────┘  └──────────┬──────────┘
           │                         │
           ▼                         ▼
┌──────────────────────────────────────────────────────────────┐
│                    STORAGE LAYER                              │
│  data/atmina.db (SQLite + WAL)    │  data/csp.db             │
│  22 tables + 2 sqlite-vec virtual │  4 tables                │
│  384-dim embeddings (e5-small)    │  10 CSP indicators       │
└──────────┬────────────────────────┴──────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────┐
│                   ANALYSIS LAYER (Claude Code)               │
│  @claim-extractor  →  @contradiction-hunter  →  @devils-adv │
│  analyze.py  │  tools.py  │  cross_check.py  │  briefs.py   │
│  confidence_drift.py  │  topic_map.py (26 groups)            │
└──────────┬───────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────┐
│                    OUTPUT LAYER                               │
│  generate.py → output/atmina/ (static HTML)                  │
│  wiki.py → wiki/ (Obsidian vault)                            │
│  briefs.py → context_notes (daily/weekly)                    │
│  wiki_writeback.py → wiki enrichment                         │
└──────────────────────────────────────────────────────────────┘
```

## Module Reference

### Core Database Layer

| Module | Purpose | Key Functions |
|--------|---------|---------------|
| `src/db.py` | SQLite persistence, vector search, document/claim storage | `init_db`, `get_db`, `insert_document`, `store_claim`, `store_contradiction`, `search_similar`, `search_similar_claims` |
| `src/models.py` | Pydantic v2 validation contracts | `PoliticianProfile`, `ScrapedContent`, `AnalysisResult`, `Claim`, `Contradiction`, `ContextNote` |
| `src/embeddings.py` | 384-dim multilingual embeddings (intfloat/multilingual-e5-small) | `embed_text`, `embed_batch`, `embed_document`, `chunk_text`, `lemmatize` |
| `src/coalition.py` | Party coalition/opposition classification from `parties` table | `get_coalition_map`, `party_status` |
| `src/topic_map.py` | 158 raw topics → 26 canonical groups with diacritics-aware matching | `normalize_topic`, `get_group_topics`, `get_all_group_names` |

### Ingestion & Scraping

| Module | Purpose | Key Functions |
|--------|---------|---------------|
| `src/ingest.py` | Web content pipeline: scrape → validate → match politicians → embed → store | `ingest_all`, `scrape_source`, `match_politicians`, `store_content`, `link_politicians_to_documents` |
| `src/social.py` | Social media orchestrator (X, YouTube, Facebook) | `fetch_all_twitter`, `fetch_all_mentions`, `fetch_all_social` |
| `src/x_scraper.py` | Twitter/X fetching via twikit with rate-limit rotation | `fetch_user_tweets`, `fetch_user_replies`, `fetch_all_x_accounts` |
| `src/x_mentions.py` | Batched @mention search across tracked politicians | `fetch_mentions` |
| `src/x_pool.py` | Round-robin pool of 5 authenticated twikit clients | `XClientPool`, `get_pool`, `reset_pool` |
| `src/ingest_log.py` | Audit trail in wiki/log-ingest.md | `append_ingest_entry`, `append_ingest_batch_summary` |

### Analysis & Quality

| Module | Purpose | Key Functions |
|--------|---------|---------------|
| `src/analyze.py` | Interactive analysis workflow for Claude Code | `get_pending_politicians`, `get_politician_documents`, `save_analysis` |
| `src/tools.py` | JSON-wrapped utilities for Claude Code integration | `retrieve_context`, `store_analysis`, `store_claim`, `store_contradiction`, `search_similar_claims`, `query_claims`, `get_contradictions` |
| `src/cross_check.py` | Weekly pairwise contradiction scanner using embedding similarity | `weekly_cross_check` |
| `src/confidence_drift.py` | Detects confidence inflation without source diversity | `check_confidence_drift` |
| `src/calibration.py` | Embedding/NLP pipeline validation with GO/NO_GO report | `run_calibration` |

### Specialized Data Sources

| Module | Purpose | Key Functions |
|--------|---------|---------------|
| `src/saeima/` | Parliament session scraper & vote tracker pakete (Playwright-based; 5 moduļi: schema/bills/parsing/claims/votes pēc F4 split) | `parse_agenda_snapshot`, `parse_vote_snapshot`, `process_vote_snapshot`, `generate_claims_from_votes`, `upsert_bill`, `append_bill_stage` |
| `src/knab.py` | KNAB political finance scraper (donations, declarations) | `fetch_all_donations`, `fetch_all_declarations`, `fetch_all` |
| `src/knab_analyze.py` | Financial anomaly detection (multi-party donors, limit violations) | `detect_multi_party_donors`, `detect_family_clusters`, `detect_limit_violations`, `run_all_checks` |
| `src/csp/` | Central Statistics Bureau (PxWeb API) pipeline | `sync_all`, `generate_insight`, `fetch_table`, `parse_jsonstat2` |
| `src/credentials.py` | System keyring credential management (12 keys) | `get_credential`, `set_credential`, `verify_all` |

### Output & Wiki

| Module | Purpose | Key Functions |
|--------|---------|---------------|
| `src/generate.py` | Static HTML site generator (21 Jinja2 templates) | `generate_public_site`, `generate_statistika` |
| `src/wiki.py` | Obsidian wiki vault sync (frontmatter auto-sync, body preserved) | `wiki_sync` |
| `src/wiki_writeback.py` | Enriches wiki pages with analysis insights | `enrich_person_page`, `enrich_topic_page` |
| `src/wiki_lint.py` | Wiki quality checks (orphans, broken links, stale frontmatter) | `lint_wiki`, `lint_wiki_with_db` |
| `src/briefs.py` | Neutral daily/weekly political briefs | `generate_daily_brief`, `generate_weekly_brief` |
| `src/routine.py` | 9-step daily routine status checker | `check_routine`, `print_routine` |
| `src/preflight.py` | Pre-operation safety checks (DB, sources, model, credentials) | `preflight_check` |

## Database Schema

### Main Database (data/atmina.db) — 22 tables

**Political Entities:**
- `tracked_politicians` — 147 profiles (name, party, role, name_forms, keywords, relationship_type)
- `parties` — 12 parties (name, short_name, coalition_status, ideology, color)
- `social_accounts` — X/Twitter/YouTube/Facebook accounts per politician

**Documents:**
- `documents` — 13032 scraped items (content, hash, simhash, source_url, language, platform)
- `document_politicians` — many-to-many junction (roles: subject, mentioned, mention_target, author)
- `document_chunks` — text chunks for embedding
- `document_vectors` — sqlite-vec virtual table (384-dim float embeddings)

**Claims & Analysis:**
- `claims` — 6316 total (858 position + 5458 saeima_vote), keyed on (opponent_id, source_url, topic)
- `claim_vectors` — sqlite-vec virtual table for semantic claim search
- `contradictions` — 10 detected inconsistencies (severity: minor_shift, reversal, direct_contradiction)
- `analyses` — analysis records per politician per period
- `political_tensions` — inter-politician conflicts

**Context & Metadata:**
- `context_notes` — daily briefs, context, tips, corrections (note_type-classified)
- `oppo_briefs` — opposition research summaries
- `logs` — action audit trail with Claude model tracking
- `metadata` — key-value configuration store
- `mention_classifications` — document categorization

**KNAB Finance (4 tables):**
- `knab_donors` → `knab_donations` → `knab_declarations` → `knab_alerts`

**Saeima Parliament (4 tables):**
- `saeima_sessions` → `saeima_agenda_items` → `saeima_votes` → `saeima_individual_votes`

### CSP Database (data/csp.db) — 4 tables

- `csp_data` — 10 economic/social indicators (unemployment, CPI, demographics, GDP, etc.)
- `csp_metadata` — table definitions and sync timestamps
- `events` — timeline events for chart overlays
- `topic_links` — indicator-to-research-topic mappings

## Agent Pipeline

Seven specialized Claude Code agents form the analysis pipeline:

| Agent | Role | Key Constraint |
|-------|------|----------------|
| `@claim-extractor` | Extract positions from documents | Max 33 docs/politician/session; confidence 0.5 is healthy |
| `@contradiction-hunter` | Find rhetoric-vs-vote contradictions | Max 5 politicians/session; 8-pattern FP taxonomy mandatory |
| `@devils-advocate` | Adversarial review of claims/contradictions | Must read original source URLs; blocks if unreviewed exist |
| `@quality-reviewer` | Final data integrity gate (PASS/BLOCKED) | Source URLs non-negotiable; blocks site generation |
| `@brief-writer` | Neutral daily/weekly political summaries | No campaign language; preserve context boxes and source URLs |
| `@mentions-monitor` | X/Twitter mention aggregation | Run AFTER fetch_all_twitter(); neutral patterns only |
| `@saeima-tracker` | Parliament session scraping via Playwright | Absolute URLs; claim_type='saeima_vote' mandatory |

**Pipeline flow:** Ingest → @claim-extractor → @contradiction-hunter → @devils-advocate → @brief-writer → @quality-reviewer → generate

## Public Site Structure

21 Jinja2 templates rendering a dark-themed static site:

| Page | Template | Content |
|------|----------|---------|
| Dashboard | `index.html.j2` | Election countdown, stats, latest contradictions, trends charts, recent votes |
| Politician | `politician.html.j2` | Tabbed profile (timeline, positions, contradictions, votes, tensions, news) |
| Parties | `partijas.html.j2` | Filterable party cards (coalition/opposition/not in Saeima) |
| Party Detail | `partija.html.j2` | Members, claims, votes, tensions, KNAB finances |
| Positions | `pozicijas.html.j2` | Filterable table of all political positions |
| Contradictions | `pretrunas.html.j2` | Severity-filtered cards with old vs. new stance |
| Votes | `balsojumi.html.j2` | Vote list + correlation matrix views |
| Statistics | `statistika.html.j2` | CSP economic/social indicator dashboard |
| Stat Detail | `statistika-detail.html.j2` | Individual indicator with trend chart + event overlays |
| Personas | `personas.html.j2` | Directory of tracked politicians |
| News | `zinas.html.j2` | News feed with source/topic/person filters |
| Finances | `finanses.html.j2` | KNAB donation stats and highlights |
| Tensions | `spriedzes.html.j2` | Political tension/conflict records |
| X/Twitter | `x.html.j2` | Social media posts |
| Blog | `blog.html.j2` / `blog-post.html.j2` | Analysis articles |

**Design system:** Dark theme (#0d1014 bg), accent #90A4AE, highlight #B71C1C. Domain-colored stat cards (economy=gray, social=purple, prices=orange, state=green). Severity badges (red/orange/yellow). Responsive 2-4 column grids.

## Data Flow Diagram

```
Sources (26 web + X/Twitter + Saeima + KNAB + CSP)
  │
  ├─ ingest_all() ──────────── Web RSS/scraping ─────────┐
  ├─ fetch_all_twitter() ───── X/Twitter posts ──────────┤
  ├─ fetch_all_mentions() ──── X/Twitter mentions ───────┤
  ├─ process_vote_snapshot() ─ Saeima votes ─────────────┤
  ├─ fetch_all() ───────────── KNAB finance ─────────────┤
  └─ sync_all() ────────────── CSP statistics ───────────┤
                                                          │
                                                          ▼
                              documents table (+ embeddings)
                                                          │
                              ┌────────────────────────────┤
                              │                            │
                              ▼                            ▼
                    match_politicians()          embed_document()
                    → document_politicians       → document_chunks
                                                 → document_vectors
                              │
                              ▼
                    @claim-extractor
                    save_analysis() [atomic]
                    → claims + claim_vectors
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
          search_similar_claims()   @contradiction-hunter
          → auto-contradiction      → manual contradiction
                    │                   │
                    └─────────┬─────────┘
                              ▼
                    @devils-advocate (review)
                    → contradictions confirmed/downgraded
                              │
                              ▼
                    @brief-writer
                    → context_notes (daily_brief)
                              │
                              ▼
                    @quality-reviewer (PASS/BLOCKED)
                              │
                              ▼
                    generate_public_site()
                    → output/atmina/ (static HTML)
                    wiki_sync()
                    → wiki/ (Obsidian vault)
```

## Key Design Decisions

1. **Claim type discipline** — `position` (media/X rhetoric) vs `saeima_vote` (voting records) prevents cross-contamination in contradiction detection
2. **URL-level idempotency** — Claims keyed on `(opponent_id, source_url, topic)` survive re-ingestion safely
3. **Atomic save_analysis** — Analysis + claims + reviewed-docs in single SQLite transaction; failures roll back completely
4. **Coalition from DB, not hardcode** — `parties.coalition_status` is the single source of truth; `relationship_type` is legacy per-politician tracking
5. **Embedding before write** — Embeddings computed outside write transaction to avoid lock-timeout under parallel extraction
6. **Simhash deduplication** — Hamming distance ≤ 3 catches near-duplicate documents at ingestion
7. **26 canonical topics** — ~158 raw topics normalized via keyword matching with Latvian diacritics awareness
8. **5-slot X client pool** — Round-robin rotation with per-slot rate-limit tracking for Twitter API resilience
9. **Playwright for Saeima** — JS-rendered parliament pages require browser automation, not HTTP fetching
10. **No sentiment analysis** — Removed as unreliable; sentiment=0.0 passed as placeholder

## Test Coverage

226+ tests across 22 files. Key areas:
- DB schema and deduplication (28 tests)
- KNAB HTML parsing (40 tests)
- Pydantic model validation (19 tests)
- Topic normalization (18 tests)
- Analysis atomicity (15 tests)
- Brief generation (11 tests)
- Name matching regression tests (ingest)
- Post-launch regression suite (10 tests from 2026-04-10/11 audits)

## Directory Structure

```
atmina/
├── .claude/agents/          # 7 agent definitions
├── assets/                  # CSS, photos, favicon
├── content/                 # Blog posts (markdown + frontmatter)
├── data/                    # SQLite databases, X cookies, events
├── docs/                    # Plans, specs, this file
├── output/atmina/           # Generated static site
├── scripts/                 # Migration scripts
├── src/                     # 34 Python modules
│   ├── csp/                 # CSP statistics sub-package (6 files)
│   └── *.py                 # Core modules (28 files)
├── templates/               # 21 Jinja2 templates
├── tests/                   # 22 test files (226+ tests)
├── wiki/                    # Obsidian vault
│   ├── persons/             # 147 politician pages
│   ├── parties/             # 12 party pages
│   ├── topics/              # 26+ topic pages
│   ├── laws/                # 34 bill pages
│   ├── operations/          # Runbooks + agent descriptions
│   ├── dailies/             # Daily snapshots
│   └── synthesis/           # Cross-party analyses
├── CLAUDE.md                # Project instructions
├── sources.yaml             # 13 source definitions (3 tiers)
├── requirements.txt         # Python dependencies
└── politracker.db           # Legacy database (unused)
```
