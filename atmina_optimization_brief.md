# Atmiņa Project Optimization Brief

## Executive read

Atmiņa should **not** be rewritten. It is already a working Python/SQLite static-site and analysis pipeline with a lot of domain-specific rules encoded in code, docs, and runbooks: source provenance, claim idempotency, Saeima vote separation, X/Twitter relay behavior, `speaker_id`, `claim_type`, atomic `save_analysis()`, and Latvian-language quality guardrails.

The best optimization path is:

> **Freeze behavior → split large files behind compatibility facades → formalize migrations → optimize hot paths → simplify operations/docs.**

The project is large enough for structure to matter: it spans ingestion, X/Twitter scraping, Saeima, KNAB, CSP, SQLite/vector search, Claude Code analysis, wiki sync, briefs, and static-site generation.

---

## 1. Keep the current public API stable while refactoring

**What:** Treat existing module entry points as compatibility contracts.

Preserve these imports and commands while moving internals:

```bash
python -c "from src.generate import generate_public_site; generate_public_site()"
python -c "from src.routine import print_routine; print_routine()"
python -m pytest tests/ -v
bash scripts/deploy.sh --dry-run
```

**How:** Use facade modules. For example, keep `src/generate.py`, but make it import from `src/site/*`. Keep `src/db.py`, but gradually re-export from `src/storage/*`.

**Pros:** Lowest breakage risk. Agents, runbooks, scripts, and muscle memory keep working.

**Cons:** Some old module names remain longer than ideal. You temporarily have both old and new structure.

---

## 2. Split `src/generate.py` first

**What:** Break the static-site generator into page/query/view-model modules.

`generate.py` currently mixes security filters, constants, colors, URL helpers, markdown/wiki parsing, DB queries, SVG helpers, page rendering, statistics, and template setup.

**How:**

```text
src/
  generate.py                 # compatibility facade
  site/
    env.py                    # Jinja env, filters, bleach/safe_json/safe_url
    constants.py              # labels, party colors, topic colors
    urls.py                   # slugify, internal links, URL safety
    queries/
      dashboard.py
      politicians.py
      parties.py
      positions.py
      contradictions.py
      statistics.py
    viewmodels/
      politician.py
      contradiction.py
      vote.py
    render.py                 # write files/assets
```

Do this page by page. Start with pure helpers/constants, then DB query functions, then page renderers. Do **not** rename output files, templates, or URLs in the same phase.

**Pros:** Biggest maintainability gain. Easier tests. Easier to change one page without touching the whole generator.

**Cons:** Risk of circular imports if split too aggressively. Requires good smoke tests around generated output.

---

## 3. Split `src/db.py`, but keep `src.db` as the stable facade

**What:** Move storage concerns into a `src/storage/` package.

`db.py` currently contains DB path/config, Latvia time helpers, schema creation, inline migrations, SQLite pragmas, document deduplication, chunk/vector storage, vector search, claim storage, contradiction storage, and indexes. It is the most important file to refactor cautiously.

**How:**

```text
src/
  db.py                       # facade / backwards-compatible exports
  storage/
    connection.py             # get_db, DB_PATH, pragmas
    time.py                   # now_lv, now_lv_dt, today_lv
    schema.py                 # base schema creation
    migrations.py             # migration runner
    documents.py              # insert_document, chunks, simhash
    claims.py                 # store_claim, store_contradiction
    vectors.py                # sqlite-vec load/search
    logs.py                   # log_action, get_last_log
```

Keep this working:

```python
from src.db import get_db, store_claim, insert_document
```

**Pros:** Makes future schema and claim logic safer. Reduces “god file” risk.

**Cons:** High coupling: many modules import from `src.db`. Move in small PRs/commits only.

---

## 4. Formalize migrations

**What:** Stop letting `init_db()` become the permanent home for every historical schema change.

Recent project changes include removing fake Saeima document rows, allowing `claims.document_id = NULL` for Saeima votes, adding `external_profiles`, adding `speaker_id`, and treating `social_accounts` as X-only.

**How:**

```text
migrations/
  0001_initial.py
  0002_document_politicians.py
  0003_claim_type.py
  0004_speaker_id.py
  0005_external_profiles.py
  0006_saeima_doc_cleanup.py
```

Each migration should expose:

```python
def check(conn) -> bool: ...
def apply(conn) -> None: ...
def verify(conn) -> None: ...
```

Add a `schema_migrations` table and run migrations explicitly.

**Pros:** Reproducible setup. Safer production DB evolution. Easier rollback planning.

**Cons:** Requires fixture DBs representing old states. Up-front migration cleanup is tedious.

---

## 5. Fix model-contract drift

**What:** Align Pydantic contracts with current DB reality.

The project rules say `claims.document_id` is optional: Saeima votes store `NULL`, while `position` and `commentary` require a document. If `Claim.document_id` is still typed as `int`, wrappers/tools may enforce outdated constraints.

**How:**

```python
class Claim(BaseModel):
    document_id: int | None
```

Then enforce the real rule in one place:

```python
if claim_type in {"position", "commentary"} and document_id is None:
    raise ValueError("document_id required for position/commentary claims")

if claim_type == "saeima_vote":
    # document_id may be None
```

**Pros:** Prevents future agents or scripts from reintroducing fake Saeima documents.

**Cons:** Needs tests around `store_claim()`, `save_analysis()`, and Saeima vote generation.

---

## 6. Keep `save_analysis()` atomic and make it the only write path for analysis batches

**What:** Treat `save_analysis()` as the canonical write boundary for analysis + claims + reviewed documents.

It should wrap analysis storage, claim writes, and reviewed-document marking inside one SQLite transaction. It should record partial failures for validation-level skips while rolling back catastrophic DB failures.

**How:** Move helper details out of `src/analyze.py`, but preserve the function signature and return shape.

Potential structure:

```text
src/analysis/
  workflow.py                 # save_analysis facade
  pending.py                  # get_pending_politicians, docs retrieval
  validation.py               # indirect-reference gate
  review.py                   # mark_documents_reviewed
```

**Pros:** Keeps the most important data-integrity boundary intact.

**Cons:** Must avoid “nice refactors” that accidentally commit claims before analysis or mark docs reviewed outside the transaction.

---

## 7. Separate ingestion into source-specific adapters

**What:** Break `src/ingest.py` into adapters and a shared orchestration layer.

`ingest.py` currently includes scraping, RSS parsing, URL filtering, language detection, source-specific rules, published-date extraction, politician matching, dedup validation, and storage.

**How:**

```text
src/ingest/
  __init__.py                 # compatibility exports
  pipeline.py                 # ingest_all / ingest_source orchestration
  rss.py                      # _parse_rss_items
  web.py                      # trafilatura/crawl4ai fetchers
  validation.py               # validate_content
  relevance.py                # URL/section/keyword filters
  matching.py                 # match_politicians, role assignment
  published_at.py             # _extract_published_at
```

**Pros:** Easier to add or debug one source without breaking others.

**Cons:** `ingest.py` is behavior-heavy; split only after characterization tests for RSS, `published_at`, dedupe, and politician matching.

---

## 8. Keep X/Twitter code isolated from generic social code

**What:** Accept that `social_accounts` is now X-only and design around that.

If old `fetch_youtube()` and `fetch_facebook()` functions still exist, they are a structural smell unless explicitly marked as legacy or experimental.

**How:**

```text
src/social/
  x_fetch.py                  # fetch_twitter, fetch_all_twitter
  x_store.py                  # _store_tweets
  mentions.py                 # fetch_all_mentions wrapper
  external_profiles.py        # display-only profile links for now
  legacy.py                   # old facebook/youtube code, if retained
```

Then either remove unused Facebook/YouTube fetchers or explicitly mark them experimental.

**Pros:** Aligns code with current invariant. Reduces chance someone adds Facebook rows back into `social_accounts`.

**Cons:** If you plan to fetch non-X profiles later, you need a new `external_profiles` fetcher design instead of reusing old `social_accounts` assumptions.

---

## 9. Make dependency groups explicit

**What:** Split requirements into runtime, dev, browser/scraping, and optional AI/graphics groups.

Current dependencies appear to mix runtime, scraping, NLP/vector, browser, graphics, and dev tooling.

**How:**

```text
requirements/
  base.txt                    # runtime: sqlite-vec, pydantic, jinja2, httpx
  scrape.txt                  # crawl4ai, playwright, trafilatura
  nlp.txt                     # sentence-transformers, fasttext, torch
  graphics.txt                # matplotlib, playwright image deps, google-genai
  dev.txt                     # pytest, ruff
  lock.txt
```

Or move to `pyproject.toml` with optional groups.

**Pros:** Faster setup for simple tasks. Cleaner CI. Easier deploy environment.

**Cons:** More files. Need to keep lock generation consistent.

---

## 10. Add `pyproject.toml` and CI

**What:** Add a single source of truth for test/lint config and run it automatically.

**How:**

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
  "integration: requires real DB/model/browser",
  "slow: slow NLP/vector tests"
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "ARG"]
ignore = []
```

CI should run:

```bash
python -m ruff check src scripts tests
python -m pytest tests -q
python -c "from src.generate import generate_public_site; generate_public_site()"
```

**Pros:** Prevents regressions before deployment. Makes refactoring much safer.

**Cons:** Playwright/NLP/model-dependent tests may need markers or caching.

---

## 11. Optimize vector and embedding performance after structure is safer

**What:** Improve heavy operations only after module boundaries are cleaner.

The project uses multilingual embeddings, SQLite, sqlite-vec, document chunks, and claim vectors. These are likely worthwhile performance areas, but they should not be optimized before behavior is frozen.

**How:**

Priorities:

1. Cache embeddings by content hash.
2. Batch document ingestion more aggressively.
3. Avoid loading sqlite-vec extension repeatedly in tight loops.
4. Add simple timing logs around scrape → validate → embed → insert.
5. Add indexes for query patterns found in `generate.py`.

**Pros:** Reduces ingest/runtime cost and generation latency.

**Cons:** Caching and batching can introduce stale data if invalidation is not clear.

---

## 12. Improve deploy safety, not deploy complexity

**What:** Keep rsync deploy, but add preflight and post-deploy verification.

The deploy model is simple and good: static output, rsync over SSH, `--dry-run`, and excludes for server-managed paths.

**How:** Add a wrapper:

```bash
python -m pytest tests -q
python -c "from src.generate import generate_public_site; generate_public_site()"
python -c "from src.wiki_lint import lint_wiki; print(lint_wiki())"
bash scripts/deploy.sh --dry-run
```

Then real deploy.

**Pros:** Keeps deployment boring. Avoids introducing hosting complexity.

**Cons:** Still depends on local machine state and SSH config.

---

## 13. Keep security fixes centralized

**What:** Keep all HTML/URL/JSON safety filters in one site environment module.

**How:** Move filters such as HTML sanitization, safe JSON serialization, and safe URL validation into `src/site/env.py`, and make every template environment import from there.

**Pros:** Security behavior becomes consistent and testable.

**Cons:** Template rendering code must not create ad-hoc Jinja environments elsewhere.

---

## 14. Reduce docs drift

**What:** Make docs generated where possible, curated where necessary.

**How:**

- Keep `wiki/index.md` generated from live DB.
- Keep `docs/architecture.md` as conceptual architecture, not live counts.
- Move volatile counts into generated sections.
- Add a “last verified against code” date.

**Pros:** Fewer misleading docs. Easier onboarding.

**Cons:** Requires discipline: not every doc should be auto-generated.

---

## 15. Remove dead code only in verified batches

**What:** Follow a verified dead-code cleanup plan, but treat agent/runbook-called functions as live.

**How:**

Good candidates:

- delete verified orphan helpers in `generate.py`;
- delete replaced Saeima parsing in `ingest.py`;
- apply safe ruff fixes;
- leave admin/runbook/agent functions unless explicitly confirmed unused.

**Pros:** Reduces noise without breaking hidden workflows.

**Cons:** Dynamic agent usage is hard to detect. Manual verification remains necessary.

---

## Perspective-by-perspective priorities

| Perspective | Highest-value optimization | Avoid |
|---|---|---|
| Architecture | Split `generate.py`, `db.py`, `ingest.py` behind facades | Big-bang rewrite |
| Data integrity | Formal migrations + contract tests | Silent schema drift in `init_db()` |
| Agent workflows | Preserve tool function names and JSON shapes | Renaming `save_analysis`, `store_claim`, `retrieve_context` casually |
| Performance | Cache embeddings, batch inserts, reduce repeated vector extension loading | Premature async rewrite of everything |
| Security | Centralize safe HTML/URL/JSON filters and add CSP at hosting layer | Scattered template safety helpers |
| Operations | Preflight before deploy, keep rsync static deploy | Adding a server app unless needed |
| Docs | Generate live counts, curate invariants | Static docs with stale numbers |
| Testing | Characterization tests before file moves | Refactoring first, testing later |

---

## Recommended implementation order

### Phase 0 — Safety baseline

Run and preserve current behavior:

```bash
python -m pytest tests/ -q
python -c "from src.generate import generate_public_site; generate_public_site()"
python -c "from src.routine import print_routine; print_routine()"
bash scripts/deploy.sh --dry-run
```

Add missing smoke tests for the core invariants:

- `source_url` required for provenance;
- idempotency on `(opponent_id, source_url, topic)`;
- `speaker_id`;
- `claim_type`;
- `feed_type`;
- `document_id=None` for Saeima votes.

### Phase 1 — Low-risk cleanup

Do verified dead-code removal and ruff-safe fixes. Do not touch architecture yet.

### Phase 2 — Generator split

Extract `src/site/env.py`, `constants.py`, `urls.py`, then one page query module at a time.

### Phase 3 — DB/storage split

Create `src/storage/`, move connection/time/document/claim/vector logic gradually, keep `src.db` exports.

### Phase 4 — Migration system

Introduce `schema_migrations`, convert current inline migration blocks into numbered migrations, leave `init_db()` as “create base + run migrations.”

### Phase 5 — Ingestion and X/social split

Separate RSS/web/matching/published-at logic. Then split X-only logic from old generic social code.

### Phase 6 — Performance

Only after the structure is safer: embedding cache, better batching, generation query profiling.

---

## Biggest risks to preserve

Do not break these:

1. **Claims without `source_url` must not become publishable**, because provenance is core to citations and contradiction checking.
2. **`store_claim()` idempotency on `(opponent_id, source_url, topic)`** must stay intact.
3. **`claim_type` separation** between `position`, `saeima_vote`, and `commentary` must remain explicit.
4. **`speaker_id` must continue separating author from subject**, especially for commentary.
5. **Saeima votes should not recreate fake `documents.platform='saeima'` rows**, because that was already cleaned up as a structural anti-pattern.
6. **Relay X accounts must not be treated as first-party speakers**, because `feed_type='relay'` fixes the LTV/media-account problem.
7. **`save_analysis()` must remain atomic**, because partial analysis/claim/doc-review writes would corrupt the workflow.

---

## Strongest recommendation

Start with **`generate.py` extraction + migration formalization**, not performance work.

Those two changes give the most long-term leverage while preserving the current product. The project’s complexity is not mainly CPU-bound; it is **invariant-bound**. The more clearly the code mirrors those invariants, the safer every future optimization becomes.

---

## Review note

This brief is based on structural review and implementation planning. It is not a verified patch and does not claim the test suite has been run.
