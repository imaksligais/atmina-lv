---
name: dienas-rutina
description: Drive the atmina.lv daily routine — status check, afternoon analysis fan-out, contradiction + devils-advocate pass, brief (human-gated), narrow render + --no-delete deploy. Encodes the timing + publish-pause + LV-style guardrails.
argument-hint: "[YYYY-MM-DD] (defaults to today)"
---

# Dienas rutīna — atmina.lv

Orchestrate today's routine. **Canonical state first**, then editorial steps. Respect the guardrails below — they encode prior incidents, not preferences.

## 0. Status

```bash
python -c "from src.routine import print_routine; print_routine()"
```

Read `wiki/index.md` for backlog/folder contract. The 10 steps live in `src/routine.py`; the agents in `.claude/agents/*.md`.

## Timing guardrails (HARD)

- **Ingest runs all day.** A morning "0/N analizēti" is EXPECTED, not a backlog warning (`project_daily_routine_timing`).
- **Analysis + brief are afternoon-only (≥15:00 LV).** Do NOT dispatch `@brief-writer` or run extraction before ~15:00 — `feedback_no_morning_brief` (2026-05-15 incident: brief dispatched before noon, rejected).

## Steps (afternoon)

1. **Ingest** — confirm new documents landed (step shows count). Don't force it in the morning.
2. **Pozīciju analīze** — fan out `@claim-extractor` in **parallel sub-agents, one per politician**. Sub-agent contexts are clean, so they bypass the ~8-politician main-context diacritic-drift limit — scale wide (`feedback_subagents_bypass_diacritic_limit`). Circuit breakers: cap batch size (≈12 docs / 12 politicians) + the `NEEDS_REVIEW` gate to avoid indirect-reference saves (`project_claim_extractor_batch_drift`, `feedback_claim_extractor_indirect`). Every claim needs a `source_url` or it's silently dropped.
3. **Pretrunu pārbaude** — for each new claim, `search_similar_claims` with a directional `claim_type_filter`; store via `store_contradiction()` (defaults `confirmed=0` — unpublished until you manually UPDATE). Also check rhetoric-vs-action. See `/deep-check` for the deeper fan-out.
4. **Devils-advocate** — run `@devils-advocate` on every new contradiction before it can publish.
5. **Spriedzes** — register political tensions if ≥2 politicians have new positions.
6. **Konteksta piezīmes (tendences)** — append-only; check existing notes first, never overwrite (destroys the evolution signal).
7. **Dienas pārskats** — `@brief-writer`. Same-day refresh = **UPDATE the existing `daily_brief` row, never a full rewrite** (`feedback_daily_brief_update_not_rewrite`); check `context_notes` first.
8. **Featured image** — `@graphics-designer` once the brief is approved.
9. **Wiki sync** — `wiki_sync()`; never hand-edit generated wiki pages.

## LV-style guardrails (every claim / brief / synthesis / tweet)

Avoid anglicisms and check grammar + stylistics before store/publish (`feedback_check_grammar_stylistics`): never "ataka" (→ uzbrukums), "polemika" (→ diskusija/domstarpības), "melīšana" (→ melošana). Diacritics intact.

## Publish gate (HARD — do NOT auto-publish)

Before any deploy of a brief: **manual proofread** the full text (verb forms, sg/pl, truncations, capitalization — `lint_lv_style` 0-issues is NOT sufficient: `feedback_brief_manual_proofread`), confirm the featured image, then **AskUserQuestion** for go-ahead (`feedback_brief_publish_pause`). Never auto-publish.

## Render + deploy

- Identify the changed domains and render narrowly: `python -m src.render --only=DOMAIN1,DOMAIN2` (full path only for release/baseline regen — `feedback_render_narrow_scope`).
- Deploy with **`bash scripts/deploy.sh --no-delete`** (standing mode — the local tree may be a partial build; `--delete` would wipe curated/server-only pages). Dry-run first: `deploy.sh --dry-run --no-delete`.
