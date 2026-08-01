# UI Restructuring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the navigation from 12 tabs to 10, adding a new Partijas (Parties) page, expanding Personas, merging Tendences into Analīzes, and moving Par mums to the footer.

**Architecture:** New `parties` DB table with party metadata. Partijas page shows party cards linking to detail sub-pages (with Biedri/Pozīcijas/Balsojumi/Spriedzes sub-tabs). Politiķi page removed — its content split between Partijas (members) and Personas (unified search). Tendences charts merged into Analīzes as a third tab.

**Tech Stack:** Python 3.12, SQLite, Jinja2 templates, vanilla JS, CSS variables (dark theme)

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `scripts/migrate_db.py` | Modify | Add `parties` table migration |
| `src/db.py` | Modify | Add `parties` table to `init_db` |
| `src/generate.py` | Modify | Add party page generation, merge tendences into analīzes, remove about page, update nav references |
| `templates/base.html.j2` | Modify | New nav (10 tabs), footer with Par mums content |
| `templates/partijas.html.j2` | Create | Party index page — card grid |
| `templates/partija.html.j2` | Create | Individual party detail page with sub-tabs |
| `templates/personas.html.j2` | Modify | Expand to include all tracked people (politicians + commentators) |
| `templates/analizes.html.j2` | Modify | Add Tendences as third tab |
| `templates/politiki.html.j2` | Delete (stop rendering) | Content moves to Partijas + Personas |
| `templates/tendences.html.j2` | Delete (stop rendering) | Content moves to Analīzes |
| `templates/about.html.j2` | Delete (stop rendering) | Content moves to footer |
| `assets/style.css` | Modify | Party card styles, sub-tab styles |

---

### Task 1: `parties` DB table + seed data

**Files:**
- Modify: `src/db.py:22-293` (add CREATE TABLE to init_db)
- Modify: `scripts/migrate_db.py` (add migration)

- [ ] **Step 1: Add `parties` table to `init_db` in `src/db.py`**

Add after the `knab_alerts` CREATE INDEX block (around line 292), before the sqlite-vec section:

```python
        -- Parties
        CREATE TABLE IF NOT EXISTS parties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            short_name TEXT NOT NULL UNIQUE,
            x_handle TEXT,
            website TEXT,
            ideology TEXT,
            coalition_status TEXT DEFAULT 'opposition',
            color TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_parties_short ON parties(short_name);
```

- [ ] **Step 2: Add migration to `scripts/migrate_db.py`**

Add a new migration function that creates the table and seeds it with the 7 active parties:

```python
def migrate_parties(db):
    """Add parties table and seed with known parties."""
    db.executescript("""
        CREATE TABLE IF NOT EXISTS parties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            short_name TEXT NOT NULL UNIQUE,
            x_handle TEXT,
            website TEXT,
            ideology TEXT,
            coalition_status TEXT DEFAULT 'opposition',
            color TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_parties_short ON parties(short_name);
    """)

    seed = [
        ("Jaunā Vienotība", "JV", "JaunaVienotiba", "https://jv.lv", "Liberālkonservatīvisms", "coalition", "#2563eb"),
        ("Progresīvie", "PRO", "Progresivie_LV", "https://progresivie.lv", "Sociāldemokrātija, zaļā politika", "coalition", "#16a34a"),
        ("Zaļo un Zemnieku savienība", "ZZS", "zzs_lv", "https://zzs.lv", "Agrārisms, centrisms", "coalition", "#65a30d"),
        ("Nacionālā apvienība", "NA", "nacionala_apv", "https://nacionalaapvieniba.lv", "Nacionālkonservatīvisms", "coalition", "#dc2626"),
        ("Latvija Pirmajā Vietā", "LPV", "LPV_partija", "https://lpv.lv", "Populisms, centrisms", "opposition", "#eab308"),
        ("Apvienotais saraksts", "AS", "Apvienotais_", "https://apvienotais.lv", "Konservatīvisms", "opposition", "#8b5cf6"),
        ("Stabilitātei!", "MMN", None, None, "Prokrievisks, sociālkonservatīvisms", "opposition", "#64748b"),
    ]
    for name, short, x, web, ideo, coal, color in seed:
        db.execute("""
            INSERT OR IGNORE INTO parties (name, short_name, x_handle, website, ideology, coalition_status, color)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (name, short, x, web, ideo, coal, color))
    db.commit()
```

- [ ] **Step 3: Run migration**

```bash
cd ~/atmina
PYTHONIOENCODING=utf-8 .venv/Scripts/python -c "
from scripts.migrate_db import migrate_parties
import sqlite3
db = sqlite3.connect('data/atmina.db')
migrate_parties(db)
db.close()
print('Done')
"
```

- [ ] **Step 4: Verify**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python -c "
import sqlite3
db = sqlite3.connect('data/atmina.db')
for r in db.execute('SELECT short_name, name, coalition_status FROM parties ORDER BY id'):
    print(r)
"
```

Expected: 7 rows (JV, PRO, ZZS, NA, LPV, AS, MMN).

- [ ] **Step 5: Commit**

```bash
git add src/db.py scripts/migrate_db.py
git commit -m "feat(db): add parties table with seed data"
```

---

### Task 2: Nav restructure — base template + footer

**Files:**
- Modify: `templates/base.html.j2`

- [ ] **Step 1: Update nav links in `base.html.j2`**

Replace the entire `<div class="nav-links">` block (lines 19-32) with:

```html
      <div class="nav-links">
        <a href="{{ assets_prefix }}pretrunas.html"{% if active_page == "pretrunas" %} class="active"{% endif %}>Pretrunas</a>
        <a href="{{ assets_prefix }}pozicijas.html"{% if active_page == "pozicijas" %} class="active"{% endif %}>Pozīcijas</a>
        <a href="{{ assets_prefix }}balsojumi.html"{% if active_page == "balsojumi" %} class="active"{% endif %}>Balsojumi</a>
        <a href="{{ assets_prefix }}partijas.html"{% if active_page == "partijas" %} class="active"{% endif %}>Partijas</a>
        <a href="{{ assets_prefix }}personas.html"{% if active_page == "personas" %} class="active"{% endif %}>Personas</a>
        <a href="{{ assets_prefix }}zinas.html"{% if active_page == "zinas" %} class="active"{% endif %}>Ziņas</a>
        <a href="{{ assets_prefix }}x.html"{% if active_page == "x" %} class="active"{% endif %}>X</a>
        <a href="{{ assets_prefix }}saites.html"{% if active_page == "saites" %} class="active"{% endif %}>Saites</a>
        <a href="{{ assets_prefix }}finanses.html"{% if active_page == "finanses" %} class="active"{% endif %}>Finanses</a>
        <a href="{{ assets_prefix }}analizes.html"{% if active_page == "analizes" %} class="active"{% endif %}>Analīzes</a>
      </div>
```

Changes: Politiķi → Partijas, removed Tendences, removed Par mums.

- [ ] **Step 2: Expand footer with Par mums content**

Replace the footer (lines 40-51) with:

```html
  <footer class="footer">
    <div class="container">
      <div class="footer-grid">
        <div>
          <strong>atmina.lv</strong> — Politiskā atmiņa<br>
          <small>Dati no publiskiem avotiem. MI-asistēta analīze ar ticamības novērtējumiem.</small>
        </div>
        <div>
          <strong>Metodoloģija</strong><br>
          <small>{{ footer_source_count|default(0) }} avoti · MI-asistēta pozīciju identifikācija · {{ footer_topic_count|default(0) }} tematiskie virzieni</small>
        </div>
        <div style="text-align: right;">
          <div>Saeimas vēlēšanas: <strong>2026-10-03</strong></div>
          <div><a href="https://agents.atmina.lv">agents.atmina.lv</a></div>
        </div>
      </div>
    </div>
  </footer>
```

- [ ] **Step 3: Add footer CSS to `assets/style.css`**

Find the existing `.footer` styles and add/update:

```css
.footer-grid {
  display: grid;
  grid-template-columns: 1fr 1fr auto;
  gap: 2rem;
  align-items: start;
}
@media (max-width: 768px) {
  .footer-grid { grid-template-columns: 1fr; text-align: center; }
  .footer-grid > div:last-child { text-align: center; }
}
```

- [ ] **Step 4: Commit**

```bash
git add templates/base.html.j2 assets/style.css
git commit -m "feat(nav): restructure nav 12→10 tabs, expand footer"
```

---

### Task 3: Partijas index page (template + generator)

**Files:**
- Create: `templates/partijas.html.j2`
- Modify: `src/generate.py` (add `_fetch_parties_page` + render call)

- [ ] **Step 1: Create `templates/partijas.html.j2`**

```html
{% extends "base.html.j2" %}
{% set active_page = "partijas" %}
{% set assets_prefix = "" %}

{% block title %}Partijas{% endblock %}

{% block content %}
<section class="section">
  <div class="section-header">
    <h2>Partijas</h2>
    <span class="count">{{ parties|length }} partijas</span>
  </div>

  <div class="filter-bar" style="margin-bottom:1.5rem;">
    <button class="filter-btn active" data-filter="all" onclick="filterParties('all', this)">Visas</button>
    <button class="filter-btn" data-filter="coalition" onclick="filterParties('coalition', this)">Koalīcija</button>
    <button class="filter-btn" data-filter="opposition" onclick="filterParties('opposition', this)">Opozīcija</button>
  </div>

  <div class="parties-grid" id="parties-grid">
    {% for p in parties %}
    <a href="partijas/{{ p.short_name|lower }}.html" class="party-card" data-coalition="{{ p.coalition_status }}" style="border-left: 4px solid {{ p.color }};">
      <div class="party-card-header">
        <h3>{{ p.name }}</h3>
        <span class="badge {% if p.coalition_status == 'coalition' %}badge-blue{% else %}badge-yellow{% endif %}">
          {% if p.coalition_status == 'coalition' %}Koalīcija{% else %}Opozīcija{% endif %}
        </span>
      </div>
      <div class="party-card-ideology">{{ p.ideology or '' }}</div>
      <div class="party-card-stats">
        <span>{{ p.member_count }} biedri</span>
        <span>{{ p.claims_count }} pozīcijas</span>
        <span>{{ p.contradictions_count }} pretrunas</span>
      </div>
      {% if p.x_handle %}
      <div class="party-card-social">
        <svg viewBox="0 0 24 24" class="x-icon" style="width:14px; height:14px;"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
        <span>@{{ p.x_handle }}</span>
      </div>
      {% endif %}
    </a>
    {% endfor %}
  </div>
</section>
{% endblock %}

{% block scripts %}
<script>
function filterParties(filter, btn) {
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('.party-card').forEach(card => {
    card.style.display = (filter === 'all' || card.dataset.coalition === filter) ? '' : 'none';
  });
}
</script>
{% endblock %}
```

- [ ] **Step 2: Add `_fetch_parties_page` to `src/generate.py`**

Add after `_fetch_politicians_page` (around line 649):

```python
def _fetch_parties_page(db: sqlite3.Connection) -> list[dict[str, Any]]:
    """Fetch party data with aggregated stats."""
    try:
        party_rows = db.execute("SELECT * FROM parties ORDER BY id").fetchall()
    except sqlite3.OperationalError:
        return []

    parties = []
    for r in party_rows:
        p = dict(r)
        short = p["short_name"]
        # Count members: match by party name or short_name
        p["member_count"] = db.execute("""
            SELECT COUNT(*) FROM tracked_politicians
            WHERE (party = ? OR party = ?) AND relationship_type != 'inactive'
        """, (p["name"], short)).fetchone()[0]
        # Aggregate claims
        p["claims_count"] = db.execute("""
            SELECT COUNT(*) FROM claims c
            JOIN tracked_politicians tp ON c.opponent_id = tp.id
            WHERE (tp.party = ? OR tp.party = ?) AND tp.relationship_type != 'inactive'
        """, (p["name"], short)).fetchone()[0]
        # Aggregate contradictions
        p["contradictions_count"] = db.execute("""
            SELECT COUNT(*) FROM contradictions ct
            JOIN tracked_politicians tp ON ct.opponent_id = tp.id
            WHERE (tp.party = ? OR tp.party = ?) AND tp.relationship_type != 'inactive'
        """, (p["name"], short)).fetchone()[0]
        parties.append(p)
    return parties
```

- [ ] **Step 3: Add render call in `generate_public_site`**

After the Politiķi render block (around line 965), add:

```python
    # Partijas (party index)
    partijas_dir = atmina_dir / "partijas"
    partijas_dir.mkdir(parents=True, exist_ok=True)
    parties_data = _fetch_parties_page(db)
    _render_page(env, "partijas.html.j2", atmina_dir / "partijas.html", {
        "parties": parties_data,
    })
```

- [ ] **Step 4: Add CSS for party cards**

Add to `assets/style.css`:

```css
/* Party cards */
.parties-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1rem;
}
.party-card {
  display: block;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1.25rem;
  transition: border-color var(--transition);
  color: inherit;
  text-decoration: none;
}
.party-card:hover { border-color: var(--accent); color: inherit; }
.party-card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem; }
.party-card-header h3 { font-size: 1.1rem; }
.party-card-ideology { color: var(--text-muted); font-size: 0.85rem; margin-bottom: 0.75rem; }
.party-card-stats { display: flex; gap: 1rem; font-size: 0.85rem; color: var(--text-muted); }
.party-card-social { display: flex; align-items: center; gap: 0.4rem; margin-top: 0.5rem; font-size: 0.8rem; color: var(--text-muted); }
```

- [ ] **Step 5: Verify site generates**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python -c "from src.generate import generate_public_site; generate_public_site()"
```

- [ ] **Step 6: Commit**

```bash
git add templates/partijas.html.j2 src/generate.py assets/style.css
git commit -m "feat: add Partijas index page with party cards"
```

---

### Task 4: Individual party detail pages

**Files:**
- Create: `templates/partija.html.j2`
- Modify: `src/generate.py` (add `_fetch_party_detail` + render loop)

- [ ] **Step 1: Create `templates/partija.html.j2`**

```html
{% extends "base.html.j2" %}
{% set active_page = "partijas" %}
{% set assets_prefix = "../" %}

{% block title %}{{ party.name }}{% endblock %}

{% block content %}
<section class="section">
  <a href="../partijas.html" class="back-link">&larr; Visas partijas</a>

  <div class="profile-header" style="border-left: 4px solid {{ party.color }}; padding-left: 1rem;">
    <h1>{{ party.name }}</h1>
    <div class="role">{{ party.ideology or '' }}</div>
    <div class="party-badge" style="margin-top:0.5rem;">
      <span class="badge {% if party.coalition_status == 'coalition' %}badge-blue{% else %}badge-yellow{% endif %}">
        {% if party.coalition_status == 'coalition' %}Koalīcija{% else %}Opozīcija{% endif %}
      </span>
      {% if party.x_handle %}
      <a href="https://x.com/{{ party.x_handle }}" target="_blank" rel="noopener" class="x-icon-link" title="@{{ party.x_handle }}" style="margin-left:0.5rem;">
        <svg viewBox="0 0 24 24" class="x-icon"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
      </a>
      {% endif %}
    </div>
  </div>

  <div class="stats-row">
    <div class="stat-card">
      <div class="stat-value">{{ members|length }}</div>
      <div class="stat-label">Biedri</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{{ claims_count }}</div>
      <div class="stat-label">Pozīcijas</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{{ contradictions_count }}</div>
      <div class="stat-label">Pretrunas</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{{ votes_count }}</div>
      <div class="stat-label">Balsojumi</div>
    </div>
  </div>

  <!-- Sub-tabs -->
  <div class="filter-bar" style="margin-bottom:1.5rem; margin-top:2rem;">
    <button class="filter-btn active" onclick="showPartyTab('biedri', this)">Biedri ({{ members|length }})</button>
    <button class="filter-btn" onclick="showPartyTab('pozicijas', this)">Pozīcijas ({{ claims|length }})</button>
    <button class="filter-btn" onclick="showPartyTab('balsojumi', this)">Balsojumi ({{ votes|length }})</button>
    <button class="filter-btn" onclick="showPartyTab('spriedzes', this)">Spriedzes ({{ tensions|length }})</button>
    {% if knab_summary %}
    <button class="filter-btn" onclick="showPartyTab('finanses', this)">Finanses</button>
    {% endif %}
  </div>

  <!-- Biedri tab -->
  <div class="party-tab" id="tab-biedri">
    <div class="politicians-grid">
      {% for m in members %}
      <div class="politician-card">
        <div style="display:flex; align-items:center; gap:0.4rem;">
          <a href="../politiki/{{ m.slug }}.html" class="politician-card-name" style="margin-bottom:0;">{{ m.name }}</a>
          {% if m.x_handle %}<a href="https://x.com/{{ m.x_handle }}" target="_blank" rel="noopener" class="x-icon-link" title="@{{ m.x_handle }}"><svg viewBox="0 0 24 24" class="x-icon"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg></a>{% endif %}
        </div>
        <span class="party-tag">{{ m.role or '' }}</span>
        <div class="politician-card-stats">
          <span>{{ m.claims_count }} pozīcijas</span>
          <span>{{ m.contradictions_count }} pretrunas</span>
          <span>{{ m.votes_count }} balsojumi</span>
        </div>
      </div>
      {% endfor %}
    </div>
  </div>

  <!-- Pozīcijas tab -->
  <div class="party-tab" id="tab-pozicijas" style="display:none;">
    {% if claims %}
    <div class="claims-list">
      {% for c in claims %}
      <div class="claim-card">
        <div class="claim-header">
          <a href="../politiki/{{ c.slug }}.html" class="claim-politician">{{ c.politician_name }}</a>
          <span class="topic-tag">{{ c.topic }}</span>
          <span class="claim-date">{{ c.stated_at[:10] if c.stated_at else '' }}</span>
        </div>
        <div class="claim-stance">{{ c.stance }}</div>
        {% if c.source_url %}<a href="{{ c.source_url }}" target="_blank" rel="noopener" class="claim-source">Avots ↗</a>{% endif %}
      </div>
      {% endfor %}
    </div>
    {% else %}
    <p style="color:var(--text-muted);">Nav pozīciju.</p>
    {% endif %}
  </div>

  <!-- Balsojumi tab -->
  <div class="party-tab" id="tab-balsojumi" style="display:none;">
    {% if votes %}
    <div class="table-scroll">
      <table>
        <thead>
          <tr><th>Datums</th><th>Balsojums</th><th>Par</th><th>Pret</th><th>Atturas</th></tr>
        </thead>
        <tbody>
          {% for v in votes %}
          <tr>
            <td>{{ v.date }}</td>
            <td>{{ v.summary }}</td>
            <td style="color:var(--green)">{{ v.par }}</td>
            <td style="color:var(--red)">{{ v.pret }}</td>
            <td style="color:var(--yellow)">{{ v.atturas }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
    {% else %}
    <p style="color:var(--text-muted);">Nav balsojumu.</p>
    {% endif %}
  </div>

  <!-- Spriedzes tab -->
  <div class="party-tab" id="tab-spriedzes" style="display:none;">
    {% if tensions %}
    {% for t in tensions %}
    <div class="card" style="margin-bottom:0.75rem;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
        <span class="badge {% if t.tension_type == 'uzbrukums' %}badge-red{% elif t.tension_type == 'atbalsts' %}badge-green{% else %}badge-yellow{% endif %}">{{ t.tension_type }}</span>
        <span style="color:var(--text-muted); font-size:0.8rem;">{{ t.created_at[:10] if t.created_at else '' }}</span>
      </div>
      <div><strong>{{ t.source_name }}</strong> → <strong>{{ t.target_name }}</strong></div>
      <div class="topic-tag">{{ t.topic }}</div>
      <div style="margin-top:0.5rem; font-size:0.9rem;">{{ t.description }}</div>
      {% if t.source_url %}<a href="{{ t.source_url }}" target="_blank" rel="noopener" style="font-size:0.8rem;">Avots ↗</a>{% endif %}
    </div>
    {% endfor %}
    {% else %}
    <p style="color:var(--text-muted);">Nav spriedžu.</p>
    {% endif %}
  </div>

  <!-- Finanses tab -->
  {% if knab_summary %}
  <div class="party-tab" id="tab-finanses" style="display:none;">
    <div class="stats-row" style="margin-bottom:1.5rem;">
      <div class="stat-card">
        <div class="stat-value">€{{ "{:,.0f}".format(knab_summary.total_donations) }}</div>
        <div class="stat-label">Kopējās ziedojumi</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ knab_summary.donor_count }}</div>
        <div class="stat-label">Ziedotāji</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ knab_summary.alert_count }}</div>
        <div class="stat-label">Brīdinājumi</div>
      </div>
    </div>
    <a href="../finanses.html" class="filter-btn" style="display:inline-block;">Skatīt pilnu finanses lapu →</a>
  </div>
  {% endif %}
</section>
{% endblock %}

{% block scripts %}
<script>
function showPartyTab(tab, btn) {
  document.querySelectorAll('.party-tab').forEach(t => t.style.display = 'none');
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + tab).style.display = '';
  btn.classList.add('active');
}
</script>
{% endblock %}
```

- [ ] **Step 2: Add `_fetch_party_detail` to `src/generate.py`**

```python
def _fetch_party_detail(db: sqlite3.Connection, party: dict) -> dict[str, Any]:
    """Fetch full detail for one party: members, claims, votes, tensions, KNAB."""
    name = party["name"]
    short = party["short_name"]
    party_match = "(tp.party = ? OR tp.party = ?)"

    # Members
    member_rows = db.execute(f"""
        SELECT tp.id, tp.name, tp.role, tp.x_handle,
               (SELECT COUNT(*) FROM claims WHERE opponent_id = tp.id) as claims_count,
               (SELECT COUNT(*) FROM contradictions WHERE opponent_id = tp.id) as contradictions_count,
               (SELECT COUNT(*) FROM saeima_individual_votes WHERE politician_id = tp.id) as votes_count
        FROM tracked_politicians tp
        WHERE {party_match} AND tp.relationship_type != 'inactive'
        ORDER BY tp.name
    """, (name, short)).fetchall()
    members = []
    for r in member_rows:
        m = dict(r)
        m["slug"] = _slugify(m["name"])
        members.append(m)

    # Claims (latest 100)
    claim_rows = db.execute(f"""
        SELECT c.*, tp.name AS politician_name
        FROM claims c
        JOIN tracked_politicians tp ON c.opponent_id = tp.id
        WHERE {party_match} AND tp.relationship_type != 'inactive'
        ORDER BY c.stated_at DESC LIMIT 100
    """, (name, short)).fetchall()
    claims = []
    for r in claim_rows:
        d = dict(r)
        d["slug"] = _slugify(d["politician_name"])
        claims.append(d)

    # Votes (party aggregate from saeima_votes where party members voted)
    vote_rows = db.execute(f"""
        SELECT sv.id, sv.date, sv.summary, sv.topic,
               SUM(CASE WHEN siv.vote = 'par' THEN 1 ELSE 0 END) as par,
               SUM(CASE WHEN siv.vote = 'pret' THEN 1 ELSE 0 END) as pret,
               SUM(CASE WHEN siv.vote = 'atturas' THEN 1 ELSE 0 END) as atturas
        FROM saeima_votes sv
        JOIN saeima_individual_votes siv ON sv.id = siv.vote_id
        JOIN tracked_politicians tp ON siv.politician_id = tp.id
        WHERE {party_match}
        GROUP BY sv.id
        ORDER BY sv.date DESC LIMIT 50
    """, (name, short)).fetchall()
    votes = [dict(r) for r in vote_rows]

    # Tensions involving this party's members
    tension_rows = db.execute(f"""
        SELECT pt.*, s.name AS source_name, s.party AS source_party,
               t.name AS target_name, t.party AS target_party
        FROM political_tensions pt
        JOIN tracked_politicians s ON pt.source_pid = s.id
        JOIN tracked_politicians t ON pt.target_pid = t.id
        WHERE (s.party IN (?, ?) OR t.party IN (?, ?))
        ORDER BY pt.created_at DESC LIMIT 30
    """, (name, short, name, short)).fetchall()
    tensions = [dict(r) for r in tension_rows]

    # KNAB summary
    knab_summary = None
    try:
        total = db.execute("SELECT COALESCE(SUM(amount_eur), 0) FROM knab_donations WHERE party = ?", (name,)).fetchone()[0]
        donors = db.execute("SELECT COUNT(DISTINCT donor_id) FROM knab_donations WHERE party = ?", (name,)).fetchone()[0]
        alerts = db.execute("SELECT COUNT(*) FROM knab_alerts WHERE party = ?", (name,)).fetchone()[0]
        if total > 0 or donors > 0:
            knab_summary = {"total_donations": total, "donor_count": donors, "alert_count": alerts}
    except sqlite3.OperationalError:
        pass

    claims_count = sum(m["claims_count"] for m in members)
    contradictions_count = sum(m["contradictions_count"] for m in members)
    votes_count = sum(m["votes_count"] for m in members)

    return {
        "members": members,
        "claims": claims,
        "votes": votes,
        "tensions": tensions,
        "knab_summary": knab_summary,
        "claims_count": claims_count,
        "contradictions_count": contradictions_count,
        "votes_count": votes_count,
    }
```

- [ ] **Step 3: Add render loop in `generate_public_site`**

After the Partijas index render, add:

```python
    # Individual party pages
    for party in parties_data:
        detail = _fetch_party_detail(db, party)
        _render_page(env, "partija.html.j2", partijas_dir / f"{party['short_name'].lower()}.html", {
            "party": party,
            **detail,
        })
    logger.info("Generated %d party pages", len(parties_data))
```

- [ ] **Step 4: Verify**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python -c "from src.generate import generate_public_site; generate_public_site()"
```

Check `output/atmina/partijas.html` and `output/atmina/partijas/jv.html` exist.

- [ ] **Step 5: Commit**

```bash
git add templates/partija.html.j2 src/generate.py
git commit -m "feat: add individual party detail pages with sub-tabs"
```

---

### Task 5: Expand Personas page

**Files:**
- Modify: `templates/personas.html.j2`
- Modify: `src/generate.py:967-987` (personas data fetch)

- [ ] **Step 1: Update personas data fetch in `src/generate.py`**

Replace the current persona_rows query (lines 968-987) with one that includes ALL tracked people with category tags:

```python
    # Personas (all tracked people — unified search)
    persona_rows = db.execute("""
        SELECT tp.id, tp.name, tp.party, tp.relationship_type, tp.x_handle, tp.role,
               (SELECT COUNT(*) FROM claims WHERE opponent_id = tp.id) as claims_count,
               (SELECT COUNT(*) FROM documents WHERE opponent_id = tp.id) as docs_count,
               (SELECT COUNT(*) FROM contradictions WHERE opponent_id = tp.id) as contradictions_count,
               (SELECT COUNT(*) FROM saeima_individual_votes WHERE politician_id = tp.id) as votes_count
        FROM tracked_politicians tp
        WHERE tp.relationship_type != 'inactive'
        ORDER BY tp.name
    """).fetchall()
    personas = []
    category_counts = {}
    for r in persona_rows:
        p = dict(r)
        p["slug"] = _slugify(p["name"])
        # Assign category
        rt = p["relationship_type"]
        if p["votes_count"] > 0:
            cat = "Deputāti"
        elif rt in ("journalist", "influencer", "neutral"):
            cat = {"journalist": "Žurnālisti", "influencer": "Ietekmētāji", "neutral": "Analītiķi"}.get(rt, "Citi")
        elif p.get("party") == "MMN":
            cat = "Kandidāti"
        elif p.get("party"):
            cat = "Amatpersonas"
        else:
            cat = "Citi"
        p["category"] = cat
        category_counts[cat] = category_counts.get(cat, 0) + 1
        personas.append(p)
    _render_page(env, "personas.html.j2", atmina_dir / "personas.html", {
        "personas": personas,
        "category_counts": category_counts,
    })
```

- [ ] **Step 2: Update `templates/personas.html.j2`**

Replace entire file with expanded version including category filter and party tags:

```html
{% extends "base.html.j2" %}
{% set active_page = "personas" %}
{% set assets_prefix = "" %}

{% block title %}Personas{% endblock %}

{% block content %}
<section class="section">
  <div class="section-header">
    <h2>Personas</h2>
    <span class="count">{{ personas|length }} sekotās personas</span>
  </div>

  <div class="filter-bar" style="margin-bottom:1rem;">
    <button class="filter-btn active" data-cat="all" onclick="filterCat('all', this)">Visas ({{ personas|length }})</button>
    {% for cat, cnt in category_counts.items() %}
    <button class="filter-btn" data-cat="{{ cat }}" onclick="filterCat('{{ cat }}', this)">{{ cat }} ({{ cnt }})</button>
    {% endfor %}
  </div>

  <div style="margin-bottom:1.5rem;">
    <input type="text" class="politicians-search" placeholder="Meklēt personu..." id="persona-search">
  </div>

  <div class="politicians-grid" id="personas-grid">
    {% for p in personas %}
    <div class="politician-card persona-card" data-name="{{ p.name|lower }}" data-category="{{ p.category }}" data-party="{{ p.party or '' }}">
      <div style="display:flex; align-items:flex-start; gap:0.75rem;">
        <div class="x-avatar" style="width:36px; height:36px; font-size:0.85rem; flex-shrink:0;">{{ p.name[0] }}</div>
        <div style="flex:1; min-width:0;">
          <div style="display:flex; align-items:center; gap:0.4rem;">
            <a href="politiki/{{ p.slug }}.html" class="politician-card-name" style="margin-bottom:0;">{{ p.name }}</a>
            {% if p.x_handle %}<a href="https://x.com/{{ p.x_handle }}" target="_blank" rel="noopener" class="x-icon-link" title="@{{ p.x_handle }}"><svg viewBox="0 0 24 24" class="x-icon"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg></a>{% endif %}
          </div>
          <div style="display:flex; gap:0.4rem; flex-wrap:wrap; margin-top:0.25rem;">
            <span class="party-tag" style="font-size:0.7rem;">{{ p.category }}</span>
            {% if p.party %}<span class="party-tag" style="font-size:0.7rem;">{{ p.party }}</span>{% endif %}
          </div>
          <div class="politician-card-stats">
            {% if p.claims_count %}<a href="pozicijas.html?persona={{ p.name|urlencode }}">{{ p.claims_count }} pozīcijas</a>{% else %}<span>0 pozīcijas</span>{% endif %}
            {% if p.contradictions_count %}<a href="pretrunas.html?persona={{ p.name|urlencode }}">{{ p.contradictions_count }} pretrunas</a>{% else %}<span>0 pretrunas</span>{% endif %}
            <span>{{ p.docs_count }} dokumenti</span>
          </div>
        </div>
      </div>
    </div>
    {% endfor %}
  </div>
</section>
{% endblock %}

{% block scripts %}
<script>
(function() {
  var search = document.getElementById('persona-search');
  var activeCat = 'all';

  function applyFilters() {
    var q = (search.value || '').toLowerCase();
    document.querySelectorAll('#personas-grid .persona-card').forEach(function(card) {
      var matchName = !q || card.dataset.name.includes(q);
      var matchCat = activeCat === 'all' || card.dataset.category === activeCat;
      card.style.display = (matchName && matchCat) ? '' : 'none';
    });
  }

  window.filterCat = function(cat, btn) {
    activeCat = cat;
    document.querySelectorAll('.filter-btn').forEach(function(b) { b.classList.remove('active'); });
    btn.classList.add('active');
    applyFilters();
  };

  search.addEventListener('input', applyFilters);
})();
</script>
{% endblock %}
```

- [ ] **Step 3: Verify**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python -c "from src.generate import generate_public_site; generate_public_site()"
```

- [ ] **Step 4: Commit**

```bash
git add templates/personas.html.j2 src/generate.py
git commit -m "feat: expand Personas page with all tracked people + category filters"
```

---

### Task 6: Merge Tendences into Analīzes

**Files:**
- Modify: `templates/analizes.html.j2`
- Modify: `src/generate.py` (pass trends_data to analīzes render)

- [ ] **Step 1: Update analīzes render call in `src/generate.py`**

Find the Analīzes render (around line 1079) and add trends_data + context_notes:

```python
    _render_page(env, "analizes.html.j2", atmina_dir / "analizes.html", {
        "analyses": analyses,
        "posts": blog_posts,
        "trends_data": trends_data,
        "context_notes": context_notes,
    })
```

- [ ] **Step 2: Update `templates/analizes.html.j2`**

Add a third tab "Tendences" to the existing tab bar. After the existing `<div id="anal-daily">` section, add:

```html
    <button class="filter-btn" id="tab-trends" onclick="switchAnalTab('trends')">Tendences</button>
```

And add the trends content div after the daily div:

```html
  <div id="anal-trends" style="display:none;">
    {% if trends_data %}
    <div class="grid-2">
      <div class="chart-container">
        <h3>Populārākās tēmas (30d)</h3>
        <canvas id="topicsChart"></canvas>
      </div>
      <div class="chart-container">
        <h3>Aktīvākie politiķi (30d)</h3>
        <canvas id="politiciansChart"></canvas>
      </div>
    </div>
    <div class="chart-container">
      <h3>Laika līnija — pozīcijas un dokumenti (30d)</h3>
      <canvas id="timelineChart"></canvas>
    </div>
    {% endif %}
    {% if context_notes %}
    <div class="section-header" style="margin-top:2rem">
      <h3>Konteksts</h3>
    </div>
    <div class="grid-3">
      {% for note in context_notes %}
      <div class="card">
        <div style="color:var(--text-muted); font-size:0.8rem; margin-bottom:0.5rem;">{{ note.topic or '' }} · {{ note.created_at[:10] if note.created_at else '' }}</div>
        <div style="font-size:0.9rem;">{{ note.content }}</div>
      </div>
      {% endfor %}
    </div>
    {% endif %}
  </div>
```

Update the JS `switchAnalTab` function to handle the new tab, and load Chart.js charts on first switch.

- [ ] **Step 3: Remove standalone tendences render from `generate_public_site`**

Comment out or remove lines 1030-1033 (the tendences.html render call). Keep the template file for now — just stop generating it.

- [ ] **Step 4: Remove standalone about render**

Comment out or remove lines 1090-1093 (the about.html render call).

- [ ] **Step 5: Pass footer context globally**

In the `_render_page` function or in `generate_public_site`, make `footer_source_count` and `footer_topic_count` available. Simplest: add to every render call via a shared context dict, or modify `_render_page` to inject global vars.

Add before the render loop:

```python
    # Global template vars (available to all pages via base.html.j2)
    global_ctx = {
        "footer_source_count": source_count,
        "footer_topic_count": topic_count,
    }
```

Then modify `_render_page` to accept and merge global context:

```python
def _render_page(env, template_name, output_path, context, global_ctx=None):
    template = env.get_template(template_name)
    if global_ctx:
        ctx = {**global_ctx, **context}
    else:
        ctx = context
    html = template.render(**ctx)
    output_path.write_text(html, encoding="utf-8")
```

And pass `global_ctx` to every `_render_page` call.

- [ ] **Step 6: Verify full site generation**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python -c "from src.generate import generate_public_site; generate_public_site()"
```

Verify: `output/atmina/analizes.html` has 3 tabs. `output/atmina/tendences.html` no longer generated. `output/atmina/about.html` no longer generated.

- [ ] **Step 7: Commit**

```bash
git add templates/analizes.html.j2 src/generate.py
git commit -m "feat: merge Tendences into Analīzes, remove standalone About page"
```

---

### Task 7: Remove old Politiķi page generation + cleanup

**Files:**
- Modify: `src/generate.py` (remove politiķi render, update output summary)

- [ ] **Step 1: Remove politiķi.html render**

Remove or comment out lines 957-965 (the politiki.html render call). Keep the `_fetch_politicians_page` function for now — it may be useful for data access.

- [ ] **Step 2: Update politician profile back-links**

In `templates/politician.html.j2` line 9, change:
```html
<a href="../pozicijas.html" class="back-link">&larr; Visi politiķi</a>
```
to:
```html
<a href="../personas.html" class="back-link">&larr; Visas personas</a>
```

- [ ] **Step 3: Update print summary in `generate_public_site`**

Update the print statements at the end to reflect the new page count and mention party pages.

- [ ] **Step 4: Verify**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python -c "from src.generate import generate_public_site; generate_public_site()"
```

- [ ] **Step 5: Commit**

```bash
git add src/generate.py templates/politician.html.j2
git commit -m "refactor: remove standalone Politiķi page, update back-links"
```

---

### Task 8: Final verification + type check

- [ ] **Step 1: Run full site generation**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python -c "from src.generate import generate_public_site; generate_public_site()"
```

- [ ] **Step 2: Verify all pages exist**

```bash
ls output/atmina/partijas.html output/atmina/partijas/ output/atmina/personas.html output/atmina/analizes.html
ls output/atmina/partijas/*.html | wc -l  # Should be 7 party pages
```

- [ ] **Step 3: Verify removed pages don't exist (or are stale)**

Check that `politiki.html`, `tendences.html`, `about.html` are NOT in the latest generation output.

- [ ] **Step 4: Run tests**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python -m pytest tests/ -v
```

- [ ] **Step 5: Visual check with serve**

Open `output/atmina/index.html` in browser and verify:
- Nav has 10 tabs (not 12)
- Partijas page shows 7 party cards
- Party detail pages have sub-tabs
- Personas shows all tracked people with category filters
- Analīzes has 3 tabs (Tematiskās, Dienas pārskati, Tendences)
- Footer shows methodology info

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "feat: complete UI restructuring — Partijas, expanded Personas, nav 12→10"
```
