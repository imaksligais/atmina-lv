# Homepage Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign atmina.lv homepage — compact hero with election countdown and activity stats, daily brief card, reduced pretrunas/balsojumi with "view all" links, subtler CTA.

**Architecture:** Three files changed: `generate.py` (add 7-day stats + latest brief data), `index.html.j2` (full template rewrite), `style.css` (new hero/brief classes). No new files. No DB schema changes.

**Tech Stack:** Python (Jinja2 templates), CSS, static HTML generation.

---

### Task 1: Add 7-day activity stats and latest brief to generate.py

**Files:**
- Modify: `src/generate.py:213-220` (`_fetch_stats`)
- Modify: `src/generate.py:1539-1544` (index render call)

- [ ] **Step 1: Add 7-day counts to `_fetch_stats()`**

In `src/generate.py`, replace the `_fetch_stats` function:

```python
def _fetch_stats(db: sqlite3.Connection) -> dict[str, int]:
    cutoff_7d = (date.today() - timedelta(days=7)).strftime("%Y-%m-%d")
    return {
        "politicians": db.execute("SELECT COUNT(*) FROM tracked_politicians WHERE relationship_type != 'inactive'").fetchone()[0],
        "politicians_active": db.execute("SELECT COUNT(DISTINCT opponent_id) FROM claims").fetchone()[0],
        "claims": db.execute("SELECT COUNT(*) FROM claims").fetchone()[0],
        "contradictions": db.execute("SELECT COUNT(*) FROM contradictions").fetchone()[0],
        "votes": db.execute("SELECT COUNT(*) FROM saeima_votes").fetchone()[0],
        "claims_7d": db.execute("SELECT COUNT(*) FROM claims WHERE stated_at >= ?", (cutoff_7d,)).fetchone()[0],
        "votes_7d": db.execute("SELECT COUNT(*) FROM saeima_votes WHERE vote_date >= ?", (cutoff_7d,)).fetchone()[0],
    }
```

- [ ] **Step 2: Update index render call to pass latest brief and reduce slices**

In `src/generate.py`, replace the index render block (around line 1539):

```python
    # 1. Index
    latest_brief = blog_posts[0] if blog_posts else None
    _render_page(env, "index.html.j2", atmina_dir / "index.html", {
        "stats": stats,
        "days_until_election": days_until,
        "latest_contradictions": contradictions[:3],
        "recent_votes": votes[:5],
        "latest_brief": latest_brief,
    })
```

- [ ] **Step 3: Verify generation runs without errors**

Run: `cd "~/atmina" && .venv/Scripts/python -c "from src.generate import generate_public_site; generate_public_site()" 2>&1 | tail -5`

Expected: Normal output listing generated pages, no errors.

- [ ] **Step 4: Commit**

```bash
git add src/generate.py
git commit -m "feat(homepage): add 7-day activity stats and latest brief to index data"
```

---

### Task 2: Add new CSS classes for homepage redesign

**Files:**
- Modify: `assets/style.css`

- [ ] **Step 1: Add hero countdown, inline stats, activity bar, and brief card styles**

In `assets/style.css`, find the `.hero-stats` rule (around line 402-406) and replace the entire hero stats block plus add new classes after it:

Replace:
```css
.hero-stats {
  font-size: 0.95rem;
  color: var(--text-muted);
  margin: 0;
}
```

With:
```css
.hero-stats {
  font-size: 0.95rem;
  color: var(--text-muted);
  margin: 0;
}
.hero-countdown {
  margin: 1rem 0 0.25rem;
}
.hero-countdown .countdown-number {
  font-size: 3.5rem;
  font-weight: 700;
  color: var(--accent);
  line-height: 1;
  letter-spacing: -0.03em;
}
.hero-countdown .countdown-label {
  font-size: 0.85rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}
.hero-stats-inline {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 0.25rem 0.75rem;
  margin-top: 1.25rem;
  font-size: 0.9rem;
  color: var(--text-muted);
}
.hero-stats-inline a {
  color: var(--text-muted);
  text-decoration: none;
  transition: color var(--transition);
}
.hero-stats-inline a:hover { color: var(--accent); }
.hero-stats-inline .stat-num {
  font-weight: 600;
  color: var(--text);
}
.hero-stats-inline .sep {
  opacity: 0.4;
}
.hero-activity {
  margin-top: 0.5rem;
  font-size: 0.8rem;
  color: var(--text-muted);
}
```

- [ ] **Step 2: Add brief card styles**

In `assets/style.css`, add after the CTA banner section (after line 429 `.cta-banner .btn:hover`):

```css
/* Daily Brief Card */
.brief-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-left: 3px solid var(--accent);
  border-radius: var(--radius);
  padding: 1.25rem 1.5rem;
  margin-bottom: 2rem;
}
.brief-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}
.brief-card-title {
  font-weight: 600;
  font-size: 0.9rem;
}
.brief-card-date {
  color: var(--text-muted);
  font-size: 0.8rem;
}
.brief-card-preview {
  color: var(--text-muted);
  font-size: 0.88rem;
  line-height: 1.5;
  margin-bottom: 0.75rem;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.brief-card-link {
  font-size: 0.82rem;
  color: var(--accent);
}
.brief-card-link:hover { text-decoration: underline; }
```

- [ ] **Step 3: Add section header link style and reduce CTA padding**

In `assets/style.css`, replace the `.section-header` block:

```css
.section-header { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 2rem; }
.section-header h2 { margin-bottom: 0.25rem; }
.section-header .count { color: var(--text-muted); font-size: 0.95rem; }
.section-header-link { font-size: 0.85rem; color: var(--text-muted); white-space: nowrap; }
.section-header-link:hover { color: var(--accent); }
```

Then replace the CTA banner padding:

```css
.cta-banner {
  background: linear-gradient(135deg, var(--surface), var(--surface2));
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1.5rem;
  text-align: center;
  margin: 2rem 0;
}
.cta-banner h3 { margin-bottom: 0.5rem; font-size: 1.1rem; }
```

- [ ] **Step 4: Update mobile breakpoints**

In `assets/style.css`, find the mobile breakpoint (around line 1125) that has `.hero` rules and update:

Replace:
```css
  .hero { padding: 2rem 1rem 1.5rem; }
  .hero-title { font-size: 2rem; }
  .hero-logo { height: 48px; }
```

With:
```css
  .hero { padding: 2rem 1rem 1.5rem; }
  .hero-title { font-size: 2rem; }
  .hero-countdown .countdown-number { font-size: 2.5rem; }
  .brief-card { padding: 1rem; }
```

- [ ] **Step 5: Commit**

```bash
git add assets/style.css
git commit -m "feat(homepage): add CSS for countdown, inline stats, brief card, section links"
```

---

### Task 3: Rewrite index.html.j2 template

**Files:**
- Modify: `templates/index.html.j2` (full rewrite)

- [ ] **Step 1: Rewrite the hero section**

In `templates/index.html.j2`, replace everything from `<section class="hero">` through `</section>` (the stats-row section, lines 8-41) with:

```html
<section class="hero">
  <div class="hero-inner">
    <h1 class="hero-title">atmina.lv</h1>
    <p class="hero-subtitle">politisk&#257; caurskat&#257;m&#299;ba</p>
    <div class="hero-countdown">
      <div class="countdown-number">{{ days_until_election }}</div>
      <div class="countdown-label">dienas l&#299;dz Saeimas v&#275;l&#275;&#353;an&#257;m</div>
    </div>
    <div class="hero-stats-inline">
      <a href="personas.html"><span class="stat-num">{{ stats.politicians_active }}</span> politi&#311;i</a>
      <span class="sep">&middot;</span>
      <a href="pozicijas.html"><span class="stat-num">{{ stats.claims }}</span> poz&#299;cijas</a>
      <span class="sep">&middot;</span>
      <a href="pretrunas.html"><span class="stat-num">{{ stats.contradictions }}</span> pretrunas</a>
      <span class="sep">&middot;</span>
      <a href="balsojumi.html"><span class="stat-num">{{ stats.votes }}</span> balsojumi</a>
    </div>
    <div class="hero-activity">P&#275;d&#275;j&#257;s 7 dien&#257;s: +{{ stats.claims_7d }} poz&#299;cijas &middot; +{{ stats.votes_7d }} balsojumi</div>
  </div>
</section>
```

- [ ] **Step 2: Add daily brief card section**

After the hero section, add the brief card (before the pretrunas section):

```html
{% if latest_brief %}
<section class="container">
  <div class="brief-card">
    <div class="brief-card-header">
      <span class="brief-card-title">{{ latest_brief.type_label }}</span>
      <span class="brief-card-date">{{ latest_brief.date }}</span>
    </div>
    <div class="brief-card-preview">{{ latest_brief.preview }}</div>
    <a href="blog/{{ latest_brief.slug }}.html" class="brief-card-link">Las&#299;t vair&#257;k &rarr;</a>
  </div>
</section>
{% endif %}
```

- [ ] **Step 3: Update pretrunas section header with "view all" link**

Replace the pretrunas section header:

```html
<section class="section">
  <div class="section-header">
    <h2>Jaun&#257;k&#257;s pretrunas</h2>
    <a href="pretrunas.html" class="section-header-link">Visas pretrunas &rarr;</a>
  </div>
```

- [ ] **Step 4: Update balsojumi section header with "view all" link**

Replace the balsojumi section header:

```html
<section class="section">
  <div class="section-header">
    <h2>P&#275;d&#275;jie Saeimas balsojumi</h2>
    <a href="balsojumi.html" class="section-header-link">Visi balsojumi &rarr;</a>
  </div>
```

- [ ] **Step 5: Verify — regenerate site and check output**

Run: `cd "~/atmina" && .venv/Scripts/python -c "from src.generate import generate_public_site; generate_public_site()" 2>&1 | tail -5`

Expected: Normal output, no errors.

Then verify key elements in output:

Run: `grep -c "hero-countdown\|brief-card\|section-header-link\|hero-activity" "~/atmina/output/atmina/index.html"`

Expected: 4+ matches confirming all new elements are present.

- [ ] **Step 6: Commit**

```bash
git add templates/index.html.j2
git commit -m "feat(homepage): rewrite template with countdown, brief card, section links"
```

---

### Task 4: Visual verification and final adjustments

**Files:**
- Possibly: `assets/style.css` (tweaks)
- Possibly: `templates/index.html.j2` (tweaks)

- [ ] **Step 1: Open the generated page and verify visually**

Open `file:///~/atmina/output/atmina/index.html` in browser. Check:
1. Hero: countdown number visible, stats row compact and inline, activity bar shows 7-day numbers
2. Brief card: left accent border, preview text, "Lasit vairak" link
3. Pretrunas: 3 cards (not 6), "Visas pretrunas ->" link in header
4. Balsojumi: 5 rows (not 10), "Visi balsojumi ->" link in header
5. CTA: smaller padding, less dominant
6. Mobile: resize browser narrow, verify nothing breaks

- [ ] **Step 2: Fix any visual issues found**

Apply CSS tweaks as needed based on visual review.

- [ ] **Step 3: Final commit if tweaks were needed**

```bash
git add -A
git commit -m "fix(homepage): visual polish after review"
```
