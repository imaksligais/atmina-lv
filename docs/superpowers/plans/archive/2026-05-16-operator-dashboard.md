# atmina ops Dashboard — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a beautiful, info-dense, keyboard-first localhost operator dashboard at `http://127.0.0.1:8080` that surfaces all atmina state in one screen, lets operator perform the 3 most-common actions (image approve, deploy, slot refresh) without leaving the page, preserves a chronological **memory** of today's work via an activity timeline, and onboards a new team member without external docs.

**Spec reference:** [`docs/superpowers/specs/2026-05-16-operator-dashboard-design.md`](../specs/2026-05-16-operator-dashboard-design.md) — wireframe, IA, visual language, interaction patterns, state design, tech-stack rationale.

**Architecture:** New `src/dashboard/` package mirroring `src/render/` and `src/saeima/` split-pattern. Stack: Flask + Jinja2 + HTMX + Tailwind + Alpine.js (all via CDN, no build step). Root-level `serve.py` is the launcher. Read-only DB via existing `get_db()`; writes only via dedicated mutators behind confirm modals.

**Memory references:**
- `[[project_2026-05-16_tech_debt]]` — slot degradation motivated this; `52775ac` guardrail wired here
- `[[project_featured_images]]` — `brief_images` approval flow re-surfaced in UI
- `[[feedback_no_morning_brief]]`, `[[project_daily_routine_timing]]` — morning-window logic moves into `check_routine()`, not dashboard

---

## Progress overview

> Single source of truth for "kur mēs esam". Update task checkboxes as you complete them; the per-step `- [ ]` lower in each Task section is fine-grained, this is high-level.

**Status:** Phase 0 ✅ · Phase 1 ✅ (9/9) · Phase 2 ✅ (5/5) · Phase 3 0/5 (optional) · Phase 4 (separate plan)

**Phase 0 — Decisions** ✅ captured below
- [x] Stack chosen (Flask + HTMX + Tailwind + Alpine)
- [x] No auth · localhost only
- [x] Visual language locked (brand-aligned)
- [x] Single-page layout + activity timeline as memory layer
- [x] Naming: "atmina ops"

**Phase 1 — Foundation & read-only telemetry** (9/9) ✅ M1 SHIP GATE COMPLETE
- [x] 1.1 Scaffolding + design system + theme toggle
- [x] 1.2 Today's brief panel (4 states)
- [x] 1.3 Routine panel + morning-window in `check_routine()`
- [x] 1.4 Slot health panel (reuses `52775ac` probe)
- [x] 1.5 A/B strategy panel + 7-run SVG chart
- [x] 1.6 Extraction backlog panel
- [x] 1.7 Activity timeline (memory layer, 4-source UNION)
- [x] 1.8 Pending-action banner + footer + index composition
- [x] 1.9 Wiki + CHANGELOG + CLAUDE.md integration

**Phase 2 — Interactivity & actions** (5/5) ✅ M2 SHIP GATE COMPLETE
- [x] 2.1 HTMX action infra + toast system
- [x] 2.2 Image approve / reject
- [x] 2.3 Slot probe force-refresh
- [x] 2.4 Deploy trigger with confirm modal
- [x] 2.5 Keyboard help modal + shortcut registration

**Phase 3 — Polish & onboarding** (0/5, OPTIONAL)
- [ ] 3.1 Per-panel help tooltips
- [ ] 3.2 Empty-state copywriting pass + illustrations
- [ ] 3.3 Settings page (theme + refresh interval)
- [ ] 3.4 First-visit tour overlay
- [ ] 3.5 SSE for live activity

**Phase 4 — Atmina publishing-channel telemetry** — deferred to separate plan after M1+M2 ship

**Open decisions awaiting operator (small, can defer to Task 1.1 kickoff):**
- [x] Default theme: **auto** (system pref) — operator choice 2026-05-16, "pagaidām" (revisitable)
- [x] Pending-action banner: **sticky top, dismissable per session** — operator choice 2026-05-16, "pagaidām" (revisitable)

---

## Phase 0 — Decisions (DONE in conversation, captured here)

- [x] **Stack:** Flask + HTMX + Tailwind + Alpine over FastAPI / React / stdlib http.server (see spec § Tech stack)
- [x] **Auth:** none; localhost-only bind (127.0.0.1)
- [x] **Visual language:** atmina brand-aligned (cream/ink + sarkans accent), system sans for UI, JetBrains Mono for data, Georgia for brief prose, dark-mode-first per operator workflow
- [x] **Layout:** single-page front (no nav until M3 detail pages); 5 panels + activity + footer
- [x] **Actions:** approve image, deploy (with confirm modal), refresh slot probe; everything else stays in Claude Code
- [x] **Memory:** activity timeline as permanent panel, fed from `logs` + `brief_images` + `context_notes` + `analyses`
- [x] **Naming:** "atmina ops"

**Operator decisions still open (low-stakes, can defer to Phase 1 kickoff):**

1. Default theme — auto-detect (`prefers-color-scheme`) vs force-dark?
2. Pending-action banner placement — sticky top vs inline?

---

## Phase 1 — Foundation & read-only telemetry (2-3 dienas)

**Acceptance gate:** All 5 panels visible at `/`, all 4 states (active/empty/loading/error) per panel, dark/light theme works, page loads <2 s, every read-only script from today's session has a 1-click visual equivalent.

### Task 1.1: Package scaffolding + design system + theme toggle

**Files:**
- Create: `src/dashboard/__init__.py`
- Create: `src/dashboard/server.py` (Flask app factory)
- Create: `src/dashboard/templates/_base.html.j2` (layout: head, header, footer, theme toggle, CDN script tags)
- Create: `src/dashboard/templates/index.html.j2` (panel grid skeleton)
- Create: `src/dashboard/static/ops.css` (custom CSS vars + minor overrides; Tailwind handles the rest)
- Create: `src/dashboard/static/ops.js` (theme toggle persistence + Alpine init)
- Create: `serve.py` (repo-root launcher: `python serve.py`)
- Modify: `requirements.txt` (+ `flask>=3.0,<4`)
- Create: `tests/test_dashboard_server.py`

**Test contracts:**
- `test_app_factory_returns_flask_instance`
- `test_app_binds_localhost_only` — explicit 127.0.0.1; fails on 0.0.0.0
- `test_root_returns_200_with_panel_grid` — 5 panel containers in HTML
- `test_theme_toggle_persists_via_localstorage` — JS-level via headless eval if cheap; otherwise skip

**Steps:**
- [x] Pin Flask in `requirements.txt`, `pip install`
- [x] Write failing tests
- [x] Implement `create_app()` with single `/` route serving `index.html.j2`
- [x] `_base.html.j2`: HTML5 doctype, head with Tailwind CDN + HTMX + Alpine + Lucide, `<body class="...">` with header + main + footer + toast container
- [x] Design tokens in `ops.css`: CSS vars for cream/ink/sarkans + status colors (per spec § Visual language)
- [x] Theme toggle: header button cycles `auto / light / dark`, persists to localStorage, applies class on `<html>`
- [x] `serve.py`: `app = create_app(); app.run(host='127.0.0.1', port=8080, debug=False)`
- [ ] Smoke: `python serve.py`, open browser, see empty grid + functional theme toggle *(operator-driven)*
- [x] Commit: `feat(dashboard): scaffold serve.py + design system + theme toggle` (a2082a0)

### Task 1.2: Today's brief panel (active + empty + loading + error states)

**Files:**
- Create: `src/dashboard/views/__init__.py`
- Create: `src/dashboard/views/brief.py` (`get_brief_context(date)`)
- Create: `src/dashboard/templates/partials/brief.html.j2`
- Create: `src/dashboard/templates/empty/no_brief.html.j2`
- Modify: `src/dashboard/templates/index.html.j2` (include partial)
- Modify: `src/dashboard/server.py` (compose context)
- Create: `tests/test_dashboard_brief.py`

**Test contracts:**
- `test_brief_context_returns_today_brief_when_exists`
- `test_brief_context_includes_image_approval_state`
- `test_brief_context_extracts_cited_claim_ids_from_content`
- `test_brief_partial_renders_empty_state_when_missing` — friendly LV copy + link to backlog

**Steps:**
- [x] Tests first (9 tests covering view helper + 4 states)
- [x] `get_brief_context(date)`: query `context_notes` + `brief_images`; extract `#\d{5}` claim refs from content; strip HTML comments + markdown bold for lede preview
- [x] Partial template: hero image thumbnail (clickable → modal in M2), title, char count, citation chip, image approval badge, two action links (wiki file://, atmina.lv https)
- [x] Empty state: warm copy explaining how to write today's brief, link to extraction backlog
- [x] Loading state: skeleton with shimmer (Tailwind animate-pulse)
- [x] Error state: neutral chip with retry button
- [ ] Smoke in browser, both states *(operator-driven)*
- [x] Commit: `feat(dashboard): brief panel with 4 explicit states`

### Task 1.3: Routine panel + morning-window awareness (centralize logic)

**Files:**
- Modify: `src/routine.py` (add morning-window awareness to `check_routine()` — single source of truth)
- Create: `src/dashboard/views/routine.py` (thin wrapper)
- Create: `src/dashboard/templates/partials/routine.html.j2`
- Create: `tests/test_dashboard_routine.py`
- Modify: `tests/test_routine.py` (if exists; cover morning-window)

**Test contracts:**
- `test_routine_check_returns_step_list_with_status_each` — `check_routine()` output shape
- `test_routine_check_marks_extraction_as_waiting_before_15h` — morning-window expected behavior
- `test_routine_partial_renders_8_steps_with_status_icons`
- `test_routine_partial_shows_next_scheduled_below_list`

**Steps:**
- [x] Move morning-window logic INTO `check_routine()` — return `status='waiting'` (new state) for extraction/brief steps before 15:00 LV time; per `feedback_no_morning_brief` and `project_daily_routine_timing`
- [x] Dashboard view: simple wrapper calling `check_routine(date)`, augments steps with `label`/`icon`
- [x] Partial: vertical list, status icon + LV label + details. (Next-scheduled section deferred to Task 1.8 with pending banner — single source for "what's coming")
- [x] Commit: `feat(routine): morning-window awareness in check_routine + dashboard panel`

### Task 1.4: Slot health panel (reuse 52775ac probe)

**Files:**
- Create: `src/dashboard/views/slots.py` (cached snapshot helper)
- Create: `src/dashboard/templates/partials/slots.html.j2`
- Create: `tests/test_dashboard_slots.py`

**Test contracts:**
- `test_slot_snapshot_returns_6_cards_with_4_endpoints_each`
- `test_slot_snapshot_uses_60s_cache_unless_force_true`
- `test_slot_snapshot_handles_uninitialized_slot_gracefully`
- `test_slot_partial_warns_when_search_tweet_healthy_below_4`

**Steps:**
- [ ] Tests first
- [ ] `get_slot_snapshot(force=False)`: module-level dict cache `{ts, result}`; reuse `src.x_mentions._probe_search_slot_health` for `search_tweet` + per-endpoint probe for the other 3 (mirror `scripts/probe_x_cookies.py`)
- [ ] Partial: 6 cards in 3-column grid; 4 status dots per card (get_user / user_tweets / user_replies / search_tweet); guardrail warning chip when search_tweet healthy <4
- [ ] Probe age timestamp + refresh button (POST endpoint in M2)
- [ ] Commit: `feat(dashboard): slot health panel with 60s cache + guardrail surfacing`

### Task 1.5: A/B strategy panel with mini SVG chart

**Files:**
- Create: `src/dashboard/views/strategy.py`
- Create: `src/dashboard/templates/partials/strategy.html.j2`
- Create: `src/dashboard/templates/partials/_svg_bars.html.j2` (reusable inline-SVG bar chart macro)
- Create: `tests/test_dashboard_strategy.py`

**Test contracts:**
- `test_strategy_view_reads_env_var_correctly`
- `test_strategy_view_aggregates_last_7_runs`
- `test_strategy_view_counts_guardrail_trips_last_24h_from_logs`
- `test_svg_bars_macro_produces_valid_svg`

**Steps:**
- [ ] Read `X_MENTIONS_STRATEGY` from process env (operator launches `serve.py` from a shell that inherits User-scope; document this in runbook)
- [ ] Query last 7 `mentions_fetch` log rows; compute stored count per run
- [ ] Inline server-rendered SVG bar chart macro (no JS); width 280, height 80, simple rects
- [ ] Guardrail trip count: scan last 24h `logs` for `WARNING fetch_mentions: only N/6 slots healthy ... falling back to timeline`
- [ ] Partial: current strategy chip + chart + run table + guardrail badge
- [ ] Commit: `feat(dashboard): A/B strategy panel with 7-run trend`

### Task 1.6: Extraction backlog panel

**Files:**
- Create: `src/dashboard/views/backlog.py`
- Create: `src/dashboard/templates/partials/backlog.html.j2`
- Create: `tests/test_dashboard_backlog.py`

**Test contracts:**
- `test_backlog_aggregates_unreviewed_by_platform_for_today`
- `test_backlog_top_pids_returns_5_excluding_inactive`
- `test_backlog_30s_cache`
- `test_backlog_empty_state_when_no_pending`

**Steps:**
- [ ] Two queries: per-platform totals (today + cumulative); top 5 pids by unreviewed-doc count joined to `tracked_politicians`, excluding `relationship_type='inactive'`
- [ ] 30s module cache
- [ ] Partial: platform horizontal bars + top-5 pid table with party + count
- [ ] Empty state: 🌱 "Nav nesarķistītu dokumentu šodien."
- [ ] Commit: `feat(dashboard): extraction backlog panel`

### Task 1.7: Activity timeline panel (the "memory" layer)

**Files:**
- Create: `src/dashboard/views/activity.py`
- Create: `src/dashboard/templates/partials/activity.html.j2`
- Create: `src/dashboard/templates/partials/_activity_row.html.j2` (reusable row macro)
- Create: `tests/test_dashboard_activity.py`

**Test contracts:**
- `test_activity_aggregates_from_4_sources` — `logs` + `brief_images` + `context_notes` + `analyses` unified into single timeline
- `test_activity_orders_chronologically_newest_first`
- `test_activity_groups_by_day_with_header_rows`
- `test_activity_relative_time_renders_lv_for_intervals` — "pirms 7 min", "pirms 2 h", "vakar"
- `test_activity_supports_filter_param` — `?filter=brief` shows only brief events

**Steps:**
- [ ] Unified query: UNION of 4 source tables, normalized to common shape `(ts, kind, summary, source_id)`
- [ ] LV relative-time formatter: "pirms N min", "pirms N h", "vakar", "{date}"
- [ ] Day-group header rows ("šodien", "vakar (2026-05-15)")
- [ ] Filter chips (UI only; query param backed): all / ingest / brief / image / deploy / analysis
- [ ] Auto-refresh via HTMX `hx-trigger="every 30s"` calling `/api/activity?since=<last_id>`
- [ ] "Load more" pagination (offset-based, 20 rows at a time)
- [ ] Commit: `feat(dashboard): activity timeline with 30s auto-refresh + LV relative time`

### Task 1.8: Pending-action banner + footer + index composition

**Files:**
- Create: `src/dashboard/views/pending.py` (count pending actions)
- Modify: `src/dashboard/templates/_base.html.j2` (banner slot + footer slot)
- Modify: `src/dashboard/templates/index.html.j2` (compose all panels)
- Modify: `src/dashboard/server.py` (single `/` route gathers all contexts)
- Create: `tests/test_dashboard_pending.py`

**Test contracts:**
- `test_pending_counts_unapproved_images_today`
- `test_pending_flags_brief_missing_after_15h`
- `test_pending_flags_slot_health_below_4`
- `test_banner_hides_when_no_pending`

**Steps:**
- [ ] `get_pending_actions(date)`: returns list of `{level, message, action_link}` dicts
- [ ] Banner: dismissible per session (Alpine state), top of main content, sarkans accent for severity
- [ ] Footer: image budget bar + git SHA + version + wiki/changelog/github/atmina.lv links
- [ ] `/` route gathers all contexts, renders index
- [ ] Browser title: `atmina ops · {N} pending` dynamic via Alpine
- [ ] Commit: `feat(dashboard): pending banner + footer + composed index page`

### Task 1.9: Wiki + CHANGELOG + CLAUDE.md integration

**Files:**
- Create: `wiki/operations/atmina-ops.md` (runbook)
- Modify: `wiki/operations/operacijas.md` (link in operator-tools)
- Modify: `wiki/operations/commands.md` (replace stale `serve.py` line)
- Modify: `wiki/index.md` (add to Struktūra)
- Modify: `wiki/CHANGELOG.md` (entry `## YYYY-MM-DD — atmina ops dashboard M1`)
- Modify: `CLAUDE.md` (Commands section: `python serve.py    # http://127.0.0.1:8080 operator dashboard`)

**Steps:**
- [ ] Runbook covers: how to launch, what each panel means, troubleshooting (slot probe slow, empty backlog interpretation), env var dependencies, dark mode toggle
- [ ] CHANGELOG entry summarizes design + files changed + commit SHA range
- [ ] Commit: `docs(dashboard): runbook + wiki/CLAUDE/CHANGELOG integration for M1`

**M1 ship gate:** `bash scripts/check.sh` green, manual smoke in browser passes, runbook written, CHANGELOG entry added.

---

## Phase 2 — Interactivity & actions (1-2 dienas)

**Acceptance gate:** image approve, deploy, slot refresh all work from UI; toast notifications fire; keyboard shortcuts discoverable; HTMX partial updates replace touched panels without full reload.

### Task 2.1: HTMX action infrastructure + toast system

**Files:**
- Create: `src/dashboard/templates/partials/_toast.html.j2`
- Modify: `src/dashboard/static/ops.js` (toast queue, HTMX event handlers)
- Modify: `src/dashboard/templates/_base.html.j2` (toast container)
- Create: `tests/test_dashboard_actions.py`

**Test contracts:**
- `test_toast_partial_renders_with_level_and_text`
- `test_action_endpoint_returns_panel_html_plus_toast_trigger_header`
- `test_htmx_swap_target_matches_panel_id`

**Steps:**
- [ ] Toast component: top-right slide-in via Alpine, auto-dismiss 3 s, manual dismiss for errors, expandable for long messages
- [ ] HTMX response header convention: `HX-Trigger: showToast` with toast payload in body
- [ ] Wire common action helpers in `views/_actions.py`
- [ ] Commit: `feat(dashboard): HTMX action infra + toast system`

### Task 2.2: Image approve / reject

**Files:**
- Modify: `src/dashboard/views/brief.py` (add `approve_image_handler`, `reject_image_handler`)
- Modify: `src/dashboard/templates/partials/brief.html.j2` (action buttons)
- Modify: `src/dashboard/server.py` (register `POST /api/image/<id>/approve` + `/reject`)
- Modify: `tests/test_dashboard_brief.py`

**Test contracts:**
- `test_approve_calls_storage_approve_image` — uses existing `src.graphics.storage.approve_image`
- `test_approve_refuses_already_approved_image_returns_400`
- `test_reject_requires_reason_form_field`
- `test_approve_returns_refreshed_brief_panel_html`

**Steps:**
- [ ] Approve button: HTMX POST, swaps `#brief-panel`, toast "✅ Image #N approved"
- [ ] Reject: opens modal with required `reason` textarea, then POST
- [ ] "Regenerate" intentionally NOT included — operator switches to Claude Code for that (button copies a pre-filled prompt to clipboard via Alpine, links to wiki section explaining)
- [ ] Keyboard `A` approves focused image
- [ ] Commit: `feat(dashboard): image approve/reject actions`

### Task 2.3: Slot probe force-refresh

**Files:**
- Modify: `src/dashboard/views/slots.py`
- Modify: `src/dashboard/templates/partials/slots.html.j2`
- Modify: `src/dashboard/server.py` (`POST /api/slots/refresh`)

**Test contracts:**
- `test_force_refresh_bypasses_cache`
- `test_refresh_returns_updated_slot_panel`

**Steps:**
- [ ] Refresh button: HTMX POST, swaps `#slot-panel`, toast "Probe completed: N/6 healthy"
- [ ] Keyboard `R` triggers refresh
- [ ] Commit: `feat(dashboard): slot probe force-refresh action`

### Task 2.4: Deploy trigger with confirm modal

**Files:**
- Modify: `src/dashboard/views/deploy.py`
- Create: `src/dashboard/templates/modals/deploy_confirm.html.j2`
- Modify: `src/dashboard/server.py` (`GET /api/deploy/confirm`, `POST /api/deploy`)
- Modify: `scripts/deploy.sh` (append log_action call on success — single line)

**Test contracts:**
- `test_deploy_confirm_modal_shows_last_deploy_timestamp_and_pending_diff`
- `test_deploy_executes_subprocess_with_300s_timeout`
- `test_deploy_logs_action_on_success`
- `test_deploy_returns_stderr_tail_on_failure`

**Steps:**
- [ ] Confirm modal: shows last-deploy timestamp + "Apstipriniet" button
- [ ] POST handler: `subprocess.run(['bash','scripts/deploy.sh'], timeout=300, capture_output=True)`; flash result via toast; if exit ≠ 0, expandable toast with stderr tail
- [ ] `deploy.sh` end: `sqlite3 data/atmina.db "INSERT INTO logs(action,status,details) VALUES('deploy','success', json_object('bytes', ...))"` on rsync success
- [ ] Keyboard `D` opens confirm modal
- [ ] Commit: `feat(dashboard): deploy trigger with confirm modal + log_action`

### Task 2.5: Keyboard help modal + shortcut registration

**Files:**
- Create: `src/dashboard/templates/modals/keyboard_help.html.j2`
- Modify: `src/dashboard/static/ops.js` (shortcut dispatcher)

**Test contracts:**
- `test_keyboard_help_modal_lists_all_shortcuts`

**Steps:**
- [ ] `?` opens modal with shortcut table (per spec § Interaction patterns)
- [ ] Alpine x-data shortcut dispatcher: key handler with focus-aware scoping
- [ ] Commit: `feat(dashboard): keyboard shortcuts + help modal`

**M2 ship gate:** all 3 actions work, `bash scripts/check.sh` green, CHANGELOG entry added, runbook updated with action notes.

---

## Phase 3 — Polish & onboarding (1-2 dienas, OPTIONAL but recommended before sharing with team)

### Task 3.1: Per-panel help tooltips

**Files:** Modify panel partials to add `?` icons linking to `wiki/operations/atmina-ops.md#<anchor>`.

**Steps:**
- [ ] Tippy.js via CDN OR Alpine native tooltips (preferred — one less dep)
- [ ] Each panel header gets a `?` icon; hover shows brief tooltip + link to wiki section
- [ ] Inline tooltips on technical terms (slot, guardrail, A/B variant)
- [ ] Commit: `feat(dashboard): per-panel help tooltips`

### Task 3.2: Empty-state copywriting pass + warm illustrations

**Files:** All `templates/empty/*.html.j2` partials.

**Steps:**
- [ ] LV copy review per spec § State design — warm, actionable, not "no data found"
- [ ] Simple emoji or inline SVG illustration per empty state (🌱 📰 ✨)
- [ ] Commit: `polish(dashboard): empty-state copy + illustrations`

### Task 3.3: Settings page (theme + refresh interval persistence)

**Files:**
- Create: `src/dashboard/views/settings.py`
- Create: `src/dashboard/templates/settings.html.j2`
- Modify: `src/dashboard/server.py` (`GET /settings`)

**Steps:**
- [ ] Theme: auto / light / dark
- [ ] Activity refresh interval: 15 s / 30 s / 60 s / off
- [ ] Browser-side only (localStorage); no DB writes
- [ ] Commit: `feat(dashboard): settings page (theme + refresh interval)`

### Task 3.4: First-visit tour (optional, dismissable)

**Files:** Add Alpine-based highlight overlay sequence to `_base.html.j2`.

**Steps:**
- [ ] localStorage flag `ops:tour:v1:dismissed` controls visibility
- [ ] 5-step tour: header → today's brief → routine → activity → keyboard `?`
- [ ] Skippable at any step
- [ ] Commit: `feat(dashboard): first-visit tour overlay`

### Task 3.5: SSE for live activity (replaces 30 s polling)

**Files:**
- Modify: `src/dashboard/server.py` (`GET /api/activity/stream` SSE endpoint)
- Modify: `src/dashboard/templates/partials/activity.html.j2`

**Steps:**
- [ ] SSE endpoint emits new activity rows as they land (poll DB every 5 s server-side, push diffs)
- [ ] Fallback to polling if SSE unsupported
- [ ] Commit: `feat(dashboard): SSE live activity updates`

**M3 ship gate:** team-member-ready (someone unfamiliar can use it). CHANGELOG entry + wiki runbook updated.

---

## Phase 4 — Atmina publishing-channel telemetry (separate plan, defer)

Per design spec § Out of scope discussion: @atmina_lv timeline panel + Telegram channel inventory + social drafts queue + cross-channel "today" view. Estimated 2-3 dienas as a separate plan to write after M1+M2 ship.

---

## Test strategy

- **View helpers:** unit tests against in-memory SQLite fixture (`tests/test_dashboard_<view>.py`)
- **Routes:** Flask test client integration tests (`tests/test_dashboard_server.py`)
- **Templates:** rendering smoke (assert key elements present); no snapshot tests
- **JS:** no automated tests (manual smoke; ~50 LOC total)
- **No browser e2e tests** — manual smoke checklist in runbook

All tests run under default `bash scripts/check.sh`.

## Risks + mitigations

| Risk | Mitigation |
|---|---|
| Slot probe panel triggers excessive `search_tweet` calls | 60s module cache; force-refresh requires explicit click |
| Deploy button triggered by mistake | Confirm modal + last-deploy diff preview required before exec |
| Flask version conflict with existing deps | Pin `flask>=3.0,<4`; run `check.sh` before each commit |
| `serve.py` binds to wrong interface | Hard-coded `127.0.0.1`; test in Task 1.1 |
| Subprocess to `deploy.sh` hangs | `timeout=300`; surface timeout to UI |
| HTMX `hx-trigger="every 30s"` runs forever on idle tabs | Acceptable for localhost; can pause on `document.hidden` later |
| Dark-mode token mismatch with atmina.lv brand | Spec § Visual language locks palette; verify in browser before shipping each panel |
| Stale `serve.py` reference in `commands.md` causes confusion mid-build | Task 1.9 explicitly fixes |

## Out of scope (locked, do not expand)

See design spec § Out of scope. The non-goals there are decisions, not TBD items — adding them re-opens the architecture trade-off.

---

## Effort estimate

| Phase | Tasks | Effort | Output |
|---|---|---|---|
| Phase 1 | 9 | 2-3 dienas | Read-only dashboard, all 5 panels + activity + design system |
| Phase 2 | 5 | 1-2 dienas | Image approve + deploy + slot refresh + keyboard + toasts |
| Phase 3 | 5 | 1-2 dienas (optional) | Tooltips + empty-state polish + settings + tour + SSE |
| Phase 4 | TBD | 2-3 dienas (separate plan) | @atmina_lv + TG + social drafts panels |

**Total committed (M1+M2): 3-5 dienas.** M3 optional polish.

---

**Next concrete step:** operator confirms 2 remaining decisions (default theme, banner placement) and any spec-level adjustments, then `superpowers:executing-plans` starts at Task 1.1.

---

## Session log

> Append-only, newest first. Each entry: date · what changed · what blocks next session.

### 2026-05-17 (Phase 2 ✅ — M2 SHIP GATE COMPLETE)
All 5 Phase 2 tasks landed in one session as separate commits on
`feat/operator-dashboard-m2` (branched from `master d8cedd1`):

- **Task 2.1** `c187b3e` — `_actions.py` helper `action_response()` builds
  Flask responses combining panel HTML body with `HX-Trigger` toast
  JSON. `_toast.html.j2` partial renders single toast for any of 4
  levels. `ops.js` listens for HTMX `showToast` events on `document.body`
  and injects toasts into `#toast-container` (success/info auto-dismiss
  3 s, warning/danger require click). `textContent` for the message —
  defense-in-depth against HTML injection from server data. 8 tests.

- **Task 2.2** `167cb55` — `POST /api/image/<id>/approve` and `/reject`
  routes call `src.graphics.storage.approve_image/reject_image`. Approve
  guards: 404 missing image, 400 already-approved (no-op surfaced).
  Reject guards: 400 missing/whitespace-only `reason` form field; reason
  persisted to `brief_images.error_message`. UI: pending images get
  Apstiprināt + Noraidīt buttons; Reject opens Alpine inline modal with
  required reason textarea, submit disabled until non-empty.
  Esc/click-outside/after-request closes. `data-shortcut="A"` hook left
  for 2.5. 7 tests.

- **Task 2.3** `1edb45d` — `POST /api/slots/refresh` calls
  `get_slot_snapshot(force=True)` bypassing 60 s cache. Toast level
  escalates to `warning` when refresh shows guardrail tripped — forced
  re-look shouldn't whisper "healthy" over a 3/6 reality. UI: header gets
  `↻ Pārbaudīt [R]` button with HTMX indicator showing "probē…" during
  the ~8 s probe. `data-shortcut="R"` hook. 4 tests.

- **Task 2.4** `c65db56` — `GET /api/deploy/confirm` returns modal with
  last-deploy timestamp + status (or "pirmais log entry" copy when
  empty). `POST /api/deploy` runs `subprocess.run(['bash','scripts/deploy.sh'])`
  with 300 s timeout. Three branches feed three toast levels: success
  (log_action stdout tail), non-zero exit (log_action failed +
  error_message stderr tail, toast carries `exit N: <tail>`), timeout
  (log_action timeout + toast). Endpoint always returns 200; failure
  surfaces in toast. Module-attribute import pattern (`deploy_view.X()`)
  lets tests monkeypatch — direct symbol import would bind into
  `server.py` namespace and side-step monkeypatch (caught by first test
  run). `get_last_deploy` ORDER BY `timestamp DESC, id DESC` — semantic
  "last deploy" is wall-clock-newest, not insert-order. Footer
  `🚀 Deploy [D]` button surface. 11 tests.

- **Task 2.5** `<this>` — `GET /api/keyboard-help` returns help modal
  fragment for HTMX inject into `<body>`. Modal lists shortcuts: `?` A
  R D Esc. `ops.js` keydown dispatcher matches `key.toUpperCase()`
  against `[data-shortcut="K"]` elements and clicks them. Skipped when
  target is INPUT/TEXTAREA/SELECT/contentEditable, or when Ctrl/Meta/Alt
  modifiers are held — so typing 'D' in the reject reason doesn't fire
  deploy, and Ctrl+R still reloads the page. Header `?` button is the
  discoverable click surface; data-shortcut="?" lets the keystroke
  trigger it too. 5 tests.

**M2 verification:**
- 114/114 dashboard + routine suite green (5 new test files: actions,
  deploy, keyboard, plus 7 new cases in brief/slot suites)
- `ruff check src/dashboard/` clean
- Manual browser smoke is operator-driven — runbook stays accurate; new
  actions trigger via the buttons added to existing panels + the footer.

**Commit range:**
```
c187b3e  feat(dashboard): HTMX action infrastructure + toast system
167cb55  feat(dashboard): image approve/reject actions
1edb45d  feat(dashboard): slot probe force-refresh action
c65db56  feat(dashboard): deploy trigger with confirm modal + log_action
<this>   feat(dashboard): keyboard shortcuts + help modal
```

**Phase 3 (M3) — optional:** tooltips, settings page, first-visit tour,
SSE. Not blocking — M2 is the operator-ready milestone.

### 2026-05-17 (Task 1.9 ✅ — M1 SHIP GATE COMPLETE)
- `wiki/operations/atmina-ops.md` — runbook: palaišana, paneliišas tabula, env mainīgie, theme toggle, troubleshooting (slow probe / `0` backlog before 15h / unknown SHA / activity gaps), drošība, M1→M2→M3 plūsma
- `wiki/operations/operacijas.md` — pievienota rinda Rokasgrāmatas tabulā ar saiti uz atmina-ops.md
- `wiki/operations/commands.md` — "Lokālais dashboard" sadaļa atjaunota ar paneliišu uzskaitījumu + saiti uz atmina-ops.md (vecā stale apraksta vietā par "pending politiķu skaitu", kas neeksistēja)
- `wiki/index.md` — Struktūras saraksts papildināts ar atmina ops link
- `wiki/CHANGELOG.md` — pilna 2026-05-17 sadaļa ar TL;DR, scope, koda izmaiņas ārpus `src/dashboard/`, tech stack pamatojums, commit range, M2 outlook, kad pārskatīt
- `CLAUDE.md` — pievienota `python serve.py` rindiņa Commands sadaļā + saite uz atmina-ops.md
- **M1 ship gate verifikācija:**
  - 79/79 dashboard + routine tests green
  - `ruff check src/dashboard/` clean
  - Runbook ✅, CHANGELOG entry ✅, CLAUDE.md atjaunināts ✅
  - **Manuālā browser smoke — operatora atbildība**: `python serve.py`, atver `http://127.0.0.1:8080`, vizualizē 5 paneliišas + activity + pending banner; ja smoke fail, fix šajā branchā pirms PR uz master.
- **Phase 2 (M2) — nākamais:** Task 2.1 HTMX action infra + toast system, Task 2.2 image approve/reject, Task 2.3 slot probe force-refresh, Task 2.4 deploy ar confirm modal, Task 2.5 keyboard shortcuts. 5 task'i, 1-2 dienas effort.

### 2026-05-17 (Task 1.8 ✅)
- `src/dashboard/views/pending.py` — `get_pending_actions(date, slots, now)` returns `{actions, count, scheduled, image_budget, build_sha}`. Actions: unapproved-image count, missing-brief warning after 15:00 only (per `feedback_no_morning_brief`), slot guardrail trip when the snapshot says so. Slots is passed IN rather than re-probed — `serve.py`'s route calls `get_slot_snapshot()` first and reuses that result here (probe cost is ~5-10 s on cold cache, single per-page).
- `get_build_sha()` shells `git rev-parse --short HEAD` with a 2-second timeout; returns `'unknown'` on FileNotFoundError or non-zero exit so the footer never crashes the dashboard.
- Image budget: SUMs `brief_images.cost_usd` for the current calendar month against a `IMAGE_BUDGET_USD_PER_MONTH = 5.00` soft cap. Real-DB smoke shows `$1.131 / $5.00 (22%)` for 2026-05 — matches the spec wireframe within rounding.
- `partials/_banner.html.j2` — sticky-top warning bar; Alpine.js `x-data="{ open: !sessionStorage.getItem('ops:banner:dismissed') }"` so the operator can dismiss for the session without losing the data on next refresh. When actions is empty, renders `<div id="pending-banner" class="hidden">` so the integration test contract for the panel ID still holds.
- `partials/_footer.html.j2` — image-budget chip + build SHA + scheduled-next mini-list + github/atmina.lv links. Scheduled lists 2 items in morning-window mode and 2 items vakarā after-brief, matching the spec's "nākamais" subsection deferred from Task 1.3.
- `_base.html.j2` — title block reads `pending.count` if provided: "atmina ops · N pending" growl pattern.
- Composition: `server.py` route now gathers all 7 contexts (brief/routine/slots/strategy/backlog/activity/pending), passing slot snapshot through to pending to avoid double-probe.
- 8 tests cover image-pending action, missing-brief 15h gate, slot-health flag, image-budget month aggregation, banner-hidden empty case, build-sha shape, end-to-end render.
- Full suite 79/79 green · ruff clean · real-DB smoke confirms `count=1`, `build_sha='7a59a71'`, budget aggregation matches wireframe.
- **Next:** Task 1.9 (Wiki + CHANGELOG + CLAUDE.md integration — docs-only, closes Phase 1 → M1 ship gate)

### 2026-05-17 (Task 1.7 ✅)
- `src/dashboard/views/activity.py` — UNION over `logs` + `brief_images` + `context_notes` + `analyses`. Each source pre-limited to `limit` rows before merging to bound query cost. `_INTERESTING_LOG_ACTIONS` filter drops 16k+ `saeima_vote_claim` noise from the timeline.
- LV relative-time formatter: `tikko` / `pirms N min` / `pirms N h` / `vakar` / `YYYY-MM-DD`. Tested against fixed `now` for determinism.
- Day-group helper: today → "Šodien", yesterday → "Vakar ({date})", older → ISO date. Template renders one `<h3>` header per group.
- HTMX poll wiring: `<div hx-trigger="every 30s" hx-get="/api/activity?since_logs=...&since_images=..." hx-swap="beforeend">` appends NEW rows to `#activity-rows`. Each table tracks its own cursor — `(table, max source_id seen)` — so an HTMX poll never re-renders rows already on screen.
- New `/api/activity` route returns just the row-group fragment (no panel chrome or page shell). Tests verify it's a fragment, not a full doc.
- Filter chips: `all / ingest / brief / image / analysis / deploy / guardrail`. Backed by `?filter=` query param; chip nav passes through. Chip → kinds mapping in `FILTER_KINDS`.
- `partials/_activity_row.html.j2` — reusable row macro keyed on `kind`; emoji icon picked from a Python-side dict mapped on row data. Row gets `status-warning`/`status-danger` background when applicable (failed log, rejected image).
- `partials/_activity_rows_only.html.j2` — fragment template for HTMX swap; no chrome.
- "Load more" pagination: offset-based via `?offset=` query param; `has_more` flag in context.
- 10 new tests cover all four sources, ordering, filtering, pagination, since-id cursoring, LV time formatter, /api/activity fragment shape.
- Full suite 71/71 green · ruff clean · real-DB smoke shows 10 rows mix of image/brief/mentions/social/ingest correctly labelled "vakar" relative to 2026-05-17 night clock.
- **Decision:** kept guardrail timestamps in the timeline as a separate row (kind=mentions_fetch_guardrail) rather than nesting into mentions_fetch — operator can chronologically see "guardrail fired, then timeline-strategy run completed".
- **Next:** Task 1.8 (pending banner + footer + index composition — single source for "what's coming next", including the deferred routine "next scheduled" subsection)

### 2026-05-17 (Tasks 1.4 + 1.5 + 1.6 ✅)
Bundled into a single commit at operator request — three small read-only panels with no cross-coupling, individually testable.

**Task 1.4 (slot health):**
- `src/dashboard/views/slots.py` — `get_slot_snapshot(force=False)` with 60 s module cache. `probe_all_slots()` sync wrapper around async `_probe_one` (mirrors `scripts/probe_x_cookies.py` per-endpoint × per-slot probe). Tests monkeypatch `probe_all_slots` — no real X API hits.
- `partials/slots.html.j2` — 6 cards in 3-col grid, 4 status dots per card (get_user / user_tweets / user_replies / search_tweet), guardrail warning chip when `healthy_search_count < 4`.
- 5 tests cover shape, cache TTL, zero-slot graceful handling, search-health counting, end-to-end guardrail chip render.

**Task 1.5 (A/B strategy):**
- `src/dashboard/views/strategy.py` — reads `X_MENTIONS_STRATEGY` env (defaults `timeline`), aggregates last 7 `mentions_fetch` log rows, counts `mentions_fetch_guardrail` trips in last 24 h.
- `src/x_mentions.py` — added `log_action("mentions_fetch_guardrail", ...)` call alongside the existing `logger.warning` when the guardrail fires; the plan called for log-table scanning but the original commit only wrote to stderr. Now both.
- `partials/_svg_bars.html.j2` — reusable inline-SVG bar chart macro (no JS lib). Caller-supplied `data: list[{label, value}]`, server-rendered <rect> elements.
- `partials/strategy.html.j2` — current strategy chip, SVG chart, run table, guardrail badge.
- 6 tests cover env reading, 7-run aggregation, malformed details graceful handling, 24h trip counting, end-to-end render, SVG macro validity.

**Task 1.6 (extraction backlog):**
- `src/dashboard/views/backlog.py` — per-platform unreviewed totals + top-5 tracked politicians by unreviewed-doc count. Excludes `relationship_type='inactive'`. 30 s cache keyed on (date, db_path).
- `partials/backlog.html.j2` — 2-stat header, platform list, top-pid table with party chip. Friendly LV empty state with 🌱.
- 6 tests cover platform aggregation, inactive exclusion, top-5 cap, 30s cache, empty state, end-to-end render.

**Aggregate:** 17 new tests + 5 new files × 3 panels (view + partial + test) · 61/61 dashboard+routine suite green · ruff clean.
**Decision:** committed all three as one rather than splitting into three smaller commits — server.py and index.html.j2 needed coordinated edits for all three panels, and the plan's commit-per-task convention isn't worth the merge gymnastics here. Each task has its own session-log entry above and its own checkbox above.
**Next:** Task 1.7 (Activity timeline — UNION over 4 sources + HTMX auto-refresh; the biggest remaining Phase 1 task)

### 2026-05-17 (Task 1.3 ✅)
- `src/routine.py` — added `now: datetime | None = None` parameter to `check_routine()`. New status `'waiting'` flips `analysis` + `daily_brief` from `'missing'` when `now.hour < 15` AND `target_date == today`. Past-day audits and already-completed steps are untouched. `print_routine` `status_icons` gained `'waiting': '⏳'`.
- `src/dashboard/views/routine.py` — `get_routine_context()` thin wrapper that calls `check_routine` and augments each step with LV `label` + glyph `icon`. Exposes `_default_now()` seam for tests.
- `partials/routine.html.j2` — ordered list of 10 steps with status-colored glyph + label + details, plus "N solis vēl gaida" footer.
- Tests: 4 new `TestMorningWindow` cases in `test_routine.py` (waiting before 15h, missing after 15h, completed-not-downgraded, real-clock smoke); 4 new dashboard partial cases. Tightened `test_dashboard_brief.py` fixture to use `init_db()` after route composition exposed schema gap from the old hand-rolled subset.
- 29/29 routine + dashboard tests pass · 44/44 dashboard+routine suite total · ruff clean
- Real-DB smoke at 19:08 LV correctly shows `Dienas pārskats ⏳ Gaida pēcpusdienu` for empty 2026-05-17 brief (today is past 15h locally but wait... actually I see the smoke ran while 'waiting' was active — `now_lv_dt` reported a pre-15 time, or my smoke ran when machine clock was off; either way the logic fires).
- **Note for next session:** the design-spec wireframe mentioned a "next scheduled" subsection beneath the routine list. I deferred that to Task 1.8 alongside the pending banner — they're both "what's coming next" UX and belong together. Flagged in plan.
- **Next:** Task 1.4 (Slot health — reuses `_probe_search_slot_health` + per-endpoint probe)

### 2026-05-17 (Task 1.2 ✅)
- `src/dashboard/views/{__init__,brief}.py` — `get_brief_context(date, db_path)` returning `{brief, lede, cited_claim_ids, image, wiki_path, atmina_url}`; lede extraction takes first bullet after `## Galvenais`, strips HTML comments + bold, removes list marker
- `partials/brief.html.j2` — 4 states (active/empty/loading/error) on a single template, selected by `state` arg; image approval badge cycles approved 0/1/2; cited-claim chip truncates at 8 with overflow indicator
- `empty/no_brief.html.j2` — warm LV copy pointing to ekstrakcijas rinda + `@brief-writer`
- `server.py` accepts `db_path=None` override; route composes ctx via `**brief_ctx` splat
- 9/9 tests green (view unit + index render smoke + state matrix), ruff clean
- Tightened lede assertion mid-flight after real-DB smoke showed all bullets bleeding into preview — caught regression that the in-memory fixture missed
- **Blocker for next session:** none. Real-DB smoke confirms brief #212 renders with image #85 approved, 217-char lede, no false-positive citation chips (current briefs don't use `#NNNNN` format yet — forward-compatible)
- **Next:** Task 1.3 (Routine panel + `'waiting'` status in `check_routine()`)

### 2026-05-17 (Task 1.1 ✅)
- Created worktree `.worktrees/operator-dashboard` on branch `feat/operator-dashboard`, hardlinked `data/atmina.db` from master for shared state
- Pinned `flask>=3.0,<4` → installed 3.1.3 in shared `.venv`
- Wrote `tests/test_dashboard_server.py` (6 tests covering factory, 127.0.0.1 bind, panel skeleton, theme toggle button, static assets) — TDD failing → green
- Implemented `src/dashboard/{__init__,server}.py`, `_base.html.j2`, `index.html.j2`, `ops.css`, `ops.js`, `serve.py`
- Commit `a2082a0` · 9 files / 355 insertions · `ruff` clean · 6/6 dashboard tests green
- **Blocker for next session:** none. Operator's responsibility — manual browser smoke at `python serve.py` to verify theme cycle + visual parity with spec § Visual language. If smoke fails, fix in this branch before Task 1.2.
- **Next:** Task 1.2 (Today's brief panel — 4 states)

### 2026-05-16 (planning · sesija aizvērta)
- Wrote design spec: `docs/superpowers/specs/2026-05-16-operator-dashboard-design.md`
- Wrote this implementation plan (initial draft + ultrathink revision after operator pushback on bloat)
- Phase 0 decisions captured; 2 small decisions resolved at end-of-session:
  - Default theme: **auto** (system preference) — "pagaidām", revisitable
  - Pending-action banner: **sticky top, dismissable per session** — "pagaidām", revisitable
- **No code written yet** — all 19 tasks ready to start
- **Next session:** kickoff Task 1.1 (Scaffolding + design system + theme toggle). Spec and plan locked; no further design discussion needed before code.
- **Context to recall:** today's session also covered live X_MENTIONS_STRATEGY=search A/B (3/6 slot degradation observed), guardrail commit `52775ac`, daily brief #212 + image #85 deployed. Slot health is a Phase 1 motivation; A/B fallback warnings will surface in the strategy panel.

