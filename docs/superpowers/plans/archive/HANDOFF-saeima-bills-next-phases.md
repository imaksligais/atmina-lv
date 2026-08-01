# Saeima Bills Tracker — Handoff for Next Sessions

> **Audience:** Claude Code session picking up after Phase 1B-ii merge (master @ `c41f4c2`, 2026-04-27).
> **Status:** Phase 0, 1A, 1B-i, 1B-ii (+ M-4/M-6 polish at `c991de5`) all merged. Phase 1C is the next package; Phase 1.5 / 2 / 3 are deferred.

---

## Current State (verified on master @ `c991de5`)

### Database (`data/atmina.db`)

- **118 saeima_bills** (102 Lp14 + 11 Lm14 + 5 P14)
- **138 saeima_bill_stages**, 0 `nezināms`
- **138 saeima_votes linked** (via `bill_id`)
- **41 bills with `base_law_slug` populated** (34.7% — top: saeimas-velesanu, izglitibas, imigracijas, civilprocesa, kreditiestazu, latvijas-bankas, meza, zinatniskas-darbibas, celu-satiksmes)
- **`saeima_bill_politicians` junction is empty** — Phase 1A backfill couldn't populate, Phase 1C will populate live via `@saeima-tracker` agent flow

### Tests
- 178 saeima/audit/bills/phase_1b_ii tests pass on master
- 19 pre-existing unrelated failures in `tests/test_ingest.py` + `tests/test_wiki.py` + `tests/social_agent/` — orthogonal, predate this work

### Wiki
- 33 `wiki/laws/<slug>.md` files have `<!-- BILLS-SYNC-AUTO -->...<!-- /BILLS-SYNC-AUTO -->` blocks (markdown table when bills exist, empty state when none)
- `wiki/laws/likumi.md` correctly says "Likumi — Indekss" (was "Likumprojekti")
- `wiki/index.md` correctly references "33 likumi" (was "34 likumprojekti")

### Public site (`output/atmina/` after `python -m src.generate`)
- `/likumprojekti/<slug>.html` — 118 bill detail pages (Phase 1B-i)
- `/likumi/<slug>.html` — 33 base-law pages (Phase 1B-ii)
- `/balsojumi.html#bills-list` — 3rd subtab with bills grid + filters (Phase 1B-i)
- 41 detail pages have "Saistītais bāzes likums" section linking to `/likumi/...html` (Phase 1B-ii)
- 0 politician pages have "Likumprojekti" tab/section yet (junction empty — lights up when Phase 1C runs)

### Phase 1B-i (merged @ `42b2375`)
- **Spec**: [`docs/superpowers/specs/2026-04-27-saeima-bills-phase-1b-i-design.md`](../specs/2026-04-27-saeima-bills-phase-1b-i-design.md)
- **Plan**: [`2026-04-27-saeima-bills-phase-1b-i-implementation.md`](2026-04-27-saeima-bills-phase-1b-i-implementation.md)
- Delivered: bill detail pages, bills-list 3rd subtab, vote-card cross-link, P14 motif fix (Step 0)

### Phase 1B-ii (merged @ `c41f4c2` + polish `c991de5`)
- **Spec**: [`docs/superpowers/specs/2026-04-27-saeima-bills-phase-1b-ii-design.md`](../specs/2026-04-27-saeima-bills-phase-1b-ii-design.md)
- **Plan**: [`2026-04-27-saeima-bills-phase-1b-ii-implementation.md`](2026-04-27-saeima-bills-phase-1b-ii-implementation.md)
- Delivered: `base_law_slug` retro-backfill, `upsert_bill` integration, BILLS-SYNC-AUTO marker writeback, `/likumi/<slug>.html` rendering, detail page "Saistītais bāzes likums" block, politician profile Likumprojekti section (conditional), wiki naming fix

### Master spec (canonical, all phases)
- [`docs/superpowers/specs/2026-04-22-saeima-bills-design.md`](../specs/2026-04-22-saeima-bills-design.md) — § 4.4 (agent prompt), § 6.3 (cross-linking), § 11 (docs) cover Phase 1C requirements

---

## Phase 1C — orchestration & glue (NEXT)

### Goal

Activate the agent + auto-link layer so the system stays current without manual intervention. Phase 1C does NOT add new UI surfaces — it wires up the live data flow that 1B-i + 1B-ii templates are already prepared to render.

### Scope (4 work items, ~2-3h, ~5-7 tasks)

**1. `@saeima-tracker` agent prompt update** — `.claude/agents/saeima-tracker.md`

Currently the agent only scrapes completed votes. Add 3 new steps per master spec § 4.4:

- **Step 2: Parse agenda** — before vote scraping, parse Saeimas dienas kārtību → `upsert_bill()` per likumprojekts → `match_submitters_to_politicians()` populates `saeima_bill_politicians` junction
- **Step 3: Capture vote snapshots** — same as today, but each vote gets linked via `bill_id`
- **Step 5.5: Link vote → bill stage** — after each `store_vote()`, call `resolve_bill_from_motif()` + `append_bill_stage()` so stage timeline updates

After this lands, junction will start populating live; politiķa profila Likumprojekti sekcija (1B-ii ready) will start showing data within days.

**2. Pozīciju auto-link regex** — `src/generate.py`

Detect `\b\d+/(Lp14|Lm14|P14)\b` pattern in `claims.summary` text and wrap with `<a href="../likumprojekti/<slug>.html">`. Tests: positive (text contains pattern → link), negative (no pattern → unchanged), and edge cases (multiple bills in one summary, surrounding punctuation).

**3. `wiki/operations/saeima-bills.md` runbook**

Document operator workflow:
- How to run `@saeima-tracker` for a new session
- How to manually add `institutional_submitter` if agent didn't recognize
- How to re-run backfill with adjustments
- Troubleshooting: agenda parse failures, why `base_law_slug=NULL`, how to spot junction data missing

Template: copy structure from existing `wiki/operations/*.md` files.

**4. `CLAUDE.md` Pipeline Invariant 12**

Add discipline rule:
> **12.** `saeima_votes.bill_id` un `saeima_bills.current_stage` atjauno **tikai** caur `append_bill_stage()`. Nekādi citi `UPDATE` neatļauti. Aizstāv denormalizācijas sinhronu — nelaiž neatomiskas izmaiņas, kas plēš stage timeline integritāti.

Place it in the "Pipeline Invariants" section after the existing 11 invariants.

### Suggested task ordering (foundation-first)

1. **Task 0** — Worktree setup + DB copy + baseline tests (procedural, ~5 min)
2. **Task 1** — `CLAUDE.md` Pipeline Invariant 12 (small, no code, ~5 min)
3. **Task 2** — Pozīciju auto-link regex + 3-4 tests (~30 min)
4. **Task 3** — `wiki/operations/saeima-bills.md` runbook (~30 min)
5. **Task 4** — `@saeima-tracker` agent prompt — Step 2 (parse agenda + upsert_bill + match_submitters) (~45 min)
6. **Task 5** — `@saeima-tracker` agent prompt — Step 5.5 (link vote → bill stage) (~30 min)
7. **Task 6** — Smoke: run `@saeima-tracker` on a recent session OR scratch validation; verify junction populates (~30 min)
8. **Task 7** — CHANGELOG + final smoke + commit (~15 min)

### Open question for Phase 1C kickoff

Should `/likumi.html` index page be included? Final review I-2 flagged: 33 base-law pages exist but unreachable from top nav — only via "Saistītais bāzes likums" cross-link from 41 bill detail pages.

- **Option A**: include `/likumi.html` index in 1C — small (~30 min, mirror `/balsojumi.html` listing pattern)
- **Option B**: defer to separate 1B-iii — keeps 1C scope tight (orchestration only)

Recommend **A** — it's small and closes the navigability loop.

---

## Phase 1.5 — Selektīvs vēsturisks re-scrape (optional)

Current 118 bills span ~2 months (2026-03 → 2026-04). 14. Saeima has been active since 2022-11. **Not needed for full historical re-scrape** — selectively pick 30-50 politically important bills (anti-SLAPP, defense funding, immigration amendments, KPL etc.), re-scrape each agenda + votes to populate `submitters` + `amendment_authors`.

**Triggered by**: contradiction detector needing politicians submitting / amending bills over longer periods.

**Estimated size:** 5-8 tasks, ~2-3h Playwright scraping + UPDATE script.

---

## Phase 2 — Priekšlikumu autori (deferred)

Per master spec § 7.1, requires Playwright spike to verify whether amendment tables on `webSasaiste?OpenView&restricttocategory=...` URLs are accessible-tree-parseable or PDF-only.

**Estimated size:** spec writing (1h) + spike (1h) + implementation (2-3h).

---

## Phase 3 — Debates → bill_id (stenogrammas)

Hook is ready: Phase 0 reserved `saeima_bill_stages.stage_kind` column (`'vote' | 'debate' | 'commission'`).

**Open design question (master spec § 12 Q5):** per-utterance in `saeima_bill_stages` rows (`stage_kind='debate'`) vs separate `saeima_debate_utterances` table with `bill_id` FK. Separate table is better if per-utterance has multiple politicians (panel debate).

**Estimated size:** spec writing (1-2h) + implementation (1-2 days).

**Recommendation:** Start with `.scratch/saeima-2026-04-22-23/session-2026-04-23.md` and `session-2026-04-23-J.md` as samples — already scraped.

---

## Open Phase 0.7 / cleanup items (low priority)

These were observed during reviews but deferred. Not blocking:

1. **`_INST_SUBMITTER_RE` module-level constant in `src/saeima.py` is unused** — `_parse_institutional_submitter` re-compiles inline. Either delete the constant or use it.

2. **`AgendaBill.reading_hint` and `vote_uuid` fields are declared but never populated** by `parse_agenda_snapshot`. Phase 1C Step 2 (parse agenda live) will need to populate them.

3. **`_stage_exists_for_vote` in `scripts/backfill_saeima_bills.py` has a stale rationale in its docstring** ("avoids WAL snapshot isolation").

4. **`stage_kind` index could use composite `(bill_id, stage_kind)`** for the WHERE clause in `append_bill_stage`'s recompute query. Re-evaluate if Phase 3 debate stages multiply per bill.

5. **Duplicate `_LAW_TITLE_RE`** — fixed by polish commit `c991de5` (now public `LAW_TITLE_RE` in `src/saeima.py`, imported by `src/generate.py`).

6. **`current_stage='nezināms'` surfaces in user UI** for 16 of 118 bills — review I-3 from Phase 1B-i. Cosmetic; could replace with muted/italic class or "—".

7. **No site-nav entry to `/likumi.html`** — see Phase 1C Open Question above.

8. **Politician profile Likumprojekti tab** — id mismatch fixed at `c41f4c2` (was `profile-bills-section`, now `tab-likumprojekti` matching JS pattern).

---

## Suggested Next-Session Workflow

1. **Read this handoff** + `wiki/CHANGELOG.md` § 2026-04-27 (latest 3 entries: Phase 1B-i, Phase 1B-ii, polish) for full context.
2. **Verify state still holds**: 
   - `git log --oneline -3` should show `c991de5` polish + `c41f4c2` 1B-ii + earlier
   - `python -m pytest tests/test_phase_1b_ii.py tests/test_generate_bills.py tests/test_generate.py tests/test_saeima_bills.py tests/test_saeima_bills_integration.py -q` should report 178 passed
   - `python -c "import sqlite3; db=sqlite3.connect('data/atmina.db'); print(db.execute('SELECT COUNT(*) FROM saeima_bills').fetchone()[0], 'bills,', db.execute('SELECT COUNT(*) FROM saeima_bills WHERE base_law_slug IS NOT NULL').fetchone()[0], 'with base_law_slug')"` should show `118 bills, 41 with base_law_slug`
3. **Decide** on Open Question (include `/likumi.html` in 1C or defer to 1B-iii).
4. **Use `superpowers:brainstorming`** — Phase 1C scope is mostly settled, but resolve the `/likumi.html` question + spec the agent prompt details (master spec § 4.4 has the high-level workflow; agent prompt itself needs concrete prompt text).
5. **Use `superpowers:writing-plans`** to draft the implementation plan, then `superpowers:subagent-driven-development` to execute.

## Helpful Commands

```bash
# Activate venv (Windows)
source .venv/Scripts/activate

# Verify DB state
PYTHONIOENCODING=utf-8 python -c "
import sqlite3
db = sqlite3.connect('data/atmina.db')
print('Bills:', db.execute('SELECT COUNT(*) FROM saeima_bills').fetchone()[0])
print('Stages:', db.execute('SELECT COUNT(*) FROM saeima_bill_stages').fetchone()[0])
print('Linked votes:', db.execute('SELECT COUNT(*) FROM saeima_votes WHERE bill_id IS NOT NULL').fetchone()[0])
print('base_law_slug populated:', db.execute('SELECT COUNT(*) FROM saeima_bills WHERE base_law_slug IS NOT NULL').fetchone()[0])
print('Junction rows:', db.execute('SELECT COUNT(*) FROM saeima_bill_politicians').fetchone()[0])
"

# Re-run backfill (idempotent — safe to repeat)
PYTHONIOENCODING=utf-8 python scripts/backfill_saeima_bills.py
PYTHONIOENCODING=utf-8 python scripts/backfill_base_law_slug.py

# Audit guardrail (vote-result integrity)
PYTHONIOENCODING=utf-8 python scripts/audit_saeima_vote_results.py

# Wiki sync — refresh BILLS-SYNC-AUTO blocks + indexes
python -c "from src.wiki import wiki_sync; wiki_sync(db_path='data/atmina.db', wiki_dir='wiki')"

# Worktree for Phase 1C
git worktree add .worktrees/saeima-bills-phase-1c -b saeima-bills-phase-1c master
```

---

## Open Strategic Questions (defer until after Phase 1C lands)

- **Phase 3 architecture**: single table with `stage_kind='debate'` vs separate `saeima_debate_utterances` (master spec § 12 Q5).
- **Historical scope (Phase 1.5)**: 30 bills, 50 bills, or all ~5000 since 2022-11? Tradeoff is Playwright session count vs. contradiction detection coverage.
- **Agenda re-parse cadence**: is `@saeima-tracker` weekly enough, or daily? Current routine is weekly (`wiki/operations/weekly-routine.md` § 3). Phase 1C agent flow may want daily for fresher data.

---

_Updated 2026-04-27 after Phase 1B-ii merge + M-4/M-6 polish (master @ `c991de5`)._
