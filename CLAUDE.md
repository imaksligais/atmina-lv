# CLAUDE.md

## Project Overview

atmina is a Latvian political transparency platform. Scrapes news sources + Twitter/X profiles (via twikit), extracts pozīcijas (claims) and pretrunas (contradictions) per politician, renders an interactive HTML site. Primary language: Latvian (lv), some Russian (ru).

**This file is the operating manual** — the project facts a fresh session cannot derive from the code and that no test enforces. Task-specific rules live in the agent prompts and skills where the task happens; this file points to them. Section numbers (Data Contract #N, inv #N, T#, escalation N) are cited from tests, `wiki/CHANGELOG.md` and agent prompts — never renumber them. This file syncs to the PUBLIC mirror: keep it free of operator-identifying or internal-only detail.

## Session Start

Read `wiki/index.md` first. Runbooks: `wiki/operations/operacijas.md`. Open work: `BACKLOG.md` (index + § Ne-darīt + § Atliktais) and `backlog/*.md` (read the topic file before working in that area). Decisions: `wiki/CHANGELOG.md` (≤5 lines per entry; narrative is `git log`), rationale before 2026-09-07: `wiki/CHANGELOG-arhivs.md`, 2026-09-07…09-30: `wiki/CHANGELOG-arhivs-2026-09.md`. Claude Code IS the analysis engine — analysis is written interactively, not by scripts. Longer earlier versions of this file: `git show f83b799c:CLAUDE.md`, `git show 196490a6:CLAUDE.md`, `git show 079da816:CLAUDE.md`.

## Standing Decisions (operator-set; do not re-litigate)

- **Public anonymity.** atmina.lv publishes anonymously. Never add operator-identifying information (personal names, company names, e-mail addresses) to any public surface — site, public mirror, social posts, commit text, repo docs. The public mirror is this repo minus a fixed exclusion set (maintainer note, private): **assume any new file is public unless its directory is in that set.**
- **Timing.** Ingest runs all day; claim extraction + daily brief only in the afternoon (~15:00 LV or later). A morning "0/N analyzed" is the expected state, not a failure.
- **Subagent model = Opus, both directions.** ALL project agents in `.claude/agents/` carry `model: opus`. Downward: a smaller-model trial (2026-06-11) made LV grammar errors in ~30–40% of stances. Upward: subagents must NOT inherit a Mythos-tier session model (Fable) — cost not justified (operator decision 2026-07-21). Workflow `agent()` calls must pass `model: 'opus'` explicitly (frontmatter pins don't reach plain `agentType: 'general-purpose'` calls). The main loop may run on any tier.
- **Publish pause.** Nothing outward-facing auto-publishes. Daily/weekly brief → manual proofread + featured-image confirm + explicit operator approval BEFORE deploy. Approval for one publish is never standing approval for the next.
- **Harsh content is not a reason to drop a position** (operator decision 2026-10-06). A politician may say anything, and the position may be as sharp as they like: insults, accusations, crude labels about named people or parties are stored as positions when they are the speaker's own words. The guard is the attribution wrap («ko viņš raksturo kā …», `.claude/agents/claim-extractor.md` § 3.6), never deletion or `NEEDS_REVIEW` for tone alone. Delete only for the usual reasons: not the speaker's words, unreadable context, wrong attribution.
- **Syntheses are hand-written.** `wiki/synthesis/` pages are manually authored (standing decision 2026-04-22). Do not propose an auto-synthesis agent.
- **Deploy is the FULL local tree (Cloudflare Workers Static Assets since 2026-09-16).** `bash scripts/deploy.sh --no-delete` uploads all of `output/atmina/`; `--no-delete` / `--delete` are accepted as no-ops. Whatever is NOT in the local tree is gone from the live site after deploy, so the tree must be complete first. Domains and redirects are Cloudflare-panel settings (`wiki/operations/deploy.md`). The old host stays in reserve until 2026-10-16 (BACKLOG 67).
- **Rules live in the repo, not private memory.** Any decision future sessions must honor goes into this file, a wiki runbook, or an agent prompt — subagents, cloud runs, and fresh sessions cannot see private memory.

## Working Conventions

- **Silent success is a defect class.** `save_analysis()` reports dropped input only in its returned `failures` list (stderr): read returned failure structures and verify stored-count == intended-count. A collision with a claim stored in an EARLIER call is silent — only the count check catches it. Any new operation that can drop input must report what it dropped.
- **A gate that cannot fail is not evidence — report the denominator, not just the finding.** State how many things a check examined; 0 or 1 is a broken gate. A checker's tests must read what the writer actually writes; a number in `BACKLOG.md`/`CHANGELOG.md` is trustworthy only with the query that produced it; **"IZPILDĪTS" means the code is in the tree, not that it ever ran** — record what exercised it. A gate is proven only once you have seen it FAIL (revert the fix).
- **Write through the `store_*()` functions — a raw INSERT silently drops their guardrails.** Validation lives in the function, not the schema. If a store function refuses your row, the row is wrong — do not route around it.
- **Denormalized fields are stale by default.** `tracked_politicians.party`/`role` and `claims.topic` do not auto-sync from the news — verify against the truth source before trusting or citing them (T6).
- **Short generated name forms are quarantined.** Matcher-generated forms ≤4 chars are substring bombs ("Kolu" → "Kolumbija"). Never auto-add `name_forms` or `negative_patterns` — operator review by standing rule.
- **Tests: name the failure first, prove it by mutation, never touch the live DB.** A test that only restates the code it follows is not worth writing; prune only on mutation evidence (method: CHANGELOG 2026-09-24 (2)). `tests/conftest.py` § 4–5 isolate every test from the production DB; a test that genuinely needs it names `src.db.PRODUCTION_DB_PATH` and skips when absent.
- **Stop beats write.** When two rules could apply and you cannot tell which, choose the action that stops-and-surfaces over the one that writes.
- **Deleting a claim does NOT remove its source document from the site.** The profile's X subtab renders the last 50 `role='subject'` tweets straight from `documents`. When withdrawing unsound content, decide whether the document goes too and say which surface you cleared. **A claim under a PUBLISHED contradiction:** withdraw the contradiction with `src.db.withdraw_contradiction()` (`confirmed=-1`), never `confirmed=0` — that deletes the page published briefs link to.
- **Abstention blocks — the label differs, the effect does not.** In the Saeima `Atturas` denies the majority exactly as `Pret` does; state the ballot as recorded, never "balsoja pret". Saeima only — not the EU Council. Full rule: `.claude/agents/contradiction-hunter.md` § 6.

## Data Contracts

1. **TOMBSTONE (2026-07-29).** `oppo_briefs` was removed; the number is kept so #2–#6 references hold. Strict Pydantic models live in `src/models.py`.

2. **Claims without `source_url` are dropped** in `save_analysis()` validation — as a `missing_source_url` entry in `failures`, not raised. `store_claim()` called directly happily inserts a NULL `source_url`. No URL = no provenance = can't cite, can't re-fetch, can't contradict.

3. **`store_claim()` is idempotent on `(opponent_id, source_url, topic)`.** Re-running the same triple returns the existing claim_id; first-write-wins. **Corollary (trap T2):** several DISTINCT positions in one topic from one document silently merge into the first claim — differentiate topics or consolidate deliberately, and verify counts.

4. **`claim_type` values:** `'position'` (default), `'saeima_vote'` (`@saeima-tracker` only), `'commentary'` (third-party, `speaker_id` set), `'program_promise'` (4a). **Every render + brief query gates on `claim_type='position'`**, so non-`position` types are invisible to those surfaces by construction. Filter by `claim_type`, never URL heuristics. [CHANGELOG § claim_type split](wiki/CHANGELOG.md#2026-04-11--claim_type-split-position-vs-saeima_vote).

   4b. **A `saeima_vote` claim exists only for a CAST ballot** (`Par`/`Pret`/`Atturas`/`Nebalsoja`), never for attendance — code-enforced in `generate_claims_from_votes()`. Attendance lives in `saeima_individual_votes`.

   4a. **`claims.party_id` + `claim_type='program_promise'` attribute a claim to a PARTY** (election programs). `opponent_id` = the list leader carrying the program; store **one consolidated promise per topic** per program source (idempotency triple unchanged). Rendered only on the party page (`src/render/parties.py`).

5. **`claims.speaker_id` attributes authorship separately from subject.** `NULL` or `= opponent_id` = first-party; otherwise third-party commentary (deprecated for new rows — #11). Readers needing a concrete speaker use `COALESCE(speaker_id, opponent_id)`. [CHANGELOG § Komentētāji](wiki/CHANGELOG.md#2026-04-23--komentētāji-speaker_id-on-claims).

6. **`claims.document_id` is `Optional`.** `saeima_vote` claims store NULL (provenance via `saeima_individual_votes` → `saeima_votes`); `position` and `commentary` REQUIRE it. Never create `documents.platform='saeima'` rows. [CHANGELOG § Strukturālā sanācija](wiki/CHANGELOG.md#2026-04-25--strukturālā-sanācija-pub_at-meta-tag-fix--saeima-vote-as-document-anti-pattern-noņemšana).

## Pipeline Invariants

7. **Contradiction check is mandatory.** Compare every new claim against that politician's full history (`search_similar_claims` with directional `claim_type_filter`), rhetoric-vs-action included; store via `store_contradiction()`. Types live in `contradictions.severity`: `direct_contradiction`, `reversal`, `minor_shift`.

8. **Context notes (`note_type='context'`) are append-only — add new rows, never overwrite.** Overwriting destroys the evolution-over-time signal. Exceptions: `daily_brief`/`weekly_brief` rows (UPSERT on same-day re-runs), and a note written by the CURRENT routine on the current routine day that was **never deployed** may be corrected in place with a paired rollback (operator decision 2026-09-09).

   **Carrier asymmetry you must not conflate.** A `context` note renders in a markdown-enabled box and may use bullets; a `political_tensions.description` renders into a table cell and must be one line (`store_tension()` refuses a newline). Verify a hand edit to either in the RENDERED HTML.

9. **`save_analysis()` is atomic.** A DB failure persists nothing (`status="failed"`); validation skips return `status="partial"` and list what they dropped (Silent success).

## Coalition Classification

10. **Truth source is `parties.coalition_status`** via `src.coalition.get_coalition_map(db)` / `party_status(party)`. **Never** use `tracked_politicians.relationship_type` for coalition logic.

- **`tracked_politicians.party` must be stored consistently within a single party** — full name is the norm (`MMN`/`JKP` excepted); string-grouping in briefs and wiki breaks on a mix.

## Source-specific invariants (social · bills · video)

11. **`social_accounts` is X-only, one row per politician.** **`feed_type` ∈ {`first_party`, `relay`}** decides how tweets link politicians; **`relationship_type='commentator'` is deprecated for new entries**; **journalists get `feed_type='relay'` by default** (operator decision 2026-08-21). Rules and exceptions: [seeding.md](wiki/operations/seeding.md), `/seed-entity`.

12. **`saeima_votes.bill_id` and `saeima_bills.current_stage` are updated only via `append_bill_stage()`.** No other `UPDATE` in new code. Named one-off exceptions, not a pattern: `scripts/backfill_saeima_bills.py`, `scripts/_apply_session_summaries_2026_05.py`, `data/fix_bill_current_stage_{procedural,p3_pilot}_2026-09-28.sql`, `scripts/recompute_bill_status.py` (reuses `derive_bill_denorm()`, the same rule `append_bill_stage()` applies).

13. **`platform='video'` documents store full speaker-labelled transcripts.** Never used in production; extraction runs only through `@video-extractor` — read [video-extractor.md](wiki/operations/agenti/video-extractor.md) before the first run.

## Output Conventions

- **UI language is Latvian throughout.** Claims = Pozīcijas, Contradictions = Pretrunas, Patterns = Tendences.
- **Timestamps use `now_lv()` from `src/db.py`** — but not every column is LV time (Schema invariants).
- **Topic names use 33 canonical groups** from `src/topic_map.py`; `store_*()` auto-normalize.
- **`sentiment=0.0`** on `save_analysis()` — schema compatibility only. Never compute it or build on it.
- **Grammar + stylistics gate (LV).** Before `store_*()`, commit, wiki sync or publish, check every new Latvian string for grammar (locījumi, garumzīmes, verb forms) AND stylistics (no calques/invented words, "Dienas pārskats" not "brief"). Your job, not the operator's — if unsure, rephrase. **Exception: `claims.quote` is VERBATIM** — a politician's own typos stay (operator decision 2026-07-07); the gate applies to OUR words (stance, reasoning, summary), never to cited ones.
- **No inline JavaScript on any public page — strict CSP.** JS only in `assets/*.js`; a new external host goes into the `assets/_headers` allowlist. Locked by `tests/test_no_inline_js.py`, `test_csp_external_hosts.py`. [CHANGELOG § Stingrā CSP](wiki/CHANGELOG.md#2026-07-23--stingrā-csp-drošības-galvenes--viss-inline-js-uz-assetsjs).

## Known Traps (named failure modes → the rule that prevents each)

Each has bitten this project at least once. Rationale: `wiki/CHANGELOG*.md`; open instances: `BACKLOG.md`.

- **T1 — Bare-surname / substring match.** The matcher links a namesake, geonym or word-substring. *Rule:* escalation rule 1.
- **T2 — Idempotency merge.** *Rule:* Data Contract #3 corollary.
- **T3 — `source_url` drop misread as success.** *Rule:* Data Contract #2; read `failures`.
- **T4 — Stripped-diacritic Latvian (context drift).** *Rule:* escalation rule 4.
- **T5 — `empty_doc_ids` omitted.** Zero-claim docs keep `reviewed_at IS NULL` and re-enter the queue forever. *Rule:* pass `empty_doc_ids` for every reviewed doc with no claims.
- **T6 — Stale party/role after a public switch.** *Rule:* verify + UPDATE with a paired rollback; cross-check `saeima_individual_votes.faction` by coverage over the sitting window, not one vote. **Corollary — party ≠ faction:** a member can sit outside the faction (`faction=NULL`, legitimate — do NOT "fix"); a per-vote statement uses THAT vote's `faction` distribution. **Second corollary:** store faction labels only via `src.saeima.votes.normalize_faction()` (`tests/test_faction_label_canonical.py`).
- **T7 — Brief skeleton coverage gap.** *Rule:* the `### Pārējās tēmas` table may be promoted from, never silently deleted (`.claude/agents/brief-writer.md`).
- **T8 — Saeima "0 votes" read as an empty day.** *Rule:* scrape all vote-URL patterns and take the union (`.claude/agents/saeima-tracker.md` Step 2.B, `/saeima-ingest`); 0 votes at a session with agenda items = STOP.
- **T9 — Rhetoric-vs-vote via embeddings.** *Rule:* an embedding search never clears rhetoric-vs-vote; only `@contradiction-hunter`'s structural SQL pass finds vote mismatches.
- **T10 — Cross-type embedding comparison.** *Rule:* pass `claim_type_filter=['position']` for rhetoric-vs-rhetoric.
- **T11 — "Optional-looking" step skipped under batch load.** *Rule:* no optional substeps; atomic units; the final gate hard-fails on NULLs.
- **T12 — Upstream format change misdiagnosed as removal.** *Rule:* assume format change; keep fallbacks; alert + retry.
- **T13 — Homonym contamination in bulk per-person ingest.** *Rule:* disambiguation lists + a pre-publish audit of each new cohort.
- **T14 — Procedural vote quoted as a policy position.** *Rule:* before citing one vote, read every vote sharing that `document_nr`; a mixed chain is cited as a chain or not at all (`.claude/agents/contradiction-hunter.md`).
- **T15 — Deploy pārnes VISU build koku, arī nepublicētus pārskata melnrakstus.** *Rule:* `deploy.sh` preflight atsaka bez `scripts/approve_publish.py <slug>` rindas; `--no-output-check` ir apzināta apiešana ([deploy.md](wiki/operations/deploy.md)).
- **T16 — Blind agreement cannot detect a rubric defect.** Coders who share a wrong rule agree unanimously. *Rule:* audit each rubric branch against the source claim text, separately from coder agreement — never from a keyword ("kvotas" matched both "we will impose quotas" and "we object to quotas").
- **T17 — Two clocks in one database.** *Rule:* before comparing timestamps across tables, check which clock writes each column (Schema invariants) and subtract the offset.
- **T18 — An audit classifier needs its own false-positive pass before its output becomes a work list.** *Rule:* read a sample of each class; never delete on a classifier's word.
- **T19 — When you cannot prove the new evidence is COMPLETE, flag; never delete.** *Rule:* a destructive step needs positive proof of completeness; otherwise mark `suspect_at` for a human.
- **T20 — A `saeima_vote` stance sentence describes the BILL, not that vote.** Amendment/procedural votes repeat the bill's summary («… atbalstīts 1. lasījumā (52:0)») — by operator decision, not a defect (`BACKLOG.md` § Ne-darīt). *Rule:* the ballot prefix is this vote; the outcome comes from `saeima_votes.result`/totals; never open a [FIX] for it.

## Quality Bars (checkable, per deliverable)

Pass/fail criteria for every deliverable: [wiki/operations/quality-bars.md](wiki/operations/quality-bars.md) — consult BEFORE storing or publishing.

## When Uncertain — Escalation Rules

1. **Attribution uncertain** (is this text really about the tracked politician?) → return empty, log the collision for operator review. Never guess-link.
2. **Claim confidence 0.5–0.6 or weak context** → store it with `reasoning` prefixed `NEEDS_REVIEW: `; below 0.5 also say why. Never silently drop; never inflate. There is **no `needs_review` parameter** — an extra key is silently discarded. Confidence bands: `.claude/agents/claim-extractor.md` § 4.

   **Readers must query `claims.review_status`, never the text.** Triggers derive it from `reasoning` — **never write the column by hand**; age queue rows via `src.db.open_review_queue()`; resolve by replacing the marker with `Izvērtēts YYYY-MM-DD:` (case-sensitive `GLOB` — do not "fix" it to `LIKE`).
3. **Contradiction plausible but unverified** → `@devils-advocate`; store survivors `confirmed=0`. Never auto-confirm. Zero yield is valid — do not manufacture findings.
4. **Diacritic validation trips / suspected context drift** → STOP the session, start fresh.
5. **Scraper returns 0 or breaks** → pattern error, not an empty result (T8, T12). STOP + report.
6. **Unsure a Latvian form is correct** → rephrase into one you are certain of.
7. **Anything outward-facing** (brief, social post, deploy, public-repo change) → proofread, confirm assets, ask the operator first. One approval ≠ standing approval.
8. **Any data mutation by hand** → paired `data/rollback_*.sql` committed BEFORE applying; parallel agents each get a UNIQUE rollback filename. If it touches `claims.topic` or `claims.stance`, **re-embed the row** (`scripts/reembed_claims.py`; never for `saeima_vote` rows — they get no vector by design).

   **And `topic` is part of the idempotency key, so an `UPDATE claims SET topic` can MANUFACTURE duplicates** — run the collision query on `(opponent_id, source_url, topic)` first and decide dedup in the same script. Never run a topic migration over votes inside a pending load's scope.
9. **Denormalized field might be stale** → verify against the truth source before citing it.
10. **A decision future sessions must honor** → write it into this file / wiki / agent prompt, not private memory.

## Commands

```bash
bash scripts/check.sh                                                # ruff + pytest + render smoke
.venv/Scripts/python.exe -c "from src.routine import print_routine; print_routine()"   # Routine status
.venv/Scripts/python.exe serve.py                                    # ops dashboard, http://127.0.0.1:8080
```

**Always `.venv/Scripts/python.exe`, never bare `python`.** Bare `python` resolves to a foreign venv, and the failure is a PARTIAL WRITE, not an error (votes stored, their claims lost). Full reference: [wiki/operations/commands.md](wiki/operations/commands.md).

## Runbooks & Agents

Skills with built-in guardrails (`/dienas-rutina`, `/deep-check`, `/social-thread`, `/seed-entity`, `/saeima-ingest`, `/audit-integrity`) live in `.claude/commands/`; agent prompts (canonical execution) in `.claude/agents/`. Invoke them rather than reconstructing a procedure from memory. Roster: [wiki/operations/agenti/agenti.md](wiki/operations/agenti/agenti.md); non-Claude-Code harness: [portability.md](wiki/operations/portability.md).

## Schema invariants (load-bearing)

- `opponent_id` references `tracked_politicians.id`. Documents link to politicians through `document_politicians` (roles: subject, mentioned, mention_target). `relationship_type='inactive'` hides a politician.
- **The matcher is substring-based and does NOT fold diacritics.** A diacritic surname needs BOTH diacritic and ASCII variants in `name_forms`. **A full `rescan_all` re-adds false links earlier fixes deleted** — dry-run on a DB copy and drop pairs restored by `data/rollback_*.sql`. **The project's own X account is never a source** (`src/matcher.py::PROJECT_X_HANDLES`). Eval gate: `scripts/eval_matcher_collisions.py`; seeding: [seeding.md](wiki/operations/seeding.md).
- **Timestamp columns are NOT one convention — check before you filter by date.** `claims`, `context_notes`, `documents`, `contradictions` store **LV** time; `political_tensions.created_at`, `analyses.created_at`, `document_politicians.created_at` store **UTC**. A UTC column needs `DATE(col, 'localtime')`; an LV column must NOT get it — either mistake shifts rows by a day exactly when the evening routine runs. **Never "fix" a timestamp by writing `now_lv()` into a UTC column.** Per-column convention: `src/schema.sql`.

  **A ROUTINE day is not a calendar day.** The day boundary for routine counts is **05:00 LV**: use `src.briefs.routine_day_window(day)` / `current_routine_day()`, never a bare calendar day (it SILENTLY drops rows). Brief-skeleton claims are the exception — they use `stated_at`.
- **`documents.scraped_at` is MUTABLE for `platform='web'` — a past day's document count can go DOWN.** URL-first dedup updates an edited article in place and resets `reviewed_at`; rows before 2026-08-18 may cite text that no longer exists (signature `scraped_at > reviewed_at`).
- **`documents.reviewed_at` is per-DOCUMENT, not per-politician.** A review stamp covers everyone named in the document, so another politician looks processed though nothing was extracted for them. Say which politician a stamp covers.
- **A brief's identity is its SUBJECT date, never `created_at`.** Read it with `src.briefs.brief_subject_date()`.
- **`tracked_politicians.x_handle` (legacy column) ≠ `social_accounts.handle`.** The latter drives the X fetch; they can silently diverge — verify both when seeding or auditing.
- **From now on, every hand-run data migration ships a paired `data/rollback_*.sql` committed alongside it** (escalation rule 8), headed with the forward change and apply date.
