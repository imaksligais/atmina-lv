"""Build a PDF of the atmina.lv intro Twitter thread."""
import base64
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "docs" / "tweet_bank"
OUT_DIR.mkdir(parents=True, exist_ok=True)
DRAFTS = ROOT / "data" / "social" / "drafts"

TWEETS = [
    {
        "n": 1,
        "image": "intro_thread_v4_t1_hero.png",
        "text": (
            "Politiķi aizmirst, ko solīja. Mēs neaizmirstam.\n\n"
            "atmina.lv — platforma politisko pozīciju un Saeimas balsojumu "
            "izsekošanai Latvijā.\n\n"
            "148 politiķi. 1 159 pozīcijas. 104 Saeimas balsojumi ar pilnu "
            "deputātu sadalījumu. Atjaunots katru dienu.\n\n"
            "🧵"
        ),
    },
    {
        "n": 2,
        "image": "intro_thread_v4_t2_mierina.png",
        "text": (
            "1/ **Pretrunas**\n\n"
            "Kad publiska retorika atšķiras no Saeimas balsojuma.\n\n"
            "Piemērs: ZZS Saeimas priekšsēdētāja Bučas samitā paziņo, ka "
            "\"Krievijas pastrādātās zvērības nedrīkst aizmirst\" — nedēļu "
            "iepriekš Saeimā atturas balsojumā par to, lai publicētu "
            "sarakstu ar Latvijas uzņēmumiem, kas turpināja tirgoties ar "
            "Krieviju.\n\n"
            "Vārdos nosoda. Darbos atturas. Rādām abus.\n\n"
            "atmina.lv"
        ),
    },
    {
        "n": 3,
        "image": "intro_thread_v4_t3_stats.png",
        "text": (
            "2/ **Saeimas balsojumi**\n\n"
            "104 balsojumi arhīvā, katram — 100 deputātu balsis. "
            "Meklējams pēc politiķa, partijas vai likumprojekta.\n\n"
            "Aktīvākie šonedēļ publiskajā retorikā: "
            "Siliņa 32, Pūpols 25, Braže 19.\n\n"
            "Viens skats. Visas balsis."
        ),
    },
    {
        "n": 4,
        "image": "intro_thread_v4_t4_avoti.png",
        "text": (
            "3/ **Avoti**\n\n"
            "Katram ierakstam — politiķis, datums, avota links un citāts vai "
            "Saeimas balsojums.\n\n"
            "LSM · Delfi · Latvijas Avīze · TVNet · NRA · X · Saeimas arhīvs.\n\n"
            "Nekas nav izdomāts. Tu vari pārbaudīt pats."
        ),
    },
    {
        "n": 5,
        "image": "intro_thread_v4_t5_cta.png",
        "text": (
            "→ atmina.lv\n\n"
            "Bez maksas. Bez reģistrācijas. Latviešu valodā.\n\n"
            "Atceries to, ko viņi cer, ka tu aizmirsīsi."
        ),
    },
]


def img_b64(path):
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


# --- Markdown ---
md = [
    "# atmina.lv · @atmina_lv intro thread",
    "",
    "**Datums:** 2026-04-19",
    "**5 tvīti · pirmais @atmina_lv post**",
    "",
    "---",
    "",
]
for t in TWEETS:
    md.append(f"## Tvīts {t['n']}/5")
    md.append("")
    if t["image"]:
        md.append(f"![tvīts {t['n']}](../../data/social/drafts/{t['image']})")
        md.append("")
    md.append("```")
    md.append(t["text"])
    md.append("```")
    md.append("")
    md.append("---")
    md.append("")
md_path = OUT_DIR / "2026-04-19-intro-thread.md"
md_path.write_text("\n".join(md), encoding="utf-8")
print(f"wrote {md_path}")

# --- HTML + PDF ---
style = """
<style>
  @page { size: A4; margin: 18mm; }
  body { font-family: Inter, Georgia, system-ui, sans-serif; color: #111;
    line-height: 1.5; }
  h1 { color: #0b0f19; border-bottom: 4px solid #B71C1C; padding-bottom: 8px; }
  h2 { color: #0b0f19; margin-top: 24px; }
  .meta { color: #666; font-size: 13px; margin: 4px 0 22px 0; }
  img { max-width: 100%; border-radius: 6px; margin: 8px 0 14px 0;
    border: 1px solid #e5e5e5; }
  pre { background: #f5f5f7; border-left: 3px solid #B71C1C;
    padding: 12px 16px; border-radius: 4px; font-family:
    "JetBrains Mono", Consolas, monospace; font-size: 13px;
    white-space: pre-wrap; }
  .tweet { page-break-inside: avoid; margin-bottom: 26px; }
  .chip { display: inline-block; background: #B71C1C; color: #fff;
    padding: 2px 10px; border-radius: 4px; font-size: 12px;
    text-transform: uppercase; letter-spacing: 1px; margin-right: 6px; }
  .footer-note { color: #666; font-size: 12px; margin-top: 40px;
    border-top: 1px solid #ddd; padding-top: 12px; }
</style>
"""

parts = [
    "<!DOCTYPE html><html lang='lv'><head><meta charset='UTF-8'>",
    style, "</head><body>",
    "<h1>atmina.lv · @atmina_lv intro thread</h1>",
    "<p class='meta'><strong>Datums:</strong> 2026-04-19 · "
    "<strong>5 tvīti</strong> · pirmais @atmina_lv post</p>",
]
for t in TWEETS:
    safe = t["text"].replace("&", "&amp;").replace("<", "&lt;")
    parts.append("<div class='tweet'>")
    parts.append(
        f"<h2><span class='chip'>Tvīts {t['n']}/5</span></h2>"
    )
    if t["image"]:
        parts.append(
            f"<img src='{img_b64(DRAFTS / t['image'])}' alt='tvīts {t['n']}'>"
        )
    parts.append(f"<pre>{safe}</pre>")
    parts.append("</div>")
parts.append(
    "<p class='footer-note'>Ģenerēts no atmina.lv draftu pipeline. "
    "Teksti manuāli sastādīti, bildes no <code>data/social/drafts/</code>.</p>"
)
parts.append("</body></html>")
html = "\n".join(parts)

html_path = OUT_DIR / "2026-04-19-intro-thread.html"
html_path.write_text(html, encoding="utf-8")
print(f"wrote {html_path}")

pdf_path = OUT_DIR / "2026-04-19-intro-thread.pdf"
with sync_playwright() as pw:
    b = pw.chromium.launch()
    p = b.new_page()
    p.set_content(html, wait_until="domcontentloaded")
    p.pdf(
        path=str(pdf_path), format="A4", print_background=True,
        margin={"top": "10mm", "bottom": "10mm", "left": "12mm", "right": "12mm"},
    )
    b.close()
print(f"wrote {pdf_path}")
