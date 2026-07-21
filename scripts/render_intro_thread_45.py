"""Render tweet 4 (Avoti) and tweet 5 (CTA) visuals for the intro thread."""
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "social" / "drafts"
OUT.mkdir(parents=True, exist_ok=True)

# --- Tweet 4: Avoti ---
T4_HTML = """
<!DOCTYPE html><html lang="lv"><head><meta charset="UTF-8"><style>
  html,body { margin:0; padding:0; background:#0b0f19; color:#fff;
    font-family: Inter, system-ui, sans-serif; }
  .card { width:1200px; height:675px; padding:72px 80px; box-sizing:border-box;
    display:flex; flex-direction:column; justify-content:space-between; }
  .head h1 { font-size:52px; margin:0; font-weight:800; letter-spacing:-1px;
    line-height:1.05; }
  .head .accent { color:#ff3b7f; }
  .head .sub { color:#a0a7b8; font-size:19px; letter-spacing:1px;
    text-transform:uppercase; margin-top:12px; }
  .flow { display:flex; gap:40px; align-items:center; margin-top:18px; }
  .sources { display:grid; grid-template-columns:1fr 1fr; gap:12px 28px; flex:1; }
  .src { padding:16px 22px; background:#151a2a; border-left:4px solid #ff3b7f;
    border-radius:8px; display:flex; justify-content:space-between; align-items:center;
    gap:20px; }
  .src .name { font-size:22px; font-weight:700; }
  .src .tag { font-size:12px; color:#a0a7b8; text-transform:uppercase;
    letter-spacing:1.5px; text-align:right; }
  .src.wide { grid-column: 1 / -1; border-left-color:#60a5fa;
    background:#0f1729; }
  .src.wide .name::before { content:"🏛 "; }
  .arrow { color:#ff3b7f; font-size:48px; line-height:1; font-weight:800;
    flex:0 0 auto; }
  .verify { flex:0 0 310px; padding:24px 26px; background:#0f1729;
    border:1px solid #2a3042; border-radius:12px; }
  .verify .head { display:flex; justify-content:space-between;
    align-items:center; margin-bottom:18px; }
  .verify .pill { display:inline-block; font-size:12px; color:#60a5fa;
    background:#0b1424; border:1px solid #1e3a5f; padding:5px 12px;
    border-radius:999px; letter-spacing:2px; text-transform:uppercase;
    font-weight:700; }
  .verify .head .label { color:#a0a7b8; font-size:11px;
    text-transform:uppercase; letter-spacing:2px; }
  .verify ul { list-style:none; margin:0; padding:0; display:flex;
    flex-direction:column; gap:12px; }
  .verify li { display:flex; align-items:center; gap:12px;
    font-size:20px; font-weight:600; color:#fff; }
  .verify li::before { content:"✓"; color:#60a5fa; font-weight:900;
    font-size:18px; width:22px; height:22px; display:inline-flex;
    align-items:center; justify-content:center;
    background:#0b1424; border:1px solid #1e3a5f;
    border-radius:6px; flex:0 0 auto; }
  .footer { display:flex; justify-content:space-between; align-items:center;
    color:#a0a7b8; font-size:18px; }
  .brand { color:#ff3b7f; font-weight:700; font-size:22px; }
</style></head><body><div class="card">
  <div class="head">
    <h1>Katram ierakstam — <span class="accent">avots</span>.</h1>
    <div class="sub">Kas · kad · kur · ko teica vai balsoja</div>
  </div>
  <div class="flow">
    <div class="sources">
      <div class="src"><span class="name">LSM</span><span class="tag">lsm.lv</span></div>
      <div class="src"><span class="name">Delfi</span><span class="tag">delfi.lv</span></div>
      <div class="src"><span class="name">Latvijas Avīze</span><span class="tag">la.lv</span></div>
      <div class="src"><span class="name">TVNet</span><span class="tag">tvnet.lv</span></div>
      <div class="src"><span class="name">NRA</span><span class="tag">nra.lv</span></div>
      <div class="src"><span class="name">X</span><span class="tag">@deputāti</span></div>
      <div class="src wide"><span class="name">Saeima</span><span class="tag">Oficiālais balsojumu arhīvs · titania.saeima.lv</span></div>
    </div>
    <div class="arrow">→</div>
    <div class="verify">
      <div class="head">
        <span class="pill">atmina.lv</span>
        <span class="label">Katrs ieraksts</span>
      </div>
      <ul>
        <li>Politiķis</li>
        <li>Datums</li>
        <li>Avota links</li>
        <li>Citāts vai balsojums</li>
      </ul>
    </div>
  </div>
  <div class="footer">
    <span>Nekas nav izdomāts. Tu vari pārbaudīt pats.</span>
    <span class="brand">atmina.lv</span>
  </div>
</div></body></html>
"""

# --- Tweet 5: CTA ---
T5_HTML = """
<!DOCTYPE html><html lang="lv"><head><meta charset="UTF-8"><style>
  html,body { margin:0; padding:0; background:#0b0f19; color:#fff;
    font-family: Inter, system-ui, sans-serif; }
  .card { width:1200px; height:675px; padding:80px 96px; box-sizing:border-box;
    display:flex; flex-direction:column; justify-content:space-between;
    position:relative; overflow:hidden; }
  /* decorative ghost-text behind */
  .ghost { position:absolute; font-size:420px; font-weight:900; color:#10182b;
    top:-60px; right:-120px; letter-spacing:-12px; line-height:1; z-index:0;
    user-select:none; }
  .main { position:relative; z-index:1; }
  .eyebrow { color:#ff3b7f; font-size:14px; font-weight:700;
    text-transform:uppercase; letter-spacing:3px; margin-bottom:28px; }
  .tagline { font-size:72px; font-weight:800; line-height:1.04;
    letter-spacing:-2px; max-width:960px; }
  .tagline .accent { color:#ff3b7f; }
  .meta { display:flex; gap:48px; margin-top:36px; color:#a0a7b8; font-size:18px; }
  .meta .dot { color:#ff3b7f; font-weight:800; }
  .footer { display:flex; justify-content:space-between; align-items:flex-end;
    position:relative; z-index:1; }
  .cta { font-size:42px; font-weight:900; color:#fff; letter-spacing:-1px; }
  .cta .accent { color:#ff3b7f; }
  .brand-tag { color:#a0a7b8; font-size:15px; text-transform:uppercase;
    letter-spacing:2px; }
</style></head><body><div class="card">
  <div class="ghost">atmiņa</div>
  <div class="main">
    <div class="eyebrow">Politiskā atmiņa · 2026</div>
    <div class="tagline">Atceries to,<br>ko viņi cer,<br>
      <span class="accent">ka tu aizmirsīsi.</span></div>
    <div class="meta">
      <div><span class="dot">•</span> Bez maksas</div>
      <div><span class="dot">•</span> Bez reģistrācijas</div>
      <div><span class="dot">•</span> Latviešu valodā</div>
    </div>
  </div>
  <div class="footer">
    <div class="cta">→ <span class="accent">atmina.lv</span></div>
    <div class="brand-tag">Skaties. Salīdzini. Dalies.</div>
  </div>
</div></body></html>
"""


def render(html, out_name):
    out_path = OUT / out_name
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page(viewport={"width": 1200, "height": 675})
        p.set_content(html, wait_until="domcontentloaded")
        p.screenshot(path=str(out_path), clip={"x": 0, "y": 0, "width": 1200, "height": 675})
        b.close()
    return out_path


render(T4_HTML, "intro_thread_t4_avoti.png")
print("tweet 4 avoti OK")
render(T5_HTML, "intro_thread_t5_cta.png")
print("tweet 5 cta OK")
