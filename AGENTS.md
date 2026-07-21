# AGENTS.md

## Project Overview

atmina is a Latvian political transparency platform. Scrapes news sources + Twitter/X profiles (via twikit), extracts pozīcijas (claims) and pretrunas (contradictions) per politician, renders an interactive HTML site. Tracks politicians across multiple parties. Primary language: Latvian (lv), some Russian (ru). No sentiment analysis — removed as unreliable.

## Session Start

Read `wiki/index.md` first — status counts, backlog, folder contract. Runbooks: `wiki/operations/operacijas.md`. Historical data-model changes + rationale for every invariant below: `wiki/CHANGELOG.md`. Codex IS the analysis engine — analysis is written interactively, not by scripts.

## Data Contracts

1. **Pydantic types are strict.** `vulnerabilities`, `strongest_attacks`, `suggested_counters` are `list[dict]` as `[{"text": "..."}]`, not `["string"]`. `contradictions_cited` is `list[int]`. `narrative_frames` is `dict`. Empty = `[]` / `{}`.

2. **Claims without `source_url` are silently dropped** at the DB layer — no error, just lost. No URL = no provenance = can't cite, can't re-fetch, can't contradict.

3. **`store_claim()` is idempotent on `(opponent_id, source_url, topic)`.** Re-running the same triple returns the existing claim_id; first-write-wins. Bulk re-scrapes that revisit the same URL are safe.

4. **`claim_type` values:** `'position'` (default, media/X rhetoric), `'saeima_vote'` (reserved for `@saeima-tracker`), `'commentary'` (third-party allegations with `speaker_id` set). Readers filter by `claim_type`, not URL heuristics. See [CHANGELOG § claim_type split](wiki/CHANGELOG.md#2026-04-11--claim_type-split-position-vs-saeima_vote) + [§ Komentētāji speaker_id](wiki/CHANGELOG.md#2026-04-23--komentētāji-speaker_id-on-claims).

4a. **`claims.speaker_id` attributes authorship separately from subject.** `NULL` (or `= opponent_id`) = first-party: the politician IS the speaker. Non-NULL and `≠ opponent_id` = third-party commentary: a different tracked entity (typically `relationship_type='commentator'`, e.g. @KlucisD, id=169) is speaking ABOUT the subject politician. Readers needing a concrete speaker use `COALESCE(speaker_id, opponent_id)`. Full rationale + extractor protocol: [CHANGELOG § Komentētāji](wiki/CHANGELOG.md#2026-04-23--komentētāji-speaker_id-on-claims) + [`wiki/operations/agenti/claim-extractor.md`](wiki/operations/agenti/claim-extractor.md).

## Pipeline Invariants

5. **Contradiction check is mandatory.** For every new claim, compare against the full history for that politician (`search_similar_claims` with directional `claim_type_filter`). Store via `store_contradiction()`. Types: `direct_contradiction`, `reversal`, `minor_shift`. Also check rhetoric-vs-action. `speaker_scope` defaults to `'first_party'`; pass `'commentary'` for commentator-self-consistency or `'all'` for legacy behavior. Rationale: [CHANGELOG § Komentētāji](wiki/CHANGELOG.md#2026-04-23--komentētāji-speaker_id-on-claims).

6. **Context notes are append-only.** Add new rows; never update old ones. Overwriting destroys the evolution-over-time signal tendences exist to preserve.

7. **Run `fetch_all_mentions()` after `fetch_all_twitter()`.** Ordering matters for rate limits.

8. **`save_analysis()` is atomic.** Analysis + claims + reviewed-docs update run in one SQLite transaction. Catastrophic DB failures return `status="failed"` with `transaction_rolled_back` and persist nothing. Validation-level skips (missing source_url, inactive politician) return `status="partial"` without rollback — logical drops, not state corruption. [CHANGELOG § atomicity](wiki/CHANGELOG.md#2026-04-11--save_analysis-atomicity-s10).

9. **Check existing context notes before adding** — avoid duplicate tendences.

10. **`claim-extractor` batch limit is 12 docs/session; `save_analysis` has a soft indirect-reference gate.** Marker list lives in `src/analyze.py::_INDIRECT_MARKERS_LOWER`; matches get `NEEDS_REVIEW:` prepended for operator triage (claim still saved). Negation-aware: `"nav <marker>"` / `"nevis <marker>"` / `"not <marker>"` etc. in a 30-char window before a marker skip the flag. For > ~5 pending docs per politician, fan-out parallel single-doc sub-agents. Diagnostics + negation fix: [CHANGELOG § batch-drift fixes](wiki/CHANGELOG.md#2026-04-22--claim-extractor-batch-drift-fixes).

## Coalition Classification

11. **Truth source is `parties.coalition_status`.** Read via `src.coalition.get_coalition_map(db)` (batch) or `party_status(party)` (single). **Never** use `tracked_politicians.relationship_type` for coalition logic — it's a legacy per-politician tracking role. [CHANGELOG § Coalition](wiki/CHANGELOG.md#2026-04-11--coalition-classification-partiescoalition_status).

## Social feed_type

12. **`social_accounts.feed_type` classifies X accounts as `'first_party'` (default) or `'relay'`.** First-party accounts (politicians, commentators, individual journalists): `_store_tweets` uses per-tweet handle match — `role='subject'` only when the tweet URL author matches one of the politician's registered handles, else `role='mentioned'`. Relay accounts (institutional media like LTV Ziņas): `_store_tweets` inserts the doc with empty `politician_links`; `link_politicians_to_documents` later picks subject from text-scanned mentions, matching RSS flow. [CHANGELOG § feed_type](wiki/CHANGELOG.md#2026-04-23--social_accountsfeed_type-relay-vs-first_party) + [§ Matcher role integrity](wiki/CHANGELOG.md#2026-04-23--matcher-role-integrity--diacritic-validator-fixes).

## Output Conventions

- **UI language is Latvian throughout.** Claims = Pozīcijas, Contradictions = Pretrunas, Patterns = Tendences.
- **Timestamps use `now_lv()` from `src/db.py`** (Latvia UTC+3 / EEST).
- **Topic names use 31 canonical groups** from `src/topic_map.py`. `store_claim()` / `store_contradiction()` auto-normalize; unknown topics pass through.
- **`sentiment=0.0`** on `save_analysis()` — parameter exists but sentiment was removed. Always pass `0.0`.

## Commands

```bash
.venv/Scripts/activate                    # Windows venv
python -m pytest tests/ -v               # Run all tests
python serve.py                           # Dashboard server (http://127.0.0.1:8080)
python -c "from src.routine import print_routine; print_routine()"  # Check routine status
python -c "from src.generate import generate_public_site; generate_public_site()"  # Generate static site output/
bash scripts/deploy.sh --dry-run          # Preview deploy to Namecheap
bash scripts/deploy.sh                    # Deploy output/atmina/ to production (see wiki/operations/deploy.md)
python scripts/telegram_brief.py [DATE] [--md2]  # Telegram-formatted daily brief (manual, see wiki/operations/telegram-brief.md)
python -m src.social_agent brainstorm             # X/Twitter draftu aģents — top 3 uz Telegrāmu (see wiki/operations/social-agent.md)
python -m src.social_agent approve|skip|revise|resend <id>   # draftu operācijas
```

## Tech Stack

Python 3.11+, SQLite (WAL) + sqlite-vec (384-dim embeddings via `intfloat/multilingual-e5-small`), Pydantic v2, Jinja2 templates, httpx + trafilatura + BeautifulSoup4, twikit (cookie-based X/Twitter auth via `data/x_cookies.json`), simplemma (Latvian lemmatization), fasttext (language detection). twikit needs local patches after reinstall — see [wiki/operations/twikit-notes.md](wiki/operations/twikit-notes.md).

## Runbooks & Agents

Routines + guides: [wiki/operations/operacijas.md](wiki/operations/operacijas.md) (daily/weekly/monthly, deploy, rubrics, source framing, KNAB, social agent, telegram brief, content pipeline, twikit notes).

Agent prompts — **canonical execution**: `.Codex/agents/*.md`. Human-readable descriptions: `wiki/operations/agenti/`. Available: `@claim-extractor` · `@contradiction-hunter` · `@devils-advocate` · `@quality-reviewer` · `@brief-writer` · `@graphics-designer` · `@mentions-monitor` · `@saeima-tracker`.

## Operational Notes

- `opponent_id` references `tracked_politicians.id` on claims, analyses, contradictions, context_notes, social_accounts, logs. Documents use `document_politicians` junction table (many-to-many with roles: subject, mentioned, mention_target).
- `relationship_type='inactive'` hides politicians from dashboard.
- Documents deduplicated at insert (hash + simhash). Same-day briefs overwritten.
- Twitter/X auth: `data/x_cookies.json` (gitignored, critical: `auth_token` + `ct0`). When expired, extract from browser DevTools.
- Routine status: `print_routine()` checks all steps. Dashboard auto-warns if incomplete.
- Ad hoc tweet share from user: see [wiki/operations/daily-routine.md § Lietotājs dalās ar tvītu](wiki/operations/daily-routine.md).
