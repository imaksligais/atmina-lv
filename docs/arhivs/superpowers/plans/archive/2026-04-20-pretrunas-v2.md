# Pretrunas V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild `/pretrunas.html` as an FT/Bloomberg-style editorial split-screen (`prv2-card`) — party-color rail, three-cell header band, `Iepriekš`/`Pašlaik` panes with a 1px gutter + severity disc, shareable anchor IDs with hash deep-link + highlight pulse, page-level methodology explainer, and mobile collapse.

**Architecture:** Pure template + CSS rewrite with a minimal Python data widening step. `_fetch_contradictions` (src/generate.py:478) gains four columns (`tp.role`, `ct.salience`, `c_old.quote`, `c_new.quote`) and four Python-side enrichments (`severity_glyph`, `initials`, `old/new_source_domain`, `delta_days`). `templates/pretrunas.html.j2` swaps `pretruna-card` for `prv2-card` markup and adds a page-level explainer + hash deep-link JS. `assets/style.css` removes legacy `.pretruna-card.*` (354–511) and `.alt-explanation` (1581–1612) and adds a single `prv2-*` block with responsive collapse at 760px. Filter JS is preserved verbatim except for the card selector change (`.pretruna-card` → `.prv2-card`). `assets_version` auto-bumps from `style.css` mtime — no manual action required.

**Tech Stack:** Python 3.11 + SQLite, Jinja2 templates, vanilla CSS (dark theme CSS variables in `:root`), vanilla JS (no framework).

**Files touched (4 total):**
- Modify: `src/generate.py` (~478–523, plus three new helpers near existing utils)
- Modify: `tests/test_generate.py` (three new `TestClass` blocks)
- Modify: `templates/pretrunas.html.j2` (full `pretruna-card` markup rewrite + explainer + hash JS)
- Modify: `assets/style.css` (delete 354–511 and 1581–1612, insert new `prv2-*` block)

**Branch:** `design/pretrunas-v2` (create from `master` at Task 0).

**Spec reference:** `docs/superpowers/specs/2026-04-20-pretrunas-v2-design.md`

---

## Task 0: Branch setup

**Files:** _none_

- [ ] **Step 1: Verify clean working tree on master**

Run: `git status --short`
Expected: only the pre-existing `M wiki/...` and `?? _claim_audit*.csv` churn listed in the session-start `git status`. No new modifications under `src/`, `templates/`, `assets/`, `tests/`, or `docs/superpowers/plans/` beyond the plan file itself.

If there are unexpected modifications in those paths, stop and ask the user before proceeding.

- [ ] **Step 2: Create and check out the feature branch**

Run:
```bash
git checkout -b design/pretrunas-v2
```
Expected: `Switched to a new branch 'design/pretrunas-v2'`

- [ ] **Step 3: Verify branch**

Run: `git branch --show-current`
Expected: `design/pretrunas-v2`

No commit at this step — the branch is empty until Task 1 lands.

---

## Task 1: Python helper `_initials_from_name` (TDD)

**Files:**
- Modify: `src/generate.py` — add helper near existing private utils (after `_source_to_internal_link` at line 475, before `_fetch_contradictions` at 478)
- Test: `tests/test_generate.py` — add `TestInitialsFromName` class after `TestSlugify`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_generate.py` (after the `TestSlugify` class):

```python
from src.generate import _initials_from_name


class TestInitialsFromName:
    def test_two_word_name(self):
        assert _initials_from_name("Evika Siliņa") == "ES"

    def test_three_word_name_uses_first_two(self):
        assert _initials_from_name("Krišjānis Feldmans Juniors") == "KF"

    def test_single_word(self):
        assert _initials_from_name("Madonna") == "M"

    def test_none(self):
        assert _initials_from_name(None) == "?"

    def test_empty_string(self):
        assert _initials_from_name("") == "?"

    def test_whitespace_only(self):
        assert _initials_from_name("   ") == "?"

    def test_latvian_diacritics_preserved(self):
        assert _initials_from_name("Āris Šķērslis") == "ĀŠ"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_generate.py::TestInitialsFromName -v`
Expected: `ImportError` (or `cannot import name '_initials_from_name'`) — every test errors.

- [ ] **Step 3: Implement the helper**

In `src/generate.py`, insert directly above `def _fetch_contradictions` (currently line 478):

```python
def _initials_from_name(name: str | None) -> str:
    """Two-letter initials for avatar chip; '?' fallback."""
    if not name:
        return "?"
    parts = [p for p in name.split() if p]
    if not parts:
        return "?"
    return "".join(p[0].upper() for p in parts[:2])
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_generate.py::TestInitialsFromName -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add src/generate.py tests/test_generate.py
git commit -m "feat(generate): add _initials_from_name helper for prv2 avatars"
```

---

## Task 2: Python helper `_delta_days` (TDD)

**Files:**
- Modify: `src/generate.py` — add helper directly after `_initials_from_name`
- Test: `tests/test_generate.py` — add `TestDeltaDays` class

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_generate.py`:

```python
from src.generate import _delta_days


class TestDeltaDays:
    def test_basic_diff(self):
        assert _delta_days("2026-01-01", "2026-01-11") == 10

    def test_same_day(self):
        assert _delta_days("2026-03-05", "2026-03-05") == 0

    def test_order_independent(self):
        # Reversed inputs still return positive diff (abs)
        assert _delta_days("2026-04-10", "2026-01-01") == 99

    def test_accepts_iso_with_time_suffix(self):
        assert _delta_days("2026-01-01T12:30:00", "2026-01-11T09:15:00") == 10

    def test_none_old(self):
        assert _delta_days(None, "2026-01-11") is None

    def test_none_new(self):
        assert _delta_days("2026-01-01", None) is None

    def test_both_none(self):
        assert _delta_days(None, None) is None

    def test_malformed_returns_none(self):
        assert _delta_days("not-a-date", "2026-01-11") is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_generate.py::TestDeltaDays -v`
Expected: ImportError on all tests.

- [ ] **Step 3: Implement the helper**

In `src/generate.py`, insert directly after `_initials_from_name`:

```python
def _delta_days(old_date: str | None, new_date: str | None) -> int | None:
    """Absolute day diff between two ISO dates; None if either missing/malformed."""
    if not old_date or not new_date:
        return None
    try:
        d_old = date.fromisoformat(old_date[:10])
        d_new = date.fromisoformat(new_date[:10])
        return abs((d_new - d_old).days)
    except (ValueError, TypeError):
        return None
```

Note: `date` is already imported from `datetime` at `src/generate.py:14` — no new import needed.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_generate.py::TestDeltaDays -v`
Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add src/generate.py tests/test_generate.py
git commit -m "feat(generate): add _delta_days helper for prv2 ΔT cells"
```

---

## Task 3: Python helper `_domain_from_url` (TDD)

**Files:**
- Modify: `src/generate.py` — add helper directly after `_delta_days`
- Test: `tests/test_generate.py` — add `TestDomainFromUrl` class

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_generate.py`:

```python
from src.generate import _domain_from_url


class TestDomainFromUrl:
    def test_basic_https(self):
        assert _domain_from_url("https://www.lsm.lv/raksts/foo") == "lsm.lv"

    def test_strips_www(self):
        assert _domain_from_url("https://www.delfi.lv/article/1") == "delfi.lv"

    def test_no_www(self):
        assert _domain_from_url("https://tvnet.lv/x") == "tvnet.lv"

    def test_subdomain_preserved(self):
        assert _domain_from_url("https://rus.delfi.lv/abc") == "rus.delfi.lv"

    def test_none(self):
        assert _domain_from_url(None) is None

    def test_empty(self):
        assert _domain_from_url("") is None

    def test_malformed(self):
        # urlparse is lenient; non-URL garbage → empty netloc → None
        result = _domain_from_url("not a url at all")
        assert result in (None, "")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_generate.py::TestDomainFromUrl -v`
Expected: ImportError on all tests.

- [ ] **Step 3: Implement the helper**

In `src/generate.py`, insert directly after `_delta_days`:

```python
def _domain_from_url(url: str | None) -> str | None:
    """Hostname with leading 'www.' stripped; None on empty/invalid."""
    if not url:
        return None
    try:
        netloc = urlparse(url).netloc
    except (ValueError, TypeError):
        return None
    if not netloc:
        return None
    return netloc.removeprefix("www.")
```

Note: `urlparse` is already imported at `src/generate.py:17` — no new import needed.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_generate.py::TestDomainFromUrl -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add src/generate.py tests/test_generate.py
git commit -m "feat(generate): add _domain_from_url helper for prv2 source chips"
```

---

## Task 4: Extend `_fetch_contradictions` SELECT and enrichment

**Files:**
- Modify: `src/generate.py:478-523` — widen SELECT, add four new enrichment fields

- [ ] **Step 1: Re-read the function before editing**

Run: `python -c "import inspect, src.generate as g; print(inspect.getsource(g._fetch_contradictions))"`

Confirm the function matches what the plan expects. If the source has drifted from the version captured during planning, stop and ask the user.

- [ ] **Step 2: Extend the SELECT with `tp.role`, `ct.salience`, `c_old.quote`, `c_new.quote`**

In `src/generate.py`, replace the SQL query inside `_fetch_contradictions` (currently lines 479–493) with:

```python
    rows = db.execute("""
        SELECT
            ct.id, ct.opponent_id, ct.topic, ct.summary, ct.severity,
            ct.detected_at, ct.salience,
            tp.name AS politician_name, tp.party, tp.role,
            c_old.stance AS old_stance, c_old.stated_at AS old_date,
            c_old.source_url AS old_source, c_old.quote AS old_quote,
            c_new.stance AS new_stance, c_new.stated_at AS new_date,
            c_new.source_url AS new_source, c_new.quote AS new_quote
        FROM contradictions ct
        JOIN tracked_politicians tp ON ct.opponent_id = tp.id
        LEFT JOIN claims c_old ON ct.claim_old_id = c_old.id
        LEFT JOIN claims c_new ON ct.claim_new_id = c_new.id
        ORDER BY ct.detected_at DESC
    """).fetchall()
```

- [ ] **Step 3: Add severity glyph map + four enrichment fields inside the row loop**

Still inside `_fetch_contradictions`, insert immediately before the existing `results = []` line:

```python
    SEVERITY_GLYPHS = {
        "direct_contradiction": "⇄",
        "reversal": "↺",
        "minor_shift": "≈",
    }
```

Then inside the row loop, immediately before `results.append(d)`, add:

```python
        # prv2 enrichment
        d["severity_glyph"] = SEVERITY_GLYPHS.get(d["severity"], "·")
        d["initials"] = _initials_from_name(d["politician_name"])
        d["old_source_domain"] = _domain_from_url(d.get("old_source"))
        d["new_source_domain"] = _domain_from_url(d.get("new_source"))
        d["delta_days"] = _delta_days(d.get("old_date"), d.get("new_date"))
```

Keep all existing enrichment (`severity_lv`, `slug`, `party_short`, `party_color`, date trimming, `old_link`/`new_link`, `vote_summary`, `vote_id`) exactly as-is.

- [ ] **Step 4: Run the existing test suite to confirm no regression**

Run: `python -m pytest tests/test_generate.py -v`
Expected: all previously passing tests still pass; the three new TestClasses from Tasks 1–3 also pass.

- [ ] **Step 5: Smoke-test by regenerating the site**

Run: `python -c "from src.generate import generate_public_site; generate_public_site()"`
Expected: completes without error. The `/pretrunas.html` page now contains legacy markup but enriched data — it will still render fine since the template reads no new keys yet.

- [ ] **Step 6: Re-read the modified function to confirm edits applied**

Run: `python -c "import inspect, src.generate as g; print(inspect.getsource(g._fetch_contradictions))"`
Expected: SELECT contains `tp.role`, `ct.salience`, `old_quote`, `new_quote`; loop contains `severity_glyph`, `initials`, `old_source_domain`, `new_source_domain`, `delta_days`.

- [ ] **Step 7: Commit**

```bash
git add src/generate.py
git commit -m "feat(generate): widen _fetch_contradictions with quote/role/salience + prv2 enrichment"
```

---

## Task 5: Rewrite `pretrunas.html.j2` card markup

**Files:**
- Modify: `templates/pretrunas.html.j2` — replace lines 74–125 (the `.grid-2 #contradictions-grid` block)

- [ ] **Step 1: Re-read the template to confirm current state**

Read `templates/pretrunas.html.j2` lines 74–125 and confirm the `{% for c in contradictions %}` block still matches what the plan expects.

- [ ] **Step 2: Replace the card loop with prv2 markup**

In `templates/pretrunas.html.j2`, replace lines 74–125 (from `<div class="grid-2" id="contradictions-grid">` through the closing `</div>` that wraps the loop) with:

```jinja
  <div class="grid-2" id="contradictions-grid">
    {% for c in contradictions %}
    <article class="prv2-card sev-{{ c.severity }}" id="pretruna-{{ c.id }}"
             data-severity="{{ c.severity }}" data-party="{{ c.party }}"
             data-person="{{ c.politician_name }}">

      <div class="prv2-partybar" style="background: {{ c.party_color }}"></div>

      <header class="prv2-head">
        <div class="prv2-persona">
          <span class="prv2-avatar" style="--pc: {{ c.party_color }}">{{ c.initials }}</span>
          <div class="prv2-persona-text">
            <a class="prv2-name" href="politiki/{{ c.slug }}.html">{{ c.politician_name }}</a>
            <div class="prv2-role">
              {%- if c.role -%}{{ c.role }} · {% endif -%}
              {{ c.party_short }}
            </div>
          </div>
        </div>
        <div class="prv2-meta-mid">
          <span class="prv2-sevbadge">{{ c.severity_glyph }} {{ c.severity_lv }}</span>
          {% if c.topic %}<span class="prv2-topic">{{ c.topic }}</span>{% endif %}
        </div>
        {% if c.delta_days is not none %}
        <div class="prv2-meta-right">
          <div class="prv2-datacell">
            <span class="prv2-datacell-l">ΔT</span>
            <span class="prv2-datacell-v">{{ c.delta_days }}d</span>
          </div>
        </div>
        {% endif %}
      </header>

      {% if c.summary %}
      <section class="prv2-summary">
        <div class="prv2-kicker">Kopsavilkums</div>
        <p>{{ c.summary }}</p>
      </section>
      {% endif %}

      <div class="prv2-split">
        <div class="prv2-pane prv2-pane-old">
          <div class="prv2-kicker">Iepriekš</div>
          <div class="prv2-pane-meta">
            <time>{{ c.old_date }}</time>
            {% if c.old_source %}
            · <a href="{{ c.old_source }}" target="_blank" rel="noopener">{{ c.old_source_domain }} ↗</a>
            {% endif %}
          </div>
          <div class="prv2-stance">{{ c.old_stance }}</div>
          {% if c.old_quote %}
          <blockquote class="prv2-quote">{{ c.old_quote }}</blockquote>
          {% else %}
          <div class="prv2-quote-fallback">Citāts nav pieejams — parafrāze no avota</div>
          {% endif %}
        </div>

        <div class="prv2-gutter">
          <span class="prv2-gutter-disc" aria-hidden="true">{{ c.severity_glyph }}</span>
        </div>

        <div class="prv2-pane prv2-pane-new">
          <div class="prv2-kicker prv2-kicker-sev">Pašlaik</div>
          <div class="prv2-pane-meta">
            <time>{{ c.new_date }}</time>
            {% if c.new_source %}
            · <a href="{{ c.new_source }}" target="_blank" rel="noopener">{{ c.new_source_domain }} ↗</a>
            {% endif %}
          </div>
          <div class="prv2-stance">{{ c.new_stance }}</div>
          {% if c.new_quote %}
          <blockquote class="prv2-quote">{{ c.new_quote }}</blockquote>
          {% else %}
          <div class="prv2-quote-fallback">Citāts nav pieejams — parafrāze no avota</div>
          {% endif %}
          {% if c.vote_summary %}
          <div class="prv2-vote">
            <span class="prv2-vote-kicker">Likumprojekts</span>
            {{ c.vote_summary }}
          </div>
          {% endif %}
        </div>
      </div>

      <footer class="prv2-foot">
        <div class="prv2-foot-meta">
          <a href="#pretruna-{{ c.id }}" class="prv2-foot-id">ID {{ '%03d' % c.id }}</a>
          · Konstatēts {{ c.detected_at[:10] }}
          {% if c.salience %} · Nozīmīgums {{ '%.2f' % c.salience }}{% endif %}
        </div>
        <div class="prv2-share" aria-hidden="true">
          <button type="button" title="Dalīties uz X (drīzumā)">𝕏</button>
          <button type="button" title="Kopēt saiti (drīzumā)">⎘</button>
        </div>
      </footer>
    </article>
    {% endfor %}
  </div>
```

- [ ] **Step 3: Verify edit applied by re-reading the template**

Read `templates/pretrunas.html.j2` lines 74–180 and confirm the `prv2-card` markup is present and the old `pretruna-card` / `severity-{{ c.severity }}` / `.alt-explanation` markup is gone.

- [ ] **Step 4: Commit**

```bash
git add templates/pretrunas.html.j2
git commit -m "feat(pretrunas): rewrite card markup to prv2 split-screen structure"
```

---

## Task 6: Page-level explainer + JS selector + hash deep-link

**Files:**
- Modify: `templates/pretrunas.html.j2` — insert explainer between pagehead-header and filter-bar (~line 30); update JS selector at line 135; append hash deep-link handler at end of the IIFE

- [ ] **Step 1: Insert the page-level explainer block**

In `templates/pretrunas.html.j2`, insert this block immediately after the `</header>` closing the `pagehead-header` (currently line 29) and before the `<div class="filter-bar" id="severity-filter">` line:

```jinja
  <div class="prv2-explainer">
    <em>Pretrunas tiek konstatētas automātiski, salīdzinot publiskās pozīcijas laika gaitā.
    Iespējami arī alternatīvi skaidrojumi — pozīcija evoluējusi, dažādas auditorijas,
    formulējuma maiņa. Iepazīstieties ar avotiem un izvērtējiet paši.</em>
  </div>
```

- [ ] **Step 2: Update the filter JS selector**

In `templates/pretrunas.html.j2`, in the inline `<script>` (around line 135), change:

```js
  const cards = document.querySelectorAll('#contradictions-grid .pretruna-card');
```

to:

```js
  const cards = document.querySelectorAll('#contradictions-grid .prv2-card');
```

The rest of the filter JS (severity buttons, multi-select, `?persona=` preselect) stays untouched.

- [ ] **Step 3: Add hash deep-link handler inside the IIFE**

In `templates/pretrunas.html.j2`, in the inline `<script>`, immediately before the closing `})();` at the end of the IIFE (currently line 221), insert:

```js
  function _prv2HashJump() {
    const hash = location.hash;
    if (!hash || !hash.startsWith('#pretruna-')) return;
    let card;
    try { card = document.querySelector(hash); } catch (e) { return; }
    if (!card) return;

    // Clear all filters so a shared link always surfaces the card.
    document.querySelectorAll('#severity-filter .filter-btn').forEach(b => b.classList.remove('active'));
    const allBtn = document.querySelector('#severity-filter [data-filter="all"]');
    if (allBtn) allBtn.classList.add('active');
    selectedParties.clear();
    selectedPersons.clear();
    document.querySelectorAll('.multi-select-option.selected').forEach(o => o.classList.remove('selected'));
    document.querySelectorAll('.multi-select-trigger.has-selection').forEach(t => {
      t.classList.remove('has-selection');
      const span = t.querySelector('span');
      if (span && t.id === 'party-trigger') span.textContent = 'Visas partijas';
      if (span && t.id === 'person-trigger') span.textContent = 'Visas personas';
    });
    activeSeverity = 'all';
    applyFilters();

    card.scrollIntoView({ behavior: 'smooth', block: 'start' });
    card.classList.add('prv2-card-pulse');
    setTimeout(() => card.classList.remove('prv2-card-pulse'), 2000);
  }
  window.addEventListener('hashchange', _prv2HashJump);
  window.addEventListener('load', _prv2HashJump);
```

Note the `try/catch` around `querySelector(hash)` — protects against malformed hashes being passed to the selector parser.

- [ ] **Step 4: Regenerate the site as a smoke test**

Run: `python -c "from src.generate import generate_public_site; generate_public_site()"`
Expected: completes without error. `/pretrunas.html` now has new markup + explainer + hash JS but no CSS yet → page will look broken (expected until Task 7 lands).

- [ ] **Step 5: Commit**

```bash
git add templates/pretrunas.html.j2
git commit -m "feat(pretrunas): add explainer block and hash deep-link handler"
```

---

## Task 7: Remove legacy CSS (`.pretruna-card.*` and `.alt-explanation`)

**Files:**
- Modify: `assets/style.css` — delete lines 352–511 (pretruna-card block) and 1581–1612 (alt-explanation block)

- [ ] **Step 1: Re-read the two CSS ranges**

Read `assets/style.css` lines 340–515 and 1575–1615 to confirm the ranges still match what the plan expects (selectors, boundaries).

If the file has drifted (e.g. line numbers shifted significantly), re-identify the blocks by locating the comment `/* Pretruna Card — editorial register...` and `/* Alternative explanation on contradiction cards */` and delete those blocks in full.

- [ ] **Step 2: Delete the `.pretruna-card` block**

In `assets/style.css`, delete the entire block from the comment `/* Pretruna Card — editorial register (serif title, mono kickers, severity left rail + tinted stance rails). */` through the final `.pretruna-card .sources a:hover { color: var(--accent); }` — currently lines 352–511.

Leave the blank line (512) separating sections.

- [ ] **Step 3: Delete the `.alt-explanation` block**

In `assets/style.css`, delete the entire block from the comment `/* Alternative explanation on contradiction cards */` through the final `.alt-explanation-content li { margin-bottom: 0.25rem; }` — currently lines 1581–1612.

- [ ] **Step 4: Verify the ranges are gone**

Run: `python -m pytest tests/test_generate.py -q` (sanity — no test touches CSS but ensures nothing else broke during edits)
Expected: passes.

Then search the file:

Run Grep: `pretruna-card|alt-explanation` in `assets/style.css`
Expected: **zero matches** in `style.css` (it may still appear in templates via old references — that's fine, Tasks 5–6 already cleaned those).

- [ ] **Step 5: Commit**

```bash
git add assets/style.css
git commit -m "refactor(css): remove legacy .pretruna-card and .alt-explanation blocks"
```

---

## Task 8: Add `prv2-*` CSS block (desktop layout + tokens)

**Files:**
- Modify: `assets/style.css` — insert new block where the removed `.pretruna-card` block lived (near line 352)

- [ ] **Step 1: Insert the new CSS block**

In `assets/style.css`, at the location where the old `.pretruna-card` block used to live (after the `.badge-*` classes ending around line 350, before the `/* Hero */` section), insert:

```css
/* Pretrunas V2 — FT/Bloomberg dense editorial split-screen.
   Party bar on top (4px), 3-cell header band, summary, Iepriekš/Pašlaik panes
   separated by 1px gutter with severity disc, footer with anchor ID + share row.
   Mobile collapse at ≤760px. */
.prv2-explainer {
  padding: 0.75rem 0;
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 14px;
  line-height: 1.55;
  color: var(--text-muted);
}
.prv2-explainer em { font-style: italic; }

.prv2-card {
  --prv2-serif: Georgia, 'Times New Roman', serif;
  --prv2-mono: 'JetBrains Mono', ui-monospace, monospace;
  --prv2-border-soft: #1f2432;
  --prv2-sev: var(--yellow);
  position: relative;
  background: var(--surface);
  border: 1px solid var(--prv2-border-soft);
  border-radius: var(--radius);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: border-color 0.18s ease;
}
.prv2-card:hover { border-color: var(--border); }
.prv2-card.sev-direct_contradiction { --prv2-sev: #dc2626; }
.prv2-card.sev-reversal             { --prv2-sev: #f97316; }
.prv2-card.sev-minor_shift          { --prv2-sev: #eab308; }

.prv2-partybar {
  height: 4px;
  width: 100%;
  background: var(--prv2-border-soft);
}

.prv2-head {
  display: grid;
  grid-template-columns: 1fr auto auto;
  align-items: center;
  gap: 1rem;
  padding: 18px 28px;
  background: var(--surface2);
  border-bottom: 1px solid var(--prv2-border-soft);
}

.prv2-persona { display: flex; align-items: center; gap: 0.85rem; min-width: 0; }
.prv2-avatar {
  flex: 0 0 auto;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--surface);
  border: 1px solid var(--pc, var(--prv2-border-soft));
  color: var(--text);
  font-family: var(--prv2-serif);
  font-size: 14px;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  letter-spacing: 0.3px;
}
.prv2-persona-text { min-width: 0; }
.prv2-name {
  font-family: var(--prv2-serif);
  font-size: 19px;
  font-weight: 500;
  letter-spacing: -0.3px;
  line-height: 1.2;
  color: var(--text);
  text-decoration: none;
  display: block;
}
.prv2-name:hover { color: var(--accent); }
.prv2-role {
  margin-top: 0.15rem;
  font-family: var(--prv2-mono);
  font-size: 10px;
  letter-spacing: 1.1px;
  text-transform: uppercase;
  color: var(--text-muted);
}

.prv2-meta-mid { display: flex; align-items: center; gap: 0.6rem; flex-wrap: wrap; }
.prv2-sevbadge {
  font-family: var(--prv2-mono);
  font-size: 10px;
  letter-spacing: 1.1px;
  text-transform: uppercase;
  padding: 4px 8px;
  border-radius: 3px;
  border: 1px solid var(--prv2-sev);
  color: var(--prv2-sev);
  white-space: nowrap;
}
.prv2-topic {
  font-family: var(--prv2-mono);
  font-size: 10px;
  letter-spacing: 1.1px;
  text-transform: uppercase;
  color: var(--text-muted);
  padding: 4px 8px;
  border: 1px solid var(--prv2-border-soft);
  border-radius: 3px;
}

.prv2-meta-right { display: flex; align-items: center; }
.prv2-datacell {
  display: inline-flex;
  flex-direction: column;
  align-items: flex-end;
  border-left: 1px solid var(--prv2-border-soft);
  padding-left: 0.85rem;
  line-height: 1.1;
}
.prv2-datacell-l {
  font-family: var(--prv2-mono);
  font-size: 9px;
  letter-spacing: 1.2px;
  text-transform: uppercase;
  color: var(--text-muted);
}
.prv2-datacell-v {
  font-family: var(--prv2-mono);
  font-size: 16px;
  color: var(--text);
  font-variant-numeric: tabular-nums;
  margin-top: 2px;
}

.prv2-summary {
  padding: 16px 28px 4px;
}
.prv2-summary p {
  margin-top: 0.35rem;
  font-family: var(--prv2-serif);
  font-size: 15px;
  line-height: 1.55;
  color: #c8ccd8;
  white-space: pre-line;
}

.prv2-kicker {
  font-family: var(--prv2-mono);
  font-size: 10px;
  letter-spacing: 1.2px;
  text-transform: uppercase;
  color: var(--text-muted);
}
.prv2-kicker-sev { color: var(--prv2-sev); }

.prv2-split {
  display: grid;
  grid-template-columns: 1fr 1px 1fr;
  padding: 20px 0;
}
.prv2-pane {
  padding: 4px 28px;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  min-width: 0;
}
.prv2-pane-new {
  background: color-mix(in srgb, var(--prv2-sev) 3%, transparent);
}
.prv2-pane-meta {
  font-family: var(--prv2-mono);
  font-size: 11px;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex-wrap: wrap;
}
.prv2-pane-meta time { font-variant-numeric: tabular-nums; }
.prv2-pane-meta a { color: var(--text-muted); }
.prv2-pane-meta a:hover { color: var(--text); }

.prv2-stance {
  font-family: var(--prv2-serif);
  font-size: 15px;
  line-height: 1.55;
  color: #c8ccd8;
  white-space: pre-line;
}

.prv2-quote {
  font-family: var(--prv2-serif);
  font-style: italic;
  font-size: 15px;
  line-height: 1.55;
  color: var(--text);
  padding: 0.4rem 0 0.4rem 0.85rem;
  border-left: 2px solid var(--prv2-sev);
  margin: 0;
}
.prv2-quote-fallback {
  font-family: var(--prv2-mono);
  font-size: 11px;
  letter-spacing: 0.4px;
  color: var(--text-muted);
  padding-left: 0.85rem;
  border-left: 2px dashed var(--prv2-border-soft);
}

.prv2-gutter {
  position: relative;
  background: var(--prv2-border-soft);
}
.prv2-gutter-disc {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: var(--surface);
  border: 1px solid var(--prv2-sev);
  color: var(--prv2-sev);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-family: var(--prv2-mono);
  font-size: 13px;
}

.prv2-vote {
  margin-top: 0.4rem;
  padding: 0.5rem 0.75rem;
  background: rgba(127, 127, 127, 0.05);
  border-left: 2px solid var(--prv2-border-soft);
  font-family: var(--prv2-serif);
  font-size: 13px;
  line-height: 1.5;
  color: var(--text-muted);
}
.prv2-vote-kicker {
  display: block;
  font-family: var(--prv2-mono);
  font-size: 9px;
  letter-spacing: 1.1px;
  text-transform: uppercase;
  color: var(--prv2-sev);
  margin-bottom: 0.25rem;
}

.prv2-foot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  padding: 14px 28px;
  background: var(--surface2);
  border-top: 1px solid var(--prv2-border-soft);
}
.prv2-foot-meta {
  font-family: var(--prv2-mono);
  font-size: 10px;
  letter-spacing: 0.8px;
  text-transform: uppercase;
  color: var(--text-muted);
}
.prv2-foot-id {
  color: var(--text-muted);
  border-bottom: 1px dotted currentColor;
}
.prv2-foot-id:hover { color: var(--text); }

.prv2-share { display: inline-flex; gap: 0.4rem; }
.prv2-share button {
  width: 28px;
  height: 28px;
  border-radius: 4px;
  border: 1px solid var(--prv2-border-soft);
  background: transparent;
  color: var(--text-muted);
  font-family: var(--prv2-mono);
  font-size: 13px;
  cursor: not-allowed;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: color 0.15s, border-color 0.15s;
}
.prv2-share button:hover {
  color: var(--text);
  border-color: var(--border);
}

.prv2-card-pulse {
  box-shadow: 0 0 0 3px var(--prv2-sev);
  transition: box-shadow 0.4s ease;
}
@media (prefers-reduced-motion: reduce) {
  .prv2-card-pulse {
    outline: 2px solid var(--prv2-sev);
    box-shadow: none;
    transition: none;
  }
}
```

- [ ] **Step 2: Regenerate the site**

Run: `python -c "from src.generate import generate_public_site; generate_public_site()"`
Expected: completes without error.

- [ ] **Step 3: Visual spot check (desktop)**

Run: `python serve.py` (in a background shell if needed).
Open `http://127.0.0.1:8080/pretrunas.html` at viewport width ≥1000px.

Verify:
- Page-level explainer is visible in italic serif under `pagehead-header`.
- Every card has a 4px party-color top bar.
- Header band shows persona (avatar + name + role · party) on the left, severity badge + topic chip in the middle, ΔT data cell on the right (when `delta_days` not null).
- Summary section appears above the split (if `summary` present).
- Split body shows two panes separated by a 1px gutter with a centered disc carrying the severity glyph.
- "Pašlaik" pane has a subtle tinted background matching the severity color.
- Blockquote renders with severity-color left rail when `quote` populated; fallback strip otherwise.
- Footer shows `ID NNN · Konstatēts DATE · Nozīmīgums X.XX` + two share stub buttons.

If any of the above is missing, stop and investigate before proceeding.

- [ ] **Step 4: Commit**

```bash
git add assets/style.css
git commit -m "feat(css): add prv2 split-screen layout with tokens and desktop styling"
```

---

## Task 9: Mobile collapse CSS (≤ 760px)

**Files:**
- Modify: `assets/style.css` — append `@media (max-width: 760px)` block directly after the `prv2-card-pulse` media query inserted in Task 8

- [ ] **Step 1: Append the mobile media query**

In `assets/style.css`, immediately after the `@media (prefers-reduced-motion: reduce)` block from Task 8, insert:

```css
@media (max-width: 760px) {
  .prv2-explainer { font-size: 13px; padding: 0.6rem 0; }

  .prv2-head {
    grid-template-columns: 1fr;
    gap: 0.6rem;
    padding: 14px 18px;
  }
  .prv2-meta-mid { order: 2; }
  .prv2-meta-right { order: 3; align-self: flex-start; }
  .prv2-meta-right .prv2-datacell {
    border-left: 0;
    padding-left: 0;
    flex-direction: row;
    align-items: baseline;
    gap: 0.4rem;
  }

  .prv2-summary { padding: 14px 18px 2px; }

  .prv2-split {
    display: block;
    padding: 16px 0;
  }
  .prv2-pane { padding: 14px 18px; }

  .prv2-gutter {
    height: 1px;
    width: 100%;
    background: var(--prv2-border-soft);
    margin: 6px 0;
  }
  .prv2-gutter-disc {
    top: 50%;
    left: 50%;
    width: 24px;
    height: 24px;
  }

  .prv2-foot {
    padding: 12px 18px;
    flex-wrap: wrap;
  }
  .prv2-foot-meta { font-size: 9px; }
  .prv2-share button { width: 26px; height: 26px; font-size: 12px; }
}
```

- [ ] **Step 2: Visual check (mobile viewport)**

With `python serve.py` still running, open `http://127.0.0.1:8080/pretrunas.html` and resize the browser to 360px width (Chrome DevTools responsive mode).

Verify:
- Header band stacks into rows (persona, then badge+topic+ΔT).
- Split panes stack vertically — `Iepriekš` above, `Pašlaik` below.
- The gutter disc sits on a thin horizontal 1px line between the two panes.
- Padding feels tighter (14/18 vs 18/28 on desktop).
- Explainer font size drops to 13px.

- [ ] **Step 3: Commit**

```bash
git add assets/style.css
git commit -m "feat(css): collapse prv2 cards to vertical stack at ≤760px"
```

---

## Task 10: End-to-end verification (no code changes)

**Files:** _none_

- [ ] **Step 1: Run the full test suite**

Run: `python -m pytest tests/ -v`
Expected: all tests pass. Fix any breakage before continuing.

- [ ] **Step 2: Regenerate the site fresh**

Run: `python -c "from src.generate import generate_public_site; generate_public_site()"`
Expected: completes without error or warning about `/pretrunas.html`.

- [ ] **Step 3: Type-check and lint (if configured)**

Run: `python -m mypy src/generate.py` — if no mypy config exists, state that explicitly and skip.
Run: `python -m ruff check src/generate.py tests/test_generate.py` — if no ruff config exists, state that explicitly and skip.

If neither tool is configured, note that in the final commit message.

- [ ] **Step 4: Functional QA against the served site**

With `python serve.py` running, open `http://127.0.0.1:8080/pretrunas.html` and exercise:

1. **Desktop layout (≥1000px)** — every card renders with party bar, 3-cell header, summary, split, footer. No console errors.
2. **Severity filter** — click `Tiešas pretrunas` → only `sev-direct_contradiction` cards remain visible. Click `Visas` → all return.
3. **Party multi-select** — pick 2 parties → cards filter correctly; "Notīrīt izvēli" resets.
4. **Person multi-select** — pick 1 person → only that person's cards; "Notīrīt izvēli" resets.
5. **Hash deep-link cold load** — navigate to `http://127.0.0.1:8080/pretrunas.html#pretruna-1` in a new tab → page scrolls to the card and it glows for ~2s. Filters are cleared even if they had selections from a prior session.
6. **Hash deep-link while filtered** — apply a severity filter that hides card #1, then manually change URL hash to `#pretruna-1` → filters clear, card scrolls into view, pulse fires.
7. **Edge cases** — find a card with `delta_days` null (if any exist in the DB) → ΔT cell absent. Find a card with `quote` null → fallback strip renders. Find a Saeima-vote card (if any) → `prv2-vote` block present in the `Pašlaik` pane.
8. **Mobile viewport (360px)** — split collapses, header stacks, explainer shrinks.
9. **Prefers-reduced-motion** — toggle OS setting (or override via DevTools `Rendering > Emulate CSS media feature prefers-reduced-motion: reduce`), repeat step 5 → card shows an instant outline instead of a fading glow.

Document any deviations; fix before merging.

- [ ] **Step 5: Confirm CSS cache-bust**

Inspect the rendered `<link rel="stylesheet">` tag in `output/atmina/pretrunas.html` (or via browser devtools). Confirm it includes a `?v=...` version string that differs from the version before Task 7. This is automatic via `assets_version` (src/generate.py:2128) keyed on `style.css` mtime — no manual bump needed.

- [ ] **Step 6: Final status commit (if any cleanup deltas arose)**

If Steps 1–5 surfaced any fixes, commit them now. Otherwise skip.

```bash
git status --short
# if clean: no-op
# if dirty: review, then
git add <files>
git commit -m "fix(pretrunas): QA cleanup after prv2 rollout"
```

- [ ] **Step 7: Summary of the branch**

Run: `git log --oneline master..HEAD`
Expected: roughly 7–9 commits implementing Tasks 1–9 (plus any QA fix from Step 6).

Offer the user the option to open a PR via `gh pr create` — do NOT open it automatically.

---

## Self-review notes (inline — not a subagent)

Coverage check against spec sections:
- §2 Scope: template rewrite (Tasks 5–6), CSS remove+add (Tasks 7–9), `_fetch_contradictions` widening (Task 4), `assets_version` is automatic via mtime (Task 10 Step 5). ✓
- §3 Data state: all enrichments handle null gracefully via Task 4 helpers + Task 5 `{% if %}` guards. ✓
- §4 Template structure: Task 5 markup matches the spec's skeleton section-for-section. ✓
- §5 Visual tokens: Task 8 CSS declares every token listed. ✓
- §6 HTML skeleton: Task 5 is a near-verbatim copy. ✓
- §7 Mobile collapse: Task 9 implements every bullet. ✓
- §8 Edge cases: all 14 edge cases handled (nulls via Jinja guards; initials fallback in helper; severity default via CSS custom property + `"·"` glyph; hash `try/catch` covers edge case 10). ✓
- §9 Python additions: Tasks 1–4 cover every helper + SELECT change. ✓
- §10 Hash deep-link JS: Task 6 Step 3 matches (with added `try/catch` hardening + multi-select trigger label reset missing in spec but required for visual consistency). ✓
- §11 File list + row counts: matches within tolerance (~340 added, ~230 removed across 4 files). ✓
- §12 Verification: Task 10 covers every bullet. ✓
- §13 Open questions: all deferred to future work, not blocking. ✓

Placeholder scan: no TBD/TODO/"similar to Task N". Every code step includes concrete code. ✓

Type/name consistency:
- `_initials_from_name`, `_delta_days`, `_domain_from_url` — signatures match across Tasks 1–4 and the SELECT widening. ✓
- `prv2-card`, `prv2-partybar`, `prv2-head`, `prv2-persona`, `prv2-avatar`, `prv2-name`, `prv2-role`, `prv2-meta-mid`, `prv2-sevbadge`, `prv2-topic`, `prv2-meta-right`, `prv2-datacell`, `prv2-datacell-l`, `prv2-datacell-v`, `prv2-summary`, `prv2-kicker`, `prv2-kicker-sev`, `prv2-split`, `prv2-pane`, `prv2-pane-old`, `prv2-pane-new`, `prv2-pane-meta`, `prv2-stance`, `prv2-quote`, `prv2-quote-fallback`, `prv2-gutter`, `prv2-gutter-disc`, `prv2-vote`, `prv2-vote-kicker`, `prv2-foot`, `prv2-foot-meta`, `prv2-foot-id`, `prv2-share`, `prv2-card-pulse`, `prv2-explainer`, `sev-direct_contradiction`, `sev-reversal`, `sev-minor_shift` — all referenced in template (Tasks 5–6) and styled in CSS (Tasks 8–9). ✓

Execution handoff: see prompt offer at end of this plan (writing-plans skill convention).
