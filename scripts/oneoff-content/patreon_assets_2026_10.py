"""Ģenerē Patreon lapas attēlus: profila attēls 1024×1024 un vāks 2500×1000 (Patreon ieteikums, 2026-10).
Bez teksta: Patreon vāka kreisajā pusē uzliek lapas nosaukumu un aprakstu, tāpēc logo ir labajā pusē.
Fons — tā pati «nakts» krāsa kā piespraustā ieraksta attēliem (scripts/oneoff-content/pinned_2026_10_viz.py).
Palaišana: .venv/Scripts/python.exe scripts/oneoff-content/patreon_assets_2026_10.py
— raksta output/images/patreon/{avatar,cover}.html + .png (ārpus output/atmina/, tātad netiek deployots)."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/images/patreon"

NIGHT = "oklch(27% 0.055 265)"
PAPER = "oklch(96.4% 0.015 90)"
RED = "oklch(64.6% 0.19 25)"
LOGO = (f'<svg viewBox="0 0 64 64" aria-hidden="true"><circle cx="27" cy="27" r="17" fill="none" stroke="{PAPER}" stroke-width="5.5"/>'
        f'<line x1="40.5" y1="40.5" x2="52" y2="52" stroke="{PAPER}" stroke-width="5.5" stroke-linecap="round"/>'
        f'<circle cx="27" cy="27" r="6" fill="{RED}"/></svg>')


def page(w, h, css, body):
    return f"""<!doctype html>
<html lang="lv"><head><meta charset="utf-8"><style>
*, *::before, *::after {{ box-sizing:border-box; margin:0; padding:0; }}
body {{ inline-size:{w}px; block-size:{h}px; background:{NIGHT}; overflow:clip; }}
{css}
</style></head><body>{body}</body></html>"""


# Profila attēls: Patreon to apgriež aplī — logo centrā ar rezervi līdz malām.
# Logo ietvars (7…55 no 64) jau ir gandrīz centrā — bez nobīdes.
avatar = page(1024, 1024, """
body { display:grid; place-items:center; }
svg { inline-size:600px; block-size:600px; }
""", LOGO)

# Vāks: lupas aplis uz laika ass līnijas (247 + 27/64·600 = 500); laika ass ar punktiem (izteikumu secība) kreisajā/vidējā daļā, lupa labajā trešdaļā.
dots = "".join(
    f'<circle cx="{x}" cy="500" r="{r}" fill="{RED if x == 1500 else PAPER}" opacity="{1 if x == 1500 else 0.28}"/>'
    for x, r in [(300, 10), (520, 10), (700, 10), (960, 10), (1180, 10), (1500, 16)]
)
cover = page(2500, 1000, """
.axis { position:absolute; inset:0; }
.logo { position:absolute; inset-block-start:247px; inset-inline-start:1700px; inline-size:600px; block-size:600px; }
""", f"""<svg class="axis" viewBox="0 0 2500 1000" aria-hidden="true">
<line x1="0" y1="500" x2="1640" y2="500" stroke="{PAPER}" stroke-opacity="0.22" stroke-width="4"/>{dots}</svg>
<div class="logo">{LOGO}</div>""")


# Līmeņa vāks: Patreon iesaka 460×200; renderē 2× asumam. Lupa uz īsas laika ass.
tier = page(920, 400, """
.axis { position:absolute; inset:0; }
.logo { position:absolute; inset-block-start:60px; inset-inline-start:520px; inline-size:280px; block-size:280px; }
""", f"""<svg class="axis" viewBox="0 0 920 400" aria-hidden="true">
<line x1="0" y1="178" x2="590" y2="178" stroke="{PAPER}" stroke-opacity="0.22" stroke-width="3"/>
<circle cx="140" cy="178" r="7" fill="{PAPER}" opacity="0.28"/><circle cx="270" cy="178" r="7" fill="{PAPER}" opacity="0.28"/>
<circle cx="400" cy="178" r="10" fill="{RED}"/></svg>
<div class="logo">{LOGO}</div>""")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, html, w, h in [("avatar", avatar, 1024, 1024), ("cover", cover, 2500, 1000), ("tier", tier, 920, 400)]:
        src = OUT / f"{name}.html"
        src.write_text(html, encoding="utf-8")
        subprocess.run([sys.executable, str(ROOT / "scripts/render_shema.py"), str(src), str(OUT / f"{name}.png"),
                        "--width", str(w), "--height", str(h)], check=True)


if __name__ == "__main__":
    main()
