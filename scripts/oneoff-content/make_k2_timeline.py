# -*- coding: utf-8 -*-
"""K2 Ventum hronoloģija — PIL timeline (dark, 16:9) atmina tvītam.

Ģenerē output/images/threads/2026-08-26-k2-timeline.png, kas ir PUBLICĒTA
attēla pirmavots (r/latvia + X melnraksti, docs/tweet_bank/2026-08-26-k2-ventum-tap-social.md).
Tāpēc šis fails ir repo kokā, ne _tmp_ prefiksā: publicēta attēla ģenerators,
kas dzīvo tikai darba kokā, ir viens git clean no pazušanas.

Deterministic; overlap assertion is the QA gate. 06.08. punkts labots 2026-08-27
(bija «Pašvaldība nepiekrīt apspriešanai» — atsauktais ierāmējums).
"""
from PIL import Image, ImageDraw, ImageFont

W, H = 1600, 900
BG = (16, 18, 24)
LINE = (70, 76, 90)
TXT = (232, 234, 240)
MUT = (150, 156, 170)
ACCENT = (240, 180, 60)   # amber — lēmumi/pretrunas
ACQUIT = (90, 200, 150)   # green — pozitīvs IVN
NEUT = (120, 160, 230)    # blue — procedūra

FONT = "C:/Windows/Fonts/arial.ttf"
FONTB = "C:/Windows/Fonts/arialbd.ttf"

TITLE = "«K2 Ventum»: no pozitīva atzinuma līdz atteikumam"
FOOTER = "Avoti: TAP lieta 25-TA-2896 · EVA · LSM · 2026-08-27 · atmina.lv"
OUT = "output/images/threads/2026-08-26-k2-timeline.png"

events = [
    ("2021", "Sākas ietekmes\nuz vidi\nnovērtējums", NEUT),
    ("30.09.25", "Pozitīvs\nIVN atzinums\n(322 MW)", ACQUIT),
    ("31.10.25", "Iesniegums\nKEM", NEUT),
    ("28.04.26", "MK atliek,\nuzdod atkārtotu\napspriešanu", NEUT),
    ("06.08.26", "Pašvaldība iebilst\npret apspriešanas\nkārtību", ACCENT),
    ("25.08.26", "Valdība\nneakceptē\nprojektu", ACCENT),
]

img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)

title_f = ImageFont.truetype(FONTB, 48)
year_f = ImageFont.truetype(FONTB, 40)
txt_f = ImageFont.truetype(FONT, 27)
foot_f = ImageFont.truetype(FONT, 24)

d.text((80, 55), TITLE, font=title_f, fill=TXT)

line_y = 470
margin = 140
step = (W - 2 * margin) / (len(events) - 1)
d.line((margin, line_y, W - margin, line_y), fill=LINE, width=4)

row_spans = {}
for i, (year, label, color) in enumerate(events):
    x = margin + i * step
    r = 16
    d.ellipse((x - r, line_y - r, x + r, line_y + r), fill=color, outline=BG, width=4)
    yw = d.textlength(year, font=year_f)
    d.text((min(max(x - yw / 2, 10), W - yw - 10), line_y - 120), year, font=year_f, fill=color)
    yy = line_y + 60
    for ln in label.split("\n"):
        lw = d.textlength(ln, font=txt_f)
        lx = min(max(x - lw / 2, 10), W - lw - 10)
        d.text((lx, yy), ln, font=txt_f, fill=TXT)
        row_spans.setdefault(round(yy), []).append((lx, lx + lw, year, ln))
        yy += 40

bad = []
for y, spans in row_spans.items():
    spans.sort()
    for a, b in zip(spans, spans[1:]):
        if a[1] > b[0] + 4:
            bad.append((y, a, b))
print("overlaps:", bad if bad else "nav")
assert not bad, f"Text overlaps detected: {bad}"

d.text((80, H - 70), FOOTER, font=foot_f, fill=MUT)
img.save(OUT)
print("saved", OUT)
