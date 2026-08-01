"""Render a wiki synthesis markdown + its featured image into a PDF."""
import argparse
import base64
import re
from pathlib import Path

import markdown
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent


def img_b64(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


def extract_frontmatter(text: str) -> tuple[dict, str]:
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, flags=re.DOTALL)
    if not m:
        return {}, text
    fm_text, body = m.group(1), m.group(2)
    fm = {}
    for line in fm_text.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip().strip('"')
    return fm, body


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("md", help="path to synthesis markdown (e.g. wiki/synthesis/foo.md)")
    ap.add_argument("--image", help="featured image path (defaults to output/atmina/images/synthesis/<slug>.png)")
    ap.add_argument("--out", help="output PDF path (defaults to docs/synthesis/<slug>.pdf)")
    ap.add_argument(
        "--pagebreak-before",
        default="",
        help="comma-separated h2 titles that must start a new page",
    )
    args = ap.parse_args()

    md_path = Path(args.md).resolve()
    slug = md_path.stem
    text = md_path.read_text(encoding="utf-8")
    fm, body = extract_frontmatter(text)

    body = re.sub(r"^\s*#\s+.+?\n", "", body, count=1)

    image_path = (
        Path(args.image).resolve()
        if args.image
        else ROOT / "output" / "atmina" / "images" / "synthesis" / f"{slug}.png"
    )
    out_path = (
        Path(args.out).resolve()
        if args.out
        else ROOT / "docs" / "synthesis" / f"{slug}.pdf"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)

    body_html = markdown.markdown(body, extensions=["tables", "fenced_code"])

    pagebreak_titles = [
        t.strip() for t in args.pagebreak_before.split(",") if t.strip()
    ]
    for title_txt in pagebreak_titles:
        body_html = body_html.replace(
            f"<h2>{title_txt}</h2>",
            f'<h2 class="pagebreak">{title_txt}</h2>',
        )

    title = fm.get("title", slug)
    description = fm.get("description", "")
    created = fm.get("created", "")

    hero_img_html = (
        f"<img class='hero' src='{img_b64(image_path)}' alt='featured'>"
        if image_path.exists()
        else ""
    )

    style = """
<style>
  @page { size: A4; margin: 16mm 14mm; }
  body { font-family: Georgia, 'Times New Roman', serif; color: #111;
    line-height: 1.55; font-size: 11.5pt; }
  h1 { font-size: 24pt; color: #0d1014; border-bottom: 3px solid #eab308;
    padding-bottom: 6px; margin-top: 0; }
  h2 { font-size: 14pt; color: #0d1014; margin-top: 22px;
    border-left: 3px solid #eab308; padding-left: 10px; }
  h2.pagebreak { page-break-before: always; break-before: page; margin-top: 0; }
  h3 { font-size: 12pt; color: #0d1014; margin-top: 18px; }
  p { margin: 8px 0; }
  .meta { color: #666; font-size: 10pt; margin: 4px 0 16px 0; }
  .desc { color: #333; font-size: 11pt; font-style: italic; margin: 4px 0 18px 0;
    border-left: 2px solid #ccc; padding-left: 10px; }
  img.hero { width: 100%; border-radius: 4px; margin: 0 0 18px 0; }
  table { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 10pt; }
  th, td { border: 1px solid #ddd; padding: 6px 8px; text-align: left;
    vertical-align: top; }
  th { background: #f5f5f5; font-family: 'JetBrains Mono', Consolas, monospace;
    font-size: 9pt; text-transform: uppercase; letter-spacing: 0.5px; }
  a { color: #0d6efd; text-decoration: none; }
  blockquote { border-left: 3px solid #eab308; margin: 10px 0; padding: 4px 12px;
    color: #444; font-style: italic; }
  code { font-family: 'JetBrains Mono', Consolas, monospace; font-size: 10pt;
    background: #f5f5f7; padding: 1px 4px; border-radius: 3px; }
  ul, ol { margin: 8px 0; padding-left: 22px; }
  li { margin: 3px 0; }
  .footer-note { color: #666; font-size: 9pt; margin-top: 32px;
    border-top: 1px solid #ddd; padding-top: 8px; }
</style>
"""

    html = f"""<!DOCTYPE html>
<html lang="lv"><head><meta charset="UTF-8">{style}</head><body>
{hero_img_html}
<h1>{title}</h1>
{f'<p class="desc">{description}</p>' if description else ''}
<p class="meta">atmina.lv · sintēze · sagatavots {created}</p>
{body_html}
<p class="footer-note">Ģenerēts no <code>{md_path.relative_to(ROOT)}</code> ·
avots: atmina.lv datu bāze un publiski citētie avoti.</p>
</body></html>
"""

    html_path = out_path.with_suffix(".html")
    html_path.write_text(html, encoding="utf-8")
    print(f"wrote {html_path}")

    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        p.set_content(html, wait_until="domcontentloaded")
        p.pdf(
            path=str(out_path),
            format="A4",
            print_background=True,
            margin={"top": "12mm", "bottom": "12mm", "left": "14mm", "right": "14mm"},
        )
        b.close()
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
