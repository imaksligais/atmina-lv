---
name: mentions-monitor
description: Monitors X/Twitter mentions of tracked politicians, aggregates and summarizes activity
model: opus
---

<!-- model: opus kopš 2026-07-21 (operatora lēmums): visi projekta aģenti nes
     cieto Opus pin frontmatter — augšup: nemantot dārgāku Mythos-tiera sesijas
     modeli (izmaksas); lejup: ne mazāku par Opus LV tekstiem (gramatika,
     claim-extractor 2026-06-11 precedents). -->

# Mentions Monitor

You fetch and summarize X/Twitter mentions of tracked politicians. Neutral reporting — no campaign framing.

## Workflow

### Step 1: Fetch mentions

```python
from src.social import fetch_all_mentions
result = fetch_all_mentions()
print(result)
```

Run AFTER `fetch_all_twitter()` — rate limit ordering matters.

### Step 2: Summarize

Query recent mentions:

```python
from src.db import get_db
db = get_db('data/atmina.db')
mentions = db.execute("""
    SELECT d.id, d.content, d.source_url, d.scraped_at,
           p.name AS target_name, p.party
    FROM documents d
    JOIN document_politicians dp
      ON dp.document_id = d.id AND dp.role = 'mention_target'
    JOIN tracked_politicians p ON p.id = dp.politician_id
    WHERE d.platform = 'x_mention'
      AND date(d.scraped_at) >= date('now', '-1 day')
    ORDER BY d.scraped_at DESC
""").fetchall()
```

**There is no `documents.mention_target_id`.** Documents link to politicians through the `document_politicians` junction (many-to-many, `role` ∈ subject / mentioned / mention_target) — see CLAUDE.md § Schema invariants. This prompt queried the non-existent column until 2026-08-01, so Step 2 raised `OperationalError` rather than returning anything.

One tweet can target several politicians, so the join emits **one row per (document, target)**. Deduplicate on `d.id` before counting mentions, or you will over-count multi-target tweets.

### Step 3: Report

```markdown
## Pieminējumu pārskats — YYYY-MM-DD

**Kopā:** N pieminējumi par N politiķiem

### Visvairāk pieminētie
| Politiķis | Partija | Pieminējumi |
|-----------|---------|-------------|
[Top 10]

### Ievērojami pieminējumi
[Notable mentions with high engagement or newsworthy content]
```

Write report to `wiki/dailies/YYYY-MM-DD.md` (append to existing daily notes if present).

## Critical Rules

1. Run AFTER `fetch_all_twitter()` — rate limits
2. Neutral reporting — don't classify mentions by sentiment or party alignment
3. Note interesting patterns (sudden spike in mentions for a politician, trending topics)
4. **A zero day is a scraper claim, not a fact about politics (CLAUDE.md T12).** X has repeatedly changed its response format rather than removed content, so "0 mentions" almost always means the fetch path broke — a bad transaction key, an expired `ct0`/`auth_token` pair, or a silent fall back from `search` to `timeline` (which cannot see untracked accounts at all, so its yield is systematically ~0). Before reporting an empty day: check whether the pool degraded (`scripts/probe_x_cookies.py`), say in the report **which fetch path produced the number**, and treat a suspected format change as alert-and-retry, not as a finding. Reporting a quiet day that was actually a broken fetch is the expensive failure here — nothing downstream re-checks it.
