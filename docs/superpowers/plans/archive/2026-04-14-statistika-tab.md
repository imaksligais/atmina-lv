# Statistika Tab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Statistika" tab to atmina.lv showing 10 CSP (Central Statistical Bureau) economic/social indicators with interactive Chart.js graphs and historical event annotations.

**Architecture:** Copy CSP data pipeline (`src/csp/`) from the `csp-proto` prototype into atmina. CSP data lives in a separate `data/csp.db` (synced independently). Two new Jinja2 templates extend atmina's `base.html.j2`. A standalone `generate_statistika()` function renders the pages without coupling to the main `generate_public_site()` cycle.

**Tech Stack:** Python 3.11+, SQLite, httpx (CSP PxWeb API), Jinja2, Chart.js 4 + chartjs-plugin-annotation, PyYAML.

---

### Task 1: Copy CSP modules into `src/csp/`

**Files:**
- Create: `src/csp/__init__.py`
- Create: `src/csp/client.py`
- Create: `src/csp/tables.py`
- Create: `src/csp/insights.py`
- Create: `src/csp/db.py`
- Create: `src/csp/sync.py`

- [ ] **Step 1: Create `src/csp/__init__.py`**

```python
"""CSP (Centrālā statistikas pārvalde) data pipeline."""
```

- [ ] **Step 2: Copy `client.py` verbatim from csp-proto**

```bash
cp "~/csp-proto/src/csp_client.py" "~/atmina/src/csp/client.py"
```

No changes needed — it has no internal imports.

- [ ] **Step 3: Copy `tables.py` from csp-proto, rename module reference**

```bash
cp "~/csp-proto/src/csp_tables.py" "~/atmina/src/csp/tables.py"
```

No changes needed — it's pure config with no imports.

- [ ] **Step 4: Copy `insights.py` verbatim**

```bash
cp "~/csp-proto/src/insights.py" "~/atmina/src/csp/insights.py"
```

No changes needed — pure functions, no imports from sibling modules.

- [ ] **Step 5: Copy `db.py` verbatim**

```bash
cp "~/csp-proto/src/db.py" "~/atmina/src/csp/db.py"
```

No changes needed.

- [ ] **Step 6: Copy `sync.py` and fix imports**

```bash
cp "~/csp-proto/src/sync.py" "~/atmina/src/csp/sync.py"
```

Then edit the imports at the top of `src/csp/sync.py` — change:

```python
from src.csp_client import fetch_table, parse_jsonstat2
from src.csp_tables import TABLES, FREQ_PERIODS_PER_YEAR
```

to:

```python
from src.csp.client import fetch_table, parse_jsonstat2
from src.csp.tables import TABLES, FREQ_PERIODS_PER_YEAR
```

- [ ] **Step 7: Copy data files**

```bash
cp "~/csp-proto/data/csp.db" "~/atmina/data/csp.db"
cp "~/csp-proto/data/events.yaml" "~/atmina/data/events.yaml"
```

- [ ] **Step 8: Verify imports work**

```bash
cd "~/atmina" && python -c "from src.csp.tables import TABLES, DASHBOARD_ORDER; print(f'{len(TABLES)} tables, order: {len(DASHBOARD_ORDER)}')"
```

Expected: `10 tables, order: 10`

```bash
python -c "from src.csp.db import init_db; conn = init_db('data/csp.db'); print(conn.execute('SELECT COUNT(*) FROM csp_data').fetchone()[0], 'rows')"
```

Expected: some number of rows (e.g. `2847 rows`).

```bash
python -c "from src.csp.insights import generate_insight; print(generate_insight([('2025M01', 5.1), ('2025M02', 5.0), ('2025M03', 4.9), ('2025M04', 4.8)], 'lower_is_better'))"
```

Expected: A Latvian insight string like `sarūk 3 mēn. pēc kārtas`.

- [ ] **Step 9: Commit**

```bash
git add src/csp/ data/csp.db data/events.yaml
git commit -m "feat: add CSP data pipeline modules (src/csp/) with data"
```

---

### Task 2: Download chartjs-plugin-annotation asset

**Files:**
- Modify: `src/generate.py` (add annotation plugin download next to chart.min.js download)

- [ ] **Step 1: Add annotation plugin download function**

In `src/generate.py`, find the `_download_chart_js` function (around line 2108). After it, add:

```python
def _download_annotation_plugin(dest: Path) -> None:
    """Download chartjs-plugin-annotation from CDN."""
    try:
        import httpx
        resp = httpx.get(
            "https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3/dist/chartjs-plugin-annotation.min.js",
            follow_redirects=True,
            timeout=30,
        )
        resp.raise_for_status()
        dest.write_bytes(resp.content)
        logger.info("Downloaded chartjs-plugin-annotation.min.js")
    except Exception as e:
        logger.warning("Could not download chartjs-plugin-annotation.min.js: %s", e)
        dest.write_text("/* chartjs-plugin-annotation unavailable */", encoding="utf-8")
```

- [ ] **Step 2: Call it in `generate_public_site`**

In `generate_public_site`, find the block (around line 1567):

```python
    chart_js = atmina_dir / "assets" / "chart.min.js"
    if not chart_js.exists():
        _download_chart_js(chart_js)
```

Add after it:

```python
    annotation_js = atmina_dir / "assets" / "chartjs-plugin-annotation.min.js"
    if not annotation_js.exists():
        _download_annotation_plugin(annotation_js)
```

- [ ] **Step 3: Verify**

```bash
python -c "from src.generate import generate_public_site; print('imports ok')"
```

Expected: `imports ok`

- [ ] **Step 4: Commit**

```bash
git add src/generate.py
git commit -m "feat: add chartjs-plugin-annotation asset download"
```

---

### Task 3: Create statistika dashboard template

**Files:**
- Create: `templates/statistika.html.j2`

- [ ] **Step 1: Create the dashboard template**

Create `templates/statistika.html.j2`:

```jinja2
{% extends "base.html.j2" %}
{% set assets_prefix = "" %}
{% set active_page = "statistika" %}

{% block title %}Statistika{% endblock %}

{% block styles %}
<style>
/* ── CSP Statistika styles ─────────────────────────── */
.stat-hero { padding: 3rem 0 1.5rem; max-width: 720px; }
.stat-hero-eyebrow {
    display: inline-flex; align-items: center; gap: 0.5rem;
    font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.12em;
    color: var(--accent-highlight, #B71C1C); font-weight: 700; margin-bottom: 0.75rem;
}
.stat-hero-eyebrow::before { content: ''; width: 24px; height: 1px; background: var(--accent-highlight, #B71C1C); }
.stat-hero h1 {
    font-size: 2.5rem; margin-bottom: 0.75rem;
    background: linear-gradient(180deg, #fff 0%, #a0a5b8 100%);
    -webkit-background-clip: text; background-clip: text; color: transparent;
}
.stat-hero-subtitle { color: var(--text-muted); font-size: 1rem; line-height: 1.55; }
.stat-hero-meta {
    display: flex; gap: 2rem; margin-top: 1.5rem;
    font-size: 0.8rem; color: var(--text-muted);
    text-transform: uppercase; letter-spacing: 0.05em; flex-wrap: wrap;
}
.stat-hero-meta strong {
    color: var(--text, #e2e4e9); font-weight: 700; font-size: 0.95rem;
    display: block; margin-top: 0.15rem; letter-spacing: 0; text-transform: none;
}
.stat-card-grid {
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem;
}
@media (max-width: 1024px) { .stat-card-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 600px) { .stat-card-grid { grid-template-columns: 1fr; } }

.stat-card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 1.1rem 1.25rem 1rem;
    transition: border-color 0.2s ease, transform 0.2s ease;
    position: relative; overflow: hidden; height: 100%;
    display: flex; flex-direction: column;
}
.stat-card::before {
    content: ''; position: absolute; left: 0; top: 0;
    width: 3px; height: 100%;
    background: var(--domain-color, var(--accent, #90A4AE)); opacity: 0.7;
}
.stat-card:hover { border-color: var(--accent-highlight, #B71C1C); transform: translateY(-1px); }
.stat-card.domain-economy { --domain-color: #90A4AE; }
.stat-card.domain-social  { --domain-color: #B388C7; }
.stat-card.domain-prices  { --domain-color: #f97316; }
.stat-card.domain-state   { --domain-color: #22c55e; }

.stat-label {
    font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase;
    letter-spacing: 0.08em; font-weight: 600; margin-bottom: 0.5rem; min-height: 2.2em;
}
.stat-value {
    font-size: 1.7rem; font-weight: 700; line-height: 1.1; letter-spacing: -0.025em;
    display: flex; align-items: baseline; gap: 0.5rem; flex-wrap: wrap; color: var(--text, #e2e4e9);
}
.stat-change {
    font-size: 0.75rem; font-weight: 600; padding: 0.15rem 0.45rem;
    border-radius: 4px; letter-spacing: 0.01em;
}
.stat-change.positive { color: #22c55e; background: rgba(34,197,94,0.12); }
.stat-change.negative { color: #f87171; background: rgba(198,40,40,0.15); }
.sparkline-wrap { height: 56px; margin: 0.75rem 0 0.5rem; }
.stat-insight {
    font-size: 0.72rem; color: var(--text-muted); font-style: italic;
    line-height: 1.4; min-height: 2em;
}
.stat-footer {
    font-size: 0.62rem; color: var(--text-muted); margin-top: 0.75rem;
    padding-top: 0.6rem; border-top: 1px solid var(--border);
    display: flex; justify-content: space-between;
    text-transform: uppercase; letter-spacing: 0.06em; font-weight: 500;
}
.stat-footer .arrow { transition: transform 0.2s ease, color 0.2s ease; }
.stat-card:hover .stat-footer .arrow { color: var(--accent-highlight, #B71C1C); transform: translateX(2px); }
.stat-card-link { text-decoration: none; color: inherit; display: block; height: 100%; }
.stat-fade-up { opacity: 0; animation: statFadeUp 0.5s ease forwards; }
@keyframes statFadeUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

.stat-source-note {
    margin-top: 2rem; padding-top: 1rem; border-top: 1px solid var(--border);
    font-size: 0.8rem; color: var(--text-muted);
}
.stat-source-note a { color: var(--text-muted); text-decoration: underline; }
</style>
{% endblock %}

{% block content %}
<section class="stat-hero">
    <span class="stat-hero-eyebrow">Statistika</span>
    <h1>Latvijas ekonomiskā realitāte</h1>
    <p class="stat-hero-subtitle">
        Ekonomiskie un sociālie rādītāji no Centrālās statistikas pārvaldes, sasaistīti ar vēsturiskajiem notikumiem.
    </p>
    <div class="stat-hero-meta">
        <div>Rādītāji <strong>{{ cards|length }}</strong></div>
        <div>Vēsture <strong>līdz 30 gadiem</strong></div>
        <div>Atjaunots <strong>{{ last_updated or '—' }}</strong></div>
    </div>
</section>

<section style="padding: 1.5rem 0 3rem;">
    <div class="section-header" style="margin-bottom: 1.25rem; padding-bottom: 0.75rem; border-bottom: 1px solid var(--border);">
        <span style="font-size: 0.8rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-muted);">Visi rādītāji</span>
        <span class="count" style="font-size: 0.8rem; font-weight: 400; letter-spacing: 0.02em;">Ekonomika · Sociālie · Cenas · Valsts</span>
    </div>
    <div class="stat-card-grid">
    {% for card in cards %}
        <a href="statistika/{{ card.table_id }}.html" class="stat-card-link stat-fade-up" style="animation-delay: {{ loop.index0 * 0.05 }}s">
            <article class="stat-card domain-{{ card.domain }}">
                <div class="stat-label">{{ card.label }}</div>
                <div class="stat-value">
                    <span>{{ card.formatted_value }}</span>
                    {% if card.change is not none %}
                    <span class="stat-change {{ 'positive' if card.change_positive else 'negative' }}">
                        {{ card.formatted_change }}
                    </span>
                    {% endif %}
                </div>
                <div class="sparkline-wrap">
                    <canvas id="spark-{{ card.table_id }}"></canvas>
                </div>
                {% if card.insight %}
                <div class="stat-insight">{{ card.insight }}</div>
                {% endif %}
                <div class="stat-footer">
                    <span>Atj. {{ card.csp_updated_short }}</span>
                    <span class="arrow">Detaļas →</span>
                </div>
            </article>
        </a>
    {% endfor %}
    </div>
</section>

<div class="stat-source-note">
    Dati: <a href="https://data.stat.gov.lv/" target="_blank" rel="noopener">Centrālā statistikas pārvalde</a>
</div>
{% endblock %}

{% block scripts %}
<script src="assets/chart.min.js"></script>
<script>
const CARDS_DATA = {{ cards_json | safe }};
const DOMAIN_COLORS = {
    economy: '#90A4AE', social: '#B388C7',
    prices: '#f97316', state: '#22c55e',
};
document.addEventListener('DOMContentLoaded', () => {
    CARDS_DATA.forEach(card => {
        const canvas = document.getElementById('spark-' + card.table_id);
        if (!canvas || !card.sparkline_values.length) return;
        const ctx = canvas.getContext('2d');
        const color = DOMAIN_COLORS[card.domain] || DOMAIN_COLORS.economy;
        const gradient = ctx.createLinearGradient(0, 0, 0, 56);
        gradient.addColorStop(0, color + '33');
        gradient.addColorStop(1, 'transparent');
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: card.sparkline_labels,
                datasets: [{
                    data: card.sparkline_values,
                    borderColor: color, backgroundColor: gradient,
                    borderWidth: 1.75, fill: true, tension: 0.35,
                    pointRadius: 0, pointHoverRadius: 3, pointBackgroundColor: color,
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: {display: false},
                    tooltip: {
                        enabled: true,
                        backgroundColor: 'rgba(22,26,34,0.95)',
                        titleColor: '#e2e4e9', bodyColor: '#e2e4e9',
                        borderColor: 'rgba(255,255,255,0.1)', borderWidth: 1,
                        cornerRadius: 6, displayColors: false, padding: 8,
                    },
                },
                scales: { x: {display: false}, y: {display: false} },
                interaction: {intersect: false, mode: 'index'},
                animation: {duration: 600, delay: card.index * 60},
            }
        });
    });
});
</script>
{% endblock %}
```

- [ ] **Step 2: Commit**

```bash
git add templates/statistika.html.j2
git commit -m "feat: add statistika dashboard template"
```

---

### Task 4: Create statistika detail template

**Files:**
- Create: `templates/statistika-detail.html.j2`

- [ ] **Step 1: Create the detail template**

Create `templates/statistika-detail.html.j2`:

```jinja2
{% extends "base.html.j2" %}
{% set assets_prefix = "../" %}
{% set active_page = "statistika" %}

{% block title %}{{ meta.label_lv }}{% endblock %}

{% block styles %}
<style>
/* ── Detail page styles ─────────────────────────── */
.stat-breadcrumb { margin-top: 1.5rem; font-size: 0.85rem; }
.stat-breadcrumb a { color: var(--text-muted); }
.stat-breadcrumb a:hover { color: var(--text, #e2e4e9); }

.stat-detail-header { padding: 1.5rem 0 2rem; }
.stat-detail-title {
    display: flex; align-items: flex-start; justify-content: space-between;
    gap: 2rem; flex-wrap: wrap;
}
.stat-detail-title h1 { font-size: 2.25rem; }
.stat-detail-meta {
    display: flex; gap: 0.5rem; flex-wrap: wrap; margin-top: 0.75rem;
    font-size: 0.75rem; color: var(--text-muted);
    text-transform: uppercase; letter-spacing: 0.06em; align-items: center;
}
.stat-detail-meta .sep { opacity: 0.4; }
.stat-detail-meta strong { color: var(--text, #e2e4e9); font-weight: 600; }

.stat-hero-value {
    display: flex; align-items: baseline; gap: 0.75rem; margin-top: 1rem; flex-wrap: wrap;
}
.stat-hero-value .num {
    font-size: 3.25rem; font-weight: 800; letter-spacing: -0.03em;
    line-height: 1; color: var(--text, #e2e4e9);
}
.stat-hero-change {
    font-size: 0.95rem; font-weight: 600; padding: 0.2rem 0.55rem; border-radius: 6px;
}
.stat-hero-change.positive { color: #22c55e; background: rgba(34,197,94,0.12); }
.stat-hero-change.negative { color: #f87171; background: rgba(198,40,40,0.15); }

.domain-chip {
    display: inline-block; padding: 0.2rem 0.55rem; border-radius: 4px;
    font-size: 0.65rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em;
}
.domain-chip.domain-economy { color: #90A4AE; background: rgba(144,164,174,0.12); }
.domain-chip.domain-social  { color: #B388C7; background: rgba(179,136,199,0.12); }
.domain-chip.domain-prices  { color: #f97316; background: rgba(249,115,22,0.12); }
.domain-chip.domain-state   { color: #22c55e; background: rgba(34,197,94,0.12); }

.stat-insight-card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 1rem 1.25rem; margin: 1.5rem 0;
    font-size: 0.95rem; color: var(--text-muted); font-style: italic;
    border-left: 3px solid var(--domain-color, var(--accent, #90A4AE));
}
.stat-insight-card.domain-economy { border-left-color: #90A4AE; }
.stat-insight-card.domain-social  { border-left-color: #B388C7; }
.stat-insight-card.domain-prices  { border-left-color: #f97316; }
.stat-insight-card.domain-state   { border-left-color: #22c55e; }

.stat-chart-container {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 1.5rem; margin: 1rem 0 1.5rem;
}
.stat-chart-wrap { position: relative; height: 440px; }

/* Event chips */
.stat-event-filter {
    display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 1rem; align-items: center;
}
.stat-event-filter-label {
    font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.08em;
    color: var(--text-muted); font-weight: 600; margin-right: 0.25rem;
}
.stat-event-chip {
    display: inline-flex; align-items: center; gap: 0.45rem;
    padding: 0.3rem 0.75rem; border-radius: 20px;
    font-size: 0.75rem; font-weight: 600; cursor: pointer;
    border: 1px solid var(--border); background: var(--surface);
    color: var(--text-muted); transition: all 0.2s ease; user-select: none;
}
.stat-event-chip:hover { color: var(--text, #e2e4e9); border-color: var(--accent, #90A4AE); }
.stat-event-chip.active { color: var(--text, #e2e4e9); border-color: transparent; }
.stat-event-chip .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--chip-color); }
.stat-event-chip.active.cat-crisis    { background: rgba(198,40,40,0.15); border-color: rgba(198,40,40,0.4); }
.stat-event-chip.active.cat-policy    { background: rgba(234,179,8,0.12); border-color: rgba(234,179,8,0.4); }
.stat-event-chip.active.cat-elections { background: rgba(144,164,174,0.12); border-color: rgba(144,164,174,0.4); }
.stat-event-chip.active.cat-milestone { background: rgba(34,197,94,0.12); border-color: rgba(34,197,94,0.4); }
.stat-event-chip.active.cat-government{ background: rgba(249,115,22,0.12); border-color: rgba(249,115,22,0.4); }
.stat-event-chip.cat-crisis    { --chip-color: #C62828; }
.stat-event-chip.cat-policy    { --chip-color: #eab308; }
.stat-event-chip.cat-elections { --chip-color: #90A4AE; }
.stat-event-chip.cat-milestone { --chip-color: #22c55e; }
.stat-event-chip.cat-government{ --chip-color: #f97316; }

/* Event legend */
.stat-event-legend {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 0.5rem 1.5rem; margin-top: 1rem; font-size: 0.78rem;
}
.stat-event-legend-item {
    display: flex; align-items: baseline; gap: 0.6rem;
    color: var(--text-muted); padding: 0.25rem 0.5rem;
    border-radius: 4px; cursor: pointer;
    transition: background 0.2s ease, color 0.2s ease; margin: 0 -0.5rem;
}
.stat-event-legend-item:hover, .stat-event-legend-item.hovered {
    background: rgba(255,255,255,0.04); color: var(--text, #e2e4e9);
}
.stat-event-legend-item.hidden { display: none; }
.stat-event-legend-item .marker {
    display: inline-block; width: 8px; height: 8px; border-radius: 50%;
    flex-shrink: 0; transform: translateY(1px);
}
.stat-event-legend-item .date {
    color: var(--text, #e2e4e9); font-weight: 600;
    font-variant-numeric: tabular-nums; white-space: nowrap; min-width: 64px;
}

/* Data table */
details.stat-data-table-wrap { margin-top: 1.5rem; }
details.stat-data-table-wrap summary {
    cursor: pointer; color: var(--text-muted); font-size: 0.8rem;
    padding: 0.75rem 1rem; background: var(--surface);
    border: 1px solid var(--border); border-radius: var(--radius);
    list-style: none; text-transform: uppercase;
    letter-spacing: 0.06em; font-weight: 600;
}
details.stat-data-table-wrap summary::-webkit-details-marker { display: none; }
details.stat-data-table-wrap summary::before { content: '\25B8  '; }
details.stat-data-table-wrap[open] summary::before { content: '\25BE  '; }
details.stat-data-table-wrap summary:hover { color: var(--text, #e2e4e9); }
.stat-data-table {
    width: 100%; border-collapse: collapse; margin-top: 0.75rem;
}
.stat-data-table th, .stat-data-table td {
    padding: 0.5rem 0.85rem; text-align: right;
    border-bottom: 1px solid var(--border); font-size: 0.8rem;
    font-variant-numeric: tabular-nums;
}
.stat-data-table th {
    color: var(--text-muted); font-weight: 600; text-align: left;
    text-transform: uppercase; font-size: 0.65rem; letter-spacing: 0.08em;
}
.stat-data-table td:first-child { text-align: left; color: var(--text-muted); }
.stat-data-table tr:last-child td { border-bottom: none; }

.stat-source-note {
    margin-top: 2rem; padding-top: 1rem; border-top: 1px solid var(--border);
    font-size: 0.8rem; color: var(--text-muted);
}
.stat-source-note a { color: var(--text-muted); text-decoration: underline; }
</style>
{% endblock %}

{% block content %}
<div class="stat-breadcrumb">
    <a href="../statistika.html">&larr; Atpakaļ uz pārskatu</a>
</div>

<header class="stat-detail-header">
    <div class="stat-detail-title">
        <div>
            <h1>{{ meta.label_lv }}</h1>
            <div class="stat-detail-meta">
                <span class="domain-chip domain-{{ meta.domain }}">{{ meta.domain_label }}</span>
                <span class="sep">&middot;</span>
                <span><strong>{{ meta.unit }}</strong></span>
                <span class="sep">&middot;</span>
                <span>{{ meta.freq_label }}</span>
                <span class="sep">&middot;</span>
                <span>{{ meta.range_str }}</span>
                {% if meta.csp_updated_short %}
                <span class="sep">&middot;</span>
                <span>Atj. {{ meta.csp_updated_short }}</span>
                {% endif %}
            </div>
        </div>
        <div class="stat-hero-value">
            <span class="num">{{ latest.formatted }}</span>
            {% if latest.change_formatted %}
            <span class="stat-hero-change {{ 'positive' if latest.change_positive else 'negative' }}">
                {{ latest.change_formatted }}
            </span>
            {% endif %}
        </div>
    </div>
</header>

{% if insight %}
<div class="stat-insight-card domain-{{ meta.domain }}">{{ insight }}</div>
{% endif %}

{% if event_categories %}
<div class="stat-event-filter" id="event-filter">
    <span class="stat-event-filter-label">Notikumi:</span>
    {% for cat in event_categories %}
    <span class="stat-event-chip cat-{{ cat.id }} active" data-cat="{{ cat.id }}">
        <span class="dot"></span>{{ cat.label }} ({{ cat.count }})
    </span>
    {% endfor %}
</div>
{% endif %}

<div class="stat-chart-container">
    <div class="stat-chart-wrap">
        <canvas id="main-chart"></canvas>
    </div>
    {% if events_list %}
    <div class="stat-event-legend" id="event-legend">
        {% for evt in events_list %}
        <div class="stat-event-legend-item" data-cat="{{ evt.category }}" data-evt-idx="{{ evt.idx }}">
            <span class="marker" style="background: {{ evt.color }}"></span>
            <span class="date">{{ evt.date_label }}</span>
            <span>{{ evt.text }}</span>
        </div>
        {% endfor %}
    </div>
    {% endif %}
</div>

<details class="stat-data-table-wrap">
    <summary>Datu tabula ({{ data_rows | length }} ieraksti)</summary>
    <table class="stat-data-table">
        <thead><tr><th>Periods</th><th>V&#275;rt&#299;ba</th></tr></thead>
        <tbody>
        {% for row in data_rows %}
        <tr><td>{{ row.period }}</td><td>{{ row.formatted }}</td></tr>
        {% endfor %}
        </tbody>
    </table>
</details>

<div class="stat-source-note">
    Dati: <a href="https://data.stat.gov.lv/" target="_blank" rel="noopener">Centr&#257;l&#257; statistikas p&#257;rvalde</a>
</div>
{% endblock %}

{% block scripts %}
<script src="../assets/chart.min.js"></script>
<script src="../assets/chartjs-plugin-annotation.min.js"></script>
<script>
const DATA = {{ chart_json | safe }};
const EVENTS = {{ events_json | safe }};
const DOMAIN = '{{ meta.domain }}';
const DOMAIN_COLORS = {
    economy: '#90A4AE', social: '#B388C7',
    prices: '#f97316', state: '#22c55e'
};
const CATEGORY_COLORS = {
    crisis: '#C62828', policy: '#eab308',
    elections: '#90A4AE', milestone: '#22c55e', government: '#f97316',
};
const color = DOMAIN_COLORS[DOMAIN] || '#90A4AE';

let chartInstance = null;
const activeCategories = new Set(EVENTS.map(e => e.category));
let highlightedEventIdx = null;

function buildAnnotations() {
    const annotations = {};
    const labelToIdx = new Map();
    DATA.labels.forEach((l, i) => labelToIdx.set(l, i));
    EVENTS.forEach((evt, i) => {
        if (!activeCategories.has(evt.category)) return;
        const idx = labelToIdx.get(evt.label);
        if (idx === undefined) return;
        const yVal = DATA.values[idx];
        if (yVal === null || yVal === undefined) return;
        const isHighlighted = highlightedEventIdx === i;
        const isDimmed = highlightedEventIdx !== null && !isHighlighted;
        annotations['line' + i] = {
            type: 'line', xMin: evt.label, xMax: evt.label,
            borderColor: CATEGORY_COLORS[evt.category] + (isHighlighted ? 'C0' : (isDimmed ? '15' : '40')),
            borderWidth: isHighlighted ? 1.5 : 1, borderDash: [3, 3],
        };
        annotations['pt' + i] = {
            type: 'point', xValue: evt.label, yValue: yVal,
            radius: isHighlighted ? 8 : 5,
            backgroundColor: CATEGORY_COLORS[evt.category] + (isDimmed ? '40' : ''),
            borderColor: '#0d1014', borderWidth: 2,
        };
    });
    return annotations;
}

function eventsAtLabel(label) {
    return EVENTS.filter(e => e.label === label && activeCategories.has(e.category));
}

function render() {
    const ctx = document.getElementById('main-chart').getContext('2d');
    const gradient = ctx.createLinearGradient(0, 0, 0, 440);
    gradient.addColorStop(0, color + '2E');
    gradient.addColorStop(1, 'transparent');
    if (chartInstance) chartInstance.destroy();
    chartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: DATA.labels,
            datasets: [{
                label: DATA.label, data: DATA.values,
                borderColor: color, backgroundColor: gradient,
                borderWidth: 2, fill: true, tension: 0.25,
                pointRadius: DATA.values.length > 60 ? 0 : 2.5,
                pointHoverRadius: 5, pointBackgroundColor: color,
                pointBorderColor: '#0d1014', pointBorderWidth: 1,
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: {
                legend: {display: false},
                annotation: {annotations: buildAnnotations()},
                tooltip: {
                    backgroundColor: 'rgba(13,16,20,0.96)',
                    titleColor: '#e2e4e9', bodyColor: '#e2e4e9',
                    footerColor: '#c9cdd9',
                    borderColor: 'rgba(255,255,255,0.1)', borderWidth: 1,
                    cornerRadius: 6, padding: 12, displayColors: false,
                    titleFont: {weight: '600', size: 12},
                    bodyFont: {size: 13},
                    footerFont: {size: 11, weight: '400', style: 'italic'},
                    footerMarginTop: 8,
                    callbacks: {
                        footer: (items) => {
                            if (!items.length) return '';
                            const matching = eventsAtLabel(items[0].label);
                            if (!matching.length) return '';
                            return matching.map(e => '\u25CF ' + e.text);
                        },
                    },
                },
            },
            scales: {
                x: {
                    ticks: {color: '#8b8fa3', maxTicksLimit: 12, font: {size: 11}},
                    grid: {color: 'rgba(255,255,255,0.03)', drawTicks: false},
                    border: {color: 'rgba(255,255,255,0.05)'},
                },
                y: {
                    ticks: {color: '#8b8fa3', font: {size: 11}},
                    grid: {color: 'rgba(255,255,255,0.03)', drawTicks: false},
                    border: {display: false},
                },
            },
            interaction: {intersect: false, mode: 'index'},
            animation: {duration: 800},
        }
    });
}

function toggleCategory(cat) {
    if (activeCategories.has(cat)) activeCategories.delete(cat);
    else activeCategories.add(cat);
    document.querySelectorAll('.stat-event-chip').forEach(chip => {
        chip.classList.toggle('active', activeCategories.has(chip.dataset.cat));
    });
    document.querySelectorAll('.stat-event-legend-item').forEach(item => {
        item.classList.toggle('hidden', !activeCategories.has(item.dataset.cat));
    });
    if (chartInstance) {
        chartInstance.options.plugins.annotation.annotations = buildAnnotations();
        chartInstance.update('none');
    }
}

function setHighlight(idx) {
    if (highlightedEventIdx === idx) return;
    highlightedEventIdx = idx;
    if (!chartInstance) return;
    chartInstance.options.plugins.annotation.annotations = buildAnnotations();
    chartInstance.update('none');
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.stat-event-chip').forEach(chip => {
        chip.addEventListener('click', () => toggleCategory(chip.dataset.cat));
    });
    document.querySelectorAll('.stat-event-legend-item').forEach(item => {
        const idx = parseInt(item.dataset.evtIdx, 10);
        item.addEventListener('mouseenter', () => { item.classList.add('hovered'); setHighlight(idx); });
        item.addEventListener('mouseleave', () => { item.classList.remove('hovered'); setHighlight(null); });
    });
    render();
});
</script>
{% endblock %}
```

- [ ] **Step 2: Commit**

```bash
git add templates/statistika-detail.html.j2
git commit -m "feat: add statistika detail page template with Chart.js + events"
```

---

### Task 5: Add nav link to base template

**Files:**
- Modify: `templates/base.html.j2:40-42`

- [ ] **Step 1: Add "Statistika" link in the nav**

In `templates/base.html.j2`, find the nav-links block (line 42):

```html
        <a href="{{ assets_prefix }}analizes.html"{% if active_page == "analizes" %} class="active"{% endif %}>Analīzes</a>
```

Add after it:

```html
        <a href="{{ assets_prefix }}statistika.html"{% if active_page == "statistika" %} class="active"{% endif %}>Statistika</a>
```

- [ ] **Step 2: Commit**

```bash
git add templates/base.html.j2
git commit -m "feat: add Statistika nav link to base template"
```

---

### Task 6: Add `generate_statistika()` to generate.py

**Files:**
- Modify: `src/generate.py`

This is the core integration. We add a standalone function that reads `data/csp.db` + `data/events.yaml` and renders the statistika pages into the same output directory as the main site. It reuses `_render_page` and the Jinja2 env from the main generator.

- [ ] **Step 1: Add imports at the top of `src/generate.py`**

Find the existing imports (around line 1-17) and add after the `from src.db import get_db` line:

```python
from src.csp.tables import TABLES as CSP_TABLES, DASHBOARD_ORDER as CSP_ORDER, DOMAIN_COLORS as CSP_DOMAIN_COLORS
from src.csp.insights import generate_insight as csp_generate_insight
```

- [ ] **Step 2: Add the `generate_statistika` function**

Add before `def _render_page` (around line 1980). This is a self-contained function with all helpers inlined:

```python
# ── CSP Statistika generator ──────────────────────────────────────────

_CSP_FREQ_LABELS = {"M": "Mēnesis", "Q": "Ceturksnis", "A": "Gads"}
_CSP_DOMAIN_LABELS = {
    "economy": "Ekonomika", "social": "Sociālie",
    "prices": "Cenas", "state": "Valsts",
}
_CSP_CATEGORY_LABELS = {
    "crisis": "Krīzes", "milestone": "Milestones",
    "policy": "Politika", "elections": "Vēlēšanas", "government": "Valdība",
}
_CSP_CATEGORY_COLORS = {
    "crisis": "#C62828", "milestone": "#22c55e",
    "policy": "#eab308", "elections": "#90A4AE", "government": "#f97316",
}


def generate_statistika(
    output_dir: str | None = None,
    csp_db_path: str | None = None,
    events_path: str | None = None,
) -> None:
    """Generate CSP statistika pages (dashboard + 10 detail pages).

    Designed to run independently from generate_public_site().
    Call after syncing CSP data (weekly/monthly).
    """
    root = Path(__file__).parent.parent
    output_dir = output_dir or str(root / "output")
    csp_db_path = csp_db_path or str(root / "data" / "csp.db")
    events_path = events_path or str(root / "data" / "events.yaml")

    atmina_dir = Path(output_dir) / "atmina"
    stat_dir = atmina_dir / "statistika"
    stat_dir.mkdir(parents=True, exist_ok=True)

    # Ensure assets exist (chart.js + annotation plugin)
    assets_dir = atmina_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    chart_js = assets_dir / "chart.min.js"
    if not chart_js.exists():
        _download_chart_js(chart_js)
    annotation_js = assets_dir / "chartjs-plugin-annotation.min.js"
    if not annotation_js.exists():
        _download_annotation_plugin(annotation_js)

    import sqlite3 as _sqlite3
    csp_conn = _sqlite3.connect(csp_db_path)
    csp_conn.row_factory = _sqlite3.Row

    # Load events
    events = []
    ep = Path(events_path)
    if ep.exists():
        events = yaml.safe_load(ep.read_text(encoding="utf-8")).get("events", [])

    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=True,
    )

    # ── Helper functions (local) ──

    def _period_to_label(period: str) -> str:
        if "M" in period:
            parts = period.split("M")
            return f"{parts[0]}-{parts[1]}"
        if "Q" in period:
            parts = period.split("Q")
            return f"{parts[0]} Q{parts[1]}"
        return period

    def _get_data(table_id: str) -> list[dict]:
        rows = csp_conn.execute(
            "SELECT period, value FROM csp_data WHERE table_id=? AND geo='LV' ORDER BY period",
            (table_id,),
        ).fetchall()
        return [{"period": r[0], "value": r[1]} for r in rows]

    def _compute_change(latest, prev, trend_dir):
        result = {"change": None, "formatted": "", "positive": True}
        if not prev or prev.get("value") is None or latest.get("value") is None:
            return result
        diff = latest["value"] - prev["value"]
        if prev["value"] != 0:
            pct = (diff / abs(prev["value"])) * 100
            result["formatted"] = f"{pct:+.1f}%"
        else:
            result["formatted"] = f"{diff:+.1f}"
        result["change"] = diff
        if trend_dir == "higher_is_better":
            result["positive"] = diff >= 0
        elif trend_dir == "lower_is_better":
            result["positive"] = diff <= 0
        else:
            result["positive"] = True
        return result

    def _event_to_period_label(event_date, freq):
        year, month = event_date[:4], event_date[5:7]
        if freq == "M":
            return f"{year}-{month}"
        if freq == "Q":
            q = (int(month) - 1) // 3 + 1
            return f"{year} Q{q}"
        return year

    def _event_applies(event, table_id):
        tables = event.get("tables", "all")
        if tables == "all" or tables is None:
            return True
        if isinstance(tables, list):
            return table_id in tables
        return False

    def _date_label(d, freq):
        if freq == "M": return d[:7]
        if freq == "Q":
            q = (int(d[5:7]) - 1) // 3 + 1
            return f"{d[:4]} Q{q}"
        return d[:4]

    def _range_str(rows, freq):
        if not rows: return ""
        first = _period_to_label(rows[0]["period"])
        last = _period_to_label(rows[-1]["period"])
        try:
            years = int(rows[-1]["period"][:4]) - int(rows[0]["period"][:4]) + 1
            return f"{first} → {last} · {years} g."
        except Exception:
            return f"{first} → {last}"

    def _build_events(table_id, freq, chart_labels_set):
        applicable = [e for e in events if _event_applies(e, table_id)]
        mapped = []
        for evt in applicable:
            pl = _event_to_period_label(evt["date"], freq)
            if pl not in chart_labels_set:
                continue
            cat = evt.get("category", "milestone")
            mapped.append({
                "label": pl, "text": evt["label"],
                "date_label": _date_label(evt["date"], freq),
                "category": cat,
                "color": _CSP_CATEGORY_COLORS.get(cat, "#90A4AE"),
            })
        mapped.sort(key=lambda e: e["label"])
        for i, m in enumerate(mapped):
            m["idx"] = i
        cat_counts: dict[str, int] = {}
        for m in mapped:
            cat_counts[m["category"]] = cat_counts.get(m["category"], 0) + 1
        event_categories = [
            {"id": c, "label": _CSP_CATEGORY_LABELS.get(c, c.title()), "count": n}
            for c, n in sorted(cat_counts.items(), key=lambda x: -x[1])
        ]
        events_json_data = [
            {"label": m["label"], "text": m["text"], "category": m["category"]}
            for m in mapped
        ]
        return {"events_list": mapped, "events_json_data": events_json_data, "event_categories": event_categories}

    # ── Dashboard ──

    cards = []
    for i, table_id in enumerate(CSP_ORDER):
        cfg = CSP_TABLES[table_id]
        rows = _get_data(table_id)
        if not rows:
            continue
        latest, prev = rows[-1], rows[-2] if len(rows) >= 2 else None
        change = _compute_change(latest, prev, cfg["trend_direction"])
        values_tuples = [(r["period"], r["value"]) for r in rows if r["value"] is not None]
        insight = csp_generate_insight(values_tuples, cfg["trend_direction"])
        spark = rows[-24:]
        meta_row = csp_conn.execute(
            "SELECT csp_updated FROM csp_metadata WHERE table_id=?", (table_id,)
        ).fetchone()
        csp_updated_short = (meta_row[0] or "")[:10] if meta_row and meta_row[0] else ""
        cards.append({
            "table_id": table_id, "label": cfg["label"], "domain": cfg["domain"],
            "formatted_value": cfg["format_short"](latest["value"]),
            "change": change["change"], "change_positive": change["positive"],
            "formatted_change": change["formatted"],
            "insight": insight,
            "sparkline_labels": [_period_to_label(r["period"]) for r in spark],
            "sparkline_values": [r["value"] for r in spark],
            "csp_updated_short": csp_updated_short,
            "index": i,
        })

    last_updated = max((c["csp_updated_short"] for c in cards if c["csp_updated_short"]), default="")
    cards_json = json.dumps(
        [{k: v for k, v in c.items() if k != "change_positive"} for c in cards],
        ensure_ascii=False,
    )

    _render_page(env, "statistika.html.j2", atmina_dir / "statistika.html", {
        "cards": cards, "cards_json": cards_json, "last_updated": last_updated,
    })
    logger.info("Generated statistika dashboard with %d cards", len(cards))

    # ── Detail pages ──

    for table_id in CSP_ORDER:
        cfg = CSP_TABLES[table_id]
        rows = _get_data(table_id)
        if not rows:
            continue

        meta_row = csp_conn.execute("SELECT * FROM csp_metadata WHERE table_id=?", (table_id,)).fetchone()
        meta = dict(meta_row) if meta_row else {}
        meta["freq_label"] = _CSP_FREQ_LABELS.get(cfg["freq"], cfg["freq"])
        meta["domain"] = cfg["domain"]
        meta["domain_label"] = _CSP_DOMAIN_LABELS.get(cfg["domain"], cfg["domain"])
        meta["label_lv"] = cfg["label"]
        meta["unit"] = cfg["unit"]
        meta["range_str"] = _range_str(rows, cfg["freq"])
        meta["csp_updated_short"] = (meta.get("csp_updated") or "")[:10]

        latest_row, prev_row = rows[-1], rows[-2] if len(rows) >= 2 else None
        change = _compute_change(latest_row, prev_row, cfg["trend_direction"])
        latest = {
            "formatted": cfg["format_value"](latest_row["value"]),
            "change_formatted": change["formatted"],
            "change_positive": change["positive"],
        }

        labels = [_period_to_label(r["period"]) for r in rows]
        values = [r["value"] for r in rows]
        chart_json = json.dumps(
            {"labels": labels, "values": values, "label": cfg["label"]},
            ensure_ascii=False,
        )

        evt_ctx = _build_events(table_id, cfg["freq"], set(labels))
        events_json = json.dumps(evt_ctx["events_json_data"], ensure_ascii=False)

        values_tuples = [(r["period"], r["value"]) for r in rows if r["value"] is not None]
        insight = csp_generate_insight(values_tuples, cfg["trend_direction"])

        fmt = cfg["format_value"]
        data_rows = [
            {"period": _period_to_label(r["period"]),
             "formatted": fmt(r["value"]) if r["value"] is not None else "..."}
            for r in reversed(rows)
        ]

        _render_page(env, "statistika-detail.html.j2", stat_dir / f"{table_id}.html", {
            "meta": meta, "latest": latest, "chart_json": chart_json,
            "events_json": events_json, "events_list": evt_ctx["events_list"],
            "event_categories": evt_ctx["event_categories"],
            "insight": insight, "data_rows": data_rows,
        })
        logger.info("Generated statistika detail: %s (%d events)", table_id, len(evt_ctx["events_list"]))

    csp_conn.close()
    logger.info("Statistika generation complete → %s", stat_dir)
```

- [ ] **Step 3: Add "statistika.html" to the sitemap**

Find the `root_pages` list in `_generate_sitemap` (around line 2020):

```python
    root_pages = [
        "",  # canonical homepage
        "pozicijas.html", "pretrunas.html", "balsojumi.html",
        "partijas.html", "personas.html", "zinas.html", "x.html",
        "saites.html", "finanses.html", "analizes.html",
        "spriedzes.html", "about.html", "blog.html",
    ]
```

Add `"statistika.html"` to the list.

Also add after the party URL loop:

```python
    # CSP statistika detail pages
    for tid in ["NVA011m", "PCI021m", "DSV010m", "IRS010m", "IKP010",
                "VFV050", "NNI030", "KRE020m", "IBE010", "ISP010c"]:
        urls.append(f"{BASE_URL}/statistika/{tid}.html")
```

- [ ] **Step 4: Verify the function loads**

```bash
cd "~/atmina" && python -c "from src.generate import generate_statistika; print('generate_statistika imported ok')"
```

Expected: `generate_statistika imported ok`

- [ ] **Step 5: Commit**

```bash
git add src/generate.py
git commit -m "feat: add generate_statistika() for CSP statistics pages"
```

---

### Task 7: Generate and verify the statistika pages

**Files:**
- No file changes — runtime verification only

- [ ] **Step 1: Run generate_statistika()**

```bash
cd "~/atmina" && python -c "
import logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
from src.generate import generate_statistika
generate_statistika()
"
```

Expected output should show:
- `Generated statistika dashboard with 10 cards`
- 10 lines of `Generated statistika detail: XXX (N events)`
- `Statistika generation complete`

- [ ] **Step 2: Verify output files exist**

```bash
ls output/atmina/statistika.html output/atmina/statistika/
```

Expected: `statistika.html` + 10 `.html` files in `statistika/`

- [ ] **Step 3: Run generate_public_site() to regenerate the main site (with new nav link)**

```bash
cd "~/atmina" && python -c "from src.generate import generate_public_site; generate_public_site()"
```

- [ ] **Step 4: Serve and verify visually**

```bash
cd "~/atmina" && python serve.py
```

Open `http://127.0.0.1:8080/atmina/statistika.html` — check:
- Dashboard shows 10 cards with sparklines
- Each card links to detail page
- Detail pages show full chart with event annotations
- Event filter chips toggle annotation visibility
- Legend hover highlights events on chart
- Nav bar shows "Statistika" link as active

- [ ] **Step 5: Final commit if any fixes were needed**

```bash
git add -A && git commit -m "fix: statistika page adjustments"
```

---

### Task 8: Add `.gitignore` entry for `data/csp.db`

**Files:**
- Modify: `.gitignore`

The `csp.db` file should be committed initially (it has seed data), but we should document that it's synced independently. Actually — check if `data/` is already gitignored.

- [ ] **Step 1: Check current .gitignore**

```bash
cat .gitignore | grep -i "data\|csp"
```

If `data/` is fully gitignored, `csp.db` won't need a separate entry. If not, the initial commit from Task 1 already includes it — no action needed since we want the seed data tracked.

- [ ] **Step 2: No changes needed if data/ is tracked**

The `csp.db` should be in version control (small, ~180KB) so clones get seed data. Fresh data comes from `sync_all()`.
