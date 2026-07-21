---
name: deep-check
description: Deep contradiction hunt for a set of politicians — parallel @contradiction-hunter fan-out at 0.80, filtered through @devils-advocate. Stores survivors unpublished (confirmed=0) for operator review. Encodes the cherry-pick + false-positive guardrails.
argument-hint: "<politician names | 'recent' | topic scope>"
---

# Deep check — pretrunu padziļināta pārbaude

Run a high-recall, high-precision contradiction pass over the requested scope (`$ARGUMENTS`; default = politicians with claims in the last ~7 days).

## Why this shape

Embeddings cluster by **topic**, not by contradiction — so similarity threshold tuning has limits: **0.70 has no practical advantage over 0.80** (`project_deep_contradiction_check`). The signal comes from **fan-out + adversarial filtering**, not a lower threshold. Expect a low yield: roughly **1 publishable contradiction per ~2700 raw pairs**. Don't manufacture findings to hit a count.

## Procedure

1. **Scope** — resolve `$ARGUMENTS` to a politician set. For each, pull the full claim history (`search_similar_claims` directional, `claim_type_filter` per direction) — **for rhetoric-vs-rhetoric only**.
   - **Rhetoric-vs-action is STRUCTURAL, not embedding-based.** `claim_type='saeima_vote'` rows are NOT in `claim_vectors` (517k deterministic templates, never vectorized), so `search_similar_claims(claim_type_filter=['saeima_vote'])` silently returns nothing — similarity is 0.000 against every position. Do NOT treat an empty result as "no vote mismatches". The vote side comes from `@contradiction-hunter`'s structured SQL pass (keyword-matched `saeima_votes` + `saeima_individual_votes` joins + mandatory faction check) — make sure each hunter sub-agent actually runs that pass, it is the only path to rhetoric-vs-`saeima_vote` candidates.
   - **`stale-pol`** scope — active politicians with ≥5 position claims whose contradiction check has never found anything OR is >60 days stale: `from src.coverage import stale_pol_politicians; stale_pol_politicians()` (ņem db_path STRING vai None → noklusētā DB; NEpadod sqlite3.Connection). Proxy for "last checked" = `MAX(contradictions.detected_at)` per politician (NULL = never found one), so it **overcounts** politicians checked-but-clean (yield is ~1/2700, so most never store a contradiction). This is the periodic coverage-hygiene target, parallel to the `recent` daily scope. It is **broad** (~79 as of 2026-06-08) — run in waves of 4-5 (highest position-claim count first), never all at once.
2. **Fan out `@contradiction-hunter`** — run it as **~4 parallel sub-agents** across the politician set (clean contexts, wide coverage). Each returns structured contradiction *candidates* at threshold **0.80**. The Hunter is prone to **cherry-picking** historic reversals out of context — treat its output as candidates, never as verified.
3. **Filter through `@devils-advocate`** — every candidate goes to `@devils-advocate`, which attacks it to strip false positives: coalition-discipline votes, procedural/whip context, journalist paraphrase mistaken for a stance, and combinable (non-contradictory) positions. Only survivors proceed.
4. **Store survivors** — `store_contradiction()` (severity ∈ `direct_contradiction` / `reversal` / `minor_shift`; `speaker_scope` defaults `first_party`). **Defaults to `confirmed=0` — UNPUBLISHED.** The operator manually `UPDATE confirmed=1` per contradiction to publish; do not auto-confirm.

## Guardrails

- LV-style on every stored summary (no anglicisms; check grammar — `feedback_check_grammar_stylistics`).
- Attribution: if a synthesis later names "X un Y kritizē Z", each named politician needs ≥1 backing claim about Z — bucket co-occurrence is NOT proof (`feedback_synthesis_attribution`).
- Render the contradictions domain narrowly when publishing: `python -m src.render --only=pretrunas` then `deploy.sh --no-delete`.
