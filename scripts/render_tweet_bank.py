"""Build a tweet-bank document (Markdown + PDF) from the draft ideas
rendered for 2026-04-19 sharing session.
"""
import base64
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "docs" / "tweet_bank"
OUT_DIR.mkdir(parents=True, exist_ok=True)

DRAFTS = ROOT / "data" / "social" / "drafts"

IDEAS = [
    {
        "n": 1,
        "pillar": "Pretrunas",
        "title": "Maija Armaņeva — 2. pensiju līmenis",
        "image": "idea_1_armaneva_v2.png",
        "text": (
            'Par X: "cilvēkiem tiktu dotas tiesības pašiem lemt, kā rīkoties '
            'ar savu 2. pensiju līmenī uzkrāto kapitālu" (28. febr.)\n\n'
            "Saeimā: Balsoja PRET 11 391 pilsoņu iesniegumu, kas prasīja "
            "tieši to pašu. (1. apr.)\n\n"
            "📊 atmina.lv/maija-armaneva"
        ),
        "meta": "direct_contradiction · salience 0.85 · LPV",
    },
    {
        "n": 2,
        "pillar": "Pretrunas",
        "title": "Evika Siliņa — sadarbība ar ZZS",
        "image": "idea_2_silina_v2.png",
        "text": (
            'Oktobrī par ZZS: "Viņi ir pieviluši savu doto solījumu" (31. okt. 2025)\n\n'
            "Martā: Paziņo, ka neizslēdz sadarbību ar ZZS arī pēc vēlēšanām. "
            "(30. mar. 2026)\n\n"
            "5 mēneši. Kas mainījās?\n\n"
            "📊 atmina.lv/evika-silina"
        ),
        "meta": "reversal · salience 0.6 · JV",
    },
    {
        "n": 3,
        "pillar": "Nedēļas stats",
        "title": "Aktīvākie politiķi (ISO W16)",
        "image": "idea_3_stats_v3.png",
        "text": (
            "32 pozīcijas 7 dienās.\n\n"
            "Kurš runāja visvairāk (11.–17. apr.):\n"
            "Siliņa 32 · Pūpols 25 · Braže 19 · Lapsa 15 · Valainis 14\n\n"
            "📊 Pilns top 10: atmina.lv/statistika"
        ),
        "meta": "weekly leaderboard · ISO W16",
    },
    {
        "n": 4,
        "pillar": "Pretrunas",
        "title": "Viktors Valainis — airBaltic",
        "image": "idea_4_valainis.png",
        "text": (
            '6. apr.: "Nav pieļaujami, ka airBaltic savu stratēģiju balsta '
            'uz to, ka valdība viņiem piešķirs papildu finansējumu."\n\n'
            '13. apr.: "esmu gatavs pārņemt uzņēmuma pārvaldību un panākt '
            'izaugsmi, kā tas tika panākts Latvenergo."\n\n'
            "Latvenergo ir 100% valsts kapitālā.\n\n"
            "Septiņas dienas. Kas mainījās? 🧐\n\n"
            "📊 atmina.lv/viktors-valainis"
        ),
        "meta": "minor_shift · salience 0.5 · ZZS · abi citāti reāli",
    },
    {
        "n": 5,
        "pillar": "Pretrunas",
        "title": "Daiga Mieriņa — Krievija",
        "image": "idea_5_mierina.png",
        "text": (
            'Bučas samitā: "Kara noziegumiem nav noilguma un Krievijas '
            'pastrādātās zvērības nedrīkst aizmirst." (1. apr.)\n\n'
            "Saeimā 6 dienas pirms: Atturējās balsojumā par importētāju "
            "saraksta publicēšanu — kas tirgojās ar Krieviju. (26. mar.)\n\n"
            "Vārdos — nosoda. Darbos — caurspīdīgumu nē.\n\n"
            "📊 atmina.lv/daiga-mierina"
        ),
        "meta": "minor_shift · salience 0.6 · ZZS · koalīcijas disciplīna",
    },
    {
        "n": 6,
        "pillar": "Sāga · Timeline",
        "title": "airBaltic karš · 7 dienas",
        "image": "idea_6_airbaltic_timeline.png",
        "text": (
            "7 dienas. Koalīcijā.\n\n"
            "No Valaiņa kritikas (6. apr.) → Valainis pieprasa pārņemt (13. apr.) → "
            "Siliņa draud ar koalīcijas izjukšanu (16. apr.) → Kleinbergs pretī: "
            '"šantāža" → Kulbergs Saeimā demonstratīvi nepiedalās.\n\n'
            "Kas sarūga koalīcijā?\n\n"
            "📊 atmina.lv/airbaltic"
        ),
        "meta": "multi-event · tensions #49, #50, #53, #54 + Valainis #24",
    },
    {
        "n": 7,
        "pillar": "Meta · Nedēļas chart",
        "title": "7 uzbrukumi pret premjeri",
        "image": "idea_7_attacks_silina.png",
        "text": (
            "7 uzbrukumi pret premjeri. 7 dienas.\n\n"
            "No Nacionālās apvienības (Šņore, Pūpols) līdz LPV (Mežals), MMN "
            '(Hermanis) — visi bija uz grīdas.\n\n'
            "Oportūnisms, korupcija, \"aklais balsojums\", Komo brauciens → "
            "prokuratūra.\n\n"
            "Kas notiek ap Siliņu?\n\n"
            "📊 atmina.lv/evika-silina#uzbrukumi"
        ),
        "meta": "7 tensions targeting Siliņa · 11.–17. apr.",
    },
]


# --- Markdown ---
md_lines = [
    "# atmina.lv · Tweet ideju banka",
    "",
    "**Datums:** 2026-04-19",
    "**Avots:** candidate pool no live DB (11 pretrunas + stats + 21 highlights)",
    "",
    "---",
    "",
]
for idea in IDEAS:
    img_rel = f"../../data/social/drafts/{idea['image']}"
    md_lines += [
        f"## {idea['n']}/7 · {idea['pillar']} — {idea['title']}",
        "",
        f"![{idea['title']}]({img_rel})",
        "",
        "**Tvīta teksts:**",
        "",
        "```",
        idea["text"],
        "```",
        "",
        f"_{idea['meta']}_",
        "",
        "---",
        "",
    ]
md_path = OUT_DIR / "2026-04-19-idejas.md"
md_path.write_text("\n".join(md_lines), encoding="utf-8")
print(f"wrote {md_path}")


# --- HTML/PDF with embedded images ---
def img_b64(path):
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


style = """
<style>
  @page { size: A4; margin: 20mm; }
  body { font-family: Inter, Georgia, system-ui, sans-serif; color: #111;
    line-height: 1.5; }
  h1 { color: #0b0f19; border-bottom: 4px solid #ff3b7f; padding-bottom: 8px; }
  h2 { color: #0b0f19; margin-top: 28px; }
  .meta { color: #666; font-size: 13px; margin: 4px 0 16px 0; }
  .pillar { display: inline-block; background: #ff3b7f; color: #fff;
    padding: 2px 10px; border-radius: 4px; font-size: 12px;
    text-transform: uppercase; letter-spacing: 1px; margin-right: 6px; }
  img { max-width: 100%; border-radius: 6px; margin: 8px 0 14px 0;
    border: 1px solid #e5e5e5; }
  pre { background: #f5f5f7; border-left: 3px solid #ff3b7f;
    padding: 12px 16px; border-radius: 4px; font-family:
    "JetBrains Mono", Consolas, monospace; font-size: 13px;
    white-space: pre-wrap; }
  .footer-note { color: #666; font-size: 12px; margin-top: 40px;
    border-top: 1px solid #ddd; padding-top: 12px; }
  .item { page-break-inside: avoid; margin-bottom: 22px; }
</style>
"""

html_parts = [
    "<!DOCTYPE html><html lang='lv'><head><meta charset='UTF-8'>",
    style, "</head><body>",
    "<h1>atmina.lv · Tweet ideju banka</h1>",
    "<p class='meta'><strong>Datums:</strong> 2026-04-19 · "
    "<strong>Avots:</strong> candidate pool no live DB "
    "(11 pretrunas + stats + 21 highlights)</p>",
]

for idea in IDEAS:
    img_path = DRAFTS / idea["image"]
    src = img_b64(img_path)
    safe_text = idea["text"].replace("&", "&amp;").replace("<", "&lt;")
    html_parts += [
        "<div class='item'>",
        f"<h2><span class='pillar'>{idea['pillar']}</span>"
        f"{idea['n']}/7 — {idea['title']}</h2>",
        f"<img src='{src}' alt='{idea['title']}'>",
        "<strong>Tvīta teksts:</strong>",
        f"<pre>{safe_text}</pre>",
        f"<p class='meta'><em>{idea['meta']}</em></p>",
        "</div>",
    ]

html_parts += [
    "<p class='footer-note'>Ģenerēts no atmina.lv social-agent pipeline "
    "(manuāli sastādīti teksti, dati no DB).</p>",
    "</body></html>",
]
html = "\n".join(html_parts)

html_path = OUT_DIR / "2026-04-19-idejas.html"
html_path.write_text(html, encoding="utf-8")
print(f"wrote {html_path}")

pdf_path = OUT_DIR / "2026-04-19-idejas.pdf"
with sync_playwright() as pw:
    b = pw.chromium.launch()
    p = b.new_page()
    p.set_content(html, wait_until="domcontentloaded")
    p.pdf(path=str(pdf_path), format="A4", print_background=True,
          margin={"top": "12mm", "bottom": "12mm", "left": "14mm", "right": "14mm"})
    b.close()
print(f"wrote {pdf_path}")
