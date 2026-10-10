---
name: saeima-ingest
description: Guarded Saeima session ingest via @saeima-tracker with a hard completeness gate, plus an `audit <range>` mode that diffs agenda↔DB by (vote_date, vote_time) across past sessions. Encodes the three-pattern union, 0-votes-STOP, and atomic-summary guardrails.
argument-hint: "<session date> | audit <from-date> <to-date>"
---

# Saeima ingest — sesijas ielāde ar pilnīguma vārtiem

Resolve `$ARGUMENTS`: a single date → **ingest mode**; `audit <from> <to>` → **audit mode**.

## Why this shape

Saeima is the only structural claims source — rhetoric-vs-action contradictions depend on it — and its failure mode is silent: titania re-archives vote pages under new UNIDs ~a week after the session, so URL-idempotence goes blind (2026-07-05 found 5 missing votes in the 04-01 session incl. the Sprūda no-confidence vote, and 74 in 05-14). Older sessions expose static `?OpenDocument` links; newer DK sessions embed vote IDs only in JS `addVotesLink()`; and from 2026-06-11 the agenda renders `./Voting?ReadForm&parentID={GUID}` links that neither earlier pattern matches — checking one pattern alone silently lost 70 votes (2026-06-04). And "optional-looking" summary steps get skipped under batch load (2026-05-16 regress → NULL summaries → 1943 generic stances). This skill wraps the canonical agent with gates that make each of those failures loud.

## Procedure — ingest mode

1. **Dispatch `@saeima-tracker`** for the session date. The scraping procedure is canonical in `.claude/agents/saeima-tracker.md` — do NOT reimplement or paraphrase its steps; the agent already encodes the three-pattern union (Step 2.B) and atomic capture → summary → `process_vote_snapshot(summary=, document_url=, document_nr=)` (Step 3, keyword-only kwargs — the atomic path that replaced the NULL→UPDATE regress).
2. **Completeness gate** (run after the agent returns; ANY failure = the session is NOT ingested, regardless of what the agent reported):
   - a. **Summaries — with a denominator:** for EVERY `vote_date` ingested in this run (a continuation sitting means several dates), call the same helper as `.claude/agents/saeima-tracker.md` Step 5 — it matches any convocation (`/Lp14`, `/Lm14`, `/Lp15` …), so the gate survives the 15th Saeima:
     ```python
     from src.db import get_db
     from src.saeima.votes import bill_votes_missing_summary
     db = get_db()
     checked, missing = bill_votes_missing_summary(db, SESSION_DATE)  # the sitting's vote_date, not today
     db.close()
     print(f"likumprojektu balsojumi: pārbaudīti {checked}, bez summary {len(missing)}")
     ```
     STOP on `checked == 0` (either the sitting had no bill votes — check the agenda — or the ingest never happened, T8; a 0 denominator is never a clean pass) and STOP on any `missing` (back to the agent's Step 3.B for each).
   - a2. **Collective-petition polarity:** for the same dates, `from src.saeima.votes import petition_votes_polarity; checked, problems = petition_votes_polarity(db, SESSION_DATE)` — print `checked` (0 is normal: no petition that day) and STOP on any problem. A rejecting draft («noraidīt» / «atstāt bez virzības») whose summary describes the petition's demand inverts every stance; the agent reads the verb with `petition_decision_verb()` (Step 3.B) and passes `petition_decision=` to `process_vote_snapshot()`.
   - b. **Deputy match rate:** count `saeima_individual_votes` rows with `politician_id IS NULL` for the session → must be ~0; a cluster = missing `name_forms`, fix first (consider `/seed-entity` for genuinely new deputies).
   - c. **Agenda parity — per DATE, across ALL sitting UUIDs:** one date can carry several sittings (2026-08-20 two, 2026-07-23 three), and a continued sitting (calendar label `A / B`, e.g. `23 / 3(As)` = the 07-23 extraordinary sitting continued on 09-03) keeps the BASE sitting's UUID — it has no row of its own; the manifest records the later date in the base row's `continued_on`. The parity audit selects such a sitting by ANY of its dates (`--dates 2026-09-03` picks the 07-23 row) and prints `(turpinājums: …)` on the base row, so read the missing votes against the continuation date. Enumerate every `DK?ReadForm&nr={uuid}` the calendar lists for the date (five label forms: bez sufiksa, `(J)`, `(A)`, `(As)`, `(S)` — `scripts/_p3_extract_sessions_2026-05-26.py`), extract the vote-URL union from each agenda snapshot (3 patterns — reuse the logic of `scripts/p3_backfill_year_urllib.py::_extract_vote_urls_from_agenda`) and compare that union against DB by `(vote_date, vote_time)` — every agenda vote must have a DB row. Tool: `.venv/Scripts/python.exe scripts/audit_saeima_agenda_parity.py --year YYYY --dates YYYY-MM-DD`. Its manifest must be FRESH: a stale `data/saeima_backfill_sessions.json` reports "trūkst 0" over sittings it never saw (that is how 08-20 stayed hidden for 13 days), so the tool STOPs on manifest age — regenerate the manifest, then re-run. Regenerate with an EXPLICIT snapshot: `.venv/Scripts/python.exe scripts/_p3_extract_sessions_2026-05-26.py --snapshot .playwright-mcp/<calendar snapshot>.yml` — without `--snapshot` it takes the newest `page-*.yml`, which after any other Playwright step is not the calendar. Check its `Turpinājumi: piesaistīti N, neparsēti M` line and exit code: an unparsed continuation (exit 1) is a sitting the audit will never see.
3. **Report** the gate table (votes stored / claims generated / deputies matched / summaries present / parity) and stop. Render + deploy stay with the operator (`--only` narrow render per `wiki/operations/commands.md`).

## Procedure — audit mode

For each calendar session in `<from>..<to>`: fetch the agenda, extract the vote-URL union (same 3 patterns), fetch each vote's `(vote_date, vote_time)` header, and diff against `saeima_votes` **by `(vote_date, vote_time)` — never by URL** (re-archived UNIDs make URL comparison lie). Output one row per session: agenda votes / DB votes / missing list. The operator picks which sessions to re-ingest (ingest mode per session). This mode executes the open BACKLOG [FIX] "Agenda↔DB pilnīguma audits visām 2022–2026 sesijām" — run it in date-range waves, not all four years at once.

## Guardrails

- **0 votes at a session that had agenda items = STOP + report** — a scraping-pattern error, never an empty day (this exact miss cost 70 votes).
- Unmatched deputies = STOP; `name_forms` first, then re-run.
- `saeima_votes.bill_id` / `saeima_bills.current_stage` change only via `append_bill_stage()` (inv #12) — the audit never UPDATEs them.
- Summaries are substantive 1–2 sentence LV (grammar gate); procedural votes without a bill reference may skip per the agent prompt.
- Audit mode is read-only; every ingest is idempotent on re-run (dedup inside `process_vote_snapshot`).
