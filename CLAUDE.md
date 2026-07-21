# CLAUDE.md

## Project Overview

atmina is a Latvian political transparency platform. Scrapes news sources + Twitter/X profiles (via twikit), extracts pozīcijas (claims) and pretrunas (contradictions) per politician, renders an interactive HTML site. Tracks politicians across multiple parties. Primary language: Latvian (lv), some Russian (ru). No sentiment analysis — removed as unreliable.

**This file is the operating manual.** It is written so a session with no other context (no private memory, no prior conversation) can work here safely. Section numbers below (Data Contract #N, inv #N) are referenced from tests, `wiki/CHANGELOG.md`, and agent prompts — never renumber them. This file syncs to the PUBLIC mirror: keep it free of operator-identifying or internal-only detail.

## Session Start

Read `wiki/index.md` first — status counts, backlog, folder contract. Runbooks: `wiki/operations/operacijas.md`. Open tech-debt + flagged-but-unfinished work: `BACKLOG.md` (repo root). Historical data-model changes + rationale for every invariant below: `wiki/CHANGELOG.md`. Claude Code IS the analysis engine — analysis is written interactively, not by scripts.

## Standing Decisions (operator-set; do not re-litigate)

- **Public anonymity.** atmina.lv publishes anonymously. Never add operator-identifying information (personal names, company names, e-mail addresses) to any public surface — the site, the public mirror, social posts, commit text, or repo docs. The public mirror is rebuilt from this repo minus a fixed exclusion set (maintainer note, private): **assume any new file is public unless its directory is in that set.**
- **Timing.** Ingest runs all day; claim extraction + daily brief only in the afternoon (~15:00 LV or later). A morning "0/N analyzed" is the expected state, not a failure.
- **Subagent model = Opus, both directions.** ALL project agents in `.claude/agents/` carry `model: opus` in frontmatter (since 2026-07-21; `@claim-extractor`/`@saeima-tracker` since 2026-06-11). Downward bound: a smaller-model trial (2026-06-11) produced LV grammar errors in ~30–40% of stances and was rejected. Upward bound: subagents must NOT inherit a Mythos-tier session model (Fable) — Opus is sufficient and the cost difference is not justified (operator decision 2026-07-21). Workflow `agent()` calls must pass `model: 'opus'` explicitly (frontmatter pins don't reach plain `agentType: 'general-purpose'` calls). Orchestration (the main loop) may run on any tier.
- **Publish pause.** Nothing outward-facing auto-publishes. Daily/weekly brief → manual proofread + featured-image confirm + explicit operator approval BEFORE deploy. Approval for one publish is never standing approval for the next.
- **Syntheses are hand-written.** `wiki/synthesis/` pages are manually authored (standing decision 2026-04-22). Do not propose an auto-synthesis agent.
- **Deploy is additive.** `deploy.sh --no-delete` always; `finanses` + `statistika` remote dirs are curated — never delete remote trees.
- **Rules live in the repo, not private memory.** Any decision future sessions must honor goes into this file, a wiki runbook, or an agent prompt — subagents, cloud runs, and fresh sessions cannot see private memory.

## Working Conventions

- **Silent success is a defect class.** The load-bearing stores can discard input while returning success: `save_analysis()` reports drops only in its returned `failures` list; the idempotency triple can merge distinct claims with `failures` EMPTY. Always inspect returned failure structures and verify stored-count == intended-count. Any new operation that can drop input must report what it dropped.
- **Denormalized fields are stale by default.** `tracked_politicians.party`, `role`, and `claims.topic`-vs-`votes.topic` do not auto-sync from the news. When claim content implies a party/office change, verify against the truth source and apply a manual UPDATE with a paired rollback.
- **Short generated name forms are quarantined.** Matcher-generated inflected forms ≤4 chars are substring bombs ("Kolu" → "Kolumbija"). Flag them for operator review; never auto-add `name_forms` or `negative_patterns` — those are operator-review changes by standing rule.
- **Stop beats write.** When two rules could apply and you cannot tell which, choose the action that stops-and-surfaces over the one that writes. Silent writes are the expensive failure here; stopping is cheap.

## Data Contracts

1. **`oppo_briefs` JSON-column shapes are a load-bearing convention (NOT Pydantic-validated).** These are `TEXT` columns holding JSON, read back with `json.loads` (e.g. `src/social_agent/candidates.py`), so the shape is enforced by readers, not a model: `vulnerabilities`, `strongest_attacks`, `suggested_counters` must be `list[dict]` as `[{"text": "..."}]`, not `["string"]`; `contradictions_cited` is `list[int]`; `narrative_frames` is `dict`. Empty = `[]` / `{}`. (The Pydantic models that ARE strictly validated live in `src/models.py` — `AnalysisResult`/`Claim`/`Contradiction`/`ContextNote` — and do not include these fields.)

2. **Claims without `source_url` are dropped** in `save_analysis()` validation (`analyze.py`), not "at the DB layer": the source document's URL is authoritative, so a claim whose document has no `source_url` is recorded as a `missing_source_url` entry in the returned `failures` list (logged to stderr, not raised — easy to miss). `store_claim()` called directly will happily insert a NULL `source_url`. No URL = no provenance = can't cite, can't re-fetch, can't contradict. Locked by `tests/test_invariants.py::test_inv2_claim_without_source_url_dropped`.

3. **`store_claim()` is idempotent on `(opponent_id, source_url, topic)`.** Re-running the same triple returns the existing claim_id; first-write-wins. Bulk re-scrapes that revisit the same URL are safe. **Corollary (trap T2):** a document with several DISTINCT positions in one topic silently merges them into the first claim — differentiate topics or consolidate deliberately, and verify counts.

4. **`claim_type` values:** `'position'` (default, media/X rhetoric), `'saeima_vote'` (reserved for `@saeima-tracker`), `'commentary'` (third-party allegations with `speaker_id` set), `'program_promise'` (party election-program promises — see below). Readers filter by `claim_type`, not URL heuristics — **every render + brief query gates on `claim_type='position'`**, so non-`position` types are invisible to those surfaces by construction (this is what keeps program promises off politician pages / coverage / dashboards for free). See [CHANGELOG § claim_type split](wiki/CHANGELOG.md#2026-04-11--claim_type-split-position-vs-saeima_vote) + [§ Komentētāji speaker_id](wiki/CHANGELOG.md#2026-04-23--komentētāji-speaker_id-on-claims).

   4a. **`claims.party_id` (nullable FK→`parties`) + `claim_type='program_promise'` attribute a claim to a PARTY** (party election programs, 2026-07-02). `party_id` = the party; `opponent_id` = the party's list leader who carries the program (idempotency triple stays `(opponent_id, source_url, topic)`, so store **one consolidated promise per topic** per program source — many promises sharing a topic+URL would collapse). Program promises render only in the party page's "Programma" section (`src/render/parties.py` filters `party_id=? AND claim_type='program_promise'`); they are excluded everywhere else automatically by the `claim_type='position'` gate above. `NULL` for all ordinary politician claims. Program docs ingest via `scripts/ingest_url.py` (HTML or PDF path, `MAX_CHARS=200k`). Threaded through `db.store_claim`/`tools.store_claim`/`analyze.save_analysis` (`party_id=` kwarg). Migration + `idx_claims_party` in `src/db.py` (index only there, NOT `schema.sql`, since `executescript` predates the ALTER). Rollback: `data/rollback_claims_party_id_2026-07-02.sql`.

5. **`claims.speaker_id` attributes authorship separately from subject.** `NULL` (or `= opponent_id`) = first-party: the politician IS the speaker. Non-NULL and `≠ opponent_id` = third-party commentary (typically `relationship_type='commentator'`). Readers needing a concrete speaker should use `COALESCE(speaker_id, opponent_id)` (convention documented in `store_claim`'s docstring; no current reader depends on it — new readers must). [CHANGELOG § Komentētāji](wiki/CHANGELOG.md#2026-04-23--komentētāji-speaker_id-on-claims) + [`wiki/operations/agenti/claim-extractor.md`](wiki/operations/agenti/claim-extractor.md).

6. **`claims.document_id` is `Optional`.** `claim_type='saeima_vote'` claims store NULL (vote provenance via `saeima_individual_votes.politician_id` (=`opponent_id`) → parent `saeima_votes.url` (=`source_url`) / `saeima_votes.vote_date` (=`stated_at`)); `position` and `commentary` REQUIRE `document_id NOT NULL`. `documents.platform='saeima'` rows should not be created (convention, not code-enforced). [CHANGELOG § Strukturālā sanācija](wiki/CHANGELOG.md#2026-04-25--strukturālā-sanācija-pub_at-meta-tag-fix--saeima-vote-as-document-anti-pattern-noņemšana).

## Pipeline Invariants

7. **Contradiction check is mandatory.** For every new claim, compare against the full history for that politician (`search_similar_claims` with directional `claim_type_filter`). Store via `store_contradiction()`. Type values live in the `contradictions.severity` column: `direct_contradiction`, `reversal`, `minor_shift` (there is no separate `contradiction_type` column). Also check rhetoric-vs-action. `speaker_scope` defaults to `'first_party'`; pass `'commentary'` for commentator-self-consistency or `'all'` for legacy behavior. [CHANGELOG § Komentētāji](wiki/CHANGELOG.md#2026-04-23--komentētāji-speaker_id-on-claims).

8. **Context notes (`note_type='context'`) are append-only — add new rows, never overwrite.** Check existing notes before adding to avoid duplicate tendences. Overwriting destroys the evolution-over-time signal tendences exist to preserve. (`daily_brief`/`weekly_brief` rows in the same table are the deliberate exception — UPSERT-refreshed on same-day re-runs.)

9. **`save_analysis()` is atomic.** Analysis + claims + reviewed-docs update run in one SQLite transaction. Catastrophic DB failures return `status="failed"` with `transaction_rolled_back` and persist nothing. Validation-level skips (missing source_url, inactive politician) return `status="partial"` without rollback.

## Coalition Classification

10. **Truth source is `parties.coalition_status`.** Read via `src.coalition.get_coalition_map(db)` (batch) or `party_status(party)` (single). **Never** use `tracked_politicians.relationship_type` for coalition logic — it's a legacy per-politician tracking role.

- **`tracked_politicians.party` must be stored consistently within a single party** — full name is the norm (`MMN`/`JKP` are the short-name exceptions). Rendering resolves both forms (`get_coalition_map` + `_party_slug_map`), but string-grouping (the brief coalition/opposition table, wiki party counts) breaks on a mix — e.g. `ASL` + `Austošā Saule Latvijai` were counted as two parties until unified 2026-06-05 (rollback `data/rollback_party_label_hygiene_2026-06-05.sql`).

## Social feed_type

11. **`social_accounts` is X-only, one row per politician** (UNIQUE `(opponent_id, platform, handle)`; FB/website → `external_profiles`). **`feed_type` ∈ {`first_party`, `relay`}** controls `_store_tweets` linking: first_party requires per-tweet author handle match for `role='subject'`; relay defers to text-scanned mentions via `link_politicians_to_documents` (matches RSS flow). **`relationship_type='commentator'` is deprecated for new entries** — historical commentary claims with `speaker_id` FK remain as audit trail. [CHANGELOG § feed_type](wiki/CHANGELOG.md#2026-04-23--social_accountsfeed_type-relay-vs-first_party) + [§ Commentator demotion](wiki/CHANGELOG.md#2026-04-25--commentator-demotion--profila-x-subtaba).

12. **`saeima_votes.bill_id` and `saeima_bills.current_stage` are updated only via `append_bill_stage()`.** No other `UPDATE` to these fields is permitted. This protects denormalization sync — the vote→stage→bill timeline is atomic, and manual writes shred historical integrity.

13. **`platform='video'` documents store full speaker-labelled transcripts.** Content is `[mm:ss] @handle: text` lines. `claim_type` stays `'position'`; per-claim `source_url` carries a timestamp anchor (`?t=N` YouTube, `#t=N` elsewhere), which preserves `store_claim()` idempotence on the `(opponent_id, source_url, topic)` tuple. Extraction runs through `@video-extractor` per-speaker pass (not `@claim-extractor`). See [wiki/operations/agenti/video-extractor.md](wiki/operations/agenti/video-extractor.md). **Operational since 2026-07-22** (E2E-verified: fetch → AiLab ASR → pyannote community-1 diarize → align → finalize → extraction stop-gate). Known limit: diarization speaker boundaries bleed on heated crosstalk — prefer calm interviews; the extractor's attribution stop-gate catches bad cases (see BACKLOG § Video ingest).

## Output Conventions

- **UI language is Latvian throughout.** Claims = Pozīcijas, Contradictions = Pretrunas, Patterns = Tendences.
- **Timestamps use `now_lv()` from `src/db.py`** (Latvia UTC+3 / EEST).
- **Topic names use 32 canonical groups** from `src/topic_map.py`. `store_claim()` / `store_contradiction()` auto-normalize; unknown topics pass through.
- **`sentiment=0.0`** on `save_analysis()` — the parameter exists only for schema compatibility; sentiment analysis was removed as unreliable. Never compute it, never store a non-zero value, never build features on it.
- **Grammar + stylistics gate (LV).** Before `store_*()`, commit, wiki sync, or publish, check every new Latvian string (claims, contradictions, syntheses, briefs, social drafts, UI text) for grammar (locījumi, garumzīmes, verb forms) AND stylistics (clear flow, no calques/invented words, "Dienas pārskats" not "brief"). This is Claude's responsibility before the tool call, not the operator's — if unsure a form is correct, rephrase. **Exception: `claims.quote` is VERBATIM** — a politician's own typos stay ("Steidamas", Kulbergs 2026-06-11; operator decision 2026-07-07). Correcting a quote is misquoting; the gate applies to OUR words (stance, reasoning, summary), never to cited ones.
- **No inline JavaScript on any public page — strict CSP.** The live site serves `script-src` WITHOUT `'unsafe-inline'` (`assets/htaccess.template`): browsers silently kill every `<script>` lacking `src=` and every `on*=` attribute, including ones injected via innerHTML. All executable JS lives in `assets/*.js` (auto-cache-busted — `_resolve_assets_version()` globs the dir); per-page data goes in non-executable `<script type="application/json" id="…">` blocks or `data-*` attributes; handlers are `data-*` + delegation. Locked by `tests/test_no_inline_js.py` across templates, curated pages, and JS strings. A new EXTERNAL script/style/font/connect host must be added to the CSP allowlist in `htaccess.template` or the resource silently fails on the live site (local preview won't catch it — no header). Never re-add `'unsafe-inline'` to script-src. [CHANGELOG § Stingrā CSP](wiki/CHANGELOG.md#2026-07-23--stingrā-csp-drošības-galvenes--viss-inline-js-uz-assetsjs). UI patterns: [wiki/operations/ui-conventions.md](wiki/operations/ui-conventions.md).

## Known Traps (named failure modes → the rule that prevents each)

Each of these has bitten this project at least once; several recur monthly. History + rationale: `wiki/CHANGELOG.md`, open instances: `BACKLOG.md`.

- **T1 — Bare-surname / substring match.** The matcher links a namesake, geonym, or word-substring ("Kolu"→"Kolumbija"). *Rule:* substring matcher, no diacritic folding — if the person in the text isn't clearly the tracked politician, mark the doc empty and log the collision for operator review; `negative_patterns` fixes are operator-approved, never auto-added.
- **T2 — Silent idempotency merge.** Distinct same-topic positions from one document collapse into one claim; `failures` stays empty. *Rule:* Data Contract #3 corollary — differentiate topics or consolidate deliberately; verify stored-count == intended-count.
- **T3 — `source_url` drop misread as success.** Dropped claims surface only in the returned `failures` (stderr). *Rule:* read `failures`; every `missing_source_url` is a real loss to resolve.
- **T4 — Stripped-diacritic Latvian (context drift).** *Rule:* if diacritic validation (`src/quality.py`) trips mid-session, STOP and start a fresh session — drift is autoregressive. Parallel subagents get clean contexts.
- **T5 — `empty_doc_ids` omitted.** Zero-claim docs keep `reviewed_at IS NULL` and re-enter the backlog forever. *Rule:* `empty_doc_ids` is mandatory whenever a reviewed doc yields no claims.
- **T6 — Stale party/role after a public switch.** A claim says "leaving party X"; `tracked_politicians.party` still says X → blocs misclassify. *Rule:* verify + manual UPDATE (+ paired rollback) in the same routine; check role chronology (vote gaps!) before assuming a data bug.
- **T7 — Brief skeleton coverage gap.** Top-5-by-count sections silently drop high-salience solo topics. *Rule:* re-add every dropped high-salience solo before enrichment.
- **T8 — Saeima "0 votes" read as an empty day.** Two vote-URL patterns exist (static `?OpenDocument` + JS `addVotesLink`); titania re-archives under new UNIDs. *Rule:* scrape BOTH, take the union; 0 votes at a session with agenda items = STOP and report; completeness by `(vote_date, vote_time)`, never URL.
- **T9 — Rhetoric-vs-vote via embeddings.** Vote claims ARE vectorized (`store_claim` embeds every claim_type), but semantic similarity does not surface rhetoric↔vote STANCE mismatches, and the post-kNN `claim_type_filter` (see T10) excludes them from rhetoric searches anyway. *Rule:* an embedding search can never clear rhetoric-vs-vote; only `@contradiction-hunter`'s structural SQL pass (+ mandatory faction check) finds vote mismatches.
- **T10 — Cross-type embedding comparison.** *Rule:* `claim_type_filter` is applied post-kNN; always pass `['position']` for rhetoric-vs-rhetoric.
- **T11 — "Optional-looking" step skipped under batch load** → required fields end up NULL. *Rule:* no optional substeps — atomic units (capture → summarize → store), no deferred batching, final gate hard-fails on NULLs.
- **T12 — Upstream format change misdiagnosed as removal** (X, VID, and saeima.lv have all done it). *Rule:* assume format change; check the upstream tracker; keep fallbacks; alert+retry, not hard failure.
- **T13 — Homonym contamination in bulk per-person ingest.** *Rule:* disambiguation whitelists (`vad_disambig` / `negative_patterns`) + a pre-publish audit of each new cohort.

## Quality Bars (checkable, per deliverable)

Pass/fail criteria for every deliverable live in [wiki/operations/quality-bars.md](wiki/operations/quality-bars.md) — consult BEFORE storing or publishing, not after. Canonical carriers must agree with that page: claims → `.claude/agents/claim-extractor.md` · contradictions → `/deep-check` + `@devils-advocate` · daily/weekly brief → `@brief-writer`/`@weekly-brief-writer` + `/dienas-rutina` · social thread → `/social-thread` · render+deploy → `scripts/check.sh` + `@quality-reviewer` (hard gate) · seeding → [seeding.md](wiki/operations/seeding.md) · Saeima session → `.claude/agents/saeima-tracker.md`.

## When Uncertain — Escalation Rules

1. **Attribution uncertain** (is this text really about the tracked politician?) → return empty, log the collision candidate for operator review. Never guess-link; never auto-add `negative_patterns`.
2. **Claim confidence 0.5–0.6 or weak context** → store with needs_review. **<0.5** → NEEDS_REVIEW status. Never silently drop; never inflate confidence to clear a bar.
3. **Contradiction plausible but unverified** → send to `@devils-advocate`; store survivors `confirmed=0`. Never auto-confirm. Zero yield is a valid outcome (~1 publishable per ~2700 raw pairs) — do not manufacture findings.
4. **Diacritic validation trips / suspected context drift** → STOP the session immediately, start fresh (T4).
5. **Scraper returns 0 or breaks** → treat as pattern error, not empty result (T8, T12). STOP + report rather than recording an empty day.
6. **Unsure a Latvian form is correct** → rephrase into a form you are certain of. Guessing grammar is not allowed past the gate.
7. **Anything outward-facing** (brief, social post, deploy, public-repo change) → proofread, confirm assets, ask the operator first. One approval ≠ standing approval.
8. **Any data mutation by hand** → paired `data/rollback_*.sql` in the same commit BEFORE applying.
9. **Denormalized field might be stale** (party/role/topic) → verify against the truth source (`parties.coalition_status`, `votes.topic`, role chronology) before trusting or citing it.
10. **A decision future sessions must honor** → write it into this file / wiki / agent prompt, not private memory.

Meta-rule: prefer the branch that stops-and-surfaces over the branch that writes.

## Commands

The two you'll always use:

```bash
bash scripts/check.sh                                                # Verification (ruff + pytest + generate_public_site smoke)
python -c "from src.routine import print_routine; print_routine()"   # Routine status
python serve.py                                                      # atmina ops dashboard at http://127.0.0.1:8080
```

Full command reference (deploy, ingest, diagnostika, video, social agent): [wiki/operations/commands.md](wiki/operations/commands.md). Tech stack + first-time setup: [wiki/operations/dev-setup.md](wiki/operations/dev-setup.md). Operator dashboard runbook: [wiki/operations/atmina-ops.md](wiki/operations/atmina-ops.md).

## Runbooks & Agents

Routines + guides: [wiki/operations/operacijas.md](wiki/operations/operacijas.md) (daily/weekly/monthly, deploy, rubrics, source framing, KNAB, social agent, telegram brief, content pipeline, twikit notes). Skills ar iekodētiem guardrail — `/dienas-rutina`, `/deep-check`, `/social-thread` (X pavediens + FB posts par pārskatu), `/seed-entity` (diacritic-pair + ≤4-char sēšanas guardrail), `/saeima-ingest` (T8 divu-paternu ūnija + 0-votes-STOP), `/audit-integrity` (read-only DB integritātes sweep) — dzīvo `.claude/commands/`; invoke tos, nevis rekonstruē procedūru no atmiņas.

Agent prompts — **canonical execution**: `.claude/agents/*.md`. Human-readable descriptions: `wiki/operations/agenti/`. Available: `@claim-extractor` · `@contradiction-hunter` · `@devils-advocate` · `@quality-reviewer` · `@brief-writer` · `@weekly-brief-writer` · `@graphics-designer` · `@mentions-monitor` · `@saeima-tracker` · `@video-extractor` · `@outlet-researcher` *(on-demand: media-outlet transparency facts → `/mediji`)*.

**Executing this repo from a non-Claude-Code harness?** Read [wiki/operations/portability.md](wiki/operations/portability.md) first — how to interpret skills/agent prompts as plain procedures, what is code-enforced vs convention-only, and the LV language-gate warning (first run = dry-run).

## Schema invariants (load-bearing)

- `opponent_id` references `tracked_politicians.id` on claims, analyses, contradictions, context_notes, social_accounts, logs. Documents use `document_politicians` junction table (many-to-many with roles: subject, mentioned, mention_target).
- `relationship_type='inactive'` hides politicians from dashboard.
- **The matcher is substring-based and does NOT fold diacritics.** A politician with a diacritic surname (Pūce, Kļaviņš, Vītols, Šuvajevs) needs BOTH diacritic and ASCII variants in `name_forms` — sources that strip diacritics (X, RSS, scraped HTML) otherwise never link. Audit with `scripts/audit_matcher_name_forms.py`; seeding pattern in [seeding.md](wiki/operations/seeding.md). Pairs with the `-ņš`/`-iņa` cross-gender collision caution in `src/matcher.py::_latvian_surname_inflections`.
- **`tracked_politicians.x_handle` (legacy column) ≠ `social_accounts.handle`.** `x_handle` drives the profile's X-link in render; `social_accounts.handle` is authoritative for the X fetch. They can silently diverge (id=19 Ašeradens once held `'VDombrovskis'`) — verify `x_handle` when seeding or auditing a profile.
- **From now on, every hand-run data migration (`data/*.sql` or a `scripts/fix_*.py` that mutates rows) ships a paired `data/rollback_*.sql` committed alongside it.** A rollback that lives only in the working tree is one `git clean` away from gone — and with it the only path back from a bad reattribution. Header each rollback with the forward change it reverses + the apply date. (Pre-2026-06-08 `fix_*.py` without a rollback — e.g. `fix_relay_subject_role.py`, `fix_subject_role_leakage.py`, `fix_matcher_name_forms.py` — are acknowledged debt, not a model to copy.)
