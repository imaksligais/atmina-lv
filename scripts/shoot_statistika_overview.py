from pathlib import Path
from playwright.sync_api import sync_playwright
from PIL import Image

OUT = Path("output/images/threads")
CREAM = (247, 243, 232)

CLEAN = r"""() => {
  document.querySelectorAll('nav.nav, footer, details').forEach(e => e.remove());
  const grid = document.querySelector('.stat-card-grid');
  // 5 kolonnas x 2 rindas = tuvāk 16:9 nekā noklusējuma režģis
  grid.style.display = 'grid';
  grid.style.gridTemplateColumns = 'repeat(5, minmax(0, 1fr))';
  grid.style.gap = '14px';
  const sec = grid.closest('section') || grid.parentElement;
  sec.id = 'shotbox';
  sec.style.padding = '30px 34px 34px';
  sec.style.background = '#F7F3E8';
  sec.style.maxWidth = 'none';
  let p = sec.parentElement;
  while (p && p.tagName !== 'BODY') { p.style.maxWidth = 'none'; p.style.width = 'auto'; p = p.parentElement; }
  document.body.style.background = '#F7F3E8';
  return Math.round(sec.getBoundingClientRect().width);
}"""

with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page(viewport={"width": 1900, "height": 1100}, device_scale_factor=2)
    page.goto("https://atmina.lv/statistika.html", wait_until="networkidle")
    page.wait_for_timeout(1500)
    w = page.evaluate(CLEAN)
    page.wait_for_timeout(600)
    raw = OUT / "_raw-1.png"
    page.locator("#shotbox").screenshot(path=str(raw))
    im = Image.open(raw).convert("RGB")
    iw, ih = im.size
    fw, fh = 1600, 900
    s = min((fw-40)/iw, (fh-40)/ih)
    im = im.resize((round(iw*s), round(ih*s)), Image.LANCZOS)
    c = Image.new("RGB", (fw, fh), CREAM)
    c.paste(im, ((fw-im.size[0])//2, (fh-im.size[1])//2))
    c.save(OUT / "2026-09-08-statistika-shot-1-parskats.png")
    raw.unlink()
    b.close()
    print(f"sec {w}px → saturs {im.size[0]}x{im.size[1]} kadrā 1600x900")
