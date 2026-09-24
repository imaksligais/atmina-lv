# Saeima Bills Phase 1C Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire up the live data flow for Saeima bills tracking so `@saeima-tracker` populates `saeima_bill_politicians`, links each vote to its bill stage, and the public site auto-links bill references and exposes a `/likumi.html` index — without adding any new core code path (Phase 1A helpers are reused).

**Architecture:** Three layers, all reusing Phase 1A primitives:
1. **Operator layer** — agent prompt (`.claude/agents/saeima-tracker.md`) gains Step 2 (parse agenda → upsert_bill + match_submitters) and Step 5 (resolve_bill_from_motif → append_bill_stage). Plus runbook (`wiki/operations/saeima-bills.md`) and CLAUDE.md Pipeline Invariant 12.
2. **Data flow** — already exists in Phase 1A helpers; agent prompt orchestrates them per session.
3. **UI surface** — `autolink_bills` Jinja filter wraps `\b\d+/(Lp14|Lm14|P14)\b` references in claim summaries; `/likumi.html` mirrors `/balsojumi.html#bills-list` pattern with topic chip + filter + search.

**Tech Stack:** Python 3.11+, Jinja2 templates, SQLite (existing `saeima_bills`/`saeima_bill_stages`/`saeima_bill_politicians` tables), pytest.

**Spec:** [`docs/superpowers/specs/2026-04-27-saeima-bills-phase-1c-design.md`](../specs/2026-04-27-saeima-bills-phase-1c-design.md)

---

## Task 0: Worktree setup + baseline tests

**Files:** none (procedural)

- [ ] **Step 1: Create worktree on a fresh branch**

```bash
git worktree add .worktrees/saeima-bills-phase-1c -b saeima-bills-phase-1c master
cd .worktrees/saeima-bills-phase-1c
```

- [ ] **Step 2: Activate venv and verify baseline tests still pass**

```bash
source .venv/Scripts/activate
python -m pytest tests/test_phase_1b_ii.py tests/test_generate_bills.py tests/test_generate.py tests/test_saeima_bills.py tests/test_saeima_bills_integration.py tests/test_saeima.py -q
```
Expected: `224 passed` (178 Phase 1B suite + 46 saeima).

- [ ] **Step 3: Snapshot DB counts (anchor for later regressions)**

```bash
PYTHONIOENCODING=utf-8 python -c "
import sqlite3
db = sqlite3.connect('data/atmina.db')
print('Bills:', db.execute('SELECT COUNT(*) FROM saeima_bills').fetchone()[0])
print('Stages:', db.execute('SELECT COUNT(*) FROM saeima_bill_stages').fetchone()[0])
print('base_law_slug:', db.execute('SELECT COUNT(*) FROM saeima_bills WHERE base_law_slug IS NOT NULL').fetchone()[0])
print('Junction:', db.execute('SELECT COUNT(*) FROM saeima_bill_politicians').fetchone()[0])
"
```
Expected: `Bills: 118`, `Stages: 138`, `base_law_slug: 41`, `Junction: 0`.

---

## Task 1: CLAUDE.md Pipeline Invariant 12

**Files:**
- Modify: `CLAUDE.md` (Pipeline Invariants section, after item 11)

- [ ] **Step 1: Add Invariant 12 to Pipeline Invariants section**

Insert after the existing item 11 ("`social_accounts` is X-only..."):

```markdown
12. **`saeima_votes.bill_id` un `saeima_bills.current_stage` atjauno tikai caur `append_bill_stage()`.** Nekādi citi `UPDATE` šajiem laukiem nav atļauti. Aizstāv denormalizācijas sinhroniju — vote→stage→bill timeline ir atomic, un manuāla rakstīšana plēš vēstures integritāti.
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs(claude): add Pipeline Invariant 12 — append_bill_stage discipline"
```

---

## Task 2: autolink_bills Jinja filter

**Files:**
- Create: `tests/test_autolink_bills.py`
- Modify: `src/generate.py` (filter implementation + registration ~line 71 area, ~line 2992 register)
- Modify: `templates/pretruna-detail.html.j2:60`
- Modify: `templates/politician.html.j2:281`
- Modify: `templates/pretrunas.html.j2:120`
- Modify: `templates/index.html.j2:147`
- Modify: `src/generate.py` — `_render_atmina_pages()` to pass `bill_slugs` in render contexts

### 2A. Write failing tests

- [ ] **Step 1: Create `tests/test_autolink_bills.py` with all 6 tests**

```python
"""Phase 1C — autolink_bills Jinja filter wraps bill references in <a> tags."""
import pytest

from src.generate import _autolink_bills_filter


def test_single_bill_match():
    out = _autolink_bills_filter("Atbalsta 1288/Lp14 likumprojektu", {"1288-lp14"})
    assert '<a href="likumprojekti/1288-lp14.html">1288/Lp14</a>' in out


def test_unknown_doc_nr_preserved():
    out = _autolink_bills_filter("Atbalsta 9999/Lp14", set())
    assert out == "Atbalsta 9999/Lp14"
    assert "<a" not in out


def test_multiple_bills_one_summary():
    out = _autolink_bills_filter("1288/Lp14 un 934/Lm14", {"1288-lp14", "934-lm14"})
    assert out.count("<a href=") == 2


def test_surrounding_punctuation():
    out = _autolink_bills_filter("(1288/Lp14), 934/Lm14.", {"1288-lp14", "934-lm14"})
    assert '>1288/Lp14</a>' in out
    assert '>934/Lm14</a>' in out


def test_word_boundary_no_partial_match():
    # Should NOT wrap "abc1288/Lp14def" — \b ensures clean boundaries
    out = _autolink_bills_filter("abc1288/Lp14def", {"1288-lp14"})
    assert "<a" not in out


def test_empty_text_and_none_slugs_graceful():
    assert _autolink_bills_filter("", set()) == ""
    assert _autolink_bills_filter(None, set()) == ""
    # bill_slugs=None must not crash (graceful default)
    assert _autolink_bills_filter("Atbalsta 1288/Lp14", None) == "Atbalsta 1288/Lp14"
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
python -m pytest tests/test_autolink_bills.py -v
```
Expected: 6 errors (`ImportError: cannot import name '_autolink_bills_filter' from 'src.generate'`).

### 2B. Implement filter

- [ ] **Step 3: Add `_autolink_bills_filter` near top of `src/generate.py`**

Add after the existing `_safe_url_filter` (around line 78):

```python
_BILL_REF_RE = re.compile(r"\b(\d+)/(Lp14|Lm14|P14)\b")


def _autolink_bills_filter(text: str, bill_slugs: set[str] | None = None) -> str:
    """Wrap '1288/Lp14' style references in <a href="likumprojekti/<slug>.html">.

    Unknown document_nr (slug not in bill_slugs) preserved as plain text — no
    broken links. Caller must ensure input is trusted (claim summaries are
    plain Latvian text); template uses `| safe` after this filter.
    bill_slugs=None is graceful (renders as plain text); never crash on
    missing context.
    """
    if not text:
        return text or ""
    bill_slugs = bill_slugs or set()

    def _sub(m: re.Match) -> str:
        nr, suffix = m.group(1), m.group(2)
        slug = f"{nr}-{suffix.lower()}"
        if slug not in bill_slugs:
            return m.group(0)
        return f'<a href="likumprojekti/{slug}.html">{m.group(0)}</a>'

    return _BILL_REF_RE.sub(_sub, text)
```

Note: `re` is already imported at the top of `src/generate.py`.

- [ ] **Step 4: Run tests, verify they pass**

```bash
python -m pytest tests/test_autolink_bills.py -v
```
Expected: 6 passed.

### 2C. Register filter + apply in templates

- [ ] **Step 5: Register filter in Jinja env (both registration sites)**

Find `env.filters["safe_url"] = _safe_url_filter` (line ~2992 and ~3745) — add a new line **immediately after each**:

```python
env.filters["autolink_bills"] = _autolink_bills_filter
```

- [ ] **Step 6: Build `bill_slugs` set in `_render_atmina_pages()` and pass it as a Jinja global**

In `src/generate.py` around line 3213 (right after `bills = _fetch_bills(db)`), add:

```python
bill_slugs = {b["slug"] for b in bills}
env.globals["bill_slugs"] = bill_slugs
```

Using `env.globals` instead of per-render context means every template can reference `bill_slugs` without each `_render_page()` call needing to thread it through — simpler maintenance and lower risk of forgetting a render site.

- [ ] **Step 7: Update 4 templates to apply the filter**

Edit `templates/pretruna-detail.html.j2:60` from:
```jinja
        <p>{{ c.summary }}</p>
```
to:
```jinja
        <p>{{ c.summary | autolink_bills(bill_slugs) | safe }}</p>
```

Edit `templates/politician.html.j2:281` from:
```jinja
          <p>{{ c.summary }}</p>
```
to:
```jinja
          <p>{{ c.summary | autolink_bills(bill_slugs) | safe }}</p>
```

Edit `templates/pretrunas.html.j2:120` from:
```jinja
        <p>{{ c.summary }}</p>
```
to:
```jinja
        <p>{{ c.summary | autolink_bills(bill_slugs) | safe }}</p>
```

Edit `templates/index.html.j2:147` from:
```jinja
        <p>{{ c.summary }}</p>
```
to:
```jinja
        <p>{{ c.summary | autolink_bills(bill_slugs) | safe }}</p>
```

Note: `pretruna-detail.html.j2` lines 6 and 9 use `c.summary|truncate(160)` for meta description / og — leave those alone (meta is plain text, not visible HTML).

- [ ] **Step 8: Regenerate site and smoke-check the rendered HTML**

```bash
PYTHONIOENCODING=utf-8 python -c "from src.generate import generate_public_site; generate_public_site()"
grep -c 'href="likumprojekti/.*\.html">[0-9]*/Lp14' output/atmina/pretrunas.html
```
Expected: at least 1 match (any pretruna whose summary mentions a bill DB knows). Zero matches is OK only if no pretrunas summary currently references a tracked bill — verify by also checking:
```bash
grep -c '/Lp14' output/atmina/pretrunas.html
grep -c '/Lp14' output/atmina/politiki/*.html | grep -v ':0$' | head
```
If those have references but the link grep returns 0, the filter is misregistered.

- [ ] **Step 9: Run full test suite, no regressions**

```bash
python -m pytest tests/ -q --ignore=tests/test_ingest.py --ignore=tests/test_wiki.py --ignore=tests/social_agent
```
Expected: 230 passed (224 baseline + 6 new). Pre-existing failures in `tests/test_ingest.py`, `tests/test_wiki.py`, `tests/social_agent/` are orthogonal — exclude with `--ignore`.

- [ ] **Step 10: Commit**

```bash
git add tests/test_autolink_bills.py src/generate.py templates/pretruna-detail.html.j2 templates/politician.html.j2 templates/pretrunas.html.j2 templates/index.html.j2
git commit -m "feat(generate): autolink_bills Jinja filter — wrap bill refs in <a> tags"
```

---

## Task 3: `/likumi.html` base-law index page

**Files:**
- Create: `tests/test_likumi_index.py`
- Modify: `src/generate.py` — add `_fetch_law_index_page()` + render call in `_render_atmina_pages()`
- Create: `templates/likumi-index.html.j2`
- Modify: `templates/balsojumi.html.j2` — footer link in `bills-list-tab`

### 3A. Write failing tests

- [ ] **Step 1: Create `tests/test_likumi_index.py`**

```python
"""Phase 1C — /likumi.html base-law index page."""
import os
import sqlite3
import tempfile
from pathlib import Path

import pytest

from src.db import init_db, get_db
from src.saeima import init_saeima_tables, load_laws_index
from src.generate import _fetch_law_index_page, generate_public_site


@pytest.fixture
def laws_dir() -> Path:
    """Use the real wiki/laws/ — index page reads it directly."""
    return Path("wiki/laws")


@pytest.fixture
def db_with_one_bill(laws_dir):
    """Fresh DB with saeima_bills + 1 row attached to a wiki/laws/ slug."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    init_saeima_tables(path)
    db = get_db(path)
    db.execute("""
        INSERT INTO saeima_bills (document_nr, bill_type, title, topic, base_law_slug,
                                  current_stage, current_status, first_seen_at,
                                  last_updated_at)
        VALUES ('1288/Lp14', 'Lp14', 'Grozījums Saeimas vēlēšanu likumā',
                'Tieslietas', 'saeimas-velesanu-likums',
                '1.lasījums', 'procesā', '2026-04-01 10:00:00', '2026-04-15 14:00:00')
    """)
    db.commit()
    yield path
    db.close()
    try:
        os.unlink(path)
    except PermissionError:
        pass


def test_includes_all_wiki_laws(db_with_one_bill, laws_dir):
    db = get_db(db_with_one_bill)
    rows = _fetch_law_index_page(db, laws_dir=laws_dir)
    db.close()
    assert len(rows) == len(load_laws_index(laws_dir))
    assert all("slug" in r and "title" in r for r in rows)


def test_law_with_attached_bills_has_count(db_with_one_bill, laws_dir):
    db = get_db(db_with_one_bill)
    rows = _fetch_law_index_page(db, laws_dir=laws_dir)
    db.close()
    sv = next(r for r in rows if r["slug"] == "saeimas-velesanu-likums")
    assert sv["bill_count"] == 1
    assert sv["topic"] == "Tieslietas"  # derived from saeima_bills.topic


def test_law_without_bills_renders_zero_and_empty_topic(db_with_one_bill, laws_dir):
    db = get_db(db_with_one_bill)
    rows = _fetch_law_index_page(db, laws_dir=laws_dir)
    db.close()
    no_bills = [r for r in rows if r["bill_count"] == 0]
    assert len(no_bills) > 0  # most laws in wiki/laws/ have no attached bill in this fixture
    assert all(r["topic"] == "" for r in no_bills)


def test_rows_sorted_alphabetically_by_title(db_with_one_bill, laws_dir):
    db = get_db(db_with_one_bill)
    rows = _fetch_law_index_page(db, laws_dir=laws_dir)
    db.close()
    titles = [r["title"] for r in rows]
    assert titles == sorted(titles, key=str.casefold)


def test_likumi_index_html_generated_by_full_pipeline(tmp_path, monkeypatch):
    """Smoke test: full generate_public_site() emits /likumi.html with expected content."""
    monkeypatch.chdir(Path(__file__).resolve().parent.parent)
    # Use the live data/atmina.db — generate_public_site reads it. Output goes to ./output.
    generate_public_site()
    site = Path("output/atmina")
    assert (site / "likumi.html").exists(), "/likumi.html was not generated"
    content = (site / "likumi.html").read_text(encoding="utf-8")
    assert "Pamatlikumi" in content
    assert 'href="likumi/saeimas-velesanu-likums.html"' in content
    # Footer link from /balsojumi.html
    balsojumi = (site / "balsojumi.html").read_text(encoding="utf-8")
    assert 'href="likumi.html"' in balsojumi
    assert "Visi pamatlikumi" in balsojumi
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
python -m pytest tests/test_likumi_index.py -v
```
Expected: 5 errors (`ImportError: cannot import name '_fetch_law_index_page' from 'src.generate'`).

### 3B. Implement data fetcher

- [ ] **Step 3: Add `_fetch_law_index_page()` in `src/generate.py`**

Insert immediately after `_generate_law_pages` (around line 1278, before `_fetch_votes`):

```python
def _fetch_law_index_page(
    db: sqlite3.Connection,
    laws_dir: Path = Path("wiki/laws"),
) -> list[dict[str, Any]]:
    """Build sortable index of base laws for /likumi.html.

    For each wiki/laws/<slug>.md (skipping likumi.md), join saeima_bills via
    base_law_slug to count attached likumprojekti and find the most recent
    activity date. Topic derives from saeima_bills.topic — most-frequent
    topic wins when a base law has bills across multiple topics. Empty
    bill_count is OK — signals no pending amendments.
    """
    from src.saeima import load_laws_index
    laws = load_laws_index(laws_dir)
    if not laws:
        return []

    counts_rows = db.execute("""
        SELECT base_law_slug,
               COUNT(*) AS bill_count,
               MAX(last_updated_at) AS last_activity
        FROM saeima_bills
        WHERE base_law_slug IS NOT NULL
        GROUP BY base_law_slug
    """).fetchall()
    counts = {r["base_law_slug"]: dict(r) for r in counts_rows}

    topic_rows = db.execute("""
        SELECT base_law_slug, topic, COUNT(*) AS n
        FROM saeima_bills
        WHERE base_law_slug IS NOT NULL AND topic IS NOT NULL
        GROUP BY base_law_slug, topic
        ORDER BY base_law_slug, n DESC
    """).fetchall()
    topics: dict[str, str] = {}
    for r in topic_rows:
        if r["base_law_slug"] not in topics:
            topics[r["base_law_slug"]] = r["topic"]

    out = []
    for slug, title in sorted(laws.items(), key=lambda kv: kv[1].casefold()):
        c = counts.get(slug, {})
        out.append({
            "slug": slug,
            "title": title,
            "topic": topics.get(slug, ""),
            "bill_count": c.get("bill_count", 0),
            "last_activity": c.get("last_activity", "") or "",
        })
    return out
```

- [ ] **Step 4: Run unit tests, verify 4 of 5 pass**

```bash
python -m pytest tests/test_likumi_index.py -v -k "not generated_by_full_pipeline"
```
Expected: 4 passed (the `_fetch_law_index_page` tests). The 5th test still needs the render call + template + footer link.

### 3C. Render call + template + footer link

- [ ] **Step 5: Wire render call in `_render_atmina_pages()`**

In `src/generate.py` around line 3210 (right after `law_count = _generate_law_pages(...)`), add:

```python
    laws_index = _fetch_law_index_page(db)
    law_topics = sorted({l["topic"] for l in laws_index if l["topic"]})
    _render_page(env, "likumi-index.html.j2", atmina_dir / "likumi.html", {
        "laws": laws_index,
        "law_topics": law_topics,
        "metrics": {
            "total": len(laws_index),
            "with_bills": sum(1 for l in laws_index if l["bill_count"] > 0),
        },
    })
    laws_index_count = len(laws_index)  # used by balsojumi.html footer below
```

Then update the existing `balsojumi.html.j2` render call (around line 3217) to pass `laws_index_count`:

```python
    _render_page(env, "balsojumi.html.j2", atmina_dir / "balsojumi.html", {
        "votes": votes,
        "vote_topics": vote_topics,
        "deputies": deputies,
        "vote_sessions": vote_sessions,
        "matrix_data": matrix_data,
        "matrix_json": matrix_json,
        "metrics": vote_metrics,
        "bills": bills,
        "bill_topics": bill_topics,
        "laws_index_count": laws_index_count,
    })
```

- [ ] **Step 6: Create `templates/likumi-index.html.j2`**

```jinja
{% extends "base.html.j2" %}
{% block title %}Pamatlikumi — atmīna.lv{% endblock %}
{% block description %}{{ metrics.total }} Latvijas pamatlikumi un to nesenie grozījumu likumprojekti.{% endblock %}
{% block content %}
<div class="page-header">
  <h1>Pamatlikumi</h1>
  <p class="muted">{{ metrics.total }} likumi · {{ metrics.with_bills }} ar aktīviem likumprojektiem</p>
</div>

<div class="filter-row" style="display:flex; gap:1rem; flex-wrap:wrap; margin-bottom:1.5rem;">
  <select id="law-topic-filter" onchange="window.applyLawsFilters()">
    <option value="">Visas tēmas</option>
    {% for t in law_topics %}<option value="{{ t }}">{{ t }}</option>{% endfor %}
  </select>
  <input type="search" id="law-search" placeholder="Meklēt nosaukumā..."
         oninput="window.applyLawsFilters()" class="bill-search-input">
</div>

<div class="bill-card-grid" id="laws-grid">
  {% for law in laws %}
  <a class="bill-card" href="likumi/{{ law.slug }}.html"
     data-topic="{{ law.topic }}" data-title="{{ law.title|lower }}">
    <div class="bill-card-title">{{ law.title }}</div>
    {% if law.topic %}<span class="topic-chip">{{ law.topic }}</span>{% endif %}
    <div class="bill-card-meta">
      {% if law.bill_count > 0 %}
        <span>{{ law.bill_count }} likumproj.</span>
        {% if law.last_activity %}<span class="muted">· {{ law.last_activity[:10] }}</span>{% endif %}
      {% else %}
        <span class="muted">nav aktīvu likumprojektu</span>
      {% endif %}
    </div>
  </a>
  {% endfor %}
</div>

<script>
window.applyLawsFilters = function() {
  var topic = document.getElementById('law-topic-filter').value;
  var q = (document.getElementById('law-search').value || '').toLowerCase();
  document.querySelectorAll('#laws-grid .bill-card').forEach(function(c) {
    var matchTopic = !topic || c.dataset.topic === topic;
    var matchQ = !q || c.dataset.title.indexOf(q) !== -1;
    c.style.display = (matchTopic && matchQ) ? '' : 'none';
  });
};
</script>
{% endblock %}
```

- [ ] **Step 7: Add footer link to `templates/balsojumi.html.j2`**

Find `<div id="bills-list-tab" style="display: none;">` (around line 259). Inside that div, find the closing `</div>` of the bills-grid section (after the `bill-card-grid` div ends). Insert immediately before that closing `</div>`:

```jinja
      <div style="margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid var(--border); font-size: 0.9rem;">
        <a href="likumi.html" class="muted-link">Visi pamatlikumi ({{ laws_index_count }}) →</a>
      </div>
```

To find the right insertion point, search for the line `<div class="bill-card-grid" id="bills-grid">` (around line 293) and locate its matching `</div>`. The footer goes after the matching `</div>` but still inside `bills-list-tab`.

- [ ] **Step 8: Regenerate site, run full likumi tests**

```bash
PYTHONIOENCODING=utf-8 python -c "from src.generate import generate_public_site; generate_public_site()"
python -m pytest tests/test_likumi_index.py -v
```
Expected: 5 passed.

- [ ] **Step 9: Visual smoke-check**

```bash
ls output/atmina/likumi.html
grep -c 'class="bill-card"' output/atmina/likumi.html
grep -c 'href="likumi.html"' output/atmina/balsojumi.html
```
Expected: file exists, 33 bill-card matches in `/likumi.html`, ≥1 match in `/balsojumi.html`.

- [ ] **Step 10: Run full suite, no regressions**

```bash
python -m pytest tests/ -q --ignore=tests/test_ingest.py --ignore=tests/test_wiki.py --ignore=tests/social_agent
```
Expected: 235 passed (224 baseline + 6 autolink + 5 likumi).

- [ ] **Step 11: Commit**

```bash
git add tests/test_likumi_index.py src/generate.py templates/likumi-index.html.j2 templates/balsojumi.html.j2
git commit -m "feat(generate): /likumi.html base-law index + balsojumi footer link"
```

---

## Task 4: `wiki/operations/saeima-bills.md` runbook

**Files:**
- Create: `wiki/operations/saeima-bills.md`

- [ ] **Step 1: Create the runbook file**

```markdown
# Saeima bills — operatorinstrukcija

## Mērķis

Likumprojektu (saeima_bills) izsekošana ļauj atmīnai sekot deputātu balsojumiem
**lielākā kontekstā**: katrs balsojums tiek piesaistīts likumprojektam → likumprojekta
stadijai → pamatlikumam (`base_law_slug`). Politiķa profila Likumprojekti tabs un
publiskā `/likumi.html` lapa atklāj šo plūsmu.

## Tipisks ciklis (jauna sēde)

1. Atver Saeimas kalendāru (`https://titania.saeima.lv/LIVS14/SaeimaLIVS2_DK.nsf/DK?ReadForm&calendar=1`),
   atrod nesenas balsojumu sesijas URL.
2. Palaiž `@saeima-tracker` aģentu ar sesijas URL.
3. Aģents:
   - Step 1-2: snapshot agendu, parse bills + URLs (Phase 1C jaunievedums)
   - Step 3-4: ievāc balsojumu rezultātus
   - Step 5: link vote → bill stage (Phase 1C jaunievedums)
4. Pārskata aģenta logus — STOP signāli (zem § Failure modes) prasa operatora
   darbību pirms turpināšanas.
5. Palaiž site renderēšanu:
   ```bash
   PYTHONIOENCODING=utf-8 python -c "from src.generate import generate_public_site; generate_public_site()"
   ```
6. Pārbauda:
   - `output/atmina/likumprojekti/<slug>.html` — jauni bill detail lapas
   - `output/atmina/likumi.html` — pamatlikumu indekss ar atjauninātu bill_count
   - `output/atmina/balsojumi.html#bills-list` — bills grid ar 3rd subtab

## Manuālā iesniedzēja pievienošana

Ja agents ziņo "STOP: unknown institutional submitter ...":

1. Pievieno jauno vērtību aģenta prompta `KNOWN_INSTITUTIONAL_SUBMITTERS`
   sarakstam (`.claude/agents/saeima-tracker.md` § Step 2.A.bis).
2. Ja jaunā vērtība arī nav atpazīta `parse_agenda_snapshot()` plūsmā,
   paplašini regex `_parse_institutional_submitter()` (`src/saeima.py:490`).
3. Re-run aģentu.

## Backfill atkārtošana

Šie skripti ir idempotenti (`WHERE base_law_slug IS NULL` filter aizsargā):

```bash
python scripts/backfill_saeima_bills.py        # restore bills + stages from votes
python scripts/backfill_base_law_slug.py       # restore base_law_slug matches
```

Drošs re-run, ja kāda lauka aizpilde palika nepilna pēc DB restore vai migration.

## Troubleshooting

### Agenda parse atgriež `[]`
HTML struktūra titania.saeima.lv mainīta. Atver sesijas URL pārlūkprogrammā,
salīdzina ar `parse_agenda_snapshot` regex (`src/saeima.py:504`). Ja .html ir
mainījies, fix parser pirms re-run.

### `base_law_slug=NULL` spītīgi
`title` lauks varbūt nesatur kanonisku likuma nosaukumu. Pārbaudi vai pareizais
`wiki/laws/<slug>.md` fails eksistē. Manuāli var iestatīt:
```sql
UPDATE saeima_bills SET base_law_slug='...' WHERE document_nr='...';
```
Tas ir viens no maziem izņēmumiem, kas NEIET caur Pipeline Invariant 12, jo
`base_law_slug` nav denormalizācija — tā ir join key.

### Junction empty pēc agent run
`match_submitters_to_politicians` fail-loud — pārbaudi `unmatched submitters`
logus. Visdrīzāk submitter_names lauka parsēšana neizdevās — atver
`parse_agenda_snapshot` output un salīdzina pret faktisko agenda HTML.

### Vote stored, bet bill_id NULL
`resolve_bill_from_motif()` neatpazina motif (Tier-3 gadījums, log+turpina).
Pārbaudi vai bill ar šo `document_nr` jau eksistē DB — ja nē, Step 2 droši vien
izlaida to (vai parse_agenda_snapshot to nesaprata).

## Saistītie faili
- `src/saeima.py` — visas helper funkcijas (`parse_agenda_snapshot`,
  `upsert_bill`, `match_submitters_to_politicians`, `append_bill_stage`,
  `resolve_bill_from_motif`)
- `.claude/agents/saeima-tracker.md` — aģenta operatorinstrukcija
- `tests/test_saeima_bills*.py` — Phase 1A unit + integration
- `wiki/CHANGELOG.md` — Phase 1A/B/C lēmumu vēsture
- `docs/superpowers/specs/2026-04-22-saeima-bills-design.md` — master spec
```

- [ ] **Step 2: Commit**

```bash
git add wiki/operations/saeima-bills.md
git commit -m "docs(operations): saeima-bills runbook — Phase 1C operator guide"
```

---

## Task 5: `@saeima-tracker` agent prompt update

**Files:**
- Modify: `.claude/agents/saeima-tracker.md`

This task is doc-only but spans several precise insertions. No tests — the prompt is validated by Task 6 (live smoke run).

- [ ] **Step 1: Replace existing Step 2 (`### Step 2: Extract voting URLs from the snapshot`) with the expanded version**

Find this block (lines ~37-40):
```markdown
### Step 2: Extract voting URLs from the snapshot
```bash
grep -oE '\./0/[A-F0-9]{32}\?OpenDocument' snapshot_file | sort -u
```
```

Replace with:

````markdown
### Step 2: Parse agenda — extract bills + voting URLs

The agenda snapshot from Step 1 holds BOTH:
  (a) the list of likumprojekti scheduled for this session (with submitters)
  (b) the URLs of the actual vote results pages.
Process both before moving to Step 3.

#### Step 2.A: Parse bills + match submitters

```python
from src.saeima import parse_agenda_snapshot, upsert_bill, match_submitters_to_politicians

with open('path/to/agenda_snapshot.md', encoding='utf-8') as f:
    snapshot_text = f.read()

agenda_bills = parse_agenda_snapshot(snapshot_text)
if not agenda_bills:
    print("WARN: parse_agenda_snapshot returned []. Likely HTML structure changed.")
    print("STOP — abort session, report to operator before proceeding.")
    raise SystemExit(1)

for ab in agenda_bills:
    # Validate institutional submitter against canonical list (see § 2.A.bis)
    if ab.institutional_submitter and ab.institutional_submitter not in KNOWN_INSTITUTIONAL_SUBMITTERS:
        print(f"  STOP: unknown institutional submitter {ab.institutional_submitter!r} for {ab.document_nr}")
        print("  Add to KNOWN_INSTITUTIONAL_SUBMITTERS list below before continuing.")
        raise SystemExit(1)

    bill_id = upsert_bill(
        db_path='data/atmina.db',
        document_nr=ab.document_nr,
        title=ab.title,
        bill_type=ab.bill_type,                      # 'Lp14' / 'Lm14' / 'P14'
        institutional_submitter=ab.institutional_submitter,
        # topic + base_law_slug auto-resolved by upsert_bill from title
    )
    matched, unmatched = match_submitters_to_politicians(
        db_path='data/atmina.db',
        bill_id=bill_id,
        submitter_names=ab.individual_submitters,
    )
    if unmatched:
        print(f"  unmatched submitters for {ab.document_nr}: {unmatched}")
        # Tier-2 deputy STOP rule (existing prompt §155) covers individuals.
```

#### Step 2.A.bis: Known institutional submitters (canonical list)

If `parse_agenda_snapshot` yields any other institutional submitter value, STOP
and ask the operator to extend this list (and, if necessary, the regex in
`src/saeima.py:_parse_institutional_submitter`). Silent acceptance creates
persistent misclassification — the discipline rule is mandatory.

```python
KNOWN_INSTITUTIONAL_SUBMITTERS = {
    "Ministru kabinets",
    "Saeimas Prezidijs",
    # Saeimas komisijas
    "Tautsaimniecības, agrārās, vides un reģionālās politikas komisija",
    "Juridiskā komisija",
    "Sociālo un darba lietu komisija",
    "Aizsardzības, iekšlietu un korupcijas novēršanas komisija",
    "Cilvēktiesību un sabiedrisko lietu komisija",
    "Izglītības, kultūras un zinātnes komisija",
    "Valsts pārvaldes un pašvaldības komisija",
    "Budžeta un finanšu (nodokļu) komisija",
    "Eiropas lietu komisija",
    "Mandātu, ētikas un iesniegumu komisija",
    "Publisko izdevumu un revīzijas komisija",
    "Pieprasījumu komisija",
    "Ārlietu komisija",
    "Ilgtspējīgas attīstības komisija",
    # Konstit. iestādes
    "Latvijas Bankas padome",
    "Augstākā tiesa",
    "Valsts kontrole",
}
```

#### Step 2.B: Extract voting URLs (existing)
```bash
grep -oE '\./0/[A-F0-9]{32}\?OpenDocument' snapshot_file | sort -u
```
````

- [ ] **Step 2: Add new Step 5 immediately after the existing Step 4 block**

Find the end of Step 4 (the `### Step 4: Parse and store using Python` block ends around line 94 with `print(result)" `). Insert immediately after that block:

````markdown

### Step 5: Link vote to bill stage

After each `store_vote()` returns `vote_id`, resolve which bill it advances and
write the stage row. This keeps `saeima_bills.current_stage` and the
denormalized timeline accurate. Phase 1C wires this in — Pipeline Invariant 12
(`CLAUDE.md`) makes `append_bill_stage()` the SOLE writer of `saeima_votes.bill_id`.

```python
from src.saeima import resolve_bill_from_motif, append_bill_stage, _reading_from_motif
from src.db import get_db

db = get_db('data/atmina.db')

# vote_db_id is the integer returned by store_vote() in Step 4
doc_nr = resolve_bill_from_motif(vote.motif)
if doc_nr is None:
    print(f"  no bill match for motif {vote.motif!r} — vote stored without bill_id")
else:
    bill = db.execute("SELECT id FROM saeima_bills WHERE document_nr=?", (doc_nr,)).fetchone()
    if bill is None:
        print(f"  WARN: motif resolved to {doc_nr} but no bill row — Step 2 may have skipped it")
    else:
        stage_name = _reading_from_motif(vote.motif)  # may return 'nezināms'
        append_bill_stage(
            db_path='data/atmina.db',
            bill_id=bill['id'],
            stage_name=stage_name,
            stage_result=vote.result,
            stage_date=vote.date,
            vote_id=vote_db_id,
        )
```

`stage_name='nezināms'` is acceptable — it's the visible signal that the motif's
reading wasn't classified. Don't invent a stage to fix it; report unusual motifs
back so the vocabulary can grow.
````

- [ ] **Step 3: Add Failure modes section before `## DO / DON'T (lessons from 2026-04-16 session)`**

Find the line `## DO / DON'T (lessons from 2026-04-16 session)` (around line 157). Insert this block **immediately before** that heading:

```markdown
## Failure modes — when to STOP vs log+continue

| Situation                                                                            | Action                |
|--------------------------------------------------------------------------------------|-----------------------|
| Unknown institutional submitter (not in `KNOWN_INSTITUTIONAL_SUBMITTERS` above)       | STOP, ask operator    |
| Unknown deputy (not in `tracked_politicians.name_forms`)                             | STOP, ask operator    |
| `parse_agenda_snapshot()` returns []                                                 | STOP, abort session   |
| `resolve_bill_from_motif()` returns None                                             | log, store vote w/o bill_id |
| `_reading_from_motif()` returns 'nezināms'                                           | log, append stage as-is |
| `upsert_bill()` raises ValueError on bill_type                                       | STOP, report          |

The first three create persistent silent corruption if ignored. The last three
are recoverable per-row — the agent flow continues, operator reviews logs after
the run.

```

- [ ] **Step 4: Verify the file is well-formed**

```bash
head -200 .claude/agents/saeima-tracker.md | wc -l
grep -c "^### Step" .claude/agents/saeima-tracker.md
```
Expected: file is now ~280 lines (up from ~197); 6 Step headings (1, 2, 3, 3.5, 4, 5).

- [ ] **Step 5: Commit**

```bash
git add .claude/agents/saeima-tracker.md
git commit -m "feat(saeima-tracker): Step 2 expand (parse agenda) + Step 5 (link vote→bill)"
```

---

## Task 6: Live smoke test (manual — operator-driven)

**Files:** none (validates prompt + glue end-to-end).

This task validates the agent prompt against a real Saeima session. It is
**operator-triggered** — no automated test substitute. Skip if no fresh session
URL is available; defer until next routine cycle.

- [ ] **Step 1: Pick a recent unscraped session**

Open the Saeima calendar:
```
https://titania.saeima.lv/LIVS14/SaeimaLIVS2_DK.nsf/DK?ReadForm&calendar=1
```
Pick a session whose `vote_date` is NOT already in `saeima_votes.vote_date`:
```bash
PYTHONIOENCODING=utf-8 python -c "
import sqlite3
db = sqlite3.connect('data/atmina.db')
for row in db.execute('SELECT DISTINCT vote_date FROM saeima_votes ORDER BY vote_date DESC LIMIT 10'):
    print(row[0])
"
```

- [ ] **Step 2: Invoke `@saeima-tracker` with the session URL**

Per the agent prompt's Workflow section. Watch the output for:
- "STOP" lines (unknown submitter / unknown deputy / parse fail) — action required
- "no bill match for motif" lines (Tier-3 log only — fine)
- "unmatched submitters" lines (deputy mismatch — investigate)

- [ ] **Step 3: Verify junction populates**

```bash
PYTHONIOENCODING=utf-8 python -c "
import sqlite3
db = sqlite3.connect('data/atmina.db')
print('Junction rows:', db.execute('SELECT COUNT(*) FROM saeima_bill_politicians').fetchone()[0])
print('Votes with bill_id:', db.execute('SELECT COUNT(*) FROM saeima_votes WHERE bill_id IS NOT NULL').fetchone()[0])
print('Bills:', db.execute('SELECT COUNT(*) FROM saeima_bills').fetchone()[0])
"
```
Expected: Junction > 0 (was 0 baseline), `bill_id` count up by ~80%+ of new votes, Bills count up by N (depending on session).

- [ ] **Step 4: Regenerate site, verify politiķa profila Likumprojekti tabs renders**

```bash
PYTHONIOENCODING=utf-8 python -c "from src.generate import generate_public_site; generate_public_site()"
```

Pick a politician whose junction got populated:
```bash
PYTHONIOENCODING=utf-8 python -c "
import sqlite3
db = sqlite3.connect('data/atmina.db')
row = db.execute('''
    SELECT tp.name, COUNT(*) AS n FROM saeima_bill_politicians bp
    JOIN tracked_politicians tp ON tp.id = bp.politician_id
    GROUP BY bp.politician_id ORDER BY n DESC LIMIT 1
''').fetchone()
print(row)
"
```

Open `output/atmina/politiki/<slug>.html` in browser, switch to "Likumprojekti" tab — should now show submitted bills (1B-ii rendered template, gated until junction populated).

---

## Task 7: CHANGELOG + finalize

**Files:**
- Modify: `wiki/CHANGELOG.md` (top — newest first)
- Modify: `wiki/index.md` (refresh status counts if needed)

- [ ] **Step 1: Add CHANGELOG entry at the top of `wiki/CHANGELOG.md`**

Insert under the `# Changelog` heading (above the most recent existing entry):

```markdown
## 2026-04-XX — Saeima Bills Phase 1C (orchestration & glue)

**TL;DR:** `@saeima-tracker` agent prompt expanded to populate
`saeima_bill_politicians` junction live (Step 2) and link votes to bill
stages (Step 5). Public site exposes `/likumi.html` base-law index +
auto-links bill references in claim summaries. CLAUDE.md gains Pipeline
Invariant 12.

**Why:** Phase 1A delivered helpers; Phase 1B delivered UI templates that
already accept the data shape. 1C is the glue layer that makes the
templates light up live, without any new core code path.

**What changed:**
- `.claude/agents/saeima-tracker.md` — Step 2 expanded to parse agenda
  bills + match submitters; new Step 5 links each vote to its bill stage
  via `append_bill_stage()`. Adds `KNOWN_INSTITUTIONAL_SUBMITTERS` prompt
  rule + Failure modes tier table.
- `src/generate.py` — `_autolink_bills_filter` Jinja filter wraps
  `\b\d+/(Lp14|Lm14|P14)\b` references in claim summaries with
  `<a href="likumprojekti/<slug>.html">`. `_fetch_law_index_page()`
  builds 33-row sortable index for `/likumi.html`.
- `templates/likumi-index.html.j2` — new (mirrors `/balsojumi.html#bills-list`
  pattern: topic chip + filter + search).
- `templates/balsojumi.html.j2` — footer link "Visi pamatlikumi (33) →" in
  bills-list-tab.
- `templates/{pretruna-detail,politician,pretrunas,index}.html.j2` —
  apply autolink_bills filter to claim summaries.
- `CLAUDE.md § Pipeline Invariants` — adds Invariant 12: append_bill_stage
  is the sole writer of `saeima_votes.bill_id` and
  `saeima_bills.current_stage`.
- `wiki/operations/saeima-bills.md` — new operator runbook.

**Tests:** 235 total (224 baseline + 6 autolink_bills + 5 likumi_index).

**Out of scope:** Top nav entry to `/likumi.html` (deferred); Phase 1.5
historical re-scrape; Phase 2 amendment authors; Phase 3 debates →
bill_id; backfilling submitters into existing 91 historical bills.
```

(Replace `XX` with actual merge date.)

- [ ] **Step 2: Refresh `wiki/index.md` status counts if 1C produced new bills/junction rows**

Open `wiki/index.md`, find the Saeima bills status line (currently mentions
"33 likumi" and "118 likumprojekti"). Update bill count and add junction
status if Task 6 ran. If Task 6 was skipped, this step is a no-op — just
verify counts are still correct.

- [ ] **Step 3: Run final verification**

```bash
python -m pytest tests/ -q --ignore=tests/test_ingest.py --ignore=tests/test_wiki.py --ignore=tests/social_agent
PYTHONIOENCODING=utf-8 python -c "from src.generate import generate_public_site; generate_public_site()"
ls output/atmina/likumi.html
grep -c 'class="bill-card"' output/atmina/likumi.html
```
Expected: 235 passed; site regenerates clean; `/likumi.html` exists with 33 cards.

- [ ] **Step 4: Final commit**

```bash
git add wiki/CHANGELOG.md wiki/index.md
git commit -m "chore(changelog): Phase 1C — orchestration & glue"
```

- [ ] **Step 5: Merge worktree branch back to master**

```bash
cd ../..   # back to main checkout
git merge --no-ff saeima-bills-phase-1c -m "Merge Phase 1C — saeima-tracker live wiring + /likumi.html"
git worktree remove .worktrees/saeima-bills-phase-1c
git branch -d saeima-bills-phase-1c
```

(Confirm with operator before merging — ultrareview optional but recommended.)

---

## Dependencies + ordering rationale

```
Task 0 (worktree+baseline) ─→ Task 1 (Invariant 12)
                            ├─→ Task 2 (autolink filter)
                            ├─→ Task 3 (/likumi.html)
                            └─→ Task 4 (runbook)
                                       ↓
                                Task 5 (agent prompt) — references Tasks 1-4 in body
                                       ↓
                                Task 6 (smoke, optional)
                                       ↓
                                Task 7 (CHANGELOG + merge)
```

Tasks 1-4 are independent in implementation but share the same worktree.
Task 5 references Invariant 12 + the runbook + the templates, so it goes
last among code changes. Task 6 is operator-triggered. Task 7 wraps up
docs and merges.

## Acceptance criteria recap (from spec § 6)

- 235 pytest passed (224 baseline + 11 new)
- `output/atmina/likumi.html` exists with 33 cards, topic filter works
- `output/atmina/balsojumi.html` has "Visi pamatlikumi" footer link
- `output/atmina/pretrunas.html` (and 3 other pages) auto-link `1288/Lp14`
  references when slug exists
- After Task 6 (live smoke): `saeima_bill_politicians > 0`,
  `saeima_votes.bill_id NOT NULL` count grows
- CLAUDE.md has Invariant 12; runbook exists; agent prompt has Step 2
  expansion + Step 5 + KNOWN_INSTITUTIONAL_SUBMITTERS list + Failure
  modes table
