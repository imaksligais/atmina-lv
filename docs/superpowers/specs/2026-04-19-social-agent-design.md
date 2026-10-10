# Social Agent — Design Spec

**Date:** 2026-04-19
**Author:** elvijss (brainstormed with Claude)
**Status:** Draft, pending user review

## Goal

Stand up a manually-triggered agent that drafts X/Twitter posts from atmina.lv data, sends the top candidates to the operator on Telegram for review, and publishes approved drafts to the `@atmina_lv` account. No automation, no public-site surfacing, no operator dashboard in MVP — this is a flow experiment.

## Motivation

atmina.lv is deployed. The project produces a lot of reportable material (pretrunas, Saeima vote anomalies, weekly activity rankings, politician-on-politician tensions, novel claims from document analyses). None of it is currently distributed. A dedicated X account exists but is empty. The operator wants to post but writing from scratch each time is too slow; he wants the system to surface the best candidates with text + visual, then edit/approve in Telegram before publishing.

## Scope

### In scope (MVP)
- CLI command `python -m src.social_agent brainstorm` that produces up to 3 draft posts.
- Draft persistence in a new `social_drafts` SQLite table.
- Draft delivery to Telegram (one message per draft, with image attachment).
- Approval via Telegram reply commands (`ok <id>`, `skip <id>`, `<id> <freetext revise instruction>`).
- Publishing via `twikit` to the `@atmina_lv` account using a separate cookie file.
- Three content pillars: **Pretrunas**, **Nedēļas stats**, **Analīžu highlights**.
- Three visual renderers: matplotlib chart, HTML→Playwright PNG quote card, nanobanana illustration.

### Out of scope (explicitly deferred)
- Automatic posting / cron trigger.
- Inline buttons or keyboard UX in Telegram (reply-based control is enough).
- Surfacing posted tweets on atmina.lv (x.html, homepage, etc.).
- Operator dashboard / admin UI for the draft queue. The user plans a separate agent-management system later.
- Multi-platform support (BlueSky, Mastodon, LinkedIn). X only.
- Engagement/analytics tracking beyond storing `tweet_id`.
- Pillar-specific voice variants. All drafts use jautājums-stils (question-led, atmina-neutral).

## Architecture

### New package: `src/social_agent/`

| File | Responsibility |
|---|---|
| `__init__.py` | Public exports: `brainstorm()`, `publish_draft()`, `handle_telegram_command()` |
| `candidates.py` | SQL queries that pull candidates per pillar + interest-score ranking |
| `drafters.py` | Pillar-specific text generators (one function per pillar, each ≤280 chars) |
| `visuals.py` | Three renderers: `chart()`, `quote_card()`, `illustration()` — all return a file path under `data/social/drafts/` |
| `publisher.py` | twikit client wrapper — posts tweet, returns `tweet_id`, handles errors |
| `telegram.py` | Sends drafts to the configured Telegram chat; parses reply commands |
| `cli.py` | Entry points: `brainstorm`, `approve <id>`, `skip <id>`, `revise <id> <instruction>`, `resend <id>` |

### New database table: `social_drafts`

```sql
CREATE TABLE social_drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pillar TEXT NOT NULL CHECK(pillar IN ('pretrunas', 'stats', 'highlights')),
    text TEXT NOT NULL,
    image_path TEXT,
    source_data_json TEXT NOT NULL,  -- opaque JSON: originating claim_ids, contradiction_id, period, etc.
    score REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK(status IN ('pending', 'approved', 'rejected', 'revising', 'posted', 'failed')),
    telegram_msg_id TEXT,
    telegram_chat_id TEXT,
    revision_count INTEGER NOT NULL DEFAULT 0,
    parent_draft_id INTEGER REFERENCES social_drafts(id),  -- for revisions
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    posted_at TIMESTAMP,
    tweet_id TEXT,
    error_message TEXT
);

CREATE INDEX idx_social_drafts_status ON social_drafts(status);
CREATE INDEX idx_social_drafts_pillar ON social_drafts(pillar);
```

### X authentication

- Separate cookie file: `data/x_cookies_atmina.json` (gitignored).
- Reuse `src/x_pool.py` session setup pattern but with a dedicated client instance bound to the atmina cookie.
- Credential surface via `src/credentials.py`: new entry `X_ATMINA_COOKIES_PATH`.

### Telegram integration

- Reuse the existing Telegram plugin (the bot that this session is running on). No new bot, no new webhook.
- Chat ID stored in `src/credentials.py`: `TELEGRAM_OPERATOR_CHAT_ID`.
- Drafts sent as photo + caption in a single message. The returned Telegram message ID is saved to `telegram_msg_id` so the approval reply can be matched back to the draft by `reply_to_message_id`.
- **Reply handling is session-bound in MVP.** The plugin delivers incoming replies into this Claude Code session as `<channel>` blocks. When a reply arrives, Claude (or the operator, from a terminal) invokes the appropriate CLI subcommand: `approve <id>`, `skip <id>`, or `revise <id> <instruction>`. No background daemon polls for replies.
- If the operator prefers to drive approvals entirely from the terminal (no Claude session open), the same CLI subcommands work standalone against the DB — the Telegram message is then just a visual preview.

## Workflow

```
 1. Operator runs: python -m src.social_agent brainstorm
      │
      ▼
 2. candidates.py queries DB:
      - Pretrunas: unposted contradictions (status != 'posted' parent) ordered by severity + recency
      - Stats: weekly aggregations if not yet posted this week
      - Highlights: recent analyses.strongest_attacks or tensions, unposted
      │
      ▼
 3. Top 3 by interest_score → drafters.py renders text → visuals.py renders image
      │
      ▼
 4. DB insert (status='pending') → telegram.py sends each as separate message
      │   Caption format: "Draft #42 · [pillar]\n\n[text]\n\n—\nApprove: `ok 42` · Skip: `skip 42` · Revise: `42 <instruction>`"
      ▼
 5. Operator replies in Telegram:
      - `ok 42`           → status='approved' → publisher.py posts to X → status='posted', tweet_id saved
      - `skip 42`         → status='rejected'
      - `42 pārraksti īsāk` → status='revising' → drafter regenerates with instruction → new draft row
                              (parent_draft_id=42, revision_count+=1) → sent to Telegram again
      │
      ▼
 6. Posted tweet_id logged; operator can check success in DB or via tweet link.
```

## Content Pillars

All drafts use **jautājums-stils** (question-led, factual, engagement-friendly, never accusatory).

### Pillar 1 — Pretrunas

**Trigger:** any unposted row in `contradictions` where severity ∈ {critical, major}.

**Template (≤280 chars):**
```
[Politiķis] par [tēmu]:

"[Citāts A]" — [datums A]
"[Citāts B]" — [datums B]

Kurš ir īstais viedoklis? 🧐

atmina.lv/[persona-slug]#[contradiction-id]
```

**Visual:** HTML→Playwright quote card. Two quote blocks stacked, politician's photo + name header, atmina.lv footer badge.

### Pillar 2 — Nedēļas stats

**Trigger:** if current ISO week has no draft yet with `pillar='stats'`.

**Template:**
```
Aktīvākie deputāti šonedēļ:
1. [vārds] — [N] pozīcijas
2. [vārds] — [N]
3. [vārds] — [N]

Kas klusē? Skaties pilno sarakstu:
atmina.lv/statistika
```

**Visual:** matplotlib bar chart, top 10 politicians by `positions_this_week` count, atmina.lv brand palette.

### Pillar 3 — Analīžu highlights

**Trigger:** recent `analyses.strongest_attacks` (last 7 days) or `tensions` rows, unposted.

**Template:**
```
[Atklājuma/uzbrukuma/spriedzes teikums — 1–2 rindas.]

[Konteksts: kāpēc tas svarīgi, 1 teikums.]

atmina.lv/[relevant-link]
```

**Visual:** default to nanobanana illustration (abstract conceptual image matching the frame — e.g. "ideoloģiju sadursme"); fall back to quote card if the highlight has a direct citation.

## Visual Style

Shared brand tokens (already established in atmina.lv):
- Background: `#0b0f19`
- Accent: `#ff3b7f`
- Text: `#ffffff` primary, `#a0a7b8` secondary
- Font: Inter (system fallback: sans-serif)
- Output: 1200×675 PNG (16:9, X optimal)

**matplotlib charts** — use shared rcParams helper (to be added to `src/social_agent/visuals.py`) applying the palette above. Savefig with `dpi=150`, `facecolor=#0b0f19`.

**HTML→Playwright quote cards** — reuse the existing Playwright setup from `src/graphics/`. A single HTML template per card type lives at `templates/social/quote_card.html.j2`.

**Nanobanana illustrations** — reuse `src/graphics/nanobanana.py`. New prompt helper composes: subject (abstract noun phrase), style reference ("editorial illustration, atmina.lv brand, dark background with magenta accent, no text"), NEGATIVE_CONSTRAINTS from existing graphics module (STRICT TEXT RULE already defined per memory).

Files land in `data/social/drafts/draft_<id>.png`. Not tracked in git (added to `.gitignore`).

## Interest Score

```
score = 0.3 * salience
      + 0.3 * severity_normalized
      + 0.2 * freshness
      + 0.2 * novelty
```

Where:
- `salience` ∈ [0,1] — from claim/contradiction `salience` field, or 0.5 default.
- `severity_normalized` ∈ [0,1] — `critical=1.0, major=0.7, minor=0.4, none=0.0`. For non-pretrunas pillars: `0.6` default.
- `freshness` ∈ [0,1] — `max(0, 1 - (age_hours / 168))` → 1.0 at zero age, 0.0 at 7 days.
- `novelty` ∈ [0,1] — `1 - jaccard(candidate_topics, recently_posted_topics_last_7d)`. No overlap = fully novel.

Top 3 candidates by score, with a hard per-pillar cap (no more than 2 of the same pillar in a single `brainstorm` run, to keep the 3-draft slate diverse).

## Error Handling

- **X posting failures** — caught in `publisher.py`, status='failed', `error_message` saved, notification sent back to Telegram.
- **Twikit rate limits / auth expiry** — surface a clear message telling the operator to refresh `data/x_cookies_atmina.json`.
- **Image render failures** — draft is still created with `image_path=NULL`; Telegram message sends as text only.
- **Telegram send failures** — draft stays `pending`; operator can manually retry via `python -m src.social_agent resend <id>`.

## Testing

Unit tests only (no integration to X in CI):
- `tests/test_social_candidates.py` — candidate selection, interest score math, per-pillar caps.
- `tests/test_social_drafters.py` — template rendering, character count ≤280 guard.
- `tests/test_social_visuals.py` — renderer signatures and file output (chart only; skip nanobanana and playwright in CI).
- `tests/test_social_publisher.py` — mocked twikit client, status transitions.

Manual flow test before declaring MVP complete: real `brainstorm` run → Telegram reply `ok <id>` → real tweet posted on a disposable test account, then re-run against `@atmina_lv` once the flow is trusted.

## Future Work (not MVP)

- Auto-posting tier for low-risk pillars (stats, highlights without direct quotes).
- Surface posted tweets on atmina.lv `x.html` or a dedicated archive page.
- Operator dashboard tab showing draft queue, posting metrics, engagement (merges with future agent-management system).
- Multi-platform fan-out (BlueSky, Mastodon, LinkedIn).
- A/B variant generation ("give me 3 different framings of this contradiction").
- Engagement feedback loop — read back replies, likes, retweets → feed `novelty` score and pillar selection over time.

## Open Questions

None at this stage — all resolved in the brainstorming thread on 2026-04-19.
