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

import hashlib
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import markdown
from jinja2 import Environment

from src.image_variants import variant_filename
from src.render._common import (
    BASE_URL,
    CONTENT_DIR,
    _label_table_cells,
    _parse_frontmatter,
    _render_page,
    _wrap_tables,
    escape_year_list_markers,
)
from src.render._common import og_render
from src.render._common.dates import lv_date_locative
from src.render.syntheses import _add_h2_anchors

# Ārēja saite `[teksts](https://…)`; attēls `![…](…)` nav avots.
_EXT_LINK = re.compile(r"(?<!!)\[[^\]]*\]\((https?://[^)\s]+)\)")
_FENCED = re.compile(r"```.*?```", re.S)
ATRADUMS_MIN_SOURCES = 2
# Mūsu pašu lapa nav pirmavots.
_OWN_HOST = "atmina.lv"


def _is_own_site(url: str) -> bool:
    host = (urlsplit(url).hostname or "").lower()
    return host == _OWN_HOST or host.endswith("." + _OWN_HOST)


def _validate_atradums(name: str, body_md: str) -> None:
    """Publicējams atradums bez atrunas vai avotiem = STOP (CLAUDE.md «Stop beats write»)."""
    if not re.search(r"^##\s+Ko mēs neapgalvojam\s*$", body_md, flags=re.M):
        raise ValueError(f"{name}: atradumam trūkst sadaļas «## Ko mēs neapgalvojam»")
    links = _EXT_LINK.findall(_FENCED.sub("", body_md))
    n = len({u for u in links if not _is_own_site(u)})
    if n < ATRADUMS_MIN_SOURCES:
        raise ValueError(
            f"{name}: atradumam vajag ≥{ATRADUMS_MIN_SOURCES} dažādas ārējas avotu saites, atrastas {n}"
        )


def _parse_og_facts(name: str, raw: Any) -> dict[str, Any] | None:
    """Neobligātais frontmatter `og:` — kartītes zīmogi un skaitļi.

    `stamps`: tieši 2 × {label, note} (laika līnija kā pretrunu kartītē),
    `gap`: teksts starp tiem, `stats`: 0–2 × {value, note}. Nepilns bloks =
    STOP: puse laika līnijas kartītē izskatītos salauzta.
    """
    if raw is None:
        return None

    def items(key: str, keys: tuple[str, str], counts: tuple[int, ...]) -> list[dict[str, str]]:
        got = raw.get(key) or []
        ok = isinstance(got, list) and len(got) in counts and all(
            isinstance(i, dict) and all(isinstance(i.get(k), str) and i[k].strip() for k in keys)
            for i in got
        )
        if not ok:
            raise ValueError(f"{name}: og.{key} jābūt {counts} ierakstiem ar laukiem {keys}")
        return [{k: i[k] for k in keys} for i in got]

    if not isinstance(raw, dict):
        raise ValueError(f"{name}: og jābūt blokam ar stamps/gap/stats")
    return {
        "stamps": items("stamps", ("label", "note"), (2,)),
        "gap": str(raw.get("gap") or ""),
        "stats": items("stats", ("value", "note"), (0, 1, 2)),
    }


def _load_analyses() -> list[dict[str, Any]]:
    """Load analysis pages from content/analizes/*.md."""
    analizes_dir = CONTENT_DIR / "analizes"
    if not analizes_dir.exists():
        return []

    analyses = []
    for md_file in sorted(analizes_dir.glob("*.md"), reverse=True):
        # utf-8-sig: ar BOM saglabātam failam `startswith("---")` citādi krīt,
        # frontmatter pazūd un `draft: true` aizietu live bez vārtiem.
        text = md_file.read_text(encoding="utf-8-sig")
        fm, body = _parse_frontmatter(text)
        # Kopīgais parsētājs YAML kļūdu norij (fm={}) — tad pazustu arī
        # `draft`/`kind`, un melnraksts aizietu live bez vārtiem. STOP.
        if text.startswith("---") and not fm:
            raise ValueError(f"{md_file.name}: frontmatter neparsējas (YAML)")
        # `draft: true` = kartīte NEparādās ne indeksā, ne sākumlapā, ne
        # sitemap — lapa vēl nav publicējama. T15 aizsardzība: deploy.sh
        # pārnes VISU output/ koku, un rutīnas renders citādi aizvestu
        # melnrakstu live (Partiju tests, 2026-09-10). Publicē, noņemot rindu.
        if fm.get("draft"):
            continue
        # Vārti PĒC draft: melnrakstam drīkst trūkt sadaļu. Nezināma `kind`
        # vērtība = STOP — drukas kļūda nedrīkst klusi kļūt par «analysis».
        raw_kind = fm.get("kind")
        if raw_kind not in (None, "", "atradums"):
            raise ValueError(
                f"{md_file.name}: nezināma kind vērtība {raw_kind!r} (atļauts: atradums vai nekas)"
            )
        kind = "atradums" if raw_kind == "atradums" else "analysis"
        if kind == "atradums":
            _validate_atradums(md_file.name, body)
        politicians = fm.get("politicians") or []
        if isinstance(politicians, str):  # `politicians: kulbergs` bez [] — nesadalīt burtos
            politicians = [politicians]
        if not fm.get("title"):
            fm["title"] = md_file.stem.replace("-", " ").title()

        # Strip leading # H1 — shown in the editorial pagehead already
        body_lines = body.split("\n")
        if body_lines and body_lines[0].startswith("# "):
            body = "\n".join(body_lines[1:]).lstrip()

        md_renderer = markdown.Markdown(extensions=["tables", "fenced_code", "md_in_html"])
        # Ritinātājs (.table-scroll) kā pārskatos/sintēzēs — tabulas rāmis un sānu ritināšana.
        content_html = _wrap_tables(_label_table_cells(md_renderer.convert(escape_year_list_markers(body))))

        image = fm.get("image") or None
        image_filename = image.rsplit("/", 1)[-1] if image else None
        # Neobligāts gaišās tēmas dvīnis (frontmatter `image_light`): kartītē
        # renderējas ABI <img>, un style.css pēc html[data-theme] rāda vajadzīgo
        # (noklusējums bez data-theme = tumšais, saskaņā ar JS-disabled atkāpi).
        image_light = fm.get("image_light") or None
        image_light_filename = (
            image_light.rsplit("/", 1)[-1] if image_light else None
        )

        analyses.append({
            "slug": md_file.stem,
            "standalone": bool(fm.get("standalone")),
            "kind": kind,
            "politicians": [str(p) for p in politicians],
            "title": fm.get("title", ""),
            "description": fm.get("description", ""),
            "date": str(fm.get("date", "")),
            "tags": fm.get("tags", []),
            "url": f"analizes/{md_file.stem}.html",
            "content_html": content_html,
            "image_filename": image_filename,
            "image_light_filename": image_light_filename,
            "og": _parse_og_facts(md_file.name, fm.get("og")) if kind == "atradums" else None,
        })
    # Jaunākā pirmā PĒC DATUMA — faila vārda kārtošana ("vad-2026" >
    # "nvo-…") sākumlapas latest_analysis un indeksa secību citādi izšķir
    # alfabēts, ne svaigums (2026-07-29 operatora pamanīts uz landing).
    analyses.sort(key=lambda a: a["date"], reverse=True)
    return analyses


def atradums_og_card(analysis: dict[str, Any]) -> dict[str, Any]:
    """Atraduma OG kartītes konteksts (veidne og-atradums.html.j2)."""
    title = analysis["title"]
    date_lv = lv_date_locative(analysis["date"], with_year=True)  # «2026. gada 17. oktobrī»
    facts = analysis.get("og") or {}
    # Ar zīmogiem un skaitļiem virsrakstam paliek ~2 rindas, ne 4.
    sizes = ((70, 54), (999, 46)) if facts else ((40, 76), (70, 64), (100, 56), (999, 50))
    return {
        "kind": "Atradums",
        "tag": "Fakti no publiskiem reģistriem — ar saitēm uz avotiem",
        "title": title,
        "title_size": og_render.og_name_size(title, sizes),
        "stamps": facts.get("stamps", []),
        "gap": facts.get("gap", ""),
        "stats": facts.get("stats", []),
        "date": date_lv,
        "url": f"atmina.lv/analizes/{analysis['slug']}",
    }


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
    og_tpl = env.get_template("og-atradums.html.j2")
    og_jobs: list[tuple[Path, str]] = []
    for analysis in analyses:
        # standalone: true frontmatter = lapa dzīvo curated/atmina/analizes/
        # (kurēts HTML, chrome sync caur _copy_curated); md fails dod tikai
        # ierakstu analizes.html indeksā — ģenerēt to pārrakstītu kurēto lapu.
        if analysis.get("standalone"):
            continue
        out_path = analizes_out / f"{analysis['slug']}.html"
        is_atradums = analysis.get("kind") == "atradums"
        post_ctx: dict[str, Any] = {
            "title": analysis["title"],
            "date": analysis["date"],
            "type_label": "Atradums" if is_atradums else "Tematiskā analīze",
            # blog-post.html.j2 og:description lasa post.preview.
            "preview": analysis["description"],
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
            if analysis.get("image_light_filename"):
                # Gaišās tēmas hero dvīnis — blog-post.html.j2 renderē abus
                # <img> ar theme-img-* klasēm (paterns kā syntheses.py).
                post_ctx["image_light_src"] = (
                    f"../images/analizes/"
                    f"{variant_filename(analysis['image_light_filename'], 'hero')}"
                )
        if is_atradums:
            # Atradumam — mūsu sepijas kartīte, ne apgriezta shēma (-og.jpg).
            og_rel = f"assets/og/atradumi/{analysis['slug']}.png"
            og_html = og_tpl.render(card=atradums_og_card(analysis))
            # ?v=: X kešo kartīti pēc URL — mainīts zīmējums = jauna adrese.
            ver = hashlib.sha256(og_html.encode("utf-8")).hexdigest()[:8]
            post_ctx["og_image_url"] = f"{BASE_URL}/{og_rel}?v={ver}"
            og_jobs.append((atmina_dir / og_rel, og_html))
        # Satura rādītājs garajām analīzēm — tas pats kā sintēzēm (≥3 h2 →
        # blog-post.html.j2 `.post-toc`), virsrakstiem `id` enkuri.
        content_html, toc = _add_h2_anchors(analysis["content_html"])
        _render_page(env, "blog-post.html.j2", out_path, {
            "post": post_ctx,
            "content_html": content_html,
            "toc": toc if len(toc) >= 3 else [],
            "back_href": (
                "../analizes.html#atradumi" if is_atradums else "../analizes.html#tematic"
            ),
            "BASE_URL": BASE_URL,
        })
    if og_jobs:
        drawn = og_render.render_og_images(og_jobs, atmina_dir)
        print(f"  assets/og/atradumi/: rendered {drawn}/{len(og_jobs)} finding preview PNGs")
