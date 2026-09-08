"""Ekrānuzņēmumi no ĪSTĀS statistikas lapas → 16:9 sociālie attēli."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from PIL import Image

OUT = Path("output/images/threads")
CREAM = (247, 243, 232)

JOBS = [
    ("1-parskats",    "https://atmina.lv/statistika.html",         1920),
    ("2-iedzivotaji", "https://atmina.lv/statistika/IRS010m.html", 1440),
    ("3-bezdarbs",    "https://atmina.lv/statistika/NVA011m.html", 1440),
    ("4-parads",      "https://atmina.lv/statistika/VFV050.html",  1440),
    ("5-notikumi",    "https://atmina.lv/statistika/PCI021m.html", 1440),
]

CLEAN = r"""() => {
  document.querySelectorAll('nav.nav, footer, details').forEach(e => e.remove());
  document.querySelectorAll('a').forEach(a => {
    if ((a.textContent||'').trim().startsWith('← Atpakaļ')) a.remove();
  });
  document.querySelectorAll('p,div').forEach(e => {
    const t = (e.textContent||'').trim();
    if (t.startsWith('Dati:') && e.children.length <= 1) e.remove();
  });
  // Notikumu TEKSTA saraksts zem grafika nost (gan YYYY-MM, gan YYYY sērijām);
  // krāsainās "NOTIKUMI:" pogas paliek — tās nes stāstu, saraksts tikai gara aste.
  const wrap = document.querySelector('.stat-chart-wrap');
  if (wrap && wrap.parentElement) {
    [...wrap.parentElement.children].forEach(ch => {
      if (ch !== wrap && /^\s*\d{4}(-\d{2})?\s/.test(ch.textContent || '')) ch.remove();
    });
  }
  const anchor = document.querySelector('h1') || document.querySelector('.stat-hero');
  let box = anchor;
  while (box && box.tagName !== 'BODY' && !box.querySelector('.stat-chart-wrap, .stat-card-grid')) box = box.parentElement;
  if (!box || box.tagName === 'BODY') box = document.querySelector('.container') || document.body;
  box.id = 'shotbox';
  box.style.padding = '32px 36px 36px';
  box.style.background = '#F7F3E8';
  document.body.style.background = '#F7F3E8';
  return Math.round(box.getBoundingClientRect().width);
}"""


def pad_to_169(src, dst, frame_w=1600):
    im = Image.open(src).convert("RGB")
    w, h = im.size
    frame_h = round(frame_w * 9 / 16)
    inner_w, inner_h = frame_w - 40, frame_h - 40
    scale = min(inner_w / w, inner_h / h)
    if scale != 1:
        im = im.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.LANCZOS)
    canvas = Image.new("RGB", (frame_w, frame_h), CREAM)
    canvas.paste(im, ((frame_w - im.size[0]) // 2, (frame_h - im.size[1]) // 2))
    canvas.save(dst)
    return im.size


with sync_playwright() as p:
    b = p.chromium.launch()
    for slug, url, vw in JOBS:
        page = b.new_page(viewport={"width": vw, "height": 1200}, device_scale_factor=2)
        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(1200)
        boxw = page.evaluate(CLEAN)
        page.wait_for_timeout(400)
        raw = OUT / f"_raw-{slug}.png"
        page.locator("#shotbox").screenshot(path=str(raw))
        dst = OUT / f"2026-09-08-statistika-shot-{slug}.png"
        inner = pad_to_169(raw, dst)
        raw.unlink()
        page.close()
        print(f"{slug:15} box {boxw:5}px → saturs {inner[0]}x{inner[1]} kadrā 1600x900")
    b.close()
