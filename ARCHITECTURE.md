# Architecture

A contributor-level intro to how atmina is structured. `docs/architecture.md` ir vēsturisks 2026-04-14 momentuzņēmums (netiek uzturēts) — šis fails ir vienīgais aktuālais arhitektūras apraksts.

## Design premise

atmina is **infrastructure that survives without a backend**. The output is static HTML; the operator dashboard is local-only; the analysis is an offline batch process. This is deliberate:

- No login system → no PII to leak, no auth surface to defend.
- Cookieless analytics only (Umami Cloud) → visitor counts, no cookies, no
  cross-site identifiers, no per-reader profiles. Every other asset — fonts,
  JS libraries — is self-hosted, so Umami is the sole third-party host in the
  CSP allowlist (`assets/htaccess.template`).
- No DB on the public host → atmina.lv can be served from any static file host.
- All claims source-cited → every assertion has an audit trail back to the original document.

This shape lets atmina survive on a shoestring (currently a Namecheap shared host). It also makes the system intelligible: contributors can read every component without grokking a microservice graph.

## The five layers

```
   Sources           Ingest          Storage         Analysis        Output
─────────────────────────────────────────────────────────────────────────────
 LSM, Delfi,       ingest.py       atmina.db       11 Claude Code  generate_public_site
 NRA, TVNet,       social.py       (SQLite WAL +   agents          → output/atmina/
 Diena, LETA,      saeima/         sqlite-vec)
 LA, Jauns.lv,     knab.py         40 tables       analyze.py      Jinja2 templates
 rus.Delfi,        csp/                            tools.py        + Markdown
 Vēstnesis        x_scraper.py    384-dim          cross_check.py  + wiki sync
                                   embeddings
 X/Twitter         vestnesis.py    intfloat/       briefs.py
 (twikit pool)     vad/            multilingual-   confidence_
                                   e5-small        drift.py
 Saeima, KNAB,
 VAD, CSP                          csp.db
                                   (separate)
```

Each layer is independently testable and replaceable. The boundary between **storage** and **analysis** is the single most load-bearing interface in the project: claims, contradictions, and context notes are append-only journals, and the analysis layer reads through them rather than mutating prior state.

## Module map

`src/` holds **131 Python modules** (`find src -name '*.py' | wc -l`): 38 flat modules plus 8 packages (one of which, `dashboard`, has a nested `views` subpackage). The diagram above names only the entry points; this is the full shape.

**Packages** (import as `src.<name>`; each has an `__init__.py` that is the intended import surface):

| Package | Modules | What it is |
|---|---|---|
| `src/render/` | 27 | The whole site generator — one module per public surface (`politicians`, `parties`, `votes`, `bills`, `laws`, `blog`, `topics`, `search_index`, …) plus `_orchestrator.py` (`generate_public_site()`) and `_common.py` (shared helpers). |
| `src/dashboard/` | 2 + `views/` (11) | The local-only operator dashboard (`serve.py` → `src.dashboard.create_app()`); `views/` is one module per panel. |
| `src/video_ingest/` | 13 | Video → transcript pipeline: `fetch` → `asr` → `diarize` → `align` → `finalize`. Verified, not yet used in production (see *What's WIP*). |
| `src/saeima/` | 8 | Parliament: `votes.py` (scrape + parse + `normalize_faction()`), `bills.py` (`append_bill_stage()`), `claims.py`, `schema.py`, `manifest.py`. |
| `src/graphics/` | 9 | Featured-image generation for briefs: prompt composition, the image API client, storage + variants, weekly charts. |
| `src/social_agent/` | 9 | Draft social posts from a published brief: candidate selection, drafters, visuals, publisher. |
| `src/vad/` | 8 | Official asset declarations — fetch, parse, match, diff, schema. (It is a **package**, not a `vad.py` file.) |
| `src/csp/` | 6 | Central Statistics Bureau time series; writes the separate `data/csp.db`. |

**Load-bearing flat modules** (the ones whose behaviour the invariants in CLAUDE.md hang on):

| Module | Role |
|---|---|
| `db.py` | Schema init + migrations + every `store_*()` guardrail. A raw INSERT bypasses the validation, which lives in the function, not the schema. |
| `analyze.py` | `save_analysis()` (atomic), `get_pending_politicians()`, the `source_url` / `empty_doc_ids` validation. |
| `matcher.py` | Substring politician matcher, **no diacritic folding** — the origin of traps T1 and T13. Module-level caches; deliberately not split. |
| `embeddings.py` | `intfloat/multilingual-e5-small` wrapper; the 384-dim vectors behind `sqlite-vec` similarity search. |
| `ingest.py` | RSS + article fetch, per-site rules, URL-first dedup (`documents.scraped_at` is mutable for `platform='web'`). |
| `briefs.py` | Daily/weekly brief skeletons, `routine_day_window()` (the 05:00 LV routine-day boundary), `brief_subject_date()`. |
| `routine.py` | Daily/weekly/monthly routine state machine — what `print_routine()` reports. |
| `wiki.py` / `wiki_lint.py` / `wiki_writeback.py` | Obsidian vault sync, its lint gate, and the writeback path. |
| `tools.py` | JSON-wrapped utilities the agents call through. |
| `models.py` | The four Pydantic models (below). |
| `quality.py` · `lv_style.py` · `topic_map.py` | Quote/diacritic checks, Latvian prose gate, the 33 canonical topic groups. |
| `social.py` · `x_scraper.py` · `x_mentions.py` · `x_pool.py` | X/Twitter fetch through the twikit cookie pool, plus mention search. |
| `knab/` (`parse` · `ingest` · `queries` · `analyze`) · `vestnesis.py` | Donation/declaration ingest and Latvijas Vēstnesis law publication. `src/knab/__init__.py` re-exports the public surface, so `from src.knab import fetch_all` still works. |
| `coalition.py` | `get_coalition_map()` / `party_status()` — the only legitimate coalition truth source (`parties.coalition_status`). |
| `coverage.py` · `confidence_drift.py` · `cross_check.py` · `party_contradictions.py` | Analysis helpers: coverage dark zones, confidence drift, rhetoric↔vote cross-checks. |

Remaining flat leaves are small single-purpose helpers: `credentials.py`, `image_variants.py`, `ingest_log.py`, `outlets.py`, `preflight.py`, `profile_kind.py`, `quoted_speaker.py`, `scope.py`, `title_extract.py`.

## Storage: the single source of truth

`data/atmina.db` (SQLite + WAL mode) holds everything load-bearing. It carries **40 logical tables** — `grep -c 'CREATE TABLE' src/schema.sql` (20) + `src/saeima/schema.py` (7) + `src/vad/schema.py` (11), plus `publish_approvals` and `external_profiles` created by the `init_db()` migration block in `src/db.py`. Two more are `sqlite-vec` virtual tables (`document_vectors`, `claim_vectors`), each of which expands into several shadow tables, so a raw `sqlite_master` count reads much higher.

- **Documents** — every scraped article, tweet, parliamentary record. Live `platform` values: `twitter`, `x_mention`, `web`, `vestnesis`, `web_scraper`, plus `video` for transcript documents. `platform='saeima'` rows are deliberately **not** created — vote provenance hangs off `saeima_individual_votes`, not a document (CLAUDE.md Data Contract #6).
- **Claims** (positions) — extracted assertions, source-URL-anchored, idempotent on `(opponent_id, source_url, topic)`.
- **Contradictions** — verified pairs across claims or claim↔vote, three types: `direct_contradiction`, `reversal`, `minor_shift`.
- **Context notes** — append-only audit trail per politician; preserves the evolution of positions over time.
- **Saeima votes + bills** — vote records, bill stages (updated only via `append_bill_stage()`).
- **Embeddings** — 384-dim vectors via `intfloat/multilingual-e5-small`, queried through `sqlite-vec`.

`data/csp.db` is a separate database for Central Statistics Bureau time series — kept apart because the data shape (numeric series, no provenance URLs) differs fundamentally from political claims.

### Idempotency contracts

**One** operation is idempotent on a documented natural key:

| Operation | Natural key | Behaviour |
|---|---|---|
| `store_claim()` | `(opponent_id, source_url, topic)` | First write wins; later calls return the existing `claim_id` |

That contract is what makes re-running ingest and claim extraction over already-processed documents safe, and it is what lets the daily routine recover from partial failures without manual reconciliation.

The other two writers are **append-only, not idempotent** — calling them twice writes two rows:

| Operation | Actual behaviour |
|---|---|
| `store_contradiction()` | Bare INSERT (`src/db.py`). Re-running a contradiction hunt over the same claim pair duplicates it. |
| `append_bill_stage()` | Bare INSERT (`src/saeima/bills.py:309`) plus an atomic recompute of the parent bill's `current_stage`. The name is accurate: it appends. |

Until 2026-08-01 this section claimed all three were idempotent and concluded that re-running anything was therefore safe. It is not: the live DB carries 25 duplicate `(bill_id, stage_name, stage_date)` groups out of 565 stage rows. Guard re-runs at the caller, and read CLAUDE.md invariant #12 before touching bill stages at all.

### Strict types

`src/models.py` (Pydantic v2) defines four models — `AnalysisResult`, `Claim`, `Contradiction`, `ContextNote` — with constrained fields where the value range matters:

- `confidence` and `salience` are `float` bounded `0.0`–`1.0`.
- `Contradiction.severity` is `Literal["minor_shift", "reversal", "direct_contradiction"]`.
- `ContextNote.note_type` is a `Literal` over the seven legal note kinds.

Violations fail at the type boundary, not at the database.

*(This section previously documented `vulnerabilities` / `strongest_attacks` / `suggested_counters` / `narrative_frames`. Those belonged to the politracker-era attack-brief models, removed with the `oppo_briefs` table on 2026-07-29 — see CLAUDE.md Data Contract #1 TOMBSTONE.)*

### Schema invariants

| Invariant | Where enforced | Why |
|---|---|---|
| Claims without `source_url` are dropped in `save_analysis()` validation — **not** at the DB layer | `src/analyze.py::save_analysis()`, reported in the returned `failures` list | No URL = no provenance = no auditability. `store_claim()` called directly will happily insert a NULL `source_url`, so the guard is in the caller, not the schema. |
| `claim_type` ∈ {`position`, `saeima_vote`, `commentary`, `program_promise`} | `store_claim()` | Readers filter by type, not URL heuristics. Every render + brief query gates on `claim_type='position'`. |
| `speaker_id` separates authorship from subject | `claims.speaker_id` | Third-party commentary about a politician is tracked distinctly from first-party rhetoric. |
| `position` and `commentary` claims require `document_id NOT NULL` | Convention + `save_analysis()`, **not** a DB constraint | Provenance is mandatory; only `saeima_vote` is allowed NULL (vote provenance via `saeima_individual_votes`). |
| Context notes are append-only | Convention + audit reviewer | Overwriting destroys the over-time evolution signal that context notes exist to preserve. |

The precise wording of the first row matters and is easy to get backwards: CLAUDE.md Data Contract #2 exists specifically to correct "dropped at the DB layer", and `AGENTS.md` was deleted on 2026-08-01 partly for repeating it. A contributor who believes the database enforces provenance will write a raw INSERT and lose it silently.

Full rationale and historical reasoning: [`wiki/CHANGELOG.md`](wiki/CHANGELOG.md).

## Analysis: Claude Code as the engine

Unlike most pipelines, atmina's analysis layer is **interactive**, not scripted. Eleven specialized Claude Code agents (`.claude/agents/*.md`) handle distinct tasks — the table below lists the nine that run on a routine cadence; `@weekly-brief-writer` and `@outlet-researcher` are the two on-demand additions:

| Agent | Reads | Writes | When |
|---|---|---|---|
| `@claim-extractor` | unreviewed documents | claims, reviewed-doc flags | daily |
| `@contradiction-hunter` | claims for one politician | candidate contradictions | weekly + on demand |
| `@devils-advocate` | candidate contradictions | filtered candidates | after `@contradiction-hunter` |
| `@quality-reviewer` | pending publish set | data-integrity verdicts | before deploy |
| `@brief-writer` | daily/weekly diff | `daily_brief` rows + Markdown | afternoon |
| `@graphics-designer` | brief topic + visual_brief_json | featured PNG (variants) + cost log | with brief |
| `@mentions-monitor` | X mention search | mentions summary | daily |
| `@saeima-tracker` | titania.saeima.lv | votes, bills, vote-stage links | session days |
| `@video-extractor` | speaker-labelled transcripts | claims with `?t=N` anchors | manual per video |

The orchestration logic lives in:

- **`src/routine.py`** — daily/weekly/monthly routine state machine.
- **`src/analyze.py`** — interactive helpers (`get_pending_politicians`, `save_analysis`).
- **`src/tools.py`** — JSON-wrapped utilities the agents call through.

There is **no** central job scheduler. The operator (a human) advances the routine each day, dispatching agents as needed. This is intentional: agents make editorial decisions, and editorial decisions need a person in the loop.

## Output: deterministic from inputs

`generate_public_site()` (in `src/render/`) reads the DB, runs Jinja2 templates, and writes `output/atmina/*.html`. Given the same DB, it produces byte-identical output (modulo timestamps).

The two outputs are not mirrors:

- **`output/atmina/`** is for the public — atmina.lv readers.
- **`wiki/`** is for the operator — Obsidian vault, link graph, internal cross-references.

Both are written by separate code paths. `wiki/` uses Latvian filenames and Obsidian wikilinks (`[[name]]`); `output/` uses URL-safe slugs and HTML.

## Configuration & credentials

- **OS keyring** (`python-keyring`) — production credentials. Set via `.venv/Scripts/python.exe -m src.credentials set <key>` (bare `python` is never correct on the maintainer machine — see `wiki/operations/commands.md`).
- **`data/x_cookies/<N>.json`** — Twitter/X session cookie pool, one file per slot (manual DevTools export). Gitignored.
- **`data/gemini_key.json`** — Google GenAI API key for graphics. Gitignored. Template: `data/gemini_key.json.example`.

No environment variables are required for core operation. `python-keyring` reads from the OS-native credential store (Windows Credential Manager / macOS Keychain / Secret Service).

## What's WIP

| Component | Status |
|---|---|
| Video ingest | **Path verified, never used in production** — fetch → AiLab ASR → pyannote diarize → align → extraction runs end to end, but `SELECT COUNT(*) FROM documents WHERE platform='video'` is **0**. What exercised it: one E2E test on 2026-07-22 (a 2-minute crosstalk clip) in which `@video-extractor`'s attribution stop-gate correctly refused to store anything; the test document was then deleted. The gate is proven, the happy path is not. Known limit that test exposed: diarization speaker boundaries bleed on heated crosstalk — pick a calm interview for the first real ingest, not a debate clip. See CLAUDE.md Data Contract #13. |
| Multi-protocol social adapter | Planned for NLnet M2 — Bluesky (AT Protocol) + Mastodon (ActivityPub). twikit replaced. |
| Country-portable refactor | Planned for NLnet M3 — `src/countries/lv/` extracted, Estonia stub. |
| Open data REST API + JSON-LD export | Planned for NLnet M4. |
| LLM provider abstraction | Planned for NLnet M5 — `AnthropicProvider`, `OpenAIProvider`, `OllamaProvider` interfaces. |

Open items and their current state live in [`BACKLOG.md`](BACKLOG.md).

## Where to start as a contributor

| If you want to… | Start by reading |
|---|---|
| Fix a misattributed claim or politician | [`docs/data-policy.md`](docs/data-policy.md) §6-7, then `wiki/persons/<slug>.md` |
| Add a news source | `sources.yaml` + [`wiki/operations/dev-setup.md`](wiki/operations/dev-setup.md) + `src/ingest.py` |
| Modify the daily routine | `src/routine.py` + [`wiki/operations/daily-routine.md`](wiki/operations/daily-routine.md) |
| Tune an agent's behaviour | `.claude/agents/<agent-name>.md` (canonical prompt) + `wiki/operations/agenti/<agent>.md` (human description) |
| Touch the DB schema | `src/db.py` + `wiki/CHANGELOG.md` (decisions log) |
| Render templates | `src/render/` + `templates/` (repo root) |

CLAUDE.md is the load-bearing contributor reference for invariants. Read it before any PR that touches data shape, idempotency, or pipeline order.
