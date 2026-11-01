"""Characterization tests for src.render sub-page rendering.

Phase F3 refactor safety net: snapshots SHA-256 hashes of selected
output/atmina/*.html files. Tests assert that rendered bytes are identical
to the committed baselines.

Source of truth: tests render the COMMITTED fixture DB
(tests/fixtures/render_fixture_data.sql, built by scripts/build_render_fixture.py)
under a frozen clock (FREEZE_INSTANT), NOT the live data/atmina.db. Baselines
therefore change ONLY when render code changes — daily ingest no longer drifts
them. statistika.html renders from the committed data/csp.db + data/events.yaml
snapshot, and the likumi pages from a static law catalog, so those are stable
too. To intentionally change coverage: rerun the builder, then
``REGEN=1 pytest tests/test_render_chars.py``, then commit fixture + baselines.

Coverage by phase:
- F3a (PR #5): pretrunas.html + 12 pretrunas/<id>.html detail pages →
  tests/fixtures/render_baseline_contradictions.json
- F3b (PR #7): personas.html (the politician/persona index page;
  there is no separate politiki.html — Personas is the index) + 159
  politiki/<slug>.html detail pages →
  tests/fixtures/render_baseline_politicians.json
- F3c (PR #8): partijas.html + 15 partijas/<short>.html detail pages →
  tests/fixtures/render_baseline_parties.json
- F3d (PR #9): pozicijas.html + zinas.html + statistika.html + 10
  statistika/<id>.html detail pages →
  tests/fixtures/render_baseline_misc.json
- F3e (PR #10): balsojumi.html + ~151 likumprojekti/<slug>.html +
  likumi.html + ~33 likumi/<slug>.html →
  tests/fixtures/render_baseline_bills.json + render_baseline_laws.json
- F3f.2 (PR #12): x.html (Twitter/X feed page) →
  tests/fixtures/render_baseline_x.json
- F3f.3 (PR #13): spriedzes.html + saites.html →
  tests/fixtures/render_baseline_graph.json
- F3f.5 (PR #14): analizes.html (combined index — orchestrator-owned)
  + analizes/<slug>.html (per-analysis pages) +
  sintezes/<slug>.html (per-synthesis pages) →
  tests/fixtures/render_baseline_analyses.json
- F3f.4 (PR #15): blog.html (index) + blog/<slug>.html
  (~25 daily/weekly briefs, dynamic count) →
  tests/fixtures/render_baseline_blog.json. ⚠️ Dynamic count means
  REGEN after every blog ingest cycle (similar to likumprojekti F3e).
- F3f.1 (this phase): index.html (homepage hero + sparklines + ticker
  + trends) + analizes.html (combined index for analyses + syntheses
  + blog posts + trends + context_notes) →
  tests/fixtures/render_baseline_dashboard.json. analizes.html SHA
  is also captured in render_baseline_analyses.json (F3f.5) — both
  fixtures assert; F3g cleanup pass will dedupe.

Refactor invariant: each F3 sub-phase preserves observable HTML output,
not changes it. If a code change intentionally alters output, regenerate
the baseline via ``REGEN=1 pytest tests/test_render_chars.py`` (writes
the new observed hashes as the new frozen expected). Without REGEN,
mismatches fail.

Determinism: ``ATMINA_ASSETS_VERSION`` is forced to ``"test"`` so the
``?v=`` cache-bust query stays stable across worktrees and machines.
Resolved by ``src.render._common._resolve_assets_version``. Without
this override the baseline drifts every time ``assets/style.css`` or
``assets/pzv1.js`` is touched (cp -p in a fresh checkout, deploy,
fmt run, …).

Note for future char-fixture authors (F3b–F3g): the override is
SESSION-SCOPED — once ``_stable_assets_version`` runs, every
subsequent test in the same pytest invocation also sees
``ATMINA_ASSETS_VERSION="test"``. That is intentional (all render
char tests want the same stable version). If a future test needs a
different pin, give it its own session-scoped fixture using the same
``_pytest.monkeypatch.MonkeyPatch`` pattern AFTER ``_stable_assets_version``
completes, or run that test in its own pytest session.

Performance: a single session-scoped fixture runs generate_public_site()
once into a tmp output_dir; both tests share that output. Adds ~30s to
pytest. Read-only — does not mutate DB or master output/.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

import pytest


FIXTURES = Path(__file__).parent / "fixtures"
EXPECTED_FILE = FIXTURES / "render_baseline_contradictions.json"
EXPECTED_FILE_POLITICIANS = FIXTURES / "render_baseline_politicians.json"
EXPECTED_FILE_PARTIES = FIXTURES / "render_baseline_parties.json"
EXPECTED_FILE_MISC = FIXTURES / "render_baseline_misc.json"
EXPECTED_FILE_BILLS = FIXTURES / "render_baseline_bills.json"
EXPECTED_FILE_LAWS = FIXTURES / "render_baseline_laws.json"
EXPECTED_FILE_X = FIXTURES / "render_baseline_x.json"
EXPECTED_FILE_GRAPH = FIXTURES / "render_baseline_graph.json"
EXPECTED_FILE_ANALYSES = FIXTURES / "render_baseline_analyses.json"
EXPECTED_FILE_BLOG = FIXTURES / "render_baseline_blog.json"
EXPECTED_FILE_DASHBOARD = FIXTURES / "render_baseline_dashboard.json"


def _sha(p: Path) -> str:
    # Normalize CRLF→LF so the hash is platform-independent. Path.write_text()
    # (the render's output path) emits \r\n on Windows — where these baselines
    # are regenerated — and \n on Linux (CI). Hashing raw bytes would make the
    # baseline never match across platforms; the page content is identical.
    return hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


# Fikstūras `_stable_assets_version`, `render_fixture_db`, `rendered_site` dzīvo
# tests/conftest.py (2026-10-21): viena fikstūras vietne uz sesiju visiem
# moduļiem, ne pa vienai katram importētājam.


def _capture_observed(atmina_dir: Path) -> dict:
    pretrunas_index = atmina_dir / "pretrunas.html"
    detail_dir = atmina_dir / "pretrunas"
    detail_files = sorted(
        detail_dir.glob("*.html"),
        key=lambda p: int(p.stem),
    )
    return {
        "pretrunas.html": _sha(pretrunas_index),
        "pretrunas_detail": {p.name: _sha(p) for p in detail_files},
    }


def _capture_observed_politicians(atmina_dir: Path) -> dict:
    personas_index = atmina_dir / "personas.html"
    detail_dir = atmina_dir / "politiki"
    # Slug names are Latvian transliterations like "krisjanis-karins".
    # Sort lexicographically — stable across runs.
    detail_files = sorted(detail_dir.glob("*.html"), key=lambda p: p.name)
    return {
        "personas.html": _sha(personas_index),
        "politiki_detail": {p.name: _sha(p) for p in detail_files},
    }


def _load_expected(path: Path) -> dict:
    if not path.exists():
        pytest.fail(
            f"Expected fixture {path} missing. "
            "Bootstrap with REGEN=1 pytest tests/test_render_chars.py."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def test_pretrunas_index_byte_identical(rendered_site):
    observed = _capture_observed(rendered_site)
    if os.environ.get("REGEN") == "1":
        EXPECTED_FILE.write_text(
            json.dumps(observed, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
        )
        pytest.skip("Regenerated baseline — re-run without REGEN to assert.")
    expected = _load_expected(EXPECTED_FILE)
    assert observed["pretrunas.html"] == expected["pretrunas.html"]


def test_pretrunas_detail_pages_byte_identical(rendered_site):
    observed = _capture_observed(rendered_site)
    if os.environ.get("REGEN") == "1":
        pytest.skip("REGEN handled by sibling test.")
    expected = _load_expected(EXPECTED_FILE)
    assert observed["pretrunas_detail"] == expected["pretrunas_detail"]


# ── F3b: politicians + personas ─────────────────────────────────────


def test_personas_index_byte_identical(rendered_site):
    observed = _capture_observed_politicians(rendered_site)
    if os.environ.get("REGEN") == "1":
        EXPECTED_FILE_POLITICIANS.write_text(
            json.dumps(observed, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
        )
        pytest.skip("Regenerated baseline — re-run without REGEN to assert.")
    expected = _load_expected(EXPECTED_FILE_POLITICIANS)
    assert observed["personas.html"] == expected["personas.html"]


def test_politiki_detail_pages_byte_identical(rendered_site):
    observed = _capture_observed_politicians(rendered_site)
    if os.environ.get("REGEN") == "1":
        pytest.skip("REGEN handled by personas sibling test.")
    expected = _load_expected(EXPECTED_FILE_POLITICIANS)
    assert observed["politiki_detail"] == expected["politiki_detail"]


# ── F3c: parties ────────────────────────────────────────────────────


def _capture_observed_parties(atmina_dir: Path) -> dict:
    partijas_index = atmina_dir / "partijas.html"
    detail_dir = atmina_dir / "partijas"
    # Per-party slug = short_name.lower() (e.g. 'jv', 'na', 'zzs').
    detail_files = sorted(detail_dir.glob("*.html"), key=lambda p: p.name)
    return {
        "partijas.html": _sha(partijas_index),
        "partijas_detail": {p.name: _sha(p) for p in detail_files},
    }


def test_partijas_index_byte_identical(rendered_site):
    observed = _capture_observed_parties(rendered_site)
    if os.environ.get("REGEN") == "1":
        EXPECTED_FILE_PARTIES.write_text(
            json.dumps(observed, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
        )
        pytest.skip("Regenerated baseline — re-run without REGEN to assert.")
    expected = _load_expected(EXPECTED_FILE_PARTIES)
    assert observed["partijas.html"] == expected["partijas.html"]


def test_partijas_detail_pages_byte_identical(rendered_site):
    observed = _capture_observed_parties(rendered_site)
    if os.environ.get("REGEN") == "1":
        pytest.skip("REGEN handled by partijas sibling test.")
    expected = _load_expected(EXPECTED_FILE_PARTIES)
    assert observed["partijas_detail"] == expected["partijas_detail"]


# ── F3d: positions + news + statistika ──────────────────────────────


def _capture_observed_misc(atmina_dir: Path) -> dict:
    pozicijas_index = atmina_dir / "pozicijas.html"
    zinas_index = atmina_dir / "zinas.html"
    statistika_index = atmina_dir / "statistika.html"
    statistika_dir = atmina_dir / "statistika"
    statistika_files = sorted(statistika_dir.glob("*.html"), key=lambda p: p.name)
    return {
        "pozicijas.html": _sha(pozicijas_index),
        "zinas.html": _sha(zinas_index),
        "statistika.html": _sha(statistika_index),
        "statistika_detail": {p.name: _sha(p) for p in statistika_files},
        "saeima.html": _sha(atmina_dir / "saeima.html"),
    }


def test_pozicijas_index_byte_identical(rendered_site):
    observed = _capture_observed_misc(rendered_site)
    if os.environ.get("REGEN") == "1":
        EXPECTED_FILE_MISC.write_text(
            json.dumps(observed, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
        )
        pytest.skip("Regenerated baseline — re-run without REGEN to assert.")
    expected = _load_expected(EXPECTED_FILE_MISC)
    assert observed["pozicijas.html"] == expected["pozicijas.html"]


def test_zinas_index_byte_identical(rendered_site):
    observed = _capture_observed_misc(rendered_site)
    if os.environ.get("REGEN") == "1":
        pytest.skip("REGEN handled by pozicijas sibling test.")
    expected = _load_expected(EXPECTED_FILE_MISC)
    assert observed["zinas.html"] == expected["zinas.html"]


def test_statistika_index_byte_identical(rendered_site):
    observed = _capture_observed_misc(rendered_site)
    if os.environ.get("REGEN") == "1":
        pytest.skip("REGEN handled by pozicijas sibling test.")
    expected = _load_expected(EXPECTED_FILE_MISC)
    assert observed["statistika.html"] == expected["statistika.html"]


def test_statistika_detail_pages_byte_identical(rendered_site):
    observed = _capture_observed_misc(rendered_site)
    if os.environ.get("REGEN") == "1":
        pytest.skip("REGEN handled by pozicijas sibling test.")
    expected = _load_expected(EXPECTED_FILE_MISC)
    assert observed["statistika_detail"] == expected["statistika_detail"]


def test_saeima_index_byte_identical(rendered_site):
    observed = _capture_observed_misc(rendered_site)
    if os.environ.get("REGEN") == "1":
        pytest.skip("REGEN handled by pozicijas sibling test.")
    expected = _load_expected(EXPECTED_FILE_MISC)
    assert observed["saeima.html"] == expected.get("saeima.html")


# ── F3e: bills + laws + votes ────────────────────────────────────────


def _capture_observed_bills(atmina_dir: Path) -> dict:
    """Bills domain captures balsojumi.html (votes index, single page) plus
    every likumprojekti/<slug>.html. Per F3e plan: balsojumi packs in here
    because votes is its own module but produces only the index page."""
    balsojumi_index = atmina_dir / "balsojumi.html"
    likumprojekti_dir = atmina_dir / "likumprojekti"
    likumprojekti_files = sorted(likumprojekti_dir.glob("*.html"), key=lambda p: p.name)
    return {
        "balsojumi.html": _sha(balsojumi_index),
        "likumprojekti_detail": {p.name: _sha(p) for p in likumprojekti_files},
    }


def _capture_observed_laws(atmina_dir: Path) -> dict:
    likumi_index = atmina_dir / "likumi.html"
    likumi_dir = atmina_dir / "likumi"
    likumi_files = sorted(likumi_dir.glob("*.html"), key=lambda p: p.name)
    return {
        "likumi.html": _sha(likumi_index),
        "likumi_detail": {p.name: _sha(p) for p in likumi_files},
    }


def test_balsojumi_index_byte_identical(rendered_site):
    observed = _capture_observed_bills(rendered_site)
    if os.environ.get("REGEN") == "1":
        EXPECTED_FILE_BILLS.write_text(
            json.dumps(observed, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
        )
        pytest.skip("Regenerated baseline — re-run without REGEN to assert.")
    expected = _load_expected(EXPECTED_FILE_BILLS)
    assert observed["balsojumi.html"] == expected["balsojumi.html"]


def test_likumprojekti_detail_pages_byte_identical(rendered_site):
    observed = _capture_observed_bills(rendered_site)
    if os.environ.get("REGEN") == "1":
        pytest.skip("REGEN handled by balsojumi sibling test.")
    expected = _load_expected(EXPECTED_FILE_BILLS)
    assert observed["likumprojekti_detail"] == expected["likumprojekti_detail"]


def test_likumi_index_byte_identical(rendered_site):
    observed = _capture_observed_laws(rendered_site)
    if os.environ.get("REGEN") == "1":
        EXPECTED_FILE_LAWS.write_text(
            json.dumps(observed, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
        )
        pytest.skip("Regenerated baseline — re-run without REGEN to assert.")
    expected = _load_expected(EXPECTED_FILE_LAWS)
    assert observed["likumi.html"] == expected["likumi.html"]


def test_likumi_detail_pages_byte_identical(rendered_site):
    observed = _capture_observed_laws(rendered_site)
    if os.environ.get("REGEN") == "1":
        pytest.skip("REGEN handled by likumi sibling test.")
    expected = _load_expected(EXPECTED_FILE_LAWS)
    assert observed["likumi_detail"] == expected["likumi_detail"]


# ── F3f.2 (PR #12): x.html — Twitter/X feed page ───────────────────


def _capture_observed_x(atmina_dir: Path) -> dict:
    return {"x.html": _sha(atmina_dir / "x.html")}


def test_x_index_byte_identical(rendered_site):
    observed = _capture_observed_x(rendered_site)
    if os.environ.get("REGEN") == "1":
        EXPECTED_FILE_X.write_text(
            json.dumps(observed, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
        )
        pytest.skip("Regenerated baseline — re-run without REGEN to assert.")
    expected = _load_expected(EXPECTED_FILE_X)
    assert observed["x.html"] == expected["x.html"]


# ── F3f.3 (this phase): spriedzes.html + saites.html ───────────────


def _capture_observed_graph(atmina_dir: Path) -> dict:
    return {
        "spriedzes.html": _sha(atmina_dir / "spriedzes.html"),
        "saites.html": _sha(atmina_dir / "saites.html"),
    }


def test_spriedzes_index_byte_identical(rendered_site):
    observed = _capture_observed_graph(rendered_site)
    if os.environ.get("REGEN") == "1":
        EXPECTED_FILE_GRAPH.write_text(
            json.dumps(observed, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
        )
        pytest.skip("Regenerated baseline — re-run without REGEN to assert.")
    expected = _load_expected(EXPECTED_FILE_GRAPH)
    assert observed["spriedzes.html"] == expected["spriedzes.html"]


def test_saites_index_byte_identical(rendered_site):
    observed = _capture_observed_graph(rendered_site)
    if os.environ.get("REGEN") == "1":
        pytest.skip("REGEN handled by spriedzes sibling test.")
    expected = _load_expected(EXPECTED_FILE_GRAPH)
    assert observed["saites.html"] == expected["saites.html"]


# ── F3f.5 (this phase): analyses + syntheses ────────────────────────


def _capture_observed_analyses(atmina_dir: Path) -> dict:
    """Capture analizes.html (combined index — orchestrator-owned, kept
    here as a sanity check that data shape from the new modules is
    unchanged) plus every analizes/<slug>.html and sintezes/<slug>.html.

    Per-page rendering moves to ``src/render/analyses.py`` (analizes/)
    and ``src/render/syntheses.py`` (sintezes/). The combined index
    ``analizes.html`` stays in the orchestrator until F3f.1 (dashboard)
    since it shares context (analyses, syntheses, blog_posts,
    trends_data, context_notes).
    """
    analizes_index = atmina_dir / "analizes.html"
    analizes_dir = atmina_dir / "analizes"
    sintezes_dir = atmina_dir / "sintezes"
    analizes_files = sorted(analizes_dir.glob("*.html"), key=lambda p: p.name)
    sintezes_files = sorted(sintezes_dir.glob("*.html"), key=lambda p: p.name)
    return {
        "analizes.html": _sha(analizes_index),
        "analizes_detail": {p.name: _sha(p) for p in analizes_files},
        "sintezes_detail": {p.name: _sha(p) for p in sintezes_files},
    }


def test_analizes_index_byte_identical(rendered_site):
    observed = _capture_observed_analyses(rendered_site)
    if os.environ.get("REGEN") == "1":
        EXPECTED_FILE_ANALYSES.write_text(
            json.dumps(observed, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
        )
        pytest.skip("Regenerated baseline — re-run without REGEN to assert.")
    expected = _load_expected(EXPECTED_FILE_ANALYSES)
    assert observed["analizes.html"] == expected["analizes.html"]


def test_analizes_detail_pages_byte_identical(rendered_site):
    observed = _capture_observed_analyses(rendered_site)
    if os.environ.get("REGEN") == "1":
        pytest.skip("REGEN handled by analizes_index sibling test.")
    expected = _load_expected(EXPECTED_FILE_ANALYSES)
    assert observed["analizes_detail"] == expected["analizes_detail"]


def test_sintezes_detail_pages_byte_identical(rendered_site):
    observed = _capture_observed_analyses(rendered_site)
    if os.environ.get("REGEN") == "1":
        pytest.skip("REGEN handled by analizes_index sibling test.")
    expected = _load_expected(EXPECTED_FILE_ANALYSES)
    assert observed["sintezes_detail"] == expected["sintezes_detail"]


# ── F3f.4 (this phase): blog index + per-post pages ────────────────


def _capture_observed_blog(atmina_dir: Path) -> dict:
    """Capture blog.html (index) + every blog/<slug>.html.

    blog_posts comes from ``_fetch_blog_posts`` (daily + weekly briefs
    via context_notes). Count is dynamic — every ingest cycle adds
    new briefs, which means REGEN is expected pēc blog ingest darbības.
    Pattern mirrors likumprojekti (F3e) where bill count is also
    dynamic.
    """
    blog_index = atmina_dir / "blog.html"
    blog_dir = atmina_dir / "blog"
    blog_files = sorted(blog_dir.glob("*.html"), key=lambda p: p.name)
    return {
        "blog.html": _sha(blog_index),
        "blog_detail": {p.name: _sha(p) for p in blog_files},
    }


def test_blog_index_byte_identical(rendered_site):
    observed = _capture_observed_blog(rendered_site)
    if os.environ.get("REGEN") == "1":
        EXPECTED_FILE_BLOG.write_text(
            json.dumps(observed, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
        )
        pytest.skip("Regenerated baseline — re-run without REGEN to assert.")
    expected = _load_expected(EXPECTED_FILE_BLOG)
    assert observed["blog.html"] == expected["blog.html"]


def test_blog_detail_pages_byte_identical(rendered_site):
    observed = _capture_observed_blog(rendered_site)
    if os.environ.get("REGEN") == "1":
        pytest.skip("REGEN handled by blog_index sibling test.")
    expected = _load_expected(EXPECTED_FILE_BLOG)
    assert observed["blog_detail"] == expected["blog_detail"]


# ── F3f.1 (this phase): dashboard (index.html + analizes.html) ──────


def _capture_observed_dashboard(atmina_dir: Path) -> dict:
    """Capture index.html (homepage hero) + analizes.html (combined
    index for analyses + syntheses + blog posts + trends + context).

    Both pages move to ``src/render/dashboard.py`` via ``render_dashboard``
    in F3f.1. analizes.html is also asserted by F3f.5
    (``render_baseline_analyses.json``) — both fixtures kept until F3g
    cleanup pass dedupes.
    """
    index_page = atmina_dir / "index.html"
    analizes_index = atmina_dir / "analizes.html"
    return {
        "index.html": _sha(index_page),
        "analizes.html": _sha(analizes_index),
    }


def test_index_homepage_byte_identical(rendered_site):
    observed = _capture_observed_dashboard(rendered_site)
    if os.environ.get("REGEN") == "1":
        EXPECTED_FILE_DASHBOARD.write_text(
            json.dumps(observed, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
        )
        pytest.skip("Regenerated baseline — re-run without REGEN to assert.")
    expected = _load_expected(EXPECTED_FILE_DASHBOARD)
    assert observed["index.html"] == expected["index.html"]


def test_analizes_combined_index_byte_identical(rendered_site):
    """analizes.html (the combined index, F3f.1 dashboard.py) — separate
    from F3f.5's analizes.html sanity assertion in render_baseline_analyses.json."""
    observed = _capture_observed_dashboard(rendered_site)
    if os.environ.get("REGEN") == "1":
        pytest.skip("REGEN handled by index_homepage sibling test.")
    expected = _load_expected(EXPECTED_FILE_DASHBOARD)
    assert observed["analizes.html"] == expected["analizes.html"]


def test_index_election_countdown_carries_election_date(rendered_site):
    """Failure: the countdown was only a number baked at render time, so a page
    left undeployed for days showed a stale «N dienas». ixv1.js now recomputes
    from ``data-election``; if the context key is dropped the attribute renders
    empty and the script silently keeps the stale number."""
    from src.render._common import ELECTION_DATE

    html = (rendered_site / "index.html").read_text(encoding="utf-8")
    assert f'data-election="{ELECTION_DATE.isoformat()}"' in html


def test_index_election_countdown_links_to_party_programmes(rendered_site):
    """Operator decision 2026-09-28: the countdown is the natural «where do I
    compare the lists?» entry, so it links to partijas.html (the 14 lists'
    programmes). Failure guarded: the element stops being a link, or loses
    what ixv1.js needs (``.hero-election[data-election]`` plus both spans)."""
    html = (rendered_site / "index.html").read_text(encoding="utf-8")
    m = re.search(r'<a class="hero-election" href="partijas\.html"[^>]*>(.*?)</a>', html, re.S)
    assert m, "vēlēšanu atskaite nav saite uz partijas.html"
    tag = m.group(0)
    assert "data-election=" in tag and "data-election-to=" in tag
    assert 'class="hero-election-days"' in m.group(1)
    assert 'class="hero-election-label"' in m.group(1)
    assert 'role="note"' not in tag


def test_party_colour_identical_on_personas_and_partijas(rendered_site):
    """Failure: one party, two colours. ``partijas.html`` painted each party
    from ``parties.color`` while ``personas.html`` (and ~20 other surfaces)
    painted it from a hard-coded ``PARTY_COLORS`` dict; the two disagreed on
    8 of 9 parties (BACKLOG vietne-ui «Partiju krāsas divos avotos»). Both now
    read ``parties.color`` through ``src.coalition.party_color_map()``."""
    partijas = (rendered_site / "partijas.html").read_text(encoding="utf-8")
    party_hex = {
        slug: hex_.lower()
        for hex_, slug in re.findall(
            r'border-left: 4px solid (#[0-9a-fA-F]{6});">\s*<div class="party-card-header">\s*'
            r'<h3><a class="party-card-link" href="partijas/([^"]+)\.html"',
            partijas,
        )
    }
    personas = (rendered_site / "personas.html").read_text(encoding="utf-8")
    spines = re.findall(
        r'data-party-short="([^"]+)".*?style="--spine:([^;"]+);"', personas, re.S
    )
    compared, diverged = set(), []
    for short, spine in spines:
        slug = short.lower()
        if slug not in party_hex:
            continue  # partija bez `parties` rindas (fikstūrā MMN) — nav ar ko salīdzināt
        compared.add(slug)
        if spine.lower() != party_hex[slug]:
            diverged.append((short, spine, party_hex[slug]))
    # Saucējs: fikstūrā 5 partijas ar `parties` rindu un politiķi (JV, PRO, NA, AS, LA).
    assert len(compared) >= 4, f"pārāk maz salīdzināto partiju: {sorted(compared)}"
    assert not diverged, f"(partija, personas.html, partijas.html): {diverged}"
