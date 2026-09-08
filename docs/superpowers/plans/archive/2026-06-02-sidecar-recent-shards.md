# Sidecar Recent-Shard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cap a typical visitor's balsojumi-matrix payload at a constant ~1 year of votes (a "recent" shard), fetching the full, ever-growing archive only when the user explicitly opens "Visa vēsture" or deep-links to an old vote.

**Architecture:** The render already emits one compact `balsojumi-matrica.json` consumed lazily by `assets/bmv1.js`. We add a second, smaller `balsojumi-matrica-recent.json` (votes within the last 400 days) produced by the *same* `_build_matrix_data` → `_emit_matrix_json` pipeline fed a date-filtered vote subset — so 0-based indexing, vote strings and dissents are correct for free. The client loads the recent file by default and fetches the full archive on demand. No schema change, no new infra. The full archive stays exactly as today (deep-links, hash nav, and any external reference keep working).

**Tech Stack:** Python 3.12 (`src/render/votes.py`), vanilla JS IIFE (`assets/bmv1.js`), Jinja2 template (`templates/balsojumi.html.j2`), pytest.

**Why this scope (simplest / fewest lines):** First-paint is already solved (balsojumi ships 76 KB brotli, matrix fetched lazily). The *only* unbounded-transfer item is that the lazy matrix ships the full vote history even for the 60-day default view. A recent shard is the minimal change that makes the default-view payload constant as history grows. Saites graph, immutable-archive cache headers, and DB log-pruning are deferred to Phase 2/3 (sketched at the bottom) — each is independently shippable.

---

## File Structure

- `src/render/votes.py` — MODIFY. Parametrize `_emit_matrix_json(..., basename=...)`; add `RECENT_WINDOW_DAYS`, `_recent_cutoff_iso()`, `_filter_recent_votes()`; emit the recent shard in `render_votes`.
- `tests/test_render_votes_matrix_json.py` — MODIFY. Add tests for basename param + recent filter.
- `assets/bmv1.js` — MODIFY. Accept `(root, recentSrc, fullSrc)`; lazy `ensureFullData`; route "Visa vēsture" and old-vote deep-links through it.
- `templates/balsojumi.html.j2:474` — MODIFY. Pass both srcs to `initBalsojumiMatrica`.

---

## Task 1: Server — parametrize the emitter

**Files:**
- Modify: `src/render/votes.py` (`_emit_matrix_json` signature + dest/log lines)
- Test: `tests/test_render_votes_matrix_json.py`

- [ ] **Step 1: Write failing test for basename param**

```python
def test_emit_matrix_json_custom_basename(tmp_path: Path, sample_matrix_data):
    dest = _emit_matrix_json(sample_matrix_data, tmp_path, basename="balsojumi-matrica-recent")
    assert dest == tmp_path / "data" / "balsojumi-matrica-recent.json"
    assert dest.exists()
    assert (tmp_path / "data" / "balsojumi-matrica-recent.json.br").exists()
    assert (tmp_path / "data" / "balsojumi-matrica-recent.json.gz").exists()
```

- [ ] **Step 2: Run it, verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_render_votes_matrix_json.py::test_emit_matrix_json_custom_basename -v`
Expected: FAIL (`_emit_matrix_json() got an unexpected keyword argument 'basename'`)

- [ ] **Step 3: Add the `basename` parameter**

In `src/render/votes.py`, change the signature and the three places that hard-code the filename:

```python
def _emit_matrix_json(
    matrix_data: dict[str, Any], atmina_dir: Path, basename: str = "balsojumi-matrica"
) -> Path:
    compact = _build_matrix_compact(matrix_data)
    data_dir = atmina_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    dest = data_dir / f"{basename}.json"
    payload = json.dumps(
        compact, ensure_ascii=False, separators=(",", ":"), default=str
    ).encode("utf-8")
    dest.write_bytes(payload)
    (data_dir / f"{basename}.json.br").write_bytes(_brotli.compress(payload, quality=11))
    (data_dir / f"{basename}.json.gz").write_bytes(_gzip.compress(payload, compresslevel=9))
    logger.info(
        "Wrote matrix JSON: %d votes × %d politicians → %s (%d raw, %d br, %d gz)",
        compact["meta"]["votes_total"], len(compact["politicians"]), dest,
        dest.stat().st_size,
        (data_dir / f"{basename}.json.br").stat().st_size,
        (data_dir / f"{basename}.json.gz").stat().st_size,
    )
    return dest
```

- [ ] **Step 4: Run the full matrix-json test module, verify green**

Run: `.venv/Scripts/python.exe -m pytest tests/test_render_votes_matrix_json.py -v`
Expected: PASS (existing default-basename tests still pass; new one passes)

- [ ] **Step 5: Commit**

```bash
git add src/render/votes.py tests/test_render_votes_matrix_json.py
git commit -F .git-commit-msg.tmp   # "feat(votes): parametrize matrix JSON basename for recent shard"
```

---

## Task 2: Server — emit the recent shard

**Files:**
- Modify: `src/render/votes.py` (module constants + `render_votes`)
- Test: `tests/test_render_votes_matrix_json.py`

- [ ] **Step 1: Write failing test for the recent filter**

```python
def test_filter_recent_votes_keeps_only_recent():
    from src.render.votes import _filter_recent_votes
    votes = [
        {"id": 1, "vote_date": "2020-01-01"},
        {"id": 2, "vote_date": "2099-01-01"},
        {"id": 3, "vote_date": None},
    ]
    kept = _filter_recent_votes(votes, "2026-01-01")
    assert [v["id"] for v in kept] == [2]   # future kept, old + null dropped
```

- [ ] **Step 2: Run it, verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_render_votes_matrix_json.py::test_filter_recent_votes_keeps_only_recent -v`
Expected: FAIL (`cannot import name '_filter_recent_votes'`)

- [ ] **Step 3: Add constants + helpers (top of `votes.py`, after `_VOTE_CHAR_MAP`)**

```python
# Recent-shard window. The matrix range buttons go up to "1 gads" (365 d), so the
# recent shard must cover ≥365 d; 400 gives a boundary buffer. The full archive
# (balsojumi-matrica.json) is fetched only for "Visa vēsture" / old-vote deep-links.
# Recent stays ~constant (~1 year of votes) as the archive grows — that is the point.
RECENT_WINDOW_DAYS = 400


def _recent_cutoff_iso(days: int = RECENT_WINDOW_DAYS) -> str:
    from datetime import date as _date
    return (_date.today() - timedelta(days=days)).isoformat()


def _filter_recent_votes(
    votes: list[dict[str, Any]], cutoff_iso: str
) -> list[dict[str, Any]]:
    """Keep votes whose vote_date (YYYY-MM-DD) is on/after cutoff. Null dates drop."""
    return [v for v in votes if str(v.get("vote_date") or "")[:10] >= cutoff_iso]
```

- [ ] **Step 4: Run the helper test, verify green**

Run: `.venv/Scripts/python.exe -m pytest tests/test_render_votes_matrix_json.py::test_filter_recent_votes_keeps_only_recent -v`
Expected: PASS

- [ ] **Step 5: Emit the recent shard in `render_votes`**

In `src/render/votes.py::render_votes`, replace the two existing emit lines:

```python
    matrix_data = _build_matrix_data(db, votes)
    _emit_matrix_json(matrix_data, atmina_dir)
```

with:

```python
    matrix_data = _build_matrix_data(db, votes)
    _emit_matrix_json(matrix_data, atmina_dir)  # full archive
    # Recent shard: same pipeline, date-filtered vote subset. Default client view
    # loads this; the full archive is fetched only on "Visa vēsture"/deep-link.
    recent_votes = _filter_recent_votes(votes, _recent_cutoff_iso())
    recent_matrix = _build_matrix_data(db, recent_votes)
    _emit_matrix_json(recent_matrix, atmina_dir, basename="balsojumi-matrica-recent")
```

- [ ] **Step 6: Integration test — both files emitted, recent ⊆ full**

```python
def test_render_votes_emits_recent_shard(tmp_path, monkeypatch):
    """render_votes writes both the full archive and the recent shard, and the
    recent shard has ≤ as many vote columns as the full archive."""
    import src.render.votes as V
    monkeypatch.setattr(V, "_build_matrix_data", lambda db, votes: {
        "votes": [{"id": v["id"], "date": v["vote_date"], "motif": "m",
                   "result": "Pieņemts", "topic": "", "total_par": 1, "total_pret": 0,
                   "total_atturas": 0, "faction_breakdown": [], "is_unanimous": True,
                   "time": ""} for v in votes],
        "factions": [], "politicians": {},
    })
    monkeypatch.setattr(V, "_render_page", lambda *a, **k: None)
    votes = [
        {"id": 1, "vote_date": "2099-06-01", "topic": "", "result": "Pieņemts",
         "tracked_votes": []},
        {"id": 2, "vote_date": "2000-01-01", "topic": "", "result": "Pieņemts",
         "tracked_votes": []},
    ]
    V.render_votes(env=None, db=None, atmina_dir=tmp_path, votes=votes, bills=[],
                   laws_index_count=0)
    import json
    full = json.loads((tmp_path / "data" / "balsojumi-matrica.json").read_text("utf-8"))
    recent = json.loads((tmp_path / "data" / "balsojumi-matrica-recent.json").read_text("utf-8"))
    assert full["meta"]["votes_total"] == 2
    assert recent["meta"]["votes_total"] == 1   # only the 2099 vote is within 400 d
```

- [ ] **Step 7: Run it, verify green**

Run: `.venv/Scripts/python.exe -m pytest tests/test_render_votes_matrix_json.py -v`
Expected: PASS (all)

- [ ] **Step 8: Commit**

```bash
git add src/render/votes.py tests/test_render_votes_matrix_json.py
git commit -F .git-commit-msg.tmp   # "feat(votes): emit balsojumi-matrica-recent.json (400-day shard)"
```

---

## Task 3: Client — load recent by default, fetch full on demand

**Files:**
- Modify: `assets/bmv1.js`
- Modify: `templates/balsojumi.html.j2:474`

- [ ] **Step 1: Add module state for the full archive**

In `assets/bmv1.js`, after `var DATA = null;` add:

```js
  var FULL_SRC = null;   // full-archive URL, fetched lazily
  var fullLoaded = false;
```

- [ ] **Step 2: Accept both srcs in the public entry point**

Change `window.initBalsojumiMatrica = function (root, dataSrc) {` to:

```js
  window.initBalsojumiMatrica = function (root, recentSrc, fullSrc) {
    if (initOnce) return;
    initOnce = true;
    ROOT = root;
    FULL_SRC = fullSrc || recentSrc;   // graceful if only one src is passed
    renderSkeleton();
    fetch(recentSrc, { credentials: "same-origin" })
```

(rest of the fetch chain unchanged — it already sets `DATA`, calls `renderShell()`, `applyHashScroll()`.)

- [ ] **Step 3: Add `ensureFullData` helper (after the entry point)**

```js
  // Fetch the full archive once, swap it into DATA, then run cb(). Used when the
  // user opens "Visa vēsture" or deep-links to a vote outside the recent shard.
  function ensureFullData(cb) {
    if (fullLoaded || !FULL_SRC) { cb(); return; }
    var info = document.getElementById("matrix-range-info");
    if (info) info.textContent = "Ielādē visu vēsturi…";
    fetch(FULL_SRC, { credentials: "same-origin" })
      .then(function (r) { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
      .then(function (json) { DATA = json; fullLoaded = true; cb(); })
      .catch(function (err) { renderError(err && err.message ? err.message : "nezināma kļūda"); });
  }
```

- [ ] **Step 4: Route "Visa vēsture" through `ensureFullData`**

Replace `function setRange(range) { ... }` with a thin router + the original body:

```js
  function setRange(range) {
    if (range === "all") { ensureFullData(function () { applyRange(range); }); return; }
    applyRange(range);
  }
  function applyRange(range) {
    STATE.range = range;
    STATE.confirmedAll = false;
    ROOT.querySelectorAll(".matrix-range-btn").forEach(function (b) {
      b.classList.toggle("active", String(b.dataset.range) === String(range));
    });
    render();
  }
```

- [ ] **Step 5: Make hash-nav resolve old votes via the full archive**

Replace `function applyHashScroll() { ... }` with:

```js
  function applyHashScroll() {
    if (!location.hash || location.hash.indexOf("#vote-") !== 0) return;
    var voteId = parseInt(location.hash.slice(6), 10);
    if (isNaN(voteId)) return;
    scrollToVid(voteId);
  }
  function scrollToVid(voteId) {
    for (var i = 0; i < DATA.votes.length; i++) {
      if (DATA.votes[i].vid === voteId) { revealVote(i); return; }
    }
    // Not in the recent shard → pull the full archive and retry once.
    if (!fullLoaded && FULL_SRC) {
      ensureFullData(function () { renderShell(); scrollToVid(voteId); });
    }
  }
  function revealVote(i) {
    var visIdx = computeVisibleVoteIndices();
    if (visIdx.indexOf(i) < 0) { STATE.range = "all"; STATE.confirmedAll = true; render(); }
    setTimeout(function () {
      showVoteDetail(i);
      var header = document.querySelector('.matrix-vote-header[data-vote-idx="' + i + '"]');
      if (header) header.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
    }, 50);
  }
```

- [ ] **Step 6: Update the template init call**

`templates/balsojumi.html.j2:474`, change:

```js
      window.initBalsojumiMatrica(root, 'data/balsojumi-matrica.json');
```

to:

```js
      window.initBalsojumiMatrica(root, 'data/balsojumi-matrica-recent.json', 'data/balsojumi-matrica.json');
```

- [ ] **Step 7: Render balsojumi only + manual verify both files referenced**

Run: `PYTHONPATH=. .venv/Scripts/python.exe scripts/render_balsojumi_only.py`
Then: confirm `output/atmina/data/balsojumi-matrica-recent.json` exists and is smaller than `balsojumi-matrica.json`; confirm `output/atmina/balsojumi.html` references `balsojumi-matrica-recent.json`.

- [ ] **Step 8: Commit**

```bash
git add assets/bmv1.js templates/balsojumi.html.j2
git commit -F .git-commit-msg.tmp   # "feat(balsojumi): client loads recent shard, lazy-fetches full archive"
```

---

## Task 4: Verify + REGEN char baselines

- [ ] **Step 1: REGEN char baselines** (template + asset hash changed balsojumi.html output)

Run: `REGEN=1 .venv/Scripts/python.exe -m pytest tests/test_render_chars.py -q`

- [ ] **Step 2: Full gate**

Run: `bash scripts/check.sh`
Expected: ruff clean, pytest green, render smoke OK.

- [ ] **Step 3: Commit baselines if changed**

```bash
git add tests/  && git commit -F .git-commit-msg.tmp   # "test: REGEN balsojumi char baseline after recent-shard wiring"
```

---

## Self-review notes

- Default view (60 d) and all range buttons up to "1 gads" (365 d) are fully served by the 400-day recent shard. Only "Visa vēsture" and deep-links to votes older than 400 d trigger the full fetch — exactly the rare, opt-in cases.
- `matrix-range-info` shows `DATA.meta.votes_total` = recent count until the full archive loads, then the true total. Cosmetic; acceptable. (If it ever matters, add `votes_grand_total` to meta — not now.)
- The confirm gate (`visIdx.length > 2000`) still fires on the genuinely huge full-history render, because the full archive is loaded *before* range="all" is applied.
- Build cost: a second `_build_matrix_data` (one extra full individual-votes query). Server-side, ~seconds — not a visitor concern.

---

## Phase 2 — saites sidecar split ✅ DONE 2026-06-02 (commit 39669dd)

Implemented as a **content split** (simpler than a recent-window shard, zero change to displayed data): `links.py::_emit_saites_json` parametrized with `basename`; `render_links` emits `saites-data.json` (claims + a `{pid: vote_count}` badge map, 214 KB br) loaded on first detail open, and `saites-votes.json` (the heavy `meta`+`byPid` ledger, 309 KB br) loaded only when a node's "Balsojumi" section opens. Common detail-open path drops 519 → 214 KB br; the fast-growing vote bulk is deferred off it. Verified in-browser (node open → only saites-data.json; Balsojumi open → saites-votes.json + 5182 cards render). saites char baseline REGEN'd via the spriedzes sibling (shared `render_baseline_graph.json`).

## Phase 3 — remaining (lower value; flagged for decision, NOT auto-implemented)

- **Immutable archive caching** — version the *full* archive filename by content hash + `Cache-Control: immutable`. **Assessment: low value-per-line right now** — the full archives (`balsojumi-matrica.json`, `saites-votes.json`) are fetched only on rare opt-in actions, and the hot files (`-recent` / `saites-data`) correctly keep the short cache. Defer until repeat-visit telemetry shows it matters.
- **Ops-DB hygiene** — prune `logs` (469K rows) older than N days + `VACUUM`. **Assessment: off-theme for this branch** — `logs` is read only by the ops dashboard (recent-windowed), NOT by the site build or render path, so it does not affect site transfer/build. It's ~90 MB DB housekeeping; worth doing as its own change, not mixed into the transfer-optimization branch.
