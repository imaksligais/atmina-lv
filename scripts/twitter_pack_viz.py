"""
Generate atmina-style data-viz PNGs for the Twitter pack.

Style: editorial poster — cream paper bg, deep navy ink,
one accent color per composition. 1408x768 (16:9) to match
brief images. Georgia serif headlines, Segoe UI body.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import patheffects, rcParams
from matplotlib.patches import FancyBboxPatch, Rectangle

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

OUT_DIR = Path(__file__).resolve().parent.parent / "output" / "images" / "social"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CREAM = "#F2EBDC"
INK = "#1A1F3A"
INK_SOFT = "#3A3F5A"
ACCENT_RED = "#8B1A1A"
ACCENT_OCHRE = "#B8860B"
ACCENT_SAGE = "#5A6B3F"

WIDTH_IN, HEIGHT_IN = 14.08, 7.68  # 1408x768 at 100 dpi

rcParams["font.family"] = "serif"
rcParams["font.serif"] = ["Georgia", "DejaVu Serif"]
rcParams["axes.edgecolor"] = INK
rcParams["axes.labelcolor"] = INK
rcParams["xtick.color"] = INK
rcParams["ytick.color"] = INK


def _new_canvas() -> tuple[plt.Figure, plt.Axes]:
    fig, ax = plt.subplots(figsize=(WIDTH_IN, HEIGHT_IN), dpi=100)
    fig.patch.set_facecolor(CREAM)
    ax.set_facecolor(CREAM)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
    return fig, ax


def _save(fig: plt.Figure, name: str) -> Path:
    out = OUT_DIR / name
    fig.savefig(out, dpi=100, facecolor=CREAM, bbox_inches="tight", pad_inches=0.4)
    plt.close(fig)
    print(f"  saved → {out}")
    return out


# ---------------------------------------------------------------------
# Tweet #1 — atmina.lv skaitļos: editorial stats poster
# ---------------------------------------------------------------------
def viz_stats_poster() -> Path:
    fig, ax = _new_canvas()
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)

    # Title: "atmina.lv" small italic top-left, "skaitļos" big serif beneath
    ax.text(
        4, 92, "atmina.lv",
        fontsize=20, color=INK_SOFT, family="serif",
        style="italic", va="top",
    )
    ax.text(
        4, 84, "skaitļos",
        fontsize=46, fontweight="bold", color=INK, family="serif",
        va="top",
    )
    # Rule under heading
    ax.plot([4, 36], [69, 69], color=INK, linewidth=1.5)

    # Five stats — center-aligned columns, evenly spaced
    stats = [
        ("156", "politiķi"),
        ("1 423", "pozīcijas"),
        ("139", "Saeimas\nbalsojumi"),
        ("11", "pretrunas"),
        ("14 647", "dokumenti"),
    ]
    n = len(stats)
    margin = 6
    col_w = (100 - 2 * margin) / n
    for i, (num, label) in enumerate(stats):
        cx = margin + col_w * (i + 0.5)
        # Accent only on "11" (pretrunas) — narrative anchor
        color = ACCENT_RED if num == "11" else INK
        ax.text(
            cx, 48, num,
            fontsize=44, fontweight="bold", color=color, family="serif",
            ha="center", va="center",
        )
        ax.text(
            cx, 28, label,
            fontsize=14, color=INK_SOFT, family="serif",
            ha="center", va="center",
        )

    # Footer
    ax.plot([4, 96], [14, 14], color=INK, linewidth=0.8, alpha=0.6)
    ax.text(
        4, 8, "Visi avoti pārbaudāmi.",
        fontsize=16, color=INK, family="serif", style="italic",
        va="center",
    )
    ax.text(
        96, 8, "atmina.lv",
        fontsize=18, fontweight="bold", color=INK, family="serif",
        ha="right", va="center",
    )

    return _save(fig, "tweet1-skaitlos.png")


# ---------------------------------------------------------------------
# Tweet #2 — Top runātāji medijos pēdējās 7 dienās
# ---------------------------------------------------------------------
def viz_top_speakers_7d() -> Path:
    speakers = [
        ("Mārtiņš Krusts", 9),
        ("Lato Lapsa", 9),
        ("Evika Siliņa", 11),
        ("Guntars Vītols", 11),
        ("Baiba Braže", 12),
        ("Andris Sprūds", 12),
        ("Alvis Hermanis", 15),
        ("Andris Kulbergs", 18),
    ]

    fig, ax = _new_canvas()
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)

    # Title block
    ax.text(
        4, 92, "Mediju aktīvākie",
        fontsize=42, fontweight="bold", color=INK, family="serif",
    )
    ax.text(
        4, 84, "pēdējās 7 dienās",
        fontsize=24, color=INK_SOFT, family="serif", style="italic",
    )

    # Bars
    n = len(speakers)
    top_y = 76
    bot_y = 14
    row_h = (top_y - bot_y) / n
    max_count = max(c for _, c in speakers)
    bar_x_start = 28
    bar_max_w = 60

    for i, (name, count) in enumerate(speakers):
        y = bot_y + (i + 0.5) * row_h
        # Name on the left
        ax.text(
            26, y, name,
            fontsize=16, color=INK, family="serif",
            ha="right", va="center",
        )
        # Bar
        w = bar_max_w * count / max_count
        # Highlight the top with accent, others ink
        bar_color = ACCENT_RED if i == n - 1 else INK
        rect = Rectangle(
            (bar_x_start, y - row_h * 0.32),
            w,
            row_h * 0.55,
            facecolor=bar_color,
            edgecolor="none",
        )
        ax.add_patch(rect)
        # Count on the right
        ax.text(
            bar_x_start + w + 1.2, y, str(count),
            fontsize=18, fontweight="bold", color=bar_color, family="serif",
            ha="left", va="center",
        )

    # Footer
    ax.plot([4, 96], [9, 9], color=INK, linewidth=0.8, alpha=0.6)
    ax.text(
        4, 4.5, "Mediju izteikumi pēdējās 7 dienās · pilns saraksts atmina.lv",
        fontsize=13, color=INK_SOFT, family="serif", style="italic",
    )

    return _save(fig, "tweet2-top7d.png")


# ---------------------------------------------------------------------
# Tweet #3 — Par ko Saeima runā: top 8 tēmas
# ---------------------------------------------------------------------
def viz_top_topics() -> Path:
    topics = [
        ("Aizsardzība un drošība", 152),
        ("airBaltic", 125),
        ("Koalīcija un partijas", 112),
        ("Ukraina un Krievija", 103),
        ("Valsts pārvalde", 96),
        ("Ārpolitika", 82),
        ("Degviela un enerģētika", 73),
        ("Vēlēšanas", 71),
    ]

    fig, ax = _new_canvas()
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)

    ax.text(
        4, 92, "Par ko runā",
        fontsize=42, fontweight="bold", color=INK, family="serif",
    )
    ax.text(
        4, 84, "Latvijas politiskā sfēra",
        fontsize=24, color=INK_SOFT, family="serif", style="italic",
    )

    n = len(topics)
    top_y = 76
    bot_y = 14
    row_h = (top_y - bot_y) / n
    max_count = max(c for _, c in topics)
    bar_x_start = 38
    bar_max_w = 50

    for i, (name, count) in enumerate(topics):
        y = bot_y + (n - i - 0.5) * row_h  # top-down (largest at top)
        ax.text(
            36, y, name,
            fontsize=15, color=INK, family="serif",
            ha="right", va="center",
        )
        w = bar_max_w * count / max_count
        bar_color = ACCENT_OCHRE if i == 0 else INK
        rect = Rectangle(
            (bar_x_start, y - row_h * 0.32),
            w,
            row_h * 0.55,
            facecolor=bar_color,
            edgecolor="none",
        )
        ax.add_patch(rect)
        ax.text(
            bar_x_start + w + 1.2, y, str(count),
            fontsize=16, fontweight="bold", color=bar_color, family="serif",
            ha="left", va="center",
        )

    ax.plot([4, 96], [9, 9], color=INK, linewidth=0.8, alpha=0.6)
    ax.text(
        4, 4.5, "Pozīcijas un komentāri pa tēmām · 31 kanoniska tēma · atmina.lv",
        fontsize=13, color=INK_SOFT, family="serif", style="italic",
    )

    return _save(fig, "tweet3-tematu-top.png")


if __name__ == "__main__":
    print("Generating atmina Twitter pack data-viz...")
    viz_stats_poster()
    viz_top_speakers_7d()
    viz_top_topics()
    print("Done.")
