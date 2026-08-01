---
name: deep-check
description: Deep contradiction hunt for a set of politicians — parallel @contradiction-hunter fan-out at 0.80, filtered through @devils-advocate. Stores survivors unpublished (confirmed=0) for operator review. Encodes the cherry-pick + false-positive guardrails.
argument-hint: "<politician names | 'recent' | topic scope>"
---

# Deep check — pretrunu padziļināta pārbaude

> **Pass/fail kritēriji pretrunām — [`wiki/operations/quality-bars.md`](../../wiki/operations/quality-bars.md). Izlasi PIRMS glabāšanas/publicēšanas, ne pēc.** CLAUDE.md § Quality Bars sauc šo failu par kanonisko nesēju; līdz 2026-08-09 uz to saistīja 1 no 17 nesējiem.

Run a high-recall, high-precision contradiction pass over the requested scope (`$ARGUMENTS`; default = politicians with claims in the last ~7 days).

## Why this shape

Embeddings cluster by **topic**, not by contradiction — so similarity threshold tuning has limits: **0.70 has no practical advantage over 0.80** (izmērīts 2026-05 deep-check pilotā). The signal comes from **fan-out + adversarial filtering**, not a lower threshold. Expect a low yield: roughly **1 publishable contradiction per ~2700 raw pairs**. Don't manufacture findings to hit a count.

**Measured 2026-07-25 — the threshold is inert, and the fan-out is what works.** Full pairwise matrices: 99.0–99.4 % of a politician's pairs clear 0.80 (Braže 99.4, Rinkēvičs 99.0, Kulbergs 99.1; corpus minimum 0.758). The cross-politician baseline is identical — two unrelated politicians' claims average 0.853 against each other, versus 0.845–0.857 within one politician. An absolute cosine cutoff therefore separates nothing at any value; raising it to ≥0.92 surfaces same-day restatements, not reversals. Keep 0.80 in the hunter call if you like, but **read it as a formality, not a filter**, and never let a report present "candidates at threshold 0.80" as if the number did work. The useful part is the relative kNN ranking within the politician's own claims plus chronological reading per topic. See `.claude/agents/contradiction-hunter.md` § threshold.

## Procedure

1. **Scope** — resolve `$ARGUMENTS` to a politician set. For each, pull the full claim history (`search_similar_claims` directional, `claim_type_filter` per direction) — **for rhetoric-vs-rhetoric only**.
   - **Rhetoric-vs-action is STRUCTURAL, not embedding-based.** Do NOT treat an empty kNN result as "no vote mismatches" — an empty result is evidence of nothing here. The vote side comes from `@contradiction-hunter`'s structured SQL pass (keyword-matched `saeima_votes` + `saeima_individual_votes` joins + mandatory faction check); make sure each hunter sub-agent actually runs that pass, it is the only path to rhetoric-vs-`saeima_vote` candidates.
     - *Corrected 2026-08-02:* this line used to say `saeima_vote` rows "are NOT in `claim_vectors` … never vectorized". That was false — `store_claim()` embeds every `claim_type`, and 572 265 of 572 811 vote claims (99.9 %) carry a vector today. The conclusion stands, the reason does not: embeddings cluster by topic and cannot separate "atbalstu reformu" from "balsoja PRET reformu" (T9), and `claim_type_filter` is applied AFTER the kNN so rhetoric searches exclude vote rows regardless (T10).
     - *Updated 2026-08-21 (operator verdict):* new `saeima_vote` claims are NO LONGER auto-embedded (`store_claim` skips them; explicit `embedding_bytes` still honored). Historical vectors remain, so old rows still appear in kNN results — but a missing vector on a recent vote claim is expected, not a defect. The structural-SQL rule above is now the ONLY path for rhetoric-vs-vote on new data too.
   - **`stale-pol`** scope — active politicians with ≥5 position claims whose contradiction check has never found anything OR is >60 days stale: `from src.coverage import stale_pol_politicians; stale_pol_politicians()` (ņem db_path STRING vai None → noklusētā DB; NEpadod sqlite3.Connection). Proxy for "last checked" = `MAX(contradictions.detected_at)` per politician (NULL = never found one), so it **overcounts** politicians checked-but-clean (yield is ~1/2700, so most never store a contradiction). This is the periodic coverage-hygiene target, parallel to the `recent` daily scope. It is **broad** (~79 as of 2026-06-08) — run in waves of 4-5 (highest position-claim count first), never all at once.
2. **Fan out `@contradiction-hunter`** — run it as **~4 parallel sub-agents** across the politician set (clean contexts, wide coverage). Each returns structured contradiction *candidates* at threshold **0.80**. The Hunter is prone to **cherry-picking** historic reversals out of context — treat its output as candidates, never as verified.

   **Model pin — pass it explicitly.** The `model: opus` frontmatter pin does **not** reach a plain `agentType: 'general-purpose'` call, and sub-agents must never inherit a Mythos-tier session model (CLAUDE.md § Standing Decisions, 2026-07-21). Dispatching via `Workflow`/`agent()` → pass `model: 'opus'` on every call (the three `.claude/workflows/*.js` files already do); dispatching a named project agent via `Agent` → the frontmatter pin covers you.
3. **Filter through `@devils-advocate`** — every candidate goes to `@devils-advocate`, which attacks it to strip false positives: coalition-discipline votes, procedural/whip context, journalist paraphrase mistaken for a stance, and combinable (non-contradictory) positions. Only survivors proceed.
4. **Store survivors** — `store_contradiction()` (severity ∈ `direct_contradiction` / `reversal` / `minor_shift`; `speaker_scope` defaults `first_party`). **Defaults to `confirmed=0` — UNPUBLISHED.** The operator manually `UPDATE confirmed=1` per contradiction to publish; do not auto-confirm.

## Guardrails

- LV-style on every stored summary (no anglicisms; check grammar — `feedback_check_grammar_stylistics`).
- Attribution: if a synthesis later names "X un Y kritizē Z", each named politician needs ≥1 backing claim about Z — bucket co-occurrence is NOT proof (`feedback_synthesis_attribution`).
- Render the contradictions domain narrowly when publishing: `python -m src.render --only=pretrunas` then `deploy.sh --no-delete`.
