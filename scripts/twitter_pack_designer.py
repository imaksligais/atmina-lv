"""
Generate 3 nanobanana illustrations for the Twitter pack.

Bypasses the @graphics-designer DB orchestration (which is brief-tied) and calls
nanobanana directly with custom prompts that REUSE the canonical style template
(STYLE_VARIANTS["editorial"] + NEGATIVE_CONSTRAINTS) so the look stays on-brand.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

from src.graphics.nanobanana import generate_image  # noqa: E402
from src.graphics.prompt import NEGATIVE_CONSTRAINTS, STYLE_VARIANTS  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent.parent / "output" / "images" / "social"
OUT_DIR.mkdir(parents=True, exist_ok=True)

EDITORIAL = STYLE_VARIANTS["editorial"]


PROMPTS = [
    {
        "name": "tweet4-kapec-atmina.png",
        "concept": "Hero for article 'Kāpēc atmina.lv?' — political memory preserved vs lost",
        "prompt": "\n".join([
            EDITORIAL,
            "",
            "Topic: political memory and accountability",
            (
                "Visual Metaphor: A side-on cross-section of stacked paper "
                "documents with thin index tabs along the right edge. Most of "
                "the stack is compressed and fades into the cream paper "
                "background — its tabs blurred and indistinct. One single "
                "index tab is pulled forward and rendered in sharp focus, "
                "with a thin deep-purple line marking its edge. From this "
                "highlighted tab, two or three faint concentric arcs emanate "
                "outward, suggesting active recall. The composition is "
                "asymmetric — the stack occupies the left two-thirds, the "
                "right third is generous negative space."
            ),
            "Emotional Mood: contemplative, archival, the act of remembering",
            "Accent Color: deep purple (used only on the single highlighted tab edge)",
            "",
            (
                'Headline text (render exactly as shown, preserve Latvian '
                'diacritics): "Kāpēc atmina.lv?"'
            ),
            "",
            NEGATIVE_CONSTRAINTS,
        ]),
    },
    {
        "name": "tweet5-ka-strada.png",
        "concept": "Hero for article 'Kā strādā sistēma' — chaos to typeset order",
        "prompt": "\n".join([
            EDITORIAL,
            "",
            "Topic: how the atmina.lv data pipeline transforms raw input into structured records",
            (
                "Visual Metaphor: A bisected composition reminiscent of a "
                "letterpress galley. The left half contains a loose, gestural "
                "cluster of small abstract geometric fragments — squares, "
                "short bars, dots, tick marks — at varying angles and sizes, "
                "evoking scattered metal type or torn paper. The cluster has "
                "a sense of gravitational pull toward the center-right, with "
                "fragments closer to the seam more aligned. A single "
                "razor-clean vertical line runs from the top to the bottom of "
                "the composition at roughly the 55% mark — this is the "
                "compositional seam. The right half contains perfectly "
                "parallel horizontal stripes of varying lengths, all aligned "
                "to a left baseline at the seam — an unmistakable typeset "
                "rhythm, like lines of text in a printed column. Each stripe "
                "is rendered in deep navy ink. ONE stripe in the right-side "
                "column carries a single muted-cyan accent stroke along its "
                "length. Cream paper background with subtle aged texture, "
                "generous negative space framing the composition top and "
                "bottom."
            ),
            "Emotional Mood: typographic, transformative, the moment chaos becomes order",
            "Accent Color: muted cyan (only on the single highlighted typeset stripe)",
            "",
            (
                'Headline text (render exactly as shown, preserve Latvian '
                'diacritics): "Kā strādā atmina.lv"'
            ),
            "",
            NEGATIVE_CONSTRAINTS,
        ]),
    },
    {
        "name": "tweet6-pretruna.png",
        "concept": "Standalone — opposing forces meeting at a fault line",
        "prompt": "\n".join([
            EDITORIAL,
            "",
            "Topic: definition of a political contradiction",
            (
                "Visual Metaphor: Two large solid geometric blocks rendered "
                "in deep navy ink, mirrored horizontally — one entering from "
                "the left third of the composition, one entering from the "
                "right third. Each block has a single sharp arrow-like point "
                "directed toward the center of the composition. The two "
                "blocks DO NOT touch — between them, there is a narrow "
                "vertical gap rendered as a single clean crimson accent "
                "stroke (the fault line). From this central stroke, two or "
                "three thin concentric arcs radiate outward to suggest "
                "tension at the meeting point. The composition is "
                "symmetric and bold: rule-of-thirds, generous negative space "
                "above and below the central horizontal axis. Cream paper "
                "background with subtle aged texture. No scales, no speech "
                "bubbles, no arrows-with-tails — only the two opposing "
                "wedge-shaped blocks and the central fault line."
            ),
            "Emotional Mood: tension, opposition, irreconcilable",
            "Accent Color: crimson (only on the central vertical fault stroke "
            "and the radiating arcs)",
            "",
            (
                'Headline text (render exactly as shown, preserve Latvian '
                'diacritics): "Pretruna ≠ viedokļa maiņa"'
            ),
            "",
            NEGATIVE_CONSTRAINTS,
        ]),
    },
]


def main() -> None:
    print(f"Generating {len(PROMPTS)} designer illustrations...")
    for spec in PROMPTS:
        out = OUT_DIR / spec["name"]
        if out.exists():
            print(f"  {spec['name']}: SKIP (already exists)")
            continue
        print(f"  {spec['name']}: {spec['concept']}")
        print(f"    calling nanobanana...")
        png = generate_image(spec["prompt"], aspect_ratio="16:9")
        out.write_bytes(png)
        print(f"    saved → {out} ({len(png)} bytes)")
    print("Done.")


if __name__ == "__main__":
    main()
