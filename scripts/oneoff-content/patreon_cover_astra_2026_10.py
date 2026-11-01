"""Render an anonymous, editorial Patreon cover for atmina.lv.

Run with E:\\atmina\\.venv\\Scripts\\python.exe.
No network, database, browser, or system fonts required. The archive cards are
symbolic illustrations, not actual quotations or statistical visualizations.
All essential text fits the intersection of the supplied desktop/mobile crops.
"""
from io import BytesIO
from pathlib import Path
import math

from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/images/patreon/cover-astra.png"
FONTS = ROOT / "output/atmina/assets/fonts"
W, H, SCALE = 2500, 1000, 2
PAPER = "#F3EFE5"
INK = "#202F43"
MUTED = "#69716F"
RULE = "#CEC9BD"
RED = "#BB493C"


def font_pair(family, size, weight=400):
    result = []
    for subset in ("latin", "latin-ext"):
        name = (f"source-serif-4-normal-{subset}.woff2" if family == "serif"
                else f"jetbrains-mono-400-{subset}.woff2")
        ft = TTFont(FONTS / name)
        cmap = ft.getBestCmap()
        if "fvar" in ft:
            ft = instantiateVariableFont(ft, {"wght": weight}, inplace=True)
        ft.flavor = None
        buf = BytesIO()
        ft.save(buf)
        buf.seek(0)
        result.append((ImageFont.truetype(buf, round(size * SCALE)), cmap))
    return result


def main():
    im = Image.new("RGB", (W * SCALE, H * SCALE), PAPER)
    d = ImageDraw.Draw(im)

    def line(points, fill=RULE, width=1):
        d.line([(round(x*SCALE), round(y*SCALE)) for x, y in points],
               fill=fill, width=max(1, round(width*SCALE)), joint="curve")

    def rect(box, fill=None, outline=None, width=1):
        d.rectangle(tuple(round(v*SCALE) for v in box), fill=fill,
                    outline=outline, width=round(width*SCALE))

    def circle(x, y, r, fill, outline=None, width=1):
        d.ellipse(tuple(round(v*SCALE) for v in (x-r, y-r, x+r, y+r)),
                  fill=fill, outline=outline, width=round(width*SCALE))

    def text(value, x, baseline, size, fill=INK, family="serif", weight=400,
             centered=False, spacing=0):
        fonts = font_pair(family, size, weight)
        runs = [(char, next((f for f, cmap in fonts if ord(char) in cmap), fonts[0][0]))
                for char in value]
        length = sum(f.getlength(c)/SCALE + spacing for c, f in runs) - spacing
        if centered:
            x -= length / 2
        for char, font in runs:
            d.text((round(x*SCALE), round(baseline*SCALE)), char,
                   font=font, fill=fill, anchor="ls")
            x += font.getlength(char)/SCALE + spacing
        return length

    # Fine archive ruling at the edges, kept away from the headline.
    for y in range(110, 950, 52):
        line([(0, y), (675, y)], "#E5E0D5")
        line([(1825, y), (2500, y)], "#E5E0D5")
    line([(98, 0), (98, 1000)], "#DDD6C9")
    line([(2402, 0), (2402, 1000)], "#DDD6C9")

    # Two stacks of archive slips, with no names, dates or fabricated quotes.
    for x, y, title in [(206, 294, "VĀRDI"), (1900, 350, "DARBI")]:
        rect((x+24, y-24, x+408, y+302), "#E5DFD3", RULE)
        rect((x+12, y-12, x+396, y+314), "#EEE9DE", RULE)
        rect((x, y, x+384, y+326), "#FBF8F0", "#A8A99F", 1.5)
        text(title, x+34, y+57, 22, MUTED, "mono", spacing=3)
        line([(x+34, y+80), (x+350, y+80)])
        if title == "VĀRDI":
            text("“", x+28, y+179, 110, RED, weight=600)
            for offset, length in [(131, 218), (162, 240), (193, 166)]:
                rect((x+100, y+offset, x+length+100, y+offset+5), "#B1B4AB")
        else:
            for row, length in enumerate((228, 180, 204)):
                yy = y+116+row*44
                rect((x+35, yy, x+53, yy+18), outline="#949D96")
                line([(x+38, yy+8), (x+43, yy+13), (x+53, yy+1)], INK, 2)
                rect((x+76, yy+7, x+76+length, yy+11), "#B1B4AB")
        line([(x+34, y+273), (x+350, y+273)])
        for i in range(16):
            line([(x+36+i*7, y+291), (x+36+i*7, y+305)], "#A8A99F", 1+i%2)

    # The red thread visually links the archive across the whole cover.
    points = []
    for x in range(-10, 2511, 3):
        y = 699 + 31*math.sin((x-270)/370) + 9*math.sin(x/130)
        points.append((x, y))
    line(points, RED, 3)
    for x in (398, 1250, 2092):
        y = 699 + 31*math.sin((x-270)/370) + 9*math.sin(x/130)
        circle(x, y, 9, PAPER, RED, 2)
        circle(x, y, 3, RED)

    # Essential content stays inside x=790..1710, y=275..620.
    text("LATVIJAS POLITIKAS ATMIŅA", 1250, 317, 23, MUTED,
         "mono", centered=True, spacing=3)
    headline_width = text("Vārdi paliek.", 1250, 468, 137, INK,
                          weight=650, centered=True, spacing=-2)
    assert headline_width < 920, headline_width
    text("Arī tad, kad tos aizmirst.", 1250, 546, 45,
         centered=True)
    text("AVOTI. SECĪBA. ATBILDĪBA.", 1250, 617, 19, MUTED,
         "mono", centered=True, spacing=2)

    # Quiet framing outside the desktop crop; nothing essential in avatar area.
    line([(1130, 155), (1370, 155)], RULE)
    line([(1130, 850), (1370, 850)], RULE)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    im = im.resize((W, H), Image.Resampling.LANCZOS)
    im.save(OUT, optimize=True)
    assert im.size == (2500, 1000)
    print(OUT)


if __name__ == "__main__":
    main()
