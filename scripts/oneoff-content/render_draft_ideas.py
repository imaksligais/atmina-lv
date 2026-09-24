"""One-off: render additional tweet draft ideas as PNGs for Telegram preview.

Not part of the MVP pipeline — dev scratchpad for 2026-04-19 sharing session.
"""
from pathlib import Path

from jinja2 import Environment, select_autoescape
from playwright.sync_api import sync_playwright
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path("data/social/drafts")
BG, ACCENT, TEXT, DIM = "#0b0f19", "#ff3b7f", "#ffffff", "#a0a7b8"

CARD_HTML = """
<!DOCTYPE html><html lang="lv"><head><meta charset="UTF-8"><style>
  html, body { margin:0; padding:0; background:#0b0f19; color:#fff;
    font-family: Inter, system-ui, sans-serif; }
  .card { width: 1200px; height: 675px; padding: 60px 72px;
    display: flex; flex-direction: column; justify-content: space-between; box-sizing: border-box; }
  .header { display: flex; align-items: baseline; justify-content: space-between; gap:40px; }
  .header h1 { font-size: 48px; margin: 0; font-weight: 600; letter-spacing: -0.5px; line-height:1.05; }
  .header .topic { font-size: 20px; color: #ff3b7f; font-weight: 700; text-transform: uppercase; letter-spacing:2px; }
  .quotes { display: flex; flex-direction: column; gap: 22px; margin-top: 28px; }
  .quote { padding: 22px 28px; background: #151a2a; border-left: 4px solid #ff3b7f;
    border-radius: 8px; }
  .quote.action { border-left-color: #60a5fa; background: #0f1729; }
  .quote p { margin: 0; font-size: 26px; line-height: 1.35; }
  .quote .label { display:inline-block; font-size:13px; letter-spacing:2px; text-transform:uppercase;
    color:#a0a7b8; margin-bottom:8px; }
  .quote.action .label { color:#60a5fa; }
  .footer { display: flex; justify-content: space-between; align-items: center;
    color: #a0a7b8; font-size: 18px; }
  .brand { color: #ff3b7f; font-weight: 700; font-size: 22px; }
</style></head><body><div class="card">
  <div class="header">
    <h1>{{ politician_name }}</h1>
    <span class="topic">{{ topic }}</span>
  </div>
  <div class="quotes">
    <div class="quote">
      <div class="label">{{ old_label }} · {{ old_date }}</div>
      <p>"{{ old_quote }}"</p>
    </div>
    <div class="quote {% if action %}action{% endif %}">
      <div class="label">{% if action %}Rīcībā{% else %}Publiski{% endif %} · {{ new_date }}</div>
      <p>{% if action %}{{ new_text }}{% else %}"{{ new_text }}"{% endif %}</p>
    </div>
  </div>
  <div class="footer"><span>{{ hook }}</span><span class="brand">atmina.lv</span></div>
</div></body></html>
"""


def render_card(ctx, out):
    env = Environment(autoescape=select_autoescape(["html"]))
    tpl = env.from_string(CARD_HTML)
    html = tpl.render(**ctx)
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page(viewport={"width": 1200, "height": 675})
        p.set_content(html, wait_until="domcontentloaded")
        p.screenshot(path=str(out), clip={"x": 0, "y": 0, "width": 1200, "height": 675})
        b.close()


# --- Idea 4: Valainis airBaltic (both REAL quotes) ---
render_card({
    "politician_name": "Viktors Valainis",
    "topic": "airBaltic",
    "old_label": "Publiski (X)",
    "old_date": "6. apr.",
    "old_quote": "Nav pieļaujami, ka airBaltic savu stratēģiju balsta uz to, ka valdība viņiem piešķirs papildu finansējumu no nodokļu maksātāju naudas",
    "new_text": "esmu gatavs pārņemt uzņēmuma pārvaldību un panākt izaugsmi, kā tas tika panākts Latvenergo",
    "new_date": "13. apr. (X)",
    "action": False,
    "hook": "Latvenergo ir 100% valsts kapitālā.",
}, OUT / "idea_4_valainis.png")
print("idea 4 OK")

# --- Idea 5: Mieriņa Krievija ---
render_card({
    "politician_name": "Daiga Mieriņa",
    "topic": "Krievija · sankcijas",
    "old_label": "Bučas samitā",
    "old_date": "1. apr.",
    "old_quote": "Kara noziegumiem nav noilguma un Krievijas pastrādātās zvērības nedrīkst aizmirst",
    "new_text": "Saeimā ATTURĒJĀS balsojumā par to, lai publicētu sarakstu ar uzņēmumiem, kas tirgojās ar Krieviju.",
    "new_date": "26. mar. (Saeima)",
    "action": True,
    "hook": "Vārdos — nosoda. Darbos — caurspīdīgumu nē.",
}, OUT / "idea_5_mierina.png")
print("idea 5 OK")

# --- Idea 6: airBaltic drama timeline ---
TIMELINE_HTML = """
<!DOCTYPE html><html lang="lv"><head><meta charset="UTF-8"><style>
  html,body { margin:0; padding:0; background:#0b0f19; color:#fff;
    font-family: Inter, system-ui, sans-serif; }
  .card { width:1200px; height:675px; padding:54px 72px; box-sizing:border-box;
    display:flex; flex-direction:column; justify-content:space-between; }
  .head h1 { font-size:52px; margin:0 0 8px 0; font-weight:800; letter-spacing:-1px; }
  .head .sub { color:#a0a7b8; font-size:19px; letter-spacing:1px; text-transform:uppercase; }
  .items { display:flex; flex-direction:column; gap:14px; margin-top:18px; }
  .item { display:flex; gap:24px; align-items:flex-start; padding:12px 14px;
    background:#121826; border-radius:8px; border-left:4px solid #ff3b7f; }
  .when { flex:0 0 72px; font-size:18px; font-weight:700; color:#ff3b7f; padding-top:2px; }
  .what { font-size:21px; line-height:1.4; color:#fff; }
  .what .who { color:#a0a7b8; font-weight:600; }
  .footer { display:flex; justify-content:space-between; align-items:center;
    color:#a0a7b8; font-size:18px; }
  .brand { color:#ff3b7f; font-weight:700; font-size:22px; }
</style></head><body><div class="card">
  <div class="head"><h1>airBaltic karš · 7 dienas</h1>
    <div class="sub">Koalīcijā no kritikas līdz šantāžai</div></div>
  <div class="items">
    <div class="item"><div class="when">6. apr.</div>
      <div class="what"><span class="who">Valainis (ZZS):</span> "nav pieļaujami valsts finansējums airBaltic"</div></div>
    <div class="item"><div class="when">13. apr.</div>
      <div class="what"><span class="who">Valainis (ZZS):</span> "gatavs pārņemt pārvaldību kā Latvenergo"</div></div>
    <div class="item"><div class="when">16. apr.</div>
      <div class="what"><span class="who">Siliņa (JV):</span> draud ar koalīcijas izjukšanu, ja ZZS nebalso par airBaltic</div></div>
    <div class="item"><div class="when">16. apr.</div>
      <div class="what"><span class="who">Kleinbergs (PRO):</span> "ZZS ar šantāžu mēģina gāzt valdību"</div></div>
    <div class="item"><div class="when">17. apr.</div>
      <div class="what"><span class="who">Kulbergs:</span> Saeimā demonstratīvi nepiedalās — "aklais balsojums"</div></div>
  </div>
  <div class="footer"><span>Kas sarūga?</span><span class="brand">atmina.lv</span></div>
</div></body></html>
"""

with sync_playwright() as pw:
    b = pw.chromium.launch()
    p = b.new_page(viewport={"width": 1200, "height": 675})
    p.set_content(TIMELINE_HTML, wait_until="domcontentloaded")
    p.screenshot(path=str(OUT / "idea_6_airbaltic_timeline.png"),
                 clip={"x": 0, "y": 0, "width": 1200, "height": 675})
    b.close()
print("idea 6 OK")

# --- Idea 7: attacks targeting Siliņa this week ---
attackers = [
    ("Šņore (NA)", "Oportūnisms · Krievijas saites"),
    ("Pūpols (NA)", "Bezjēdzīga rosināšana"),
    ("Hermanis (MMN)", "Korupcijas tīklojumi kā Orbānam"),
    ("Lapsa", "Komo brauciens → prokuratūra"),
    ("Smiltēns", "Aizstāvības taktika"),
    ("Mežals (LPV)", "Adenauera fonds · interešu konflikts"),
    ("Kulbergs", "Aklais balsojums · airBaltic"),
][::-1]

fig = plt.figure(figsize=(12, 6.75), dpi=100, facecolor=BG)
ax = fig.add_axes([0.30, 0.10, 0.65, 0.66])
ax.set_facecolor(BG)

ys = list(range(len(attackers)))
names = [a for (a, _) in attackers]
ax.scatter([1] * len(attackers), ys, s=400, color=ACCENT, zorder=3)
for y, (who, what) in enumerate(attackers):
    ax.hlines(y, xmin=0, xmax=1, color="#2a3042", linewidth=2, zorder=1)
    ax.text(1.15, y, what, color=TEXT, fontsize=15, va="center")
ax.set_yticks(ys)
ax.set_yticklabels(names, color=TEXT, fontsize=14)
ax.set_xlim(0, 3.8)
ax.set_xticks([])
for s in ax.spines.values():
    s.set_visible(False)
ax.tick_params(length=0)

fig.text(0.05, 0.91, "7 uzbrukumi pret premjēri",
         color=TEXT, fontsize=28, fontweight="bold", va="top")
fig.text(0.05, 0.85, "Evika Siliņa · 11.–17. apr. · atmina.lv",
         color=DIM, fontsize=14, va="top")
fig.text(0.96, 0.04, "atmina.lv", color=ACCENT, fontsize=14,
         fontweight="bold", ha="right", va="bottom")
fig.savefig(OUT / "idea_7_attacks_silina.png", dpi=150, facecolor=BG)
plt.close(fig)
print("idea 7 OK")
