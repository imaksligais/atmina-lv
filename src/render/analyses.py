"""Render analizes/<slug>.html — thematic analysis pages from
``content/analizes/*.md``.

Phase F3f.5 carve-out from ``src/generate.py``. Self-contained loader
``_load_analyses`` lives here so the F3g orchestrator-lift keeps one
canonical location.

The combined ``analizes.html`` index page (which lists analyses +
syntheses + blog posts + trends + context_notes) is rendered by
``src/render/dashboard.py:render_dashboard`` (post-F3f.1).

History note: ``_load_wiki_profile`` lived here as orphan code from
F3f.5 onwards — moved to ``src/render/_common.py`` in F3g.3 alongside
restoring its callsite at ``src/render/politicians.py:310``.

Sub-page boundary: imports only from ``src.render._common`` and stdlib.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import markdown
from jinja2 import Environment

from src.image_variants import variant_filename
from src.render._common import (
    BASE_URL,
    CONTENT_DIR,
    _parse_frontmatter,
    _render_page,
)


def _load_analyses() -> list[dict[str, Any]]:
    """Load analysis pages from content/analizes/*.md."""
    analizes_dir = CONTENT_DIR / "analizes"
    if not analizes_dir.exists():
        return []

    analyses = []
    for md_file in sorted(analizes_dir.glob("*.md"), reverse=True):
        text = md_file.read_text(encoding="utf-8")
        fm, body = _parse_frontmatter(text)
        if not fm.get("title"):
            fm["title"] = md_file.stem.replace("-", " ").title()

        # Strip leading # H1 — shown in the editorial pagehead already
        body_lines = body.split("\n")
        if body_lines and body_lines[0].startswith("# "):
            body = "\n".join(body_lines[1:]).lstrip()

        md_renderer = markdown.Markdown(extensions=["tables", "fenced_code"])
        content_html = md_renderer.convert(body)

        image = fm.get("image") or None
        image_filename = image.rsplit("/", 1)[-1] if image else None

        analyses.append({
            "slug": md_file.stem,
            "title": fm.get("title", ""),
            "description": fm.get("description", ""),
            "date": str(fm.get("date", "")),
            "tags": fm.get("tags", []),
            "url": f"analizes/{md_file.stem}.html",
            "content_html": content_html,
            "image_filename": image_filename,
        })
    return analyses


def render_analyses(
    env: Environment,
    atmina_dir: Path,
    analyses: list[dict[str, Any]],
) -> None:
    """Emit ``atmina_dir/analizes/<slug>.html`` per analysis page.

    Mirrors the inline block previously at ``src/generate.py`` lines
    955-971.
    """
    analizes_out = atmina_dir / "analizes"
    analizes_out.mkdir(parents=True, exist_ok=True)
    for analysis in analyses:
        out_path = analizes_out / f"{analysis['slug']}.html"
        post_ctx: dict[str, Any] = {
            "title": analysis["title"],
            "date": analysis["date"],
            "type_label": "Tematiskā analīze",
        }
        if analysis.get("image_filename"):
            post_ctx["image_filename"] = analysis["image_filename"]
            # Hero = -hero.webp variants; image_dir="analizes" nodrošina, ka
            # blog-post.html.j2 og bloks ņem -og.jpg no pareizā kataloga
            # (bez tā tas noklusēti rādīja uz images/briefs/, kur faila nav).
            post_ctx["image_src"] = (
                f"../images/analizes/"
                f"{variant_filename(analysis['image_filename'], 'hero')}"
            )
            post_ctx["image_dir"] = "analizes"
        _render_page(env, "blog-post.html.j2", out_path, {
            "post": post_ctx,
            "content_html": analysis["content_html"],
            "back_href": "../analizes.html#tematic",
            "BASE_URL": BASE_URL,
        })
