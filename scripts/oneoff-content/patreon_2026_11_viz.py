"""Patreon novembra pārskata 1. attēls «Pārskats skaitļos» (forma kā patreon_2026_10_viz.py).
Trīs attēli: 1 skaitļi, 2 kvīts (no src/graphics/templates/kvits.html; Patreon Earnings 6.11.), 3 izmaksas (oktobra saturs).
Palaišana: .venv/Scripts/python.exe scripts/oneoff-content/patreon_2026_11_viz.py"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import patreon_2026_10_viz as oct_viz  # noqa: E402

# DB 2026-11-06, logs 20.10.–5.11.: claims position (routine_day_window)=952; saeima_votes (vote_date)=121;
# daily_brief ar subjekta datumu šajā logā=17; contradictions confirmed=1 (detected_at)=7
TILES = [
    (952, "politiķu pozīcijas ar saiti uz avotu"),
    (121, "Saeimas balsojumi"),
    (17, "dienas pārskati"),
    (7, "publicētas pretrunas"),
]
NEW = [
    "6 jauni «Atradumi» un izpētes tāfele",
    "«Nedēļas stāsti»: jauna nedēļas pārskata forma",
    "15. Saeimas balsojumi no pirmās sēdes",
]

body = f"""<div class="tiles">{"".join(f'<div><b class="num">{oct_viz.nb(v)}</b><span>{t}</span></div>' for v, t in TILES)}</div>
<ul class="news"><h2>JAUNS VIETNĒ</h2>{"".join(f"<li>{t}</li>" for t in NEW)}</ul>
<div class="foot"><span>Mūs atbalsta <b class="num">2</b> cilvēki.</span><span>20. oktobris – 5. novembris</span></div>"""

oct_viz.TOTAL = 3
html = oct_viz.page(1, "Pārskats skaitļos", "Kas paveikts kopš iepriekšējā pārskata.", body, oct_viz.css1)
html = html.replace("Patreon oktobra pārskats", "Patreon novembra pārskats").replace("patreon_2026_10_viz", "patreon_2026_11_viz")


html3 = oct_viz.page(3, "Kur aiziet atbalsts", "Atbalsts sedz šīs izmaksas.", oct_viz.body2.replace("<p>Viss saturs bez maksas visiem.</p>", ""), oct_viz.css2)
html3 = html3.replace("oktobra pārskats", "novembra pārskats").replace("patreon_2026_10_viz", "patreon_2026_11_viz")


def kvits():
    tpl = (oct_viz.ROOT / "src/graphics/templates/kvits.html").read_text(encoding="utf-8")
    tpl = tpl.replace("../../../output/", "../../output/")
    tpl = tpl[:tpl.index("<!-- Paraugs")] + "<!-- Patreon novembra pārskats, attēls 2/3; no kvits.html. -->" + tpl[tpl.index("<html"):]
    say_a = tpl.index('<h1>')
    say_b = tpl.index('</h1>')
    tpl = tpl[:say_a] + "<h1>Mums ir divi atbalstītāji. <em>Paldies.</em>" + tpl[say_b:]
    tpl = tpl.replace("</style>", ".row.total { font-size:26px; white-space:nowrap; } .row.total .v { font-size:36px; white-space:nowrap; }</style>")
    a = tpl.index('<article class="receipt">')
    b = tpl.index("</article>")
    return tpl[:a] + """<article class="receipt">
    <header><b>atmina.lv</b><span>Ienākumi · 2026. gada oktobris</span></header>
    <div class="cut"></div>
    <div class="row"><span>Saņemts</span><span class="v">13,00 €</span></div>
    <div class="row minus"><span>Patreon komisija</span><span class="v">−1,30 €</span></div>
    <div class="row minus"><span>Maksājumu apstrāde</span><span class="v">−1,60 €</span></div>
    <div class="cut"></div>
    <div class="row total"><span>Pēc Patreon maksām</span><span class="v">10,10 €</span></div>
    <p class="note">Pirms izmaksas maksas un nodokļiem.<br>Viss saturs paliek bez maksas visiem.</p>
  """ + tpl[b:]


def main():
    for slug, doc in {"1-skaitli": html, "2-kvits": kvits(), "3-izmaksas": html3}.items():
        h = oct_viz.OUT_HTML / f"patreon-2026-11-{slug}.html"
        h.write_text(doc, encoding="utf-8")
        png = oct_viz.OUT_PNG / f"2026-11-{slug}.png"
        subprocess.run([sys.executable, str(oct_viz.ROOT / "scripts/render_shema.py"), str(h), str(png)], check=True, timeout=120)


if __name__ == "__main__":
    main()
