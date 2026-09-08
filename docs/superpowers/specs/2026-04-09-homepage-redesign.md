# Homepage Redesign Spec

**Date:** 2026-04-09
**Goal:** Redesign atmina.lv homepage to be more informative, compact, and visually polished. Replace generic hero + stat cards with a dense, purposeful landing that communicates what's happening in Latvian politics right now.

## Current State

The homepage has 5 sections:
1. Hero — large SVG logo (duplicates nav logo), title, subtitle, stats text links
2. Stats row — 4 separate `stat-card` elements (Politiki, Pozicijas, Pretrunas, Balsojumi)
3. Jaunakas pretrunas — 6 full contradiction cards in `grid-2`
4. Pedejie Saeimas balsojumi — 10-row vote table
5. CTA banner — agents.atmina.lv promo

`days_until_election` is passed to the template but never rendered.

## New Design

### 1. Hero (compact, informative)

**Remove:** Large SVG logo (already in nav).

**Keep:** Title "atmina.lv" + subtitle "politiska caurskatamiba".

**Add:**
- **Election countdown** below subtitle: large number (e.g. `177`) in `--accent` color, with "dienas lidz Saeimas velesanam" in `--text-muted` below it. No conditional logic needed — will be removed/repurposed manually post-election.
- **Stat counters** as a compact inline row replacing the separate `stats-row` section. Format: `150 politiki · 6102 pozicijas · 312 pretrunas · 847 balsojumi`. Each is a link to the respective page. Styled as inline text with `--text-muted`, no card borders/padding.
- **Activity bar** below stats: "Pedejas 7 dienas: +34 pozicijas · +2 balsojumi" in smaller font, `--text-muted`. Two metrics only (pozicijas + balsojumi, no pretrunas — they don't appear daily).

**Delete:** The separate `<section class="stats-row">` with 4 `stat-card` elements.

**Mobile:** All inline rows wrap naturally. Countdown stacks above stats.

### 2. Daily Brief Card (new section)

Immediately below hero. Shows the latest daily brief from `context_notes` (note_type='daily_brief').

- Left border accent (like contradiction severity indicator) to visually distinguish from other sections
- Header: "Dienas parskats · 9. apr." (type label + formatted date)
- Body: first 2-3 lines of brief content as preview text
- Footer: "Lasit vairak ->" link to `blog/{date}.html`
- Only shown if the latest brief exists and is from the last 3 days

**Data source:** `_fetch_blog_posts(db)` already exists. Pass `blog_posts[0]` to the index template as `latest_brief`.

### 3. Latest Contradictions (reduced)

- **3 cards** instead of 6 — keeps the impactful "before vs after" format which is the platform's core value proposition
- Section header with link: "Jaunakas pretrunas" (left) + "Visas pretrunas ->" (right, links to `pretrunas.html`)
- Card design unchanged — already works well

**Data:** Change `contradictions[:6]` to `contradictions[:3]` in generate.py.

### 4. Latest Votes (reduced)

- **5 rows** instead of 10
- Section header with link: "Pedejie balsojumi" (left) + "Visi balsojumi ->" (right, links to `balsojumi.html`)
- Table design unchanged

**Data:** Change `votes[:10]` to `votes[:5]` in generate.py.

### 5. CTA Banner (subtler)

- Reduce padding from `2.5rem` to `1.5rem`
- Smaller heading font
- Keep content and link unchanged

## Data Changes in generate.py

### `_fetch_stats()` — add 7-day activity counts

```python
cutoff_7d = (date.today() - timedelta(days=7)).strftime("%Y-%m-%d")
stats["claims_7d"] = db.execute(
    "SELECT COUNT(*) FROM claims WHERE stated_at >= ?", (cutoff_7d,)
).fetchone()[0]
stats["votes_7d"] = db.execute(
    "SELECT COUNT(*) FROM saeima_votes WHERE vote_date >= ?", (cutoff_7d,)
).fetchone()[0]
```

### Index template data — add latest brief

```python
_render_page(env, "index.html.j2", atmina_dir / "index.html", {
    "stats": stats,
    "days_until_election": days_until,
    "latest_contradictions": contradictions[:3],  # was [:6]
    "recent_votes": votes[:5],                    # was [:10]
    "latest_brief": blog_posts[0] if blog_posts else None,  # NEW
})
```

## CSS Changes

- Keep `.stats-row` / `.stat-card` CSS classes (used by `partija.html.j2` and `finanses.html.j2`)
- Add `.hero-countdown` — large number styling
- Add `.hero-stats-inline` — compact inline stat row
- Add `.hero-activity` — activity bar styling
- Add `.brief-card` — daily brief preview card with left border accent
- Add `.section-header-link` — "Visas pretrunas ->" style link in section headers
- Reduce `.cta-banner` padding

## Template Changes

- `index.html.j2` — full rewrite of hero section, add brief card, add section header links, reduce data counts
- `base.html.j2` — no changes needed

## Files Affected

1. `src/generate.py` — `_fetch_stats()` (add 2 queries), index render call (change slice sizes, add latest_brief)
2. `templates/index.html.j2` — hero rewrite, add brief card, section header links, reduce counts
3. `assets/style.css` — new classes, CTA padding reduction

## Out of Scope

- Nav tab restructuring (Analizes/Parskati) — future work
- Bento/dashboard grid layout — rejected for stability
- "Aktivakie politiki" section — future work
- "Karstakas temas" section — future work
- Post-election countdown handling — manual change when needed
