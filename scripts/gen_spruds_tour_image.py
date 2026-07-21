"""One-off image generator for the Sprūds 24.04. triple-front tour tweet.

Generates a 16:9 editorial illustration via nanobanana, writes to
docs/tweet_bank/2026-04-25-rita-drafti/sprud_tour.png.

Composition: three abstract theatres in a single frame —
1) a stylised continental Europe silhouette with two glowing markers
   in the northwest (Luxembourg + Belgium),
2) a maritime chokepoint silhouette (Persian Gulf / Hormuz) with
   a stylised mine-clearing vessel and floating mines,
3) connecting amber dotted line tracing the tour.
No text, no national flags, no faces.
"""
from pathlib import Path

from src.social_agent.visuals import render_illustration


def main() -> None:
    out_dir = Path("docs/tweet_bank/2026-04-25-rita-drafti")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "sprud_tour.png"

    subject = (
        "a single editorial frame uniting three distant defence theatres in one day: "
        "(a) a stylised continental Europe silhouette in the upper-left third with two "
        "glowing amber pinpoints in the northwest indicating Luxembourg and Belgium, "
        "small drone silhouettes hovering above them; "
        "(b) a maritime chokepoint silhouette in the lower-right third — narrow strait "
        "between two landmasses with a stylised mine-clearing vessel and a few "
        "scattered floating mines below the waterline; "
        "(c) a thin amber dotted arc connecting the European pinpoints to the strait, "
        "tracing a single-day diplomatic flight path. "
        "Background: deep navy/charcoal #0d1014. Accent: amber #eab308 used only for "
        "pinpoints, the dotted arc, and rim highlights on the vessel and drones. "
        "Cinematic editorial composition, sharp geometric shapes, slight grain, depth of field, "
        "no perspective tricks, no people, no faces, no national flags, no text labels."
    )

    payload = {
        "subject": subject,
        "style_hint": (
            "minimalist editorial illustration with strong geometric silhouettes, "
            "high contrast amber-on-dark palette, slight cinematic grain"
        ),
    }

    print(f"Generating {out_path} ...")
    render_illustration(payload, out_path)
    print(f"OK {out_path}  ({out_path.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
