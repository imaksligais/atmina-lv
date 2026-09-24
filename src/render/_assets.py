"""Asset + chrome plumbing for the public-site build (carve-out of ``_orchestrator``).

Phase 5.7 of docs/plans/2026-09-05-strukturas-tirisanas-plans.md — a pure
move of the asset/chrome cluster out of ``src.render._orchestrator``
(former L106-425). No behaviour change; ``_orchestrator`` re-imports every
name below, so ``from src.render._orchestrator import _copy_brief_images``
and ``monkeypatch.setattr(orch, ...)`` keep working
(tests/test_brief_variants_selfheal.py, tests/test_orchestrator_gating.py,
tests/test_synthesis_image_variants.py).

Carries the T15 publish-gate half of the image pipeline:
``DEPLOYABLE_BRIEF_SUFFIXES`` + ``_rejected_brief_stems`` decide which brief
imagery may reach ``output/`` at all. ``_sync_curated_chrome`` re-renders the
frozen curated pages' nav/footer from ``base.html.j2`` — the injected chrome
script is an EXTERNAL ``src=`` tag, never inline (strict CSP, CLAUDE.md
§ Output Conventions).

Imports ``src.render._common`` (leaf), ``src.db`` and ``src.image_variants``
only — never a peer page module, so the partial-init contract documented in
``src/render/__init__.py`` holds.
"""

from __future__ import annotations

import logging
import re
import shutil
import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Optional

from jinja2 import Environment

from src.db import get_db
from src.image_variants import make_variants as _make_variants
from src.render._common import (
    TEMPLATES_DIR,
    _resolve_assets_version,
)

logger = logging.getLogger(__name__)



# Page-referenced responsive brief variants only. Raw ``-.png`` masters stay in
# source as regeneration masters but are referenced by ZERO pages (audit
# 2026-05-30: 108 files / ~75 MB orphaned in output), so they are not deployed.
# og social cards are ``.jpg``; hero/card/thumb are ``.webp``. ``.svg`` covers
# the deterministic in-body weekly movers chart (src/graphics/weekly_chart.py).
DEPLOYABLE_BRIEF_SUFFIXES = (".webp", ".jpg", ".jpeg", ".svg")


def _is_variant_of(stem: str, base_stems: frozenset[str] | set[str]) -> bool:
    """True, ja ``stem`` ir kāda ``base_stems`` elementa varianta fails.

    Salīdzina pēc PREFIKSA ar atdalītāju, ne pēc pilnas sakritības: diskā guļ
    ``<base>-og.jpg`` / ``-hero.webp`` / ``-card.webp`` / ``-thumb.webp``, tāpēc
    pilnas sakritības filtrs klusi nedarītu neko. Atdalītājs ``-`` ir obligāts,
    lai viens hash-stem nekad neapēstu citu, garāku ar to pašu sākumu.
    """
    return any(stem == b or stem.startswith(f"{b}-") for b in base_stems)


def _copy_images(
    src_dir: Path,
    dest_dir: Path,
    suffixes: tuple[str, ...],
    skip_stems: frozenset[str] | set[str] = frozenset(),
) -> int:
    """Copy files whose suffix is in ``suffixes`` from ``src_dir`` to ``dest_dir``.

    A missing ``src_dir`` is a no-op returning 0; ``dest_dir`` is created if
    needed. Suffix matching is case-insensitive. Asserted in
    tests/test_orchestrator_gating.py.

    ``skip_stems`` izlaiž nosaukto bāzes stem-u VARIANTUS (sk. ``_is_variant_of``).
    Noklusējums ir tukšs, tāpēc analīžu/sintēžu izsaucēji nemainās.
    """
    if not src_dir.exists():
        return 0
    dest_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    for img in src_dir.iterdir():
        if img.is_file() and img.suffix.lower() in suffixes:
            if skip_stems and _is_variant_of(img.stem, skip_stems):
                continue
            shutil.copy2(img, dest_dir / img.name)
            copied += 1
    return copied


# Variantu faili beidzas ar kādu no šiem stem-sufiksiem — izlaižam tos, lai
# nekad neapstrādātu variantu atkārtoti caur make_variants (defensīvi: varianti
# ir .webp/.jpg, nevis .png, tāpēc *.png meklējums tos jau tāpat neaptver).
_VARIANT_STEM_SUFFIXES = ("-hero", "-og", "-card", "-thumb")


def _ensure_image_variants(
    src_dir: Path, skip_stems: frozenset[str] | set[str] = frozenset()
) -> int:
    """Generate -hero/-og/-card/-thumb variants for every source PNG in *src_dir*.

    Self-healing invariants solis: pirms attēlu kopēšanas nodrošina, ka katram
    ``<slug>.png`` blakus ir tā responsīvie varianti. Trūkstošs katalogs =
    no-op (0). ``make_variants`` ir mtime-kešots — atkārtoti renderi izlaiž jau
    svaigos variantus, tāpēc solis ir lēts. Atgriež jaunģenerēto avotu skaitu.

    ``skip_stems`` izlaiž nosauktos PNG stem-us — brief attēliem tos dod
    ``_rejected_brief_stems()``. Tās ir kalibrācijas pēdas (nepareiza metafora,
    atsaukts virsraksts, bojāta tipogrāfija), un additīvais
    ``deploy.sh --no-delete`` tos serverī paturētu mūžīgi pieejamus uzminamā
    URL, kaut neviena lapa uz tiem nesaista.

    **Šis vārts sedz tikai ĢENERĒŠANU.** Rinda, kas kļūst noraidīta PĒC tam, kad
    tās varianti jau uzģenerēti, paliek diskā, tāpēc to pašu kopu obligāti jāpadod
    arī ``_copy_brief_images`` — citādi vārts ir kosmētisks (2026-08-16: tieši tā
    `approved=2` rindas varianti tomēr nokļuva publiskajā kokā).
    """
    if not src_dir.exists():
        return 0
    generated = 0
    for png in sorted(src_dir.glob("*.png")):
        if png.stem.endswith(_VARIANT_STEM_SUFFIXES):
            continue
        if png.stem in skip_stems:
            continue
        _make_variants(png)
        generated += 1
    return generated


def _copy_brief_images(
    src_dir: Path, dest_dir: Path, skip_stems: frozenset[str] | set[str] = frozenset()
) -> int:
    """Copy page-referenced brief image variants (webp/jpg) to the deploy dir.

    Skips raw ``-.png`` masters (orphaned — see ``DEPLOYABLE_BRIEF_SUFFIXES``).
    A missing ``src_dir`` (fresh clone with no rendered briefs yet) is a no-op
    returning 0. Asserted in tests/test_orchestrator_gating.py.

    ``skip_stems`` = ``_rejected_brief_stems()``. Bez tā vārts būtu kosmētisks:
    ģenerēšanas izlaišana neaizsniedz variantus, kas jau guļ avota mapē no laika,
    kad rinda vēl bija apstiprināta.
    """
    return _copy_images(
        src_dir, dest_dir, DEPLOYABLE_BRIEF_SUFFIXES, skip_stems=skip_stems
    )


def _rejected_brief_stems(db_path: str | None = None) -> frozenset[str]:
    """Operatora noraidīto pārskata plakātu PNG stem-i — nekad neģenerē, nekad nesūta.

    Vienai nozīmei repo ir TRĪS kodējumi (mērīts 2026-08-16, saucējs 269 rindas):

    * ``approved = 2``  — atcelts/aizstāts kandidāts (79 rindas);
    * ``approved = -1`` — aizstāts, ``error_message`` formā "superseded by id=N" (4);
    * ``approved = 0``, kam TAJĀ PAŠĀ notē ir ``approved = 1`` brālis (28) — šī
      rodas, kad operators atsauc apstiprinājumu (``1 -> 0``), un tā ir DABISKĀ
      darbība. Vecie vārti zināja tikai ``2``, tāpēc 27 noraidīti plakāti
      (108 faili / 5,44 MB) nonāca dzīvajā serverī, kur additīvais deploy tos
      vairs nevar noņemt.

    ``approved = 0`` BEZ apstiprināta brāļa APZINĀTI netiek iekļauts — tie ir
    kandidāti, kas vēl var tikt apstiprināti (6 rindas mērījuma brīdī).

    Tukšs ``image_path`` tiek izmests (3 rindas — id 54, 72, 275; API-kļūdu
    audita rindas, sk. src/schema.sql brief_images komentāru): tā stem ir
    ``""``, un prefiksa salīdzinājumā tas sakristu ar KATRU failu, t.i.
    nobloķētu visus pārskatu attēlus. Tas ir šī vārta bīstamākais nepareizais
    variants.

    DB kļūda nav klusa: atgriež tukšu kopu un brīdina, t.i. atkāpjas uz veco
    uzvedību (sūta visu), nevis uz "nesūta neko".
    """
    try:
        conn = get_db(db_path)
    except sqlite3.Error:
        logger.warning("brief_images approval state unreadable — self-healing every PNG")
        return frozenset()
    try:
        rows = conn.execute(
            """
            SELECT image_path FROM brief_images b
             WHERE b.approved IN (-1, 2)
                OR (b.approved = 0
                    AND EXISTS (SELECT 1 FROM brief_images s
                                 WHERE s.note_id = b.note_id AND s.approved = 1))
            """
        ).fetchall()
    except sqlite3.Error:
        logger.warning("brief_images approval state unreadable — self-healing every PNG")
        return frozenset()
    finally:
        conn.close()
    return frozenset(
        stem for r in rows if r["image_path"] and (stem := Path(r["image_path"]).stem)
    )


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
