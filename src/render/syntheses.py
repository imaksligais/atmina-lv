"""Render sintezes/<slug>.html — cross-cutting synthesis pages from
``wiki/synthesis/*.md``.

Phase F3f.5 carve-out from ``src/generate.py``. Companion to
``src/render/analyses.py`` — split semantically because syntheses
have a 1:N politician mapping (``_map_syntheses_to_politicians``)
consumed by ``render_politicians`` (F3b), while analyses do not.

``_load_syntheses(atmina_dir=...)`` was made worktree-portable in
F3g-pre (PR #11); see ``tests/test_load_syntheses.py``.

Sub-page boundary: imports only from ``src.render._common`` and stdlib.
"""

from __future__ import annotations

import html as _html
import logging
import re
from pathlib import Path
from typing import Any

import markdown
from jinja2 import Environment

from src.image_variants import variant_filename
from src.render._common import (
    BASE_URL,
    WIKI_DIR,
    _parse_frontmatter,
    _render_page,
    _sanitize_html,
    _slugify,
)

logger = logging.getLogger(__name__)

# A widget marker is a paragraph whose entire content is ``[vidžets:NAME]``.
# `markdown` wraps a standalone line in ``<p>...</p>``; `bleach` does NOT
# touch the square brackets or the LV letter ``ž`` (they are text, not markup),
# so the sanitized form is literally ``<p>[vidžets:NAME]</p>``. NAME is
# ``[a-z0-9-]+``. Matched against the real rendered form (not the raw markdown),
# per the bleach-may-rewrite caution in the 2026-07-09 redesign plan.
_WIDGET_MARKER_RE = re.compile(r"<p>\s*\[vidžets:([a-z0-9-]+)\]\s*</p>")

# ``<td>—</td>`` incl. an optional ``align`` attribute (markdown `tables` emits
# ``align="center"`` etc.). Only a bare em-dash cell is treated as "empty".
_EMPTY_TD_RE = re.compile(r"<td( align=\"[a-z]+\")?>—</td>")

# ``<h2>text</h2>`` — capture inner HTML for the id slug + TOC title.
_H2_RE = re.compile(r"<h2>(.*?)</h2>", re.DOTALL)


def _enhance_synthesis_html(
    content_html: str, slug: str
) -> tuple[str, list[dict[str, str]]]:
    """Post-sanitize enrichment of a synthesis page's HTML.

    Runs AFTER ``_sanitize_html`` and applies, in order:

    a. **Widget injection.** A paragraph whose content is exactly
       ``[vidžets:NAME]`` (rendered by markdown+bleach as
       ``<p>[vidžets:NAME]</p>``; ``NAME`` = ``[a-z0-9-]+``) is replaced by the
       raw contents of ``wiki/synthesis/widgets/<slug>/<NAME>.html`` **without
       sanitization**. This is a deliberate SEC-01 carve-out: widget files are
       repo-authored and trusted exactly like Jinja templates, so they may use
       ``div``/``span``/``class`` that the bleach whitelist forbids in
       user-facing markdown. Missing file → the marker is dropped from the HTML
       and a ``logger.warning`` is emitted (render never crashes). Matching is
       done against the real rendered form, since bleach can rewrite the source.
    b. **Table scroll wrap.** Every ``<table>…</table>`` not already inside a
       ``div.table-scroll`` is wrapped in one (fixes mobile overflow). Widget
       tables are wrapped too unless the widget author already wrapped them.
    c. **Empty-cell muting.** ``<td>—</td>`` (with an optional ``align`` attr)
       gains ``class="cell-empty"``.
    d. **h2 anchors + TOC.** Each ``<h2>`` gets a unique ``id`` (via
       ``_slugify``, deduped with ``-2``/``-3`` suffixes). Returns a TOC list
       ``[{"id", "title"}]`` for the template.

    Returns ``(enhanced_html, toc)``.
    """
    # (a) Widget injection — before the table wrap so injected tables also wrap.
    widget_dir = WIKI_DIR / "synthesis" / "widgets" / slug

    def _inject(m: re.Match) -> str:
        name = m.group(1)
        widget_path = widget_dir / f"{name}.html"
        if not widget_path.exists():
            logger.warning(
                "Synthesis %s: widget %r not found (%s) — marker dropped",
                slug, name, widget_path,
            )
            return ""
        return widget_path.read_text(encoding="utf-8")

    html = _WIDGET_MARKER_RE.sub(_inject, content_html)

    # (b) Table scroll wrap — skip a table already wrapped by a widget author.
    html = _wrap_tables(html)

    # (c) Empty-cell muting.
    def _mute_cell(m: re.Match) -> str:
        align = m.group(1) or ""
        return f'<td class="cell-empty"{align}>—</td>'

    html = _EMPTY_TD_RE.sub(_mute_cell, html)

    # (d) h2 anchors + TOC.
    html, toc = _add_h2_anchors(html)
    return html, toc


def _wrap_tables(html: str) -> str:
    """Wrap each top-level ``<table>…</table>`` in ``<div class="table-scroll">``.

    Skips tables already inside a ``table-scroll`` div (widget authors may wrap
    their own tables). Walks matched ``<table>``/``</table>`` pairs so nested
    tables are handled by the outermost wrap only.
    """
    out: list[str] = []
    pos = 0
    lower = html.lower()
    while True:
        start = lower.find("<table", pos)
        if start == -1:
            out.append(html[pos:])
            break
        # Find the matching </table> accounting for nesting.
        depth = 0
        i = start
        end = -1
        while i < len(html):
            if lower.startswith("<table", i):
                depth += 1
                i += 6
            elif lower.startswith("</table>", i):
                depth -= 1
                i += 8
                if depth == 0:
                    end = i
                    break
            else:
                i += 1
        if end == -1:  # malformed — no closing tag; emit remainder untouched.
            out.append(html[pos:])
            break
        # Already wrapped? Check the nearest preceding non-space chunk.
        preceding = html[pos:start]
        if re.search(r'class="[^"]*table-scroll[^"]*"[^>]*>\s*$', preceding):
            out.append(html[pos:end])
        else:
            out.append(html[pos:start])
            out.append('<div class="table-scroll">')
            out.append(html[start:end])
            out.append("</div>")
        pos = end
    return "".join(out)


def _add_h2_anchors(html: str) -> tuple[str, list[dict[str, str]]]:
    """Add a unique ``id`` to every ``<h2>`` and return the TOC list."""
    toc: list[dict[str, str]] = []
    seen: dict[str, int] = {}

    def _sub(m: re.Match) -> str:
        inner = m.group(1)
        # Strip any nested tags for the slug/title text.
        text = _html.unescape(re.sub(r"<[^>]+>", "", inner)).strip()
        base = _slugify(text) or "sadala"
        n = seen.get(base, 0) + 1
        seen[base] = n
        anchor = base if n == 1 else f"{base}-{n}"
        toc.append({"id": anchor, "title": text})
        return f'<h2 id="{anchor}">{inner}</h2>'

    html = _H2_RE.sub(_sub, html)
    return html, toc


def _load_syntheses(atmina_dir: Path = Path("output/atmina")) -> list[dict[str, Any]]:
    """Load cross-cutting syntheses from wiki/synthesis/*.md.

    Frontmatter fields: title, description, politicians (list of partial
    slugs), topics (list), created (date).

    `syn_img_dir` resolves relative to `atmina_dir` (typically
    `<output_dir>/atmina`) rather than CWD. Fresh worktrees previously
    drifted because `output/` was empty and `has_image` defaulted to
    `False`; an explicit path lets callers (incl. char tests) point at
    the canonical image location.
    """
    syn_dir = Path("wiki/synthesis")
    if not syn_dir.exists():
        return []
    syn_img_dir = atmina_dir / "images" / "synthesis"
    syntheses: list[dict[str, Any]] = []
    for md_file in sorted(syn_dir.glob("*.md"), reverse=True):
        text = md_file.read_text(encoding="utf-8")
        fm, body = _parse_frontmatter(text)
        if not fm.get("title"):
            fm["title"] = md_file.stem.replace("-", " ").capitalize()
        body_lines = body.split("\n")
        if body_lines and body_lines[0].startswith("# "):
            body = "\n".join(body_lines[1:]).lstrip()
        md_renderer = markdown.Markdown(extensions=["tables", "fenced_code"])
        content_html = _sanitize_html(md_renderer.convert(body))
        # Post-sanitize enrichment: widget injection, table scroll wrap, empty-
        # cell muting, h2 anchors + TOC. See `_enhance_synthesis_html`.
        content_html, toc = _enhance_synthesis_html(content_html, md_file.stem)
        img_name = f"{md_file.stem}.png"
        has_image = (syn_img_dir / img_name).exists()
        syntheses.append({
            "slug": md_file.stem,
            "title": fm.get("title", ""),
            "description": fm.get("description", ""),
            "created": str(fm.get("created", "")),
            "politicians": fm.get("politicians", []) or [],
            "topics": fm.get("topics", []) or [],
            "content_html": content_html,
            # TOC only when there are ≥3 h2 headings (short pages don't warrant
            # a "Saturs" block); template gates on truthiness.
            "toc": toc if len(toc) >= 3 else [],
            "image_filename": img_name if has_image else None,
            "og_image_version": fm.get("og_image_version"),
        })
    # Newest first by `created` (YYYY-MM-DD lexical sort == chronological).
    # The reverse-filename glob above only provides a stable tiebreak for
    # syntheses sharing the same created date; recency is what drives both
    # the analizes.html grid order and the homepage `latest_synthesis` pick
    # (src/render/dashboard.py), so sort on the date explicitly.
    syntheses.sort(key=lambda s: s.get("created") or "", reverse=True)
    return syntheses


def _map_syntheses_to_politicians(
    syntheses: list[dict[str, Any]], politicians: list[dict[str, Any]]
) -> dict[int, list[dict[str, Any]]]:
    """Match synthesis frontmatter politician tokens to politician IDs.

    Tokens are partial slugs (e.g. 'silina', 'valainis'). We match against
    each politician's full slug by exact equality or suffix (after '-'),
    because full LV names typically end with the surname.
    """
    result: dict[int, list[dict[str, Any]]] = {}
    for syn in syntheses:
        for raw_token in syn.get("politicians", []):
            tok = _slugify(str(raw_token))
            if not tok:
                continue
            for p in politicians:
                pslug = p.get("slug") or ""
                if pslug == tok or pslug.endswith(f"-{tok}"):
                    result.setdefault(p["id"], []).append(syn)
                    break
    return result


def render_syntheses(
    env: Environment,
    atmina_dir: Path,
    syntheses: list[dict[str, Any]],
) -> None:
    """Emit ``atmina_dir/sintezes/<slug>.html`` per synthesis page.

    Mirrors the inline block previously at ``src/generate.py`` lines
    973-991.
    """
    sintezes_out = atmina_dir / "sintezes"
    sintezes_out.mkdir(parents=True, exist_ok=True)
    for syn in syntheses:
        out_path = sintezes_out / f"{syn['slug']}.html"
        post_ctx: dict[str, Any] = {
            "title": syn["title"],
            "date": syn["created"],
            "type_label": "Sintēze",
        }
        if syn.get("description"):
            post_ctx["description"] = syn["description"]
            post_ctx["preview"] = syn["description"]
        if syn.get("image_filename"):
            post_ctx["image_filename"] = syn["image_filename"]
            # Hero attēls = -hero.webp variants (nevis raw PNG ~600 KB); og
            # bloks blog-post.html.j2 atsevišķi ņem -og.jpg no image_dir.
            post_ctx["image_src"] = (
                f"../images/synthesis/"
                f"{variant_filename(syn['image_filename'], 'hero')}"
            )
            post_ctx["image_dir"] = "synthesis"
            # Optional cache-bust query param on og:image URL — set via
            # frontmatter `og_image_version: "2"` when social platforms
            # (Twitter, Facebook) have a stale "no image" cache entry
            # from earlier failed fetches that page-URL ?v= doesn't bust
            # because they cache image URLs independently from page URLs.
            if syn.get("og_image_version"):
                post_ctx["image_cache_bust"] = syn["og_image_version"]
        _render_page(env, "blog-post.html.j2", out_path, {
            "post": post_ctx,
            "content_html": syn["content_html"],
            "toc": syn.get("toc") or [],
            "back_href": "../analizes.html#sintezes",
            "BASE_URL": BASE_URL,
        })
