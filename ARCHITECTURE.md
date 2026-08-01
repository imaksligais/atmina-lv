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
 LA, Jauns.lv,     knab.py         35+ tables      analyze.py      Jinja2 templates
 rus.Delfi,        csp/                            tools.py        + Markdown
 Vēstnesis        x_scraper.py    384-dim          cross_check.py  + wiki sync
                                   embeddings
 X/Twitter         vestnesis.py    intfloat/       briefs.py
 (twikit pool)     vad.py          multilingual-   confidence_
                                   e5-small        drift.py
 Saeima, KNAB,
 VAD, CSP                          csp.db
                                   (separate)
```

Each layer is independently testable and replaceable. The boundary between **storage** and **analysis** is the single most load-bearing interface in the project: claims, contradictions, and context notes are append-only journals, and the analysis layer reads through them rather than mutating prior state.

## Storage: the single source of truth

`data/atmina.db` (SQLite + WAL mode) holds everything load-bearing:

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

- **OS keyring** (`python-keyring`) — production credentials. Set via `python -m src.credentials set <key>`.
- **`data/x_cookies/<N>.json`** — Twitter/X session cookie pool, one file per slot (manual DevTools export). Gitignored.
- **`data/gemini_key.json`** — Google GenAI API key for graphics. Gitignored. Template: `data/gemini_key.json.example`.

No environment variables are required for core operation. `python-keyring` reads from the OS-native credential store (Windows Credential Manager / macOS Keychain / Secret Service).

## What's WIP

| Component | Status |
|---|---|
| Video ingest | **Operational since 2026-07-22** — fetch → AiLab ASR → pyannote diarize → align → extraction, E2E-verified. Known limit: diarization speaker boundaries bleed on heated crosstalk, so calm interviews work best; the extractor's attribution stop-gate catches bad cases. |
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
