# atmina — Operating-manual proposal (v2)

_v1 drafted 2026-07-07 morning (analysis only). **v2 same day: the CLAUDE.md rewrite is APPLIED** (see repo diff), the skill briefs are sharpened, and two v1 errors are corrected — see § v1→v2 changelog at the end. Goal: CLAUDE.md + wiki self-sufficient so a weaker model (or any session without private memory) works here at a high bar._

---

## 0. The structural problem — and the constraint v1 missed

**Load-bearing standing decisions lived only in private auto-memory**, invisible to subagents, cloud runs, and fresh sessions: anonymity, afternoon-only extraction timing, extraction-on-Opus, publish-pause, manual syntheses.

**Resolution (applied):** each *rule* is promoted into CLAUDE.md § Standing Decisions; the private *why*/history stays in memory.

**The constraint v1 missed: CLAUDE.md and most of `docs/` sync to the PUBLIC mirror.** The exclusion set covers only `data/*.sql`, `docs/audits`, `docs/tweet_bank`, `docs/social`, `docs/funding`, `wiki/dailies`, `wiki/log-ingest` — `docs/plans/` (this file) is public. Consequences:

- The anonymity rule is phrased **neutrally** in CLAUDE.md ("never add operator-identifying information to any public surface") — stating the policy leaks nothing; naming what must not be named would.
- New convention, now in CLAUDE.md: **assume any new file is public unless its directory is in the exclusion set.**
- v1 of this document referenced a private memory slug whose filename itself contained identity-linking text — scrubbed in v2. Repo docs may reference memory *topics*, never slugs that embed sensitive names.

## 0b. Second constraint v1 missed: CLAUDE.md numbering is load-bearing

`wiki/CHANGELOG.md`, agent prompts, memory files, and `tests/test_invariants.py` reference sections by number ("Data Contract #3", "inv #13"). The applied rewrite therefore **preserves every existing section name and number verbatim** and adds the new material around them: § Standing Decisions, § Working Conventions, § Known Traps (T1–T13), § Quality Bars, § When Uncertain.

---

## 1. What the applied CLAUDE.md rewrite contains

1. **Standing Decisions** (promoted from memory, public-safe): anonymity · afternoon timing · extraction on Opus · publish pause · manual syntheses · additive deploy · rules-live-in-repo.
2. **Working Conventions** (added): silent-success-is-a-defect-class (inspect `failures`, verify counts) · denormalized-fields-stale-by-default · ≤4-char generated name forms quarantined · stop-beats-write meta-rule.
3. **Known Traps T1–T13** — every named failure mode from BACKLOG/CHANGELOG history with the rule that prevents it: T1 substring/namesake match · T2 silent idempotency merge · T3 source_url drop misread as success · T4 diacritic drift → STOP session · T5 empty_doc_ids omitted · T6 stale party/role · T7 brief-skeleton coverage gap · T8 Saeima 0-votes ≠ empty day · T9 votes-not-vectorized (empty ≠ clean) · T10 cross-type embedding noise · T11 optional-looking steps skipped under load · T12 upstream format change ≠ removal · T13 homonym contamination in bulk ingest.
4. **Quality Bars** — pointer section; the pass/fail checklists themselves live in [`wiki/operations/quality-bars.md`](../../wiki/operations/quality-bars.md) (moved out of CLAUDE.md same day to hold per-session size at ~21 KB; CLAUDE.md keeps the deliverable → canonical-carrier map).
5. **When Uncertain** — 10 escalation rules + the stop-beats-write meta-rule.

Deliberately NOT moved into CLAUDE.md (stays in wiki/skills, referenced by pointer): rubric tables (`rubrics.md`), full routine procedures (`/dienas-rutina`), social-thread mechanics (`/social-thread`), seeding walkthrough (`seeding.md`).

## 2. Wiki follow-ups

- **APPLIED 2026-07-07:** canonical-prompt banner atop all 11 `wiki/operations/agenti/*.md`; afternoon-timing rule at the top of `daily-routine.md` (memory pointer replaced with the in-repo rule); `quality-bars.md` created + row in the operacijas.md handbook table.
- Still open: `wiki/operations/escalation.md` — optional expansion of the 10 rules into a decision tree with examples; CLAUDE.md stays the authority.
- Error-recovery playbooks (ingest hang, render timeout, deploy socket drop) — CHANGELOG records fixes, no runbook teaches recovery. Candidate: `wiki/operations/recovery.md`.

---

## 3. Three skills that save the most hours

**BUILT 2026-07-07** — live in `.claude/commands/` (seed-entity.md, audit-integrity.md, saeima-ingest.md); the briefs below were the spec. Every referenced function/script/column was verified against the code before authoring (`process_vote_snapshot` keyword-only summary kwargs, `parties.short_name NOT NULL UNIQUE`, `_latvian_surname_inflections`, `_extract_vote_urls_from_agenda` in `scripts/p3_backfill_year_urllib.py`); the audit-integrity core queries were run read-only against the live DB and surfaced real findings on the first pass (10 active politicians with ≤4-char forms; x_handle divergence id=62).

Ranked by (recurring operator time) × (severity of silent failure prevented); none duplicate `/dienas-rutina`, `/deep-check`, `/social-thread`, or the historic-* workflows.

### Skill 1 — `/audit-integrity`
**Why #1:** the two highest-frequency failure classes (T1 matcher collisions ~8×/3 weeks; T2/T6 silent staleness) are today caught only by luck — the 7-week-old `reviewed=0` contradictions and the stale-party bug (Vergina) both surfaced from one ad-hoc consistency audit. A scheduled sweep converts "noticed by chance" into "reported every run."

```
---
name: audit-integrity
description: Read-only DB integrity sweep — matcher-collision candidates, silent-merge suspects, stale party/coalition, orphaned refs, aging reviewed=0 rows, x_handle divergence, missing brief-image variants, diacritic-stripped text. Emits a triage table + BACKLOG-ready blocks; fixes only with operator approval + paired rollback.
argument-hint: "[--fix] [matcher|stale|orphans|briefs|all]"
---
## Why this shape
The worst failures here return success (empty `failures`, stale denormalized fields, junctions
nobody re-reads). None raise. A periodic read-only sweep surfaces them; by standing rule
matcher/party fixes are operator-review, so the skill PROPOSES, never auto-applies.
## Procedure (read-only unless --fix)
1. Matcher: junctions where doc text lacks the full name / shows a different first name;
   generated name_forms ≤4 chars; candidate negative_patterns per finding.
2. Silent merges (T2): extractions that stored fewer claims than distinct same-topic positions.
3. Staleness (T6): claims with party-exit/switch language vs unchanged tracked_politicians.party;
   claims.topic != votes.topic for saeima_vote rows.
4. Hygiene: contradictions with missing claim refs; claims on inactive politicians;
   reviewed=0 rows older than N days; x_handle vs social_accounts.handle divergence;
   brief images missing -hero/-og/-card/-thumb variants; truncated-stub docs (word_count).
5. Output: one triage table + a paste-ready BACKLOG.md block per finding class
   (matches the existing operator-review workflow); log to logs(action='integrity_audit').
## Guardrails
- Default read-only; --fix applies ONLY operator-approved items, each with paired
  data/rollback_*.sql, in one transaction.
- Never auto-add negative_patterns / change party — propose only (standing rule).
- Cadence: weekly-routine step; also on-demand before big publishes.
```

### Skill 2 — `/saeima-ingest`
**Why #2:** Saeima is the only *structural* claim source (rhetoric-vs-action depends on it); ingest is the most manual weekly task (3–5h in session weeks); its failure mode is silent and expensive (70 votes lost 06-04; two more gaps found 07-05). The `audit` mode directly executes the open BACKLOG [FIX] "Agenda↔DB pilnīguma audits visām 2022–2026 sesijām".

```
---
name: saeima-ingest
description: Ingest one Saeima session — both vote-URL patterns unioned, atomic per-vote summary-then-store, completeness gate (deputies matched + summaries present + (vote_date, vote_time) parity vs agenda). `audit <range>` mode diffs agenda↔DB across past sessions and lists gaps for re-ingest.
argument-hint: "<session date> | audit <date range>"
---
## Why this shape
titania re-archives vote pages under new UNIDs (~1 week post-session) → URL-idempotence goes
blind (07-05 gaps). Old sessions use static ?OpenDocument links; new DK sessions embed IDs in
JS addVotesLink() — one pattern alone silently lost 70 votes (06-04). "Optional" summary steps
get skipped under batch load (05-16) → NULL summaries → generic stances.
## Procedure — ingest mode
1. Resolve session from the calendar; capture agenda snapshot.
2. Extract BOTH vote-URL patterns (union; 3 extraction patterns per _extract_vote_urls_from_agenda).
3. Per vote, ATOMICALLY: capture → write summary → process_vote_snapshot(summary=, document_url=,
   document_nr=). No batching, no .5 steps (T11).
4. Store → generate_claims_from_votes → append_bill_stage (inv #12).
5. Gate (hard-fail on any): ~100 deputies matched; every bill-type vote has a summary;
   (vote_date, vote_time) set matches the agenda union.
## Procedure — audit mode
For each calendar session in range: agenda URL union → compare with DB by (vote_date,
vote_time) → report missing votes per session → operator picks which to re-ingest (ingest mode).
## Guardrails
- 0 votes at a session with agenda items → STOP + report (T8). Never record an empty day.
- Unmatched deputies → STOP; fix name_forms first.
- Dedup by (vote_date, vote_time), never URL.
```

### Skill 3 — `/seed-entity`
**Why #3:** every mis-seed *causes* the downstream recurring traps (T1 collisions, T6 staleness, x_handle divergence), and election season is adding parties now — Suverēnā vara + Jaunlatvieši (party row + carrier) are an open BACKLOG item today.

```
---
name: seed-entity
description: Onboard a politician / party / organization / CVK-list carrier — diacritic+ASCII name_forms with ≤4-char collision flags, independent party verification, x_handle↔social_accounts consistency, coalition on parties.coalition_status, INSERTs + paired rollback for operator approval.
argument-hint: "<name> [party|org|carrier] [role] [x_handle]"
---
## Why this shape
Matcher is substring-based without diacritic folding → BOTH variants or the politician never
links; audit script catches missing ASCII but NOT wrong stems (Šnore/Šņore) — stems are
eyeball-verified; ≤4-char generated forms are substring bombs (T1); news joint-list wording
mislabels party (LPV/"Kopā Latvijai" trap); x_handle (render) and social_accounts.handle
(fetch) silently diverge.
## Procedure
1. Duplicate/typo check vs existing rows (name + name_forms overlap).
2. Generate name_forms: diacritic + ASCII + Latvian inflections; flag every ≤4-char generated
   form; present stems for eyeball check.
3. Verify party against an independent source (Wikipedia LV / ir.lv / official site), never
   joint-list news wording. relationship_type per seeding.md ('organization' slot for interest
   groups; journalist guard for common-noun surnames).
4. CVK-list case: seed parties row (+ coalition_status) AND carrier politician together;
   program flow then follows Data Contract #4a.
5. social_accounts row (feed_type, active) + x_handle consistency check.
6. Emit INSERTs + paired data/rollback_*.sql; operator approves BEFORE commit.
## Guardrails
- Operator approves final party value and any ≤4-char form; no auto-commit.
- Both name_form variant sets present or the seed is INCOMPLETE.
- Coalition lives on parties.coalition_status, never per-politician (inv #10).
```

**Runners-up (rejected for top 3):** deploy verification (check.sh + quality-reviewer + curated re-freeze already cover most; low frequency) · historic-backfill coordinator (workflows exist) · X slot-health manager (dashboard surfaces it; low hours) · brief-skeleton salience fix (that one is a *code* fix in `src/briefs.py`, not a skill — see BACKLOG).

---

## 4. v1 → v2 changelog

1. **Anonymity self-leak fixed.** v1 referenced a private memory slug whose filename embeds identity-linking text, inside this public-syncing directory. Scrubbed; replaced with the neutral-phrasing rule + the "assume public unless excluded" convention (both now in CLAUDE.md).
2. **"Put the rule in CLAUDE.md" corrected to "put the *public-safe phrasing* in CLAUDE.md".** v1 didn't check that CLAUDE.md ships to the public mirror; v2 § 0 documents the exclusion set.
3. **Numbering preservation added** (§ 0b): v1's "rewrite" framing would have invited renumbering that breaks CHANGELOG/memory/test cross-references; the applied rewrite keeps all section names/numbers.
4. **Rewrite APPLIED, not proposed** — CLAUDE.md now carries Standing Decisions, Working Conventions, Traps T1–T13, Quality Bars, When Uncertain. This doc's v1 inline drafts of those sections are superseded by the file itself; removed here to avoid drift (single source of truth).
5. **Skill briefs sharpened:** `/audit-integrity` gains BACKLOG-ready output blocks, x_handle-divergence + brief-image-variant + truncated-stub checks, weekly cadence; `/saeima-ingest` gains the `audit <range>` mode that executes the open BACKLOG completeness-audit FIX; `/seed-entity` gains the CVK party+carrier case (matches the open Suverēnā vara + Jaunlatvieši item) and the wrong-stem eyeball check.
6. **Quality bars enriched** (in CLAUDE.md): historic `stated_at`=publication-date rule; REGEN-baseline-treadmill vs real-regression distinction; brief-image live HTTP-200 check; weekly stale-note over-correction check.
