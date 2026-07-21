"""Orchestrator for the public site — owns ``generate_public_site``.

Phase F3g (refactor-plan-2026-04-29 § Fāze 3) carve-out from
``src/generate.py``. This module is the canonical home of the site
entry-point: orchestrator pre-fetches all DB-backed data once and
threads it through to each ``render_*`` sub-page module from
``src/render/*.py``.

``src/render/__init__.py`` re-exports ``generate_public_site``,
``_generate_sitemap`` and ``_generate_og_image`` so the public
contract is ``from src.render import generate_public_site``.
``src/generate.py`` keeps a thin shim re-exporting the same symbols
plus all sub-page private helpers so existing test imports
(``from src.generate import _fetch_x_data``, …) continue working.

Cycle safety: imports run depth-first from ``__init__.py`` →
``_orchestrator.py`` → ``_common.py`` (leaf) + sub-pages (leaves
relative to peers). No sibling sub-page imports.
"""

from __future__ import annotations

import logging
import re
import shutil
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment, FileSystemLoader

from src.db import get_db, today_lv
from src.image_variants import make_variants as _make_variants
from src.image_variants import variant_filename as _brief_image_variant
from src.outlets import load_outlets
from src.render._common import (
    ASSETS_DIR,
    BASE_URL,
    DEFAULT_DB_PATH,
    DEFAULT_OUTPUT_DIR,
    ELECTION_DATE,
    TEMPLATES_DIR,
    _autolink_bills_filter,
    _download_annotation_plugin,
    _download_chart_js,
    _lv_plural,
    _party_page_slug,
    _party_short_name,
    _render_page,
    _resolve_assets_version,
    _safe_json_filter,
    _safe_url_filter,
)
from src.render.analyses import _load_analyses, render_analyses
from src.render.bills import _fetch_bills, render_bills
from src.render.blog import _fetch_blog_posts, _fetch_context_notes, render_blog
from src.render.contradictions import _fetch_contradictions, render_contradictions
from src.render.dashboard import (
    _fetch_stats,
    _fetch_trends_data,
    render_dashboard,
)
from src.render.rankings import fetch_rankings
from src.render.topics import _fetch_topics, render_topics
from src.render.laws import render_laws
from src.render.links import render_links
from src.render.news import render_news
from src.render.mediji import render_mediji
from src.render.parties import _fetch_parties_page, render_parties
from src.render.personas import render_personas
from src.render.politicians import _fetch_politicians, render_politicians
from src.render.positions import _fetch_claims, render_positions
from src.render.search_index import render_search_index
from src.render.syntheses import _load_syntheses, _map_syntheses_to_politicians, render_syntheses
from src.render.tensions import _fetch_tensions, render_tensions
from src.render.votes import _fetch_votes, render_votes
from src.render.x import render_x

logger = logging.getLogger(__name__)


KNOWN_DOMAINS = frozenset({
    "dashboard",    # index.html + analizes.html (combined hero)
    "pretrunas",    # pretrunas/* + OG cards
    "pozicijas",    # pozicijas.html + JSON
    "temas",        # temas.html + temas/<slug>.html (topic destination pages)
    "likumi",       # likumi.html
    "bills",        # likumi/<slug>.html per-bill
    "balsojumi",    # balsojumi.html + matrix JSON/.br/.gz
    "partijas",     # partijas.html + partijas/<slug>.html
    "mediji",       # mediji.html + mediji/<slug>.html (media outlets)
    "personas",     # personas.html
    "zinas",        # zinas.html
    "x",            # X/Twitter timeline
    "spriedzes",    # spriedzes.html (political tensions)
    "saites",       # saites.html (force-graph)
    "blog",         # blog.html + blog/<slug>.html (daily + weekly briefs)
    "analizes",     # analizes/<slug>.html (thematic)
    "sintezes",     # sintezes/<slug>.html
    "politiki",     # politiki/<slug>.html (176 profiles)
    "static",       # about, kontakti, 404, htaccess, robots, sitemap, og
})


# Page-referenced responsive brief variants only. Raw ``-.png`` masters stay in
# source as regeneration masters but are referenced by ZERO pages (audit
# 2026-05-30: 108 files / ~75 MB orphaned in output), so they are not deployed.
# og social cards are ``.jpg``; hero/card/thumb are ``.webp``. ``.svg`` covers
# the deterministic in-body weekly movers chart (src/graphics/weekly_chart.py).
DEPLOYABLE_BRIEF_SUFFIXES = (".webp", ".jpg", ".jpeg", ".svg")


def _copy_images(src_dir: Path, dest_dir: Path, suffixes: tuple[str, ...]) -> int:
    """Copy files whose suffix is in ``suffixes`` from ``src_dir`` to ``dest_dir``.

    A missing ``src_dir`` is a no-op returning 0; ``dest_dir`` is created if
    needed. Suffix matching is case-insensitive. Asserted in
    tests/test_orchestrator_gating.py.
    """
    if not src_dir.exists():
        return 0
    dest_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    for img in src_dir.iterdir():
        if img.is_file() and img.suffix.lower() in suffixes:
            shutil.copy2(img, dest_dir / img.name)
            copied += 1
    return copied


# Variantu faili beidzas ar kādu no šiem stem-sufiksiem — izlaižam tos, lai
# nekad neapstrādātu variantu atkārtoti caur make_variants (defensīvi: varianti
# ir .webp/.jpg, nevis .png, tāpēc *.png meklējums tos jau tāpat neaptver).
_VARIANT_STEM_SUFFIXES = ("-hero", "-og", "-card", "-thumb")


def _ensure_image_variants(src_dir: Path) -> int:
    """Generate -hero/-og/-card/-thumb variants for every source PNG in *src_dir*.

    Self-healing invariants solis: pirms attēlu kopēšanas nodrošina, ka katram
    ``<slug>.png`` blakus ir tā responsīvie varianti. Trūkstošs katalogs =
    no-op (0). ``make_variants`` ir mtime-kešots — atkārtoti renderi izlaiž jau
    svaigos variantus, tāpēc solis ir lēts. Atgriež jaunģenerēto avotu skaitu.
    """
    if not src_dir.exists():
        return 0
    generated = 0
    for png in sorted(src_dir.glob("*.png")):
        if png.stem.endswith(_VARIANT_STEM_SUFFIXES):
            continue
        _make_variants(png)
        generated += 1
    return generated


def _copy_brief_images(src_dir: Path, dest_dir: Path) -> int:
    """Copy page-referenced brief image variants (webp/jpg) to the deploy dir.

    Skips raw ``-.png`` masters (orphaned — see ``DEPLOYABLE_BRIEF_SUFFIXES``).
    A missing ``src_dir`` (fresh clone with no rendered briefs yet) is a no-op
    returning 0. Asserted in tests/test_orchestrator_gating.py.
    """
    return _copy_images(src_dir, dest_dir, DEPLOYABLE_BRIEF_SUFFIXES)


# Curated overlay pages freeze their CONTENT but not their site chrome: the
# <nav> menu and <footer> are re-rendered from base.html.j2 on every build (see
# _sync_curated_chrome) so a frozen snapshot can never drift from the live site.
# Each spec is (extraction regex on base.html.j2, replacement-target regex on
# the curated page). For <nav> the base fragment also grabs the external chrome
# <script src=...chrome-v1.js...> that immediately follows it (theme/sound
# toggle, burger, "Vairāk" disclosure, copy, card-nav) — curated pages hold
# only the <nav>, so the script tag is injected. The curated-target regex
# swallows an OPTIONAL trailing <script>…</script> right after </nav> so the sync
# is idempotent: on old frozen pages it purges a stale INLINE chrome script
# (pre-existing duplicate-chrome bug), and on re-synced pages it replaces the
# already-injected src tag. The negative lookahead excludes
# application/json + application/ld+json blocks (non-executable, CSP-exempt data
# blocks that later phases add right after nav) so only a real chrome script is
# swallowed; the \s* before <script means it must sit IMMEDIATELY after </nav>
# (whitespace only), never a page-content script further down. <footer> is a 1:1
# swap; page-specific <script> blocks after </footer> are left untouched.
_CHROME_SPECS = (
    (
        re.compile(
            r'<nav class="nav">.*?</nav>\s*'
            r'<script src[^>]*chrome-v1\.js[^>]*></script>',
            re.DOTALL,
        ),
        re.compile(
            r'<nav class="nav">.*?</nav>'
            r'(?:\s*<script(?![^>]*application/(?:ld\+)?json)[^>]*>.*?</script>)?',
            re.DOTALL,
        ),
    ),
    (
        re.compile(r'<footer class="footer">.*?</footer>', re.DOTALL),
        re.compile(r'<footer class="footer">.*?</footer>', re.DOTALL),
    ),
)
_CHROME_ENV = Environment(autoescape=True)


@lru_cache(maxsize=1)
def _base_chrome_blocks() -> tuple:
    """The (target_re, fragment_template) chrome blocks lifted from base.html.j2.

    base.html.j2 is the single source of truth for the <nav> menu + <footer>.
    Each fragment is returned as a Jinja *template* string (still holding
    ``{{ assets_prefix }}`` / ``active_page`` conditionals) so each curated page
    renders it for its own depth + active tab. Raises if a marker moves — a loud
    build failure beats silently falling back to stale chrome.
    """
    text = (Path(TEMPLATES_DIR) / "base.html.j2").read_bytes().decode("utf-8")
    blocks = []
    for base_re, target_re in _CHROME_SPECS:
        m = base_re.search(text)
        if not m:
            raise RuntimeError(
                f"base.html.j2 chrome fragment {base_re.pattern!r} not found — "
                "curated chrome sync would silently drift."
            )
        blocks.append((target_re, m.group(0)))
    return tuple(blocks)


@lru_cache(maxsize=16)
def _rendered_chrome(
    template: str, assets_prefix: str, active_page: str, assets_version: str
) -> str:
    """Render one base.html.j2 chrome fragment for a curated page's depth/tab.

    The nav fragment now carries an external ``<script src=...chrome-v1.js?v=…>``
    tag, so the fragment template holds ``{{ assets_version }}`` — passed through
    (and part of the lru_cache key) so the injected cache-bust matches the rest
    of the built site.
    """
    return _CHROME_ENV.from_string(template).render(
        assets_prefix=assets_prefix,
        active_page=active_page,
        assets_version=assets_version,
    )


def _sync_curated_chrome(html: str, rel: Path) -> str:
    """Swap a frozen curated page's stale <nav>/<footer> for the live base chrome.

    ``rel`` is the page path relative to ``curated/atmina/`` — its depth gives
    ``assets_prefix`` (``""`` at root, ``"../"`` one level down for
    ``statistika/*``) and its top-level segment gives the ``active_page`` tab
    (``finanses`` / ``statistika``). Chrome blocks absent from the page are left
    untouched; page-specific content (incl. the <script> after </footer>) is
    preserved.
    """
    assets_prefix = "../" * (len(rel.parts) - 1)
    active_page = Path(rel.parts[0]).stem
    assets_version = _resolve_assets_version()
    for target_re, template in _base_chrome_blocks():
        if not target_re.search(html):
            continue
        rendered = _rendered_chrome(
            template, assets_prefix, active_page, assets_version
        )
        # default-arg binds `rendered` (avoids late-binding) AND sidesteps
        # re.sub treating a literal replacement's backslashes as group refs.
        html = target_re.sub(lambda _m, r=rendered: r, html, count=1)
    return html


def _copy_curated(curated_root: Path, atmina_dir: Path) -> int:
    """Overlay frozen one-off curated pages onto the build output.

    ``finanses.html`` + ``statistika.*`` are unique analyses generated ONCE,
    NOT per build — ``generate_public_site`` deliberately does not render them.
    They live as frozen snapshots under ``curated/atmina/`` (git-tracked) and
    are copied through each build, so a clean rebuild + rsync ``--delete``
    deploy preserves them instead of wiping them. The nested ``statistika/``
    subtree is preserved.

    The page CONTENT is frozen, but each ``.html`` page's ``<nav>`` + ``<footer>``
    chrome is re-rendered from base.html.j2 at copy time (see
    _sync_curated_chrome) so they stay in lock-step with the rest of the site —
    the on-disk curated snapshot keeps its original (possibly stale) chrome, but
    the served output always carries the live menu + footer. Non-HTML assets are
    copied byte-for-byte. Missing ``curated_root`` is a no-op returning 0.
    Asserted in tests/test_orchestrator_gating.py.
    """
    if not curated_root.exists():
        return 0
    copied = 0
    for src in sorted(curated_root.rglob("*")):
        if not src.is_file():
            continue
        rel = src.relative_to(curated_root)
        dest = atmina_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix == ".html":
            # read/write via bytes to preserve source newlines byte-for-byte
            # (Path.read_text has no ``newline=`` before 3.13).
            html = src.read_bytes().decode("utf-8")
            dest.write_bytes(_sync_curated_chrome(html, rel).encode("utf-8"))
        else:
            shutil.copy2(src, dest)
        copied += 1
    return copied


def _heavy_fetch_plan(only: Optional[set[str]]) -> dict[str, bool]:
    """Which of the three MEASURED-expensive prefetches a build actually needs.

    ``blog_posts`` (~12.6s, N+1 footer stats), ``votes`` (~5.6s) and
    ``trends_data`` (~1.1s) dominate the ~20s eager prefetch. A narrow
    ``--only`` build that consumes none of them can skip the whole floor.
    The map mirrors the render call-sites below and is locked exhaustively in
    tests/test_orchestrator_gating.py — keep the two in sync.

    NB: ``render_politicians`` re-queries votes per-pid (politicians.py:650)
    and does NOT consume the orchestrator ``votes`` list, so ``politiki`` is
    deliberately absent from the ``votes`` condition (the silent-empty-page
    failure mode the audit's adversarial review flagged).
    """
    def want(domain: str) -> bool:
        return only is None or domain in only

    return {
        "votes": want("balsojumi") or want("dashboard"),
        "blog_posts": want("blog") or want("dashboard") or want("static"),
        "trends_data": want("dashboard"),
    }


def generate_public_site(
    db_path: Optional[str] = None,
    output_dir: Optional[str] = None,
    only: Optional[set[str]] = None,
) -> str:
    """Generate the full public site, or a subset.

    ``only`` — if provided, only the listed render domains run; everything
    else is skipped. Valid names are exposed via ``KNOWN_DOMAINS``. Data
    pre-fetch still happens (cheap DB queries); only the heavy ``render_X``
    calls are gated. Use ``python -m src.render --only=blog,partijas`` for
    quick narrow re-renders (~10-30s) instead of the full ~12 min path.

    Returns the output directory path.
    """
    if only is not None:
        unknown = set(only) - KNOWN_DOMAINS
        if unknown:
            raise ValueError(
                f"Unknown render domains: {sorted(unknown)}. "
                f"Valid: {sorted(KNOWN_DOMAINS)}"
            )

    def _want(domain: str) -> bool:
        return only is None or domain in only

    db_path = db_path or DEFAULT_DB_PATH
    output_dir = output_dir or DEFAULT_OUTPUT_DIR

    output = Path(output_dir)
    atmina_dir = output / "atmina"
    politiki_dir = atmina_dir / "politiki"

    # Ensure output directories. analizes/ + sintezes/ are created by
    # render_analyses() / render_syntheses() (F3f.5); blog/ by render_blog()
    # (F3f.4).
    for d in [atmina_dir, politiki_dir, atmina_dir / "assets"]:
        d.mkdir(parents=True, exist_ok=True)

    # Copy assets
    if ASSETS_DIR.exists():
        for asset in ASSETS_DIR.iterdir():
            if asset.is_file():
                shutil.copy2(asset, atmina_dir / "assets" / asset.name)
            elif asset.is_dir():
                dest = atmina_dir / "assets" / asset.name
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(asset, dest)
    logger.info("Assets copied to %s", atmina_dir / "assets")

    # Copy featured-image PNGs into atmina_dir/images/briefs/ so they are
    # served at atmina.lv/images/briefs/<file>.png. Source lives outside the
    # deploy root at output/images/briefs/; missing dir is fine (no images
    # yet on a fresh clone).
    briefs_src = output / "images" / "briefs"
    briefs_dest = atmina_dir / "images" / "briefs"
    briefs_dest.mkdir(parents=True, exist_ok=True)
    copied = _copy_brief_images(briefs_src, briefs_dest)
    logger.info("Copied %d brief images to %s", copied, briefs_dest)

    # Thematic-analysis images: source from output/images/analizes/, served
    # at atmina.lv/images/analizes/<file>. Referenced via image: frontmatter
    # field on content/analizes/*.md.
    analizes_img_src = output / "images" / "analizes"
    analizes_img_dest = atmina_dir / "images" / "analizes"
    analizes_img_dest.mkdir(parents=True, exist_ok=True)
    _ensure_image_variants(analizes_img_src)
    if analizes_img_src.exists():
        copied = 0
        for img in analizes_img_src.iterdir():
            if img.is_file() and img.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                shutil.copy2(img, analizes_img_dest / img.name)
                copied += 1
        logger.info("Copied %d analysis images to %s", copied, analizes_img_dest)

    # Synthesis featured images: source from output/images/synthesis/, served
    # at atmina.lv/images/synthesis/<file>. Persisting them in a SOURCE dir
    # (not the throwaway deploy tree) keeps a clean rebuild self-contained —
    # generate_synthesis_image.py writes here. NB synthesis pages reference the
    # raw .png directly (render/syntheses.py: has_image keys off <slug>.png), so
    # png is copied alongside the webp/jpg variants. This block must run BEFORE
    # _load_syntheses() below so has_image resolves against the populated dir.
    _ensure_image_variants(output / "images" / "synthesis")
    synthesis_copied = _copy_images(
        output / "images" / "synthesis",
        atmina_dir / "images" / "synthesis",
        (".png", ".jpg", ".jpeg", ".webp"),
    )
    logger.info("Copied %d synthesis images", synthesis_copied)

    # Curated one-off pages (finanses, statistika) — frozen CONTENT, NOT
    # regenerated, copied from the git-tracked curated/atmina/ overlay so a
    # clean rebuild + rsync --delete deploy preserves them. Their <nav> chrome
    # is re-synced from base.html.j2 at copy time (see _copy_curated) so the
    # menu never drifts. ASSETS_DIR.parent is the project root.
    curated_copied = _copy_curated(ASSETS_DIR.parent / "curated" / "atmina", atmina_dir)
    logger.info("Copied %d curated pages", curated_copied)

    # Download chart.min.js if not present
    chart_js = atmina_dir / "assets" / "chart.min.js"
    if not chart_js.exists():
        _download_chart_js(chart_js)

    # Download annotation plugin if not present
    annotation_js = atmina_dir / "assets" / "chartjs-plugin-annotation.min.js"
    if not annotation_js.exists():
        _download_annotation_plugin(annotation_js)

    # Set up Jinja2
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=True,
    )
    env.filters["lv_date"] = lambda s: f"{s[8:10]}.{s[5:7]}.{s[:4]}" if s and len(s) >= 10 and "-" in s else s or ""
    env.filters["safe_json"] = _safe_json_filter
    env.filters["safe_url"] = _safe_url_filter
    env.filters["autolink_bills"] = _autolink_bills_filter
    env.filters["image_variant"] = _brief_image_variant
    env.filters["lv_plural"] = _lv_plural
    env.globals["_party_short_name"] = _party_short_name
    env.filters["party_page_slug"] = _party_page_slug

    # Cache-bust the stylesheet (env override via ATMINA_ASSETS_VERSION
    # for deterministic char fixtures — sk. _resolve_assets_version).
    env.globals["assets_version"] = _resolve_assets_version()

    # Open DB
    db = get_db(db_path)

    # Fetch all data. The three measured-expensive prefetches (votes,
    # trends_data, blog_posts) are gated to the domains that consume them so
    # narrow ``--only`` builds skip the ~20s floor — see _heavy_fetch_plan.
    # When ``only is None`` (full build) every flag is True, so output is
    # byte-identical and the char-baseline fixtures are unaffected.
    heavy = _heavy_fetch_plan(only)
    stats = _fetch_stats(db)
    contradictions = _fetch_contradictions(db)
    claims = _fetch_claims(db)
    votes = _fetch_votes(db) if heavy["votes"] else []
    politicians = _fetch_politicians(db)
    trends_data = _fetch_trends_data(db) if heavy["trends_data"] else {}
    context_notes = _fetch_context_notes(db)
    blog_posts = _fetch_blog_posts(db) if heavy["blog_posts"] else []
    tensions = _fetch_tensions(db)
    analyses = _load_analyses()
    syntheses = _load_syntheses(atmina_dir)
    pid_to_syntheses = _map_syntheses_to_politicians(syntheses, politicians)
    bills = _fetch_bills(db)
    parties = _fetch_parties_page(db)
    outlets = load_outlets()
    bill_slugs = {b["slug"] for b in bills}
    env.globals["bill_slugs"] = bill_slugs

    # Days until election
    today = today_lv()
    days_until = (ELECTION_DATE - today).days

    # Unique parties for filters (used by render_contradictions); topics
    # are now derived inside render_positions itself.
    all_parties = sorted(set(c["party"] for c in claims if c.get("party")))

    source_count = db.execute("SELECT COUNT(*) FROM sources WHERE active = 1").fetchone()[0]
    topic_count = len(set(c["topic"] for c in claims if c.get("topic")))

    # ── Render pages ──
    # Each block is gated by ``_want(domain)`` so ``only={...}`` callers
    # can skip heavy steps. ``politician_count`` is needed for the final
    # summary print; it stays 0 when politiki render is skipped.
    politician_count = 0

    # 1. Index (hero) + Analīzes combined index — both rendered by
    # render_dashboard since they share orchestrator-fetched data
    # (stats, contradictions, votes, blog_posts, syntheses, analyses,
    # trends_data, context_notes, days_until). analizes.html sits at
    # block #6 because it lists data produced by blocks 2-5; it is
    # kept here for sub-page locality.
    if _want("dashboard"):
        # limit=5: līderu + 4 rindas — landing kartītes paliek kompaktas un
        # savstarpēji līdzsvarotas (8 rindas statija "Sakritība" kartīti
        # tālu zem kaimiņiem); pilnie saraksti dzīvo apakšlapās.
        rankings = fetch_rankings(db, contradictions, limit=5)
        render_dashboard(
            env, db, atmina_dir,
            stats, contradictions, votes, blog_posts,
            syntheses, analyses, trends_data, context_notes,
            days_until, rankings,
        )

    # 2. Pretrunas — index, per-detail pages, and OG card PNGs.
    if _want("pretrunas"):
        render_contradictions(env, atmina_dir, contradictions, all_parties)

    # 3. Pozīcijas V2 — index page + embedded JSON (.json/.br/.gz).
    if _want("pozicijas"):
        render_positions(env, db, atmina_dir)

    # 3a. Meklēšanas ieteikumu indekss (data/sg-index.json) — homepage
    # typeahead sidecar. Gated on BOTH daily-routine narrow domains so the
    # counts never go stale: dashboard (homepage owns the search box) and
    # pozicijas (claims changed). Sub-second emit; no _heavy_fetch_plan use.
    if _want("dashboard") or _want("pozicijas"):
        render_search_index(db, atmina_dir)

    # 3b. Tēmas — topic destination pages (directory + per-topic detail).
    # syntheses pre-loaded above feeds the per-topic "Saistītās sintēzes" block.
    if _want("temas"):
        topic_pages = render_topics(env, db, atmina_dir, syntheses)
        logger.info("Generated %d topic pages", topic_pages)

    # 4. Likumi/Likumprojekti/Balsojumi — laws_index_count threads through
    # to the balsojumi footer. bills + votes are passed in (already fetched
    # for the index page hero + bill_slugs autolink globals).
    laws_index_count = 0
    if _want("likumi") or _want("balsojumi"):
        laws_index_count = render_laws(env, db, atmina_dir) if _want("likumi") else db.execute(
            "SELECT COUNT(*) FROM saeima_bills WHERE base_law_slug IS NOT NULL AND base_law_slug != ''"
        ).fetchone()[0]
    if _want("bills"):
        bill_count = render_bills(env, db, atmina_dir)
        logger.info("Generated %d bill pages", bill_count)
    if _want("balsojumi"):
        render_votes(env, db, atmina_dir, votes, bills, laws_index_count)

    # Partijas (index + per-party detail pages). parties pre-fetched
    # for sitemap consumption — render_parties is self-contained
    # post-F3g.2 and no longer returns a list.
    if _want("partijas"):
        render_parties(env, db, atmina_dir, parties)
        logger.info("Generated %d party pages", len(parties))

    # Mediji (media-outlet profiles + descriptive coverage). Outlets are
    # config-driven (sources.yaml via load_outlets); coverage is computed
    # from existing documents at render time. render_mediji is self-contained.
    if _want("mediji"):
        render_mediji(env, db, atmina_dir, outlets)
        logger.info("Generated %d media outlet pages", len(outlets))

    # Personas (all tracked people — unified search). claims_count is
    # position-only so the "pozīcijas" label in the personas grid is
    # honest — it counts rhetoric, not vote attendance.
    if _want("personas"):
        render_personas(env, db, atmina_dir)

    # Ziņas
    if _want("zinas"):
        render_news(env, db, atmina_dir)

    # X / Twitter
    if _want("x"):
        render_x(env, db, atmina_dir)

    # 5. Tendences — merged into Analīzes as third tab (standalone page removed)

    # Spriedzes
    if _want("spriedzes"):
        render_tensions(env, db, atmina_dir, tensions)

    # Saites (force-graph + per-politician detail panel)
    if _want("saites"):
        render_links(env, db, atmina_dir, tensions)

    # Finanses page is manually curated — see OppTracker/Deklare2/finanses_content.html

    # 6. Analīzes combined index — already rendered by render_dashboard
    # (block #1 above) since it shares context with index.html hero.

    # 7-9. Blog: index (blog.html) + per-post (blog/<slug>.html) +
    # orphan cleanup. Render order matches prior inline blocks 7/8/9.
    if _want("blog"):
        render_blog(env, atmina_dir, blog_posts)

    # 10. Individual analysis pages (analizes/<slug>.html)
    if _want("analizes"):
        render_analyses(env, atmina_dir, analyses)

    # 10b. Individual synthesis pages (sintezes/<slug>.html)
    if _want("sintezes"):
        render_syntheses(env, atmina_dir, syntheses)

    # 11. Politician pages
    if _want("politiki"):
        politician_count = render_politicians(env, db, atmina_dir, politicians, pid_to_syntheses)

    if _want("static"):
        # 12. About page
        _render_page(env, "about.html.j2", atmina_dir / "about.html", {
            "stats": stats,
            "source_count": source_count,
            "topic_count": topic_count,
        })

        # 12b. Contacts page
        _render_page(env, "kontakti.html.j2", atmina_dir / "kontakti.html", {
            "canonical_url": f"{BASE_URL}/kontakti.html",
        })

        # 13. 404 page (served by host for any unknown URL)
        _render_page(env, "404.html.j2", atmina_dir / "404.html", {
            "canonical_url": f"{BASE_URL}/404.html",
        })

        # 14a. .htaccess — copied from tracked template (assets/htaccess.template)
        # because output/ is gitignored. LiteSpeed RewriteRules + JSON
        # pre-compressed serving live here.
        htaccess_src = ASSETS_DIR / "htaccess.template"
        if htaccess_src.exists():
            (atmina_dir / ".htaccess").write_text(
                htaccess_src.read_text(encoding="utf-8"), encoding="utf-8"
            )

        # 14. robots.txt
        (atmina_dir / "robots.txt").write_text(
            "User-agent: *\n"
            "Allow: /\n"
            "\n"
            f"Sitemap: {BASE_URL}/sitemap.xml\n",
            encoding="utf-8",
        )

        # 15. sitemap.xml
        topic_slugs = [t["slug"] for t in _fetch_topics(db)]
        _generate_sitemap(atmina_dir, politicians, parties, blog_posts, analyses, contradictions, syntheses, bills, topic_slugs)

        # 16. OG image (generate once if missing — cached across builds)
        og_image_path = atmina_dir / "assets" / "og-image.png"
        if not og_image_path.exists():
            _generate_og_image(og_image_path)

    db.close()

    logger.info(
        "Site generated: %d root pages, %d politician pages",
        9, politician_count,
    )
    print(f"Generated site in {output}")
    print("  atmina/: index, pozicijas, pretrunas, personas, partijas, zinas, X, analizes, finanses, spriedzes, saites")
    print(f"  politiki/: {politician_count} politician profile pages")
    print("  partijas/: party index + individual party pages")
    print(f"  mediji/: {len(outlets)} media outlet pages")
    print(f"  blog/: {len(blog_posts)} blog posts")
    print(f"  analizes/: {len(analyses)} analysis pages")
    print(f"  sintezes/: {len(syntheses)} synthesis pages")
    print("  SEO: robots.txt, sitemap.xml, 404.html, assets/og-image.png")

    return str(output)


def _generate_sitemap(
    atmina_dir: Path,
    politicians: list[dict[str, Any]],
    parties: list[dict[str, Any]],
    blog_posts: list[dict[str, Any]],
    analyses: list[dict[str, Any]],
    contradictions: list[dict[str, Any]] | None = None,
    syntheses: list[dict[str, Any]] | None = None,
    bills: list[dict[str, Any]] | None = None,
    topic_slugs: list[str] | None = None,
) -> None:
    """Write sitemap.xml listing all public URLs."""
    today = today_lv().isoformat()
    urls: list[str] = []

    root_pages = [
        "",  # canonical homepage
        "pozicijas.html", "pretrunas.html", "balsojumi.html",
        "partijas.html", "mediji.html", "personas.html", "zinas.html", "x.html",
        "saites.html", "finanses.html", "analizes.html", "temas.html",
        "spriedzes.html", "about.html", "kontakti.html", "blog.html",
        "statistika.html",
    ]
    for p in root_pages:
        urls.append(f"{BASE_URL}/{p}")

    for slug in topic_slugs or []:
        urls.append(f"{BASE_URL}/temas/{slug}.html")

    for p in politicians:
        urls.append(f"{BASE_URL}/politiki/{p['slug']}.html")

    for party in parties:
        sn = party.get("short_name") or ""
        if sn:
            urls.append(f"{BASE_URL}/partijas/{_party_page_slug(sn)}.html")

    for outlet in load_outlets():
        urls.append(f"{BASE_URL}/mediji/{outlet['slug']}.html")

    for post in blog_posts:
        slug = post.get("slug")
        if slug:
            urls.append(f"{BASE_URL}/blog/{slug}.html")

    for a in analyses:
        slug = a.get("slug")
        if slug:
            urls.append(f"{BASE_URL}/analizes/{slug}.html")

    for s in syntheses or []:
        slug = s.get("slug")
        if slug:
            urls.append(f"{BASE_URL}/sintezes/{slug}.html")

    for c in contradictions or []:
        urls.append(f"{BASE_URL}/pretrunas/{c['id']}.html")

    # Bills (Phase 1B-i)
    for b in bills or []:
        urls.append(f"{BASE_URL}/likumprojekti/{b['slug']}.html")

    # CSP statistika detail pages
    for tid in ["NVA011m", "PCI021m", "DSV010m", "IRS010m", "IKP010",
                "VFV050", "NNI030", "KRE020m", "IBE010", "ISP010c"]:
        urls.append(f"{BASE_URL}/statistika/{tid}.html")

    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    for url in urls:
        lines.append(
            f"  <url><loc>{url}</loc><lastmod>{today}</lastmod></url>"
        )
    lines.append("</urlset>")
    lines.append("")
    (atmina_dir / "sitemap.xml").write_text("\n".join(lines), encoding="utf-8")
    logger.info("Generated sitemap.xml with %d URLs", len(urls))


def _generate_og_image(dest: Path) -> None:
    """Generate a 1200x630 Open Graph image for social sharing.

    Uses the site's dark theme colors. Skips silently if Pillow is missing.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        logger.warning("Pillow not available — skipping og-image.png generation")
        return

    W, H = 1200, 630
    bg = (13, 16, 20)           # --bg
    text_color = (226, 228, 233)  # --text
    muted = (144, 164, 174)      # --accent (blue-grey)
    tagline_color = (139, 143, 163)
    accent_bar = (183, 28, 28)   # --accent-highlight

    img = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img)
    draw.rectangle([(0, H - 14), (W, H)], fill=accent_bar)

    try:
        title_font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 120)
        sub_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 48)
        small_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 30)
    except OSError:
        title_font = ImageFont.load_default()
        sub_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    def _centered(text: str, y: int, font, fill) -> None:
        bb = draw.textbbox((0, 0), text, font=font)
        w = bb[2] - bb[0]
        draw.text(((W - w) // 2, y), text, font=font, fill=fill)

    _centered("atmina.lv", 190, title_font, text_color)
    _centered("Politiskā atmiņa", 340, sub_font, muted)
    _centered(
        "Latvijas politiķu pozīcijas, pretrunas un balsojumi",
        430, small_font, tagline_color,
    )

    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "PNG", optimize=True)
    logger.info("Generated og-image.png")
