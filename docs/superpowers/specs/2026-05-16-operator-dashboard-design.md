# atmina ops — Design Spec

> Visual + interaction design for the operator dashboard. Implementation plan: `docs/superpowers/plans/2026-05-16-operator-dashboard.md`.

## Goal

A single-page command center for the atmina operator that surfaces **all** operationally-relevant state in one screen, makes the most-common actions one-click away, preserves a chronological **memory** of what was done today/yesterday, and onboards a new team member without 100 pages of documentation.

## Users

- **Primary:** solo operator who lives in CLI but wants visual review + memory recall
- **Secondary:** future contributors who need a low-friction window into "what's happening, what's stuck, what's pending"
- **NOT served by this UI:** public visitors (they go to atmina.lv); analysts (they query DB directly); developers (they read code)

## Design principles

1. **Single screen by default.** No drill-down for the common case. Detail views are progressive disclosure, not hidden state.
2. **Memory is first-class.** Activity timeline is a permanent panel — operator should be able to glance and recall "what did I do today" in 2 seconds.
3. **Actionable, not decorative.** Surfaces show actionable signals (pending, degraded, stale) only — green / "all fine" produces minimal visual weight.
4. **Calm density.** Linear-style typographic hierarchy + tabular alignment. Lots of information, no shouting.
5. **Brand consistency.** Same visual family as atmina.lv (Georgia serif for prose, sarkans accent, restrained Baltic neoclassical tone) — but ops-specific (mono fonts for data, status badges, dark-mode-first).
6. **Keyboard-first.** Every action has a single-letter shortcut. Mouse is fallback.
7. **Safe to explore.** No DELETE buttons in M1/M2. All destructive actions have confirm modals + audit log entries. New team members can click freely.

## Information architecture

Three levels:

```
DASHBOARD (/)                  ← M1 + M2 default home, all panels visible
├── Activity archive (/activity?date=2026-05-15)
├── Brief detail (/brief/2026-05-16) ← modal in M2, full page in M3
├── Slot detail (/slots/1)            ← drill-down per slot, M3
├── Politician focus (/politiki/<pid>) ← reuses public profile, M3
└── Settings (/settings)               ← theme, refresh interval, M3
```

M1 ships only `/`. M2 adds modals + action endpoints. M3 adds detail pages.

## Wireframe — single page (default home)

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║  atmina ops                                                                    ║
║  ─────────                                                                     ║
║  pirmdiena · 2026. gada 16. maijs · 18:42 EEST           [⌕ search]  [◐] [?]  ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  ⓘ  image #85 awaiting approval  ·  brief #212 ready  ·  3/6 slots healthy   ║
║                                                                                ║
║  ┌─── ŠODIENAS PĀRSKATS ──────────────┬─── RUTĪNA ───────────────────────────┐║
║  │                                     │                                       │║
║  │  ┌─────────────────┐                │  ✅  ingest          627 d   13:42   │║
║  │  │                 │  #212          │  ✅  X timelines      92 tw  13:48   │║
║  │  │   hero image    │  8091 chars    │  ✅  mentions [search] 213    15:50   │║
║  │  │   (clickable)   │  ▸ cited #20383│  ✅  analysis        13 cl   16:30   │║
║  │  │                 │    -20395      │  ✅  brief #212       8091   17:08   │║
║  │  └─────────────────┘                │  ✅  image #85        $0.04  17:18   │║
║  │                                     │  ✅  render            44 p  17:25   │║
║  │  Rinkēvičs uztic Andrim             │  ✅  deploy         1.70 MB  17:35   │║
║  │  Kulbergam veidot valdību…          │                                       │║
║  │                                     │  ─── nākamais ─────                  │║
║  │  image #85 ✅ approved              │  • social draft (pēc 19:00)          │║
║  │                                     │  • Telegram brief (pēc 20:00)        │║
║  │  [📄 wiki]  [🔗 atmina.lv/blog/…]   │                                       │║
║  └─────────────────────────────────────┴───────────────────────────────────────┘║
║                                                                                ║
║  ┌─── X COOKIE POOL ─────── probed 53s ago [R] ─────────────────────────────┐ ║
║  │                                                                            │ ║
║  │   slot 1  ✅✅❌❌    slot 2  ✅✅✅✅    slot 3  ✅✅❌❌                  │ ║
║  │   slot 4  ✅✅❌❌    slot 5  ✅✅✅✅    slot 6  ✅✅✅✅                  │ ║
║  │            get_user  user_tweets  user_replies  search_tweet              │ ║
║  │                                                                            │ ║
║  │   search_tweet healthy: 3/6 ⚠  guardrail will fall back to timeline       │ ║
║  └────────────────────────────────────────────────────────────────────────────┘ ║
║                                                                                ║
║  ┌─── X_MENTIONS = search ─────────────┬─── EKSTRAKCIJAS RINDA ──────────────┐║
║  │                                     │                                       │║
║  │  last 7 mentions_fetch runs:        │   Šodien:    0 nesarķistīti          │║
║  │   213 ████████████████              │   Nedēļā:   47 gaida                  │║
║  │   129 ███████████                   │                                       │║
║  │     3 ▏                             │   Top pid (jāekstraktē):              │║
║  │     2 ▏                             │   #47 Šuvajevs    web · 8 docs        │║
║  │     1 ▏                             │   #12 Velps       tw  · 6 docs        │║
║  │     0                               │   #22 Kotello     mn  · 4 docs        │║
║  │     3 ▏                             │                                       │║
║  │                                     │   [→ triage]                          │║
║  │  guardrail tripped: 0 (24h)         │                                       │║
║  └─────────────────────────────────────┴───────────────────────────────────────┘║
║                                                                                ║
║  ┌─── AKTIVITĀTE · last 24h ─────────────────────────────────  [filter ▾]  ─┐ ║
║  │                                                                            │ ║
║  │  pirms 7 min   ✅  deploy     1.70 MB → atmina.lv (45 s, exit 0)          │ ║
║  │  pirms 17 min  ✅  render     44 blog posts · 175 politiķi                 │ ║
║  │  pirms 24 min  ✅  image      #85 approved by you · brief #212             │ ║
║  │  pirms 34 min  ✅  brief      #212 stored "Rinkēvičs uztic…" (8091 ch)    │ ║
║  │  pirms 1 h     ✅  analysis   4 politiķi · 13 jauni claims · 0 pretrunas   │ ║
║  │  pirms 1.5 h   ✅  mentions   search · 213 stored · 0 err                  │ ║
║  │  pirms 2 h     ✅  slot probe 5/6 OK (manual)                              │ ║
║  │  pirms 5 h     ✅  ingest     627 docs · 11 source feeds                   │ ║
║  │  pirms 18 h    ✅  deploy     2.3 MB → atmina.lv (yesterday's brief)       │ ║
║  │                                                                            │ ║
║  │  ───────── vakar (2026-05-15) ──────────                                  │ ║
║  │                                                                            │ ║
║  │  22:15  ✅  brief      #211 stored "Sprūda demisijas sekas…" (7240 ch)   │ ║
║  │  21:55  ✅  image      #84 approved                                        │ ║
║  │  ...                                                                       │ ║
║  │                                                                            │ ║
║  │                              [↓ load more]                                 │ ║
║  └────────────────────────────────────────────────────────────────────────────┘ ║
║                                                                                ║
║  ─── attēlu budžets $1.131 / $5.00 (23%) · build f99595a · v0.1.0 ───────────  ║
║  wiki ↗  ·  changelog ↗  ·  github ↗  ·  atmina.lv ↗                          ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

## Visual language

### Brand alignment

| Element | atmina.lv public | atmina ops | Why |
|---|---|---|---|
| Primary font (prose) | Georgia | Georgia (brief preview only) | brand continuity in editorial content |
| UI font | Georgia + system sans | system sans (`-apple-system, "Segoe UI"`) | UI density needs neutral sans |
| Data font | (n/a) | JetBrains Mono / Cascadia Code / Consolas | tabular alignment for numbers/IDs |
| Primary accent | sarkans `#9F1B1B` | sarkans `#9F1B1B` (sparingly — pending badges, links) | brand |
| Background | cream `#FAF7F0` | cream (light mode) / charcoal (dark mode default) | ops works at night |
| Text | ink `#1A1A1A` | ink / cream | high contrast |

### Status palette (WCAG AA in both themes)

| State | Light | Dark | Use |
|---|---|---|---|
| Success | bg `#DCFCE7` text `#14532D` | bg `#14532D` text `#86EFAC` | ✅ completed, healthy slot |
| Warning | bg `#FEF3C7` text `#78350F` | bg `#78350F` text `#FCD34D` | ⚠ degraded, pending action |
| Danger | bg `#FECACA` text `#7F1D1D` | bg `#7F1D1D` text `#FCA5A5` | ❌ failed, broken slot |
| Info | bg `#DBEAFE` text `#1E3A8A` | bg `#1E3A8A` text `#93C5FD` | ⓘ neutral signal |
| Neutral | bg `#F1F5F9` text `#475569` | bg `#1E293B` text `#94A3B8` | — empty state, secondary text |

### Typography scale

```
display    24/32  600  — page header "atmina ops"
heading    16/24  600  — panel titles "ŠODIENAS PĀRSKATS"
body       14/20  400  — default text
caption    12/16  400  — timestamps, secondary labels
mono       13/18  400  — IDs, numbers, log content
serif      15/22  400  — brief preview prose (Georgia)
```

### Spacing

8px grid. Panel padding 24px. Panel gap 16px. Inline gap 8px or 12px.

### Iconography

Lucide icons (CDN, no install) — minimal stroke-style. Status uses emoji-style filled glyphs (`✅`/`⚠`/`❌`/`ⓘ`) since they communicate fastest and don't require font loading.

### Density target

Default zoom (1x), 1366x768 minimum, single screen shows:
- Header + actionable banner
- 4 of 5 panels (activity scrolls below fold)
- Footer

13" laptop full-screen = everything visible without horizontal scroll.

## Interaction patterns

### Keyboard shortcuts (M2)

| Key | Action | Scope |
|---|---|---|
| `?` | open keyboard help modal | global |
| `R` | refresh slot probe | global |
| `A` | approve focused image | brief panel focused |
| `D` | open deploy confirm | global |
| `B` | open brief content modal | global |
| `Esc` | close modal | modal open |
| `/` | focus search | global (search added in M3) |
| `g a` | scroll to activity | global |
| `g s` | scroll to slots | global |

Shortcuts discovered via `?` modal AND inline hints (small `[R]` after panel title for the refresh action).

### HTMX partial updates

Action buttons POST to `/api/...` endpoints that return HTML fragments. HTMX swaps the affected panel only — no full page reload. UX feels app-like, but code is server-rendered.

Example: approve image button → POST `/api/image/85/approve` → returns updated brief panel HTML → HTMX swaps `#brief-panel` element.

### Auto-refresh

- **Activity panel:** polls `/api/activity?since=<last_id>` every 30 s; new rows appear with subtle highlight fade.
- **Other panels:** static unless user clicks refresh OR an action completes (HTMX broadcasts refresh signal).

Server-Sent Events (SSE) optional in M3 — polling is fine for solo operator.

### Toast notifications

Top-right slide-in toasts for action results:
- ✅ "Image #85 approved" (success, 3 s auto-dismiss)
- ❌ "Deploy failed — exit 1" (error, manual dismiss, expandable for log tail)

### Modals

Reserved for:
- Deploy confirmation (form with "Apstipriniet" button + last-deploy-diff preview)
- Brief content preview (full markdown rendered)
- Keyboard help
- Image preview (zoom)

ESC closes; click-outside closes; focus trap inside.

## State design

Every panel has 4 explicit states designed:

### Active (data present)
The wireframe above.

### Empty (no data, nothing pending)
Warm, encouraging copy — not "no data found". Examples:

```
EKSTRAKCIJAS RINDA
──────────────────
🌱  Nav nesarķistītu dokumentu šodien.
    Lielisks darbs! Nākamais ingest ~rītdienā plkst. 13:00.
```

```
ŠODIENAS PĀRSKATS
──────────────────
📰  Brief vēl nav uzrakstīts.
    Pirms briefa: 562 docs nesarķistīti — sāc ar @claim-extractor.
    [→ ekstrakcijas rinda]
```

### Loading (during async fetch)
Skeleton rows (shimmer animation), not spinner. Maintains layout stability.

### Error (fetch/action failed)
Neutral error chip + retry button + link to log:

```
X COOKIE POOL
─────────────
❌  Probe failed: ConnectionError (5s timeout)
    [retry]   [logs ↗]
```

## Onboarding affordances

For new team members opening the dashboard for the first time:

1. **Inline tooltips** on technical terms. Hover "slot" → "X scraping cookie pool — 6 atmina accounts for round-robin fetching"
2. **Per-panel help icon** (`?` in panel header) → opens tooltip linking to relevant `wiki/operations/*.md` page
3. **Empty states explain** what should appear (so a quiet day doesn't look broken)
4. **No destructive actions** without confirm — explorability without anxiety
5. **First-visit tour** (M3, optional): one-time overlay walks through each panel; dismissable, never auto-shown again
6. **Footer wiki link** is always present, prominent

Self-onboarding target: a new team member should understand the dashboard in 60 seconds without external docs.

## Memory & history

Three layers of memory:

1. **Active panels (today)** — Brief, Routine, Slots, A/B, Backlog — show current state.
2. **Activity timeline (last 24-48h)** — chronological log of every action. The "what did I do today" view.
3. **Archive views (M3)** — `/activity?date=YYYY-MM-DD` for any past day's full timeline; `/brief/YYYY-MM-DD` for any past brief.

Activity rows are emitted from `logs` table + `brief_images` + `context_notes` + `analyses` + git commits (M3) into a unified timeline. Each row has:
- Relative time ("pirms 7 min") + absolute on hover
- Status icon
- Action verb
- Free-text context (politicians touched, doc count, etc.)
- Source (where this came from — `logs` row id, brief id, etc.) for drill-down

## Branding & naming

- **Product name:** "atmina ops"
- **Visible header:** lowercase "atmina ops" + tagline "operatora panelis · localhost:8080"
- **Favicon:** atmina sarkanais "a" mark (reuse public site favicon)
- **Browser title:** "atmina ops · {pending_count} pending" — pending count in title is the "growl notification" pattern

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Backend | Flask 3.x | Server-rendered HTML; Jinja already used by `src/render/`; minimal deps |
| Templates | Jinja2 | Same as render pipeline |
| Frontend reactivity | HTMX 1.9 | Partial updates without React; ~14 KB |
| Local interactions | Alpine.js 3 | Tiny (~15 KB) for modals, dropdowns, keyboard shortcuts |
| Styling | Tailwind CSS 3 via CDN | Design system + dark mode; no build step |
| Charts | Inline SVG (server-rendered) | No JS lib; charts are simple bars |
| Icons | Lucide via CDN + emoji glyphs | Zero install |

Total page weight: <100 KB gzipped (Tailwind via CDN cached). No build pipeline, no npm.

## Out of scope (M1-M3)

- Authentication / TLS (localhost only)
- Multi-user state (no per-user prefs in DB; localStorage only for theme)
- WebSockets (SSE in M3 if needed)
- Mobile-first design (desktop primary; mobile "doesn't break" only)
- i18n (LV-only)
- Editing brief content from UI (operator uses text editor + Edit tool)
- Direct agent dispatch (Claude Code subagents aren't callable externally — buttons that "need an agent" copy a prompt to clipboard with link to Claude Code session)
- X Premium API integration ($200/mo deferred indefinitely)
- Real-time charts beyond simple bars
- Notification email/Slack/Telegram

## Open design questions

1. **Branding tone** — "atmina ops" feels right, but "atmina staff" / "atmina redakcija" (Latvian, newsroom metaphor) are alternatives. Operator preference?
2. **Default theme** — dark mode by default (operator is in terminal) or system-preference auto? Default: auto with manual override.
3. **Activity row click behavior** — expand inline with detail, or navigate to detail page? Default: expand inline (M2), drill-down page (M3).
4. **Pending actions banner** — top of page (sticky) or inline? Default: top of page, dismissible per session.

---

**Implementation:** see `docs/superpowers/plans/2026-05-16-operator-dashboard.md`.
