# Mobile Filter Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mobile users (≤900px) see content first; filters collapse behind a "Filtri (N)" toggle with active-filter chips. Desktop (>900px) layout is bit-identical to current.

**Architecture:** Zero DOM restructuring. New `mobile-filterbar` element added before the grid; new `data-mobile-filter-open` attribute on the grid toggles visibility of `aside` (+ `ticker-bar` on X) via CSS selectors scoped to `@media (max-width: 900px)`. All new CSS rules use new selectors only — no existing declarations are modified. JS hooks into existing `render()` / `apply()` central functions.

**Tech Stack:** Jinja2 templates (`templates/*.html.j2`), vanilla CSS (`assets/style.css`), vanilla JS (`assets/pzv1.js`, `assets/x-v1.js`). Static site generator: `src.generate.generate_public_site()`.

**Testing reality:** This project has no UI test framework (no Playwright, no Jest). Python pytest covers non-UI code. Verification is: (a) `python -m pytest tests/ -v` must stay green (no Python touched, but forced discipline), and (b) manual browser verification at multiple viewport widths after each task. Each task below specifies exact browser check criteria.

**Reference spec:** `docs/superpowers/specs/2026-04-19-mobile-filter-panel-design.md`

---

## Phase 1 — Pozīcijas tab

### Task 1: Add mobile filterbar markup + data attribute (Pozīcijas)

**Files:**
- Modify: `templates/pozicijas.html.j2:29-31` (add markup after `</header>`, add attribute to `.pzv1-grid`)

- [ ] **Step 1: Add mobile filter bar markup and data attribute**

Open `templates/pozicijas.html.j2`. After the closing `</header>` at line 29 and before `<div class="pzv1-grid">` at line 31, and also modifying line 31 to add the data attribute:

Find this exact block:
```jinja
    </div>
  </header>

  <div class="pzv1-grid">
```

Replace with:
```jinja
    </div>
  </header>

  <div class="pzv1-mobile-filterbar">
    <button class="pzv1-mobile-toggle" type="button" aria-expanded="false">
      Filtri <span class="pzv1-mobile-count">(0)</span>
    </button>
    <div class="pzv1-mobile-chips" hidden></div>
  </div>

  <div class="pzv1-grid" data-mobile-filter-open="false">
```

- [ ] **Step 2: Regenerate site**

Run:
```bash
python -c "from src.generate import generate_public_site; generate_public_site()"
```

Expected: runs without error; `output/atmina/pozicijas.html` is regenerated.

- [ ] **Step 3: Verify HTML output**

Run:
```bash
grep -c 'pzv1-mobile-filterbar' output/atmina/pozicijas.html
grep -c 'data-mobile-filter-open="false"' output/atmina/pozicijas.html
```

Expected: both output `1`.

- [ ] **Step 4: Manual browser check — desktop unchanged**

Start server: `python serve.py` (background OK).
Open `http://127.0.0.1:8080/pozicijas.html` at window width 1200px.
Expected: page looks *exactly* like before. No mobile filter bar visible (CSS not added yet, so element exists but is browser-default inline block — this is expected and temporary; will be hidden in Task 2).

- [ ] **Step 5: Commit**

```bash
git add templates/pozicijas.html.j2 output/atmina/pozicijas.html
git commit -m "feat(pozicijas): pievieno mobile filter bar markup + data atribūts

Jauns pzv1-mobile-filterbar elements pirms grid; data-mobile-filter-open='false'
uz grid. CSS/JS nāk nākamajos soļos — pagaidām tikai markup."
```

---

### Task 2: Add baseline CSS (Pozīcijas) — hide on desktop, show on mobile, hide aside when closed

**Files:**
- Modify: `assets/style.css` (append new rules after line 4067 — end of existing mobile responsive block)

- [ ] **Step 1: Add CSS rules**

Open `assets/style.css`. Navigate to line 4067 (end of the `@media (max-width: 900px)` block). After the closing `}` on line 4067, append:

```css

/* ---- Mobile filter panel (Pozīcijas + X) ---- */
.pzv1-mobile-filterbar,
.xv1-mobile-filterbar {
  display: none;
}

@media (max-width: 900px) {
  .pzv1-mobile-filterbar,
  .xv1-mobile-filterbar {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
    margin: 16px 0 12px;
  }
  .pzv1-mobile-chips,
  .xv1-mobile-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    align-items: center;
  }
  .pzv1-grid[data-mobile-filter-open="false"] .pzv1-aside { display: none; }
  .xv1-grid[data-mobile-filter-open="false"] .xv1-aside { display: none; }
  .xv1-grid[data-mobile-filter-open="false"] .xv1-ticker-bar { display: none; }
}
```

- [ ] **Step 2: Regenerate site**

```bash
python -c "from src.generate import generate_public_site; generate_public_site()"
```

- [ ] **Step 3: Manual browser check — desktop**

Reload `http://127.0.0.1:8080/pozicijas.html` at 1200px.
Expected: page looks *identical* to pre-Task-1 state. Left sidebar visible. No mobile toggle button visible anywhere.

- [ ] **Step 4: Manual browser check — mobile**

Chrome DevTools → responsive mode → iPhone SE (375×812).
Expected:
- Unstyled "Filtri (0)" button visible immediately below header metrics.
- Claims list starts immediately below the button. Left sidebar (aside) is NOT visible.
- No chip bar visible (chips container has `hidden` attribute).

- [ ] **Step 5: Commit**

```bash
git add assets/style.css output/atmina/
git commit -m "feat(css): mobile filter panel baseline CSS

Slēpj mobile bar desktop; uz <=900px slēpj aside kad
data-mobile-filter-open='false'. Vēl bez pogas stila."
```

---

### Task 3: JS toggle handler (Pozīcijas) — open/close panel

**Files:**
- Modify: `assets/pzv1.js` (add inside the main IIFE, before the `// --- Bootstrap ---` comment at line 456)

- [ ] **Step 1: Add toggle handler**

Open `assets/pzv1.js`. Find the Bootstrap section:

```javascript
  // --- Bootstrap ---
  // All event-listener blocks from later tasks (4.2–4.5) must be inserted
  // ABOVE this Bootstrap section, inside the same IIFE.
  render();
```

Before the `// --- Bootstrap ---` comment line, insert:

```javascript
  // --- Mobile filter toggle ---
  const mobileToggleEl = document.querySelector(".pzv1-mobile-toggle");
  const mobileGridEl = document.querySelector(".pzv1-grid");
  if (mobileToggleEl && mobileGridEl) {
    mobileToggleEl.addEventListener("click", () => {
      const isOpen = mobileGridEl.dataset.mobileFilterOpen === "true";
      mobileGridEl.dataset.mobileFilterOpen = String(!isOpen);
      mobileToggleEl.setAttribute("aria-expanded", String(!isOpen));
    });
  }

```

- [ ] **Step 2: Regenerate site**

```bash
python -c "from src.generate import generate_public_site; generate_public_site()"
```

- [ ] **Step 3: Manual browser check — mobile open/close**

Reload at 375×812. Click "Filtri (0)" button.
Expected: left sidebar contents (topic rail, party rail, period, confidence, persons) appears between the button and the claims list. Button still visible above.

Click button again.
Expected: sidebar contents collapse. Claims list moves back up.

Inspect the grid element in DevTools. Attribute `data-mobile-filter-open` should toggle between `"false"` and `"true"`. `aria-expanded` on button should match.

- [ ] **Step 4: Manual browser check — desktop still OK**

Resize to 1200px. Sidebar should appear as left column (no toggle visible).
Open DevTools console: no JS errors.

- [ ] **Step 5: Commit**

```bash
git add assets/pzv1.js output/atmina/
git commit -m "feat(pzv1): mobile toggle atver/aizver aside paneli"
```

---

### Task 4: JS chip rendering + hook into render()

**Files:**
- Modify: `assets/pzv1.js:57-64` (modify `render()` function to call new `renderMobileFilterState()`)
- Modify: `assets/pzv1.js` (add new `renderMobileFilterState()` function after `render()`)

- [ ] **Step 1: Add renderMobileFilterState() function**

Open `assets/pzv1.js`. After the `render()` function (which ends at line 64 with `}`), insert a new function:

```javascript

  // --- Mobile filter state (chips + count) ---
  const DEFAULT_VALUES = {
    topic: "visas",
    party: "Visas",
    period: "visi",
    confidence: "visas",
  };
  const AXIS_LABELS = {
    topic: "Tēma",
    party: "Partija",
    period: "Periods",
    confidence: "Ticamība",
    person: "Persona",
  };
  function renderMobileFilterState() {
    const chipsEl = document.querySelector(".pzv1-mobile-chips");
    const countEl = document.querySelector(".pzv1-mobile-count");
    if (!chipsEl || !countEl) return;

    const actives = [];
    // Single-select axes: topic, party, period, confidence
    document.querySelectorAll('.pzv1-rail-row[data-axis].is-active').forEach(btn => {
      const axis = btn.dataset.axis;
      const value = btn.dataset.value;
      if (axis === "person") return; // person handled below as multi-select
      if (DEFAULT_VALUES[axis] === value) return;
      const label = btn.querySelector(".pzv1-rail-label")?.textContent?.trim() || value;
      actives.push({ axis, value, label });
    });
    // Multi-select axis: person
    document.querySelectorAll('.pzv1-rail-person.is-active').forEach(btn => {
      const value = btn.dataset.value;
      const label = btn.querySelector(".pzv1-rail-label")?.textContent?.trim() || value;
      actives.push({ axis: "person", value, label });
    });

    countEl.textContent = `(${actives.length})`;

    // Rebuild chip bar
    chipsEl.innerHTML = "";
    for (const a of actives) {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "pzv1-chip";
      chip.dataset.axis = a.axis;
      chip.dataset.value = a.value;
      chip.setAttribute("aria-label", `Noņemt filtru: ${AXIS_LABELS[a.axis]}: ${a.label}`);
      chip.innerHTML = `<span class="pzv1-chip-label">${AXIS_LABELS[a.axis]}: ${a.label}</span><span class="pzv1-chip-x" aria-hidden="true">✕</span>`;
      chipsEl.appendChild(chip);
    }
    if (actives.length >= 2) {
      const clearBtn = document.createElement("button");
      clearBtn.type = "button";
      clearBtn.className = "pzv1-mobile-clearall";
      clearBtn.textContent = "Notīrīt visu";
      chipsEl.appendChild(clearBtn);
    }
    chipsEl.hidden = actives.length === 0;
  }

```

- [ ] **Step 2: Hook into render()**

Find the existing `render()` function (line 57–64):

```javascript
  function render() {
    const filtered = filterAndSort();
    renderRows(filtered);
    renderPagination(filtered.length);
    renderShownCount(filtered.length);
    renderActiveClear();
    updateFacetedCounts();
  }
```

Replace the last line (`}`) — add one new call before it:

```javascript
  function render() {
    const filtered = filterAndSort();
    renderRows(filtered);
    renderPagination(filtered.length);
    renderShownCount(filtered.length);
    renderActiveClear();
    updateFacetedCounts();
    renderMobileFilterState();
  }
```

- [ ] **Step 3: Regenerate site**

```bash
python -c "from src.generate import generate_public_site; generate_public_site()"
```

- [ ] **Step 4: Manual browser check — chip appears on filter**

Reload at 375×812. Open panel (click Filtri). Click on a topic (e.g., "Drošība").
Expected:
- Button count changes to `Filtri (1)`.
- A chip appears next to the button: "Tēma: Drošība ✕".
- Claims list filters to only Drošība.

Click on a party (e.g., "Jaunā Vienotība") within panel.
Expected:
- Button count changes to `Filtri (2)`.
- Second chip appears: "Partija: Jaunā Vienotība ✕".
- "Notīrīt visu" text button appears at end of chip row.

Close panel (click Filtri again). Chips + count stay visible above claims list.

- [ ] **Step 5: Manual browser check — person multi-select**

Open panel. Expand "Personas" section (may be `<details>` with summary). Click 2 politicians.
Expected: 2 chips appear, one per selected politician, labeled "Persona: <name> ✕".

- [ ] **Step 6: Commit**

```bash
git add assets/pzv1.js output/atmina/
git commit -m "feat(pzv1): mobile chip bar + count caur render() hook

renderMobileFilterState() skenē .is-active rail-rows (izņemot
default vērtības) un ģenerē chip-bar. Hook render() beigās =
katra filter maiņa atjauno chips + count."
```

---

### Task 5: JS chip click + clear-all handlers (Pozīcijas)

**Files:**
- Modify: `assets/pzv1.js` (add event delegation on `.pzv1-mobile-chips` inside the IIFE, before Bootstrap)

- [ ] **Step 1: Add chip click handler**

Open `assets/pzv1.js`. Find the block added in Task 3:

```javascript
  // --- Mobile filter toggle ---
  const mobileToggleEl = document.querySelector(".pzv1-mobile-toggle");
  const mobileGridEl = document.querySelector(".pzv1-grid");
  if (mobileToggleEl && mobileGridEl) {
    mobileToggleEl.addEventListener("click", () => {
      const isOpen = mobileGridEl.dataset.mobileFilterOpen === "true";
      mobileGridEl.dataset.mobileFilterOpen = String(!isOpen);
      mobileToggleEl.setAttribute("aria-expanded", String(!isOpen));
    });
  }
```

Immediately after it (still above Bootstrap), insert:

```javascript

  // --- Mobile chip clicks ---
  const mobileChipsEl = document.querySelector(".pzv1-mobile-chips");
  if (mobileChipsEl) {
    mobileChipsEl.addEventListener("click", (e) => {
      // "Notīrīt visu"
      const clearAll = e.target.closest(".pzv1-mobile-clearall");
      if (clearAll) {
        const mainClear = document.getElementById("pzv1-clear");
        if (mainClear) mainClear.click();
        return;
      }
      // Individual chip: simulate click on the corresponding rail row
      // to remove this one filter via existing code paths.
      const chip = e.target.closest(".pzv1-chip");
      if (!chip) return;
      const axis = chip.dataset.axis;
      const value = chip.dataset.value;
      if (axis === "person") {
        // Multi-select: clicking the active row toggles it off.
        const btn = document.querySelector(
          `.pzv1-rail-person[data-value="${CSS.escape(value)}"]`
        );
        if (btn) btn.click();
      } else {
        // Single-select: click the active row to toggle off → goes to default.
        const active = document.querySelector(
          `.pzv1-rail-row[data-axis="${axis}"].is-active`
        );
        if (active) active.click();
      }
    });
  }

```

Note: this handler uses the *existing* `#pzv1-clear` button (defined at line 262-284 of `pzv1.js`) for "Notīrīt visu" — reusing its full reset logic rather than duplicating it. Verify the element exists: grep `id="pzv1-clear"` in `templates/pozicijas.html.j2`.

- [ ] **Step 2: Verify #pzv1-clear exists**

Run:
```bash
grep -n 'id="pzv1-clear"' templates/pozicijas.html.j2
```

Expected: one line showing the element (usually a button like "Notīrīt filtrus" in the filter summary area).

**If no match**: the clear handler cannot reuse existing logic. Fallback: inline the reset logic by iterating `DEFAULT_VALUES` and calling `.click()` on each default rail row. This is a documented alternative — proceed with fallback if grep returns nothing.

- [ ] **Step 3: Regenerate site**

```bash
python -c "from src.generate import generate_public_site; generate_public_site()"
```

- [ ] **Step 4: Manual browser check — chip ✕**

Reload at 375×812. Activate a topic filter → chip appears.
Click the chip's ✕ area.
Expected:
- Chip disappears.
- Count returns to `Filtri (0)` (or decrements if multiple).
- Claims list updates to un-filtered state.
- Panel does NOT open (chip click does not propagate to toggle).

- [ ] **Step 5: Manual browser check — Notīrīt visu**

Activate 2 filters → chips appear + "Notīrīt visu" text button.
Click "Notīrīt visu".
Expected:
- All chips disappear.
- Count returns to `Filtri (0)`.
- Chip bar disappears entirely (`hidden` attribute re-applied).
- Claims list shows all claims.

- [ ] **Step 6: Commit**

```bash
git add assets/pzv1.js output/atmina/
git commit -m "feat(pzv1): chip X klikšķis + Notīrīt visu handler

Izmanto esošo rail-row click ceļu filter reset'am —
viens stāvokļa avots, no duplicated logic."
```

---

### Task 6: Style chips and toggle button (Pozīcijas visual polish)

**Files:**
- Modify: `assets/style.css` (inside the `@media (max-width: 900px)` block added in Task 2)

- [ ] **Step 1: Add chip + toggle styles**

Open `assets/style.css`. Find the block added in Task 2 (after existing responsive block). Inside the `@media (max-width: 900px)` block, add these specific visual rules — append before the closing `}`:

```css
  .pzv1-mobile-toggle,
  .xv1-mobile-toggle {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 14px;
    font: inherit;
    font-weight: 600;
    font-size: 14px;
    color: var(--xv1-text);
    background: var(--xv1-bg-alt, #fff);
    border: 1px solid var(--xv1-border, #d8d8d8);
    border-radius: 6px;
    cursor: pointer;
  }
  .pzv1-mobile-toggle:hover,
  .xv1-mobile-toggle:hover {
    background: var(--xv1-bg-hover, #f4f4f4);
  }
  .pzv1-mobile-count,
  .xv1-mobile-count {
    color: var(--xv1-text-dim, #777);
    font-weight: 500;
  }
  .pzv1-chip,
  .xv1-chip {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 4px 8px 4px 10px;
    font-size: 12px;
    color: var(--xv1-text);
    background: var(--xv1-bg-soft, #f4f4f4);
    border: 1px solid var(--xv1-border-soft, #e4e4e4);
    border-radius: 999px;
    cursor: pointer;
  }
  .pzv1-chip:hover,
  .xv1-chip:hover {
    background: var(--xv1-bg-hover, #ebebeb);
  }
  .pzv1-chip-x,
  .xv1-chip-x {
    font-size: 10px;
    color: var(--xv1-text-dim, #777);
    margin-left: 2px;
  }
  .pzv1-mobile-clearall,
  .xv1-mobile-clearall {
    background: none;
    border: none;
    padding: 4px 6px;
    font-size: 12px;
    color: var(--xv1-text-dim, #777);
    text-decoration: underline;
    cursor: pointer;
  }
  .pzv1-mobile-clearall:hover,
  .xv1-mobile-clearall:hover {
    color: var(--xv1-text);
  }
```

Note: CSS uses existing CSS variables from the `xv1-*` design system (shared across both pages). Fallback colors provided via `var(--name, fallback)` syntax for robustness.

- [ ] **Step 2: Regenerate site**

```bash
python -c "from src.generate import generate_public_site; generate_public_site()"
```

- [ ] **Step 3: Manual browser check — visual polish**

Reload at 375×812. Activate 2 filters.
Expected:
- "Filtri (2)" button has rounded border, clear padding, distinct from chips.
- Chips are pill-shaped (fully rounded), with a subtle background and ✕ slightly smaller/dimmer.
- "Notīrīt visu" is an underlined text link (no border/background).
- Hover states work (subtle background change).

- [ ] **Step 4: Commit**

```bash
git add assets/style.css output/atmina/
git commit -m "style(css): mobile toggle pogas + chip-bar vizuāli

Pill-style chipi, piedžis poga ar 600-weight Filtri label,
Notīrīt visu kā underlined text-link."
```

---

### Task 7: Phase 1 full verification

- [ ] **Step 1: Run pytest**

```bash
python -m pytest tests/ -v
```

Expected: all tests pass (no Python was touched, but discipline).

- [ ] **Step 2: Manual browser matrix**

Start `python serve.py`.

| Viewport | Expected |
|---|---|
| 1200px | Identical to pre-plan state. Left sidebar visible. No mobile bar. |
| 900px (exactly) | Grid collapses to 1 col (existing behavior). Mobile bar visible. Sidebar hidden by default. |
| 375px (iPhone SE) | Mobile bar visible. Sidebar hidden. Content starts immediately after filter bar. |
| 375px, panel open | Sidebar revealed between button and claims list. All rail groups interactive. |

- [ ] **Step 3: Keyboard navigation check**

At 375px, close panel first. Press Tab from URL bar until focus reaches "Filtri" button. Press Enter.
Expected: panel opens. Continue tabbing — focus moves through rail rows inside panel. Shift+Tab back to button. Enter closes panel.

- [ ] **Step 4: Confirm no Phase 1 rollback needed**

If any check above fails:
1. Identify which task's changes caused the regression.
2. `git log --oneline` to find the commit.
3. `git revert <hash>` for that single commit.
4. Re-do that task with fix.

If all checks pass, Phase 1 is complete. **STOP HERE and ask the user to review Phase 1 in a real browser before proceeding to Phase 2.**

---

## Phase 2 — X tab

**⚠️ Do not start Phase 2 until Phase 1 is merged/approved.**

The structure mirrors Phase 1. Only the differences vs Phase 1 are detailed; for identical steps, the plan references Phase 1's task.

### Task 8: Add mobile filterbar markup + data attribute (X tab)

**Files:**
- Modify: `templates/x.html.j2:31` (add markup before `<div class="xv1-grid">` and add attribute)

- [ ] **Step 1: Add mobile filter bar**

Open `templates/x.html.j2`. Find line 31:

```jinja
  <div class="xv1-grid">
```

Replace with:

```jinja
  <div class="xv1-mobile-filterbar">
    <button class="xv1-mobile-toggle" type="button" aria-expanded="false">
      Filtri <span class="xv1-mobile-count">(0)</span>
    </button>
    <div class="xv1-mobile-chips" hidden></div>
  </div>

  <div class="xv1-grid" data-mobile-filter-open="false">
```

- [ ] **Step 2: Regenerate + verify**

```bash
python -c "from src.generate import generate_public_site; generate_public_site()"
grep -c 'xv1-mobile-filterbar' output/atmina/x.html
grep -c 'data-mobile-filter-open="false"' output/atmina/x.html
```

Expected: both `1`.

- [ ] **Step 3: Browser check — desktop unchanged**

Reload `http://127.0.0.1:8080/x.html` at 1200px. Layout identical to before.

- [ ] **Step 4: Browser check — mobile**

375×812. "Filtri (0)" button visible immediately below header. Feed (X ticker items) starts immediately below button. Aside (Pieminētākie/Tēmas) NOT visible. Ticker-bar (Visi/Ieraksti/Pieminējumi tabs + dropdowns) NOT visible.

- [ ] **Step 5: Commit**

```bash
git add templates/x.html.j2 output/atmina/x.html
git commit -m "feat(x): pievieno mobile filter bar markup + data atribūts"
```

---

### Task 9: JS toggle handler (X tab)

**Files:**
- Modify: `assets/x-v1.js` (add inside the main IIFE, near the end but before any final `apply()` call)

- [ ] **Step 1: Locate the end of x-v1.js IIFE**

Open `assets/x-v1.js`. Find the end of the main `(function () { "use strict"; ... })();` IIFE. The file is 203 lines; the final `})();` is at the bottom. Find the last `apply()` or `updateLabel()` call inside the IIFE.

- [ ] **Step 2: Add toggle handler**

Near the end of the IIFE (just before `})();`), insert:

```javascript

  // --- Mobile filter toggle ---
  const xvMobileToggleEl = document.querySelector(".xv1-mobile-toggle");
  const xvMobileGridEl = document.querySelector(".xv1-grid");
  if (xvMobileToggleEl && xvMobileGridEl) {
    xvMobileToggleEl.addEventListener("click", () => {
      const isOpen = xvMobileGridEl.dataset.mobileFilterOpen === "true";
      xvMobileGridEl.dataset.mobileFilterOpen = String(!isOpen);
      xvMobileToggleEl.setAttribute("aria-expanded", String(!isOpen));
    });
  }
```

- [ ] **Step 3: Regenerate + browser check**

```bash
python -c "from src.generate import generate_public_site; generate_public_site()"
```

At 375px, click "Filtri (0)".
Expected: aside (Pieminētākie · Tēmas lists) AND ticker-bar (tabs + dropdowns) both appear between button and feed. Click again → both collapse.

- [ ] **Step 4: Commit**

```bash
git add assets/x-v1.js output/atmina/x.html
git commit -m "feat(xv1): mobile toggle atver/aizver aside + ticker-bar"
```

---

### Task 10: JS chip rendering + hook into apply() (X tab)

**Files:**
- Modify: `assets/x-v1.js` — locate `apply()` (around line 21), add hook call at end
- Modify: `assets/x-v1.js` — add `renderXvMobileFilterState()` function

- [ ] **Step 1: Add renderXvMobileFilterState()**

In `assets/x-v1.js`, after the `apply()` function (around line 33), insert:

```javascript

  // --- Mobile filter state (chips + count) ---
  const XV_TYPE_LABELS = { post: "Ieraksti", mention: "Pieminējumi" };
  function renderXvMobileFilterState() {
    const chipsEl = document.querySelector(".xv1-mobile-chips");
    const countEl = document.querySelector(".xv1-mobile-count");
    if (!chipsEl || !countEl) return;

    const actives = [];
    if (state.type) {
      actives.push({ kind: "type", value: state.type, label: `Tips: ${XV_TYPE_LABELS[state.type] || state.type}` });
    }
    for (const p of state.personas) {
      actives.push({ kind: "persona", value: p, label: p });
    }
    for (const pt of state.parties) {
      actives.push({ kind: "party", value: pt, label: pt });
    }
    if (state.topic) {
      actives.push({ kind: "topic", value: state.topic, label: `Tēma: ${state.topic}` });
    }

    countEl.textContent = `(${actives.length})`;

    chipsEl.innerHTML = "";
    for (const a of actives) {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "xv1-chip";
      chip.dataset.kind = a.kind;
      chip.dataset.value = a.value;
      chip.setAttribute("aria-label", `Noņemt filtru: ${a.label}`);
      chip.innerHTML = `<span class="xv1-chip-label">${a.label}</span><span class="xv1-chip-x" aria-hidden="true">✕</span>`;
      chipsEl.appendChild(chip);
    }
    if (actives.length >= 2) {
      const clearBtn = document.createElement("button");
      clearBtn.type = "button";
      clearBtn.className = "xv1-mobile-clearall";
      clearBtn.textContent = "Notīrīt visu";
      chipsEl.appendChild(clearBtn);
    }
    chipsEl.hidden = actives.length === 0;
  }
```

- [ ] **Step 2: Hook into apply()**

Find `apply()` (lines 21-33). Currently:

```javascript
  function apply() {
    for (const el of items) {
      const t = el.dataset.type;
      const p = el.dataset.persona;
      const party = el.dataset.party;
      const topic = el.dataset.topic;
      const matchType    = !state.type || t === state.type;
      const matchPersona = state.personas.size === 0 || state.personas.has(p);
      const matchParty   = state.parties.size === 0 || state.parties.has(party);
      const matchTopic   = !state.topic || topic === state.topic;
      el.style.display = (matchType && matchPersona && matchParty && matchTopic) ? "" : "none";
    }
  }
```

Add one line before the closing `}`:

```javascript
  function apply() {
    for (const el of items) {
      const t = el.dataset.type;
      const p = el.dataset.persona;
      const party = el.dataset.party;
      const topic = el.dataset.topic;
      const matchType    = !state.type || t === state.type;
      const matchPersona = state.personas.size === 0 || state.personas.has(p);
      const matchParty   = state.parties.size === 0 || state.parties.has(party);
      const matchTopic   = !state.topic || topic === state.topic;
      el.style.display = (matchType && matchPersona && matchParty && matchTopic) ? "" : "none";
    }
    renderXvMobileFilterState();
  }
```

- [ ] **Step 3: Initial render on load**

Locate the end of the IIFE. Before the final `})();`, find where apply() is already called on init (search for standalone `apply();` near the bottom). If it exists, `renderXvMobileFilterState()` is triggered automatically via the hook.

If no init `apply()` call exists, add one just before `})();`:

```javascript
  apply();
```

- [ ] **Step 4: Regenerate + browser check — chips**

```bash
python -c "from src.generate import generate_public_site; generate_public_site()"
```

At 375px, open panel, click "Tikai ieraksti" tab.
Expected: count `Filtri (1)`, chip `Tips: Ieraksti ✕`.

Open Personas dropdown, pick 1 politician.
Expected: count `Filtri (2)`, second chip with politician name.

Click on a topic in "Tēmas" list (aside).
Expected: count `Filtri (3)`, third chip `Tēma: <topic> ✕`, "Notīrīt visu" appears.

- [ ] **Step 5: Commit**

```bash
git add assets/x-v1.js output/atmina/x.html
git commit -m "feat(xv1): mobile chip bar + count hook apply() beigās"
```

---

### Task 11: JS chip click + clear-all handlers (X tab)

**Files:**
- Modify: `assets/x-v1.js` (add inside IIFE, near toggle handler)

- [ ] **Step 1: Add chip click handler**

In `assets/x-v1.js`, after the toggle handler block (added in Task 9), add:

```javascript

  // --- Mobile chip clicks ---
  const xvMobileChipsEl = document.querySelector(".xv1-mobile-chips");
  if (xvMobileChipsEl) {
    xvMobileChipsEl.addEventListener("click", (e) => {
      // "Notīrīt visu"
      const clearAll = e.target.closest(".xv1-mobile-clearall");
      if (clearAll) {
        // Reset all state
        state.type = "";
        state.personas.clear();
        state.parties.clear();
        state.topic = null;
        // Reset UI: type tabs
        document.querySelectorAll(".xv1-tab").forEach(b => b.classList.remove("active"));
        const defaultTab = document.querySelector('.xv1-tab[data-type=""]');
        if (defaultTab) defaultTab.classList.add("active");
        // Reset UI: multi-select dropdowns (remove .selected from all options)
        document.querySelectorAll("#xv1-persona-select .xv1-select-option.selected").forEach(o => o.classList.remove("selected"));
        document.querySelectorAll("#xv1-party-select .xv1-select-option.selected").forEach(o => o.classList.remove("selected"));
        // Reset UI: topic chip holder (hide any existing chip)
        const chipHolder = document.getElementById("xv1-topic-chip");
        if (chipHolder) chipHolder.innerHTML = "";
        // Update labels
        document.querySelectorAll("#xv1-persona-select .xv1-select-label").forEach(l => l.textContent = "Visas personas");
        document.querySelectorAll("#xv1-party-select .xv1-select-label").forEach(l => l.textContent = "Visas partijas");
        apply();
        return;
      }
      // Individual chip
      const chip = e.target.closest(".xv1-chip");
      if (!chip) return;
      const kind = chip.dataset.kind;
      const value = chip.dataset.value;
      if (kind === "type") {
        state.type = "";
        document.querySelectorAll(".xv1-tab").forEach(b => b.classList.remove("active"));
        const defaultTab = document.querySelector('.xv1-tab[data-type=""]');
        if (defaultTab) defaultTab.classList.add("active");
      } else if (kind === "persona") {
        state.personas.delete(value);
        const opt = document.querySelector(`#xv1-persona-select .xv1-select-option[data-value="${CSS.escape(value)}"]`);
        if (opt) opt.classList.remove("selected");
        // Update label
        const label = document.querySelector("#xv1-persona-select .xv1-select-label");
        if (label) label.textContent = state.personas.size === 0 ? "Visas personas" : `${state.personas.size} izvēlētas`;
      } else if (kind === "party") {
        state.parties.delete(value);
        const opt = document.querySelector(`#xv1-party-select .xv1-select-option[data-value="${CSS.escape(value)}"]`);
        if (opt) opt.classList.remove("selected");
        const label = document.querySelector("#xv1-party-select .xv1-select-label");
        if (label) label.textContent = state.parties.size === 0 ? "Visas partijas" : `${state.parties.size} izvēlētas`;
      } else if (kind === "topic") {
        state.topic = null;
        const chipHolder = document.getElementById("xv1-topic-chip");
        if (chipHolder) chipHolder.innerHTML = "";
      }
      apply();
    });
  }
```

Note: this is more verbose than Pozīcijas chip handler because X tab has 4 distinct filter kinds, each with its own UI sync (tabs, dropdown labels, topic chip holder). No existing "clear all" button in x.html.j2 to delegate to — logic is inlined here.

- [ ] **Step 2: Sanity-check the label format**

Run:
```bash
grep -n 'izvēlētas\|izvēlēta\|Visas personas\|Visas partijas' assets/x-v1.js
```

Expected: matches inside `updateLabel()` function (lines 79–82 of original). Verify the plan's label strings match the existing convention — if existing code uses a different pluralization (e.g., `1 izvēlēta` singular vs `2 izvēlētas` plural), mirror it.

**If existing code has different label logic**: extract `updateLabel()` into a named function so the chip handler can call it instead of duplicating label rebuilding. Adjust plan if needed.

- [ ] **Step 3: Regenerate + browser check**

```bash
python -c "from src.generate import generate_public_site; generate_public_site()"
```

Test each chip type removal:
1. Activate `Tips: Ieraksti` → click chip ✕ → chip disappears, "Visi" tab active again.
2. Pick 2 personas → 2 chips → click one chip ✕ → only that persona chip removed, dropdown label updates.
3. Pick a party → chip → remove → dropdown label back to "Visas partijas".
4. Click topic in aside → chip → remove → feed un-filtered.
5. With ≥2 filters → click "Notīrīt visu" → all chips gone, all UI reset.

- [ ] **Step 4: Commit**

```bash
git add assets/x-v1.js output/atmina/x.html
git commit -m "feat(xv1): chip X klikšķis + Notīrīt visu handler

Katrs chip kinds (type/persona/party/topic) sinhronizē
attiecīgo UI komponenti (tabs, dropdown labels, topic chip holder)."
```

---

### Task 12: Phase 2 full verification

- [ ] **Step 1: Run pytest**

```bash
python -m pytest tests/ -v
```

Expected: green.

- [ ] **Step 2: Manual browser matrix — X tab**

| Viewport | Expected |
|---|---|
| 1200px | Identical to pre-plan. Left aside visible. Ticker-bar above feed with tabs + dropdowns. No mobile bar. |
| 900px | Single column. Mobile bar visible. Aside + ticker-bar hidden by default. |
| 375px | Mobile bar below header. Feed starts right below. Aside + ticker-bar hidden. |
| 375px, panel open | Order from top: Pieminētākie → Tēmas → tabs → persona → partija → (divider) → feed below. |

- [ ] **Step 3: Cross-tab regression check**

Verify Pozīcijas tab still works correctly at 375px and 1200px. Phase 2 CSS additions were shared in `@media` block — confirm no accidental impact.

- [ ] **Step 4: Confirm plan complete**

If all checks pass: plan fully executed. No tag/release step — this is a static site, deploy happens via existing `scripts/deploy.sh` when user chooses.

---

## Scope discipline (YAGNI — not in this plan)

- Height/slide animation on panel open.
- Swipe-to-close gesture.
- Bottom sheet / modal variants.
- URL param sync for mobile-filter-open state.
- Blog / Partijas / Personas pages — separate structures, separate future work.
- Automated UI tests (Playwright/similar) — no existing infra; manual browser verification is the discipline here.

## Rollback strategy

Each task commits independently. If any task introduces a regression that can't be fixed in ≤2 attempts (per user's global rule #9):

```bash
git log --oneline  # find the offending commit
git revert <hash>  # creates reverse commit
```

Do NOT force-push to master (per user's memory). Revert commits are preferred over `git reset --hard`.
