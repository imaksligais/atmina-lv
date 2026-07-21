# Plan: separate Saeima votes from media positions via `claim_type`

**Date:** 2026-04-11 (revised 2026-04-11 after council review)
**Status:** Not started — planned in 2026-04-11 session, to be executed in a later session
**Source:** Strategic analysis T1 / S1, from the 2026-04-10 backlog audit and 2026-04-11 project-wide retrospective. Revision incorporates council review findings on backfill heuristic, phase sizing, cutover safety, and contradiction filter directionality.

## Why

The atmina DB currently holds **6189 "claims"**, but **5458 of them (88%) are Saeima voting records** ingested via `saeima-tracker` (authoritative count via `documents.platform='saeima'`), not first-person political positions. They sit in the same `claims` table alongside ~720 media-sourced positions, and every metric, UI page, contradiction check, and topic aggregation treats them interchangeably. This causes:

1. **Headline metrics mislead.** "6189 pozīcijas" implies a rhetorical corpus 8× larger than reality. The 2026-04-11 S4 fix ("6189 pozīcijas (5469 Saeimas balsojumi + 720 media)") patches the dashboard text but the underlying data is still mixed — and that fix itself used the fragile `source_url LIKE '%saeima%'` heuristic, which overcounts by 11 rows (media articles citing saeima.lv).
2. **Topic distribution is corrupted.** `Valsts pārvalde` has 1173 claims, disproportionately because it is the fallback topic for legislative votes (`saeima.py:769` silent default). **Note:** this plan fixes the *denominator skew*, not the fallback-topic root cause. S3 remains required for that.
3. **Contradiction detection drowns in procedural noise.** The 2026-04-11 data audit identified 187 politician-topic pairs with opposing stance patterns, the vast majority being Saeima procedural votes rather than genuine shifts. Real rhetoric-vs-action contradictions are buried.
4. **Claim #85 syndrome.** ~1000 claims are factual descriptions of legislative outcomes rather than first-person positions. Example: Rinkēvičs claim #85 stance = "Otrreiz izsludinātais likums apstiprināts Saeimā..." — that is the Saeima's action, not Rinkēvičs' stated position.
5. **Claim count per politician is distorted.** Median `position`-type claims per active politician is **0**, and 85/147 have zero. Total count is hidden by vote rows.

Separating the two row types via an explicit `claim_type` lets every downstream consumer pick the right denominator and rendering.

## Schema state today (verified 2026-04-11)

```
claims by claim_type:            position=5594, vote=595   (total 6189)
claims via documents.platform:   saeima=5458 ← authoritative
claims via source_url heuristic: saeima=5469 (overcounts by 11)
orphan vote row:                 id=468, URL=x.com/maija_armaneva/... (legacy mislabel)
baseline passing tests:          245
```

The `saeima-tracker` ingester populates `claim_type` partially and inconsistently. Backfill is required — **but via the authoritative `documents.platform='saeima'` join, not the URL substring**.

## Decisions confirmed

These decisions are locked in for this revision. Re-read them before starting Phase A — if any change, update this plan before executing.

1. **Naming.** `'position'` vs `'saeima_vote'` (Option B). Future-proof for `'ep_vote'`, `'committee_vote'`, `'press_release'`.
2. **Backfill signal.** `documents.platform='saeima'` (join), **NOT** `source_url LIKE '%saeima%'`. Rationale: the URL heuristic mislabels 11 verified rows (media articles citing saeima.lv). The plan also explicitly re-labels the orphan `'vote'` row #468 based on its actual nature (position — it's a tweet).
3. **Contradiction detection semantics.** Cross-type comparisons allowed, but the filter is **directional / per-call-site**, not a global toggle:
   - Contradiction retrieval (position → candidates): include both `position` and `saeima_vote`.
   - Contradiction retrieval (saeima_vote → candidates): include **only `position`** (vote-vs-vote excluded as procedural noise).
   - Generic similarity lookups: no filter by default.
   - `search_similar_claims` gains `claim_type_filter: Optional[list[str]]` parameter; callers pass the right list explicitly. Both directions must have test coverage.
4. **UI effect.** Default to `'position'` only on dashboards, leaderboards, topic-stance lists. Politician profile grows a second section "Balsojumi". Contradiction page stays cross-type. **Headline metrics on wiki/index.md and the public dashboard retain a split presentation** ("720 pozīcijas + 5458 Saeimas balsojumi") so the -88% visible drop is framed as reclassification, not data loss.

## Prerequisite: land S10 first

S10 (`save_analysis` atomicity — wrap `store_analysis` + all `store_claim` calls in one SQLite transaction) **must land before Phase A**, not after. Rationale: if `save_analysis` isn't atomic and Phase A extends its signature, a mid-save crash leaves mixed `claim_type` state across `analyses` and `claims`. The refactor surface is the same regardless of ordering, so doing it first costs nothing and buys safety for the rest of this plan.

If S10 is not yet landed at execution time, stop and land it before Phase A.

## Phased execution

Six phases (Phase D split into D1/D2), each with a commit and verification checkpoint. Do not batch phases. If a phase fails verification, revert before the next phase. Every phase touches ≤5 files.

### Phase A — Data layer (4 files)

Goal: the column is populated correctly via authoritative signal, the write path accepts `claim_type`, the index exists, and backfill is done.

Steps:
1. **Backup the DB.** Copy `data/atmina.db` → `data/atmina.db.backup-20260411` before any UPDATE.
2. **Sample audit before backfill.** Run: `SELECT c.id, c.source_url, d.platform, substr(c.stance,1,80) FROM claims c JOIN documents d ON c.document_id=d.id WHERE d.platform != 'saeima' AND c.source_url LIKE '%saeima%' LIMIT 20`. Confirm all 11 rows are genuinely media positions citing saeima.lv (expected) — if any look like misclassified votes, stop and investigate.
3. **Backfill via authoritative join:**
   ```sql
   UPDATE claims
   SET claim_type = 'saeima_vote'
   WHERE document_id IN (SELECT id FROM documents WHERE platform = 'saeima');
   ```
   Expected: 5458 rows affected.
4. **Fix the orphan.** Row #468 is a tweet mislabeled as `'vote'`:
   ```sql
   UPDATE claims SET claim_type = 'position' WHERE id = 468;
   ```
   (Or: `UPDATE claims SET claim_type='position' WHERE claim_type='vote' AND document_id NOT IN (SELECT id FROM documents WHERE platform='saeima')` for generality.)
5. **Add index** for future filter performance:
   ```sql
   CREATE INDEX IF NOT EXISTS idx_claims_claim_type ON claims(claim_type);
   CREATE INDEX IF NOT EXISTS idx_claims_opp_type_topic ON claims(opponent_id, claim_type, topic);
   ```
6. **`src/db.py store_claim`:** add `claim_type: str = 'position'` parameter, thread through the `INSERT`.
7. **`src/db.py search_similar_claims`:** add `claim_type_filter: Optional[list[str]] = None`; when set, add `WHERE claim_type IN (...)` to the query. Default `None` = no filter (existing behavior).
8. **`src/tools.py store_claim` + `search_similar_claims`:** add matching parameters on the wrappers.
9. **`src/analyze.py save_analysis`:** accept `claim_type` as an optional per-claim field in the claims dict (default `'position'`), pass through.
10. **Tests** (all in `tests/test_db.py` and/or `tests/test_analyze.py`):
    - `store_claim(claim_type='saeima_vote')` inserts correctly.
    - `save_analysis(claims=[{..., 'claim_type': 'saeima_vote'}])` routes correctly.
    - `search_similar_claims(claim_type_filter=['position'])` excludes vote rows.
    - `search_similar_claims(claim_type_filter=None)` returns both (existing default).
    - **Bidirectional contradiction retrieval:** given a stored `position` "Pret X" and a stored `saeima_vote` "Atbalsta: X likumprojekts" for the same politician:
        - Query from the position side with `claim_type_filter=['position','saeima_vote']` → finds the vote.
        - Query from the vote side with `claim_type_filter=['position']` → finds the position.
    - Regression: existing tests pass without explicit `claim_type`.
    - Test fixture in `tests/test_wiki.py` gains `claim_type` column seeding.
11. **Verify:**
    - `pytest tests/` passes, test count **≥ 245** (current baseline).
    - `SELECT claim_type, COUNT(*) FROM claims GROUP BY claim_type` returns **exactly two rows**: `'position'` and `'saeima_vote'`. No `'vote'` left.
    - Counts: `saeima_vote=5458`, `position=731` (6189 − 5458).

Commit: `feat(claims): introduce claim_type column split (position vs saeima_vote)`

Files: `src/db.py`, `src/tools.py`, `src/analyze.py`, `tests/test_db.py` (+ `tests/test_analyze.py` / `tests/test_wiki.py` fixture edit if needed — stays within 5 files). Backfill + index SQL lives in a throwaway script or documented one-off.

**No ingestion between Phase A and Phase B.** New rows written by any ingester would land with the old `claim_type` default and silently re-pollute. Pause the routine until Phase B lands.

### Phase B — Saeima writer (1–2 files)

Goal: every new row the Saeima tracker inserts arrives with `claim_type='saeima_vote'`.

Steps:
1. **`src/saeima.py`:** grep every `store_claim` call site, add `claim_type='saeima_vote'` to each.
2. **Smoke test:** run one ingest cycle against a live snapshot; verify new rows have correct `claim_type`.
3. Unit test covering the saeima writer call path.

Commit: `feat(saeima): tag new vote records with claim_type='saeima_vote'`

Files: `src/saeima.py`, `tests/test_saeima.py` (if exists, else skip).

### Phase C — Readers and filters + dual-read guard (5 files)

Goal: every module that queries `claims` uses `claim_type` rather than the URL heuristic, **with a temporary dual-read assertion that would catch backfill drift before it reaches the UI**.

Steps:
1. **`src/wiki.py`:** replace the `source_url LIKE '%saeima%'` filters (line 426 and nearby) with `claim_type = 'saeima_vote'` / `claim_type = 'position'`. **Add a temporary assertion** next to each converted query that recomputes the count via the old URL heuristic and logs/raises on divergence. This assertion lives for one phase only — removed in Phase D2.
2. **`src/confidence_drift.py`:** filter to `claim_type = 'position'`. Procedural votes should not contribute to confidence inflation signals.
3. **`src/cross_check.py`:** filter to `claim_type = 'position'`. Vote-vs-vote pair scanning is pure noise. Pass `claim_type_filter=['position']` on any `search_similar_claims` call.
4. **`src/briefs.py`:** in daily/weekly briefs, surface position count and vote count separately ("12 jaunas pozīcijas, 34 Saeimas balsojumi").
5. **Tests** for each module's filter change + the dual-read assertion.
6. **Verify:** regenerate `wiki/index.md`, confirm headline numbers match Phase A counts (731 position + 5458 saeima_vote). If the dual-read assertion logs any divergence, stop and investigate before proceeding to Phase D1.

Commit: `refactor(readers): query by claim_type instead of source_url heuristic (with dual-read guard)`

Files: `src/wiki.py`, `src/confidence_drift.py`, `src/cross_check.py`, `src/briefs.py`, `tests/test_wiki.py`. (5 files exactly.)

### Phase D1 — Generate fetch functions (≤5 files)

Goal: all `_fetch_*` functions in `src/generate.py` filter by `claim_type` where appropriate. **No template changes yet.**

Steps:
1. **Inventory:** grep `src/generate.py` for every `_fetch_*` function touching `claims`. Classify each: positions-only, votes-only, both-as-separate-keys, or no-filter (contradictions). Produce a short classification table in the commit message.
2. **Dashboard / homepage fetch:** positions only.
3. **`_fetch_politician_detail`:** return `positions: [...]` and `votes: [...]` as distinct keys in the context dict (template will consume both in D2).
4. **Topic page fetch:** positions for "top stances"; add `votes` list as separate key.
5. **Party page fetch:** positions for stance aggregation; votes as separate key.
6. **Leaderboards fetch:** positions only.
7. **Contradictions fetch:** no filter.
8. **Matrix / tensions / graph:** per-case decisions made in the inventory step; implement here.
9. **Smoke test:** `python -c "from src.generate import generate_public_site; generate_public_site()"` still produces `output/` without errors. Templates may show temporary ugliness (votes missing from profile); that's expected and fixed in D2.
10. **Tests:** at least one test per modified fetch function confirming the filter.

Commit: `refactor(generate): filter _fetch_* by claim_type, expose positions+votes separately`

Files: `src/generate.py`, `tests/test_generate.py` (if exists) — aim for 1–2 files + any directly-imported helper. Cap: 5 files. If the fetch changes spill beyond that, split D1 into D1a (dashboard/leaderboard/topic) and D1b (party/profile/matrix).

### Phase D2 — Templates, headline framing, cleanup (≤5 files)

Goal: public site renders positions and votes as distinct first-class concepts; headline metrics retain split framing; dual-read guard from Phase C is removed.

Steps:
1. **Politician profile template:** render "Pozīcijas" and "Balsojumi" as two distinct sections with their own counts.
2. **Topic / party templates:** add optional "Balsojumi" section below the stance list where data supports it.
3. **Headline framing:** on `wiki/index.md` (via `src/wiki.py` templating) and the public dashboard, the top metric reads "**731 pozīcijas + 5458 Saeimas balsojumi**" (split), not "731 pozīcijas" alone. Add a pinned "Kas mainījās 2026-04-11" note explaining the reclassification so readers don't perceive data loss.
4. **CSS adjustments** if needed for the new section.
5. **Remove the Phase C dual-read assertion** now that UI is stable.
6. **Cleanup orphaned contradictions:** delete rows in `contradictions` where both sides are now `saeima_vote`:
   ```sql
   DELETE FROM contradictions
   WHERE claim_a_id IN (SELECT id FROM claims WHERE claim_type='saeima_vote')
     AND claim_b_id IN (SELECT id FROM claims WHERE claim_type='saeima_vote');
   ```
   (Verify column names against actual `contradictions` schema before running.) Expect a meaningful drop — most of the 187 audit-flagged pairs should disappear.
7. **Smoke test:** full generate, manually open 3–4 pages (dashboard, one politician profile, one topic page, contradictions page).
8. **Verify:** `pytest tests/` passes with test count **≥ 245**; `@quality-reviewer` run reports no new inconsistencies.

Commit: `feat(site): render positions and Saeima votes as distinct sections + cleanup`

Files: `templates/*.html.j2` (profile, topic, party — up to 3), `src/wiki.py` (header text), `assets/style.css` if needed. Cap: 5 files.

### Phase E — Agents and documentation (2 tracked files + .claude local)

Goal: prompts and runbooks reflect the new vocabulary.

Steps:
1. **`.claude/agents/claim-extractor.md`** (gitignored — local-only): document that `claim_type` defaults to `'position'`, agent should not override.
2. **`.claude/agents/saeima-tracker.md`** (gitignored): document that it must always set `claim_type='saeima_vote'`.
3. **`wiki/operations/agenti/claim-extractor.md`:** same summary (this IS tracked).
4. **`wiki/operations/agenti/saeima-tracker.md`:** same (tracked).
5. **`wiki/operations/daily-routine.md`:** update Step 2 example showing `claim_type` pass-through is optional.

Commit: `docs: update agent runbooks for claim_type split`

Files (tracked): `wiki/operations/agenti/claim-extractor.md`, `wiki/operations/agenti/saeima-tracker.md`, `wiki/operations/daily-routine.md`. `.claude/` edits are not committed.

## Risk profile

- **Phase A backfill is destructive-but-reversible.** Backup copy makes rollback one `cp` away. Double-check row counts before and after. **The "no ingestion between A and B" rule is load-bearing** — a single Saeima ingest run in between would re-pollute the column.
- **Backfill heuristic risk eliminated.** Previous draft used `source_url LIKE '%saeima%'`, which would mislabel 11 media articles. This revision uses `documents.platform='saeima'` (5458 authoritative rows) and handles the orphan row explicitly.
- **Phase D1 is the highest-risk phase** (not D2). `generate.py` is 444 lines and has no end-to-end test. Mitigation: inventory-first step, cap at 5 files with D1a/D1b fallback, explicit per-function classification table in the commit message.
- **Dual-read guard catches backfill drift.** If Phase A missed any rows (it shouldn't), the Phase C assertions will raise before any UI is regenerated. Guard is removed in D2.
- **Contradiction directionality test is mandatory.** Both directions (position→vote and vote→position) must have explicit test coverage, not just the risk-profile example.
- **Headline metric communication.** The -88% visible drop (6189 → 731) is reframed as "731 pozīcijas + 5458 Saeimas balsojumi" retained on all public surfaces + a pinned changelog note.
- **Uncommitted wiki edits.** `git status` shows 20+ modified `wiki/*.md` files. Commit or stash them before Phase C regenerates `wiki/index.md`, or they will be clobbered.

## Unresolved questions to revisit before starting

- **`position_shifts` from save_analysis:** currently unused downstream. Leave alone unless it surfaces during Phase A.
- **Historical `'vote'` values:** one orphan (row #468), handled explicitly in Phase A step 4.
- **Contradiction cleanup idempotency:** the Phase D2 DELETE assumes contradictions store stable claim IDs. Verify the schema before running; if it uses a different reference model, adapt.

## Success criteria

After all six phases:

1. `SELECT claim_type, COUNT(*) FROM claims GROUP BY claim_type` returns **exactly two rows**: `position=731` and `saeima_vote=5458`. No `'vote'`.
2. `idx_claims_claim_type` and `idx_claims_opp_type_topic` exist.
3. `wiki/index.md` shows split headline ("731 pozīcijas + 5458 Saeimas balsojumi") via `claim_type`, with a pinned "kas mainījās 2026-04-11" changelog note.
4. A politician profile page shows **two distinct sections**: Pozīcijas and Balsojumi, each with their own counts.
5. `@quality-reviewer` run against a post-migration routine reports no new inconsistencies.
6. `pytest tests/` passes with **≥ 245** tests (current baseline; new tests added in Phases A/C/D1 should push this higher).
7. `@devils-advocate` can still find and confirm rhetoric-vs-action contradictions (cross-type, bidirectional).
8. Vote-vs-vote rows in `contradictions` table are cleaned up (Phase D2 DELETE).
9. Phase C dual-read assertion never fired during execution (or fired and was investigated before proceeding).

## What this plan does NOT cover

- **S2** — Media coverage as a first-class primary metric on atmina.lv homepage.
- **S3 Phase 1** — Remaining HIGH/MEDIUM silent-swallow blocks, **including `saeima.py:769` fallback-topic bug**. This plan fixes the denominator skew in topic distribution but NOT the root cause — Saeima votes still fall into the `Valsts pārvalde` fallback topic. S3 still required.
- **S8** — Expanding `tests/test_ingest.py` beyond name-match regressions.
- **S9** — Russian-language extraction pipeline (307 docs, 0 claims).
- **S11** — `generate.py` decomposition.

**S10** (`save_analysis` atomicity) was previously listed here but is now a **prerequisite** to Phase A — see "Prerequisite" section above.

## References

- 2026-04-10 backlog audit (session commits `bf49be6` through `eddf419`)
- 2026-04-11 strategic analysis (two parallel Explore agent reports, synthesized in-session)
- 2026-04-11 silent-swallow audit (10 Category C blocks classified; 1 HIGH fixed in `eddf419`)
- 2026-04-11 council review of this plan's first draft (see session transcript)
- Current `wiki/index.md` metric split (S4 commit `2db7f80`)
- Verified 2026-04-11: `documents.platform='saeima'` → 5458 claims; URL heuristic → 5469 (11 false positives); orphan `'vote'` row id=468 (tweet); test baseline 245
