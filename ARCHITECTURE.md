# Architecture

A contributor-level intro to how atmina is structured. For the deep module reference (every file, every function), see [`docs/architecture.md`](docs/architecture.md) — auto-generated, updated periodically.

## Design premise

atmina is **infrastructure that survives without a backend**. The output is static HTML; the operator dashboard is local-only; the analysis is an offline batch process. This is deliberate:

- No login system → no PII to leak, no auth surface to defend.
- No analytics → no third-party tracking dependencies.
- No DB on the public host → atmina.lv can be served from any static file host.
- All claims source-cited → every assertion has an audit trail back to the original document.

This shape lets atmina survive on a shoestring (currently a Namecheap shared host). It also makes the system intelligible: contributors can read every component without grokking a microservice graph.

## The five layers

```
   Sources           Ingest          Storage         Analysis        Output
─────────────────────────────────────────────────────────────────────────────
 LSM, Delfi,       ingest.py       atmina.db       9 Claude Code   generate_public_site
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

- **Documents** — every scraped article, tweet, parliamentary record (`platform` ∈ {`web`, `social`, `saeima`, `video`}).
- **Claims** (positions) — extracted assertions, source-URL-anchored, idempotent on `(opponent_id, source_url, topic)`.
- **Contradictions** — verified pairs across claims or claim↔vote, three types: `direct_contradiction`, `reversal`, `minor_shift`.
- **Context notes** — append-only audit trail per politician; preserves the evolution of positions over time.
- **Saeima votes + bills** — vote records, bill stages (updated only via `append_bill_stage()`).
- **Embeddings** — 384-dim vectors via `intfloat/multilingual-e5-small`, queried through `sqlite-vec`.

`data/csp.db` is a separate database for Central Statistics Bureau time series — kept apart because the data shape (numeric series, no provenance URLs) differs fundamentally from political claims.

### Idempotency contracts

Three operations are idempotent on documented natural keys:

| Operation | Natural key | Behaviour |
|---|---|---|
| `store_claim()` | `(opponent_id, source_url, topic)` | First write wins; later calls return existing `claim_id` |
| `store_contradiction()` | `(politician_id, claim_a_id, claim_b_id, type)` | First write wins |
| `append_bill_stage()` | `(bill_id, stage_type, stage_date)` | First write wins; updates `current_stage` to latest |

Re-running ingest or analysis on already-processed data is therefore safe. This is the contract that lets the daily routine recover from partial failures without manual reconciliation.

### Strict types

`src/models.py` (Pydantic v2) enforces strict shapes — notably:

- `vulnerabilities`, `strongest_attacks`, `suggested_counters` are `list[dict]` as `[{"text": "..."}]`, **not** `list[str]`.
- `contradictions_cited` is `list[int]`.
- `narrative_frames` is `dict`.
- Empty = `[]` / `{}`.

Violations fail at the type boundary, not at the database. This catches schema drift early during agent development.

### Schema invariants

| Invariant | Where enforced | Why |
|---|---|---|
| Claims without `source_url` are dropped silently at the DB layer | `src/db.py::store_claim()` | No URL = no provenance = no auditability. |
| `claim_type` ∈ {`position`, `saeima_vote`, `commentary`} | Pydantic + `store_claim()` | Readers filter by type, not URL heuristics. |
| `speaker_id` separates authorship from subject | `claims.speaker_id` | Third-party commentary about a politician is tracked distinctly from first-party rhetoric. |
| `position` and `commentary` claims require `document_id NOT NULL` | DB constraint | Provenance is mandatory; only `saeima_vote` is allowed NULL (vote provenance via `saeima_individual_votes`). |
| Context notes are append-only | Convention + audit reviewer | Overwriting destroys the over-time evolution signal that context notes exist to preserve. |

Full rationale and historical reasoning: [`wiki/CHANGELOG.md`](wiki/CHANGELOG.md).

## Analysis: Claude Code as the engine

Unlike most pipelines, atmina's analysis layer is **interactive**, not scripted. Nine specialized Claude Code agents (`.claude/agents/*.md`) handle distinct tasks:

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
| `@video-extractor` *(WIP)* | speaker-labelled transcripts | claims with `?t=N` anchors | manual per video |

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
- **`data/x_cookies.json`** — Twitter/X session cookies (manual DevTools export). Gitignored.
- **`data/gemini_key.json`** — Google GenAI API key for graphics. Gitignored. Template: `data/gemini_key.json.example`.

No environment variables are required for core operation. `python-keyring` reads from the OS-native credential store (Windows Credential Manager / macOS Keychain / Secret Service).

## What's WIP

| Component | Status |
|---|---|
| `@video-extractor` | Pipeline scaffolded; speaker diarization manual-only on Python 3.12+ (pyannote + speechbrain compat). |
| Multi-protocol social adapter | Planned for NLnet M2 — Bluesky (AT Protocol) + Mastodon (ActivityPub). twikit replaced. |
| Country-portable refactor | Planned for NLnet M3 — `src/countries/lv/` extracted, Estonia stub. |
| Open data REST API + JSON-LD export | Planned for NLnet M4. |
| LLM provider abstraction | Planned for NLnet M5 — `AnthropicProvider`, `OpenAIProvider`, `OllamaProvider` interfaces. |

See [`README.md` → Roadmap](README.md#roadmap).

## Where to start as a contributor

| If you want to… | Start by reading |
|---|---|
| Fix a misattributed claim or politician | [`docs/data-policy.md`](docs/data-policy.md) §6-7, then `wiki/persons/<slug>.md` |
| Add a news source | `sources.yaml` + [`wiki/operations/dev-setup.md`](wiki/operations/dev-setup.md) + `src/ingest.py` |
| Modify the daily routine | `src/routine.py` + [`wiki/operations/daily-routine.md`](wiki/operations/daily-routine.md) |
| Tune an agent's behaviour | `.claude/agents/<agent-name>.md` (canonical prompt) + `wiki/operations/agenti/<agent>.md` (human description) |
| Touch the DB schema | `src/db.py` + `wiki/CHANGELOG.md` (decisions log) |
| Render templates | `src/render/` + `src/templates/` |

CLAUDE.md is the load-bearing contributor reference for invariants. Read it before any PR that touches data shape, idempotency, or pipeline order.
