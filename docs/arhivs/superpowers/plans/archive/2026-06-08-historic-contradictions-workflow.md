# Historic-contradictions Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A reusable Workflow that discovers historic articles for a small set of politicians via WebSearch, ingests them backdated, extracts pozīcijas, and hunts contradictions against their full history — ending at `confirmed=0` survivors for operator review.

**Architecture:** One net-new tested CLI (`scripts/ingest_url.py`) generalizes the hardcoded retrofetch pattern (fetch → clean → backdate → insert → link). One Workflow script (`.claude/workflows/historic-contradictions.js`) orchestrates a per-politician `pipeline(discover → ingest → extract → contradict)` plus a final report barrier, reusing the `@claim-extractor` / `@contradiction-hunter` / `@devils-advocate` agents and the deep-check 0.80 pattern.

**Tech Stack:** Python 3.12 (httpx, trafilatura, sqlite3), existing `src/db.py` + `src/matcher.py` + `src/ingest.py` + `src/title_extract.py`; Workflow JS DSL (`agent`/`pipeline`/`parallel`/`phase`).

---

## File Structure

- **Create `scripts/ingest_url.py`** — generic single/manifest URL historic-ingest CLI. Pure-ish core (`ingest_one`, `ingest_manifest`, `parse_manifest`, `_published_at_from_url`) with injectable `fetch_fn` / `link_fn` / `db_path`; thin `main(argv)` argparse wrapper. One responsibility: turn URLs into backdated, politician-linked `documents` rows + a JSON report.
- **Create `tests/test_ingest_url.py`** — TDD coverage; network + matcher injected, temp DB.
- **Create `.claude/workflows/historic-contradictions.js`** — the Workflow orchestration script. One responsibility: drive discovery→ingest→extract→contradict→report; no business logic of its own.
- **Modify `wiki/operations/operacijas.md`** — add a runbook subsection documenting invocation + discovery-yield caveat.

---

## Task 1: `ingest_url.py` core — `ingest_one` backdating

**Files:**
- Create: `scripts/ingest_url.py`
- Test: `tests/test_ingest_url.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ingest_url.py
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db import init_db, insert_document, get_db  # noqa: E402
import scripts.ingest_url as iu  # noqa: E402


@pytest.fixture
def tmp_db(tmp_path) -> str:
    db_path = str(tmp_path / "t.db")
    init_db(db_path=db_path)
    return db_path


def _fetch_ok(text="x" * 400, title="Vēsturisks raksts", published_at="2021-03-01T10:00:00+03:00"):
    def _fn(url):
        return {"text": text, "title": title, "published_at": published_at}
    return _fn


def test_ingest_one_backdates_published_at(tmp_db):
    res = iu.ingest_one(
        "https://lsm.lv/raksts/old.a1",
        politician_id=None,
        fetch_fn=_fetch_ok(),
        db_path=tmp_db,
    )
    assert res["status"] == "ingested"
    assert res["doc_id"] is not None
    row = get_db(tmp_db).execute(
        "SELECT published_at FROM documents WHERE id=?", (res["doc_id"],)
    ).fetchone()
    assert row["published_at"] == "2021-03-01T10:00:00+03:00"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ingest_url.py::test_ingest_one_backdates_published_at -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.ingest_url'` (or `AttributeError: ingest_one`).

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/ingest_url.py
"""Generic historic-article ingest CLI.

Generalizes the hardcoded retrofetch_* scripts into one tested tool:
fetch -> clean (trafilatura) -> backdate -> insert_document -> link politicians.

  python scripts/ingest_url.py --url URL [--politician-id N]
  python scripts/ingest_url.py --manifest items.jsonl   # {"url": "...", "politician_id": N}

Idempotent: skips URLs already in `documents`; insert_document dedups by content_hash.
Additive only (no row mutation beyond insert_document's URL-first update) -> no rollback SQL.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Callable, Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db import DB_PATH, get_db, insert_document  # noqa: E402
from src.matcher import link_politicians_to_documents  # noqa: E402

MIN_CHARS = 150
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "lv,en;q=0.5",
}


def _published_at_from_url(url: str) -> Optional[str]:
    """Best-effort date from a /YYYY/MM/DD/ or /YYYY/ path. Rare for LSM/TVNet."""
    m = re.search(r"/(20\d{2})/(\d{2})/(\d{2})/", url)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.search(r"/(20\d{2})/", url)
    if m:
        return f"{m.group(1)}-01-01"
    return None


def _default_fetch(url: str) -> Optional[dict]:
    """Real network path: httpx GET -> trafilatura + title + published_at. None on error."""
    import httpx
    import trafilatura

    from src.ingest import _extract_published_at
    from src.title_extract import extract_title

    try:
        with httpx.Client(timeout=20.0, follow_redirects=True, headers=HEADERS) as client:
            resp = client.get(url)
            resp.raise_for_status()
    except Exception as e:  # noqa: BLE001
        print(f"  ERR fetch {url[:80]}: {e}", file=sys.stderr)
        return None
    text = trafilatura.extract(
        resp.text, include_comments=False, include_tables=False, deduplicate=True
    )
    pub = _extract_published_at(resp.text) or _published_at_from_url(url)
    return {"text": text, "title": extract_title(resp.text), "published_at": pub}


def ingest_one(
    url: str,
    politician_id: Optional[int] = None,
    *,
    fetch_fn: Callable[[str], Optional[dict]] = _default_fetch,
    db_path: str = DB_PATH,
) -> dict:
    """Ingest one URL. Returns {url, status, doc_id, published_at, title}.

    status: ingested | already_present | dupe | thin | fetch_error
    """
    out = {"url": url, "status": None, "doc_id": None, "published_at": None, "title": None}

    existing = get_db(db_path).execute(
        "SELECT id FROM documents WHERE source_url=?", (url,)
    ).fetchone()
    if existing:
        out["status"] = "already_present"
        out["doc_id"] = existing["id"]
        return out

    parsed = fetch_fn(url)
    if parsed is None:
        out["status"] = "fetch_error"
        return out

    text = (parsed.get("text") or "")
    if len(text) < MIN_CHARS:
        out["status"] = "thin"
        return out

    out["published_at"] = parsed.get("published_at")
    out["title"] = parsed.get("title")
    doc_id = insert_document(
        content=text[:50000],
        source_id=None,
        platform="web",
        language="lv",
        source_url=url,
        published_at=parsed.get("published_at"),
        title=parsed.get("title"),
        db_path=db_path,
    )
    if doc_id is None:
        out["status"] = "dupe"
        return out
    out["status"] = "ingested"
    out["doc_id"] = doc_id
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ingest_url.py::test_ingest_one_backdates_published_at -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/ingest_url.py tests/test_ingest_url.py
git commit -m "feat(ingest): ingest_url.py core — backdated single-URL ingest"
```

---

## Task 2: `ingest_one` status branches

**Files:**
- Modify: `tests/test_ingest_url.py` (add tests)
- (No source change — Task 1 implementation already covers these; this task locks them.)

- [ ] **Step 1: Write the failing tests**

```python
def test_ingest_one_already_present(tmp_db):
    insert_document(
        content="y" * 400, source_id=None, platform="web", language="lv",
        source_url="https://lsm.lv/raksts/seen.a2", published_at=None,
        title="t", db_path=tmp_db,
    )

    def _boom(url):
        raise AssertionError("fetch_fn must not be called when already present")

    res = iu.ingest_one("https://lsm.lv/raksts/seen.a2", fetch_fn=_boom, db_path=tmp_db)
    assert res["status"] == "already_present"


def test_ingest_one_dupe_by_content(tmp_db):
    shared = "z" * 400
    insert_document(
        content=shared, source_id=None, platform="web", language="lv",
        source_url="https://a.lv/one.a1", published_at=None, title="t", db_path=tmp_db,
    )
    res = iu.ingest_one(
        "https://b.lv/two.a2", fetch_fn=_fetch_ok(text=shared), db_path=tmp_db
    )
    assert res["status"] == "dupe"


def test_ingest_one_thin(tmp_db):
    res = iu.ingest_one(
        "https://a.lv/thin.a3", fetch_fn=_fetch_ok(text="too short"), db_path=tmp_db
    )
    assert res["status"] == "thin"
    assert res["doc_id"] is None


def test_ingest_one_fetch_error(tmp_db):
    res = iu.ingest_one("https://a.lv/err.a4", fetch_fn=lambda u: None, db_path=tmp_db)
    assert res["status"] == "fetch_error"


def test_published_at_from_url():
    assert iu._published_at_from_url("https://x.lv/2021/03/15/foo") == "2021-03-15"
    assert iu._published_at_from_url("https://x.lv/2019/foo") == "2019-01-01"
    assert iu._published_at_from_url("https://lsm.lv/raksts/foo.a12345") is None
```

- [ ] **Step 2: Run tests to verify they pass (implementation already present)**

Run: `python -m pytest tests/test_ingest_url.py -v`
Expected: all PASS (Task 1 code satisfies them). If `test_ingest_one_dupe_by_content` fails, confirm the shared content is ≥150 chars and identical bytes.

- [ ] **Step 3: Commit**

```bash
git add tests/test_ingest_url.py
git commit -m "test(ingest): lock ingest_one status branches"
```

---

## Task 3: `parse_manifest` + `ingest_manifest` + summary

**Files:**
- Modify: `scripts/ingest_url.py` (add `parse_manifest`, `ingest_manifest`)
- Modify: `tests/test_ingest_url.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_parse_manifest_skips_bad_lines(tmp_path):
    p = tmp_path / "m.jsonl"
    p.write_text(
        '{"url": "https://a.lv/1.a1", "politician_id": 5}\n'
        "not json\n"
        '{"url": "https://a.lv/2.a2"}\n',
        encoding="utf-8",
    )
    items = iu.parse_manifest(str(p))
    assert [i["url"] for i in items] == ["https://a.lv/1.a1", "https://a.lv/2.a2"]
    assert items[0]["politician_id"] == 5
    assert items[1].get("politician_id") is None


def test_ingest_manifest_summary(tmp_db):
    items = [
        {"url": "https://a.lv/ok.a1", "politician_id": 7},
        {"url": "https://a.lv/thin.a2", "politician_id": 7},
    ]

    def _fetch(url):
        if "thin" in url:
            return {"text": "short", "title": None, "published_at": None}
        return {"text": "w" * 400, "title": "T", "published_at": "2020-05-05"}

    def _fake_link(days=1, rescan_all=False, db_path=None):
        # pretend the matcher linked the freshly-ingested doc to pid 7
        return {doc_id: [7] for doc_id in iu._LAST_INGESTED_IDS}

    summary = iu.ingest_manifest(
        items, fetch_fn=_fetch, link_fn=_fake_link, db_path=tmp_db
    )
    assert summary["ingested"] == 1
    assert summary["thin"] == 1
    assert 7 in summary["linked_to"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ingest_url.py::test_parse_manifest_skips_bad_lines tests/test_ingest_url.py::test_ingest_manifest_summary -v`
Expected: FAIL — `AttributeError: module 'scripts.ingest_url' has no attribute 'parse_manifest'`.

- [ ] **Step 3: Write the implementation**

```python
# append to scripts/ingest_url.py

_LAST_INGESTED_IDS: list[int] = []


def parse_manifest(path: str) -> list[dict]:
    """Read a JSONL manifest of {url, politician_id?}. Bad lines skipped with a warning."""
    items: list[dict] = []
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if "url" not in obj:
                raise ValueError("no url")
            items.append({"url": obj["url"], "politician_id": obj.get("politician_id")})
        except Exception as e:  # noqa: BLE001
            print(f"  SKIP bad manifest line {n}: {e}", file=sys.stderr)
    return items


def ingest_manifest(
    items: list[dict],
    *,
    fetch_fn: Callable[[str], Optional[dict]] = _default_fetch,
    link_fn: Callable = link_politicians_to_documents,
    db_path: str = DB_PATH,
) -> dict:
    """Ingest all items, link politicians once, return an aggregate summary dict."""
    global _LAST_INGESTED_IDS
    results = [
        ingest_one(it["url"], it.get("politician_id"), fetch_fn=fetch_fn, db_path=db_path)
        for it in items
    ]
    _LAST_INGESTED_IDS = [r["doc_id"] for r in results if r["status"] == "ingested"]

    linked = link_fn(days=1, rescan_all=True) if _LAST_INGESTED_IDS else {}
    linked_to: dict[int, list[int]] = {}
    for doc_id, pids in (linked or {}).items():
        for pid in pids:
            linked_to.setdefault(pid, []).append(doc_id)

    summary = {
        "ingested": sum(r["status"] == "ingested" for r in results),
        "already_present": sum(r["status"] == "already_present" for r in results),
        "dupe": sum(r["status"] == "dupe" for r in results),
        "thin": sum(r["status"] == "thin" for r in results),
        "fetch_error": sum(r["status"] == "fetch_error" for r in results),
        "dateless": [r["doc_id"] for r in results
                     if r["status"] == "ingested" and not r["published_at"]],
        "linked_to": linked_to,
        "results": results,
    }
    return summary
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ingest_url.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/ingest_url.py tests/test_ingest_url.py
git commit -m "feat(ingest): manifest parsing + batch ingest summary"
```

---

## Task 4: `main(argv)` CLI wrapper

**Files:**
- Modify: `scripts/ingest_url.py` (add `main` + `__main__` guard)
- Modify: `tests/test_ingest_url.py`

- [ ] **Step 1: Write the failing test (parse-only, no network)**

```python
def test_main_requires_url_or_manifest(capsys):
    rc = iu.main(["--politician-id", "5"])
    assert rc == 2  # argparse-style usage error


def test_main_single_url_invokes_ingest(monkeypatch, tmp_db):
    calls = {}

    def _fake_ingest_manifest(items, **kw):
        calls["items"] = items
        return {"ingested": len(items), "already_present": 0, "dupe": 0, "thin": 0,
                "fetch_error": 0, "dateless": [], "linked_to": {}, "results": []}

    monkeypatch.setattr(iu, "ingest_manifest", _fake_ingest_manifest)
    rc = iu.main(["--url", "https://a.lv/x.a1", "--politician-id", "9", "--db", tmp_db])
    assert rc == 0
    assert calls["items"] == [{"url": "https://a.lv/x.a1", "politician_id": 9}]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ingest_url.py::test_main_single_url_invokes_ingest -v`
Expected: FAIL — `AttributeError: module 'scripts.ingest_url' has no attribute 'main'`.

- [ ] **Step 3: Write the implementation**

```python
# append to scripts/ingest_url.py

def main(argv: Optional[list[str]] = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # Latvian titles
    ap = argparse.ArgumentParser(description="Historic article ingest (fetch -> backdate -> link).")
    ap.add_argument("--url", help="single URL to ingest")
    ap.add_argument("--politician-id", type=int, default=None, help="hint pid for --url")
    ap.add_argument("--manifest", help="JSONL of {url, politician_id?}")
    ap.add_argument("--db", default=DB_PATH, help="DB path (default: live)")
    args = ap.parse_args(argv)

    if not args.url and not args.manifest:
        ap.print_usage(sys.stderr)
        print("error: one of --url or --manifest is required", file=sys.stderr)
        return 2

    items = (
        [{"url": args.url, "politician_id": args.politician_id}]
        if args.url
        else parse_manifest(args.manifest)
    )
    summary = ingest_manifest(items, db_path=args.db)
    for r in summary["results"]:
        print("RESULT_JSON:" + json.dumps(r, ensure_ascii=False))
    printable = {k: v for k, v in summary.items() if k != "results"}
    print("SUMMARY_JSON:" + json.dumps(printable, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests + ruff**

Run: `python -m pytest tests/test_ingest_url.py -v && ruff check scripts/ingest_url.py tests/test_ingest_url.py`
Expected: all PASS, ruff clean.

- [ ] **Step 5: Commit**

```bash
git add scripts/ingest_url.py tests/test_ingest_url.py
git commit -m "feat(ingest): ingest_url CLI wrapper (--url / --manifest)"
```

---

## Task 5: The Workflow script

**Files:**
- Create: `.claude/workflows/historic-contradictions.js`

- [ ] **Step 1: Write the workflow script**

Write `.claude/workflows/historic-contradictions.js` verbatim from the "Workflow script" appendix at the bottom of this plan. It must:
- begin with a pure-literal `export const meta = {...}` (name, description, phases);
- read `args = { politicians, since?, until?, topics?, perPolitician?, seedUrls? }`;
- run a Resolve agent → `pipeline(resolved, discover, ingest, extract, contradict)` → Report barrier;
- set `stated_at = published_at` in the extract prompt;
- store contradiction survivors at `confirmed=0`;
- return the report object; never render/deploy.

- [ ] **Step 2: Lint the JS (syntax sanity, no execution)**

Run: `node --check .claude/workflows/historic-contradictions.js`
Expected: no output (valid syntax). If `node` is unavailable, skip — the Workflow runtime parses it on invoke.

- [ ] **Step 3: Dry-run with a single well-covered minister (smoke)**

Invoke via the Workflow tool: `{ name: "historic-contradictions", args: { politicians: ["Jānis Vitenbergs"], since: "2020-01-01", until: "2022-12-31", perPolitician: 6 } }`
Expected: phases progress Resolve→Discover→Ingest→Extract→Contradict→Report; report returns URL/claim/contradiction counts; any survivors are `confirmed=0`. Verify no `confirmed=1` row was written:
`python -c "from src.db import get_db; print(get_db().execute(\"SELECT COUNT(*) FROM contradictions WHERE confirmed=1 AND detected_at>=date('now','-1 day')\").fetchone()[0])"`
Expected: `0`.

- [ ] **Step 4: Commit**

```bash
git add .claude/workflows/historic-contradictions.js
git commit -m "feat(workflow): historic-contradictions discovery→ingest→extract→contradict"
```

---

## Task 6: Runbook entry

**Files:**
- Modify: `wiki/operations/operacijas.md`

- [ ] **Step 1: Add a subsection** (place near the deep-check / contradiction runbook material):

```markdown
### Vēsturisko rakstu ingest + pretrunu hunt (`historic-contradictions` workflow)

Atrod un ielādē politiķa **vēsturiskos** rakstus no tīmekļa (WebSearch), backdatē
(`published_at`), izvelk pozīcijas un meklē pretrunas pret pilno vēsturi.

- **Palaišana:** Workflow rīks → `historic-contradictions`,
  `args = { politicians: ["Vārds Uzvārds", …], since, until, perPolitician }`.
- **Avots:** tikai WebSearch discovery; `seedUrls: {vārds: [url,…]}` injicē zināmus URL.
- **Manuāls ingest atsevišķiem URL:** `python scripts/ingest_url.py --manifest items.jsonl`
  (JSONL `{"url": "...", "politician_id": N}`) vai `--url URL --politician-id N`.
- **Iznākums:** pretrunu survivors glabājas `confirmed=0` (nepublicēti). Operators pārskata,
  `UPDATE confirmed=1`, tad **šaurs render**: `python -m src.render --only=pretrunas` → `deploy.sh --no-delete`.
- **Raža mainās:** ministriem/frakciju vadītājiem ir bagāta vēsturiskā pārklāšanās; X-only /
  oportūnistiskiem kritiķiem bieži nav. "0 rakstu" ir derīgs iznākums — neizdomā atradumus
  (ROI ~1/2700, sk. `reference_contradiction_hunt_lessons`).
```

- [ ] **Step 2: Verify the file still renders as valid markdown** (visual scan; `operacijas.md` is hand-maintained, not wiki_sync-generated — safe to edit directly).

- [ ] **Step 3: Commit**

```bash
git add wiki/operations/operacijas.md
git commit -m "docs(runbook): historic-contradictions workflow + ingest_url CLI"
```

---

## Task 7: Full verification

- [ ] **Step 1:** `python -m pytest tests/test_ingest_url.py -v` → all PASS.
- [ ] **Step 2:** `ruff check scripts/ingest_url.py tests/test_ingest_url.py` → clean.
- [ ] **Step 3:** `bash scripts/check.sh` → ruff + full pytest + render smoke all green (confirms no regression from the new files entering ruff/pytest scope).
- [ ] **Step 4:** Report results (quote the check.sh tail). Do not claim done before this passes.

---

## Appendix: Workflow script (`.claude/workflows/historic-contradictions.js`)

> **CANONICAL = the committed `.claude/workflows/historic-contradictions.js`.** The skeleton
> below is the design intent; the shipped file corrects two things found during implementation:
> (1) **each pipeline stage threads an accumulator** (`{...prev, newField}`) so the final Report
> sees `urls`/`linked_doc_ids`/`extract`/`survivors` — a bare `pipeline()` only hands the *last*
> stage's return to the result array; (2) **`agentType` per stage** loads canonical agents
> (`general-purpose` for resolve/discover/ingest, `claim-extractor`, `contradiction-hunter`,
> `devils-advocate`) instead of re-describing each contract inline.

```javascript
export const meta = {
  name: 'historic-contradictions',
  description: 'Discover historic articles for a small set of politicians, ingest them backdated, extract pozīcijas, and hunt contradictions vs full history (survivors stored confirmed=0).',
  phases: [
    { title: 'Resolve', detail: 'names -> politician ids' },
    { title: 'Discover', detail: 'WebSearch historic articles per politician' },
    { title: 'Ingest', detail: 'ingest_url.py — backdated insert + link' },
    { title: 'Extract', detail: '@claim-extractor, stated_at = published_at' },
    { title: 'Contradict', detail: '@contradiction-hunter -> @devils-advocate -> confirmed=0' },
    { title: 'Report', detail: 'operator review summary' },
  ],
}

const A = args || {}
const NAMES = A.politicians || []
const SINCE = A.since || '2018-01-01'
const UNTIL = A.until || 'older than ~6 months ago'
const TOPICS = A.topics || null
const PER = A.perPolitician || 12
const SEED = A.seedUrls || {}

if (!NAMES.length) {
  log('No politicians passed in args.politicians — nothing to do.')
  return { error: 'args.politicians is required (array of names or ids)' }
}

const RESOLVE_SCHEMA = {
  type: 'object',
  properties: {
    resolved: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          input: { type: 'string' },
          id: { type: ['integer', 'null'] },
          name: { type: ['string', 'null'] },
          surname: { type: ['string', 'null'] },
          party: { type: ['string', 'null'] },
          existing_claim_count: { type: 'integer' },
          note: { type: 'string' },
        },
        required: ['input', 'id'],
      },
    },
  },
  required: ['resolved'],
}

phase('Resolve')
const resolveOut = await agent(
  `Resolve these politician inputs to tracked_politicians rows in the atmina DB: ${JSON.stringify(NAMES)}.
For each input run (via Bash/python) a lookup against the live DB. Suggested:
  python -c "import json,sys; from src.db import get_db; db=get_db(); \\
    q=sys.argv[1]; rows=db.execute(\\"SELECT id,name,party,relationship_type FROM tracked_politicians WHERE name LIKE ?\\",(f'%{q}%',)).fetchall(); \\
    print(json.dumps([dict(r) for r in rows], ensure_ascii=False))" "<input>"
Match by name substring (the matcher does NOT fold diacritics — try the exact Latvian form first).
Skip rows where relationship_type='inactive' unless that is the only match (note it).
For each resolved politician also fetch existing_claim_count:
  SELECT COUNT(*) FROM claims WHERE opponent_id=? AND claim_type IN ('position','saeima_vote').
Return JSON for the StructuredOutput tool. id=null for unresolved inputs (with a note why).`,
  { label: 'resolve', phase: 'Resolve', schema: RESOLVE_SCHEMA }
)

const resolved = (resolveOut?.resolved || []).filter((r) => r.id != null)
const unresolved = (resolveOut?.resolved || []).filter((r) => r.id == null)
if (unresolved.length) log(`Unresolved (skipped): ${unresolved.map((u) => u.input).join(', ')}`)
if (!resolved.length) return { error: 'no politicians resolved', unresolved }
log(`Resolved ${resolved.length}: ${resolved.map((r) => r.name).join(', ')}`)

const DISCOVER_SCHEMA = {
  type: 'object',
  properties: {
    urls: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          url: { type: 'string' },
          why: { type: 'string' },
          guessedDate: { type: ['string', 'null'] },
        },
        required: ['url'],
      },
    },
  },
  required: ['urls'],
}

const INGEST_SCHEMA = {
  type: 'object',
  properties: {
    summary_json: { type: 'string', description: 'the SUMMARY_JSON line from ingest_url.py, raw' },
    linked_doc_ids: { type: 'array', items: { type: 'integer' } },
    dateless_doc_ids: { type: 'array', items: { type: 'integer' } },
  },
  required: ['linked_doc_ids'],
}

const EXTRACT_SCHEMA = {
  type: 'object',
  properties: {
    claim_ids: { type: 'array', items: { type: 'integer' } },
    claims: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'integer' },
          topic: { type: 'string' },
          stance: { type: 'string' },
          stated_at: { type: ['string', 'null'] },
        },
      },
    },
    empty_doc_ids: { type: 'array', items: { type: 'integer' } },
    failures: { type: 'array', items: { type: 'object' } },
  },
  required: ['claim_ids'],
}

const CONTRADICT_SCHEMA = {
  type: 'object',
  properties: {
    candidates: { type: 'integer' },
    survivors: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: ['integer', 'null'] },
          severity: { type: 'string' },
          summary: { type: 'string' },
          old_claim_id: { type: ['integer', 'null'] },
          new_claim_id: { type: ['integer', 'null'] },
        },
        required: ['severity', 'summary'],
      },
    },
  },
  required: ['survivors'],
}

const results = await pipeline(
  resolved,
  // STAGE 1 — discover (WebSearch)
  (pol) =>
    agent(
      `You are doing HISTORIC article discovery for Latvian politician "${pol.name}" (id ${pol.id}, party ${pol.party}).
Find OLDER public articles/interviews/quotes published between ${SINCE} and ${UNTIL}${TOPICS ? `, focused on topics: ${TOPICS.join(', ')}` : ''}.
Use the WebSearch tool with several angles (multi-modal sweep), e.g.:
  - "${pol.name}" intervija / komentē / paziņo  (per year in range)
  - "${pol.name}" site:lsm.lv  ·  site:delfi.lv  ·  site:tvnet.lv  ·  site:nra.lv  ·  site:la.lv
  - "${pol.name}" <topic>  for each likely topic
Collect candidate article URLs. FILTER OUT: tag/section/listing/search pages, paywalled-only stubs,
and pages not plausibly about this politician. Prefer URLs where the politician is the subject/speaker
and a publication date is establishable. Deduplicate. Cap at ${PER} best URLs.
${(SEED[pol.name] || SEED[pol.input] || []).length ? `Also INCLUDE these operator-supplied seed URLs: ${JSON.stringify(SEED[pol.name] || SEED[pol.input])}` : ''}
Return JSON {urls:[{url, why, guessedDate}]}. Empty list is a valid, honest answer — do not invent URLs.`,
      { label: `discover:${pol.name}`, phase: 'Discover', schema: DISCOVER_SCHEMA, agentType: 'Explore' }
    ).then((d) => ({ pol, urls: (d?.urls || []).slice(0, PER) })),

  // STAGE 2 — ingest (Bash -> ingest_url.py)
  (disc) => {
    if (!disc.urls.length) return { pol: disc.pol, ingest: null, linked_doc_ids: [] }
    const manifest = disc.urls
      .map((u) => JSON.stringify({ url: u.url, politician_id: disc.pol.id }))
      .join('\n')
    return agent(
      `Ingest historic articles for "${disc.pol.name}" (id ${disc.pol.id}).
1. Write this JSONL to a temp file (e.g. via Write to a path under the system temp or repo tmp/):
---MANIFEST---
${manifest}
---END---
2. Run: python scripts/ingest_url.py --manifest <that file>
3. Read stdout. Each RESULT_JSON: line is one URL's outcome; the final SUMMARY_JSON: line aggregates counts + linked_to{pid:[doc_ids]} + dateless[doc_ids].
Return JSON: summary_json = the raw SUMMARY_JSON payload (the JSON after "SUMMARY_JSON:");
linked_doc_ids = the doc_ids that linked to pid ${disc.pol.id} (summary linked_to["${disc.pol.id}"], may be empty);
dateless_doc_ids = summary dateless intersected with linked_doc_ids.
Do NOT publish, render, or deploy anything.`,
      { label: `ingest:${disc.pol.name}`, phase: 'Ingest', schema: INGEST_SCHEMA }
    ).then((ing) => ({ pol: disc.pol, ingest: ing, linked_doc_ids: ing?.linked_doc_ids || [] }))
  },

  // STAGE 3 — extract (@claim-extractor) — stated_at = published_at
  (ing) => {
    const ids = ing.linked_doc_ids || []
    if (!ids.length) return { pol: ing.pol, extract: { claim_ids: [], claims: [] } }
    return agent(
      `Extract pozīcijas for "${ing.pol.name}" (opponent_id ${ing.pol.id}) from these freshly-ingested HISTORIC document ids ONLY: ${JSON.stringify(ids)}.
For each doc read content + published_at from the DB (get_politician_documents returns published_at, or query documents directly).
CRITICAL HISTORIC RULE: set each claim's stated_at = that document's published_at (NOT today). These are old articles;
defaulting stated_at to scrape time would mis-date the claim and destroy the over-time contradiction signal.
Follow your normal @claim-extractor contract: claim_type='position', preserve Latvian diacritics, run the
indirect-reference self-check, and pass empty_doc_ids for every reviewed-but-empty doc. Call save_analysis exactly once.
Respect the 12-doc quality envelope; if more than 12 ids, process the highest-salience 12 and note the remainder.
Return JSON {claim_ids, claims:[{id,topic,stance,stated_at}], empty_doc_ids, failures}. Check result["failures"].`,
      { label: `extract:${ing.pol.name}`, phase: 'Extract', schema: EXTRACT_SCHEMA, agentType: 'claim-extractor' }
    ).then((ex) => ({ pol: ing.pol, extract: ex }))
  },

  // STAGE 4 — contradict (deep-check pattern, nested adversarial verify)
  async (ex) => {
    const newClaimIds = ex.extract?.claim_ids || []
    if (!newClaimIds.length) return { pol: ex.pol, candidates: 0, survivors: [] }
    const hunt = await agent(
      `You are @contradiction-hunter for "${ex.pol.name}" (opponent_id ${ex.pol.id}).
NEW historic claims just stored: ${JSON.stringify(ex.extract.claims || [])} (ids ${JSON.stringify(newClaimIds)}).
Compare these OLD positions against the politician's FULL existing claim history to surface contradictions
(old historic stance vs newer stance, and rhetoric-vs-saeima_vote action mismatches). Use search_similar_claims
with directional claim_type_filter at the 0.80 threshold. Apply ALL false-positive filters (coalition discipline >80%
faction, procedural votes, tactical blocking, different subtopic, legitimate evolution, role change, audience framing).
Output structured CANDIDATES only — do NOT store yet. For each: old_claim_id, new_claim_id, topic, proposed severity
(direct_contradiction|reversal|minor_shift), a Latvian summary, salience, and the journalist-test verdict.`,
      { label: `hunt:${ex.pol.name}`, phase: 'Contradict' }
    )
    // adversarial verification: each candidate refuted by @devils-advocate, survivors stored confirmed=0
    const stored = await agent(
      `You are @devils-advocate gating contradiction candidates for "${ex.pol.name}" (opponent_id ${ex.pol.id}).
Here are the @contradiction-hunter candidates:
${hunt}
For EACH candidate: open the source_urls, read the original context, and try to REFUTE it (coalition discipline,
procedural/whip context, journalist paraphrase mistaken for stance, combinable non-contradictory positions, insufficient
time gap). Keep ONLY robust survivors. For each survivor, store it:
  python -c "from src.tools import store_contradiction; print(store_contradiction(opponent_id=${ex.pol.id}, old_claim_id=OLD, new_claim_id=NEW, topic='T', summary='LV summary', severity='reversal', salience=0.5))"
store_contradiction defaults to confirmed=0 (UNPUBLISHED) — DO NOT set confirmed=1, DO NOT render or deploy.
Apply the LV grammar+stylistics gate to every stored summary. Return JSON {candidates:<int total reviewed>,
survivors:[{id, old_claim_id, new_claim_id, severity, summary}]} (id = the returned contradiction id).`,
      { label: `verify:${ex.pol.name}`, phase: 'Contradict', schema: CONTRADICT_SCHEMA }
    )
    return { pol: ex.pol, candidates: stored?.candidates || 0, survivors: stored?.survivors || [] }
  }
)

phase('Report')
const clean = results.filter(Boolean)
const report = clean.map((r) => ({
  politician: r.pol?.name,
  id: r.pol?.id,
  urls_found: r.urls?.length ?? (r.ingest ? undefined : undefined),
  linked_docs: (r.linked_doc_ids || []).length,
  new_claims: (r.extract?.claim_ids || []).length,
  candidates: r.candidates || 0,
  survivors: (r.survivors || []).map((s) => ({ id: s.id, severity: s.severity, summary: s.summary })),
}))

const totalSurvivors = report.reduce((n, r) => n + r.survivors.length, 0)
log(`Done. ${report.length} politicians, ${totalSurvivors} contradiction survivors stored confirmed=0.`)

return {
  scope: { since: SINCE, until: UNTIL, perPolitician: PER },
  report,
  next_steps:
    totalSurvivors > 0
      ? "Review confirmed=0 contradictions, UPDATE confirmed=1 the keepers, then: python -m src.render --only=pretrunas && deploy.sh --no-delete"
      : 'No survivors to publish. (0 is a valid outcome — see reference_contradiction_hunt_lessons.)',
}
```
```
```

> **Self-review note (done):** spec coverage — every spec deliverable maps to a task (CLI→T1-4, workflow→T5, runbook→T6, verification→T7); no placeholders (all code complete); type consistency — `ingest_one`/`ingest_manifest`/`parse_manifest`/`main` signatures and the `status` vocabulary (`ingested|already_present|dupe|thin|fetch_error`) match across tasks and the workflow's `INGEST_SCHEMA`.
