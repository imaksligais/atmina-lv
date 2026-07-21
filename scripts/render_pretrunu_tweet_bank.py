"""Build a review document (Markdown + HTML + PDF) for all unposted
pretrunas drafts, using the atmina.lv visual language.

Style matches the post-2026-04-21 overhaul: amber accent (#eab308) instead
of magenta, Georgia serif + JetBrains Mono labels, OG card images reused
directly from the public site build.
"""
from __future__ import annotations

import argparse
import base64
from pathlib import Path

from playwright.sync_api import sync_playwright

from src.social_agent.candidates import fetch_pretrunas_candidates
from src.social_agent.drafters import draft_pretrunas

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "docs" / "tweet_bank"
OG_DIR = ROOT / "output" / "atmina" / "assets" / "og"

# Politicians / contradictions we've already posted manually or via agent.
# Manual tweets don't go through social_drafts, so candidates can't auto-dedupe.
ALREADY_TWEETED = {13}  # Mieriņa — https://x.com/AtminaLV/status/2046649588853985325


def build(output_date: str) -> tuple[Path, Path, Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    candidates = [
        c for c in fetch_pretrunas_candidates()
        if c["contradiction_id"] not in ALREADY_TWEETED
    ]
    # Sort by contradiction id ascending for stable ordering.
    candidates.sort(key=lambda c: c["contradiction_id"])

    items: list[dict] = []
    for c in candidates:
        cid = c["contradiction_id"]
        og_path = OG_DIR / f"pretruna-{cid}.png"
        if not og_path.exists():
            print(f"[skip] #{cid}: OG PNG missing at {og_path}")
            continue
        text = draft_pretrunas(c)
        severity = c.get("severity") or "—"
        salience = c.get("salience")
        meta_bits = [f"pretruna #{cid:03d}", severity]
        if salience is not None:
            meta_bits.append(f"salience {salience:.2f}")
        items.append({
            "id": cid,
            "politician": c["politician_name"],
            "topic": c["topic"],
            "text": text,
            "og_path": og_path,
            "meta": " · ".join(meta_bits),
        })

    if not items:
        raise SystemExit("No unposted pretrunas to render.")

    # --- Markdown ---
    md_lines = [
        "# atmina.lv · Pretrunu tvītu bank",
        "",
        f"**Datums:** {output_date}",
        f"**{len(items)} draft{'s' if len(items) == 1 else 'i'}** — nepublicētas pretrunas, "
        "teksts ģenerēts caur `src.social_agent.drafters.draft_pretrunas`, "
        "attēls kopēts no `/assets/og/pretruna-{id}.png`.",
        "",
        "**Stils:** jaunā pretrunu kartes valoda (2026-04-21) — PAZIŅOJUMS/BALSOJUMS labels, "
        "chronological sort, severity glyph, amber accent.",
        "",
        "---",
        "",
    ]
    for it in items:
        img_rel = f"../../output/atmina/assets/og/pretruna-{it['id']}.png"
        md_lines += [
            f"## #{it['id']:03d} — {it['politician']} · {it['topic']}",
            "",
            f"![Pretruna #{it['id']}]({img_rel})",
            "",
            "**Tvīta teksts:**",
            "",
            "```",
            it["text"],
            "```",
            "",
            f"_{it['meta']}_",
            "",
            "---",
            "",
        ]
    md_path = OUT_DIR / f"{output_date}-pretrunas.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"wrote {md_path}")

    # --- HTML/PDF with embedded images ---
    style = """
    <style>
      @page { size: A4; margin: 18mm; }
      body {
        font-family: Georgia, 'Times New Roman', serif;
        color: #1a1d24;
        line-height: 1.55;
        background: #fafafa;
      }
      h1 {
        color: #0d1014;
        border-bottom: 4px solid #eab308;
        padding-bottom: 10px;
        font-weight: 500;
        letter-spacing: -0.3px;
      }
      h2 {
        color: #0d1014;
        margin-top: 32px;
        font-weight: 500;
        font-size: 22px;
        letter-spacing: -0.2px;
      }
      .lede {
        color: #555;
        font-size: 14px;
        margin: 6px 0 22px 0;
      }
      .meta {
        color: #666;
        font-size: 11px;
        font-family: 'JetBrains Mono', Consolas, monospace;
        letter-spacing: 0.6px;
        margin: 6px 0 18px 0;
      }
      .pillar {
        display: inline-block;
        background: #0d1014;
        color: #eab308;
        padding: 3px 10px;
        border-radius: 3px;
        font-size: 10px;
        font-family: 'JetBrains Mono', Consolas, monospace;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        font-weight: 600;
        margin-right: 10px;
        vertical-align: middle;
      }
      img {
        max-width: 100%;
        border-radius: 6px;
        margin: 12px 0 16px 0;
        border: 1px solid #d8d8dc;
        box-shadow: 0 2px 10px rgba(0,0,0,0.08);
      }
      pre {
        background: #0d1014;
        color: #e2e4e9;
        border-left: 3px solid #eab308;
        padding: 16px 20px;
        border-radius: 0 4px 4px 0;
        font-family: 'JetBrains Mono', Consolas, monospace;
        font-size: 12.5px;
        white-space: pre-wrap;
        line-height: 1.6;
      }
      .item {
        page-break-inside: avoid;
        margin-bottom: 28px;
      }
      .footer-note {
        color: #666;
        font-size: 11px;
        font-family: 'JetBrains Mono', Consolas, monospace;
        margin-top: 48px;
        border-top: 1px solid #ddd;
        padding-top: 14px;
      }
      a { color: #b3820a; }
    </style>
    """

    def img_b64(path: Path) -> str:
        return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()

    html_parts = [
        "<!DOCTYPE html><html lang='lv'><head><meta charset='UTF-8'>",
        style, "</head><body>",
        "<h1>atmina.lv · Pretrunu tvītu bank</h1>",
        f"<p class='lede'><strong>{output_date}</strong> · {len(items)} drafti — "
        "nepublicētas pretrunas. Teksts no `draft_pretrunas`, attēls kopēts no publicētās "
        "OG kartes (<code>/assets/og/pretruna-{id}.png</code>).</p>",
    ]
    for it in items:
        src = img_b64(it["og_path"])
        safe_text = it["text"].replace("&", "&amp;").replace("<", "&lt;")
        cid = it["id"]
        html_parts += [
            "<div class='item'>",
            f"<h2><span class='pillar'>Pretrunas</span>"
            f"#{cid:03d} — {it['politician']} · {it['topic']}</h2>",
            f"<img src='{src}' alt='Pretruna #{cid}'>",
            "<strong>Tvīta teksts:</strong>",
            f"<pre>{safe_text}</pre>",
            f"<p class='meta'>{it['meta']}</p>",
            "</div>",
        ]
    html_parts += [
        "<p class='footer-note'>Ģenerēts no atmina.lv social-agent pipeline — "
        "teksts: <code>src.social_agent.drafters.draft_pretrunas</code>, "
        "vizuāls: <code>output/atmina/assets/og/pretruna-{id}.png</code> (publiskā OG karte).</p>",
        "</body></html>",
    ]
    html = "\n".join(html_parts)

    html_path = OUT_DIR / f"{output_date}-pretrunas.html"
    html_path.write_text(html, encoding="utf-8")
    print(f"wrote {html_path}")

    pdf_path = OUT_DIR / f"{output_date}-pretrunas.pdf"
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        p.set_content(html, wait_until="domcontentloaded")
        p.pdf(
            path=str(pdf_path), format="A4", print_background=True,
            margin={"top": "14mm", "bottom": "14mm", "left": "16mm", "right": "16mm"},
        )
        b.close()
    print(f"wrote {pdf_path}")
    return md_path, html_path, pdf_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="2026-04-21", help="Output filename date stamp (YYYY-MM-DD)")
    args = ap.parse_args()
    build(args.date)
