"""Four renderers: pretruna OG copy / chart / quote_card / illustration → PNG files."""
from __future__ import annotations

import shutil
from pathlib import Path

# Brand tokens — must match atmina.lv (see assets/style.css + templates/og-card.html.j2).
# The magenta accent (#ff3b7f) was dropped in 2026-04-21 — site uses severity-driven
# amber/yellow as the primary brand color.
BG = "#0d1014"
ACCENT = "#eab308"        # amber — same as --sev-minor_shift
TEXT = "#e2e4e9"
TEXT_DIM = "#8b8fa3"

# Path to the pregenerated pretruna OG PNGs — single source of truth for visuals.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_OG_DIR = _PROJECT_ROOT / "output" / "atmina" / "assets" / "og"


def render_pretruna_og_card(contradiction_id: int, out_path: Path) -> Path:
    """Copy the pregenerated OG card from the public site build.

    The public site rendering pipeline (`src.generate._render_og_cards`)
    already produces these 1200×630 PNGs with the full atmina.lv visual
    treatment — politician photo, party color ring, severity chip, new
    PAZIŅOJUMS/BALSOJUMS labels, chronological ordering. Reusing them as
    tweet images guarantees social output never drifts from the site.

    Raises FileNotFoundError if the site hasn't been generated recently.
    """
    src = _OG_DIR / f"pretruna-{contradiction_id}.png"
    if not src.exists():
        raise FileNotFoundError(
            f"Pretruna OG PNG missing for contradiction #{contradiction_id} "
            f"(expected {src}). Run generate_public_site() first."
        )
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, out_path)
    return out_path


def _draw_bar_chart(
    labels: list[str],
    values: list[int | float],
    title: str,
    xlabel: str,
    out_path: Path,
    bar_colors: list[str] | None = None,
    footer_right: str = "● atmina.lv",
    subtitle: str | None = None,
) -> Path:
    """Shared 1200×675 horizontal bar chart renderer — atmina.lv palette.

    labels/values are ordered top-to-bottom as the caller passes them; this
    helper reverses internally because matplotlib places the first entry at
    the bottom.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if not values:
        raise ValueError("bar chart needs at least one row")

    labels_rev = labels[::-1]
    values_rev = values[::-1]
    colors_rev = (bar_colors or [ACCENT] * len(values))[::-1]

    fig, ax = plt.subplots(figsize=(12, 6.75), dpi=100)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    ax.barh(labels_rev, values_rev, color=colors_rev, edgecolor="none", height=0.7)

    ax.tick_params(colors=TEXT_DIM, labelsize=13)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xlabel(xlabel, color=TEXT_DIM, fontsize=12, fontfamily="DejaVu Sans")

    # Title gets Georgia serif; optional subtitle slots underneath.
    title_y = 0.965 if subtitle else 0.955
    fig.text(0.065, title_y, title, color=TEXT, fontsize=26,
             fontfamily="serif", fontweight="semibold", ha="left", va="top")
    if subtitle:
        fig.text(0.065, 0.915, subtitle, color=TEXT_DIM, fontsize=13,
                 fontfamily="monospace", ha="left", va="top", alpha=0.85)

    max_v = max(values_rev) if values_rev else 1
    for i, v in enumerate(values_rev):
        ax.text(v + max_v * 0.01, i, str(v),
                color=TEXT, va="center", fontsize=14, fontweight="bold")
    fig.text(0.99, 0.02, footer_right, color=ACCENT, fontsize=13,
             ha="right", va="bottom", fontweight="bold", fontfamily="monospace")

    # Leave extra top space for title/subtitle; tight_layout would clip them.
    plt.subplots_adjust(top=0.85 if subtitle else 0.88, left=0.22, right=0.96, bottom=0.1)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, facecolor=BG, bbox_inches="tight")
    plt.close(fig)
    return out_path


def render_chart(payload: dict, out_path: Path) -> Path:
    """Horizontal bar chart of `leaderboard` → 1200×675 PNG, atmina.lv palette."""
    board = payload.get("leaderboard", [])
    if not board:
        raise ValueError("leaderboard is empty — nothing to chart")
    names = [e["name"] for e in board]
    counts = [e["count"] for e in board]
    return _draw_bar_chart(
        labels=names,
        values=counts,
        title="Aktīvākie deputāti",
        xlabel="Pozīcijas šonedēļ",
        out_path=out_path,
        subtitle=payload.get("subtitle"),
    )


# Party colors mirror src.generate.PARTY_COLORS — kept decoupled to avoid
# pulling the whole site renderer into the social agent's import graph.
_PARTY_COLORS = {
    "Jaunā Vienotība": "#0066cc",
    "Nacionālā apvienība": "#8b1b1b",
    "Progresīvie": "#e11d48",
    "Zaļo un Zemnieku savienība": "#16a34a",
    "Apvienotais saraksts": "#f97316",
    "Latvija Pirmajā Vietā": "#a855f7",
    "MMN": "#06b6d4",
    "Bezpartejisks": "#8b8fa3",
    "Latvijas attīstībai": "#eab308",
}


def render_party_chart(payload: dict, out_path: Path) -> Path:
    """Party-aggregated position counts over a window → 1200×675 bar chart."""
    rows = payload.get("rows", [])
    if not rows:
        raise ValueError("party chart needs at least one row")
    labels = [r["party"] for r in rows]
    values = [r["count"] for r in rows]
    colors = [_PARTY_COLORS.get(p, ACCENT) for p in labels]
    return _draw_bar_chart(
        labels=labels,
        values=values,
        title="Aktīvākās partijas",
        xlabel=payload.get("xlabel", "Pozīcijas šonedēļ"),
        subtitle=payload.get("subtitle"),
        bar_colors=colors,
        out_path=out_path,
    )


def render_topics_chart(payload: dict, out_path: Path) -> Path:
    """Top-N topic counts → 1200×675 bar chart, single amber color."""
    rows = payload.get("rows", [])
    if not rows:
        raise ValueError("topics chart needs at least one row")
    labels = [r["topic"] for r in rows]
    values = [r["count"] for r in rows]
    return _draw_bar_chart(
        labels=labels,
        values=values,
        title="Par ko runā politiķi",
        xlabel=payload.get("xlabel", "Pozīcijas šonedēļ"),
        subtitle=payload.get("subtitle"),
        out_path=out_path,
    )


# Severity-driven colors for contradiction categories, matching site CSS tokens.
_CATEGORY_COLORS = {
    "Vārdi vs. darbi": "#dc2626",   # --sev-direct_contradiction
    "Pozīcijas maiņa": "#eab308",   # --sev-minor_shift
    "Balsojuma maiņa": "#f97316",   # --sev-reversal
}


def render_category_chart(payload: dict, out_path: Path) -> Path:
    """Contradiction-category distribution → 1200×675 bar chart."""
    rows = payload.get("rows", [])
    if not rows:
        raise ValueError("category chart needs at least one row")
    labels = [r["category"] for r in rows]
    values = [r["count"] for r in rows]
    colors = [_CATEGORY_COLORS.get(c, ACCENT) for c in labels]
    return _draw_bar_chart(
        labels=labels,
        values=values,
        title="Pretrunu kategorijas",
        xlabel=payload.get("xlabel", "Pretrunas"),
        subtitle=payload.get("subtitle"),
        bar_colors=colors,
        out_path=out_path,
    )


TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates" / "social"


def render_quote_card(payload: dict, out_path: Path) -> Path:
    """Render quote_card.html.j2 with Playwright → 1200×675 PNG."""
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    from playwright.sync_api import sync_playwright

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    tpl = env.get_template("quote_card.html.j2")
    html = tpl.render(**payload)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 675})
        page.set_content(html, wait_until="domcontentloaded")
        page.screenshot(path=str(out_path), full_page=False,
                        clip={"x": 0, "y": 0, "width": 1200, "height": 675})
        browser.close()
    return out_path


def _nanobanana_bytes(prompt: str, **kwargs) -> bytes:
    """Indirection so tests can monkeypatch. Delegates to src.graphics.nanobanana."""
    from src.graphics.nanobanana import generate_image
    return generate_image(prompt, **kwargs)


def render_illustration(payload: dict, out_path: Path) -> Path:
    """Compose nanobanana prompt for an abstract editorial illustration."""
    subject = payload["subject"]
    style = payload.get("style_hint") or "editorial illustration"
    prompt = (
        f"{style} of: {subject}. "
        "atmina.lv brand, dark background #0d1014 with amber/yellow accent #eab308, "
        "cinematic lighting, no text, no letters, no words, no labels. "
        "16:9 composition, centered subject, depth of field."
    )
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    png = _nanobanana_bytes(prompt, aspect_ratio="16:9")
    out_path.write_bytes(png)
    return out_path
