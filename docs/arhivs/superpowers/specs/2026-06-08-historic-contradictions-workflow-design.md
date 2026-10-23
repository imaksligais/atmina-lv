# Historic-contradictions workflow — design (2026-06-08)

## Problem

atmina ingests only **live** signal: RSS (rolling window), X timelines, Saeima votes.
There is no path to pull a politician's **older** public record — and that record is
exactly what the over-time contradiction signal needs (an old baseline position to
contradict today's rhetoric against). The only existing historic-ingest tooling is
hardcoded one-off scripts (`scripts/retrofetch_vitenbergs_2020_2022.py` and siblings):
a static URL list + httpx + trafilatura + `insert_document` + `link_politicians_to_documents`,
re-pasted per politician, untested, in ruff scope. Contradiction hunting over the result
is then done by hand via `/deep-check`.

## Goal

One reusable Workflow that, for a small set of politicians, **discovers** historic articles
on the web, **ingests** them backdated, **extracts** pozīcijas, and **hunts contradictions**
against the politician's full existing history — ending at `confirmed=0` survivors for
operator review. Plus the missing generic single-URL ingest CLI the codebase lacks today.

## Deliverables

1. **`scripts/ingest_url.py`** (new, tested) — generalizes the retrofetch pattern into a tool.
2. **`.claude/workflows/historic-contradictions.js`** (new) — the orchestration script.
3. **`tests/test_ingest_url.py`** (new) — TDD coverage for the CLI (network mocked).
4. **`wiki/operations/operacijas.md`** — runbook entry (invocation + discovery-yield caveat).

## Architecture

### 1. `scripts/ingest_url.py` — generic historic ingest CLI

Single source for fetch → clean → backdate → insert → link, replacing inline retrofetch logic.

- `python scripts/ingest_url.py --url URL [--politician-id N]` — one URL.
- `python scripts/ingest_url.py --manifest FILE.jsonl` — many `{url, politician_id?}` lines.
- Per URL:
  1. **Pre-check** `SELECT id FROM documents WHERE source_url=?` → skip fetch, emit
     `status: already_present` (saves bandwidth; ingest is idempotent anyway).
  2. **Fetch** (httpx, browser UA, `follow_redirects`, 20s timeout) → `status: fetch_error` on failure.
  3. **Clean** `trafilatura.extract(..., include_comments=False, include_tables=False,
     deduplicate=True)`; `< 150` chars → `status: thin`.
  4. **Title** `extract_title(html)`; **date** `_extract_published_at(html)`; if null, attempt a
     URL-path year/date fallback (`.../2021/...`, `.aNNN` ignored) and mark `published_at_source`.
  5. **Insert** `insert_document(content, source_id=None, platform="web", language="lv",
     source_url=url, published_at=pub_at, title=title)` (backdating via `published_at`). `None`
     return = `status: dupe` (content_hash already present).
  6. **Link** once after the batch: `link_politicians_to_documents(days=1, rescan_all=True)`;
     report `linked_pids` per doc (intersected with `--politician-id` when given).
- **Output**: one JSON object per URL on a line prefixed `RESULT_JSON:` plus a final
  `SUMMARY_JSON:` `{ingested, already_present, dupe, thin, fetch_error, linked_to[pid]:[doc_ids]}`.
  Stdout forced UTF-8 (Latvian titles).
- **Not a migration** (additive, idempotent, dedup-protected) → no paired rollback SQL required.

### 2. `.claude/workflows/historic-contradictions.js` — the workflow

`args = { politicians: ["Name"|id, …], since?: "YYYY-MM-DD", until?: "YYYY-MM-DD",
topics?: [...], perPolitician?: 12, seedUrls?: {name: [url,…]} }`.
Defaults: `until` = 6 months ago; `since` = `"2018-01-01"`; `perPolitician` = 12.

- **meta** — `name: historic-contradictions`, phases: Resolve, Discover, Ingest, Extract,
  Contradict, Report.
- **Resolve** (1 agent) — names → `{id, name, surname, party, existing_claim_count}` via DB;
  warns on unknowns; drops them from the run.
- **`pipeline(resolved, discover, ingest, extract, contradict)`** — four independent
  per-politician stages (no barrier; A hunts while E searches):
  - **discover** (WebSearch agent, `phase: 'Discover'`) — *multi-modal sweep*: several search
    angles within `[since, until]` (by topic, by year, `site:lsm.lv|delfi.lv|tvnet.lv|nra.lv|la.lv`,
    interview/quote framings). Dedup URLs; filter to plausibly-about-this-politician + dated +
    real-article (drop tag/section/listing pages). Merge `seedUrls[name]`. Cap at `perPolitician`.
    Returns `{politician, urls:[{url, why, guessedDate}]}`. Empty is a valid result.
  - **ingest** (Bash agent, `phase: 'Ingest'`) — write URLs to a temp JSONL, run
    `scripts/ingest_url.py --manifest … --politician-id id`, parse `SUMMARY_JSON`. Return the
    doc_ids that **actually linked** to this politician; flag docs with no `published_at`.
  - **extract** (`@claim-extractor`, `phase: 'Extract'`) — process exactly those doc_ids.
    **`stated_at` = each doc's `published_at`** (THE historic guardrail; default would mis-date
    to today and collapse the over-time signal). Populate `empty_doc_ids`. If > 12 docs, fan out
    parallel ≤12-doc sub-agents. Returns new claim ids + `{id, topic, stance, stated_at}`.
  - **contradict** (deep-check pattern, `phase: 'Contradict'`) — `@contradiction-hunter`
    compares the new historic claims vs the politician's **full** history at **0.80**
    (`search_similar_claims` directional `claim_type_filter` + rhetoric-vs-`saeima_vote`).
    Each candidate → `@devils-advocate` (parallel fan-out) → survivors stored
    `store_contradiction(confirmed=0)`. Returns `{candidates, survivors:[{id, severity, summary}]}`.
- **Report** (synthesis barrier, 1 agent) — aggregate per politician: URLs found/ingested/
  duped/dateless, claims extracted, candidates vs survivors, the `confirmed=0` contradiction ids
  to review, and next steps (`python -m src.render --only=pretrunas` → `deploy.sh --no-delete`).
  Workflow returns this object. **Never renders or deploys** (human-gated).

## Data flow

WebSearch → URL list → temp JSONL manifest → `ingest_url.py` → `documents` (backdated
`published_at`) + `document_politicians` → `@claim-extractor` → `save_analysis` (claims with
`stated_at = published_at`) → `@contradiction-hunter` → `@devils-advocate` →
`contradictions (confirmed=0)` → operator review → narrow render → deploy.

## Guardrails (house rules + memory)

- `stated_at = published_at` on every historic claim.
- Survivors `confirmed=0` (unpublished); **never auto-confirm / render / deploy**.
- LV grammar+stylistics gate on every stored summary/claim (no anglicisms, correct locījumi).
- Idempotent: `insert_document` dedups (content_hash + URL-first); `store_claim` idempotent on
  `(opponent_id, source_url, topic)`. Safe re-runs.
- Honest yield: "0 historic URLs found" is valid. Topic-owning ministers/faction leaders have
  rich historic coverage; X-only / opportunistic profiles often don't
  (`reference_contradiction_hunt_lessons`, ROI ~1/2700). No manufacturing findings to a count.
- `perPolitician` default 12 = claim-extractor circuit-breaker envelope.

## Testing (TDD — `scripts/ingest_url.py`)

- backdating: `published_at` passed through to `insert_document` unchanged.
- `already_present`: existing `source_url` → no fetch, `status: already_present`.
- `dupe`: `insert_document` → `None` → `status: dupe`.
- `thin`: extracted text `< 150` chars → `status: thin`, no insert.
- `fetch_error`: httpx raises → `status: fetch_error`, batch continues.
- manifest parsing: JSONL → per-line ingest; bad lines skipped with a warning.
- network/DB mocked (injectable `fetch_fn` + temp DB) — no real HTTP, no real-DB writes.

The workflow JS itself is verified by a dry run (see runbook), not unit-tested.

## Scope (YAGNI)

Discovery mode only (the chosen source). `seedUrls` covers the operator-manifest case without a
separate `--mode`. No render/deploy automation. No X historic backfill (separate twikit concern).
No new web-search infra — uses the `WebSearch` tool the discovery agent already has.

## Non-goals / unchanged

`@claim-extractor` / `@contradiction-hunter` / `@devils-advocate` prompts unchanged (the workflow
drives them, doesn't rewrite them). Idempotency, `confirmed=0` gate, deep-check thresholds (0.80),
matcher, and the render/deploy flow all unchanged.
