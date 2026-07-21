---
name: audit-integrity
description: Read-only DB integrity sweep — matcher-collision risks (≤4-char forms), x_handle↔social_accounts divergence, orphaned contradiction refs, aging unreviewed/unconfirmed rows, stale-party language, same-day duplicate claims, missing brief-image variants, truncated stubs. Emits a triage table + BACKLOG-ready blocks; fixes only with operator approval + paired rollback.
argument-hint: "[matcher|stale|orphans|briefs|all] [--fix]"
---

# Audit integrity — datu integritātes pārbaude

Run the read-only sweep over the scope in `$ARGUMENTS` (default `all`). Report findings; apply NOTHING without operator approval.

## Why this shape

The worst failures here return success: silent idempotency merges leave `failures` empty, denormalized fields go stale without any signal, and false junctions sit until someone happens to reread the doc. Historically these were caught only by ad-hoc consistency audits (that is how the Vergina stale-party bug and the aging `reviewed=0` contradictions surfaced). A scheduled sweep converts "noticed by luck" into "reported every run". Core queries validated against the live DB 2026-07-07 — the first run already surfaced 10 active politicians with ≤4-char forms (incl. the known Kols case) and one live x_handle divergence (id=62).

**Honest scope limit:** the T2 silent idempotency merge is invisible post-hoc by definition (the second claim never lands in the DB) — it can only be caught at extraction time via stored-count == intended-count (CLAUDE.md T2). This audit covers the closest detectable proxy (same-day cross-source duplicates) instead.

## Checks

1. **Matcher collision risk (T1).** For every active politician, list stored `name_forms` ≤4 chars AND generated forms ≤4 chars (apply `src/matcher.py::_latvian_surname_inflections` to each surname form). For each, sample-grep recent `documents.content` to show what it currently collides with. Output candidate `negative_patterns` — proposals only.
2. **x_handle divergence.** `tracked_politicians.x_handle` vs active `social_accounts.handle` (`platform='twitter'`), case-insensitive mismatch.
3. **Orphans.** Contradictions whose `claim_old_id`/`claim_new_id` no longer resolve; `position` claims on `relationship_type='inactive'` politicians (informational — audit trail is expected, flag counts only).
4. **Aging review queues.** `contradictions` with `reviewed=0` older than 14 days; `confirmed=0` survivors (deep-check output) older than 30 days; NEEDS_REVIEW claims older than 14 days.
5. **Stale party language (T6).** Claims from the last 30 days in topic `Koalīcija un partijas` whose stance/reasoning contains exit/switch language (`izstāj%`, `pamet%`, `pāriet%`, `jaunu partiju%`) where `tracked_politicians.party` is unchanged since before `stated_at` — cross-check candidates for manual party UPDATE.
6. **Same-day duplicates.** Same `(opponent_id, topic, DATE(stated_at))` with different `source_url` and near-identical stance (the Kulbergs X+LETA class) — trim candidates.
7. **Brief image variants.** PNGs under `output/atmina/images/briefs/` without a `-hero.webp` sibling (render only copies variants; the self-heal does NOT cover briefs).
8. **Truncated stubs.** Unreviewed `documents` with `word_count < 80` (pmo.ee paywall class) — re-ingest candidates, NOT extraction targets.

## Output

- One triage table (check · count · top examples with ids).
- For each non-empty class: a paste-ready BACKLOG.md block in the house `[OPEN]/[FIX] + apraksts + operatora review` style, so findings survive the session.
- Log the run: `db.log_action(action='integrity_audit', ...)`.

## Guardrails

- **Default read-only.** `--fix` applies ONLY items the operator approved one-by-one, each with a paired `data/rollback_*.sql`, in one transaction.
- Never auto-add `negative_patterns`, never change `party` — propose, don't apply (standing rule; CLAUDE.md Working Conventions).
- Findings in LV where they become stored text; grammar gate applies.
- Cadence: weekly-routine step + on demand before big publishes. Full sweep is cheap (read-only, <1 min).
