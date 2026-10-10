# Media Outlet Profiles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add even-handed, evidence-based media-outlet transparency profiles + descriptive coverage tracking to atmina.lv (`mediji.html` + `mediji/<slug>.html`).

**Architecture:** Config-driven, zero new DB tables. The outlet registry (identity + sourced transparency facts) extends `sources.yaml`; a thin reader (`src/outlets.py`) exposes outlets to the renderer; coverage is computed at render time from existing `documents` / `document_politicians` / `claims` via a host→outlet map, in single-pass queries. A new render module mirrors `src/render/parties.py`.

**Tech Stack:** Python 3.12, SQLite, Jinja2, PyYAML, existing `src/render` framework. Verify with `bash scripts/check.sh` (ruff + pytest + render smoke).

**Spec:** `docs/superpowers/specs/2026-06-01-media-outlet-profiles-design.md`

**Conventions:** UI language Latvian. Run Python via the venv (`.venv/Scripts/python.exe`) — bare `python` hits a broken Windows store stub. Set `$env:PYTHONIOENCODING='utf-8'` for any script printing Latvian. Commit only when the user asks (their standing rule) — the `git commit` steps below are written for completeness; batch and run them per the user's go-ahead.

---

## File Structure

- `src/schema.sql` — MODIFY: add the load-bearing `idx_social_accounts_unique` (Task 0, independent).
- `sources.yaml` — MODIFY: tag feeds with `outlet:`; add top-level `outlets:` registry block (Task 1).
- `src/outlets.py` — CREATE: read `sources.yaml` → outlet dicts; host→outlet map (Task 2).
- `src/render/mediji.py` — CREATE: coverage computation + `render_mediji` (Tasks 3–4).
- `templates/mediji.html.j2`, `templates/medijs.html.j2` — CREATE: index + detail (Task 5).
- `src/render/_orchestrator.py` — MODIFY: register `mediji` domain + sitemap (Task 6).
- `templates/base.html.j2` — MODIFY: nav link (Task 6).
- `.claude/agents/outlet-researcher.md` — CREATE: on-demand fact-research agent (Task 7).
- Tests: `tests/test_schema_social_unique.py`, `tests/test_outlets.py`, `tests/test_render_mediji.py`.

---

## Task 0: Schema fix — `idx_social_accounts_unique` (independent commit)

CLAUDE.md #11 treats `UNIQUE(opponent_id, platform, handle)` on `social_accounts` as load-bearing, but it is created only by `scripts/migrate_external_profiles.py`, so a fresh/test DB lacks it. Move it into the tracked schema.

**Files:**
- Modify: `src/schema.sql` (after the `idx_social_opponent` index line, ~line 247)
- Test: `tests/test_schema_social_unique.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_schema_social_unique.py
from src.db import init_db, get_db


def test_fresh_db_has_social_accounts_unique_index(tmp_path):
    db_path = str(tmp_path / "fresh.db")
    init_db(db_path)
    db = get_db(db_path)
    names = {r[0] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type='index' "
        "AND tbl_name='social_accounts'"
    ).fetchall()}
    db.close()
    assert "idx_social_accounts_unique" in names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_schema_social_unique.py -v`
Expected: FAIL — `idx_social_accounts_unique` not in names (init_db doesn't create it).

- [ ] **Step 3: Add the index to `src/schema.sql`**

Immediately after the existing `CREATE INDEX IF NOT EXISTS idx_social_opponent ON social_accounts(opponent_id);` line, add:

```sql
-- Load-bearing: store-social-account idempotency dedups on this triple
-- (CLAUDE.md #11). Previously created only by scripts/migrate_external_profiles.py,
-- so fresh/test DBs lacked it. Declared here so fresh + test DBs match prod.
CREATE UNIQUE INDEX IF NOT EXISTS idx_social_accounts_unique
    ON social_accounts(opponent_id, platform, handle);
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_schema_social_unique.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/schema.sql tests/test_schema_social_unique.py
git commit -m "fix: declare idx_social_accounts_unique in schema.sql (was prod-only)"
```

---

## Task 1: Outlet registry in `sources.yaml`

Establish the config registry: tag each scraper feed with its outlet, and add a top-level `outlets:` block with identity for every outlet. Transparency `facts:` start empty here — they are filled later, per-outlet, by `@outlet-researcher` (Task 7) with sourced values. This task is data only (no test; Task 2 tests the reader against it).

**Files:**
- Modify: `sources.yaml`

- [ ] **Step 1: Tag each feed with its outlet**

Add an `outlet: <short_name>` line to every active feed under `sources:`. Mapping:

| feed `name` | `outlet:` |
|---|---|
| LSM.lv Latvija, LSM.lv Ekonomika | `lsm` |
| Diena.lv Latvijā, Diena.lv Viedokļi | `diena` |
| TVNet RSS | `tvnet` |
| Delfi.lv | `delfi` |
| rus.Delfi.lv | `delfi-ru` |
| LETA | `leta` |
| Neatkarīgā, Neatkarīgā Viedokļi | `nra` |
| Latvijas Avīze | `la` |
| Jauns.lv | `jauns` |
| Latvijas Vēstnesis JL | `vestnesis` |

(Leave the `excluded` Instagram/TikTok/Bluesky rows untagged.)

- [ ] **Step 2: Add the `outlets:` block at the end of `sources.yaml`**

Full shape (two complete examples). `facts:` is intentionally empty for now:

```yaml
outlets:
  - short_name: lsm
    name: "Latvijas Sabiedriskie mediji (LSM)"
    type: public_tv
    language: lv
    hosts: ["lsm.lv"]
    x_handle: "ltvzinas"
    website: "https://www.lsm.lv"
    description: "Latvijas sabiedriskais medijs (LTV + Latvijas Radio kopējais ziņu portāls)."
    facts: []

  - short_name: nra
    name: "Neatkarīgā Rīta Avīze (nra.lv)"
    type: print
    language: lv
    hosts: ["nra.lv"]
    x_handle: "nralv"
    website: "https://nra.lv"
    description: "Latvijas dienas laikraksts un ziņu portāls."
    facts: []
```

Add one entry per remaining outlet, identity fields filled (facts empty):

| short_name | name | type | language | hosts | x_handle | website |
|---|---|---|---|---|---|---|
| `diena` | Diena | print | lv | `diena.lv` | | https://www.diena.lv |
| `tvnet` | TVNet | online | lv | `tvnet.lv` | | https://www.tvnet.lv |
| `delfi` | Delfi | online | lv | `delfi.lv` | | https://www.delfi.lv |
| `delfi-ru` | Delfi (krievu) | online | ru | `rus.delfi.lv` | | https://rus.delfi.lv |
| `leta` | LETA | agency | lv | `leta.lv` | `letanewslv` | https://www.leta.lv |
| `la` | Latvijas Avīze | print | lv | `la.lv`, `nasha.la.lv` | | https://www.la.lv |
| `jauns` | Jauns.lv | online | lv | `jauns.lv` | | https://jauns.lv |
| `vestnesis` | Latvijas Vēstnesis | agency | lv | `vestnesis.lv` | | https://www.vestnesis.lv |

(Optional X-only outlets without a web feed — TV3 Ziņas `tv3`, LTV De Facto, etc. — can be added later; v1 focuses on outlets with web coverage data.)

- [ ] **Step 3: Sanity-check YAML parses**

Run: `.venv/Scripts/python.exe -c "import yaml; d=yaml.safe_load(open('sources.yaml',encoding='utf-8')); print(len(d['outlets']),'outlets'); print(sum('outlet' in s for s in d['sources']),'tagged feeds')"`
Expected: prints `10 outlets` (or however many you added) and the count of tagged feeds (12).

- [ ] **Step 4: Commit**

```bash
git add sources.yaml
git commit -m "feat: add outlet registry + feed tags to sources.yaml"
```

---

## Task 2: Outlet reader — `src/outlets.py`

**Files:**
- Create: `src/outlets.py`
- Test: `tests/test_outlets.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_outlets.py
import textwrap
from src.outlets import load_outlets, host_to_outlet, OUTLET_FACT_FIELDS


def _write_yaml(tmp_path):
    p = tmp_path / "sources.yaml"
    p.write_text(textwrap.dedent("""
        sources:
          - url: "https://www.lsm.lv/rss/?lang=lv&catid=20"
            name: "LSM.lv Latvija"
            outlet: lsm
          - url: "https://www.lsm.lv/rss/?lang=lv&catid=22"
            name: "LSM.lv Ekonomika"
            outlet: lsm
          - url: "https://www.instagram.com"
            name: "Instagram"
        outlets:
          - short_name: lsm
            name: "LSM"
            type: public_tv
            language: lv
            hosts: ["www.lsm.lv", "lsm.lv"]
            website: "https://www.lsm.lv"
            description: "Public broadcaster."
            facts:
              - field: owner
                value: "Valsts"
                source_url: "https://example.org/lsm-owner"
                as_of: "2026-06-01"
              - field: funding_model
                value: "Valsts budžets"
                source_url: ""
                as_of: "2026-06-01"
          - short_name: nra
            name: "Neatkarīgā"
            type: print
            language: lv
            hosts: ["nra.lv"]
            facts: []
    """), encoding="utf-8")
    return p


def test_load_outlets_groups_feeds_and_normalizes_hosts(tmp_path):
    outlets = load_outlets(_write_yaml(tmp_path))
    by = {o["short_name"]: o for o in outlets}
    assert set(by) == {"lsm", "nra"}
    # hosts normalized (www. stripped) + de-duplicated to one
    assert by["lsm"]["hosts"] == ["lsm.lv"]
    # feed urls grouped under the outlet
    assert len(by["lsm"]["feed_urls"]) == 2
    # slug derived
    assert by["lsm"]["slug"] == "lsm"


def test_load_outlets_drops_unsourced_facts(tmp_path):
    by = {o["short_name"]: o for o in load_outlets(_write_yaml(tmp_path))}
    fields = [f["field"] for f in by["lsm"]["facts"]]
    # owner has a source_url -> kept; funding_model has empty source_url -> dropped
    assert fields == ["owner"]
    assert all(f["field"] in OUTLET_FACT_FIELDS for f in by["lsm"]["facts"])


def test_host_to_outlet_map(tmp_path):
    outlets = load_outlets(_write_yaml(tmp_path))
    m = host_to_outlet(outlets)
    assert m["lsm.lv"] == "lsm"
    assert m["nra.lv"] == "nra"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_outlets.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.outlets'`.

- [ ] **Step 3: Implement `src/outlets.py`**

```python
"""Read media-outlet definitions from sources.yaml.

Outlets are a config-driven entity (no DB table): the registry lives in
sources.yaml alongside the scraper source feeds. Each feed row may carry an
`outlet: <short_name>` tag grouping it under an outlet; outlet identity +
sourced transparency facts live in a top-level `outlets:` block.

Pure read — mirrors how sources.yaml already seeds the `sources` table.
Transparency facts without a source_url are dropped, mirroring the claims
"no source_url -> dropped" provenance rule (CLAUDE.md Data Contract #2).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

SOURCES_YAML = Path(__file__).resolve().parent.parent / "sources.yaml"

# Controlled vocabularies — symmetry: same field set for every outlet.
OUTLET_TYPES = ("public_tv", "private_tv", "radio", "print", "agency", "online")
OUTLET_FACT_FIELDS = (
    "owner", "funding_model", "legal_form", "editorial_leadership", "founded",
)


def _normalize_host(host: str) -> str:
    host = (host or "").strip().lower()
    return host[4:] if host.startswith("www.") else host


def load_outlets(path: str | Path = SOURCES_YAML) -> list[dict[str, Any]]:
    """Return outlets sorted by display name. Empty list if file/section absent."""
    p = Path(path)
    if not p.exists():
        return []
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}

    feeds_by_outlet: dict[str, list[str]] = {}
    for s in data.get("sources") or []:
        tag = s.get("outlet")
        if tag:
            feeds_by_outlet.setdefault(tag, []).append(s.get("url"))

    outlets: list[dict[str, Any]] = []
    for o in data.get("outlets") or []:
        short = o["short_name"]
        # de-dupe normalized hosts, preserving order
        seen: dict[str, None] = {}
        for h in (o.get("hosts") or []):
            nh = _normalize_host(h)
            if nh:
                seen.setdefault(nh, None)
        hosts = list(seen)
        facts = [
            {"field": f["field"], "value": f["value"],
             "source_url": f["source_url"], "as_of": f.get("as_of")}
            for f in (o.get("facts") or [])
            if f.get("field") in OUTLET_FACT_FIELDS and f.get("value") and f.get("source_url")
        ]
        outlets.append({
            "short_name": short,
            "slug": short.lower(),
            "name": o.get("name") or short,
            "type": o.get("type"),
            "language": o.get("language") or "lv",
            "hosts": hosts,
            "x_handle": o.get("x_handle"),
            "website": o.get("website"),
            "description": o.get("description") or "",
            "facts": facts,
            "feed_urls": feeds_by_outlet.get(short, []),
        })
    outlets.sort(key=lambda o: o["name"].lower())
    return outlets


def host_to_outlet(outlets: list[dict[str, Any]]) -> dict[str, str]:
    """Map normalized host -> outlet short_name."""
    m: dict[str, str] = {}
    for o in outlets:
        for h in o["hosts"]:
            m[h] = o["short_name"]
    return m
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_outlets.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add src/outlets.py tests/test_outlets.py
git commit -m "feat: src/outlets.py — read outlet registry from sources.yaml"
```

---

## Task 3: Coverage computation — `src/render/mediji.py` (data layer)

Compute per-outlet coverage in single-pass queries (no N+1), keyed by normalized host. Reuse the canonical audience-role exclusion set from `blog.py`.

**Files:**
- Create: `src/render/mediji.py` (data functions only this task)
- Test: `tests/test_render_mediji.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_render_mediji.py
from src.db import init_db, get_db
from src.render.mediji import _fetch_coverage, _cross_outlet_avg_party_share

OUTLETS = [
    {"short_name": "lsm", "slug": "lsm", "name": "LSM", "hosts": ["lsm.lv"],
     "type": "public_tv", "language": "lv", "x_handle": None, "website": None,
     "description": "", "facts": [], "feed_urls": []},
    {"short_name": "nra", "slug": "nra", "name": "Neatkarīgā", "hosts": ["nra.lv"],
     "type": "print", "language": "lv", "x_handle": None, "website": None,
     "description": "", "facts": [], "feed_urls": []},
]


def _seed(db_path):
    init_db(db_path)
    db = get_db(db_path)
    # two politicians of different parties + one audience (journalist) row
    db.execute("INSERT INTO tracked_politicians (id,name,party,relationship_type) VALUES (1,'A Kalns','JV','tracked')")
    db.execute("INSERT INTO tracked_politicians (id,name,party,relationship_type) VALUES (2,'B Lejas','NA','tracked')")
    db.execute("INSERT INTO tracked_politicians (id,name,party,relationship_type) VALUES (3,'TV3 Ziņas',NULL,'journalist')")
    # documents: 2 LSM (www + bare host), 1 NRA
    db.execute("INSERT INTO documents (id,content,content_hash,platform,source_domain,source_url,scraped_at) "
               "VALUES (10,'c1','h1','web','www.lsm.lv','https://www.lsm.lv/a','2026-05-30')")
    db.execute("INSERT INTO documents (id,content,content_hash,platform,source_domain,source_url,scraped_at) "
               "VALUES (11,'c2','h2','web','lsm.lv','https://lsm.lv/b','2026-05-31')")
    db.execute("INSERT INTO documents (id,content,content_hash,platform,source_domain,source_url,scraped_at) "
               "VALUES (12,'c3','h3','web','nra.lv','https://nra.lv/c','2026-05-29')")
    # links: doc10->A, doc11->A+B, doc12->B ; plus an audience link that must be excluded
    for d, p in [(10, 1), (11, 1), (11, 2), (12, 2), (10, 3)]:
        db.execute("INSERT INTO document_politicians (document_id,politician_id,role) VALUES (?,?, 'subject')", (d, p))
    # one claim on an LSM doc
    db.execute("INSERT INTO claims (opponent_id,document_id,topic,stance,claim_type,source_url,stated_at) "
               "VALUES (1,10,'Aizsardzība un drošība','x','position','https://www.lsm.lv/a','2026-05-30')")
    db.commit()
    return db


def test_fetch_coverage_volume_and_host_normalization(tmp_path):
    db = _seed(str(tmp_path / "t.db"))
    cov = _fetch_coverage(db, OUTLETS)
    assert cov["lsm"]["volume"] == 2   # www.lsm.lv + lsm.lv merged
    assert cov["nra"]["volume"] == 1


def test_fetch_coverage_excludes_audience_roles(tmp_path):
    db = _seed(str(tmp_path / "t.db"))
    cov = _fetch_coverage(db, OUTLETS)
    names = set(cov["lsm"]["by_politician"])
    assert "A Kalns" in names
    assert "TV3 Ziņas" not in names   # journalist role excluded


def test_fetch_coverage_by_party_and_topic(tmp_path):
    db = _seed(str(tmp_path / "t.db"))
    cov = _fetch_coverage(db, OUTLETS)
    # LSM: A(JV) in doc10+doc11 -> JV=2 distinct docs; B(NA) in doc11 -> NA=1
    assert cov["lsm"]["by_party"]["JV"] == 2
    assert cov["lsm"]["by_party"]["NA"] == 1
    assert cov["lsm"]["by_topic"]["Aizsardzība un drošība"] == 1


def test_cross_outlet_avg_party_share(tmp_path):
    db = _seed(str(tmp_path / "t.db"))
    cov = _fetch_coverage(db, OUTLETS)
    avg = _cross_outlet_avg_party_share(cov)
    # shares are fractions in [0,1]; JV present
    assert 0.0 <= avg.get("JV", 0) <= 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_render_mediji.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.render.mediji'`.

- [ ] **Step 3: Implement the data layer in `src/render/mediji.py`**

```python
"""Render the Mediji (media outlets) pages.

Outlets are config-driven (src/outlets.py reads sources.yaml) — there is no
outlets DB table. Coverage is computed at render time from existing documents/
document_politicians/claims, grouped by outlet via a normalized host map, in
single-pass queries (NOT per-outlet N+1 — mirrors the anti-N+1 discipline in
src/render/blog.py::_compute_brief_footers).

Descriptive only: counts + shares, every figure derived from data. No tone,
no labels (see docs/superpowers/specs/2026-06-01-media-outlet-profiles-design.md).
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from jinja2 import Environment

from src.outlets import host_to_outlet
from src.render._common import _render_page, _slugify
# Canonical audience/non-first-party roles excluded from "who an outlet covers".
from src.render.blog import _FOOTER_POSITION_EXCLUDED_ROLES

# Normalized host expression (strip leading www.) for grouping documents.
_NORM = ("CASE WHEN d.source_domain LIKE 'www.%' THEN substr(d.source_domain, 5) "
         "ELSE lower(d.source_domain) END")


def _empty_cov() -> dict[str, Any]:
    return {"volume": 0, "by_politician": {}, "by_party": {}, "by_topic": {}, "recent": []}


def _fetch_coverage(db: sqlite3.Connection,
                    outlets: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Per-outlet coverage aggregates, keyed by short_name. Single-pass queries."""
    h2o = host_to_outlet(outlets)
    cov = {o["short_name"]: _empty_cov() for o in outlets}
    hosts = tuple(h2o)
    if not hosts:
        return cov
    hp = ",".join("?" * len(hosts))
    excl = _FOOTER_POSITION_EXCLUDED_ROLES
    ep = ",".join("?" * len(excl))

    # Volume per outlet
    for host, n in db.execute(
        f"SELECT {_NORM} h, COUNT(*) FROM documents d "
        f"WHERE d.platform='web' AND {_NORM} IN ({hp}) GROUP BY h", hosts):
        cov[h2o[host]]["volume"] += n

    # Who they cover + by party (one pass; DISTINCT docs per politician)
    for host, name, party, c in db.execute(
        f"""SELECT {_NORM} h, tp.name, tp.party, COUNT(DISTINCT d.id)
            FROM documents d
            JOIN document_politicians dp ON dp.document_id = d.id
            JOIN tracked_politicians tp ON tp.id = dp.politician_id
            WHERE d.platform='web' AND {_NORM} IN ({hp})
              AND tp.relationship_type NOT IN ({ep})
            GROUP BY h, tp.id""", (*hosts, *excl)):
        o = cov[h2o[host]]
        o["by_politician"][name] = {"party": party, "count": c, "slug": _slugify(name)}
        if party:
            o["by_party"][party] = o["by_party"].get(party, 0) + c

    # Top topics (via claims on the outlet's web docs)
    for host, topic, n in db.execute(
        f"""SELECT {_NORM} h, c.topic, COUNT(*)
            FROM claims c JOIN documents d ON d.id = c.document_id
            WHERE d.platform='web' AND {_NORM} IN ({hp}) AND c.claim_type='position'
            GROUP BY h, c.topic""", hosts):
        cov[h2o[host]]["by_topic"][topic] = n

    # Recent articles (top 5 per outlet) — newest first, bucketed in Python
    db.row_factory = sqlite3.Row
    rows = db.execute(
        f"""SELECT {_NORM} h, d.source_url AS url, d.content AS content,
                   d.scraped_at AS scraped_at
            FROM documents d
            WHERE d.platform='web' AND {_NORM} IN ({hp})
            ORDER BY d.scraped_at DESC""", hosts).fetchall()
    for r in rows:
        bucket = cov[h2o[r["h"]]]["recent"]
        if len(bucket) < 5:
            text = (r["content"] or "").replace("\n", " ").strip()
            bucket.append({
                "url": r["url"],
                "title": text[:90] + ("..." if len(text) > 90 else ""),
                "date": (r["scraped_at"] or "")[:10],
            })
    return cov


def _cross_outlet_avg_party_share(cov: dict[str, dict[str, Any]]) -> dict[str, float]:
    """Mean per-party coverage share across outlets (reference line for the
    per-outlet share, so incumbency isn't misread as bias). Share = party's
    tag-count / outlet's total party tags."""
    shares: dict[str, list[float]] = {}
    for o in cov.values():
        total = sum(o["by_party"].values())
        if not total:
            continue
        for party, c in o["by_party"].items():
            shares.setdefault(party, []).append(c / total)
    n_outlets = sum(1 for o in cov.values() if sum(o["by_party"].values()) > 0) or 1
    # average over ALL covering outlets (absent party counts as 0 share)
    return {p: sum(v) / n_outlets for p, v in shares.items()}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_render_mediji.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add src/render/mediji.py tests/test_render_mediji.py
git commit -m "feat: media-outlet coverage computation (single-pass, host-keyed)"
```

---

## Task 4: Render functions — `src/render/mediji.py` (`render_mediji`)

Add the page-assembly + write functions to the module from Task 3.

**Files:**
- Modify: `src/render/mediji.py`
- Test: `tests/test_render_mediji.py` (append)

- [ ] **Step 1: Write the failing test (append)**

```python
# append to tests/test_render_mediji.py
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from src.render.mediji import render_mediji


def _env():
    return Environment(
        loader=FileSystemLoader("templates"),
        autoescape=select_autoescape(["html", "j2"]),
    )


def test_render_mediji_writes_index_and_detail(tmp_path):
    db = _seed(str(tmp_path / "t.db"))
    out = tmp_path / "site"
    out.mkdir()
    render_mediji(_env(), db, out, OUTLETS)
    assert (out / "mediji.html").exists()
    assert (out / "mediji" / "lsm.html").exists()
    assert (out / "mediji" / "nra.html").exists()
    html = (out / "mediji" / "lsm.html").read_text(encoding="utf-8")
    assert "LSM" in html
```

(Note: this test depends on the templates from Task 5; run it after Task 5's templates exist. Until then it fails at template lookup — expected.)

- [ ] **Step 2: Implement `_outlet_detail` + `render_mediji` (append to `src/render/mediji.py`)**

```python
def _party_shares(by_party: dict[str, int]) -> list[dict[str, Any]]:
    total = sum(by_party.values()) or 1
    rows = [{"party": p, "count": c, "share": c / total}
            for p, c in by_party.items()]
    rows.sort(key=lambda r: r["count"], reverse=True)
    return rows


def _top(d: dict, n: int) -> list[dict[str, Any]]:
    return sorted(
        ({"key": k, **(v if isinstance(v, dict) else {"count": v})}
         for k, v in d.items()),
        key=lambda r: r["count"], reverse=True,
    )[:n]


def _outlet_detail(outlet: dict[str, Any], cov: dict[str, Any],
                   avg_share: dict[str, float]) -> dict[str, Any]:
    party_rows = _party_shares(cov["by_party"])
    for r in party_rows:
        r["avg_share"] = avg_share.get(r["party"], 0.0)
    return {
        "volume": cov["volume"],
        "top_politicians": _top(cov["by_politician"], 12),
        "party_rows": party_rows,
        "top_topics": _top(cov["by_topic"], 10),
        "recent": cov["recent"],
    }


def render_mediji(env: Environment, db: sqlite3.Connection, atmina_dir: Path,
                  outlets: list[dict[str, Any]]) -> None:
    """Emit mediji.html (index) + mediji/<slug>.html per outlet.

    Mirrors src/render/parties.py::render_parties. Coverage computed once for
    all outlets, then sliced per page."""
    cov = _fetch_coverage(db, outlets)
    avg_share = _cross_outlet_avg_party_share(cov)

    index_rows = [{
        **o,
        "volume": cov[o["short_name"]]["volume"],
        "top_party": (_party_shares(cov[o["short_name"]]["by_party"]) or [{}])[0].get("party"),
    } for o in outlets]

    _render_page(env, "mediji.html.j2", atmina_dir / "mediji.html", {
        "outlets": index_rows,
        "metrics": {"total": len(outlets),
                    "total_articles": sum(c["volume"] for c in cov.values())},
    })

    mediji_dir = atmina_dir / "mediji"
    mediji_dir.mkdir(parents=True, exist_ok=True)
    for o in outlets:
        detail = _outlet_detail(o, cov[o["short_name"]], avg_share)
        _render_page(env, "medijs.html.j2", mediji_dir / f"{o['slug']}.html", {
            "outlet": o,
            **detail,
        })
```

- [ ] **Step 3: (Deferred) run after Task 5 templates exist**

Run: `.venv/Scripts/python.exe -m pytest tests/test_render_mediji.py::test_render_mediji_writes_index_and_detail -v`
Expected: PASS once Task 5 templates exist.

- [ ] **Step 4: Commit**

```bash
git add src/render/mediji.py tests/test_render_mediji.py
git commit -m "feat: render_mediji index + detail assembly"
```

---

## Task 5: Templates — `mediji.html.j2` + `medijs.html.j2`

Mirror `partijas.html.j2` / `partija.html.j2`. Read those two files first to match the project's card/section markup and CSS classes; the markup below is the required structure.

**Files:**
- Create: `templates/mediji.html.j2`
- Create: `templates/medijs.html.j2`

- [ ] **Step 1: Create `templates/mediji.html.j2` (index)**

```jinja
{% extends "base.html.j2" %}
{% set active_page = "mediji" %}
{% block title %}Mediji — Politiskā atmiņa{% endblock %}
{% block content %}
<section class="section">
  <h1>Mediji</h1>
  <p class="section-intro">Mediju caurskatāmība: īpašnieki, finansējums un faktiskais
     politiskais pārklājums — aprēķināts no atmina datiem. {{ metrics.total }} mediji,
     {{ metrics.total_articles }} raksti.</p>
  <div class="card-grid">
    {% for o in outlets %}
    <a class="card" href="mediji/{{ o.slug }}.html">
      <h3>{{ o.name }}</h3>
      <div class="card-meta">{{ o.type or '' }} · {{ o.language|upper }}</div>
      <div class="card-stats">
        <span><b>{{ o.volume }}</b> raksti</span>
        {% if o.top_party %}<span>visvairāk: {{ o.top_party }}</span>{% endif %}
      </div>
    </a>
    {% endfor %}
  </div>
</section>
{% endblock %}
```

- [ ] **Step 2: Create `templates/medijs.html.j2` (detail)**

```jinja
{% extends "base.html.j2" %}
{% set active_page = "mediji" %}
{% block title %}{{ outlet.name }} — Mediji — Politiskā atmiņa{% endblock %}
{% block content %}
<section class="section">
  <a href="../mediji.html" class="brief-back">&larr; Visi mediji</a>
  <h1>{{ outlet.name }}</h1>
  <div class="card-meta">{{ outlet.type or '' }} · {{ outlet.language|upper }}
    {% if outlet.website %} · <a href="{{ outlet.website }}" target="_blank" rel="noopener">mājaslapa</a>{% endif %}
    {% if outlet.x_handle %} · <a href="https://x.com/{{ outlet.x_handle }}" target="_blank" rel="noopener">@{{ outlet.x_handle }}</a>{% endif %}
  </div>
  {% if outlet.description %}<p>{{ outlet.description }}</p>{% endif %}

  <h2>Caurskatāmība</h2>
  {% if outlet.facts %}
  <table class="data-table">
    <tbody>
    {% for f in outlet.facts %}
      <tr>
        <th>{{ f.field }}</th>
        <td>{{ f.value }} <a href="{{ f.source_url }}" target="_blank" rel="noopener" class="source-link">avots</a>
          {% if f.as_of %}<span class="muted">({{ f.as_of }})</span>{% endif %}</td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
  {% else %}
  <p class="muted">Caurskatāmības dati vēl nav apkopoti šim medijam.</p>
  {% endif %}

  <h2>Pārklājums — {{ volume }} raksti</h2>
  <p class="muted">Aprakstoši dati no atmina dokumentiem. Viens raksts var pieminēt
     vairākas partijas, tāpēc daļas summējas pāri 100%.</p>

  <h3>Visvairāk atspoguļotie politiķi</h3>
  <ul>
    {% for p in top_politicians %}
    <li><a href="../personas/{{ p.slug }}.html">{{ p.key }}</a>
        {% if p.party %}({{ p.party }}){% endif %} — {{ p.count }}</li>
    {% endfor %}
  </ul>

  <h3>Pārklājums pa partijām</h3>
  <table class="data-table">
    <thead><tr><th>Partija</th><th>Raksti</th><th>Daļa</th><th>Vidēji (visi mediji)</th></tr></thead>
    <tbody>
    {% for r in party_rows %}
      <tr>
        <td>{{ r.party }}</td>
        <td>{{ r.count }}</td>
        <td>{{ (r.share * 100)|round(0)|int }}%</td>
        <td class="muted">{{ (r.avg_share * 100)|round(0)|int }}%</td>
      </tr>
    {% endfor %}
    </tbody>
  </table>

  <h3>Biežākās tēmas</h3>
  <ul>
    {% for t in top_topics %}<li>{{ t.key }} — {{ t.count }}</li>{% endfor %}
  </ul>

  <h3>Jaunākie raksti</h3>
  <ul>
    {% for a in recent %}
    <li><a href="{{ a.url }}" target="_blank" rel="noopener">{{ a.title }}</a>
        <span class="muted">{{ a.date }}</span></li>
    {% endfor %}
  </ul>
</section>
{% endblock %}
```

- [ ] **Step 3: Run the deferred render test from Task 4**

Run: `.venv/Scripts/python.exe -m pytest tests/test_render_mediji.py -v`
Expected: PASS (all tests, including `test_render_mediji_writes_index_and_detail`).

- [ ] **Step 4: Commit**

```bash
git add templates/mediji.html.j2 templates/medijs.html.j2 tests/test_render_mediji.py
git commit -m "feat: mediji index + detail templates"
```

---

## Task 6: Wire into the orchestrator + nav + sitemap

**Files:**
- Modify: `src/render/_orchestrator.py`
- Modify: `templates/base.html.j2`
- Test: `tests/test_render_mediji.py` (append an orchestrator smoke test)

- [ ] **Step 1: Add the nav link in `templates/base.html.j2`**

After the `partijas.html` nav `<a>` (line ~45), add:

```jinja
        <a href="{{ assets_prefix }}mediji.html"{% if active_page == "mediji" %} class="active"{% endif %}>Mediji</a>
```

- [ ] **Step 2: Register the domain in `src/render/_orchestrator.py`**

a) Near the other render imports (~line 60):

```python
from src.outlets import load_outlets
from src.render.mediji import render_mediji
```

b) Add `"mediji"` to the `KNOWN_DOMAINS` frozenset (~line 72), after `"partijas"`:

```python
    "mediji",        # mediji.html + mediji/<slug>.html
```

c) Where `parties = _fetch_parties_page(db)` is fetched (~line 320), add:

```python
    outlets = load_outlets()
```

d) After the `if _want("partijas"): render_parties(...)` block (~line 380):

```python
    if _want("mediji"):
        render_mediji(env, db, atmina_dir, outlets)
```

e) Update the console summary line (~line 481) to include `mediji`, and add a `mediji/` summary line near the `partijas/` one (~line 483):

```python
    print(f"  mediji/: {len(outlets)} media outlet pages")
```

f) Sitemap: add `"mediji.html"` to the top-level pages list (~line 509), and after the per-party URL loop (~line 523) add:

```python
        for o in outlets:
            urls.append(f"{BASE_URL}/mediji/{o['slug']}.html")
```

- [ ] **Step 3: Write the orchestrator smoke test (append to `tests/test_render_mediji.py`)**

```python
def test_orchestrator_knows_mediji_domain():
    from src.render._orchestrator import KNOWN_DOMAINS
    assert "mediji" in KNOWN_DOMAINS
```

- [ ] **Step 4: Run the targeted render smoke**

Run: `.venv/Scripts/python.exe -m pytest tests/test_render_mediji.py -v`
Expected: PASS.

Then a live partial render:
Run: `.venv/Scripts/python.exe -c "from src.render import generate_public_site; generate_public_site(only={'mediji'})"`
Expected: writes `output/atmina/mediji.html` + `output/atmina/mediji/<slug>.html`; no errors.

- [ ] **Step 5: Full verification**

Run: `bash scripts/check.sh`
Expected: ruff clean; pytest green (no NEW failures vs baseline); render smoke OK.

- [ ] **Step 6: Commit**

```bash
git add src/render/_orchestrator.py templates/base.html.j2 tests/test_render_mediji.py
git commit -m "feat: register mediji domain + nav + sitemap"
```

---

## Task 7: `@outlet-researcher` agent prompt

On-demand agent that proposes a sourced `outlets:` entry for one outlet, for human review as a YAML diff. No DB writes, no automation.

**Files:**
- Create: `.claude/agents/outlet-researcher.md`

- [ ] **Step 1: Create `.claude/agents/outlet-researcher.md`**

Read an existing agent (e.g. `.claude/agents/mentions-monitor.md`) first to match the frontmatter format. Content:

```markdown
---
name: outlet-researcher
description: Research one media outlet's transparency facts (ownership, funding, legal form, editorial leadership, founding) and propose a sourced sources.yaml `outlets:` entry for human review. On-demand, one outlet at a time.
---

You research ONE Latvian media outlet and propose its transparency profile as a
`sources.yaml` `outlets:` YAML entry. You do not write to the database and you do
not run unattended.

## Input
Outlet name, website, and (if known) X handle.

## Research these fields (and ONLY these)
- owner — controlling owner/parent (use the corporate registry: ur.gov.lv,
  Lursoft, Firmas.lv; for public broadcasters, the governing law/body)
- funding_model — e.g. "Valsts budžets" (public), "Reklāma + abonēšana" (private)
- legal_form — legal entity type (SIA, AS, nodibinājums, valsts iestāde, …)
- editorial_leadership — current editor-in-chief / responsible editor
- founded — founding year

## Hard rules
- NEUTRAL, DESCRIPTIVE language only. No characterization of coverage quality,
  bias, or motive — that is the computed coverage section's job, not yours.
- The SAME fields for EVERY outlet, regardless of perceived political lean
  (symmetry is the whole point).
- EVERY fact needs a `source_url`. If you cannot source a fact, OMIT it — do not
  guess. (Mirrors the platform's "no claim without source_url" rule.)
- Set `as_of` to today's date for each fact.

## Output (propose, do not apply)
Emit a YAML block to be reviewed and pasted into `sources.yaml` under `outlets:`:

    - short_name: <slug>
      name: "<display name>"
      type: <public_tv|private_tv|radio|print|agency|online>
      language: <lv|ru|lv,ru>
      hosts: ["<host>"]
      x_handle: "<handle or omit>"
      website: "<url>"
      description: "<one neutral sentence>"
      facts:
        - field: owner
          value: "<...>"
          source_url: "<...>"
          as_of: "<YYYY-MM-DD>"
        # ...one entry per sourced field...

Then summarize which fields you could NOT source, so the human knows the gaps.
```

- [ ] **Step 2: Verify it loads (lint the frontmatter)**

Run: `.venv/Scripts/python.exe -c "import pathlib,yaml; t=pathlib.Path('.claude/agents/outlet-researcher.md').read_text(encoding='utf-8'); fm=t.split('---')[1]; print(yaml.safe_load(fm)['name'])"`
Expected: prints `outlet-researcher`.

- [ ] **Step 3: Commit**

```bash
git add .claude/agents/outlet-researcher.md
git commit -m "feat: @outlet-researcher agent prompt (on-demand, sourced YAML proposals)"
```

---

## Task 8 (optional, last): "Media landscape" overview + cross-links

Descriptive-safe polish. Only do this after Tasks 0–7 are green.

**Files:**
- Modify: `src/graphics/` (new `landscape_chart.py` mirroring `src/graphics/weekly_chart.py`)
- Modify: `src/render/mediji.py` (emit the SVG, reference it from `mediji.html.j2`)
- Modify: politician/party templates (add "most-covering outlets" cross-link) — optional follow-up.

- [ ] **Step 1:** Mirror `src/graphics/weekly_chart.py` to produce a deterministic horizontal-bar SVG of outlets by article volume (`make_landscape_svg(outlets_with_volume) -> bytes`), with intrinsic `width`/`height` attributes (per the SVG-in-`<img>` fix already applied to weekly_chart). Write a wellformed-SVG test like `tests/test_weekly_chart.py`.
- [ ] **Step 2:** In `render_mediji`, write the SVG to `atmina_dir/images/briefs/mediji-landscape.svg` and reference it from `mediji.html.j2`.
- [ ] **Step 3:** Run `bash scripts/check.sh`; commit.

---

## Self-Review (completed by plan author)

- **Spec coverage:** registry→Task 1/2; coverage (descriptive, single-pass, shares + cross-outlet avg, role-exclusion, src.coalition note)→Task 3/4; rendering+nav+sitemap→Task 5/6; `@outlet-researcher`→Task 7; schema fix→Task 0; landscape/cross-links→Task 8. Framing-internal honored (no framing field rendered). No migration, no new DB tables — honored.
- **Placeholder scan:** none — every code/test step shows complete code; the only "fill in" is outlet *data* (Task 1 table) and researched *facts* (Task 7), which is content by design, not logic.
- **Type consistency:** `load_outlets`→dicts with `short_name/slug/name/type/language/hosts/x_handle/website/description/facts/feed_urls`; `host_to_outlet`; `_fetch_coverage`→`{short_name:{volume,by_politician,by_party,by_topic,recent}}`; `_cross_outlet_avg_party_share`→`{party:share}`; `_outlet_detail`→`{volume,top_politicians,party_rows,top_topics,recent}`. Names consistent across tasks and templates.
- **Coalition note:** v1 shows party shares only (no coalition split), so `src.coalition` is not yet needed; if a coalition split is added later it MUST go through `src.coalition.party_status()` (recorded in spec Open items).
- **Coverage join key:** uses `documents.source_domain` (normalized) — robust and validated; `source_id` join left as a future optimization (spec).
