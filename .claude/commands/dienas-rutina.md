---
name: dienas-rutina
description: Drive the atmina.lv daily routine — status check, afternoon analysis fan-out, contradiction + devils-advocate pass, brief (human-gated), narrow render + --no-delete deploy. Encodes the timing + publish-pause + LV-style guardrails.
argument-hint: "[YYYY-MM-DD] (defaults to today)"
---

# Dienas rutīna — atmina.lv

> **Pass/fail kritēriji dienas pārskatam — [`wiki/operations/quality-bars.md`](../../wiki/operations/quality-bars.md). Izlasi PIRMS glabāšanas/publicēšanas, ne pēc.** CLAUDE.md § Quality Bars sauc šo failu par kanonisko nesēju; līdz 2026-08-09 uz to saistīja 1 no 17 nesējiem.

Orchestrate today's routine. **Canonical state first**, then editorial steps. Respect the guardrails below — they encode prior incidents, not preferences.

## 0. Status

```bash
.venv/Scripts/python.exe -c "from src.routine import print_routine; print_routine()"
```

**Never bare `python`** — on the operator machine it resolves to a foreign venv, and the failure mode is a PARTIAL WRITE, not a clean error (CLAUDE.md § Commands).

Read `wiki/index.md` for backlog/folder contract. The 10 steps live in `src/routine.py`; the agents in `.claude/agents/*.md`.

## Timing guardrails (HARD)

- **Ingest runs all day.** A morning "0/N analizēti" is EXPECTED, not a backlog warning (CLAUDE.md § Standing Decisions — Timing).
- **Analysis + brief are afternoon-only (≥15:00 LV).** Do NOT dispatch `@brief-writer` or run extraction before ~15:00 — 2026-05-15 incident: a brief dispatched before noon was rejected.

## Steps (afternoon)

1. **Ingest** — confirm new documents landed (step shows count). Don't force it in the morning.
2. **Pozīciju analīze** — fan out `@claim-extractor` in **parallel sub-agents, batched by queue volume** (operator decision 2026-08-19): politicians with small queues (≤2 docs) MAY share one sub-agent up to ≈8 docs total (amortizes the 48 KB prompt); a politician with a larger queue gets their own agent. Each claim still carries its own politician's `opponent_id` — cross-attribution inside a shared agent is the batch failure mode to watch. Sub-agent contexts are clean, so they bypass the ~8-politician main-context diacritic-drift limit — scale wide (CLAUDE.md T4). Circuit breakers: cap batch size (≈12 docs / 12 politicians) + the `NEEDS_REVIEW` gate to avoid indirect-reference saves (kanoniskie noteikumi: `.claude/agents/claim-extractor.md`). Every claim needs a `source_url` or it is dropped — and the drop IS reported, as a `missing_source_url` entry in `save_analysis()`'s returned `failures` with `status="partial"`. It goes to stderr and never raises, so it is easy to miss but not silent: read `failures` and treat every entry as a real lost claim (T3).

   **Divi pastāvīgi soļi (institucionalizēti 2026-08-20 pēc 08-17 eksperimentiem + 08-19 pilnā palaidiena):**
   - **±5 d aģentūras dublikātu pārbaude — katrā dispatch promptā.** Pirms glabāšanas aģents pārbauda `get_existing_claims(pid, days=5)` — tas pats izteikums no cita avota jau glabāts → NEGLABĀ, piemin atskaitē (logs ±5 d ir operatora lēmums 2026-08-18; ±2 d bija par šauru — Sprūda #689743 izslīdēja). Zināmās robežas: neiet RT-skip slotos un neredz cita pid dublikātus. 08-19: ≥5 reāli dublikāti noķerti, 0 FP.
   - **Junction-atgūšana PĒC ekstrakcijas (orkestratora solis).** Citētie runātāji ar `role='mentioned'` nekad neienāk `get_pending_politicians` rindā (reviewed_at ir per-dokumenta) — pēc galvenā fan-out palaid citēto `mentioned` pāru caurskati un dispatchē atgūšanas aģentu atrastajiem. NB: `pending_quoted_mentioned(days=1)` filtrs ir par šauru (08-17 deva 0, kamēr plašais ekspozīcijas vaicājums 50 pārus) — lieto plašāku logu/vaicājumu. 08-17 raža: 4 pozīcijas no 16 pāriem.

   **Model pin — pass it explicitly on every fan-out.** All project agents carry `model: opus` in frontmatter, but that pin does **not** reach a plain `agentType: 'general-purpose'` call, and sub-agents must never inherit a Mythos-tier session model (CLAUDE.md § Standing Decisions, operator decision 2026-07-21). When dispatching via `Workflow`/`agent()`, pass `model: 'opus'` on each call; when dispatching a named project agent via `Agent`, the frontmatter pin covers you. Orchestration itself may run on any tier.
3. **Pretrunu pārbaude** — for each new claim, `search_similar_claims` with a directional `claim_type_filter`; store via `store_contradiction()` (defaults `confirmed=0` — unpublished until you manually UPDATE). Also check rhetoric-vs-action. See `/deep-check` for the deeper fan-out. **Pēc medību pabeigšanas — arī pie 0 atradumiem — pieraksti izpildes pēdu** (`store_contradiction` raksta tikai atradumus; bez šīs rindas godīgā nulle nav atšķirama no „netika palaists", un `_check_contradictions` ziņos `missing`):
   ```bash
   .venv/Scripts/python.exe -c "from src.db import log_action; log_action('contradiction_hunt', details={'date': '<YYYY-MM-DD>', 'claims_checked': <N>, 'found': <M>})"
   ```
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

## Quality gate (HARD — before render, not after)

Run `bash scripts/check.sh`, then dispatch **`@quality-reviewer`** over the day's output. CLAUDE.md § Quality Bars names both as the render+deploy carrier and calls the reviewer a hard gate: it is the last check on data integrity, source links, completeness and neutrality before anything reaches the public site. A green `check.sh` alone does not clear this step — it validates the build, not the editorial content.

**Past midnight, tell the reviewer which day it is reviewing.** Its first code block binds `ROUTINE_DAY = today_lv().isoformat()` and every check keys off it. When the routine finishes after 00:00 LV — which is normal, 26 of 130 stored briefs have a subject day that differs from their `created_at` day — the calendar day is no longer the routine day, and the reviewer would look at a day whose work does not exist yet. Say the covered date explicitly in the dispatch (`ROUTINE_DAY = '2026-08-14'`), the same way `check_routine(target_date)` takes it. Two related behaviours since 2026-08-15, both deliberate: the reviewer resolves the brief through `src.routine._daily_briefs_for()` (subject date, not `created_at`), and a **missing brief is now a FAIL, not a silent pass** — if it reports "pārskats nav atrasts" on a day you did run the routine, the day you passed it is wrong, not the brief.

## Render + deploy

- Identify the changed domains and render narrowly: `.venv/Scripts/python.exe -m src.render --only=DOMAIN1,DOMAIN2` (full path only for release/baseline regen — `feedback_render_narrow_scope`). **After approving the featured image, the render MUST include `dashboard`** — the landing page and `analizes.html` listing cards live in that domain, so a `blog`-only re-render publishes a brief whose image shows only on the brief page itself (bitten live 2026-08-18). **Always include `static`** — `about.html`'s corpus figures and `sitemap.xml` are emitted by that domain alone, so omitting it silently publishes stale counts and a sitemap missing the day's brief (~5s; 2026-08-01 audit found about.html three days stale).
- **Pēc korektūras un operatora atļaujas — ieraksti publicēšanas karogu:** `.venv/Scripts/python.exe scripts/approve_publish.py <YYYY-MM-DD>` (nedēļas pārskatam `nedela-<YYYY-MM-DD>`). Kopš 2026-08-18 deploy preflight prasa `publish_approvals` rindu KATRAI `blog/` pārskata lapai — attēla apstiprinājums vairs nav pietiekams, jo tas pierāda tikai hero izvēli, ne to, ka teksts drīkst iet ārā. Bez rindas deploy apstājas ar `publish-gate: ... nav publicēšanas apstiprinājuma`. Atsaukšana: `--revoke`. Atļauja der vienam publicējumam — pārģenerēts brief tajā pašā dienā PATUR rindu (atslēga ir lapas slugs), tāpēc pēc būtiskas pārrakstīšanas atsauc un apstiprini no jauna.
- Deploy with **`bash scripts/deploy.sh --no-delete`** (standing mode — the local tree may be a partial build; `--delete` would wipe curated/server-only pages). Dry-run first: `deploy.sh --dry-run --no-delete`.
- **New EXTERNAL resource host → CSP allowlist, or it dies silently on the live site.** The live `script-src` has no `'unsafe-inline'`, and every external host (script, style, font, image, `connect`) must be added to the allowlist in `assets/htaccess.template`. Local preview serves no headers, so it **cannot** catch this — the resource simply fails in the browser after deploy, with no build error and no test failure. Two tests cover the source side: `tests/test_no_inline_js.py` (inline-JS half, all 36 templates + curated pages) and `tests/test_csp_external_hosts.py` (external-host half — since 2026-08-15 it also scans `curated/` and the vendored `assets/cuelume/`, which it previously skipped). Neither can verify the LIVE headers or a host that only appears at runtime, which is why the manual confirmation below stays in this checklist. If today's render touched a template, a curated page or `assets/*`, confirm no new external host appeared before deploying, and verify it live after (CLAUDE.md § No inline JavaScript).
