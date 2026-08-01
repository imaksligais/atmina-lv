# Profile Page Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform politician profile pages from flat data tables into rich, narrative pages with timeline, tensions, news, party linking, and X integration.

**Architecture:** Enrich `_fetch_politician_detail` in `src/generate.py` to return timeline events, tensions, recent news, and party metadata. Rewrite `templates/politician.html.j2` with tabbed interface (Timeline, Pretrunas, Balsojumi, Spriedzes) and enriched header with X link and party color.

**Tech Stack:** Python 3.12, SQLite, Jinja2, vanilla JS, CSS variables (dark theme)

**NOTE:** Another agent may be writing to the DB concurrently (party declarations analysis). All changes here are read-only templates + generator code — no DB writes.

---

## Pre-task: Sync parties table with all tracked parties

The `parties` table has 7 entries but `tracked_politicians.party` has additional values: "Bezpartejisks", "Nezināms", "Latvijas attīstībai", "Konservatīvie", and duplicate "ZZS". These don't need party pages but the profile page needs to handle them gracefully (no party link, no color).

Also, 4 politicians have `party = 'ZZS'` (short name) while the table has full name "Zaļo un Zemnieku savienība". The `_fetch_party_detail` already handles both via `(party = ? OR party = ?)` — profile pages should do the same.

---

### Task 1: Enrich `_fetch_politician_detail` with timeline, tensions, news, party data

**Files:**
- Modify: `src/generate.py:322-380` (`_fetch_politician_detail` function)

- [ ] **Step 1: Read current `_fetch_politician_detail`**

Current function (lines 322-380) returns: claims, contradictions, votes, claim_topics.

- [ ] **Step 2: Add timeline query**

After the existing votes query, add a combined timeline that interleaves claims and votes:

```python
    # Timeline: interleaved claims + votes, most recent first
    timeline_rows = db.execute("""
        SELECT stated_at as date, 'claim' as event_type, topic, stance as detail,
               source_url, confidence, NULL as vote_result
        FROM claims WHERE opponent_id = ? AND stated_at IS NOT NULL
        UNION ALL
        SELECT sv.vote_date as date, 'vote' as event_type, sv.topic,
               sv.motif as detail, sv.url as source_url, NULL as confidence,
               siv.vote as vote_result
        FROM saeima_individual_votes siv
        JOIN saeima_votes sv ON siv.vote_id = sv.id
        WHERE siv.politician_id = ?
        ORDER BY date DESC
        LIMIT 50
    """, (pid, pid)).fetchall()
    timeline = [dict(r) for r in timeline_rows]
```

- [ ] **Step 3: Add tensions query**

```python
    # Tensions involving this politician
    tension_rows = db.execute("""
        SELECT pt.*, s.name AS source_name, s.party AS source_party,
               t.name AS target_name, t.party AS target_party
        FROM political_tensions pt
        JOIN tracked_politicians s ON pt.source_pid = s.id
        JOIN tracked_politicians t ON pt.target_pid = t.id
        WHERE pt.source_pid = ? OR pt.target_pid = ?
        ORDER BY pt.created_at DESC LIMIT 20
    """, (pid, pid)).fetchall()
    tensions = [dict(r) for r in tension_rows]
```

- [ ] **Step 4: Add recent news query**

```python
    # Recent news mentioning this politician
    news_rows = db.execute("""
        SELECT d.id, d.source_url, d.source_domain, d.scraped_at,
               SUBSTR(d.content, 1, 200) as preview
        FROM documents d
        WHERE d.opponent_id = ? AND d.platform = 'web'
        ORDER BY d.scraped_at DESC LIMIT 10
    """, (pid,)).fetchall()
    news = [dict(r) for r in news_rows]
```

- [ ] **Step 5: Add party metadata lookup**

```python
    # Party metadata (color, link)
    party_meta = None
    politician = db.execute("SELECT * FROM tracked_politicians WHERE id = ?", (pid,)).fetchone()
    if politician:
        p_party = dict(politician).get("party")
        if p_party:
            try:
                party_row = db.execute(
                    "SELECT * FROM parties WHERE name = ? OR short_name = ?",
                    (p_party, p_party)
                ).fetchone()
                if party_row:
                    party_meta = dict(party_row)
            except Exception:
                pass
```

- [ ] **Step 6: Update return dict**

Add to the existing return:
```python
    return {
        "claims": claims,
        "contradictions": contradictions,
        "votes": votes,
        "claim_topics": claim_topics,
        "timeline": timeline,
        "tensions": tensions,
        "news": news,
        "party_meta": party_meta,
    }
```

- [ ] **Step 7: Update render call in `generate_public_site`**

Find the politician render loop (around line 1257-1271). Update to pass the new data:

```python
    for p in politicians:
        detail = _fetch_politician_detail(db, p["id"])
        wiki_profile = _load_wiki_profile(p["slug"])

        _render_page(env, "politician.html.j2", politiki_dir / f"{p['slug']}.html", {
            "politician": p,
            "claims": detail["claims"],
            "contradictions": detail["contradictions"],
            "votes": detail["votes"],
            "claim_topics": detail["claim_topics"],
            "timeline": detail["timeline"],
            "tensions": detail["tensions"],
            "news": detail["news"],
            "party_meta": detail["party_meta"],
            "wiki_profile": wiki_profile,
        })
        politician_count += 1
```

- [ ] **Step 8: Verify site generates**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python -c "from src.generate import generate_public_site; generate_public_site()"
```

- [ ] **Step 9: Commit**

```bash
git add src/generate.py
git commit -m "feat: enrich politician detail with timeline, tensions, news, party meta"
```

---

### Task 2: Rewrite politician profile template

**Files:**
- Modify: `templates/politician.html.j2` (full rewrite)
- Modify: `assets/style.css` (add timeline + profile styles)

- [ ] **Step 1: Rewrite `templates/politician.html.j2`**

Full new template:

```html
{% extends "base.html.j2" %}
{% set active_page = "" %}
{% set assets_prefix = "../" %}

{% block title %}{{ politician.name }}{% endblock %}

{% block content %}
<section class="section">
  <a href="../personas.html" class="back-link">&larr; Visas personas</a>

  <div class="profile-header"{% if party_meta %} style="border-left: 4px solid {{ party_meta.color }}; padding-left: 1rem;"{% endif %}>
    <div style="display:flex; align-items:center; gap:0.75rem; flex-wrap:wrap;">
      <h1 style="margin:0;">{{ politician.name }}</h1>
      {% if politician.x_handle %}
      <a href="https://x.com/{{ politician.x_handle }}" target="_blank" rel="noopener" class="x-icon-link" title="@{{ politician.x_handle }}">
        <svg viewBox="0 0 24 24" class="x-icon" style="width:20px; height:20px;"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
      </a>
      {% endif %}
    </div>
    <div class="role">{{ politician.role or '' }}</div>
    <div class="party-badge" style="margin-top:0.5rem;">
      {% if party_meta %}
      <a href="../partijas/{{ party_meta.short_name|lower }}.html" class="badge badge-blue" style="text-decoration:none; color:inherit;">{{ politician.party }}</a>
      {% else %}
      <span class="badge badge-blue">{{ politician.party or 'Nav norādīts' }}</span>
      {% endif %}
    </div>
  </div>

  <div class="stats-row">
    <div class="stat-card">
      <div class="stat-value">{{ politician.claims_count }}</div>
      <div class="stat-label">Pozīcijas</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{{ politician.contradictions_count }}</div>
      <div class="stat-label">Pretrunas</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{{ politician.votes_count }}</div>
      <div class="stat-label">Balsojumi</div>
    </div>
  </div>

  {% if wiki_profile %}
  <div class="wiki-profile post-content">
    {{ wiki_profile | safe }}
  </div>
  {% endif %}

  <!-- Sub-tabs -->
  <div class="filter-bar" style="margin-bottom:1.5rem; margin-top:2rem;">
    <button class="filter-btn active" onclick="showProfileTab('timeline', this)">Laika līnija ({{ timeline|length }})</button>
    <button class="filter-btn" onclick="showProfileTab('pozicijas', this)">Pozīcijas ({{ claims|length }})</button>
    {% if contradictions %}<button class="filter-btn" onclick="showProfileTab('pretrunas', this)">Pretrunas ({{ contradictions|length }})</button>{% endif %}
    {% if votes %}<button class="filter-btn" onclick="showProfileTab('balsojumi', this)">Balsojumi ({{ votes|length }})</button>{% endif %}
    {% if tensions %}<button class="filter-btn" onclick="showProfileTab('spriedzes', this)">Spriedzes ({{ tensions|length }})</button>{% endif %}
    {% if news %}<button class="filter-btn" onclick="showProfileTab('zinas', this)">Ziņas ({{ news|length }})</button>{% endif %}
  </div>

  <!-- Timeline tab -->
  <div class="profile-tab" id="tab-timeline">
    {% if timeline %}
    <div class="timeline">
      {% for e in timeline %}
      <div class="timeline-event timeline-{{ e.event_type }}">
        <div class="timeline-date">{{ e.date[:10] if e.date else '' }}</div>
        <div class="timeline-body">
          {% if e.event_type == 'claim' %}
          <span class="topic-tag">{{ e.topic }}</span>
          <div class="timeline-detail">{{ e.detail }}</div>
          {% elif e.event_type == 'vote' %}
          <span class="badge {% if e.vote_result == 'Par' %}badge-green{% elif e.vote_result == 'Pret' %}badge-red{% elif e.vote_result == 'Atturas' %}badge-yellow{% else %}badge-muted{% endif %}" style="margin-right:0.5rem;">{{ e.vote_result }}</span>
          <span class="topic-tag">{{ e.topic or '' }}</span>
          <div class="timeline-detail">{{ e.detail[:120] }}{% if e.detail and e.detail|length > 120 %}…{% endif %}</div>
          {% endif %}
          {% if e.source_url %}<a href="{{ e.source_url }}" target="_blank" rel="noopener" class="timeline-source">↗</a>{% endif %}
        </div>
      </div>
      {% endfor %}
    </div>
    {% else %}
    <p style="color:var(--text-muted);">Nav notikumu.</p>
    {% endif %}
  </div>

  <!-- Pozīcijas tab -->
  <div class="profile-tab" id="tab-pozicijas" style="display:none;">
    {% if claim_topics %}
    <div class="filter-bar" id="topic-filter" style="margin-bottom:1rem;">
      <button class="filter-btn active" data-filter="all">Visas tēmas</button>
      {% for topic in claim_topics %}
      <button class="filter-btn" data-filter="{{ topic }}">{{ topic }}</button>
      {% endfor %}
    </div>
    {% endif %}

    {% if claims %}
    <div class="table-wrap">
      <table class="data-table" id="claims-table">
        <thead>
          <tr>
            <th>Tēma</th>
            <th>Pozīcija</th>
            <th>Datums</th>
            <th>Avots</th>
          </tr>
        </thead>
        <tbody>
          {% for c in claims %}
          <tr data-topic="{{ c.topic }}">
            <td><span class="topic-tag" style="display:inline-block; background:var(--surface2); color:var(--text-muted); padding:0.15rem 0.6rem; border-radius:2rem; font-size:0.75rem;">{{ c.topic }}</span></td>
            <td>{{ c.stance }}</td>
            <td style="white-space:nowrap">{{ c.stated_at[:10] if c.stated_at else '' }}</td>
            <td>{% if c.source_url %}<a href="{{ c.source_url }}">Avots</a>{% endif %}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
    {% else %}
    <p style="color:var(--text-muted);">Nav pozīciju.</p>
    {% endif %}
  </div>

  <!-- Pretrunas tab -->
  {% if contradictions %}
  <div class="profile-tab" id="tab-pretrunas" style="display:none;">
    <div class="grid-2">
      {% for c in contradictions %}
      <div class="pretruna-card severity-{{ c.severity }}">
        <div class="card-header">
          <span class="badge {% if c.severity == 'direct_contradiction' %}badge-red{% elif c.severity == 'reversal' %}badge-orange{% else %}badge-yellow{% endif %}">{{ c.severity_lv }}</span>
        </div>
        <span class="topic-tag">{{ c.topic }}</span>
        <div class="summary">{{ c.summary }}</div>
        <div class="stances">
          <div class="stance">
            <div class="stance-label">
              Iepriekš
              {% if c.old_source %}<a href="{{ c.old_source }}" target="_blank" rel="noopener" style="margin-left:0.4rem; font-size:0.75rem; opacity:0.6;">↗</a>{% endif %}
            </div>
            {{ c.old_stance }} <span class="stance-date">{{ c.old_date }}</span>
          </div>
          <div class="stance">
            <div class="stance-label">
              {% if c.vote_id %}
              <a href="../balsojumi.html#vote-{{ c.vote_id }}" style="color:inherit; text-decoration:none; border-bottom:1px dotted currentColor;">Tagad</a>
              {% else %}Tagad{% endif %}
              {% if c.new_source %}<a href="{{ c.new_source }}" target="_blank" rel="noopener" style="margin-left:0.4rem; font-size:0.75rem; opacity:0.6;">↗</a>{% endif %}
            </div>
            {{ c.new_stance }} <span class="stance-date">{{ c.new_date }}</span>
            {% if c.vote_summary %}
            <div style="margin-top:0.5rem; padding:0.4rem 0.6rem; background:var(--bg-card-alt, rgba(127,127,127,0.07)); border-radius:4px; font-size:0.82rem; line-height:1.5;">
              <strong>Likumprojekts:</strong> {{ c.vote_summary }}
            </div>
            {% endif %}
          </div>
        </div>
        <details class="alt-explanation">
          <summary>Alternatīvs skaidrojums ▸</summary>
          <div class="alt-explanation-content">
            Šī pretruna tika konstatēta automātiski, salīdzinot pozīcijas laika gaitā. Citi iespējami skaidrojumi:
            <ul>
              <li>Pozīcija ir evoluējusi — mainījušies apstākļi vai pieejama jauna informācija</li>
              <li>Izteikumi bija domāti dažādām auditorijām ar atšķirīgu kontekstu</li>
              <li>Formulējuma atšķirība, nevis satura maiņa</li>
            </ul>
            <div style="margin-top:0.5rem;">Iepazīstieties ar avotiem un izvērtējiet paši.</div>
          </div>
        </details>
      </div>
      {% endfor %}
    </div>
  </div>
  {% endif %}

  <!-- Balsojumi tab -->
  {% if votes %}
  <div class="profile-tab" id="tab-balsojumi" style="display:none;">
    <div class="table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th>Datums</th>
            <th>Jautājums</th>
            <th>Balsojums</th>
          </tr>
        </thead>
        <tbody>
          {% for v in votes %}
          <tr>
            <td style="white-space:nowrap">{{ v.vote_date }}</td>
            <td>{{ v.motif[:80] }}{% if v.motif|length > 80 %}…{% endif %}</td>
            <td>
              <span class="badge {% if v.vote == 'Par' %}badge-green{% elif v.vote == 'Pret' %}badge-red{% elif v.vote == 'Atturas' %}badge-yellow{% else %}badge-muted{% endif %}">{{ v.vote }}</span>
            </td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </div>
  {% endif %}

  <!-- Spriedzes tab -->
  {% if tensions %}
  <div class="profile-tab" id="tab-spriedzes" style="display:none;">
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
  </div>
  {% endif %}

  <!-- Ziņas tab -->
  {% if news %}
  <div class="profile-tab" id="tab-zinas" style="display:none;">
    {% for n in news %}
    <div class="card" style="margin-bottom:0.75rem;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
        <span style="color:var(--text-muted); font-size:0.8rem;">{{ n.source_domain or '' }}</span>
        <span style="color:var(--text-muted); font-size:0.8rem;">{{ n.scraped_at[:10] if n.scraped_at else '' }}</span>
      </div>
      <div style="font-size:0.9rem;">{{ n.preview }}{% if n.preview and n.preview|length >= 200 %}…{% endif %}</div>
      {% if n.source_url %}<a href="{{ n.source_url }}" target="_blank" rel="noopener" style="font-size:0.8rem;">Lasīt pilnu rakstu ↗</a>{% endif %}
    </div>
    {% endfor %}
  </div>
  {% endif %}
</section>
{% endblock %}

{% block scripts %}
<script>
(function() {
  // Tab switching
  window.showProfileTab = function(tab, btn) {
    document.querySelectorAll('.profile-tab').forEach(function(t) { t.style.display = 'none'; });
    document.querySelectorAll('.filter-bar > .filter-btn').forEach(function(b) { b.classList.remove('active'); });
    var el = document.getElementById('tab-' + tab);
    if (el) el.style.display = '';
    btn.classList.add('active');
  };

  // Topic filter within Pozīcijas tab
  var topicFilter = document.getElementById('topic-filter');
  if (topicFilter) {
    var rows = document.querySelectorAll('#claims-table tbody tr');
    topicFilter.addEventListener('click', function(e) {
      if (!e.target.classList.contains('filter-btn')) return;
      topicFilter.querySelectorAll('.filter-btn').forEach(function(b) { b.classList.remove('active'); });
      e.target.classList.add('active');
      var f = e.target.dataset.filter;
      rows.forEach(function(row) {
        row.style.display = (f === 'all' || row.dataset.topic === f) ? '' : 'none';
      });
    });
  }
})();
</script>
{% endblock %}
```

- [ ] **Step 2: Add timeline CSS to `assets/style.css`**

Add after the existing profile styles:

```css
/* Timeline */
.timeline { position: relative; padding-left: 1.5rem; }
.timeline::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 2px;
  background: var(--border);
}
.timeline-event {
  position: relative;
  padding-bottom: 1.25rem;
  padding-left: 1rem;
}
.timeline-event::before {
  content: '';
  position: absolute;
  left: -1.5rem;
  top: 0.4rem;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 2px solid var(--border);
  background: var(--bg);
}
.timeline-claim::before { border-color: var(--accent); }
.timeline-vote::before { border-color: var(--green); }
.timeline-date {
  font-size: 0.8rem;
  color: var(--text-muted);
  margin-bottom: 0.25rem;
}
.timeline-detail {
  font-size: 0.9rem;
  margin-top: 0.25rem;
  line-height: 1.5;
}
.timeline-source {
  font-size: 0.75rem;
  opacity: 0.6;
  margin-left: 0.4rem;
}

/* Profile tabs */
.profile-tab { min-height: 200px; }
```

- [ ] **Step 3: Verify site generation**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python -c "from src.generate import generate_public_site; generate_public_site()"
```

- [ ] **Step 4: Commit**

```bash
git add templates/politician.html.j2 assets/style.css
git commit -m "feat: rebuild politician profile with timeline, tensions, news tabs"
```

---

### Task 3: Final verification

- [ ] **Step 1: Full site generation**
- [ ] **Step 2: Run tests**
- [ ] **Step 3: Spot-check key profiles** (Evika Siliņa, Ainārs Šlesers, Edgars Rinkēvičs)
- [ ] **Step 4: Verify party links work from profile**
