---
name: audit-integrity
description: Read-only DB integrity sweep — runs scripts/audit_integrity.py (20 checks, numbers unchanged) covering matcher-collision risks, x_handle↔social_accounts divergence, orphaned contradiction refs, aging review queues (aged from the marker), stale-party language, party↔faction record + ministers-without-votes denominator, same-day duplicates, brief-image variants, truncated stubs, unresolvable provenance, saeima_vote per-vote parity, junction role inversion, stale claim vectors, non-canonical brief/position topics. Emits a triage table + BACKLOG-ready blocks; fixes only with operator approval + paired rollback.
argument-hint: "[matcher|stale|orphans|briefs|all] [--fix]"
---

# Audit integrity — datu integritātes pārbaude

Run the read-only sweep over the scope in `$ARGUMENTS` (default `all`). Report findings; apply NOTHING without operator approval.

## Why this exists

The worst failures here return success: silent idempotency merges leave `failures` empty, denormalized fields go stale without a signal, false junctions sit until someone rereads the doc. A scheduled sweep turns "noticed by luck" into "reported every run". Every check is code in `scripts/audit_integrity.py` with hermetic tests (`tests/test_audit_integrity.py`) that prove it can fail — do not re-type queries from memory. Baselines, incident history and the transfer notes: `.claude/references/audit-integrity/bazes-linijas.md` — read the section for any check that flags before triaging it.

**Honest scope limit:** the T2 silent idempotency merge is invisible post-hoc (the second claim never lands) — only stored-count == intended-count at extraction catches it. Check 6 is the nearest detectable proxy.

## Run

```bash
PYTHONUTF8=1 .venv/Scripts/python.exe scripts/audit_integrity.py --scope all        # ~1.5 min
PYTHONUTF8=1 .venv/Scripts/python.exe scripts/audit_integrity.py --only 2,9b,14 --rows
PYTHONUTF8=1 .venv/Scripts/python.exe scripts/audit_integrity.py --json            # for the log entry
```

`$ARGUMENTS` maps to `--scope` (default `all`). Scopes: `matcher` 1 1b 2 12 15 · `stale` 4 5 8 9 9b 13 17 · `orphans` 3 6 10 11 14 18 · `briefs` 7 16. Exit **0** clean · **1** findings · **2** broken denominator (`checked=0`) or unverified method (check 13's control failed) — a 2 is never a clean run. Only gate checks set the exit code; `[info]` checks (1, 1b, 6, 8, 12, 15) print their table and denominator but never fail the run. `flagged` is the raw count; `new` excludes the documented `ACCEPTED_*` ids in the script (changed only by the operator).

## Triage — how to read each class

- **1 / 1b (T1, info).** ≤4-char forms are namesake risks since B2 (word-boundary matching), not substring bombs — say which class. 1b: a tracked politician repeatedly vetoed next to the same capitalised token = coverage bug (missing `_VETO_STOP_WORDS` entry or name-token declension, "Pēcāk Ratnieks"); a namesake vetoed = guard working; a NEW recurring namesake first name = full-name-twin warning (Bērziņš). Proposals only.
- **2.** Always report `saucējs N | NULL klase X | vērtību nesakritība Y`. `0 | 0 | 0` means the join broke. A NULL row is a missing X link on a live profile page unless the politician is `inactive`.
- **3.** Any unresolved ref outside `ACCEPTED_3` is a defect. Position claims on `inactive` politicians are an audit trail — count only.
- **4.** Gate = `src.db.open_review_queue()` form (`age_days > REVIEW_QUEUE_AGE_DAYS`, aged from the marker). Report the whole age distribution, not only the breach. `reviewed=1 confirmed=0` is a documented rejection, not queue debt. Trigger sanity must be 0. Resolve rows per `wiki/operations/weekly-routine.md` (replace the marker with `Izvērtēts YYYY-MM-DD:`), never by writing `review_status`.
- **5 (T6).** Each row is a candidate — verify against a fresh source before any `party` UPDATE (+ rollback). There is no party history, so a switch already applied keeps flagging until it leaves the 30-day window.
- **6 (info).** Upper bound without a stance-similarity filter; read the stances, trim only true same-content pairs (Kulbergs X+LETA class), operator decides.
- **7.** Read the flag count TOGETHER with the `approved` bucket line: a row moving to `approved=2` leaves the checked set — a bucket shift is the signal, a bare green is not proof of repair.
- **8 (info).** Re-ingest candidates (paywall/truncated), NOT extraction targets; read the `web` bucket — tweets are short by nature.
- **9 (T6).** Triage by coverage inside the most recent labelled sitting window (the `logs` column), not lifetime rows: dense (≳80 %) and different from `party` → real switch, field stale → propose UPDATE + paired rollback; thin/isolated (≲30 %) → scraper artifact; no label + `role` "ārpus frakcijām" → expected. `party` ≠ `faction` (Kiršteins with `faction=NULL` is legitimate). A new label variant → extend `normalize_faction()`, never special-case the query.
- **9b.** Not a defect: a minister automated verification cannot reach. Check party by hand (CVK, ministry page, fresh source). `role` is free text; the `ministr` substring over-includes (pid 64).
- **10.** A/B/C are defects, not judgement calls: check whether a stored claim backs the row, then repoint the URL at the real document or delete the row (paired rollback). D is a same-session tripwire only.
- **11 / 14.** Expected 0. 11 compares keys and misses doubled rows with distinct topics — 14 sees them the same day. In 14 read the ratio: exactly 2.0 = loaded twice; <1.0 = partial write (`store_vote()` commits before claims); 0 = generation never ran. Run 14 before and after every bulk ingest.
- **12 / 15 (info).** One measurement. Read the rate, not the count; the tweet lane is dominated by satire false positives. Proposals only — no role changes.
- **13.** Any stale row is a hand edit that skipped escalation rule 8's re-embed (never re-embed `saeima_vote`). Exit 2 = the control set failed — the whole run is a method artifact.
- **16.** Fix with `src.briefs.daily_brief_topic()` + `brief_subject_date()`, never a hand-written prefix.
- **17.** An id outside `ACCEPTED_17` = a fresh re-scrape ate another quote: triage per quote (repair against the new revision, or accept and add to the list with the date). Never batch-fix; never "correct" a quote's spelling.
- **18.** `checked` drifts up daily; `flagged=0` and `distinct ≤ 33` must hold.

## Output

- One triage table — the script's lines: `N · nosaukums · checked=… flagged=… (sagaidāms …)` + example ids. **Every row carries its denominator**; a green without one is worse than no check (check 7 once scanned a directory holding one file).
- For each non-empty class: a paste-ready BACKLOG.md block in the house `[OPEN]/[FIX] + apraksts + operatora review` style.
- Log the run: `db.log_action(action='integrity_audit', details=<the --json payload summary>)` — the script itself never writes.

## Guardrails

- **Default read-only** (the script opens the DB `mode=ro`). `--fix` applies ONLY items the operator approved one-by-one, each with a paired `data/rollback_*.sql`, in one transaction.
- Never auto-add `negative_patterns`, never change `party` — propose, don't apply.
- Findings in LV where they become stored text; grammar gate applies.
- Cadence: weekly-routine step + on demand before big publishes.
