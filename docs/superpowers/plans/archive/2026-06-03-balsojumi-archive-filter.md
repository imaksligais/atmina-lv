# Balsojumi TAB 1 — archive-mode session/topic/deputy filtering

**Date:** 2026-06-03
**Branch:** `feat/balsojumi-archive-filter`
**Goal:** Let the "Balsojumi" subtab (TAB 1) filter by *any* session/topic/deputy across the full vote history (~5704 votes), not just the SSR'd latest 200 — while keeping first-paint unchanged (no upfront cost).

## Root cause (verified in code)

- `templates/balsojumi.html.j2:97` SSRs only `votes[:200]` as rich cards.
- `src/render/votes.py:637-646` deliberately limits the three filter dropdowns to that 200-vote subset (comment: avoid dead options that match no rendered card).
- Inline filter JS (`balsojumi.html.j2`) iterates only the SSR DOM cards.

## Key insight

The matrix JSON (`_build_matrix_compact`) already carries everything a TAB-1 card needs, and already has recent/full lazy-load infra:

| Card field | Compact JSON |
|---|---|
| motif/date/time/result | `m,d,t,r` |
| totals Par/Pret/Atturas | `tot` |
| faction strip | `f=[{f,p,n,a,x}]` |
| summary (where present) | `s` |
| titania/table links | `url,doc_url` |
| tracked politicians + their vote | `politicians[pid].v[i]` + `.n/.f/.s` |

Missing only: **bill_slug + bill_doc_nr** (for the `likumprojekti/<slug>.html` link) and **faction coalition status** (for chip coloring). Both are tiny additions.

## Design — reuse the matrix JSON for TAB-1 "archive mode"

1. **Filter dropdowns populated from the FULL vote set** (all sessions/topics/deputies). Cost ~3 KB DOM; first paint unchanged.
2. **No filter → SSR 200 cards** (unchanged, instant).
3. **Any filter active → archive mode:** lazy-fetch the full matrix JSON (`ensureFullData`, 303 KB br, one-time, cached), filter all votes, render matching cards client-side (SSR-identical HTML), capped with "Rādīt vairāk". Clear filters → restore SSR cards.

Archive mode always loads the **full** archive (not recent) because topic/deputy filters span all history; correctness over the 75 KB→303 KB delta on an explicit, cached, opt-in action.

## Changes

### `src/render/votes.py`
- `_build_matrix_data`: fetch `coalition_map`; add `coalition_status` to each faction object; carry `bill_slug` + `bill_doc_nr` into `vote_columns`.
- `_build_matrix_compact`: emit `bsl`/`bnr` (optional) per vote; `cs` per faction.
- `render_votes`: build `vote_topics`/`deputies`/`vote_sessions` from the FULL `votes`, not `votes[:200]`. (Archive mode makes every option live.)

### `assets/bmv1.js`
- Extract shared `loadInto(src, markFull, cb)`; `initBalsojumiMatrica` + `ensureFullData` reuse it.
- `window.balsojumiEnsureData(recentSrc, fullSrc, wantFull, cb)` — load (full when wanted) without rendering the matrix.
- `window.balsojumiArchiveRender(filters, opts, cb)` — ensure full data, filter indices, return SSR-identical card HTML (faction strip from `v.f` + computed discipline/majority + `cs`; tracked table from scanning `politicians`).

### `templates/balsojumi.html.j2`
- Inline filter JS: maintain selected sets; on change, if any set non-empty → call `balsojumiArchiveRender` into `#votes-list`; else restore SSR cards. Pass recent+full JSON srcs. Cap + "Rādīt vairāk".

## Verification
- Unit: `tests/test_render_votes_matrix_json.py` — assert `bsl/bnr/cs` present + shapes.
- `scripts/render_balsojumi_only.py` (~15s) smoke.
- Playwright: (a) default load fetches NO matrix JSON; (b) selecting an old session triggers full-archive fetch + renders cards; (c) clearing restores SSR.
- `REGEN=1 pytest tests/test_render_chars.py` (balsojumi.html + bmv1.js asset version drift).
- `bash scripts/check.sh` green.

## Non-goals
- No per-session JSON shards (rejected: ~200 files, data duplication, no infra reuse).
- No change to the Matrica tab behavior or the recent-shard default.
