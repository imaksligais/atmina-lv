"""Laika joslas attēla ģenerators — teksta attēlus zīmē ar kodu, ne ģenerē.

Sociālajiem materiāliem (Reddit/X), kur notikumu secība jārāda precīzi:
attēlu ģeneratori LV diakritiku tekstā kropļo, tāpēc viss teksts ir PIL
(Georgia — tas pats serifs, ko lieto vietnes virsraksti; krāsas = tumšā tēma).

    .venv/Scripts/python.exe scripts/make_timeline.py --events notikumi.json \
        --title "Virsraksts" --out output/images/social/timeline.png

events JSON — saraksts hronoloģiskā secībā:
    [{"date": "10.07.", "text": "Notikums īsā tekstā", "accent": true}, ...]
`accent` (neobligāts) iezīmē mezglu sarkanā akcenta krāsā (pagrieziena punkts).
Ietilpība: 3–7 notikumi; teksts aplaužas ~24 zīmēs, ieteicams <= 3 rindas.
"""

import argparse
import json
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H, SS = 1600, 900, 2
BG = (13, 16, 20)            # --bg (tumšā tēma)
TEXT = (226, 228, 233)       # --text
MUTED = (144, 164, 174)      # --accent (zili pelēkais)
LINE = (62, 72, 84)          # klusināta ass līnija
ACCENT = (239, 83, 80)       # --logo-dot (tumšā tēma)
BAR = (183, 28, 28)          # sarkanā josla kā og-image


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(f"C:/Windows/Fonts/{name}", size * SS)


def render(title: str, events: list[dict], out_path: Path) -> None:
    img = Image.new("RGB", (W * SS, H * SS), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([(0, (H - 12) * SS), (W * SS, H * SS)], fill=BAR)

    f_title = _font("georgiab.ttf", 46)
    f_date = _font("georgiab.ttf", 26)
    f_text = _font("georgia.ttf", 24)
    f_brand = _font("georgia.ttf", 20)

    d.text((70 * SS, 56 * SS), title, font=f_title, fill=TEXT)

    brand = "atmina.lv"
    bb = d.textbbox((0, 0), brand, font=f_brand)
    d.text((W * SS - (bb[2] - bb[0]) - 60 * SS, (H - 52) * SS),
           brand, font=f_brand, fill=MUTED)

    n = len(events)
    axis_y = int(H * 0.52) * SS
    margin = 130 * SS
    step = ((W * SS - 2 * margin) / (n - 1)) if n > 1 else 0
    d.line((margin, axis_y, W * SS - margin, axis_y),
           fill=LINE, width=3 * SS)

    r = 11 * SS
    for i, ev in enumerate(events):
        x = int(margin + i * step)
        color = ACCENT if ev.get("accent") else MUTED
        d.ellipse((x - r, axis_y - r, x + r, axis_y + r), fill=color)
        d.ellipse((x - r - 4 * SS, axis_y - r - 4 * SS,
                   x + r + 4 * SS, axis_y + r + 4 * SS),
                  outline=color, width=2 * SS)

        above = i % 2 == 0
        lines = textwrap.wrap(ev["text"], width=24)
        block_h = len(lines) * 32 * SS
        date_bb = d.textbbox((0, 0), ev["date"], font=f_date)
        date_w = date_bb[2] - date_bb[0]

        if above:
            ty = axis_y - 46 * SS - block_h - 40 * SS
        else:
            ty = axis_y + 46 * SS

        def _tx(width: float, cx: float = x) -> float:
            # malējiem mezgliem teksts paliek kanvas iekšpusē
            return min(max(cx - width / 2, 50 * SS), W * SS - 50 * SS - width)

        d.text((_tx(date_w), ty), ev["date"], font=f_date, fill=TEXT)
        ty += 40 * SS
        for ln in lines:
            lb = d.textbbox((0, 0), ln, font=f_text)
            d.text((_tx(lb[2] - lb[0]), ty), ln, font=f_text, fill=MUTED)
            ty += 32 * SS

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.resize((W, H), Image.LANCZOS).save(out_path, optimize=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="atmina laika joslas attēls")
    ap.add_argument("--events", required=True, help="JSON fails ar notikumiem")
    ap.add_argument("--title", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    events = json.loads(Path(args.events).read_text(encoding="utf-8"))
    if not 2 <= len(events) <= 8:
        raise SystemExit(f"2–8 notikumi, saņemti {len(events)}")
    render(args.title, events, Path(args.out))
    print(f"OK: {args.out} ({len(events)} notikumi)")


if __name__ == "__main__":
    main()
