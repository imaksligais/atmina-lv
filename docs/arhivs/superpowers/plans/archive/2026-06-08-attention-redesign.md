# atmina.lv Attention/Engagement Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: executed via the Workflow tool (parallel new-file phase) + main-session integration. Steps use checkbox (`- [ ]`) syntax. Verification: `bash scripts/check.sh` (venv: `.venv/Scripts/python.exe`).

**Goal:** Turn the homepage from a database into a destination — curiosity-first hero, no-typing discovery ranks, 31 topic destination pages, keep-digging blocks, nav 12→6, mobile-first polish — reusing existing data, no DB/schema changes.

**Architecture:** Static-site generator. `templates/*.j2` + `src/render/*.py` (self-contained sub-page modules importing only from `src.render._common` + `src.db`) + `assets/style.css` + SQLite. Two NEW disjoint modules (`topics.py`, `rankings.py`) + NEW templates are built in parallel; the contention-prone shared core (nav, hero, orchestrator, CSS) is integrated sequentially.

**Tech Stack:** Python 3, Jinja2, SQLite, vanilla JS (no new deps), Playwright (verify only).

---

## Interface Contracts (locked — all phases code to these)

### `src/render/rankings.py`
```python
def fetch_rankings(
    db: sqlite3.Connection,
    contradictions: list[dict[str, Any]],   # the orchestrator's enriched list
    *, limit: int = 8,
) -> dict[str, list[dict[str, Any]]]:
    """Site-wide discovery ranks. Pure aggregation; reuses already-enriched
    contradictions (slug/party_color/delta_days/severity_* present) and runs
    two small DB queries. Neutral framing — counts and %, never a 'score'."""
```
Returns keys (each a list of dicts):
- `most_contradictions`: `{name, slug, party, party_color, count}` — Counter over `contradictions` by politician, desc.
- `biggest_reversals`: `{id, name, slug, party_color, topic, delta_days, severity_lv, severity_glyph}` — `contradictions` with non-None `delta_days`, sorted desc.
- `most_active_7d`: `{name, slug, party, party_color, count}` — DB: `claims` `claim_type='position'`, `stated_at>=cutoff_7d`, group by `opponent_id`, exclude inactive, desc.
- `vote_alignment_outliers`: `{name, slug, party, party_color, agree_pct, sample}` — DB: per current deputy, % of their votes matching the **chamber majority** per `vote_id`, lowest first. Metric label in UI: "balso visretāk ar Saeimas vairākumu". Restricted to `sample >= 50` shared votes. **Performance:** must run < 3s on the 517k-row `saeima_individual_votes`; benchmark in Step P1-R4. Returns `[]` gracefully if no qualifying rows.

### `src/render/topics.py`
```python
def render_topics(env: Environment, db: sqlite3.Connection, atmina_dir: Path) -> int:
    """Write temas.html (directory) + temas/<slug>.html per non-empty canonical
    topic group. Returns page count (index + per-topic). Self-contained."""
```
Internal `_fetch_topics(db) -> list[dict]` — one entry per `topic_map.TOPIC_GROUPS` key that has ≥1 position claim OR ≥1 contradiction:
- `{name, slug, color, position_count, contradiction_count, politician_count}` for the directory.
Internal `_fetch_topic_detail(db, name) -> dict`:
- `top_politicians`: `{name, slug, party, party_color, count}` (positions on topic, desc, top 10).
- `latest_positions`: `{politician_name, slug, party_color, stance, stated_at, source_url, source_domain, confidence}` (top 15, desc).
- `contradictions`: enriched contradictions where `topic == name` (reuse `_enrich_contradiction`).
- `related_bills`: `{slug, title, ...}` IF bills carry this topic, else `[]` (graceful).
- `related_syntheses`: syntheses whose frontmatter `topics` list contains `name`.
- `keep_digging`: built via the generic shape below.

Topic match is a **direct equality** on the canonical group name — `claims.topic` / `contradictions.topic` already store normalized canonical names (CLAUDE.md §Output Conventions: `store_claim`/`store_contradiction` auto-normalize). Colors from `positions.PZV1_TOPIC_COLORS` (import the dict; promote to `_common` if cleaner). Slug = `_common._slugify(name)`.

### `templates/_keep_digging.html.j2` (generic, low-coupling)
Renders one optional dict `digging`:
```jinja
{# digging = {"columns": [{"title": str, "links": [{"label": str, "href": str, "sub": str|None}]}]} #}
{% if digging and digging.columns %}
<section class="keep-digging">
  <div class="keep-digging-kicker">Turpini rakt</div>
  <div class="keep-digging-grid">
    {% for col in digging.columns %}
      {% if col.links %}
      <div class="keep-digging-col">
        <h3 class="keep-digging-title">{{ col.title }}</h3>
        <ul class="keep-digging-list">
          {% for l in col.links %}
          <li><a href="{{ l.href }}">{{ l.label }}</a>{% if l.sub %}<span class="keep-digging-sub">{{ l.sub }}</span>{% endif %}</li>
          {% endfor %}
        </ul>
      </div>
      {% endif %}
    {% endfor %}
  </div>
</section>
{% endif %}
```
Each caller builds `digging.columns`. Profile: "Citi šajā partijā" + "Citi par šo tēmu" (top topic) + "Nejaušs profils". Pretruna-detail: "Saistītās pretrunas" (same topic/politician) + "Citi šajā partijā" + "Šī tēma →". Tema: "Top politiķi" + "Saistītās pretrunas" + "Cita tēma".

### New render domain
`temas` added to `_orchestrator.KNOWN_DOMAINS`; gated `if _want("temas"): topic_count = render_topics(env, db, atmina_dir)`; index context gets `rankings` + `week_summary`; sitemap lists `temas.html` + every `temas/<slug>.html`.

---

## PHASE 1 — Parallel new files (Workflow; disjoint paths, zero contention)

### Task P1-R: `src/render/rankings.py` + test
**Files:** Create `src/render/rankings.py`, `tests/test_rankings.py`.

- [ ] **R1** Write `tests/test_rankings.py` against the `fixture_db` pattern from `tests/test_render_chars.py` (build tmp DB from `tests/fixtures/render_fixture_data.sql`). Assert `fetch_rankings(db, contradictions)` returns the 4 keys; each value is a `list`; every item has `slug` + `party_color`; `most_contradictions` is sorted non-increasing by `count`; `biggest_reversals` non-increasing by `delta_days`.
- [ ] **R2** Run: `.venv/Scripts/python.exe -m pytest tests/test_rankings.py -v` → FAIL (no module).
- [ ] **R3** Implement `fetch_rankings` per contract. Import `_slugify`, `PARTY_COLORS` from `src.render._common`; `today_lv`/`timedelta` for the 7d cutoff. `most_contradictions`/`biggest_reversals` from the passed `contradictions` list (no new query). `most_active_7d` + `vote_alignment_outliers` via DB.
- [ ] **R4** Benchmark `vote_alignment_outliers`: `.venv/Scripts/python.exe -c "import time;from src.db import get_db;from src.render.rankings import fetch_rankings;from src.render.contradictions import _fetch_contradictions;db=get_db('data/atmina.db');c=_fetch_contradictions(db);t=time.time();r=fetch_rankings(db,c);print('s=',round(time.time()-t,2));print({k:len(v) for k,v in r.items()})"`. Expected < 3s, all 4 keys populated. If slow, add the documented majority-CTE index hint or reduce to current-term votes; if still empty/slow, return `[]` for that key (graceful) and note it.
- [ ] **R5** Run pytest → PASS. **Commit** `feat(render): site-wide discovery rankings helper`.

### Task P1-T: `src/render/topics.py` + `templates/tema.html.j2` + `templates/temas.html.j2` + test
**Files:** Create `src/render/topics.py`, `templates/tema.html.j2`, `templates/temas.html.j2`, `tests/test_topics.py`.

- [ ] **T1** Write `tests/test_topics.py` (fixture_db pattern): call `render_topics(env, db, tmp)` with a Jinja env (`FileSystemLoader(_common.TEMPLATES_DIR)` + the same filters the orchestrator registers — copy the filter registration block). Assert `temas.html` exists; assert one `temas/<slug>.html` per non-empty group; assert returned count == `1 + len(non_empty_groups)`; assert a known fixture topic page contains its topic name.
- [ ] **T2** Run → FAIL.
- [ ] **T3** Implement `topics.py` (`_fetch_topics`, `_fetch_topic_detail`, `render_topics`) per contract. `temas.html.j2` = directory grid of topic cards (name, color dot, position/contradiction counts) linking to `temas/<slug>.html`. `tema.html.j2` extends `base.html.j2`, `{% set active_page = "temas" %}`, `{% set assets_prefix = "../" %}` (it lives one dir deep — mirror `politiki/<slug>.html` prefix convention), sections: top politicians, latest positions (reuse claim-card markup vocabulary), in-topic contradictions (reuse `prv2` card include or compact variant), related bills/syntheses, then `{% include "_keep_digging.html.j2" %}`. Per-page OG meta via `{% block og_title %}`/`{% block og_description %}`.
- [ ] **T4** Run → PASS. **Commit** `feat(render): topic destination pages (temas/) domain`.

### Task P1-K: `templates/_keep_digging.html.j2`
**Files:** Create `templates/_keep_digging.html.j2`.
- [ ] **K1** Write the partial exactly as in the contract above. No test (pure markup; exercised via T1 + integration).
- [ ] **K2** **Commit** `feat(templates): generic keep-digging partial`.

> P1-R, P1-T, P1-K run concurrently. P1-T's `tema.html.j2` `{% include "_keep_digging.html.j2" %}` depends on P1-K — Workflow orders K before T's render test, or T stubs an empty `digging`.

---

## PHASE 2 — Sequential integration (main session; shared files, in this order)

### Task P2-1: Nav 12→6 + mobile hamburger — `templates/base.html.j2`
- [ ] **2.1a** Replace `.nav-links` block: primary = Pretrunas, Pozīcijas, Balsojumi, **Tēmas** (`temas.html`), Politiķi (`personas.html`), Analīzes. Add a `<details class="nav-more">`/`<summary>Vairāk</summary>` (or checkbox) holding Partijas, Mediji, Ziņas, X, Saites, Finanses, Statistika. Preserve `active_page` checks; secondary pages mark "Vairāk" active.
- [ ] **2.1b** Add a mobile hamburger: a `<input type="checkbox" id="nav-toggle">` + `<label>` button + CSS-driven slide-down overlay (no JS dependency; ~10 lines JS only to close on link tap). Tap targets ≥44px.
- [ ] **2.1c** Render smoke: `CHECK_RENDER_ONLY=dashboard,personas .venv/Scripts/python.exe -m src.render --only=dashboard,personas` (or the inline smoke) → no template error. **Commit** `feat(nav): compress 12→6 primary + Vairāk disclosure + mobile menu`.

### Task P2-2: Orchestrator wiring — `src/render/_orchestrator.py`
- [ ] **2.2a** Add `"temas"` to `KNOWN_DOMAINS`. Import `render_topics`; add gated block `if _want("temas"): topic_pages = render_topics(env, db, atmina_dir)`. Import `fetch_rankings`; compute `rankings = fetch_rankings(db, contradictions)` (cheap) and pass into `render_dashboard`. Add `temas.html` + per-topic URLs to `_generate_sitemap` (thread a `topic_slugs` list out of `render_topics` or recompute from `_fetch_topics`).
- [ ] **2.2b** Update `tests/test_orchestrator_gating.py`: add `"temas"` to its `KNOWN_DOMAINS` expectation and the `_heavy_fetch_plan` map assertions (temas consumes none of votes/blog/trends → no change to heavy flags, but the exhaustive set must include it). Run: `.venv/Scripts/python.exe -m pytest tests/test_orchestrator_gating.py -v` → PASS.
- [ ] **2.2c** **Commit** `feat(render): wire temas domain + rankings into orchestrator`.

### Task P2-3: Homepage hero + ranks + this-week + search — `templates/index.html.j2`, `src/render/dashboard.py`
- [ ] **2.3a** `dashboard.py`: extend `render_dashboard` signature with `rankings` param; build `week_summary` from `stats` (`claims_7d`, `votes_7d`, `contradictions_7d`) + latest weekly brief slug; pass `rankings`, `week_summary`, and a `hero_contradictions = contradictions[:5]` (for rotation) into `index.html.j2` context. Keep existing keys.
- [ ] **2.3b** `index.html.j2`: (1) hero — brand line → small kicker; add global search `<form action="pozicijas.html"><input name="q" ...></form>`; featured rotating contradiction using `prv2` vocabulary over `hero_contradictions` (JS fade-cycle, reduced-motion = first only); metric tiles → compact secondary strip. (2) NEW "Atklāj" rank block (tabs or stacked) over `rankings`. (3) NEW "Šonedēļ" strip over `week_summary`. Keep existing sections (briefs, latest contradictions grid, analyses, trends, votes) but ensure no duplication with the new hero contradiction.
- [ ] **2.3c** Smoke render dashboard → no error. **Commit** `feat(home): curiosity-first hero + discovery ranks + this-week strip + search`.

### Task P2-4: Keep-digging data on profile + pretruna-detail — `src/render/politicians.py`, `src/render/contradictions.py`, `templates/politician.html.j2`, `templates/pretruna-detail.html.j2`
- [ ] **2.4a** `politicians.py`: build a `keep_digging` dict (columns: same-party politicians, top-topic → `temas/<slug>.html`, random profile) and pass to `politician.html.j2`; `{% include "_keep_digging.html.j2" %}` near the existing `related-syntheses` block (templates/politician.html.j2:135/212).
- [ ] **2.4b** `contradictions.py`: build `keep_digging` for detail pages (same-topic contradictions, same-party, "šī tēma →"); include the partial in `pretruna-detail.html.j2`.
- [ ] **2.4c** Smoke render `pretrunas,politiki` → no error. **Commit** `feat(engage): keep-digging blocks on profiles + contradiction detail`.

### Task P2-5: Share affordance everywhere — `templates/index.html.j2`, `templates/tema.html.j2`, `templates/politician.html.j2`
- [ ] **2.5a** Extract the `prv2-share-x` X-intent pattern (pretruna-detail.html.j2:121) into reuse on homepage/list contradiction cards, topic pages, and profiles (X-intent + copy-URL button, ~15 lines JS for clipboard). Ensure per-page OG meta on tema + profile pages.
- [ ] **2.5b** Smoke render → no error. **Commit** `feat(share): X-intent + copy-URL on cards, topics, profiles`.

### Task P2-6: Design refinement + mobile-first CSS — `assets/style.css`
- [ ] **2.6a** Append clearly-delimited sections for: nav `Vairāk` + hamburger, hero search + featured-contradiction scaling, `.atklaj`/rank lists, `.week-strip`, `.keep-digging`, `temas` grid + detail, share buttons. Reuse tokens (`--bg`, `--surface`, `--accent`, `--border`, `--radius`); match existing `prv2`/`hero-v2` vocabulary.
- [ ] **2.6b** Refinement pass: consistent section spacing, card elevation/hover, type scale. Mobile-first audit at 360–414px (hero, ranks, prv2 cards, tables → scroll/reflow, nav). 44px tap targets; zero horizontal overflow; honor `prefers-reduced-motion`.
- [ ] **2.6c** (CSS does not drift char baselines — `?v=` pinned to "test".) **Commit** `style: mobile-first polish + new component styles`.

---

## PHASE 3 — Verification

### Task P3-1: Regenerate char baselines (nav change touched every page)
- [ ] **3.1a** `REGEN=1 .venv/Scripts/python.exe -m pytest tests/test_render_chars.py` then re-run without REGEN → PASS. Inspect `git diff --stat tests/fixtures/render_baseline_*.json` — every page hash changed (expected, nav). **Commit** `test: regen render char baselines after nav + home redesign`.
- [ ] **3.1b** (Optional) Add a `temas` capture + test to `tests/test_render_chars.py` and bootstrap its baseline.

### Task P3-2: Full check + render
- [ ] **3.2a** `bash scripts/check.sh` → green (ruff + full pytest + smoke). New failures fail; pre-existing baseline failures (docs/refactor/baseline-2026-04-29.md) tolerated.
- [ ] **3.2b** Full render: `.venv/Scripts/python.exe -m src.render` (or `CHECK_RENDER_ONLY=all`) into `output/atmina/`; confirm `temas.html` + `temas/*.html` exist and link.

### Task P3-3: Parallel adversarial review (Workflow) + Playwright screenshots
- [ ] **3.3a** Workflow fan-out (read-only): (1) neutrality/CLAUDE.md conventions (no score/sentiment/tabloid; vote-alignment factual), (2) LV grammar + stylistics on every new string, (3) mobile responsiveness via Playwright @390px (home, a tema, a profile) — no overflow, tap targets, (4) render/link integrity (no broken internal hrefs, every topic page reachable), (5) accessibility (contrast, focus, reduced-motion).
- [ ] **3.3b** Capture before/after Playwright screenshots: home + tema + profile @1280 & 390. Fix all confirmed findings; re-run `bash scripts/check.sh`.

### Task P3-4: Handoff
- [ ] **3.4a** Present before/after screenshots + summary. **No deploy without operator confirmation** (memory: feedback_brief_publish_pause / render_narrow_scope). On approval: narrow deploy with `--no-delete`.

---

## Self-review
- **Spec coverage:** A→P2-1; B→P2-3; C→P1-R+P2-3; D→P2-3; E→P1-T+P2-2; F→P1-K+P2-4; G→P2-5; H→P2-6; neutrality→P3-3; tests/baselines→P3-1/3-2. All covered.
- **Type consistency:** `fetch_rankings(db, contradictions)`, `render_topics(env, db, atmina_dir)`, `digging.columns[].links[].{label,href,sub}` used consistently across tasks.
- **No placeholders:** every task has concrete files, commands, contracts, commit messages.
- **Non-goals honored:** no DB writes (no rollback needed), finanses/statistika untouched, no new deps, no scorecards.
