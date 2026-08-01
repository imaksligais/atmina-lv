"""Render today's social_drafts (by IDs) to PDF tweet bank.

Usage: python scripts/render_daily_drafts_pdf.py 2026-04-22 4 5 6
"""
import base64
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.db import get_db  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "docs" / "tweet_bank"
OUT_DIR.mkdir(parents=True, exist_ok=True)

date = sys.argv[1]
draft_ids = [int(x) for x in sys.argv[2:]]

db = get_db()
rows = db.execute(
    f"SELECT id, pillar, text, image_path, score, source_data_json "
    f"FROM social_drafts WHERE id IN ({','.join('?' * len(draft_ids))}) "
    f"ORDER BY id",
    draft_ids,
).fetchall()

drafts = [dict(r) for r in rows]

style = """
<style>
  @page { size: A4; margin: 20mm; }
  body { font-family: Georgia, system-ui, sans-serif; color: #111; line-height: 1.5; }
  h1 { color: #0b0f19; border-bottom: 4px solid #eab308; padding-bottom: 8px; }
  h2 { color: #0b0f19; margin-top: 28px; }
  .meta { color: #666; font-size: 13px; margin: 4px 0 16px 0; }
  .pillar { display: inline-block; background: #eab308; color: #0d1014;
    padding: 2px 10px; border-radius: 4px; font-size: 12px;
    text-transform: uppercase; letter-spacing: 1px; margin-right: 6px; }
  img { max-width: 100%; border-radius: 6px; margin: 8px 0 14px 0;
    border: 1px solid #e5e5e5; }
  pre { background: #f5f5f7; border-left: 3px solid #eab308;
    padding: 12px 16px; border-radius: 4px; font-family:
    Consolas, monospace; font-size: 13px; white-space: pre-wrap; }
  .footer-note { color: #666; font-size: 12px; margin-top: 40px;
    border-top: 1px solid #ddd; padding-top: 12px; }
  .item { page-break-inside: avoid; margin-bottom: 22px; }
</style>
"""


def img_b64(path_str: str) -> str:
    p = Path(path_str)
    return "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()


html_parts = [
    "<!DOCTYPE html><html lang='lv'><head><meta charset='UTF-8'>",
    style, "</head><body>",
    "<h1>atmina.lv · Tweet ideju banka</h1>",
    f"<p class='meta'><strong>Datums:</strong> {date} · "
    f"<strong>Draftu ID:</strong> {', '.join(str(d['id']) for d in drafts)}</p>",
]

for i, d in enumerate(drafts, 1):
    src = img_b64(d["image_path"])
    safe = d["text"].replace("&", "&amp;").replace("<", "&lt;")
    html_parts += [
        "<div class='item'>",
        f"<h2><span class='pillar'>{d['pillar']}</span>"
        f"{i}/{len(drafts)} — Draft #{d['id']} (score {d['score']:.2f})</h2>",
        f"<img src='{src}' alt='Draft {d['id']}'>",
        "<strong>Tvīta teksts:</strong>",
        f"<pre>{safe}</pre>",
        "</div>",
    ]

html_parts += [
    "<p class='footer-note'>Ģenerēts no atmina.lv social-agent brainstorm "
    "(live DB dati). Draftu apstiprināšana caur Telegrāmu.</p>",
    "</body></html>",
]
html = "\n".join(html_parts)

slug = f"{date}-social-drafts"
html_path = OUT_DIR / f"{slug}.html"
html_path.write_text(html, encoding="utf-8")
print(f"wrote {html_path}")

pdf_path = OUT_DIR / f"{slug}.pdf"
with sync_playwright() as pw:
    b = pw.chromium.launch()
    p = b.new_page()
    p.set_content(html, wait_until="domcontentloaded")
    p.pdf(path=str(pdf_path), format="A4", print_background=True,
          margin={"top": "12mm", "bottom": "12mm", "left": "14mm", "right": "14mm"})
    b.close()
print(f"wrote {pdf_path}")
