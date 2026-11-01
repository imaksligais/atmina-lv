"""Izpētes tāfeles lapas (analizes/<slug>.html) no content/tafeles/*.yaml."""
from __future__ import annotations

from pathlib import Path
import re

from jinja2 import Environment

from src.render._common import og_render
from src.render._common.assets import _render_page
from src.render import analyses
from src.tafele.model import GRID, Board, load_board, validate_board

TIER_LABELS = {1: "Reģistrs vai dokuments", 2: "Pēc pašu teiktā", 3: "Tikai norāde"}
KIND_LABELS = {"amats": "Amati", "ipasums": "Īpašums un akcijas", "pilsoniba": "Pilsonība un vēstules",
               "zoar": "Zoar grupa", "adrese": "Adreses", "cits": "Cits"}


def nonbreaking_numbers(text: str) -> str:
    """Keep grouped digits and their percent/currency unit on the same line."""
    text = re.sub(r"(?<!\d)\d{1,3}(?: \d{3})+(?!\d)",
                  lambda match: match[0].replace(" ", "\u00a0"), text)
    return re.sub(r"(?<=\d) (?=[%€])", "\u00a0", text)


def _context(board: Board) -> dict:
    by_entity: dict[str, list] = {e.id: [] for e in board.entities}
    for l in board.links:
        by_entity[l.from_id].append(l)
        by_entity[l.to_id].append(l)
    return {
        "board": board, "grid": GRID, "tier_labels": TIER_LABELS, "kind_labels": KIND_LABELS,
        "links_by_entity": by_entity,
        "persons": [e for e in board.entities if e.type == "person"],
        "used_kinds": sorted({l.kind for l in board.links}),
        "active_page": "analizes",
    }


def render_board(env: Environment, atmina_dir: Path, board: Board,
                 og_image_url: str | None = None, notes_html: str | None = None) -> Path:
    env.filters["tf_numbers"] = nonbreaking_numbers
    out = atmina_dir / "analizes" / f"{board.slug}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    _render_page(env, "tafele.html.j2", out, {**_context(board), "og_image_url": og_image_url, "notes_html": notes_html})
    return out


def render_tafeles(env: Environment, atmina_dir: Path,
                   data_dir: Path | None = None, articles_dir: Path | None = None) -> int:
    # Noklusējums seko analyses.CONTENT_DIR (testi to novirza uz fixture).
    data_dir = data_dir or analyses.CONTENT_DIR / "tafeles"
    articles_dir = articles_dir or analyses.CONTENT_DIR / "analizes"
    n = 0
    og_jobs: list[tuple[Path, str]] = []
    for f in sorted(Path(data_dir).glob("*.yaml")):
        board = load_board(f)
        out = atmina_dir / "analizes" / f"{board.slug}.html"
        if board.draft:
            # T15: melnraksts nedrīkst palikt kokā — deploy preflight bloķētu visu deploy.
            out.unlink(missing_ok=True)
            continue
        validate_board(board, articles_dir, require_published=True)
        # Atraduma kartīte no saraksta ieraksta (content/analizes/<slug>.md);
        # bez tā ieraksta paliek vietnes kopējā og-atmina.png.
        entry = analyses._load_analyses(articles_dir=articles_dir, slugs={board.slug})
        og_url = None
        # Saraksta ieraksta ķermenis (atrunas, avotu norādes) — jau renderēts
        # caur _load_analyses (H1 noņemts), tāpēc |safe veidnē.
        notes_html = entry[0]["content_html"] if entry else None
        if entry and entry[0]["kind"] == "atradums":
            og_url, job = analyses.atradums_og_job(env.get_template("og-atradums.html.j2"), entry[0], atmina_dir)
            og_jobs.append(job)
        render_board(env, atmina_dir, board, og_url, notes_html)
        n += 1
    if og_jobs:
        drawn = og_render.render_og_images(og_jobs, atmina_dir)
        print(f"  assets/og/atradumi/: rendered {drawn}/{len(og_jobs)} board preview PNGs")
    return n
