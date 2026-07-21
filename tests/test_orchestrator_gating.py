"""P0 build-loop perf: orchestrator heavy-fetch gating + orphan-PNG drop.

Two independent changes, both verified here:

1. ``_heavy_fetch_plan(only)`` — decides which of the three MEASURED-expensive
   prefetches (blog_posts ~12.6s, votes ~5.6s, trends ~1.1s) a given ``--only``
   build actually needs. The dependency map is the silent-empty-page risk the
   audit's @devils-advocate flagged, so it is locked exhaustively here. The
   ``{"politiki"}`` case encodes the key finding: politician pages re-query
   votes per-pid (politicians.py:650) and do NOT consume the orchestrator
   ``votes`` list, so a ``--only=politiki`` build must skip the 5.6s fetch.

2. ``_copy_brief_images(src, dest)`` — copies only the page-referenced
   responsive variants (.webp/.jpg/.jpeg) and NOT the raw -.png masters, which
   are referenced by zero pages (measured: 108 files / 75 MB, 0 HTML refs).
"""

from __future__ import annotations

import pytest


# ── 1. Heavy-fetch dependency map (pure function) ──────────────────────────

@pytest.mark.parametrize(
    "only,expected",
    [
        # Full build (only=None) must fetch everything — the gating is a no-op,
        # which is what keeps the char-baseline fixtures byte-identical.
        (None, {"votes": True, "blog_posts": True, "trends_data": True}),
        # A cheap, unrelated narrow build skips all three (the core win).
        ({"pretrunas"}, {"votes": False, "blog_posts": False, "trends_data": False}),
        ({"politiki"}, {"votes": False, "blog_posts": False, "trends_data": False}),
        # temas (topic pages) reads only claims/contradictions/syntheses —
        # none of the three measured-expensive prefetches.
        ({"temas"}, {"votes": False, "blog_posts": False, "trends_data": False}),
        # balsojumi consumes votes only.
        ({"balsojumi"}, {"votes": True, "blog_posts": False, "trends_data": False}),
        # blog index + sitemap (static) consume blog_posts only.
        ({"blog"}, {"votes": False, "blog_posts": True, "trends_data": False}),
        ({"static"}, {"votes": False, "blog_posts": True, "trends_data": False}),
        # dashboard hero+analizes consume all three.
        ({"dashboard"}, {"votes": True, "blog_posts": True, "trends_data": True}),
    ],
)
def test_heavy_fetch_plan(only, expected):
    from src.render._orchestrator import _heavy_fetch_plan
    assert _heavy_fetch_plan(only) == expected


def test_narrow_render_skips_unneeded_heavy_fetches(tmp_path, monkeypatch):
    """Wiring check: a --only=pretrunas build must not call the heavy fetches.

    This is the integration counterpart to test_heavy_fetch_plan — it proves
    the orchestrator actually consults the plan rather than eagerly prefetching.
    """
    import src.render._orchestrator as orch
    from src.db import init_db
    from src.saeima import init_saeima_tables, init_saeima_bills

    # Schema-complete but empty temp DB so the render reads real (empty) tables
    # rather than the live, gitignored data/atmina.db (absent in CI). The
    # dashboard stats header (rendered for every build) reads saeima_votes, so
    # the Saeima tables must exist too — init_db() alone only builds the base
    # schema. Keep the DB out of output_dir so a render-side cleanup of the
    # output tree can't delete it mid-run.
    db_path = str(tmp_path / "render.db")
    init_db(db_path)
    init_saeima_tables(db_path)
    init_saeima_bills(db_path)
    output_dir = str(tmp_path / "site")

    # Avoid network (chart.js / annotation plugin download into a fresh tmp dir).
    monkeypatch.setattr(orch, "_download_chart_js", lambda *a, **k: None)
    monkeypatch.setattr(orch, "_download_annotation_plugin", lambda *a, **k: None)

    called: set[str] = set()
    monkeypatch.setattr(orch, "_fetch_votes", lambda *a, **k: called.add("votes") or [])
    monkeypatch.setattr(orch, "_fetch_blog_posts", lambda *a, **k: called.add("blog_posts") or [])
    monkeypatch.setattr(orch, "_fetch_trends_data", lambda *a, **k: called.add("trends_data") or {})

    orch.generate_public_site(db_path=db_path, output_dir=output_dir, only={"pretrunas"})

    assert called == set(), (
        f"--only=pretrunas must skip blog_posts/votes/trends prefetch, but ran: {called}"
    )


# ── 2. Brief-image copy excludes orphaned raw PNG masters ──────────────────

def test_copy_brief_images_excludes_raw_png(tmp_path):
    from src.render._orchestrator import _copy_brief_images

    src = tmp_path / "briefs_src"
    src.mkdir()
    dest = tmp_path / "briefs_dest"
    dest.mkdir()

    # One brief: raw PNG master (orphaned) + the variants pages actually use.
    (src / "brief-218.png").write_bytes(b"rawmaster")
    (src / "brief-218-hero.webp").write_bytes(b"hero")
    (src / "brief-218-card.webp").write_bytes(b"card")
    (src / "brief-218-thumb.webp").write_bytes(b"thumb")
    (src / "brief-218-og.jpg").write_bytes(b"og")

    n = _copy_brief_images(src, dest)

    names = sorted(p.name for p in dest.iterdir())
    assert "brief-218.png" not in names, (
        "raw brief PNG masters are referenced by zero pages (75 MB orphaned) — "
        "they must not be deployed"
    )
    assert names == [
        "brief-218-card.webp",
        "brief-218-hero.webp",
        "brief-218-og.jpg",
        "brief-218-thumb.webp",
    ]
    assert n == 4


def test_copy_brief_images_missing_src_is_noop(tmp_path):
    """A fresh clone has no output/images/briefs/ — copying must not error."""
    from src.render._orchestrator import _copy_brief_images

    dest = tmp_path / "dest"
    dest.mkdir()
    assert _copy_brief_images(tmp_path / "does_not_exist", dest) == 0


def test_copy_brief_images_includes_svg_movers_chart(tmp_path):
    """The deterministic weekly movers chart (.svg) must be deployed."""
    from src.render._orchestrator import _copy_brief_images

    src = tmp_path / "src"
    src.mkdir()
    dest = tmp_path / "dest"
    dest.mkdir()
    (src / "2026-05-26-nedelas-movers.svg").write_bytes(b"<svg/>")
    (src / "brief-1-hero.webp").write_bytes(b"hero")

    n = _copy_brief_images(src, dest)
    names = sorted(p.name for p in dest.iterdir())
    assert "2026-05-26-nedelas-movers.svg" in names
    assert n == 2


# ── 3. Generic _copy_images (synthesis includes .png, unlike briefs) ────────

def test_copy_images_includes_png_and_filters_by_suffix(tmp_path):
    """Synthesis pages reference the raw .png directly (render/syntheses.py),
    so the synthesis copy must include png — unlike the brief copy which drops
    orphaned png masters. _copy_images takes explicit suffixes."""
    from src.render._orchestrator import _copy_images

    src = tmp_path / "synthesis_src"
    src.mkdir()
    (src / "topic.png").write_bytes(b"raw")
    (src / "topic-hero.webp").write_bytes(b"hero")
    (src / "topic-og.jpg").write_bytes(b"og")
    (src / "notes.txt").write_bytes(b"ignore")

    # dest does not pre-exist — _copy_images must create it.
    dest = tmp_path / "deep" / "synthesis_dest"
    n = _copy_images(src, dest, (".png", ".jpg", ".jpeg", ".webp"))

    names = sorted(p.name for p in dest.iterdir())
    assert names == ["topic-hero.webp", "topic-og.jpg", "topic.png"], "png INCLUDED, txt excluded"
    assert n == 3


def test_copy_images_missing_src_is_noop(tmp_path):
    from src.render._orchestrator import _copy_images
    assert _copy_images(tmp_path / "nope", tmp_path / "dest", (".png",)) == 0


# ── 4. Curated one-off pages overlay (finanses, statistika) ─────────────────

def test_copy_curated_overlays_nested_tree(tmp_path):
    """finanses.html + statistika/* are frozen one-offs copied through verbatim
    (NOT regenerated). The overlay must preserve the nested statistika/ subdir."""
    from src.render._orchestrator import _copy_curated

    curated = tmp_path / "curated" / "atmina"
    (curated / "statistika").mkdir(parents=True)
    (curated / "finanses.html").write_text("FIN", encoding="utf-8")
    (curated / "statistika.html").write_text("STAT-INDEX", encoding="utf-8")
    (curated / "statistika" / "IKP010.html").write_text("STAT-DETAIL", encoding="utf-8")

    dest = tmp_path / "out" / "atmina"
    dest.mkdir(parents=True)
    n = _copy_curated(curated, dest)

    assert (dest / "finanses.html").read_text(encoding="utf-8") == "FIN"
    assert (dest / "statistika.html").read_text(encoding="utf-8") == "STAT-INDEX"
    assert (dest / "statistika" / "IKP010.html").read_text(encoding="utf-8") == "STAT-DETAIL"
    assert n == 3


def test_copy_curated_missing_root_is_noop(tmp_path):
    from src.render._orchestrator import _copy_curated
    assert _copy_curated(tmp_path / "no_curated", tmp_path / "atmina") == 0


def test_copy_curated_resyncs_chrome_from_base(tmp_path):
    """Frozen curated pages freeze CONTENT, not chrome: each page's stale <nav>
    AND <footer> are re-rendered from base.html.j2 at copy time so they can never
    drift from the live site. Depth drives assets_prefix; top segment drives the
    active tab. Page content + page-specific scripts are preserved verbatim."""
    from src.render._orchestrator import _copy_curated

    old_nav = (
        '<nav class="nav"><div class="container">'
        '<a href="index.html" class="nav-logo"><svg>OLD-LOGO</svg></a>'
        '<div class="nav-links">'
        '<a href="pozicijas.html">Pozīcijas</a>'
        '<a href="personas.html">Personas</a>'
        '<a href="finanses.html" class="active">Finanses</a>'
        '</div></div></nav>'
    )
    # Frozen curated pages carry a STALE INLINE chrome <script> right after
    # </nav> (pre-CSP snapshots). The chrome-sync target regex must swallow it
    # and inject exactly ONE external chrome-v1.js src tag (idempotent —
    # re-syncing an already-synced page replaces the src tag, not duplicates it).
    stale_chrome_script = "<script>STALE-INLINE-CHROME();</script>"
    old_footer = (
        '<footer class="footer"><div class="container">'
        '<svg>OLD-FOOTER-LOGO</svg><span>old footer</span>'
        "</div></footer>"
    )
    page = (
        "<!DOCTYPE html><html><head></head><body>"
        + old_nav
        + stale_chrome_script
        + '<main class="container">SENTINEL-CONTENT</main>'
        + old_footer
        + "<script>PAGE-SCRIPT</script></body></html>"
    )
    curated = tmp_path / "curated" / "atmina"
    (curated / "statistika").mkdir(parents=True)
    (curated / "finanses.html").write_text(page, encoding="utf-8")
    (curated / "statistika" / "IKP010.html").write_text(page, encoding="utf-8")
    # a chrome-less asset passes through unchanged
    (curated / "robots.txt").write_text("User-agent: *\n", encoding="utf-8")

    dest = tmp_path / "out" / "atmina"
    dest.mkdir(parents=True)
    n = _copy_curated(curated, dest)
    assert n == 3

    fin = (dest / "finanses.html").read_text(encoding="utf-8")
    # new menu chrome injected, old flat nav gone
    assert 'id="nav-burger"' in fin and 'class="nav-more"' in fin
    assert "OLD-LOGO" not in fin and ">Personas<" not in fin
    # stale inline chrome script purged; exactly ONE external chrome-v1.js tag
    # injected right after </nav> (idempotent duplicate-chrome fix)
    assert "STALE-INLINE-CHROME" not in fin
    assert fin.count("chrome-v1.js") == 1
    fin_nav_close = fin.index("</nav>")
    fin_main = fin.index("<main", fin_nav_close)
    assert fin[fin_nav_close:fin_main].count("<script") == 1
    # root page → no prefix, finanses tab active, content preserved
    assert 'href="temas.html"' in fin and 'href="mediji.html"' in fin
    assert 'href="finanses.html" class="active"' in fin
    assert "SENTINEL-CONTENT" in fin
    # footer re-synced from base; old footer gone; page script preserved
    assert "OLD-FOOTER-LOGO" not in fin
    assert 'class="footer-brand"' in fin and ">Par mums<" in fin
    assert 'href="about.html"' in fin
    assert "<script>PAGE-SCRIPT</script>" in fin

    sub = (dest / "statistika" / "IKP010.html").read_text(encoding="utf-8")
    # subpage one level down → ../ prefix on both nav + footer, statistika active
    assert 'href="../temas.html"' in sub
    # inline SVG logo (30b51ad: <img logo.svg> → <symbol>+<use>, asset refs nav/footer vairs nav)
    assert '<use href="#atm-logo"/>' in sub
    assert 'href="../statistika.html" class="active"' in sub
    assert 'href="../about.html"' in sub and 'href="../kontakti.html"' in sub
    assert "OLD-FOOTER-LOGO" not in sub
    assert "<script>PAGE-SCRIPT</script>" in sub

    # non-HTML asset copied byte-for-byte
    assert (dest / "robots.txt").read_text(encoding="utf-8") == "User-agent: *\n"
