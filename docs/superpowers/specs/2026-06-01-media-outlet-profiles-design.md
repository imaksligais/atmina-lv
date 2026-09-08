# Media Outlet Profiles — Design Spec

_Date: 2026-06-01_

## Goal

Add even-handed, evidence-based **media-outlet transparency profiles** + **descriptive coverage tracking** to atmina.lv — analogous to the existing politician/party profiles, but for media outlets (LSM, Delfi, Neatkarīgā/NRA, TVNet, LETA, Diena, Latvijas Avīze, Jauns.lv, LTV programs, TV3 Ziņas, IR, etc.).

**Ethos: transparency, not targeting.** Every transparency fact is sourced; coverage is descriptive and computed from data; metrics are symmetric across all outlets and all parties; there are **no `corrupt` / `bought` / `attacking` / `biased` labels** anywhere. This is the only way the feature stays credible and survives scrutiny — a one-sided "expose the corrupt media" framing would discredit the whole platform and was explicitly rejected.

## Scope (v1)

- **Outlets only** (institutions) — not individual journalists/commentators.
- **Descriptive coverage only** — no tone, sentiment, or bias scoring.
- **Roster:** the ~13–15 outlets already present in `sources.yaml` / `documents`.
- The existing editorial-`framing:` characterization in `sources.yaml` **stays internal** (it remains an `@claim-extractor` confidence signal; it is not published on the outlet pages).

## Non-goals (v1)

- No framing/bias layer on the public site (deferred to phase 2, and only with a published, symmetric rubric).
- No individual-journalist profiles (later phase).
- No recurring automation / daemon.
- No migration or deactivation of the existing `tracked_politicians` media rows.
- No new DB tables.

## Key findings that shaped this design

1. **`sources.yaml` already is the outlet registry** — every outlet is there with `name`, host URL, `tier`, `legal_status`, `legal_notes`, and an even-handed `framing:` description. The `sources` DB table is loaded from it. → The registry is config, not new schema.
2. **Coverage is fully derivable from existing data.** Validated on the live DB: `documents.source_domain` (normalized) `JOIN document_politicians JOIN claims` already yields "which outlet covered which politician / party / topic, with links" — no new scraping, no new storage. Example (LSM, 1,058 web articles): top-covered Siliņa (101)/Sprūds (53)/Rinkēvičs (52); by party JV 135 / PRO 80 / ZZS 53 …; top topics Aizsardzība un drošība (25)…
3. **`parties` table + `src/render/parties.py`** are the exact precedent for the outlet entity + render module.
4. Media actors today are crammed into `tracked_politicians` (`relationship_type IN ('journalist','organization')`, 15 + 3 rows) — a mix of outlets and individuals, fed via `social_accounts` (X). v1 leaves these untouched.

## Architecture (config-driven, zero new DB tables)

### Registry — extend `sources.yaml`
- Tag each existing feed with `outlet: <short_name>` so per-feed rows group into one outlet (LSM Latvija + LSM Ekonomika → `lsm`; Diena Latvijā + Viedokļi → `diena`; NRA + NRA Viedokļi → `nra`).
- Add a top-level `outlets:` block — one entry per outlet:
  - `short_name`, `name`, `type` (`public_tv` / `private_tv` / `radio` / `print` / `agency` / `online`), `language` (`lv` / `ru` / `lv,ru`), `hosts: [domains]`, `x_handle`, `website`, `description`.
  - `facts:` — a list of `{field, value, source_url, as_of}` for `owner`, `funding_model`, `legal_form`, `editorial_leadership`, `founded`. **Each fact carries its own `source_url`; unsourced facts are omitted** (mirrors the `claims` "no source_url → dropped" rule). `as_of` records when the fact was last verified.

### Reader — `src/outlets.py`
- Pure read of `sources.yaml` → `list[Outlet]` (groups feeds, exposes `hosts`, `facts`, identity). No DB writes. Mirrors how `sources.yaml` is already consumed for the `sources` table.

### Coverage — render-time, single pass
- Grouped by outlet via `documents.source_domain` (normalized: strip leading `www.`), or via `documents.source_id → sources → outlet` if `source_id` proves reliably populated (verify during planning).
- **One-pass `GROUP BY` queries across all outlets** — not per-outlet N+1 (the codebase explicitly refactored away from N+1 in `_compute_brief_footers`; the claims-index regression went 5s→16min). Add `idx_documents_source_domain`.
- Metrics per outlet:
  - **Volume** — article count (web), for a stated period + all-time.
  - **Who they cover** — top politicians (name + party), excluding the canonical audience roles using the *same* set `blog.py::_FOOTER_POSITION_EXCLUDED_ROLES` (journalist, influencer, neutral, inactive, commentator, organization).
  - **Coverage by party** — **share** (not raw count), shown alongside the **cross-outlet average** so incumbency (the governing parties get covered more — normal newsworthiness) is not misread as bias. Page states the period and that one article can tag multiple parties (shares are of tags, not articles).
  - **Top topics** — via `claims.document_id → topic` (already normalized to the 31 canonical groups).
  - **Recent articles** — latest N with source links + dates.
  - Any coalition-vs-opposition split derives from `parties.coalition_status` via `src.coalition.party_status()` — never inferred (CLAUDE.md #10).

## Rendering & site integration

- **New:** `src/render/mediji.py` mirroring `parties.py` — `_fetch_outlets_page()`, `_fetch_outlet_detail()`, `render_mediji()`.
- **New templates:** `templates/mediji.html.j2` (index) + `templates/medijs.html.j2` (detail), reusing existing party/profile CSS.
- **`src/render/_orchestrator.py`:** import the render fns; add `"mediji"` to `KNOWN_DOMAINS`; pre-fetch outlets (so sitemap reuses them); `if _want("mediji"): render_mediji(...)`; add to the console summary; sitemap += `mediji.html` and a `mediji/<slug>.html` loop.
- **`templates/base.html.j2`:** one nav link `Mediji` → `mediji.html` after `Partijas` (`active_page == "mediji"`).
- **URLs:** `mediji.html` + `mediji/<slug>.html` (slug = `short_name` lowercased), mirroring `partijas/`.
- **Index extras (descriptive-safe):** a "media landscape" overview chart (outlets by volume / coverage share) rendered with the existing deterministic-SVG approach (`weekly_chart.py`-style — no new dependency); cross-links between outlet pages and politician/party pages.

## Seeding the facts — `@outlet-researcher`

- **New agent prompt** `.claude/agents/outlet-researcher.md`, run **on demand, one outlet at a time** (consistent with project-brief: "Claude Code ir analīzes dzinējs … interaktīvi sarunā, nevis automatizētos skriptos"). It is the 10th agent in the existing pattern.
- **Input:** outlet name, website, X handle.
- **Researches:** ownership (corporate registry — Lursoft / `ur.gov.lv` / Firmas.lv), funding model (state budget for public broadcasters; ads/subscriptions/owner for private), legal form, editor-in-chief / editorial leadership, founding year.
- **Output:** a proposed `outlets:` entry in `sources.yaml` — each fact with `source_url` + `as_of`. Facts it cannot source are left blank.
- **Human-in-the-loop:** you review the YAML diff in git before commit (better provenance than DB rows). No DB writes, no daemon.
- **Hard constraints in the prompt:** neutral descriptive language; the *same fields for every outlet* regardless of perceived lean (symmetry); no characterization of coverage quality (that is the computed coverage section's job).
- **Updates:** ownership changes are rare → re-run on demand or edit by hand; git history is the change log.

## Methodology guardrails (baked into the pages)

- Every transparency fact shows a visible source link; unsourced → not shown.
- Coverage is descriptive counts/shares computed from data; the page states the comparison period and the multi-tag caveat.
- Coverage-by-party shown as share + cross-outlet average reference (interpretation without labeling).
- Identical fields and metrics for every outlet, regardless of perceived lean.
- No `corrupt` / `bought` / `biased` labels anywhere; editorial framing stays internal in v1.

## Tangential fix (separate, independent commit)

- Move `CREATE UNIQUE INDEX idx_social_accounts_unique ON social_accounts(opponent_id, platform, handle)` into `src/schema.sql`. It is currently created only by the one-off `scripts/migrate_external_profiles.py`, so a fresh/test DB lacks it and CLAUDE.md #11's idempotency invariant silently fails there (same rationale `schema.sql` already documents for `idx_claims_opp_type_topic`). Add/confirm a test that `init_db()` produces it. **Independent of the media feature.**

## Testing

- `test_outlets.py` — `sources.yaml` parses into outlet objects; feeds group by `outlet:` tag; `hosts`/`facts` extracted; unsourced facts omitted.
- `test_render_mediji.py` — index + a detail page render against a fixture DB; coverage numbers match hand-computed values; audience-role exclusion applied; coverage-by-party uses shares; identical field set per outlet.
- Coverage-query test — single-pass + indexed; counts match a seed DB.
- Orchestrator — `"mediji"` in `KNOWN_DOMAINS`; `generate_public_site(only={'mediji'})` writes `mediji.html` + `mediji/<slug>.html`; sitemap includes them.
- Schema-fix test (separate commit) — fresh `init_db()` has `idx_social_accounts_unique`.
- Gate: `bash scripts/check.sh` (ruff + pytest + render smoke) green.

## Open items / future

- **Phase 2** (would justify real DB tables): published-rubric framing/emphasis layer; individual-journalist profiles; an optional recurring media-brief agent.
- Decide whether `rus.delfi.lv` / `nasha.la.lv` are separate Russian-language outlets or subsumed under Delfi / Latvijas Avīze.
- Decide whether `vestnesis.lv` (official gazette) is an `agency`/official outlet or excluded from coverage comparisons (it is official publishing, not journalism).
- Known doc drift to tidy opportunistically (not blocking): `wiki/operations/source-framing.md` (7 outlets, partial) has drifted from `sources.yaml` (authoritative); `wiki/index.md` says "16 partijas" but the DB has 15.
