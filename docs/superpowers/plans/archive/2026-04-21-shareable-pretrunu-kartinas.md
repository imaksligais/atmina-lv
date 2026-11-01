# Shareable Pretrunu Kartiņas (Per-Contradiction Detail Pages + Social Preview PNGs)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When someone shares a link to a specific contradiction on X / Telegram / WhatsApp / Signal / Slack, the recipient sees a beautiful, information-dense 1200×630 rich preview card (politician photo + severity glyph + topic + IEPRIEKŠ/PAŠLAIK contrast), not the generic `atmina.lv` site hero.

**Architecture:** Two-part feature. (1) Generate a dedicated HTML page per contradiction at `/pretrunas/<id>.html` with contradiction-specific `<meta property="og:*">` tags — social crawlers ignore `#fragment`, so a real URL per card is mandatory. (2) Generate a 1200×630 PNG per contradiction at `assets/og/pretruna-<id>.png` by rendering a dedicated Jinja template in a headless Chromium via Playwright and screenshotting. The 𝕏 share button switches from an anchor URL to a detail-page URL so the X crawler fetches per-contradiction metadata.

**Tech Stack:** Python 3.11 + SQLite, Jinja2 templates, vanilla CSS, Playwright (Python) + headless Chromium for the screenshot pipeline, Pillow optional for PNG optimization. No new Python dependencies beyond Playwright (which may already be in the dev env for MCP tooling — the plan verifies and installs if missing).

**Context at session start:**

- The main page `/pretrunas.html` already renders all contradictions with `id="pretruna-<N>"` anchors and a 𝕏 share button per card.
- The share button currently links to `https://atmina.lv/pretrunas.html#pretruna-<N>` — X/Telegram ignore the `#fragment`, so ALL shared contradictions show the same site-level `og-image.png`.
- `_fetch_contradictions(db)` in `src/generate.py` already returns enriched dicts with `severity_glyph`, `initials`, `delta_days`, `old_source_domain`, `new_source_domain`, `old_quote`, `new_quote`, `party_short`, `party_color`, `slug`, `salience`, `detected_at`, `has_photo`, `summary` and everything else the OG card will need.
- Politician photos exist at `assets/photos/<slug>.jpg` — 148 available, covering all current pretrunu subjects.
- `BASE_URL = "https://atmina.lv"` is defined at `src/generate.py` top.
- The previous branch (merged or pending PR) added per-contradiction ID anchors and the hash deep-link JS that clears filters and scrolls+pulses the card. That work stays; this plan layers on top.
- At time of writing: 11 contradictions. Expected to scale to ~50 over the next year.

**Files that will be created:**

- `templates/pretruna-detail.html.j2` — standalone HTML page per contradiction, extends `base.html.j2`, overrides og/twitter meta blocks.
- `templates/og-card.html.j2` — self-contained 1200×630 HTML document used only by the screenshot pipeline (not linked from anywhere). Inlines all styles, fonts (via base64 or @font-face with data URIs), and the politician photo (base64).
- `assets/og/.gitkeep` — to ensure the output directory exists in repo layout; the generated PNGs themselves (`output/atmina/assets/og/pretruna-<N>.png`) are build artifacts, not committed.

**Files that will be modified:**

- `src/generate.py` — add `_photo_data_uri()`, `_render_og_cards()`, and a loop that renders one `pretruna-detail.html.j2` per contradiction; call `_render_og_cards()` from `generate_public_site()`; update sitemap generation to include detail URLs.
- `templates/pretrunas.html.j2` — change the 𝕏 share button `href` from anchor (`#pretruna-<N>`) to detail page (`pretrunas/<N>.html`); URL encoding handled by existing `|urlencode` filter.
- `assets/style.css` — small additions for the detail-page "back to all" link and (optional) "citas {{ politician }} pretrunu" grid at the bottom. The existing `.prv2-*` styles are reused verbatim for the main card on the detail page.
- `tests/test_generate.py` — add tests for the detail-page rendering, the OG card HTML rendering, and PNG existence/size.
- `pyproject.toml` (or `requirements.txt`) — add `playwright` as a dev/build dependency if not already present.

**Branch:** `feature/pretrunu-share-kartinas` (create fresh from current `master` / merged-state of the previous `design/pretrunas-v2` branch).

---

## Task 0: Environment verification and branch setup

**Files:** none yet

- [ ] **Step 1: Confirm the previous pretrunas-v2 branch state has landed**

Run: `git log --oneline master -5`
Expected: see the recent `feat(pretrunas)`, `fix(css)` etc commits from the Pretrunas V2 branch on `master` (or the current working branch). If those commits aren't present, STOP and resolve that first — this plan assumes they're in place.

- [ ] **Step 2: Verify working tree is clean in the paths this plan touches**

Run: `git status --short | grep -E "^( M|\?\?) (src/generate\.py|templates/(pretrunas|og-card|pretruna-detail)\.html\.j2|assets/style\.css|tests/test_generate\.py)"`
Expected: zero lines. If there are pending changes in those files, stop and ask the user.

- [ ] **Step 3: Check Python venv activation**

Run: `.venv/Scripts/python.exe --version`
Expected: `Python 3.11.x` or higher. If the path doesn't exist, escalate — the venv layout has drifted.

- [ ] **Step 4: Verify Playwright availability**

Run: `.venv/Scripts/python.exe -c "import playwright; print(playwright.__version__)"`

Expected: prints a version string (e.g. `1.48.0`).

If import fails with `ModuleNotFoundError`, install:
```bash
.venv/Scripts/python.exe -m pip install playwright
```

- [ ] **Step 5: Verify Chromium is installed for Playwright**

Run: `.venv/Scripts/python.exe -c "from playwright.sync_api import sync_playwright; sync_playwright().__enter__().chromium.launch().close()"`

Expected: completes silently.

If this fails with "Executable doesn't exist" or similar:
```bash
.venv/Scripts/python.exe -m playwright install chromium
```

Then re-run the verification.

- [ ] **Step 6: Create the feature branch**

Run:
```bash
git checkout -b feature/pretrunu-share-kartinas
git branch --show-current
```
Expected: `feature/pretrunu-share-kartinas`

- [ ] **Step 7: Record Playwright version to requirements**

Check whether `playwright` is already listed in `pyproject.toml` or `requirements.txt`:
```bash
grep -E "playwright" pyproject.toml requirements.txt 2>/dev/null
```

If it's missing, add it. Preferred: `pyproject.toml` under `[project.optional-dependencies]` in a new `build` group, since Playwright is only needed at build-time (`generate_public_site`), not at runtime. Example addition (adapt to the file's actual layout):

```toml
[project.optional-dependencies]
build = ["playwright>=1.40"]
```

If the project only has `requirements.txt`, add a line:
```
playwright>=1.40
```

Commit:
```bash
git add pyproject.toml  # or requirements.txt
git commit -m "chore: declare playwright as build-time dependency for og cards"
```

---

## Task 1: Create the OG card HTML template (`templates/og-card.html.j2`)

**Files:**
- Create: `templates/og-card.html.j2`

This template is **standalone** — it does NOT extend `base.html.j2`. It's rendered headlessly into a 1200×630 viewport and screenshotted. Nothing links to it; the browser renders it, takes a PNG, and throws it away.

Inlines everything: all CSS, the JetBrains Mono font (via Google Fonts `<link>` — Playwright will fetch it at render time; see Task 2 for networkidle wait), the politician photo as a base64 data URI.

- [ ] **Step 1: Create the template with the following content**

```jinja
<!DOCTYPE html>
<html lang="lv">
<head>
  <meta charset="UTF-8">
  <title>OG card — {{ c.id }}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    html, body {
      width: 1200px;
      height: 630px;
      overflow: hidden;
      background: #0d1014;
      color: #e2e4e9;
      font-family: Georgia, 'Times New Roman', serif;
    }
    :root {
      --sev-direct_contradiction: #dc2626;
      --sev-reversal: #f97316;
      --sev-minor_shift: #eab308;
      --mono: 'JetBrains Mono', ui-monospace, monospace;
      --text: #e2e4e9;
      --text-muted: #8b8fa3;
      --surface2: #242838;
      --border-soft: #1f2432;
    }
    .card {
      position: relative;
      width: 1200px;
      height: 630px;
      padding: 48px 56px;
      display: grid;
      grid-template-rows: auto 1fr auto;
      gap: 28px;
    }
    .sev-rail {
      position: absolute;
      top: 0; left: 0; right: 0;
      height: 8px;
      background: var(--sev);
    }
    .brand-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
      font-family: var(--mono);
      font-size: 18px;
      font-weight: 500;
      letter-spacing: 0.4px;
      color: var(--text-muted);
    }
    .brand-dot {
      width: 10px; height: 10px; border-radius: 50%;
      background: var(--sev);
    }
    .severity-chip {
      font-family: var(--mono);
      font-size: 18px;
      letter-spacing: 1.8px;
      text-transform: uppercase;
      color: var(--sev);
      border: 2px solid var(--sev);
      padding: 8px 18px;
      border-radius: 4px;
      display: inline-flex;
      align-items: center;
      gap: 10px;
    }
    .severity-glyph {
      font-family: var(--mono);
      font-size: 22px;
    }

    .main {
      display: grid;
      grid-template-columns: 200px 1fr;
      gap: 36px;
      align-items: start;
    }
    .photo {
      width: 200px; height: 200px;
      border-radius: 50%;
      border: 3px solid var(--pc, var(--border-soft));
      background: var(--surface2);
      object-fit: cover;
      flex-shrink: 0;
    }
    .avatar-fallback {
      width: 200px; height: 200px;
      border-radius: 50%;
      border: 3px solid var(--pc, var(--border-soft));
      background: var(--surface2);
      color: var(--text);
      display: flex;
      align-items: center;
      justify-content: center;
      font-family: Georgia, serif;
      font-size: 72px;
      letter-spacing: 2px;
    }
    .persona {
      min-width: 0;
    }
    .name {
      font-family: Georgia, serif;
      font-size: 58px;
      font-weight: 500;
      line-height: 1.05;
      letter-spacing: -1px;
      color: var(--text);
      margin-bottom: 14px;
    }
    .role {
      font-family: var(--mono);
      font-size: 18px;
      letter-spacing: 1.6px;
      text-transform: uppercase;
      color: var(--text-muted);
      margin-bottom: 28px;
    }
    .topic {
      display: inline-block;
      font-family: var(--mono);
      font-size: 20px;
      letter-spacing: 1.8px;
      text-transform: uppercase;
      color: var(--text);
      border-bottom: 3px solid var(--sev);
      padding-bottom: 4px;
    }

    .stances {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 28px;
      margin-top: 8px;
    }
    .stance-block {
      min-width: 0;
    }
    .stance-label {
      font-family: var(--mono);
      font-size: 14px;
      letter-spacing: 2px;
      text-transform: uppercase;
      color: var(--text-muted);
      margin-bottom: 10px;
    }
    .stance-label.then { color: var(--text-muted); }
    .stance-label.now { color: var(--sev); }
    .stance-text {
      font-family: Georgia, serif;
      font-style: italic;
      font-size: 22px;
      line-height: 1.35;
      color: var(--text);
      /* Clamp to ~4 lines */
      display: -webkit-box;
      -webkit-line-clamp: 4;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }

    .foot {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      font-family: var(--mono);
      font-size: 15px;
      letter-spacing: 1px;
      color: var(--text-muted);
    }
    .foot-brand strong {
      color: var(--text);
      font-weight: 600;
      letter-spacing: 0.8px;
    }
    .foot-id {
      color: var(--text-muted);
    }
  </style>
</head>
<body>
  <div class="card"
       style="--sev: var(--sev-{{ c.severity }}, var(--sev-minor_shift)); --pc: {{ c.party_color or '#1f2432' }};">
    <div class="sev-rail"></div>

    <div class="brand-row">
      <div class="brand">
        <span class="brand-dot"></span>
        <span>atmina.lv</span>
        <span style="color: #3a4052;">·</span>
        <span>Pretruna #{{ '%03d' % c.id }}</span>
      </div>
      <div class="severity-chip">
        <span class="severity-glyph">{{ c.severity_glyph }}</span>
        {{ c.severity_lv }}
      </div>
    </div>

    <div class="main">
      {% if c.photo_data_uri %}
      <img class="photo" src="{{ c.photo_data_uri }}" alt="">
      {% else %}
      <div class="avatar-fallback">{{ c.initials }}</div>
      {% endif %}

      <div class="persona">
        <div class="name">{{ c.politician_name }}</div>
        <div class="role">
          {%- if c.role %}{{ c.role }} · {% endif -%}
          {{ c.party_short }}
        </div>
        {% if c.topic %}
        <div class="topic">{{ c.topic }}</div>
        {% endif %}

        <div class="stances">
          <div class="stance-block">
            <div class="stance-label then">Iepriekš · {{ c.old_date }}</div>
            <div class="stance-text">{{ c.old_quote or c.old_stance }}</div>
          </div>
          <div class="stance-block">
            <div class="stance-label now">Pašlaik · {{ c.new_date }}</div>
            <div class="stance-text">{{ c.new_quote or c.new_stance }}</div>
          </div>
        </div>
      </div>
    </div>

    <div class="foot">
      <div class="foot-brand"><strong>atmina.lv</strong> — Politiskā atmiņa</div>
      <div class="foot-id">pretrunas/{{ c.id }}.html</div>
    </div>
  </div>
</body>
</html>
```

- [ ] **Step 2: Preview-render a single card manually for visual sanity**

Write a quick ad-hoc script (don't commit it):

```bash
cat > /tmp/og_preview.py <<'EOF'
import sys
sys.path.insert(0, ".")
from jinja2 import Environment, FileSystemLoader
from src.generate import _fetch_contradictions, ASSETS_DIR
from src.db import get_db
import base64
from pathlib import Path

env = Environment(loader=FileSystemLoader("templates"), autoescape=True)
db = get_db()
cs = _fetch_contradictions(db)
c = cs[0]
# Inline photo if available
photo_path = ASSETS_DIR / "photos" / f"{c['slug']}.jpg"
if photo_path.exists():
    c["photo_data_uri"] = "data:image/jpeg;base64," + base64.b64encode(photo_path.read_bytes()).decode()
else:
    c["photo_data_uri"] = None
html = env.get_template("og-card.html.j2").render(c=c)
Path("/tmp/og_preview.html").write_text(html, encoding="utf-8")
print(f"Wrote /tmp/og_preview.html for {c['politician_name']} id={c['id']}")
EOF
.venv/Scripts/python.exe /tmp/og_preview.py
```

Open `/tmp/og_preview.html` in a browser (ideally at 1200×630 viewport). Confirm: severity rail, photo circle, name, role, topic chip, both stances, foot brand. Nothing cut off. Italic quotes render in Georgia. No diacritic glitches.

If the layout is broken, fix the template BEFORE Task 2. Don't move on until the HTML looks right at 1200×630.

- [ ] **Step 3: Commit the template**

```bash
git add templates/og-card.html.j2
git commit -m "feat(templates): add og-card template for per-contradiction social preview"
```

---

## Task 2: PNG generation pipeline in `src/generate.py`

**Files:**
- Modify: `src/generate.py` — add `_photo_data_uri()` helper (unless already present) and `_render_og_cards()` function

- [ ] **Step 1: Add the `_photo_data_uri` helper**

Locate the block of private helpers near `_enrich_contradiction` in `src/generate.py`. Directly after `_domain_from_url`, add:

```python
def _photo_data_uri(slug: str) -> str | None:
    """Read `assets/photos/<slug>.jpg` and return a base64 data URI, or None."""
    path = ASSETS_DIR / "photos" / f"{slug}.jpg"
    if not path.exists():
        return None
    import base64
    return "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode()
```

- [ ] **Step 2: Add `_render_og_cards()` function**

Add this function after `_fetch_contradictions` (so it can be called from the pretrunas rendering block):

```python
def _render_og_cards(
    contradictions: list[dict[str, Any]],
    env: Environment,
    out_dir: Path,
) -> int:
    """Render 1200×630 OG preview PNGs, one per contradiction.

    Uses headless Chromium via Playwright. Launches ONE browser instance
    and reuses a single page across all cards — reduces overhead from
    ~2s/card to ~200ms/card after warmup.

    Writes to `out_dir / pretruna-<id>.png`. Skips rendering if the
    PNG already exists AND the contradiction's detected_at is older
    than the PNG's mtime (simple incremental-build optimization).

    Returns the count of cards actually rendered.
    """
    from playwright.sync_api import sync_playwright

    out_dir.mkdir(parents=True, exist_ok=True)
    tpl = env.get_template("og-card.html.j2")
    rendered = 0

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": 1200, "height": 630},
            device_scale_factor=2,  # 2x for crisp display on high-DPI social feeds
        )
        page = context.new_page()

        for c in contradictions:
            out_path = out_dir / f"pretruna-{c['id']}.png"

            # Skip if the PNG already exists and is newer than the contradiction timestamp
            if out_path.exists():
                detected = c.get("detected_at") or ""
                try:
                    from datetime import datetime
                    png_mtime = datetime.fromtimestamp(out_path.stat().st_mtime)
                    detected_dt = datetime.fromisoformat(detected.replace("Z", "+00:00")[:19])
                    if png_mtime > detected_dt:
                        continue
                except (ValueError, TypeError):
                    pass  # fall through and re-render

            # Build render context: clone dict + add photo data URI
            render_c = dict(c)
            render_c["photo_data_uri"] = _photo_data_uri(c["slug"])

            html = tpl.render(c=render_c)
            page.set_content(html, wait_until="networkidle")
            page.screenshot(
                path=str(out_path),
                full_page=False,
                omit_background=False,
                type="png",
            )
            rendered += 1

        browser.close()

    return rendered
```

- [ ] **Step 3: Wire `_render_og_cards()` into `generate_public_site()`**

Find the `_render_page(env, "pretrunas.html.j2", ...)` call (around line 2276 at time of writing — grep for `pretrunas.html.j2` to locate current line).

Directly AFTER that render (but before the subsequent page renders), add:

```python
    # Render per-contradiction OG preview PNGs (1200×630, Playwright).
    og_cards_dir = atmina_dir / "assets" / "og"
    og_rendered = _render_og_cards(contradictions, env, og_cards_dir)
    print(f"  assets/og/: rendered {og_rendered}/{len(contradictions)} pretruna preview PNGs")
```

- [ ] **Step 4: Smoke-test**

Run: `.venv/Scripts/python.exe -c "from src.generate import generate_public_site; generate_public_site()"`
Expected:
- Runs without error
- Prints `assets/og/: rendered <N>/<N> pretruna preview PNGs` where N = current contradiction count
- `output/atmina/assets/og/pretruna-<id>.png` files exist

Run: `ls output/atmina/assets/og/ | head -5`
Expected: `pretruna-<id>.png` entries.

Run: `.venv/Scripts/python.exe -c "from pathlib import Path; [print(p.name, p.stat().st_size) for p in sorted(Path('output/atmina/assets/og').glob('*.png'))]"`
Expected: all PNGs are between 80KB and 400KB (typical OG card size at 2x scale).

- [ ] **Step 5: Visually verify a sample PNG**

Open one of the generated PNGs (e.g. `output/atmina/assets/og/pretruna-<first-id>.png`) in an image viewer. Confirm:
- 2400×1260 pixel dimensions (2x scale of 1200×630)
- Severity rail at top
- Photo or initials circle
- Name clear, role readable
- Both stances visible, not clipped beyond ~4 lines
- Brand footer

If the layout is wrong, iterate on `og-card.html.j2` (Task 1) and re-run `generate_public_site()`. The existing PNG will be overwritten because the mtime incremental check only skips when the PNG is NEWER than the contradiction.

- [ ] **Step 6: Commit**

```bash
git add src/generate.py
git commit -m "feat(generate): render 1200x630 OG preview PNGs per contradiction via playwright"
```

---

## Task 3: Detail-page template (`templates/pretruna-detail.html.j2`)

**Files:**
- Create: `templates/pretruna-detail.html.j2`

Extends `base.html.j2`. Contains ONE prv2-card (full version, identical markup to `pretrunas.html.j2`), a "back to all" link, and (optional) a "citas {{ politician }} pretrunas" compact grid at the bottom for engagement.

- [ ] **Step 1: Create the template**

```jinja
{% extends "base.html.j2" %}
{% set active_page = "pretrunas" %}
{% set assets_prefix = "../" %}

{% block title %}{{ c.politician_name }} · {{ c.severity_lv }}{% if c.topic %} — {{ c.topic }}{% endif %}{% endblock %}
{% block description %}{% if c.summary %}{{ c.summary|truncate(160) }}{% else %}{{ c.politician_name }} — {{ c.severity_lv }}{% if c.topic %} par {{ c.topic }}{% endif %}.{% endif %}{% endblock %}

{% block og_title %}{{ c.politician_name }}: {{ c.topic or "pretruna" }}{% endblock %}
{% block og_description %}{% if c.summary %}{{ c.summary|truncate(200) }}{% else %}{{ c.severity_lv }} · {{ c.old_date }} → {{ c.new_date }}{% endif %}{% endblock %}
{% block og_image %}{{ BASE_URL }}/assets/og/pretruna-{{ c.id }}.png{% endblock %}

{% block content %}
<section class="pagehead-section">
  <div class="prv2-detail-back">
    <a href="../pretrunas.html">← Visas pretrunas</a>
  </div>

  <div class="prv2-detail-wrap">
    {%- set share_text = c.politician_name ~ " — " ~ c.severity_lv ~ (" par " ~ c.topic if c.topic else "") -%}
    {%- set share_url = BASE_URL ~ "/pretrunas/" ~ c.id ~ ".html" -%}

    <article class="prv2-card sev-{{ c.severity }}" id="pretruna-{{ c.id }}"
             data-severity="{{ c.severity }}" data-party="{{ c.party }}"
             data-person="{{ c.politician_name }}">

      <div class="prv2-partybar" style="background: {{ c.party_color }}"></div>

      <header class="prv2-head">
        <div class="prv2-persona">
          {%- if c.has_photo %}
          <img class="prv2-avatar prv2-avatar-photo" src="{{ assets_prefix }}assets/photos/{{ c.slug }}.jpg" alt="{{ c.politician_name }}" style="--pc: {{ c.party_color }}">
          {%- else %}
          <span class="prv2-avatar" style="--pc: {{ c.party_color }}">{{ c.initials }}</span>
          {%- endif %}
          <div class="prv2-persona-text">
            <a class="prv2-name" href="{{ assets_prefix }}politiki/{{ c.slug }}.html">{{ c.politician_name }}</a>
            <div class="prv2-role">
              {%- if c.role %}{{ c.role }} · {% endif -%}
              {{ c.party_short -}}
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
            <time datetime="{{ c.old_date }}">{{ c.old_date }}</time>
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
            <time datetime="{{ c.new_date }}">{{ c.new_date }}</time>
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
          <span class="prv2-foot-id">ID {{ '%03d' % c.id }}</span>
          · Konstatēts {{ c.detected_at[:10] }}
          {% if c.salience %} · Nozīmīgums {{ '%.2f' % c.salience }}{% endif %}
        </div>
        <a class="prv2-share-x"
           href="https://x.com/intent/tweet?text={{ share_text|urlencode }}&url={{ share_url|urlencode }}"
           target="_blank" rel="noopener"
           title="Dalīties uz X">𝕏&nbsp;Dalīties</a>
      </footer>
    </article>

    {% if related %}
    <section class="prv2-detail-related">
      <h2>Citas {{ c.politician_name }} pretrunu</h2>
      <div class="prv2-related-grid">
        {% for r in related %}
        <a class="prv2-related-card sev-{{ r.severity }}" href="{{ r.id }}.html">
          <div class="prv2-related-glyph">{{ r.severity_glyph }}</div>
          <div class="prv2-related-body">
            <div class="prv2-related-sev">{{ r.severity_lv }}</div>
            <div class="prv2-related-topic">{{ r.topic or '—' }}</div>
            <div class="prv2-related-summary">{{ (r.summary or r.old_stance or '')|truncate(120) }}</div>
          </div>
        </a>
        {% endfor %}
      </div>
    </section>
    {% endif %}
  </div>
</section>
{% endblock %}
```

Note the `canonical_url` mechanism: `base.html.j2` already handles `{% if canonical_url %}<link rel="canonical">{% endif %}`. We'll pass `canonical_url` through the render context in Task 4.

- [ ] **Step 2: Commit**

```bash
git add templates/pretruna-detail.html.j2
git commit -m "feat(templates): add pretruna detail page template"
```

---

## Task 4: Wire detail-page rendering into `generate_public_site()`

**Files:**
- Modify: `src/generate.py`

- [ ] **Step 1: Add the detail-page render loop**

Find the block where `_render_og_cards()` is called (added in Task 2). Directly AFTER it, add:

```python
    # Render per-contradiction detail pages.
    pretrunas_detail_dir = atmina_dir / "pretrunas"
    pretrunas_detail_dir.mkdir(exist_ok=True)
    # Build a politician→[contradictions] map for "related" recommendations
    by_politician: dict[int, list[dict]] = {}
    for _c in contradictions:
        by_politician.setdefault(_c["opponent_id"], []).append(_c)

    for c in contradictions:
        related = [r for r in by_politician[c["opponent_id"]] if r["id"] != c["id"]][:3]
        _render_page(
            env,
            "pretruna-detail.html.j2",
            pretrunas_detail_dir / f"{c['id']}.html",
            {
                "c": c,
                "related": related,
                "BASE_URL": BASE_URL,
                "canonical_url": f"{BASE_URL}/pretrunas/{c['id']}.html",
            },
        )
    print(f"  pretrunas/: {len(contradictions)} detail pages")
```

- [ ] **Step 2: Regenerate and verify**

Run: `.venv/Scripts/python.exe -c "from src.generate import generate_public_site; generate_public_site()"`
Expected:
- `pretrunas/: <N> detail pages` logged
- `output/atmina/pretrunas/<id>.html` files exist for every contradiction

Run: `ls output/atmina/pretrunas/ | head -5`
Expected: list of `<id>.html` files.

- [ ] **Step 3: Spot-check one generated detail page**

Run: `grep -E 'og:(title|description|image|url)|canonical' output/atmina/pretrunas/<pick-an-id>.html`
Expected: 5-6 matching lines. Every tag present. og:image points to `https://atmina.lv/assets/og/pretruna-<id>.png`.

- [ ] **Step 4: Commit**

```bash
git add src/generate.py
git commit -m "feat(generate): render per-pretruna detail pages with og metadata"
```

---

## Task 5: Update the 𝕏 share button to link to the detail page

**Files:**
- Modify: `templates/pretrunas.html.j2`

- [ ] **Step 1: Update the share URL**

In `templates/pretrunas.html.j2`, locate the `{%- set share_url %}` line. Change:

```jinja
{%- set share_url = BASE_URL ~ "/pretrunas.html#pretruna-" ~ c.id -%}
```

to:

```jinja
{%- set share_url = BASE_URL ~ "/pretrunas/" ~ c.id ~ ".html" -%}
```

Leave `share_text` unchanged.

- [ ] **Step 2: Regenerate and verify**

Run: `.venv/Scripts/python.exe -c "from src.generate import generate_public_site; generate_public_site()"`

Run: `grep -oE 'x\.com/intent/tweet\?[^"]*' output/atmina/pretrunas.html | head -2`
Expected: URLs now end with `...&url=https%3A//atmina.lv/pretrunas/<id>.html` (not the anchor form).

- [ ] **Step 3: Commit**

```bash
git add templates/pretrunas.html.j2
git commit -m "feat(pretrunas): point X share button to per-contradiction detail page"
```

---

## Task 6: Sitemap entries for detail pages

**Files:**
- Modify: `src/generate.py`

- [ ] **Step 1: Find the current sitemap generation**

Run: `grep -n "sitemap\.xml" src/generate.py`
Expected: locate the function (likely `_write_sitemap` or inline block near the end of `generate_public_site()`).

- [ ] **Step 2: Read the sitemap builder and add pretruna entries**

Read the function body. Add entries for each contradiction detail page. The pattern will look something like:

```python
# Add pretruna detail pages
for c in contradictions:
    urls.append({
        "loc": f"{BASE_URL}/pretrunas/{c['id']}.html",
        "lastmod": (c.get("detected_at") or "")[:10] or today_lv(),
        "priority": "0.7",
        "changefreq": "monthly",
    })
```

Adapt the exact keys (`loc`, `lastmod`, etc.) to match what the existing sitemap builder accepts — read the existing code first.

- [ ] **Step 3: Regenerate and verify**

Run: `.venv/Scripts/python.exe -c "from src.generate import generate_public_site; generate_public_site()"`

Run: `grep -c '/pretrunas/[0-9]*\.html' output/atmina/sitemap.xml`
Expected: matches the contradiction count.

- [ ] **Step 4: Commit**

```bash
git add src/generate.py
git commit -m "feat(sitemap): include per-pretruna detail pages"
```

---

## Task 7: Styles for the detail page

**Files:**
- Modify: `assets/style.css`

Only small additions needed — the prv2-card itself reuses existing styles. Add: back-link pill, related-pretrunu grid.

- [ ] **Step 1: Append styles**

At the end of the `prv2-*` CSS block in `assets/style.css` (just before the `@media (prefers-reduced-motion)` block), add:

```css
.prv2-detail-back {
  margin-bottom: 16px;
}
.prv2-detail-back a {
  font-family: var(--prv2-mono);
  font-size: 11px;
  letter-spacing: 1.2px;
  text-transform: uppercase;
  color: var(--text-muted);
  text-decoration: none;
  border-bottom: 1px dotted currentColor;
}
.prv2-detail-back a:hover { color: var(--text); }

.prv2-detail-wrap {
  max-width: 900px;
  margin: 0 auto;
}

.prv2-detail-related {
  margin-top: 48px;
}
.prv2-detail-related h2 {
  font-family: var(--prv2-mono);
  font-size: 14px;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--text-muted);
  margin-bottom: 14px;
  font-weight: 500;
}
.prv2-related-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 12px;
}
.prv2-related-card {
  --prv2-sev: var(--yellow);
  display: grid;
  grid-template-columns: 36px 1fr;
  gap: 14px;
  padding: 14px 16px;
  background: var(--surface2);
  border: 1px solid var(--prv2-border-soft);
  border-left: 3px solid var(--prv2-sev);
  border-radius: 4px;
  color: var(--text);
  text-decoration: none;
  transition: border-color 0.18s ease;
}
.prv2-related-card:hover { border-color: var(--border); }
.prv2-related-card.sev-direct_contradiction { --prv2-sev: #dc2626; }
.prv2-related-card.sev-reversal             { --prv2-sev: #f97316; }
.prv2-related-card.sev-minor_shift          { --prv2-sev: #eab308; }

.prv2-related-glyph {
  font-family: var(--prv2-mono);
  font-size: 22px;
  color: var(--prv2-sev);
  display: flex;
  align-items: flex-start;
  justify-content: center;
}
.prv2-related-body { min-width: 0; }
.prv2-related-sev {
  font-family: var(--prv2-mono);
  font-size: 9px;
  letter-spacing: 1.1px;
  text-transform: uppercase;
  color: var(--prv2-sev);
  margin-bottom: 2px;
}
.prv2-related-topic {
  font-family: var(--prv2-serif);
  font-size: 14px;
  color: var(--text);
  margin-bottom: 4px;
}
.prv2-related-summary {
  font-family: var(--prv2-serif);
  font-size: 13px;
  line-height: 1.45;
  color: var(--text-muted);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

@media (max-width: 768px) {
  .prv2-detail-wrap { max-width: 100%; }
  .prv2-related-grid { grid-template-columns: 1fr; }
}
```

- [ ] **Step 2: Regenerate and verify**

Run: `.venv/Scripts/python.exe -c "from src.generate import generate_public_site; generate_public_site()"`

Serve and browse:
```bash
.venv/Scripts/python.exe -m http.server 8765 --directory output/atmina &
# open http://localhost:8765/pretrunas/<id>.html
```

Confirm: back link visible at top, single big card centered, related-pretrunu grid below if politician has more than one contradiction.

- [ ] **Step 3: Commit**

```bash
git add assets/style.css
git commit -m "feat(css): styles for pretruna detail page (back link + related grid)"
```

---

## Task 8: Tests

**Files:**
- Modify: `tests/test_generate.py`

- [ ] **Step 1: Add test for OG card template rendering**

Append to `tests/test_generate.py`:

```python
class TestOgCardTemplate:
    def test_renders_with_minimal_data(self, tmp_path):
        from jinja2 import Environment, FileSystemLoader
        env = Environment(loader=FileSystemLoader("templates"), autoescape=True)
        c = {
            "id": 1,
            "politician_name": "Test Persona",
            "role": "Deputāts",
            "party_short": "JV",
            "party_color": "#ff0000",
            "severity": "reversal",
            "severity_lv": "Apvērsums",
            "severity_glyph": "↺",
            "topic": "Test tēma",
            "initials": "TP",
            "old_date": "2026-01-01",
            "new_date": "2026-02-01",
            "old_stance": "Iepriekš stance",
            "new_stance": "Pašlaik stance",
            "old_quote": None,
            "new_quote": None,
            "summary": "Test summary",
            "photo_data_uri": None,
        }
        html = env.get_template("og-card.html.j2").render(c=c)
        assert "Test Persona" in html
        assert "↺" in html
        assert "Apvērsums" in html
        assert "TP" in html  # initials fallback
        assert "Iepriekš stance" in html
        assert "Pašlaik stance" in html

    def test_photo_data_uri_rendered_when_present(self):
        from jinja2 import Environment, FileSystemLoader
        env = Environment(loader=FileSystemLoader("templates"), autoescape=True)
        c = {
            "id": 2,
            "politician_name": "P",
            "role": None,
            "party_short": "X",
            "party_color": "#00ff00",
            "severity": "minor_shift",
            "severity_lv": "Niansē",
            "severity_glyph": "≈",
            "topic": None,
            "initials": "P",
            "old_date": "2026-01-01",
            "new_date": "2026-01-02",
            "old_stance": "a",
            "new_stance": "b",
            "old_quote": None,
            "new_quote": None,
            "summary": None,
            "photo_data_uri": "data:image/jpeg;base64,AAA=",
        }
        html = env.get_template("og-card.html.j2").render(c=c)
        assert 'data:image/jpeg;base64,AAA=' in html
        assert 'class="avatar-fallback"' not in html
```

- [ ] **Step 2: Add test for detail-page template rendering**

```python
class TestPretrunaDetailTemplate:
    def test_renders_with_og_meta(self):
        from jinja2 import Environment, FileSystemLoader
        env = Environment(loader=FileSystemLoader("templates"), autoescape=True)
        c = {
            "id": 17,
            "politician_name": "Evika Siliņa",
            "slug": "evika-silina",
            "role": "Ministru prezidente",
            "party": "Jaunā Vienotība",
            "party_short": "JV",
            "party_color": "#0066cc",
            "severity": "reversal",
            "severity_lv": "Apvērsums",
            "severity_glyph": "↺",
            "topic": "Koalīcija un partijas",
            "initials": "ES",
            "has_photo": True,
            "old_date": "2025-10-31",
            "new_date": "2026-03-30",
            "old_stance": "iepriekš teksts",
            "new_stance": "pašlaik teksts",
            "old_source": "https://lsm.lv/raksts",
            "new_source": "https://delfi.lv/raksts",
            "old_source_domain": "lsm.lv",
            "new_source_domain": "delfi.lv",
            "old_quote": "Viņi ir pieviluši",
            "new_quote": None,
            "summary": "Test summary",
            "detected_at": "2026-04-05 12:00:00",
            "salience": 0.85,
            "delta_days": 150,
            "vote_summary": None,
            "vote_id": None,
        }
        html = env.get_template("pretruna-detail.html.j2").render(
            c=c, related=[], BASE_URL="https://atmina.lv",
            canonical_url="https://atmina.lv/pretrunas/17.html",
        )
        assert 'property="og:image" content="https://atmina.lv/assets/og/pretruna-17.png"' in html
        assert 'rel="canonical" href="https://atmina.lv/pretrunas/17.html"' in html
        assert "Evika Siliņa" in html
        assert "Visas pretrunas" in html  # back link
        assert "pretrunas/17.html" in html  # share URL
```

- [ ] **Step 3: Add test for `_photo_data_uri` helper**

```python
class TestPhotoDataUri:
    def test_missing_returns_none(self):
        from src.generate import _photo_data_uri
        assert _photo_data_uri("this-slug-does-not-exist") is None

    def test_existing_returns_data_uri(self):
        """Uses any real photo from assets/photos/."""
        import os
        from src.generate import _photo_data_uri, ASSETS_DIR
        photos = list((ASSETS_DIR / "photos").glob("*.jpg"))
        if not photos:
            pytest.skip("No photos available")
        slug = photos[0].stem
        uri = _photo_data_uri(slug)
        assert uri is not None
        assert uri.startswith("data:image/jpeg;base64,")
        assert len(uri) > 100
```

Note: remember to add `from src.generate import _photo_data_uri` to the top-of-file import block (or the test will fail with ImportError before running).

- [ ] **Step 4: Run all tests**

Run: `.venv/Scripts/python.exe -m pytest tests/test_generate.py -v`
Expected: all tests pass, including the three new classes.

- [ ] **Step 5: Commit**

```bash
git add tests/test_generate.py
git commit -m "test(generate): og card + detail page rendering + photo data uri"
```

---

## Task 9: End-to-end manual verification

**Files:** none

- [ ] **Step 1: Regenerate clean**

Run:
```bash
rm -rf output/atmina/pretrunas output/atmina/assets/og
.venv/Scripts/python.exe -c "from src.generate import generate_public_site; generate_public_site()"
```

Expected:
- Fresh `pretrunas/<id>.html` files
- Fresh `assets/og/pretruna-<id>.png` files

- [ ] **Step 2: Serve and browse**

```bash
.venv/Scripts/python.exe -m http.server 8765 --directory output/atmina
# visit http://localhost:8765/pretrunas/<any-id>.html in a browser
```

Check:
- Page renders with the big prv2-card centered
- "← Visas pretrunas" link at top goes back to the main page
- The 𝕏 share button has `href` ending in `/pretrunas/<id>.html`
- Related contradictions appear if the politician has more than one
- View-source: `<meta property="og:image" content="https://atmina.lv/assets/og/pretruna-<id>.png">` is present

- [ ] **Step 3: Preview the OG image**

Open `output/atmina/assets/og/pretruna-<id>.png` directly in an image viewer.
Check: high-density render (2400×1260), severity color accent, photo or initials, name, role, topic, both stances, brand footer. No text clipped.

- [ ] **Step 4: Manual meta-tag inspection**

Run: `curl -s http://localhost:8765/pretrunas/<id>.html | grep -E '<meta|<link rel="canonical"'`

Confirm presence of:
- `<meta property="og:title">`
- `<meta property="og:description">`
- `<meta property="og:image">` (with absolute URL)
- `<meta property="og:url">` (canonical)
- `<meta name="twitter:card" content="summary_large_image">` (inherited from base)
- `<link rel="canonical">`

- [ ] **Step 5: (After deployment) validator testing**

This step requires the branch to be merged and deployed. Document in the PR:

Post-deploy verification steps (not done as part of this plan's implementation):

1. Twitter/X Card Validator: https://cards-dev.twitter.com/validator
   - Enter `https://atmina.lv/pretrunas/<id>.html`
   - Expect: "Card found" with large image preview
   - Note: X caches aggressively — may need several minutes after first fetch

2. Facebook Sharing Debugger: https://developers.facebook.com/tools/debug/
   - Same URL; verify og:image renders

3. LinkedIn Post Inspector: https://www.linkedin.com/post-inspector/

4. Telegram manual test: paste the URL into any Telegram chat; should show rich preview with the OG image

5. WhatsApp: paste into a chat; should show preview with the OG image

If any platform doesn't pick up the image:
- Check HTTP status of the PNG URL is 200
- Check Content-Type is `image/png`
- Check og:image absolute URL matches what the crawler fetches
- X specifically requires og:image to be < 5MB and dimensions ≥ 300×157

---

## Task 10: Final cleanup + PR

**Files:** none (metadata only)

- [ ] **Step 1: Confirm the full test suite is green**

Run: `.venv/Scripts/python.exe -m pytest tests/ -q`
Expected: all tests pass, including the three new classes from Task 8.

- [ ] **Step 2: Confirm generate runs clean**

Run: `.venv/Scripts/python.exe -c "from src.generate import generate_public_site; generate_public_site()"`
Expected: runs without warnings, reports the new counts.

- [ ] **Step 3: Check linter / type checker if configured**

Run:
```bash
.venv/Scripts/python.exe -m ruff check src/generate.py tests/test_generate.py 2>&1 | tail -5
```

If ruff is configured, fix any new errors. If not configured, document that in the commit or skip.

Same for mypy:
```bash
.venv/Scripts/python.exe -m mypy src/generate.py 2>&1 | tail -5
```

- [ ] **Step 4: Summarize commits**

Run: `git log --oneline master..HEAD`
Expected: approximately 8 commits:
```
<sha> test(generate): og card + detail page rendering + photo data uri
<sha> feat(css): styles for pretruna detail page (back link + related grid)
<sha> feat(sitemap): include per-pretruna detail pages
<sha> feat(pretrunas): point X share button to per-contradiction detail page
<sha> feat(generate): render per-pretruna detail pages with og metadata
<sha> feat(templates): add pretruna detail page template
<sha> feat(generate): render 1200x630 OG preview PNGs per contradiction via playwright
<sha> feat(templates): add og-card template for per-contradiction social preview
<sha> chore: declare playwright as build-time dependency for og cards
```

- [ ] **Step 5: Open PR (ask user first)**

Do NOT open the PR automatically. Ask the user whether to open it, and if they want to tweak the description.

If asked to open:
```bash
gh pr create --title "Shareable pretrunu kartiņas: per-contradiction pages + 1200×630 social PNGs" --body "$(cat <<'EOF'
## Summary
- New dedicated page per contradiction at `/pretrunas/<id>.html` so social crawlers see per-pretruna OG metadata (the main page's `#fragment` was stripped by X/Telegram).
- 1200×630 preview PNG generated per contradiction via headless Chromium into `assets/og/pretruna-<id>.png`. Rendered from a new standalone Jinja template that inlines photos as base64, severity colors, name/role/topic/stances.
- 𝕏 share button now links to the detail page, so X's preview card renders the correct per-pretruna PNG.
- Existing anchor URL (`/pretrunas.html#pretruna-<id>`) still works for humans; only the share URL changed.

## Verification checklist
- [ ] All tests pass (`pytest tests/`)
- [ ] `generate_public_site()` runs clean
- [ ] `output/atmina/pretrunas/<id>.html` has per-contradiction og:title/og:description/og:image/canonical
- [ ] `output/atmina/assets/og/pretruna-<id>.png` renders at 2400×1260 (2× scale of 1200×630)
- [ ] Detail page loads in browser, back link works, related contradictions show for politicians with multiple

## Post-deploy checks
- [ ] Twitter/X Card Validator shows rich preview
- [ ] Telegram shows rich preview when URL pasted
- [ ] WhatsApp shows rich preview when URL pasted

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Edge cases and risk register

| # | Case | Mitigation |
|---|---|---|
| 1 | Playwright not installed in venv | Task 0 installs it before any other work |
| 2 | Chromium not installed | Task 0 runs `playwright install chromium` |
| 3 | Google Fonts fails to load at build time (offline build) | Template uses `wait_until="networkidle"` with default 30s timeout; font falls back to system mono if timeout. Option: pre-download JetBrains Mono TTF and embed via @font-face + base64. Low priority — dev env always online. |
| 4 | Politician has no photo | `c.photo_data_uri` is None → template renders `.avatar-fallback` with initials |
| 5 | Very long quote / stance exceeds 4 lines | CSS `-webkit-line-clamp: 4` clips gracefully |
| 6 | Very long name (e.g. double-barreled surname) | Georgia at 58px fits ~18 chars in 900px persona column; longer wraps to 2 lines (acceptable visually). If truly catastrophic, reduce to 52px. |
| 7 | Contradiction deleted from DB between builds | Orphan PNG + HTML remain in `output/` — not a correctness issue. Optional: add a sweep step that removes PNGs whose contradiction ID is no longer in `contradictions`. Skip for V1. |
| 8 | Slow build (100+ contradictions) | Incremental rendering skips unchanged cards (mtime check in `_render_og_cards`). At 200ms each, even 100 cards takes 20s once; subsequent builds only re-render changed. |
| 9 | X crawler refuses image (too large, wrong MIME) | 1200×630 at 2× = 2400×1260 ~150KB PNG. Well under X's 5MB limit. Content-Type is `image/png` — verify post-deploy via curl. |
| 10 | Unicode / diacritics in URL-encoded share text | Jinja `urlencode` filter handles correctly. Verified in previous branch work. |
| 11 | Canonical URL mismatch (http vs https, www vs non-www) | `BASE_URL = "https://atmina.lv"` is the single source of truth. Ensure deployed site redirects non-canonical variants via hosting config (outside scope of this plan). |
| 12 | New politician added mid-build without photo | Falls through to initials fallback. No error. |
| 13 | `summary` is empty/None for old contradictions | Template has fallback: `og:description` uses `{{ c.severity_lv }} · {{ c.old_date }} → {{ c.new_date }}` when summary missing. |
| 14 | Concurrent builds write to same OG dir | Non-concern — `generate_public_site()` is intended to run single-threaded |
| 15 | Build-time network fetch of Google Fonts affects CI | If moving to CI, bundle the font. For now, local dev environment assumed online. |

---

## Self-review checklist (the implementer should run this at the end)

Skim through the spec above and verify each section maps to a task:
- ✅ Per-pretruna HTML page with og meta tags → Tasks 3, 4
- ✅ 1200×630 PNG per pretruna → Tasks 1, 2
- ✅ X share button points to detail page → Task 5
- ✅ Sitemap includes detail pages → Task 6
- ✅ CSS for detail page styling → Task 7
- ✅ Tests → Task 8
- ✅ Manual verification steps → Task 9

No placeholders, no "TBD", no `implement later`. Every code block is concrete. Every command is exact.

## Notes for future extensions (NOT in scope of this plan)

- **Per-politician OG cards** on `/politiki/<slug>.html` — same mechanism, different template
- **Pre-Facebook crawl "refresh" endpoint** — `curl -X POST` to Facebook graph API with the URL to force cache invalidation after content changes (out of scope; rarely needed)
- **Per-contradiction static microdata / JSON-LD** — schema.org ClaimReview markup for Google fact-check card eligibility (significant extra work, separate plan)
- **Dark-mode vs light-mode OG variants** — skip; dark looks good everywhere and matches brand
- **Animated preview for X (MP4 card)** — X supports video cards, could show a mini swipe animation; overkill for V1
