"""Renderē Twitter/X profila bildi 400x400 PNG no 10-twitter-avatar.svg ģeometrijas.

PNG ir gitignored (*.png), tāpēc regenere ar:
    .venv/Scripts/python design/logo-drafts/render_twitter_avatar.py
"""
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).parent / "twitter-avatar-{name}-400.png"

S = 4            # supersampling faktors antialiasingam
SIZE = 400       # gala izmērs px
K = 6.25 * S     # 64-box vienības -> px (supersampled)

VARIANTS = {
    "light":  {"tile": "#37474F", "ring": "#ECEFF1", "dot": "#EF5350"},
    "dark":   {"tile": "#0d1014", "ring": "#ECEFF1", "dot": "#EF5350"},
    "header": {"tile": "#0d1014", "ring": "#90A4AE", "dot": "#EF5350"},
}


def sc(v: float) -> float:
    return v * K


def main() -> None:
    for name, v in VARIANTS.items():
        w = SIZE * S
        img = Image.new("RGB", (w, w), v["tile"])
        d = ImageDraw.Draw(img)

        lw = int(round(5 * K))
        # Rokturis (pirms gredzena — sākums paliek zem tā)
        x1, y1, x2, y2 = sc(40.5), sc(40.5), sc(51), sc(51)
        d.line([x1, y1, x2, y2], fill=v["ring"], width=lw)
        r = lw / 2
        d.ellipse([x1 - r, y1 - r, x1 + r, y1 + r], fill=v["ring"])
        d.ellipse([x2 - r, y2 - r, x2 + r, y2 + r], fill=v["ring"])
        # Lēcas gredzens
        cx, cy, rr = sc(29), sc(29), sc(15)
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=v["ring"], width=lw)
        # Punkts
        dr = sc(5.5)
        d.ellipse([cx - dr, cy - dr, cx + dr, cy + dr], fill=v["dot"])

        img = img.resize((SIZE, SIZE), Image.LANCZOS)
        out = OUT.with_name(OUT.name.format(name=name))
        img.save(out)
        print(f"saved {out} {img.size}")


if __name__ == "__main__":
    main()
