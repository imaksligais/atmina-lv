"""Build an infographics review document (Markdown + HTML + PDF) with
chart-style tweets — leaderboard, party activity, top topics, contradiction
categories, party-level contradictions.

All charts use the atmina.lv palette (amber #eab308, dark #0d1014, Georgia
serif titles, JetBrains Mono labels). Output style matches the 2026-04-21
pretrunas tweet bank.
"""
from __future__ import annotations

import argparse
import base64
from pathlib import Path

from playwright.sync_api import sync_playwright

from src.db import get_db
from src.social_agent.visuals import (
    render_chart,
    render_party_chart,
    render_topics_chart,
    render_category_chart,
)

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "docs" / "tweet_bank"
ASSETS_OUT = ROOT / "data" / "social" / "drafts" / "infografikas"

MAX_LEN = 280
ELLIPSIS = "…"


def _short_party(name: str) -> str:
    shorts = {
        "Jaunā Vienotība": "JV",
        "Nacionālā apvienība": "NA",
        "Progresīvie": "PRO",
        "Zaļo un Zemnieku savienība": "ZZS",
        "Apvienotais saraksts": "AS",
        "Latvija Pirmajā Vietā": "LPV",
        "MMN": "MMN",
        "Bezpartejisks": "Bezp.",
        "Latvijas attīstībai": "LA",
    }
    return shorts.get(name, name)


# --- Data queries ------------------------------------------------------------

def fetch_leaderboard(limit: int = 10) -> list[dict]:
    with get_db() as db:
        rows = db.execute("""
            SELECT p.name, p.party, COUNT(c.id) AS n
            FROM claims c
            JOIN tracked_politicians p ON p.id = c.opponent_id
            WHERE c.claim_type = 'position'
              AND c.stated_at >= datetime('now','-7 days')
              AND p.relationship_type NOT IN ('journalist','influencer','neutral','inactive')
            GROUP BY p.id HAVING n > 0 ORDER BY n DESC LIMIT ?
        """, (limit,)).fetchall()
    return [{"name": r["name"], "party": r["party"], "count": r["n"]} for r in rows]


def fetch_party_activity() -> list[dict]:
    with get_db() as db:
        rows = db.execute("""
            SELECT p.party, COUNT(c.id) AS n
            FROM claims c
            JOIN tracked_politicians p ON p.id = c.opponent_id
            WHERE c.claim_type = 'position'
              AND c.stated_at >= datetime('now','-7 days')
              AND p.party IS NOT NULL AND p.party != ''
              AND p.relationship_type NOT IN ('journalist','influencer','neutral','inactive')
            GROUP BY p.party ORDER BY n DESC
        """).fetchall()
    return [{"party": r["party"], "count": r["n"]} for r in rows]


def fetch_top_topics(limit: int = 8) -> list[dict]:
    with get_db() as db:
        rows = db.execute("""
            SELECT c.topic, COUNT(*) AS n
            FROM claims c
            JOIN tracked_politicians p ON p.id = c.opponent_id
            WHERE c.claim_type = 'position'
              AND c.stated_at >= datetime('now','-7 days')
              AND p.relationship_type NOT IN ('journalist','influencer','neutral','inactive')
              AND c.topic IS NOT NULL AND c.topic != ''
            GROUP BY c.topic ORDER BY n DESC LIMIT ?
        """, (limit,)).fetchall()
    return [{"topic": r["topic"], "count": r["n"]} for r in rows]


def fetch_contradiction_categories() -> list[dict]:
    with get_db() as db:
        rows = db.execute("""
            SELECT co.claim_type AS old_ct, cn.claim_type AS new_ct, COUNT(*) AS n
            FROM contradictions ct
            JOIN claims co ON co.id = ct.claim_old_id
            JOIN claims cn ON cn.id = ct.claim_new_id
            GROUP BY old_ct, new_ct
        """).fetchall()
    counts = {"Vārdi vs. darbi": 0, "Pozīcijas maiņa": 0, "Balsojuma maiņa": 0}
    for r in rows:
        pair = tuple(sorted([r["old_ct"], r["new_ct"]]))
        if pair == ("position", "position"):
            counts["Pozīcijas maiņa"] += r["n"]
        elif pair == ("position", "saeima_vote"):
            counts["Vārdi vs. darbi"] += r["n"]
        elif pair == ("saeima_vote", "saeima_vote"):
            counts["Balsojuma maiņa"] += r["n"]
    return [{"category": k, "count": v} for k, v in counts.items() if v > 0]


def fetch_party_contradictions() -> list[dict]:
    with get_db() as db:
        rows = db.execute("""
            SELECT p.party, COUNT(ct.id) AS n
            FROM contradictions ct
            JOIN tracked_politicians p ON p.id = ct.opponent_id
            WHERE p.party IS NOT NULL AND p.party != ''
            GROUP BY p.party ORDER BY n DESC
        """).fetchall()
    return [{"party": r["party"], "count": r["n"]} for r in rows]


# --- Drafters ----------------------------------------------------------------

def draft_leaderboard(rows: list[dict]) -> str:
    lines = ["Aktīvākie deputāti šonedēļ:"]
    for i, r in enumerate(rows[:5], start=1):
        lines.append(f"{i}. {r['name']} ({_short_party(r['party'])}) — {r['count']}")
    lines.append("")
    lines.append("Pilns top 10 ar avotiem: atmina.lv")
    text = "\n".join(lines)
    return text[: MAX_LEN - 1] + ELLIPSIS if len(text) > MAX_LEN else text


def draft_party_activity(rows: list[dict]) -> str:
    lines = ["Partijas pa aktivitāti šonedēļ:"]
    for i, r in enumerate(rows[:6], start=1):
        lines.append(f"{i}. {_short_party(r['party'])} — {r['count']} pozīcijas")
    lines.append("")
    lines.append("Katrs paziņojums ar avotu: atmina.lv/partijas")
    text = "\n".join(lines)
    return text[: MAX_LEN - 1] + ELLIPSIS if len(text) > MAX_LEN else text


def draft_topics(rows: list[dict]) -> str:
    lines = ["Par ko runā Latvijas politiķi (7 dienas):"]
    for i, r in enumerate(rows[:6], start=1):
        lines.append(f"{i}. {r['topic']} — {r['count']}")
    lines.append("")
    lines.append("atmina.lv")
    text = "\n".join(lines)
    return text[: MAX_LEN - 1] + ELLIPSIS if len(text) > MAX_LEN else text


def draft_categories(rows: list[dict]) -> str:
    total = sum(r["count"] for r in rows)
    lines = [f"{total} atklātās pretrunas — kā tās sadalās:"]
    for r in rows:
        lines.append(f"{r['count']}× {r['category'].lower()}")
    lines.append("")
    lines.append("Katra ar datumiem un avotiem: atmina.lv/pretrunas")
    text = "\n".join(lines)
    return text[: MAX_LEN - 1] + ELLIPSIS if len(text) > MAX_LEN else text


def draft_party_contradictions(rows: list[dict]) -> str:
    lines = ["Pretrunas pa partijām:"]
    for r in rows:
        lines.append(f"{_short_party(r['party'])} — {r['count']}")
    lines.append("")
    lines.append("atmina.lv/pretrunas")
    text = "\n".join(lines)
    return text[: MAX_LEN - 1] + ELLIPSIS if len(text) > MAX_LEN else text


# --- Build -------------------------------------------------------------------

def _window_subtitle() -> str:
    from datetime import datetime, timedelta
    now = datetime.now()
    start = now - timedelta(days=7)
    return f"{start:%d.%m} – {now:%d.%m.%Y}"


def build(output_date: str) -> tuple[Path, Path, Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_OUT.mkdir(parents=True, exist_ok=True)

    subtitle_week = _window_subtitle()
    subtitle_all = "Visā atmina.lv arhīvā"

    infographics: list[dict] = []

    # 1. Leaderboard
    lb = fetch_leaderboard()
    if lb:
        png = ASSETS_OUT / f"{output_date}_leaderboard.png"
        render_chart(
            {"leaderboard": lb, "subtitle": subtitle_week},
            out_path=png,
        )
        infographics.append({
            "title": "Nedēļas aktivitāte — politiķi",
            "kind": "Stats",
            "img": png,
            "text": draft_leaderboard(lb),
            "meta": f"top {len(lb)} deputāti · claims.claim_type=position · pēdējās 7 dienas",
        })

    # 2. Party activity
    pa = fetch_party_activity()
    if pa:
        png = ASSETS_OUT / f"{output_date}_party_activity.png"
        render_party_chart(
            {"rows": pa, "subtitle": subtitle_week, "xlabel": "Pozīcijas šonedēļ"},
            out_path=png,
        )
        infographics.append({
            "title": "Nedēļas aktivitāte — partijas",
            "kind": "Stats",
            "img": png,
            "text": draft_party_activity(pa),
            "meta": f"{len(pa)} partijas · grupēts no claims · pēdējās 7 dienas",
        })

    # 3. Top topics
    tt = fetch_top_topics()
    if tt:
        png = ASSETS_OUT / f"{output_date}_topics.png"
        render_topics_chart(
            {"rows": tt, "subtitle": subtitle_week, "xlabel": "Pozīcijas šonedēļ"},
            out_path=png,
        )
        infographics.append({
            "title": "Par ko runā šonedēļ",
            "kind": "Topics",
            "img": png,
            "text": draft_topics(tt),
            "meta": f"top {len(tt)} tēmas · no 31 kanoniskā topika",
        })

    # 4. Contradiction categories
    cc = fetch_contradiction_categories()
    if cc:
        png = ASSETS_OUT / f"{output_date}_categories.png"
        render_category_chart(
            {"rows": cc, "subtitle": subtitle_all, "xlabel": "Pretrunas"},
            out_path=png,
        )
        infographics.append({
            "title": "Pretrunu kategorijas",
            "kind": "Pretrunas",
            "img": png,
            "text": draft_categories(cc),
            "meta": f"{sum(r['count'] for r in cc)} pretrunas · claim_type pāris",
        })

    # 5. Party-level contradictions
    pc = fetch_party_contradictions()
    if pc:
        png = ASSETS_OUT / f"{output_date}_party_pretrunas.png"
        render_party_chart(
            {"rows": pc, "subtitle": subtitle_all, "xlabel": "Pretrunas"},
            out_path=png,
        )
        infographics.append({
            "title": "Partijas ar visvairāk pretrunu",
            "kind": "Pretrunas",
            "img": png,
            "text": draft_party_contradictions(pc),
            "meta": f"{len(pc)} partijas · grupēts no contradictions",
        })

    # --- Markdown ---
    md_lines = [
        "# atmina.lv · Infografiku banka",
        "",
        f"**Datums:** {output_date}",
        f"**{len(infographics)} chart-stila drafti** — atmina.lv amber palete, "
        "Georgia serif virsraksti, JetBrains Mono metki.",
        "",
        "---",
        "",
    ]
    for it in infographics:
        img_rel = f"../../data/social/drafts/infografikas/{it['img'].name}"
        md_lines += [
            f"## {it['kind']} — {it['title']}",
            "",
            f"![{it['title']}]({img_rel})",
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
    md_path = OUT_DIR / f"{output_date}-infografikas.md"
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
      .item { page-break-inside: avoid; margin-bottom: 28px; }
      .footer-note {
        color: #666;
        font-size: 11px;
        font-family: 'JetBrains Mono', Consolas, monospace;
        margin-top: 48px;
        border-top: 1px solid #ddd;
        padding-top: 14px;
      }
    </style>
    """

    def img_b64(path: Path) -> str:
        return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()

    html_parts = [
        "<!DOCTYPE html><html lang='lv'><head><meta charset='UTF-8'>",
        style, "</head><body>",
        "<h1>atmina.lv · Infografiku banka</h1>",
        f"<p class='lede'><strong>{output_date}</strong> · {len(infographics)} chart-drafti "
        "ar atmina.lv brand paleti — amber accent, Georgia serif, tumšs fons.</p>",
    ]
    for it in infographics:
        src = img_b64(it["img"])
        safe_text = it["text"].replace("&", "&amp;").replace("<", "&lt;")
        html_parts += [
            "<div class='item'>",
            f"<h2><span class='pillar'>{it['kind']}</span>{it['title']}</h2>",
            f"<img src='{src}' alt='{it['title']}'>",
            "<strong>Tvīta teksts:</strong>",
            f"<pre>{safe_text}</pre>",
            f"<p class='meta'>{it['meta']}</p>",
            "</div>",
        ]
    html_parts += [
        "<p class='footer-note'>Ģenerēts no atmina.lv DB — "
        "<code>src.social_agent.visuals</code> + <code>scripts/render_infografiku_tweet_bank.py</code>.</p>",
        "</body></html>",
    ]
    html = "\n".join(html_parts)

    html_path = OUT_DIR / f"{output_date}-infografikas.html"
    html_path.write_text(html, encoding="utf-8")
    print(f"wrote {html_path}")

    pdf_path = OUT_DIR / f"{output_date}-infografikas.pdf"
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
    ap.add_argument("--date", default="2026-04-21")
    args = ap.parse_args()
    build(args.date)
