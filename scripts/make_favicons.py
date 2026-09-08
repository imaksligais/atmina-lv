"""Ģenerē rastra faviconus no atmina.lv header logo ģeometrijas.

Google meklēšanas rezultātiem SVG favicons ar prefers-color-scheme nav
uzticams (rāda vispārīgo aizvietotāju) — vadlīnijas prasa rastra ikonu,
kuras malas garums ir 48 px daudzkārtnis. Šis skripts uzzīmē to pašu
logo, kas base.html.j2 <symbol id="atm-logo"> (lupa + sarkanais punkts),
gaišās tēmas krāsās uz krēmkrāsas fona, lai ikona ir salasāma gan
gaišā, gan tumšā pārlūka/Google UI.

Izvade: assets/favicon-96.png, assets/favicon-192.png,
assets/apple-touch-icon.png (180 px). Palaid no repo saknes:
    python scripts/make_favicons.py
"""

from pathlib import Path

from PIL import Image, ImageDraw

ASSETS = Path(__file__).resolve().parent.parent / "assets"

# Ģeometrija no base.html.j2 #atm-logo (viewBox 0 0 64 64)
RING_CX, RING_CY, RING_R = 27.0, 27.0, 17.0
STROKE = 5.5
HANDLE = (40.5, 40.5, 52.0, 52.0)
DOT_R = 6.0

BG = "#f7f3e8"      # --bg (gaišā tēma)
RING = "#1f2d4d"    # --logo-ring (gaišā tēma)
DOT = "#B71C1C"     # --logo-dot (gaišā tēma)

SS = 4              # supersample pret robainām malām
PAD = 0.88          # logo aizņem 88% no kanvas — neliela elpa kā ikonām pierasts


def draw_favicon(size: int) -> Image.Image:
    big = size * SS
    img = Image.new("RGB", (big, big), BG)
    d = ImageDraw.Draw(img)

    scale = big / 64.0 * PAD
    # 64-box logo vizuālais centrs ir ~ (29.5, 29.5), ne (32, 32)
    off_x = big / 2 - 29.5 * scale
    off_y = big / 2 - 29.5 * scale

    def pt(x: float, y: float) -> tuple[float, float]:
        return (off_x + x * scale, off_y + y * scale)

    w = STROKE * scale
    half = w / 2

    # Gredzens: PIL ellipse width zīmē uz iekšu no bbox, tāpēc bbox = ārējais rādiuss
    cx, cy = pt(RING_CX, RING_CY)
    r_out = RING_R * scale + half
    d.ellipse(
        (cx - r_out, cy - r_out, cx + r_out, cy + r_out),
        outline=RING, width=max(1, round(w)),
    )

    # Rokturis ar apaļiem galiem
    x1, y1 = pt(HANDLE[0], HANDLE[1])
    x2, y2 = pt(HANDLE[2], HANDLE[3])
    d.line((x1, y1, x2, y2), fill=RING, width=max(1, round(w)))
    for ex, ey in ((x1, y1), (x2, y2)):
        d.ellipse((ex - half, ey - half, ex + half, ey + half), fill=RING)

    # Sarkanais punkts
    dr = DOT_R * scale
    d.ellipse((cx - dr, cy - dr, cx + dr, cy + dr), fill=DOT)

    return img.resize((size, size), Image.LANCZOS)


def main() -> None:
    targets = {
        "favicon-96.png": 96,
        "favicon-192.png": 192,
        "apple-touch-icon.png": 180,
    }
    for name, size in targets.items():
        out = ASSETS / name
        draw_favicon(size).save(out, optimize=True)
        print(f"  {out.relative_to(ASSETS.parent)} ({size}x{size})")


if __name__ == "__main__":
    main()
