---
name: saeima-ingest
description: Guarded Saeima session ingest via @saeima-tracker with a hard completeness gate, plus an `audit <range>` mode that diffs agenda↔DB by (vote_date, vote_time) across past sessions. Encodes the two-pattern union, 0-votes-STOP, and atomic-summary guardrails.
argument-hint: "<session date> | audit <from-date> <to-date>"
---

# Saeima ingest — sesijas ielāde ar pilnīguma vārtiem

Resolve `$ARGUMENTS`: a single date → **ingest mode**; `audit <from> <to>` → **audit mode**.

## Why this shape

Saeima is the only structural claims source — rhetoric-vs-action contradictions depend on it — and its failure mode is silent: titania re-archives vote pages under new UNIDs ~a week after the session, so URL-idempotence goes blind (2026-07-05 found 5 missing votes in the 04-01 session incl. the Sprūda no-confidence vote, and 74 in 05-14). Older sessions expose static `?OpenDocument` links; newer DK sessions embed vote IDs only in JS `addVotesLink()` — checking one pattern alone silently lost 70 votes (2026-06-04). And "optional-looking" summary steps get skipped under batch load (2026-05-16 regress → NULL summaries → 1943 generic stances). This skill wraps the canonical agent with gates that make each of those failures loud.

## Procedure — ingest mode

1. **Dispatch `@saeima-tracker`** for the session date. The scraping procedure is canonical in `.claude/agents/saeima-tracker.md` — do NOT reimplement or paraphrase its steps; the agent already encodes the two-pattern union (Step 2.B) and atomic capture → summary → `process_vote_snapshot(summary=, document_url=, document_nr=)` (Step 3, keyword-only kwargs — the atomic path that replaced the NULL→UPDATE regress).
2. **Completeness gate** (run after the agent returns; ANY failure = the session is NOT ingested, regardless of what the agent reported):
   - a. **Summaries:** `SELECT id, motif FROM saeima_votes WHERE vote_date = :session AND summary IS NULL AND (motif LIKE '%/Lp14)%' OR motif LIKE '%/Lm14)%')` → must be empty.
   - b. **Deputy match rate:** count `saeima_individual_votes` rows with `politician_id IS NULL` for the session → must be ~0; a cluster = missing `name_forms`, fix first (consider `/seed-entity` for genuinely new deputies).
   - c. **Agenda parity:** extract the vote-URL union from the agenda snapshot (3 patterns — reuse the logic of `scripts/p3_backfill_year_urllib.py::_extract_vote_urls_from_agenda`) and compare against DB by `(vote_date, vote_time)` — every agenda vote must have a DB row.
3. **Report** the gate table (votes stored / claims generated / deputies matched / summaries present / parity) and stop. Render + deploy stay with the operator (`--only` narrow render per `wiki/operations/commands.md`).

## Procedure — audit mode

For each calendar session in `<from>..<to>`: fetch the agenda, extract the vote-URL union (same 3 patterns), fetch each vote's `(vote_date, vote_time)` header, and diff against `saeima_votes` **by `(vote_date, vote_time)` — never by URL** (re-archived UNIDs make URL comparison lie). Output one row per session: agenda votes / DB votes / missing list. The operator picks which sessions to re-ingest (ingest mode per session). This mode executes the open BACKLOG [FIX] "Agenda↔DB pilnīguma audits visām 2022–2026 sesijām" — run it in date-range waves, not all four years at once.

## Guardrails

- **0 votes at a session that had agenda items = STOP + report** — a scraping-pattern error, never an empty day (this exact miss cost 70 votes).
- Unmatched deputies = STOP; `name_forms` first, then re-run.
- `saeima_votes.bill_id` / `saeima_bills.current_stage` change only via `append_bill_stage()` (inv #12) — the audit never UPDATEs them.
- Summaries are substantive 1–2 sentence LV (grammar gate); procedural votes without a bill reference may skip per the agent prompt.
- Audit mode is read-only; every ingest is idempotent on re-run (dedup inside `process_vote_snapshot`).
