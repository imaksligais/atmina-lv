# Pozīcijas V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the V2 handoff design (`atmina-handoff/atmina/project/src/pozicijas-v2.jsx`) to `/pozicijas.html` — sticky filter rail + dense editorial table + confidence indicator + client-side paginated UI.

**Architecture:** New `.pzv1-*` class scope that **reuses** the existing `--xv1-*` CSS variables (token block selector extended to both sections). Jinja2 template `pozicijas.html.j2` fully rewritten. New `assets/pzv1.js` holds all client behavior. Python side adds row enrichment + metrics helper + 26-topic color palette.

**Tech Stack:** Python 3.11, Jinja2, sqlite3, vanilla JavaScript, CSS Grid.

**Font constraint:** Serif is `Georgia, 'Times New Roman', serif` (shared `--xv1-serif` token). **NOT Newsreader** — it was dropped from the project because Newsreader renders Latvian diacritics incorrectly (committed in `53a347a`). Plan tasks must not reintroduce Newsreader references.

**Spec reference:** `docs/superpowers/specs/2026-04-18-pozicijas-v2-design.md`

**Branch:** `feat/pozicijas-v2` (forked from `design/pozicijas-v2` which holds the spec)

---

## Phase 1 — Data layer (`src/generate.py` + tests)

Files touched this phase:
- `src/generate.py` (modify)
- `tests/test_pozicijas_v2.py` (create)

Goal of phase: pure-function helpers + enrichment + updated render call, all covered by unit tests, before any template/CSS/JS work.

### Task 1.1: `_confidence_tier` helper

**Files:**
- Modify: `src/generate.py` (add helper near top alongside `PARTY_COLORS`, around line 108)
- Create: `tests/test_pozicijas_v2.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_pozicijas_v2.py`:

```python
"""Tests for Pozīcijas V2 data helpers in src/generate.py."""

import pytest

from src.generate import _confidence_tier


class TestConfidenceTier:
    def test_augsta_boundary(self):
        assert _confidence_tier(0.9) == "augsta"
        assert _confidence_tier(1.0) == "augsta"

    def test_laba_range(self):
        assert _confidence_tier(0.89) == "laba"
        assert _confidence_tier(0.75) == "laba"

    def test_merena_range(self):
        assert _confidence_tier(0.74) == "merena"
        assert _confidence_tier(0.0) == "merena"

    def test_none_is_merena(self):
        assert _confidence_tier(None) == "merena"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/Scripts/python -m pytest tests/test_pozicijas_v2.py -v
```

Expected: `ImportError: cannot import name '_confidence_tier' from 'src.generate'`

- [ ] **Step 3: Add the helper to `src/generate.py`**

Locate the existing `_party_short_name` function (around line 89–107). Immediately after it, insert:

```python
def _confidence_tier(c: float | None) -> str:
    """Map a numeric confidence (0.0–1.0) to the Pozīcijas V2 tier label.
    None falls through to 'merena' — conservative default for any future
    rows where extraction didn't record confidence."""
    if c is None:
        return "merena"
    if c >= 0.9:
        return "augsta"
    if c >= 0.75:
        return "laba"
    return "merena"
```

- [ ] **Step 4: Run test to verify it passes**

```bash
.venv/Scripts/python -m pytest tests/test_pozicijas_v2.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/generate.py tests/test_pozicijas_v2.py
git commit -m "feat(generate): add _confidence_tier helper for pozīcijas V2"
```

---

### Task 1.2: `PZV1_TOPIC_COLORS` dict

**Files:**
- Modify: `src/generate.py` (add dict near `PARTY_COLORS`)
- Modify: `tests/test_pozicijas_v2.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_pozicijas_v2.py`:

```python
from src.generate import PZV1_TOPIC_COLORS
from src.topic_map import TOPIC_GROUPS


class TestTopicColors:
    def test_covers_all_26_canonical_groups(self):
        canonical = set(TOPIC_GROUPS.keys())
        palette = set(PZV1_TOPIC_COLORS.keys())
        missing = canonical - palette
        assert not missing, f"missing colors for: {sorted(missing)}"

    def test_all_colors_are_hex(self):
        for group, color in PZV1_TOPIC_COLORS.items():
            assert color.startswith("#"), f"{group} color not hex: {color}"
            assert len(color) == 7, f"{group} color wrong length: {color}"

    def test_no_color_matches_party_palette(self):
        from src.generate import PARTY_COLORS
        party_colors = set(PARTY_COLORS.values())
        for group, color in PZV1_TOPIC_COLORS.items():
            assert color not in party_colors, \
                f"{group} color {color} clashes with a party color"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/Scripts/python -m pytest tests/test_pozicijas_v2.py::TestTopicColors -v
```

Expected: `ImportError`.

- [ ] **Step 3: Add the dict to `src/generate.py`**

Immediately after `_confidence_tier`, insert:

```python
# 26 canonical topic groups → chip colors for the Pozīcijas V2 feed.
# First 16 entries match the handoff palette (atmina-handoff/…/pozicijas-data.jsx).
# Last 10 are HSL-derived (L=62%, S=52%) at 36° intervals, avoiding PARTY_COLORS.
PZV1_TOPIC_COLORS: dict[str, str] = {
    "Aizsardzība un drošība":      "#dc2626",
    "airBaltic":                   "#2563eb",
    "Koalīcija un partijas":       "#a855f7",
    "Ukraina un Krievija":         "#eab308",
    "Valsts pārvalde":             "#64748b",
    "Ārpolitika":                  "#0891b2",
    "Vēlēšanas":                   "#ec4899",
    "Degviela un enerģētika":      "#f97316",
    "Tieslietas":                  "#16a34a",
    "Budžets un finanses":         "#84cc16",
    "Pašvaldības":                 "#06b6d4",
    "Imigrācija":                  "#d946ef",
    "Transports":                  "#14b8a6",
    "Sabiedriskie mediji":         "#f43f5e",
    "Droni":                       "#6366f1",
    "Sociālā politika":            "#8b5cf6",
    # handoff palette ends here — remaining 10 derived HSL rotation
    "ES politika":                 "#e17055",
    "Rail Baltica":                "#b89a5b",
    "Mežsaimniecība":              "#6b8e4e",
    "Valsts kapitālsabiedrības":   "#4fa58a",
    "Izglītība":                   "#5b8fb8",
    "Valodu politika":             "#7a6fb8",
    "Vide":                        "#b85b8f",
    "Pensijas":                    "#b87a5b",
    "Lauksaimniecība":             "#8fa55b",
    "Kultūra":                     "#5bb88e",
}
```

Note — these 26 colors avoid `PARTY_COLORS` (`#3b82f6, #84cc16, #22c55e, #a855f7, #ef4444, #06b6d4, #f97316, #14b8a6`). If the test fails on `no_color_matches_party_palette`, adjust by ±2 on the hue channel.

- [ ] **Step 4: Run test to verify it passes**

```bash
.venv/Scripts/python -m pytest tests/test_pozicijas_v2.py::TestTopicColors -v
```

Expected: 3 passed. If `no_color_matches_party_palette` fails, bump the clashing hex by a few units and rerun.

- [ ] **Step 5: Commit**

```bash
git add src/generate.py tests/test_pozicijas_v2.py
git commit -m "feat(generate): add PZV1_TOPIC_COLORS for 26 canonical topics"
```

---

### Task 1.3: `_fetch_pozicijas_metrics` helper

**Files:**
- Modify: `src/generate.py`
- Modify: `tests/test_pozicijas_v2.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_pozicijas_v2.py`:

```python
import sqlite3
from datetime import datetime, timedelta

from src.db import now_lv_dt


def _build_test_db() -> sqlite3.Connection:
    """In-memory SQLite with minimal schema for Pozīcijas V2 tests.

    Creates tracked_politicians + claims tables mirroring the production
    schema subset these helpers read from. Does NOT need vector tables.
    """
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE tracked_politicians (
            id INTEGER PRIMARY KEY,
            name TEXT,
            party TEXT,
            relationship_type TEXT DEFAULT 'tracked'
        );
        CREATE TABLE claims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            opponent_id INTEGER,
            topic TEXT,
            stance TEXT,
            source_url TEXT,
            stated_at TEXT,
            created_at TEXT,
            confidence REAL,
            salience REAL,
            claim_type TEXT DEFAULT 'position'
        );
    """)
    db.execute("INSERT INTO tracked_politicians (id, name, party) VALUES (1, 'Test Polit', 'JV')")
    return db


class TestFetchPozicijasMetrics:
    def test_empty_db(self):
        from src.generate import _fetch_pozicijas_metrics
        db = _build_test_db()
        m = _fetch_pozicijas_metrics(db)
        assert m == {"total": 0, "last_week": 0, "confidence_good_pct": 0}

    def test_counts_and_percentage(self):
        from src.generate import _fetch_pozicijas_metrics
        db = _build_test_db()
        # 4 rows: 2 augsta (both last week), 1 laba (old), 1 merena (last week)
        now = now_lv_dt()
        recent = now.strftime("%Y-%m-%d %H:%M:%S")
        old = (now - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        rows = [
            (1, "T", "s1", "u1", recent, recent, 0.95, 0.5, "position"),
            (1, "T", "s2", "u2", recent, recent, 0.92, 0.5, "position"),
            (1, "T", "s3", "u3", old,    old,    0.80, 0.5, "position"),
            (1, "T", "s4", "u4", recent, recent, 0.50, 0.5, "position"),
        ]
        db.executemany(
            "INSERT INTO claims (opponent_id, topic, stance, source_url, stated_at, created_at, confidence, salience, claim_type) VALUES (?,?,?,?,?,?,?,?,?)",
            rows,
        )
        m = _fetch_pozicijas_metrics(db)
        assert m["total"] == 4
        assert m["last_week"] == 3
        # 3 of 4 are ≥ 0.75 → 75%
        assert m["confidence_good_pct"] == 75

    def test_excludes_non_position_claim_types(self):
        from src.generate import _fetch_pozicijas_metrics
        db = _build_test_db()
        now = now_lv_dt().strftime("%Y-%m-%d %H:%M:%S")
        db.execute(
            "INSERT INTO claims (opponent_id, topic, stance, source_url, stated_at, created_at, confidence, claim_type) VALUES (1,'T','s','u',?,?,0.9,'saeima_vote')",
            (now, now),
        )
        m = _fetch_pozicijas_metrics(db)
        assert m["total"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/Scripts/python -m pytest tests/test_pozicijas_v2.py::TestFetchPozicijasMetrics -v
```

Expected: ImportError.

- [ ] **Step 3: Add the helper**

Find an existing `_fetch_*` helper in `src/generate.py` (e.g., `_fetch_claims` around line 471). Immediately after `_fetch_claims` — i.e., after its closing `return results` — insert:

```python
def _fetch_pozicijas_metrics(db: sqlite3.Connection) -> dict[str, int]:
    """Three header metrics for Pozīcijas V2:
    - total position claims
    - count stated in the last 7 days (Latvia time)
    - % with confidence ≥ 0.75 (rounded int).

    Excludes claim_type='saeima_vote' rows (Pozīcijas feed is position-only).
    """
    row = db.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN stated_at >= ? THEN 1 ELSE 0 END) AS last_week,
            SUM(CASE WHEN confidence >= 0.75 THEN 1 ELSE 0 END) AS good
        FROM claims
        WHERE claim_type = 'position'
    """, ((now_lv_dt() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S"),)).fetchone()

    total = row["total"] or 0
    good = row["good"] or 0
    return {
        "total": total,
        "last_week": row["last_week"] or 0,
        "confidence_good_pct": round((good / total) * 100) if total else 0,
    }
```

Verify the imports at the top of `src/generate.py` already include `timedelta` from `datetime`. If not, add:

```python
from datetime import date, datetime, timedelta
```

(adjust the existing `from datetime import ...` line to include `timedelta`).

Also verify `now_lv_dt` is imported from `src.db`. If not, add it to the existing import line.

- [ ] **Step 4: Run tests**

```bash
.venv/Scripts/python -m pytest tests/test_pozicijas_v2.py::TestFetchPozicijasMetrics -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add src/generate.py tests/test_pozicijas_v2.py
git commit -m "feat(generate): add _fetch_pozicijas_metrics helper"
```

---

### Task 1.4: `_fetch_claims` row enrichment

**Files:**
- Modify: `src/generate.py` (`_fetch_claims` function body)
- Modify: `tests/test_pozicijas_v2.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_pozicijas_v2.py`:

```python
class TestFetchClaimsEnrichment:
    def test_enrichment_fields_present(self):
        from src.generate import _fetch_claims
        db = _build_test_db()
        now = now_lv_dt().strftime("%Y-%m-%d %H:%M:%S")
        db.execute(
            "INSERT INTO claims (opponent_id, topic, stance, source_url, stated_at, created_at, confidence, claim_type) VALUES (1,'Aizsardzība','s','https://lsm.lv/raksts/a/b',?,?,0.95,'position')",
            (now, now),
        )
        rows = _fetch_claims(db)
        assert len(rows) == 1
        r = rows[0]
        assert r["party_color"] == "#3b82f6"      # JV color
        assert r["party_short"] == "JV"
        assert r["confidence_tier"] == "augsta"
        assert r["source_domain"] == "lsm.lv"
        assert r["date_iso"] == now[:10]

    def test_missing_party_fallback(self):
        from src.generate import _fetch_claims
        db = _build_test_db()
        db.execute("INSERT INTO tracked_politicians (id, name, party, relationship_type) VALUES (2, 'Lato Lapsa', NULL, 'neutral')")
        now = now_lv_dt().strftime("%Y-%m-%d %H:%M:%S")
        db.execute(
            "INSERT INTO claims (opponent_id, topic, stance, source_url, stated_at, created_at, confidence, claim_type) VALUES (2,'T','s','',?,?,0.5,'position')",
            (now, now),
        )
        rows = _fetch_claims(db)
        r = [x for x in rows if x["politician_name"] == "Lato Lapsa"][0]
        assert r["party_color"] == "#8b8fa3"
        assert r["party_short"] == "—"
        assert r["confidence_tier"] == "merena"
        assert r["source_domain"] == ""
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/Scripts/python -m pytest tests/test_pozicijas_v2.py::TestFetchClaimsEnrichment -v
```

Expected: `KeyError: 'party_color'` (or similar).

- [ ] **Step 3: Modify `_fetch_claims` to enrich each row**

Locate `_fetch_claims` in `src/generate.py` (around line 471). The current body iterates `rows` and appends `d` to `results`. Modify the loop so each dict includes the enrichment fields. Replace:

```python
    results = []
    for r in rows:
        d = dict(r)
        # Skip media accounts — they belong in X feed only
        if d["politician_name"] in MEDIA_ACCOUNTS:
            continue
        d["slug"] = _slugify(d["politician_name"])
        # Label: Komentētājs for journalists/influencers/neutrals without party
        if d.get("relationship_type") in ("journalist", "influencer", "neutral") and not d.get("party"):
            d["persona_type"] = "Komentētājs"
        else:
            d["persona_type"] = "Politiķis"
        results.append(d)
```

with:

```python
    results = []
    for r in rows:
        d = dict(r)
        # Skip media accounts — they belong in X feed only
        if d["politician_name"] in MEDIA_ACCOUNTS:
            continue
        d["slug"] = _slugify(d["politician_name"])
        # Label: Komentētājs for journalists/influencers/neutrals without party
        if d.get("relationship_type") in ("journalist", "influencer", "neutral") and not d.get("party"):
            d["persona_type"] = "Komentētājs"
        else:
            d["persona_type"] = "Politiķis"
        # Pozīcijas V2 enrichment
        party = d.get("party")
        d["party_color"] = PARTY_COLORS.get(party or "", "#8b8fa3")
        d["party_short"] = _party_short_name(party) if party else "—"
        d["confidence_tier"] = _confidence_tier(d.get("confidence"))
        src_url = d.get("source_url") or ""
        d["source_domain"] = urlparse(src_url).netloc if src_url else ""
        d["date_iso"] = (d.get("stated_at") or "")[:10]
        results.append(d)
```

Verify `urlparse` is imported at the top of `src/generate.py`. If not, add:

```python
from urllib.parse import urlparse
```

- [ ] **Step 4: Run tests**

```bash
.venv/Scripts/python -m pytest tests/test_pozicijas_v2.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/generate.py tests/test_pozicijas_v2.py
git commit -m "feat(generate): enrich _fetch_claims for pozīcijas V2 (party_color, party_short, confidence_tier, source_domain)"
```

---

### Task 1.5: Update pozicijas render call

**Files:**
- Modify: `src/generate.py` (around line 1994–2000)

No new tests this task — verified via Phase 5 integration run. We're just plumbing data into the template context.

- [ ] **Step 1: Read the current render call**

```bash
.venv/Scripts/python -c "with open('src/generate.py') as f: print(''.join(f.readlines()[1990:2005]))"
```

Expected to see the current block:

```python
    # 3. Pozīcijas — feed is position-only by construction (_fetch_claims
    # filters claim_type='position'); no vote rows arrive here.
    pozicijas_persons = sorted(set(c["politician_name"] for c in claims if c.get("politician_name")))
    _render_page(env, "pozicijas.html.j2", atmina_dir / "pozicijas.html", {
        "claims": claims,
        "topics": topics_with_counts,
        "parties": all_parties,
        "persons": pozicijas_persons,
    })
```

- [ ] **Step 2: Replace with enriched context**

Replace the block above with:

```python
    # 3. Pozīcijas V2 — feed is position-only by construction (_fetch_claims
    # filters claim_type='position'); no vote rows arrive here.
    metrics = _fetch_pozicijas_metrics(db)

    topics_with_counts_colors = [
        (name, count, PZV1_TOPIC_COLORS.get(name, "#8b8fa3"))
        for name, count in topics_with_counts
    ]

    parties_with_counts = []
    for pname in sorted({c["party"] for c in claims if c.get("party")}):
        parties_with_counts.append((
            pname,
            _party_short_name(pname),
            PARTY_COLORS.get(pname, "#8b8fa3"),
            sum(1 for c in claims if c.get("party") == pname),
        ))
    bez_partijas = sum(1 for c in claims if not c.get("party"))
    if bez_partijas:
        parties_with_counts.append(("Bez partijas", "—", "#8b8fa3", bez_partijas))

    # sorted by count desc so the rail surfaces the busy parties first
    parties_with_counts.sort(key=lambda p: -p[3])

    politicians_with_counts = sorted(
        (
            (n, _slugify(n), sum(1 for c in claims if c.get("politician_name") == n))
            for n in {c["politician_name"] for c in claims if c.get("politician_name")}
        ),
        key=lambda x: (-x[2], x[0]),
    )

    _render_page(env, "pozicijas.html.j2", atmina_dir / "pozicijas.html", {
        "claims": claims,
        "topics": topics_with_counts_colors,
        "parties_with_counts": parties_with_counts,
        "politicians_with_counts": politicians_with_counts,
        "metrics": metrics,
    })
```

- [ ] **Step 3: Verify generate.py still imports cleanly**

```bash
.venv/Scripts/python -c "from src.generate import generate_public_site; print('ok')"
```

Expected: `ok`.

- [ ] **Step 4: Run unit tests again to ensure no regression**

```bash
.venv/Scripts/python -m pytest tests/test_pozicijas_v2.py tests/test_generate.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/generate.py
git commit -m "feat(generate): enriched context for pozīcijas.html.j2 V2 render"
```

---

## Phase 2 — Template (`templates/pozicijas.html.j2`)

Files touched this phase:
- `templates/pozicijas.html.j2` (rewrite)

Goal of phase: replace the entire template with the V2 structure. This is static markup + a JS data feed — styling and behaviors land in Phase 3 and 4.

### Task 2.1: Full template rewrite

**Files:**
- Rewrite: `templates/pozicijas.html.j2`

- [ ] **Step 1: Write the new template**

Replace the entire contents of `templates/pozicijas.html.j2` with:

```jinja2
{% extends "base.html.j2" %}
{% set active_page = "pozicijas" %}
{% set assets_prefix = "" %}

{% block title %}Pozīcijas{% endblock %}

{% block content %}
<section class="pzv1-section">

  <header class="pzv1-header">
    <div class="pzv1-header-title">
      <div class="pzv1-kicker">Pozīciju reģistrs</div>
      <h1 class="pzv1-h1">Pozīcijas</h1>
    </div>
    <div class="pzv1-metrics">
      <div class="pzv1-metric">
        <span class="pzv1-metric-label">Kopā</span>
        <span class="pzv1-metric-value">{{ "{:,}".format(metrics.total).replace(",", " ") }}</span>
      </div>
      <div class="pzv1-metric">
        <span class="pzv1-metric-label">Pēdējā nedēļā</span>
        <span class="pzv1-metric-value">{{ metrics.last_week }}</span>
      </div>
      <div class="pzv1-metric">
        <span class="pzv1-metric-label">Ticamība ≥ laba</span>
        <span class="pzv1-metric-value">{{ metrics.confidence_good_pct }}%</span>
      </div>
    </div>
  </header>

  <div class="pzv1-grid">

    <aside class="pzv1-aside">
      <div class="pzv1-rail-group">
        <div class="pzv1-rail-title">Tēma</div>
        <div class="pzv1-rail-rows" id="pzv1-rail-topics">
          <button type="button" class="pzv1-rail-row is-active" data-axis="topic" data-value="visas">
            <span class="pzv1-rail-dot" aria-hidden="true"></span>
            <span class="pzv1-rail-label">Visas tēmas</span>
            <span class="pzv1-rail-count">{{ claims|length }}</span>
          </button>
          {% for name, count, color in topics[:10] %}
          <button type="button" class="pzv1-rail-row" data-axis="topic" data-value="{{ name }}" data-color="{{ color }}">
            <span class="pzv1-rail-dot" style="background:{{ color }}"></span>
            <span class="pzv1-rail-label">{{ name }}</span>
            <span class="pzv1-rail-count">{{ count }}</span>
          </button>
          {% endfor %}
          {% if topics|length > 10 %}
          <button type="button" class="pzv1-rail-more" id="pzv1-topic-more">+ rādīt visas {{ topics|length }} →</button>
          <div class="pzv1-rail-hidden" hidden>
            {% for name, count, color in topics[10:] %}
            <button type="button" class="pzv1-rail-row" data-axis="topic" data-value="{{ name }}" data-color="{{ color }}">
              <span class="pzv1-rail-dot" style="background:{{ color }}"></span>
              <span class="pzv1-rail-label">{{ name }}</span>
              <span class="pzv1-rail-count">{{ count }}</span>
            </button>
            {% endfor %}
          </div>
          {% endif %}
        </div>
      </div>

      <div class="pzv1-rail-group">
        <div class="pzv1-rail-title">Partija</div>
        <div class="pzv1-rail-rows" id="pzv1-rail-parties">
          <button type="button" class="pzv1-rail-row is-active" data-axis="party" data-value="Visas">
            <span class="pzv1-rail-dot" aria-hidden="true"></span>
            <span class="pzv1-rail-label">Visas partijas</span>
            <span class="pzv1-rail-count">{{ claims|length }}</span>
          </button>
          {% for name, short, color, count in parties_with_counts %}
          <button type="button" class="pzv1-rail-row" data-axis="party" data-value="{{ name }}" data-color="{{ color }}">
            <span class="pzv1-rail-dot" style="background:{{ color }}"></span>
            <span class="pzv1-rail-label">{{ name }}</span>
            <span class="pzv1-rail-count">{{ count }}</span>
          </button>
          {% endfor %}
        </div>
      </div>

      <details class="pzv1-rail-group pzv1-rail-details" id="pzv1-rail-persons">
        <summary class="pzv1-rail-title">Persona <span class="pzv1-rail-caret">▾</span></summary>
        <div class="pzv1-rail-search">
          <input type="text" class="pzv1-rail-search-input" placeholder="Meklēt personu…">
        </div>
        <div class="pzv1-rail-rows pzv1-rail-rows-scroll">
          {% for name, slug, count in politicians_with_counts %}
          <button type="button" class="pzv1-rail-row pzv1-rail-person" data-axis="person" data-value="{{ name }}">
            <span class="pzv1-rail-checkbox" aria-hidden="true"></span>
            <span class="pzv1-rail-label">{{ name }}</span>
            <span class="pzv1-rail-count">{{ count }}</span>
          </button>
          {% endfor %}
        </div>
      </details>

      <div class="pzv1-rail-group">
        <div class="pzv1-rail-title">Periods</div>
        <div class="pzv1-rail-rows">
          <button type="button" class="pzv1-rail-row" data-axis="period" data-value="nedela">
            <span class="pzv1-rail-dot" aria-hidden="true"></span>
            <span class="pzv1-rail-label">Pēdējā nedēļa</span>
            <span class="pzv1-rail-count" data-count-for="period:nedela">0</span>
          </button>
          <button type="button" class="pzv1-rail-row" data-axis="period" data-value="menesis">
            <span class="pzv1-rail-dot" aria-hidden="true"></span>
            <span class="pzv1-rail-label">Šomēnes</span>
            <span class="pzv1-rail-count" data-count-for="period:menesis">0</span>
          </button>
          <button type="button" class="pzv1-rail-row" data-axis="period" data-value="gads">
            <span class="pzv1-rail-dot" aria-hidden="true"></span>
            <span class="pzv1-rail-label">Šogad</span>
            <span class="pzv1-rail-count" data-count-for="period:gads">0</span>
          </button>
          <button type="button" class="pzv1-rail-row is-active" data-axis="period" data-value="visi">
            <span class="pzv1-rail-dot" aria-hidden="true"></span>
            <span class="pzv1-rail-label">Visi</span>
            <span class="pzv1-rail-count">{{ claims|length }}</span>
          </button>
        </div>
      </div>

      <div class="pzv1-rail-group">
        <div class="pzv1-rail-title">Ticamība</div>
        <div class="pzv1-rail-rows">
          <button type="button" class="pzv1-rail-row" data-axis="confidence" data-value="augsta">
            <span class="pzv1-rail-dot" aria-hidden="true"></span>
            <span class="pzv1-rail-label">Augsta (≥0.9)</span>
            <span class="pzv1-rail-count" data-count-for="confidence:augsta">0</span>
          </button>
          <button type="button" class="pzv1-rail-row" data-axis="confidence" data-value="laba">
            <span class="pzv1-rail-dot" aria-hidden="true"></span>
            <span class="pzv1-rail-label">Laba (≥0.75)</span>
            <span class="pzv1-rail-count" data-count-for="confidence:laba">0</span>
          </button>
          <button type="button" class="pzv1-rail-row is-active" data-axis="confidence" data-value="visas">
            <span class="pzv1-rail-dot" aria-hidden="true"></span>
            <span class="pzv1-rail-label">Visas</span>
            <span class="pzv1-rail-count">{{ claims|length }}</span>
          </button>
        </div>
      </div>
    </aside>

    <main class="pzv1-main">
      <div class="pzv1-searchbar">
        <svg class="pzv1-search-icon" viewBox="0 0 16 16" aria-hidden="true"><circle cx="7" cy="7" r="5" fill="none" stroke="currentColor" stroke-width="1.2"/><line x1="11" y1="11" x2="14" y2="14" stroke="currentColor" stroke-width="1.2"/></svg>
        <input type="text" class="pzv1-search-input" id="pzv1-search" placeholder="Meklēt politiķi, tēmu, atslēgvārdu…">
        <button type="button" class="pzv1-clear-chip" id="pzv1-clear" hidden>Notīrīt ✕</button>
      </div>

      <div class="pzv1-sortbar">
        <span class="pzv1-showing">Rāda <span id="pzv1-shown">0</span> no <span id="pzv1-total">{{ claims|length }}</span></span>
        <span class="pzv1-sortbar-spacer"></span>
        <span class="pzv1-sortbar-label">Kārtot:</span>
        <button type="button" class="pzv1-sortbtn is-active" data-sort="date">datums ↓</button>
        <button type="button" class="pzv1-sortbtn" data-sort="confidence">ticamība</button>
        <button type="button" class="pzv1-sortbtn" data-sort="topic">tēma</button>
      </div>

      <div class="pzv1-thead">
        <div>Persona</div>
        <div>Tēma</div>
        <div>Pozīcija</div>
        <div class="pzv1-thead-right">Datums</div>
        <div class="pzv1-thead-right">Ticamība / avots</div>
      </div>

      <div class="pzv1-rows" id="pzv1-rows" aria-live="polite"></div>

      <div class="pzv1-pagination" id="pzv1-pagination"></div>
    </main>

  </div>
</section>
{% endblock %}

{% block scripts %}
<script>
var _pzData = [
  {% for c in claims %}
  [{{ c.topic|tojson }},{{ (c.party or '')|tojson }},{{ c.party_short|tojson }},{{ c.party_color|tojson }},{{ c.politician_name|tojson }},{{ c.slug|tojson }},{{ (c.stance or '')|tojson }},{{ c.date_iso|tojson }},{{ (c.source_url or '')|tojson }},{{ c.source_domain|tojson }},{{ (c.confidence or 0.0)|tojson }},{{ c.confidence_tier|tojson }}]{% if not loop.last %},{% endif %}
  {% endfor %}
];
</script>
<script src="assets/pzv1.js?v={{ assets_version }}"></script>
{% endblock %}
```

Note the data tuple order — **12 fields**:

`[topic, party, partyShort, partyColor, person, slug, stanceText, dateISO, sourceUrl, sourceDomain, confidence, confidenceTier]`

The JS code in Phase 4 reads these by positional index, so the order matters.

- [ ] **Step 2: Verify Jinja renders without syntax errors**

```bash
.venv/Scripts/python -c "from src.generate import generate_public_site; generate_public_site()"
```

Expected: site regenerates. Warnings about missing pzv1.js are OK at this stage (CSS/JS added in later phases).

- [ ] **Step 3: Sanity-check the emitted HTML**

```bash
.venv/Scripts/python -c "
path = 'output/atmina/pozicijas.html'
with open(path, encoding='utf-8') as f: html = f.read()
print('has pzv1-section:', 'pzv1-section' in html)
print('has _pzData:', '_pzData' in html)
print('claims rows:', html.count('pzv1-rail-person'))
print('metrics:', 'Kopā' in html, 'Pēdējā nedēļā' in html, 'Ticamība ≥ laba' in html)
"
```

Expected — all True. The `_pzData` array has one row per claim; rail has one `pzv1-rail-person` per tracked politician.

- [ ] **Step 4: Commit**

```bash
git add templates/pozicijas.html.j2
git commit -m "feat(templates): rewrite pozicijas.html.j2 to V2 two-column layout"
```

---

## Phase 3 — CSS (`assets/style.css`)

Files touched this phase:
- `assets/style.css` (modify one selector, append new block)

Goal of phase: tokens available on `.pzv1-section`, full `.pzv1-*` style block lands at the end of the stylesheet. After this phase, an unstyled-to-styled visual jump appears on `/pozicijas.html`.

### Task 3.1: Share CSS tokens between xv1 and pzv1

**Files:**
- Modify: `assets/style.css:2537`

- [ ] **Step 1: Edit one selector**

Find line 2537 `.xv1-section {` and change it to:

```css
.xv1-section,
.pzv1-section {
```

No other change — the rest of the block (all `--xv1-*` variable declarations plus `font-family`, `color`, `border-top`) applies to both sections automatically.

- [ ] **Step 2: Verify X tab still renders identically**

```bash
.venv/Scripts/python -c "from src.generate import generate_public_site; generate_public_site()"
```

Manual check: `python serve.py`, visit `http://127.0.0.1:8080/x.html`. Page should look identical to before this edit.

- [ ] **Step 3: Commit**

```bash
git add assets/style.css
git commit -m "feat(style): extend xv1 token block to apply to pzv1-section"
```

---

### Task 3.2: `.pzv1-*` header + grid + aside structure

**Files:**
- Modify: `assets/style.css` (append)

- [ ] **Step 1: Append the header + grid + aside block at EOF**

Open `assets/style.css`, go to the very end, and append:

```css

/* ====================================================================
   Pozīcijas V2 — dense editorial table with sticky filter rail.
   Reuses --xv1-* tokens (shared with X tab). Scope: .pzv1-*
   ==================================================================== */

/* ---- Header ---- */
.pzv1-header {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 40px;
  align-items: end;
  padding: 36px 0 24px;
  border-bottom: 1px solid var(--xv1-border-soft);
}
.pzv1-kicker {
  font-family: var(--xv1-mono);
  font-size: 11px;
  letter-spacing: 1.4px;
  text-transform: uppercase;
  color: var(--xv1-text-muted);
  margin-bottom: 10px;
}
.pzv1-h1 {
  font-family: var(--xv1-serif);
  font-size: 40px;
  font-weight: 500;
  letter-spacing: -0.8px;
  line-height: 1;
  margin: 0;
}
.pzv1-metrics { display: flex; gap: 32px; }
.pzv1-metric { display: flex; flex-direction: column; gap: 4px; }
.pzv1-metric-label {
  font-family: var(--xv1-mono);
  font-size: 10px;
  letter-spacing: 0.8px;
  text-transform: uppercase;
  color: var(--xv1-text-muted);
}
.pzv1-metric-value {
  font-family: var(--xv1-serif);
  font-size: 26px;
  font-weight: 500;
  letter-spacing: -0.4px;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}

/* ---- Grid ---- */
.pzv1-grid {
  display: grid;
  grid-template-columns: 240px 1fr;
  align-items: start;
}

/* ---- Aside (sticky filter rail) ---- */
.pzv1-aside {
  position: sticky;
  top: 0;
  align-self: start;
  max-height: 100vh;
  overflow-y: auto;
  padding: 22px 20px 40px 0;
  border-right: 1px solid var(--xv1-border-soft);
  scrollbar-width: thin;
}

.pzv1-rail-group {
  margin-bottom: 22px;
}
.pzv1-rail-title {
  font-family: var(--xv1-mono);
  font-size: 9px;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: var(--xv1-text-muted);
  padding-bottom: 6px;
  margin-bottom: 10px;
  border-bottom: 1px solid var(--xv1-border-soft);
  cursor: default;
}
.pzv1-rail-rows { display: flex; flex-direction: column; }
```

- [ ] **Step 2: Verify X tab still unaffected, pozicijas shows top of page**

```bash
.venv/Scripts/python -c "from src.generate import generate_public_site; generate_public_site()"
```

Open `/pozicijas.html` — header with metrics should now be visible (unstyled elsewhere, expected).

- [ ] **Step 3: Commit**

```bash
git add assets/style.css
git commit -m "feat(style): pzv1 header + grid + aside structure"
```

---

### Task 3.3: Rail rows, dots, active state, persons details

**Files:**
- Modify: `assets/style.css` (append)

- [ ] **Step 1: Append rail row primitives**

Continue appending at EOF:

```css

.pzv1-rail-row {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 8px;
  padding: 5px 10px 5px 0;
  background: transparent;
  border: none;
  border-left: 2px solid transparent;
  margin-left: -10px;
  padding-left: 8px;
  text-align: left;
  font-family: var(--xv1-serif);
  font-size: 13px;
  color: var(--xv1-text-muted);
  cursor: pointer;
  transition: color 80ms ease, background 80ms ease;
}
.pzv1-rail-row:hover {
  color: var(--xv1-text);
  background: var(--xv1-surface);
}
.pzv1-rail-row.is-active {
  color: var(--xv1-text);
  font-weight: 500;
  border-left-color: var(--xv1-brand-red);
}
.pzv1-rail-row.is-active[data-color] {
  border-left-color: attr(data-color); /* fallback below */
}
.pzv1-rail-dot {
  width: 6px;
  height: 6px;
  flex-shrink: 0;
}
.pzv1-rail-checkbox {
  width: 10px;
  height: 10px;
  border: 1px solid var(--xv1-text-dim);
  display: inline-block;
  flex-shrink: 0;
}
.pzv1-rail-row.is-active .pzv1-rail-checkbox {
  background: var(--xv1-text);
  border-color: var(--xv1-text);
}
.pzv1-rail-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}
.pzv1-rail-count {
  font-family: var(--xv1-mono);
  font-size: 10px;
  color: var(--xv1-text-dim);
  font-variant-numeric: tabular-nums;
}
.pzv1-rail-more {
  font-family: var(--xv1-mono);
  font-size: 9px;
  letter-spacing: 0.6px;
  text-transform: uppercase;
  color: var(--xv1-text-dim);
  padding: 6px 0;
  background: transparent;
  border: none;
  cursor: pointer;
  text-align: left;
}
.pzv1-rail-more:hover { color: var(--xv1-text-muted); }

/* Persons details group */
.pzv1-rail-details > summary {
  list-style: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
}
.pzv1-rail-details > summary::-webkit-details-marker { display: none; }
.pzv1-rail-caret {
  margin-left: auto;
  font-size: 10px;
  color: var(--xv1-text-dim);
}
.pzv1-rail-details[open] .pzv1-rail-caret { transform: rotate(180deg); }
.pzv1-rail-search {
  padding: 6px 0 8px;
}
.pzv1-rail-search-input {
  width: 100%;
  background: var(--xv1-surface);
  border: 1px solid var(--xv1-border-soft);
  color: var(--xv1-text);
  font-family: var(--xv1-serif);
  font-size: 12px;
  padding: 5px 8px;
  outline: none;
}
.pzv1-rail-search-input:focus {
  border-color: var(--xv1-border);
}
.pzv1-rail-rows-scroll {
  max-height: 280px;
  overflow-y: auto;
  scrollbar-width: thin;
}
.pzv1-rail-person.is-hidden { display: none; }
```

`attr(data-color)` in CSS is not universally supported for non-content properties. The fallback for active rail rows with custom colors is set inline by the JS in Phase 4 via `element.style.borderLeftColor`. The CSS rule above is decorative — real binding happens in JS. Leaving the CSS rule in as documentation is fine (noop effect in Chrome/Firefox).

- [ ] **Step 2: Regenerate + visually check rail has vertical flow + hover**

```bash
.venv/Scripts/python -c "from src.generate import generate_public_site; generate_public_site()"
```

Visit `/pozicijas.html`. Rail should show Tēma / Partija / Persona / Periods / Ticamība sections vertically; hover on any row should show slight bg.

- [ ] **Step 3: Commit**

```bash
git add assets/style.css
git commit -m "feat(style): pzv1 rail rows, dots, checkboxes, persons details"
```

---

### Task 3.4: Main area — searchbar, sortbar, thead, rows

**Files:**
- Modify: `assets/style.css` (append)

- [ ] **Step 1: Append main area styles**

```css

/* ---- Main (search + sort + table) ---- */
.pzv1-main { min-width: 0; }

.pzv1-searchbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 22px;
  border-bottom: 1px solid var(--xv1-border-soft);
}
.pzv1-search-icon {
  width: 14px;
  height: 14px;
  color: var(--xv1-text-dim);
  flex-shrink: 0;
}
.pzv1-search-input {
  flex: 1;
  background: transparent;
  border: none;
  color: var(--xv1-text);
  font-family: var(--xv1-serif);
  font-size: 15px;
  font-style: italic;
  padding: 4px 0;
  outline: none;
  letter-spacing: -0.1px;
}
.pzv1-search-input:not(:placeholder-shown) { font-style: normal; }
.pzv1-clear-chip {
  font-family: var(--xv1-mono);
  font-size: 10px;
  letter-spacing: 0.8px;
  text-transform: uppercase;
  color: var(--xv1-text-muted);
  background: transparent;
  border: none;
  cursor: pointer;
  flex-shrink: 0;
}
.pzv1-clear-chip:hover { color: var(--xv1-text); }

.pzv1-sortbar {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 22px;
  border-bottom: 1px solid var(--xv1-border-soft);
  font-family: var(--xv1-mono);
  font-size: 10px;
  color: var(--xv1-text-muted);
  letter-spacing: 0.8px;
  text-transform: uppercase;
}
.pzv1-showing { font-variant-numeric: tabular-nums; }
.pzv1-showing #pzv1-shown, .pzv1-showing #pzv1-total { color: var(--xv1-text); }
.pzv1-sortbar-spacer { flex: 1; }
.pzv1-sortbar-label { letter-spacing: 0.8px; }
.pzv1-sortbtn {
  font-family: var(--xv1-mono);
  font-size: 10px;
  letter-spacing: 0.8px;
  text-transform: uppercase;
  color: var(--xv1-text-muted);
  background: transparent;
  border: none;
  border-bottom: 1px solid transparent;
  padding: 0 0 2px;
  cursor: pointer;
}
.pzv1-sortbtn:hover { color: var(--xv1-text); }
.pzv1-sortbtn.is-active {
  color: var(--xv1-text);
  border-bottom-color: var(--xv1-brand-red);
}

/* ---- Table head + rows ---- */
.pzv1-thead,
.pzv1-row {
  display: grid;
  grid-template-columns: 160px 120px 1fr 80px 100px;
  gap: 14px;
  padding: 10px 22px 9px;
}
.pzv1-thead {
  font-family: var(--xv1-mono);
  font-size: 9px;
  color: var(--xv1-text-dim);
  letter-spacing: 1px;
  text-transform: uppercase;
  border-bottom: 1px solid var(--xv1-border);
}
.pzv1-thead-right { text-align: right; }

.pzv1-row {
  padding: 12px 22px;
  align-items: flex-start;
  border-bottom: 1px solid var(--xv1-border-soft);
  border-left: 2px solid transparent;
  margin-left: 0;
  cursor: pointer;
}
.pzv1-row:hover {
  background: var(--xv1-surface);
}

.pzv1-row-persona-name {
  font-family: var(--xv1-serif);
  font-size: 13px;
  font-weight: 500;
}
.pzv1-row-persona-name a { color: inherit; text-decoration: none; }
.pzv1-row-persona-name a:hover { text-decoration: underline; text-underline-offset: 2px; }
.pzv1-row-party {
  font-family: var(--xv1-mono);
  font-size: 9px;
  letter-spacing: 0.6px;
  text-transform: uppercase;
  margin-top: 3px;
}
.pzv1-row-topic-chip {
  font-family: var(--xv1-mono);
  font-size: 9px;
  letter-spacing: 0.6px;
  text-transform: uppercase;
  padding: 2px 6px;
  display: inline-block;
  border: 1px solid;
  cursor: pointer;
  background: transparent;
}
.pzv1-row-stance-tag {
  font-family: var(--xv1-mono);
  font-size: 9px;
  letter-spacing: 0.6px;
  text-transform: uppercase;
  font-weight: 500;
  color: var(--xv1-text-dim);
  margin-bottom: 4px;
}
.pzv1-row-text {
  font-family: var(--xv1-serif);
  font-size: 14px;
  line-height: 1.45;
  margin: 0;
  letter-spacing: -0.05px;
  text-wrap: pretty;
}
.pzv1-row-date {
  font-family: var(--xv1-mono);
  font-size: 10px;
  color: var(--xv1-text-muted);
  text-align: right;
  letter-spacing: 0.4px;
}
.pzv1-row-confidence {
  font-family: var(--xv1-mono);
  font-size: 10px;
  text-align: right;
  display: flex;
  flex-direction: column;
  gap: 3px;
  align-items: flex-end;
}
.pzv1-conf-dots {
  display: inline-flex;
  gap: 3px;
  align-items: center;
}
.pzv1-conf-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  border: 1px solid var(--xv1-text-dim);
  box-sizing: border-box;
}
.pzv1-conf-dot.is-on {
  background: var(--xv1-text);
  border-color: var(--xv1-text);
}
.pzv1-conf-label {
  letter-spacing: 0.4px;
  text-transform: uppercase;
  color: var(--xv1-text-muted);
}
.pzv1-row-source {
  color: var(--xv1-text-muted);
  text-decoration: none;
}
.pzv1-row-source:hover {
  color: var(--xv1-text);
  text-decoration: underline;
  text-underline-offset: 2px;
}

.pzv1-empty {
  padding: 60px 22px;
  text-align: center;
  font-family: var(--xv1-serif);
  font-style: italic;
  font-size: 17px;
  color: var(--xv1-text-muted);
}
```

- [ ] **Step 2: Regenerate — empty rows, sort bar visible**

```bash
.venv/Scripts/python -c "from src.generate import generate_public_site; generate_public_site()"
```

Rows area is still empty (JS hasn't rendered yet), but sort bar + thead + empty list should be styled.

- [ ] **Step 3: Commit**

```bash
git add assets/style.css
git commit -m "feat(style): pzv1 searchbar, sortbar, thead, row primitives"
```

---

### Task 3.5: Pagination + responsive

**Files:**
- Modify: `assets/style.css` (append)

- [ ] **Step 1: Append pagination + media query**

```css

/* ---- Pagination ---- */
.pzv1-pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  padding: 14px 22px;
  background: var(--xv1-surface);
  font-family: var(--xv1-mono);
  font-size: 10px;
  color: var(--xv1-text-muted);
  letter-spacing: 0.8px;
  text-transform: uppercase;
}
.pzv1-pagination button {
  font: inherit;
  background: transparent;
  border: none;
  color: inherit;
  cursor: pointer;
  padding: 2px 4px;
  letter-spacing: inherit;
  text-transform: inherit;
}
.pzv1-pagination button:hover { color: var(--xv1-text); }
.pzv1-pagination button.is-active {
  color: var(--xv1-text);
  border-bottom: 1px solid var(--xv1-brand-red);
}
.pzv1-pagination button:disabled {
  color: var(--xv1-text-dim);
  cursor: default;
}
.pzv1-pagination-pages {
  display: flex;
  gap: 4px;
  align-items: center;
}
.pzv1-pagination-ellipsis {
  color: var(--xv1-text-dim);
  padding: 0 2px;
}

/* ---- Responsive ---- */
@media (max-width: 900px) {
  .pzv1-header {
    grid-template-columns: 1fr;
    gap: 20px;
  }
  .pzv1-metrics {
    flex-wrap: wrap;
    gap: 18px;
  }
  .pzv1-grid { grid-template-columns: 1fr; }
  .pzv1-aside {
    position: static;
    max-height: none;
    border-right: none;
    border-bottom: 1px solid var(--xv1-border-soft);
    padding: 22px 0 30px;
  }
  .pzv1-thead { display: none; }
  .pzv1-row {
    grid-template-columns: 1fr auto;
    grid-template-areas:
      "persona date"
      "topic   confidence"
      "text    text";
    gap: 8px;
  }
  .pzv1-row > :nth-child(1) { grid-area: persona; }
  .pzv1-row > :nth-child(2) { grid-area: topic; }
  .pzv1-row > :nth-child(3) { grid-area: text; }
  .pzv1-row > :nth-child(4) { grid-area: date; text-align: right; }
  .pzv1-row > :nth-child(5) { grid-area: confidence; }
}
```

- [ ] **Step 2: Regenerate + resize browser below 900px**

```bash
.venv/Scripts/python -c "from src.generate import generate_public_site; generate_public_site()"
```

Manual check: shrink browser to ~600px width → rail stacks above main, row lays out in the 3-area grid.

- [ ] **Step 3: Commit**

```bash
git add assets/style.css
git commit -m "feat(style): pzv1 pagination + responsive under 900px"
```

---

## Phase 4 — JavaScript (`assets/pzv1.js`)

Files touched this phase:
- `assets/pzv1.js` (create)

Goal of phase: full client-side interaction. After this phase the page is functional.

### Task 4.1: Core state, render skeleton, escape helper

**Files:**
- Create: `assets/pzv1.js`

- [ ] **Step 1: Create the file with core structure**

```javascript
// Pozīcijas V2 — filter rail + dense table + client-side pagination.
// Runs on /pozicijas.html. Data comes from window._pzData (populated by
// the Jinja template as a positional tuple array).
//
// Tuple order (12 fields):
//   [topic, party, partyShort, partyColor, person, slug,
//    stanceText, dateISO, sourceUrl, sourceDomain, confidence, confidenceTier]

(function () {
  "use strict";

  // --- Tuple index constants ---
  const IDX_TOPIC = 0, IDX_PARTY = 1, IDX_PARTY_SHORT = 2, IDX_PARTY_COLOR = 3,
        IDX_PERSON = 4, IDX_SLUG = 5, IDX_STANCE = 6, IDX_DATE = 7,
        IDX_SOURCE_URL = 8, IDX_SOURCE_DOMAIN = 9,
        IDX_CONF = 10, IDX_CONF_TIER = 11;

  const PAGE_SIZE = 50;

  // --- State ---
  const pzState = {
    topic: "visas",
    party: "Visas",
    persons: new Set(),
    period: "visi",       // visi | nedela | menesis | gads
    confidence: "visas",  // visas | augsta | laba
    query: "",
    sort: "date",         // date | confidence | topic
    page: 1,
  };

  const data = window._pzData || [];
  window._pzData = null; // free reference

  // --- Elements ---
  const rowsEl = document.getElementById("pzv1-rows");
  const paginationEl = document.getElementById("pzv1-pagination");
  const shownEl = document.getElementById("pzv1-shown");
  const searchEl = document.getElementById("pzv1-search");
  const clearEl = document.getElementById("pzv1-clear");
  if (!rowsEl) return;

  // --- Utilities ---
  function esc(s) {
    if (s == null) return "";
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;")
                    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function topicColorFor(topic) {
    // Look up color from the rail button that carries data-color.
    const btn = document.querySelector(`#pzv1-rail-topics .pzv1-rail-row[data-value="${CSS.escape(topic)}"]`);
    return (btn && btn.dataset.color) || "#8b8fa3";
  }

  // --- Rendering (stubs for next task) ---
  function render() {
    const filtered = filterAndSort();
    renderRows(filtered);
    renderPagination(filtered.length);
    renderShownCount(filtered.length);
    renderActiveClear();
    updateFacetedCounts();
  }

  function filterAndSort() {
    // Implemented in Task 4.2
    return data;
  }

  function renderRows(filtered) {
    const page = pzState.page;
    const slice = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
    if (slice.length === 0) {
      rowsEl.innerHTML = '<div class="pzv1-empty">Nav atbilstošu pozīciju.</div>';
      return;
    }
    const frag = document.createDocumentFragment();
    for (const c of slice) {
      frag.appendChild(renderRow(c));
    }
    rowsEl.innerHTML = "";
    rowsEl.appendChild(frag);
  }

  function renderRow(c) {
    const row = document.createElement("div");
    row.className = "pzv1-row";
    row.style.borderLeftColor = "transparent";
    row.addEventListener("mouseenter", () => { row.style.borderLeftColor = c[IDX_PARTY_COLOR]; });
    row.addEventListener("mouseleave", () => { row.style.borderLeftColor = "transparent"; });

    const topicColor = topicColorFor(c[IDX_TOPIC]);
    const dots = [0, 1, 2].map(i => {
      const on = (c[IDX_CONF_TIER] === "augsta" && i < 3)
             || (c[IDX_CONF_TIER] === "laba"   && i < 2)
             || (c[IDX_CONF_TIER] === "merena" && i < 1);
      return `<span class="pzv1-conf-dot${on ? " is-on" : ""}"></span>`;
    }).join("");
    const tierLabel = { augsta: "Augsta", laba: "Laba", merena: "Mērena" }[c[IDX_CONF_TIER]] || "";

    row.innerHTML =
      `<div>
         <div class="pzv1-row-persona-name"><a href="politiki/${esc(c[IDX_SLUG])}.html">${esc(c[IDX_PERSON])}</a></div>
         <div class="pzv1-row-party" style="color:${esc(c[IDX_PARTY_COLOR])}">${esc(c[IDX_PARTY_SHORT])}</div>
       </div>
       <div>
         <button type="button" class="pzv1-row-topic-chip" style="color:${esc(topicColor)}; border-color:${esc(topicColor)}55; background:${esc(topicColor)}11" data-topic="${esc(c[IDX_TOPIC])}">${esc(c[IDX_TOPIC])}</button>
       </div>
       <div><p class="pzv1-row-text">${esc(c[IDX_STANCE])}</p></div>
       <div class="pzv1-row-date">${esc(c[IDX_DATE])}</div>
       <div class="pzv1-row-confidence">
         <span class="pzv1-conf-dots" title="Ticamība ${Number(c[IDX_CONF]).toFixed(2)}">${dots}</span>
         <span class="pzv1-conf-label">${esc(tierLabel)}</span>
         ${c[IDX_SOURCE_URL]
           ? `<a class="pzv1-row-source" href="${esc(c[IDX_SOURCE_URL])}" target="_blank" rel="noopener">${esc(c[IDX_SOURCE_DOMAIN] || "avots")} ↗</a>`
           : ""}
       </div>`;
    return row;
  }

  function renderPagination(total) {
    const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
    if (pages === 1) { paginationEl.innerHTML = ""; return; }
    const p = pzState.page;
    const nums = paginationNumbers(p, pages);
    const numsHtml = nums.map(n => n === "…"
      ? '<span class="pzv1-pagination-ellipsis">…</span>'
      : `<button type="button" class="${n === p ? "is-active" : ""}" data-page="${n}">${n}</button>`
    ).join("");
    paginationEl.innerHTML =
      `<button type="button" data-page="${p - 1}" ${p <= 1 ? "disabled" : ""}>← prev</button>
       <div class="pzv1-pagination-pages">${numsHtml}</div>
       <button type="button" data-page="${p + 1}" ${p >= pages ? "disabled" : ""}>next →</button>`;
  }

  function paginationNumbers(current, total) {
    // Always show: 1, last, current±1. Ellipsis elsewhere.
    const set = new Set([1, total, current, current - 1, current + 1]);
    const nums = [...set].filter(n => n >= 1 && n <= total).sort((a, b) => a - b);
    const out = [];
    for (let i = 0; i < nums.length; i++) {
      if (i > 0 && nums[i] - nums[i - 1] > 1) out.push("…");
      out.push(nums[i]);
    }
    return out;
  }

  function renderShownCount(total) {
    if (shownEl) shownEl.textContent = total;
  }

  function renderActiveClear() {
    const active = pzState.topic !== "visas"
                || pzState.party !== "Visas"
                || pzState.persons.size > 0
                || pzState.period !== "visi"
                || pzState.confidence !== "visas"
                || pzState.query !== "";
    if (clearEl) clearEl.hidden = !active;
  }

  function updateFacetedCounts() {
    // Implemented in Task 4.3
  }

  // --- Clear button ---
  if (clearEl) {
    clearEl.addEventListener("click", () => {
      pzState.topic = "visas";
      pzState.party = "Visas";
      pzState.persons.clear();
      pzState.period = "visi";
      pzState.confidence = "visas";
      pzState.query = "";
      pzState.page = 1;
      if (searchEl) searchEl.value = "";
      document.querySelectorAll(".pzv1-rail-row").forEach(b => {
        const axis = b.dataset.axis;
        const isDefault = (axis === "topic" && b.dataset.value === "visas")
                       || (axis === "party" && b.dataset.value === "Visas")
                       || (axis === "period" && b.dataset.value === "visi")
                       || (axis === "confidence" && b.dataset.value === "visas");
        b.classList.toggle("is-active", !!isDefault);
        b.style.borderLeftColor = "";
      });
      document.querySelectorAll(".pzv1-rail-person.is-active").forEach(b => b.classList.remove("is-active"));
      render();
    });
  }

  // --- Bootstrap ---
  // All event-listener blocks from later tasks (4.2–4.5) must be inserted
  // ABOVE this Bootstrap section, inside the same IIFE.
  render();
})();
```

All subsequent tasks in Phase 4 **insert their code ABOVE the `// --- Bootstrap ---` line**, inside the same IIFE. Do NOT create new IIFEs.

- [ ] **Step 2: Regenerate + check rows render**

```bash
.venv/Scripts/python -c "from src.generate import generate_public_site; generate_public_site()"
```

Manual check: `/pozicijas.html` should now show 50 rows. Clicking persona name → opens politician page. Clicking topic chip does nothing yet (wired in 4.3). Pagination should show numbers.

- [ ] **Step 3: Commit**

```bash
git add assets/pzv1.js
git commit -m "feat(js): pzv1 core state + row rendering + pagination numbering"
```

---

### Task 4.2: Filter pipeline

**Files:**
- Modify: `assets/pzv1.js`

- [ ] **Step 1: Replace the `filterAndSort` stub**

Locate the stub function `filterAndSort()` in `assets/pzv1.js` (currently returns `data`). Replace its body with the full pipeline. Also add a helper `periodCutoff()`:

```javascript
  // --- Filtering ---
  function periodCutoff(period) {
    if (period === "visi") return null;
    const now = new Date();
    if (period === "nedela") {
      const d = new Date(now); d.setDate(d.getDate() - 7);
      return d.toISOString().slice(0, 10);
    }
    if (period === "menesis") {
      return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-01`;
    }
    if (period === "gads") {
      return `${now.getFullYear()}-01-01`;
    }
    return null;
  }

  function matchesExcept(c, skipAxis) {
    if (skipAxis !== "topic") {
      if (pzState.topic !== "visas" && c[IDX_TOPIC] !== pzState.topic) return false;
    }
    if (skipAxis !== "party") {
      if (pzState.party !== "Visas") {
        if (pzState.party === "Bez partijas") {
          if (c[IDX_PARTY]) return false;
        } else {
          if (c[IDX_PARTY] !== pzState.party) return false;
        }
      }
    }
    if (skipAxis !== "person") {
      if (pzState.persons.size > 0 && !pzState.persons.has(c[IDX_PERSON])) return false;
    }
    if (skipAxis !== "period") {
      const cutoff = periodCutoff(pzState.period);
      if (cutoff && c[IDX_DATE] < cutoff) return false;
    }
    if (skipAxis !== "confidence") {
      if (pzState.confidence === "augsta" && c[IDX_CONF_TIER] !== "augsta") return false;
      if (pzState.confidence === "laba"
          && c[IDX_CONF_TIER] !== "augsta" && c[IDX_CONF_TIER] !== "laba") return false;
    }
    if (skipAxis !== "query") {
      if (pzState.query) {
        const q = pzState.query.toLowerCase();
        const hay = (c[IDX_PERSON] + " " + c[IDX_TOPIC] + " " + c[IDX_STANCE]).toLowerCase();
        if (!hay.includes(q)) return false;
      }
    }
    return true;
  }

  function filterAndSort() {
    const filtered = data.filter(c => matchesExcept(c, null));
    const s = pzState.sort;
    if (s === "date") {
      filtered.sort((a, b) => (b[IDX_DATE] || "").localeCompare(a[IDX_DATE] || ""));
    } else if (s === "confidence") {
      filtered.sort((a, b) => (b[IDX_CONF] || 0) - (a[IDX_CONF] || 0));
    } else if (s === "topic") {
      filtered.sort((a, b) => (a[IDX_TOPIC] || "").localeCompare(b[IDX_TOPIC] || ""));
    }
    return filtered;
  }
```

Insert these functions **above** the existing `filterAndSort` stub, and delete the stub.

- [ ] **Step 2: Wire the search input**

Add before the `// --- Bootstrap ---` line:

```javascript
  // --- Search input ---
  if (searchEl) {
    searchEl.addEventListener("input", () => {
      pzState.query = searchEl.value.trim();
      pzState.page = 1;
      render();
    });
  }
```

- [ ] **Step 3: Wire the sort buttons**

Also add before `// --- Bootstrap ---`:

```javascript
  // --- Sort buttons ---
  document.querySelectorAll(".pzv1-sortbtn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".pzv1-sortbtn").forEach(b => b.classList.remove("is-active"));
      btn.classList.add("is-active");
      pzState.sort = btn.dataset.sort;
      pzState.page = 1;
      render();
    });
  });
```

- [ ] **Step 4: Verify search + sort work**

Regenerate → type in search box → rows filter live; click sort buttons → rows reorder.

```bash
.venv/Scripts/python -c "from src.generate import generate_public_site; generate_public_site()"
```

- [ ] **Step 5: Commit**

```bash
git add assets/pzv1.js
git commit -m "feat(js): pzv1 filter pipeline + sort + search wiring"
```

---

### Task 4.3: Rail interactions + faceted counts

**Files:**
- Modify: `assets/pzv1.js`

- [ ] **Step 1: Replace the `updateFacetedCounts` stub**

Replace the current empty stub with the real implementation:

```javascript
  function updateFacetedCounts() {
    // For each axis, each rail row shows how many rows match if we TOGGLE that value on this axis
    // while keeping every other axis at its current state.
    document.querySelectorAll(".pzv1-rail-row[data-axis]").forEach(btn => {
      const axis = btn.dataset.axis;
      const value = btn.dataset.value;
      let count;
      if (axis === "topic") {
        count = data.filter(c => matchesExcept(c, "topic") && (value === "visas" || c[IDX_TOPIC] === value)).length;
      } else if (axis === "party") {
        count = data.filter(c => {
          if (!matchesExcept(c, "party")) return false;
          if (value === "Visas") return true;
          if (value === "Bez partijas") return !c[IDX_PARTY];
          return c[IDX_PARTY] === value;
        }).length;
      } else if (axis === "person") {
        count = data.filter(c => matchesExcept(c, "person") && c[IDX_PERSON] === value).length;
      } else if (axis === "period") {
        const save = pzState.period;
        pzState.period = value;
        count = data.filter(c => matchesExcept(c, null)).length;
        pzState.period = save;
      } else if (axis === "confidence") {
        const save = pzState.confidence;
        pzState.confidence = value;
        count = data.filter(c => matchesExcept(c, null)).length;
        pzState.confidence = save;
      } else {
        return;
      }
      const countEl = btn.querySelector(".pzv1-rail-count");
      if (countEl) countEl.textContent = count;
    });
  }
```

- [ ] **Step 2: Add rail click listeners (topic, party, period, confidence — single-select)**

Add before `// --- Bootstrap ---`:

```javascript
  // --- Rail: single-select axes ---
  function railSingleSelect(axis, resetValue) {
    document.querySelectorAll(`.pzv1-rail-row[data-axis="${axis}"]`).forEach(btn => {
      btn.addEventListener("click", () => {
        const currentActive = document.querySelector(`.pzv1-rail-row[data-axis="${axis}"].is-active`);
        const wasActive = btn === currentActive;
        document.querySelectorAll(`.pzv1-rail-row[data-axis="${axis}"]`).forEach(b => {
          b.classList.remove("is-active");
          b.style.borderLeftColor = "";
        });
        let newValue;
        if (wasActive && btn.dataset.value !== resetValue) {
          // toggle off → go to default
          const def = document.querySelector(`.pzv1-rail-row[data-axis="${axis}"][data-value="${CSS.escape(resetValue)}"]`);
          if (def) def.classList.add("is-active");
          newValue = resetValue;
        } else {
          btn.classList.add("is-active");
          if (btn.dataset.color) btn.style.borderLeftColor = btn.dataset.color;
          newValue = btn.dataset.value;
        }
        pzState[axis] = newValue;
        pzState.page = 1;
        render();
      });
    });
  }
  railSingleSelect("topic", "visas");
  railSingleSelect("party", "Visas");
  railSingleSelect("period", "visi");
  railSingleSelect("confidence", "visas");
```

- [ ] **Step 3: Add persona multi-select + search**

Add before `// --- Bootstrap ---`:

```javascript
  // --- Rail: persons (multi-select) ---
  document.querySelectorAll('.pzv1-rail-row[data-axis="person"]').forEach(btn => {
    btn.addEventListener("click", () => {
      const name = btn.dataset.value;
      if (pzState.persons.has(name)) {
        pzState.persons.delete(name);
        btn.classList.remove("is-active");
      } else {
        pzState.persons.add(name);
        btn.classList.add("is-active");
      }
      pzState.page = 1;
      render();
    });
  });

  const personSearchEl = document.querySelector("#pzv1-rail-persons .pzv1-rail-search-input");
  if (personSearchEl) {
    personSearchEl.addEventListener("input", () => {
      const q = personSearchEl.value.trim().toLowerCase();
      document.querySelectorAll(".pzv1-rail-person").forEach(btn => {
        const label = btn.querySelector(".pzv1-rail-label").textContent.toLowerCase();
        btn.classList.toggle("is-hidden", q && !label.includes(q));
      });
    });
  }

  // --- Rail: topic "+ rādīt visas 26" expander ---
  const topicMoreBtn = document.getElementById("pzv1-topic-more");
  if (topicMoreBtn) {
    topicMoreBtn.addEventListener("click", () => {
      const hidden = topicMoreBtn.nextElementSibling;
      if (!hidden || !hidden.classList.contains("pzv1-rail-hidden")) return;
      hidden.removeAttribute("hidden");
      topicMoreBtn.remove();
      // Re-run the topic single-select wiring for newly-visible rows
      hidden.querySelectorAll('.pzv1-rail-row[data-axis="topic"]').forEach(btn => {
        btn.addEventListener("click", () => {
          document.querySelectorAll(`.pzv1-rail-row[data-axis="topic"]`).forEach(b => {
            b.classList.remove("is-active");
            b.style.borderLeftColor = "";
          });
          btn.classList.add("is-active");
          if (btn.dataset.color) btn.style.borderLeftColor = btn.dataset.color;
          pzState.topic = btn.dataset.value;
          pzState.page = 1;
          render();
        });
      });
      updateFacetedCounts();
    });
  }

- [ ] **Step 4: Verify**

Regenerate + test every rail interaction:
- Click any topic → rows filter, counts update across ALL axes
- Click same topic again → resets to "Visas tēmas"
- Click multiple persons → multi-select accumulates
- Type in persona search → rows hide/show
- Click "+ rādīt visas 26 →" → hidden 16 topics appear

```bash
.venv/Scripts/python -c "from src.generate import generate_public_site; generate_public_site()"
```

- [ ] **Step 5: Commit**

```bash
git add assets/pzv1.js
git commit -m "feat(js): pzv1 rail interactions + faceted counts + topic expander"
```

---

### Task 4.4: Pagination click + row topic chip click

**Files:**
- Modify: `assets/pzv1.js`

- [ ] **Step 1: Wire pagination**

Add before `// --- Bootstrap ---`:

```javascript
  // --- Pagination click ---
  paginationEl.addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-page]");
    if (!btn || btn.disabled) return;
    const n = parseInt(btn.dataset.page, 10);
    if (Number.isFinite(n) && n >= 1) {
      pzState.page = n;
      render();
      // Scroll to top of table so the new page is in view
      const main = document.querySelector(".pzv1-main");
      if (main) main.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  });
```

- [ ] **Step 2: Wire row topic chip click (delegate)**

Add before `// --- Bootstrap ---`:

```javascript
  // --- Row topic chip → set topic filter ---
  rowsEl.addEventListener("click", (e) => {
    const chip = e.target.closest(".pzv1-row-topic-chip");
    if (!chip) return;
    e.stopPropagation();
    const topic = chip.dataset.topic;
    const railBtn = document.querySelector(`.pzv1-rail-row[data-axis="topic"][data-value="${CSS.escape(topic)}"]`);
    if (railBtn) railBtn.click();
  });
```

- [ ] **Step 3: Verify**

Regenerate → click pagination numbers → rows paginate; click topic chip inside a row → rail reflects selection.

- [ ] **Step 4: Commit**

```bash
git add assets/pzv1.js
git commit -m "feat(js): pzv1 pagination click + row topic chip shortcut"
```

---

### Task 4.5: URL params + keyboard shortcuts

**Files:**
- Modify: `assets/pzv1.js`

- [ ] **Step 1: Add URL param starts BEFORE the initial render call**

Locate the `// --- Bootstrap ---` section. Immediately before the `render();` call, insert:

```javascript
  // --- URL param starts ---
  (function applyUrlParams() {
    const params = new URLSearchParams(window.location.search);
    const persona = params.get("persona");
    if (persona) {
      const name = decodeURIComponent(persona);
      pzState.persons.add(name);
      const btn = document.querySelector(`.pzv1-rail-person[data-value="${CSS.escape(name)}"]`);
      if (btn) btn.classList.add("is-active");
      const details = document.getElementById("pzv1-rail-persons");
      if (details) details.open = true;
    }
    const tema = params.get("tema");
    if (tema) {
      const name = decodeURIComponent(tema);
      pzState.topic = name;
      document.querySelectorAll('.pzv1-rail-row[data-axis="topic"]').forEach(b => {
        b.classList.toggle("is-active", b.dataset.value === name);
        if (b.dataset.value === name && b.dataset.color) b.style.borderLeftColor = b.dataset.color;
      });
      // If the topic is in the hidden tail, expand the extras
      const hiddenMatch = document.querySelector(`#pzv1-rail-topics .pzv1-rail-hidden .pzv1-rail-row[data-value="${CSS.escape(name)}"]`);
      if (hiddenMatch) {
        const more = document.getElementById("pzv1-topic-more");
        if (more) more.click();
      }
    }
    const partija = params.get("partija");
    if (partija) {
      const name = decodeURIComponent(partija);
      pzState.party = name;
      document.querySelectorAll('.pzv1-rail-row[data-axis="party"]').forEach(b => {
        b.classList.toggle("is-active", b.dataset.value === name);
        if (b.dataset.value === name && b.dataset.color) b.style.borderLeftColor = b.dataset.color;
      });
    }
  })();
```

- [ ] **Step 2: Add keyboard shortcuts**

Add before `// --- Bootstrap ---`:

```javascript
  // --- Keyboard ---
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      document.querySelectorAll(".pzv1-rail-details[open]").forEach(d => { d.open = false; });
    } else if (e.key === "/" && document.activeElement !== searchEl
               && !(document.activeElement && document.activeElement.tagName === "INPUT")) {
      e.preventDefault();
      if (searchEl) searchEl.focus();
    }
  });
```

- [ ] **Step 3: Verify**

Regenerate. Test:
- `http://localhost:8080/pozicijas.html?persona=Baiba%20Bra%C5%BEe` → persona rail row pre-ticked, only Braže rows shown
- `http://localhost:8080/pozicijas.html?tema=Aizsardz%C4%ABba%20un%20dro%C5%A1%C4%ABba` → topic preselected
- `?partija=Jaun%C4%81%20Vienot%C4%ABba` → party preselected
- Press `/` → focus moves to search box
- Open Persona `<details>`, press Escape → closes

- [ ] **Step 4: Commit**

```bash
git add assets/pzv1.js
git commit -m "feat(js): pzv1 URL param deep links + keyboard shortcuts"
```

---

## Phase 5 — Integration + regression

Files touched: none. This phase is verification only.

### Task 5.1: Full site regeneration + sanity checks

- [ ] **Step 1: Clean regen**

```bash
.venv/Scripts/python -c "from src.generate import generate_public_site; generate_public_site()"
```

Expected: no new errors. Generation log mentions `pozicijas.html` without warnings.

- [ ] **Step 2: Run all tests**

```bash
.venv/Scripts/python -m pytest tests/test_pozicijas_v2.py tests/test_generate.py -v
```

Expected: all tests pass.

- [ ] **Step 3: Type-check (if mypy configured)**

Check if mypy is configured — `ls pyproject.toml mypy.ini 2>/dev/null`. If yes:

```bash
.venv/Scripts/python -m mypy src/generate.py
```

If mypy is not configured for this project, skip this step and note: "project has no type-checker configured."

- [ ] **Step 4: Lighthouse sanity (optional)**

If chrome-based lighthouse is available, audit `/pozicijas.html` for Performance/Accessibility. Not a blocker — acceptable if previous audit numbers hold.

---

### Task 5.2: Manual regression checklist

Open `python serve.py` → `http://127.0.0.1:8080/pozicijas.html`. Walk through:

- [ ] **Step 1: Header metrics are non-zero and plausible**
  - `Kopā` ≥ 1000
  - `Pēdējā nedēļā` matches recent activity
  - `Ticamība ≥ laba` around 75–85%

- [ ] **Step 2: Filter rail — each axis works**
  - Click any topic → rows filter, counts on other axes re-compute
  - Click same topic again → returns to "Visas tēmas"
  - Multi-select persons accumulate
  - Persona search hides non-matching rows
  - Period "Šogad" cuts to 2026 rows only
  - Confidence "Augsta" only shows ≥0.9 rows

- [ ] **Step 3: Main area**
  - Search `airbaltic` → filters visibly
  - Sort by "ticamība" → 0.95+ at top
  - Sort by "tēma" → alphabetical
  - Clicking persona name in row → opens `/politiki/<slug>.html`
  - Clicking topic chip in row → sets rail topic

- [ ] **Step 4: Pagination**
  - Bottom shows `← prev · 1 · 2 · 3 · … · N · next →`
  - Click page 2 → rows 51–100
  - Click next → page advances
  - Filter down to <50 rows → pagination hides

- [ ] **Step 5: Deep links**
  - `?persona=Evika Siliņa` — persona chip in rail is active
  - `?tema=Aizsardzība un drošība` — topic chip active
  - `?partija=Jaunā Vienotība` — party chip active

- [ ] **Step 6: Clear button**
  - Apply 3 filters
  - Click `Notīrīt ✕` → all filters reset, back to "Visas"

- [ ] **Step 7: Responsive**
  - Shrink browser to 700px → rail stacks above main
  - Row layout switches to 3-area grid
  - Metrics wrap

---

### Task 5.3: X tab regression check

- [ ] **Step 1: X tab still identical**
  - Open `http://127.0.0.1:8080/x.html`
  - Verify header, two-column layout, ticker, leaderboard all render as before
  - Click any persona in `Pieminētākie` → filter applies
  - Click any topic in `Tēmas` → filter applies

Zero visual regressions should be present. CSS var scope extension is a no-op for rendered xv1 styles.

---

### Task 5.4: Final commit of plan doc to branch

- [ ] **Step 1: Commit this plan doc itself**

```bash
git add docs/superpowers/plans/2026-04-18-pozicijas-v2.md
git commit -m "docs(pozicijas-v2): implementation plan"
```

- [ ] **Step 2: Summarize for handoff**

Branch `feat/pozicijas-v2` is ready for review. Merge target: `master`. Spec lives on `design/pozicijas-v2` and is already documented in the commit history.

---

## Summary of acceptance criteria (from spec §10)

- [x] All 1132 position claim rows accessible after filtering — covered by rowsEl rendering all `data` after filter pass
- [x] No `confidence_tier` NULL in rendering — Task 1.1 `_confidence_tier(None) → "merena"`
- [x] Faceted filter counts correct on all 5 axes — Task 4.3 `updateFacetedCounts`
- [x] `?persona=` and `?tema=` deep-links work — Task 4.5 `applyUrlParams`
- [x] Dynamic header metrics — Task 1.3 `_fetch_pozicijas_metrics`
- [x] 26 topic chip colors — Task 1.2 `PZV1_TOPIC_COLORS`
- [x] X tab unaffected — Task 3.1 selector extension (no style change)
- [x] Unit tests pass — Tasks 1.1–1.4 all use TDD
- [ ] Lighthouse score not worse — Task 5.1 Step 4 (optional)
