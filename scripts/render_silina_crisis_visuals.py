"""Render social visuals for the Siliņa government-collapse synthesis.

Input narrative: wiki/synthesis/silinas-valdibas-krisana-2026-05.md
Output: 1200x675 PNG cards under docs/tweet_bank plus one synthesis hero copy
under output/atmina/images/synthesis.
"""
from __future__ import annotations

import html
import shutil
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SLUG = "silinas-valdibas-krisana-2026-05"
OUT_DIR = ROOT / "docs" / "tweet_bank" / "2026-05-14-silinas-valdibas-krisana"
SYNTHESIS_IMAGE = ROOT / "output" / "atmina" / "images" / "synthesis" / f"{SLUG}.png"

W = 1200
H = 675


def e(value: str) -> str:
    return html.escape(value, quote=True)


BASE_CSS = """
* { box-sizing: border-box; }
html, body {
  width: 1200px;
  height: 675px;
  margin: 0;
  overflow: hidden;
}
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.card {
  position: relative;
  width: 1200px;
  height: 675px;
  overflow: hidden;
}
.dark {
  background:
    radial-gradient(circle at 78% 18%, rgba(234,179,8,0.13), transparent 30%),
    linear-gradient(135deg, #0d1014 0%, #111722 52%, #080b10 100%);
  color: #e2e4e9;
}
.paper {
  background:
    linear-gradient(rgba(13,16,20,0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(13,16,20,0.04) 1px, transparent 1px),
    radial-gradient(circle at 25% 15%, rgba(234,179,8,0.09), transparent 34%),
    #f1eadb;
  background-size: 120px 120px, 120px 120px, auto, auto;
  color: #071124;
}
.rail {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 10px;
  background: #eab308;
}
.rail.red { background: #dc2626; }
.brand {
  position: absolute;
  right: 62px;
  bottom: 42px;
  font-family: Georgia, "Times New Roman", serif;
  font-weight: 700;
  font-size: 30px;
  letter-spacing: -0.6px;
}
.brand.dark-brand { color: #071124; }
.kicker {
  font-family: ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", monospace;
  font-size: 17px;
  letter-spacing: 1.2px;
  text-transform: uppercase;
  color: #a5aaba;
  font-weight: 700;
}
.paper .kicker { color: #625d52; }
.rule {
  width: 286px;
  height: 5px;
  background: #eab308;
  margin-top: 16px;
}
.headline {
  font-family: Georgia, "Times New Roman", serif;
  font-weight: 700;
  letter-spacing: -1.2px;
  line-height: 0.98;
}
.muted { color: #8b8fa3; }
.paper .muted { color: #686154; }
.mono {
  font-family: ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", monospace;
  letter-spacing: 0.8px;
}
.footer-left {
  position: absolute;
  left: 64px;
  bottom: 42px;
  font-size: 18px;
  color: #a5aaba;
}
.paper .footer-left { color: #686154; }
.micro {
  font-family: ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", monospace;
  font-size: 13px;
  letter-spacing: 1px;
  text-transform: uppercase;
}
.print-mark {
  position: absolute;
  width: 54px;
  height: 54px;
  border-left: 1px solid rgba(226,228,233,0.35);
  border-top: 1px solid rgba(226,228,233,0.35);
}
.paper .print-mark { border-color: rgba(7,17,36,0.28); }
.pm-tl { left: 28px; top: 28px; }
.pm-tr { right: 28px; top: 28px; transform: scaleX(-1); }
.pm-bl { left: 28px; bottom: 28px; transform: scaleY(-1); }
.pm-br { right: 28px; bottom: 28px; transform: scale(-1); }
"""


def page_html(body: str, *, paper: bool = False, rail: str = "yellow") -> str:
    theme = "paper" if paper else "dark"
    rail_cls = "rail red" if rail == "red" else "rail"
    return f"""<!doctype html>
<html lang="lv">
<head>
<meta charset="utf-8">
<style>{BASE_CSS}</style>
</head>
<body>
  <main class="card {theme}">
    <div class="{rail_cls}"></div>
    <span class="print-mark pm-tl"></span>
    <span class="print-mark pm-tr"></span>
    <span class="print-mark pm-bl"></span>
    <span class="print-mark pm-br"></span>
    {body}
  </main>
</body>
</html>"""


def card_00_hero() -> str:
    body = """
    <style>
      .hero-copy { position:absolute; left:64px; top:68px; width:650px; }
      .hero-title { font-size:76px; margin-top:56px; max-width:650px; }
      .hero-sub { margin-top:30px; font-family:Georgia,serif; font-size:29px; line-height:1.38; max-width:590px; color:#d5d8e0; }
      .seven { position:absolute; right:96px; top:94px; font-family:Georgia,serif; font-size:286px; line-height:.8; color:rgba(226,228,233,.08); }
      .cascade { position:absolute; right:112px; top:148px; width:382px; height:360px; }
      .drop-line { position:absolute; width:5px; height:330px; background:linear-gradient(#eab308,#dc2626); left:188px; top:12px; transform:rotate(-22deg); opacity:.9; }
      .drone { position:absolute; right:22px; top:42px; width:174px; height:92px; opacity:.9; }
      .drone .body { position:absolute; left:60px; top:34px; width:58px; height:25px; border:3px solid #cfd3dc; border-radius:18px; }
      .drone .arm { position:absolute; left:26px; top:45px; width:124px; height:3px; background:#cfd3dc; }
      .drone .arm.b { transform:rotate(90deg); left:27px; top:45px; }
      .drone .rotor { position:absolute; width:36px; height:36px; border:3px solid #cfd3dc; border-radius:50%; }
      .drone .r1 { left:8px; top:25px; } .drone .r2 { right:8px; top:25px; }
      .drone .r3 { left:70px; top:-12px; } .drone .r4 { left:70px; bottom:-12px; }
      .fault { position:absolute; right:80px; bottom:132px; width:390px; height:130px; border-bottom:2px solid rgba(226,228,233,.23); transform:skewX(-18deg); }
      .fault:before { content:""; position:absolute; left:40px; top:58px; width:300px; height:4px; background:#dc2626; transform:rotate(-6deg); box-shadow:0 0 16px rgba(220,38,38,.4); }
      .chips { display:flex; gap:12px; margin-top:34px; flex-wrap:wrap; }
      .chip { border:1px solid #2d3148; color:#a5aaba; padding:8px 12px; border-radius:4px; font-size:13px; }
      .chip strong { color:#eab308; }
    </style>
    <section class="hero-copy">
      <div class="kicker">Sintēze · 2026-05-14</div>
      <div class="rule"></div>
      <h1 class="headline hero-title">Septiņu dienu kaskāde</h1>
      <p class="hero-sub">7.05 droni Latgalē pārtapa par 14.05 valdības krišanu.</p>
      <div class="chips mono">
        <span class="chip"><strong>1</strong> Drošība</span>
        <span class="chip"><strong>2</strong> Koalīcija</span>
        <span class="chip"><strong>3</strong> Korupcija</span>
      </div>
    </section>
    <div class="seven">7</div>
    <div class="cascade">
      <div class="drop-line"></div>
      <div class="drone"><span class="body"></span><span class="arm"></span><span class="arm b"></span><span class="rotor r1"></span><span class="rotor r2"></span><span class="rotor r3"></span><span class="rotor r4"></span></div>
    </div>
    <div class="fault"></div>
    <div class="footer-left mono">7.05 → 14.05 · pozīcijas · pretrunas · avoti</div>
    <div class="brand">atmina.lv</div>
    """
    return page_html(body)


def card_01_three_tensions() -> str:
    body = """
    <style>
      .copy { position:absolute; left:70px; top:70px; width:455px; }
      .title { font-size:64px; margin-top:44px; }
      .sub { margin-top:22px; font-family:Georgia,serif; font-size:24px; line-height:1.35; color:#3d382e; }
      .merge { position:absolute; right:70px; top:92px; width:560px; height:470px; }
      .band { position:absolute; left:12px; width:430px; height:62px; border-radius:2px; color:#f8f4ea; display:flex; align-items:center; justify-content:flex-start; padding-left:24px; font-weight:800; font-size:20px; box-shadow:0 14px 24px rgba(7,17,36,.12); clip-path:polygon(0 0, calc(100% - 34px) 0, 100% 50%, calc(100% - 34px) 100%, 0 100%); }
      .b1 { top:54px; background:#17233a; }
      .b2 { top:198px; background:#b91c1c; }
      .b3 { top:342px; background:#5b21b6; }
      .sink { position:absolute; right:10px; top:160px; width:174px; height:174px; border:9px solid #eab308; border-radius:50%; background:#071124; color:#f8f4ea; display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; box-shadow:0 0 0 18px rgba(234,179,8,.18); }
      .sink strong { font-family:Georgia,serif; font-size:38px; line-height:1; }
      .sink span { margin-top:8px; font-size:16px; letter-spacing:1px; }
      .dates { position:absolute; left:18px; right:200px; bottom:8px; display:grid; grid-template-columns:repeat(3,1fr); gap:10px; }
      .date { border-top:2px solid rgba(7,17,36,.18); padding-top:10px; font-size:15px; color:#625d52; }
      .date strong { color:#071124; }
    </style>
    <section class="copy">
      <div class="kicker">Krīzes mehānika</div>
      <div class="rule"></div>
      <h1 class="headline title">Trīs spriedzes, viens kritiens</h1>
      <p class="sub">Valdība nekrita no viena notikuma. Trīs līnijas vienlaikus saplūda vienā politiskā punktā.</p>
    </section>
    <section class="merge">
      <div class="band b1 mono">Drošība · 7-10.05</div>
      <div class="band b2 mono">Koalīcija · 11-14.05</div>
      <div class="band b3 mono">Korupcija · 12-14.05</div>
      <div class="sink mono"><strong>14.05</strong><span>DEMISIJA</span></div>
      <div class="dates mono">
        <div class="date"><strong>Sprūds</strong><br>atkāpjas</div>
        <div class="date"><strong>PRO</strong><br>atsaka kompromisu</div>
        <div class="date"><strong>Krauze</strong><br>atstādināts</div>
      </div>
    </section>
    <div class="footer-left mono">atmina.lv/sintezes · kaskāde, ne epizode</div>
    <div class="brand dark-brand">atmina.lv</div>
    """
    return page_html(body, paper=True)


def card_02_timeline() -> str:
    events = [
        ("7.05", "Droni Latgalē", "Krīzes vadības sēde"),
        ("8.05", "Kļūdu analīze", "ne atbildīgā meklēšana"),
        ("10.05", "Sprūds atkāpjas", "pirmā demisija"),
        ("11.05", "Melnis kā kompromiss", "PRO atsaka"),
        ("13.05", "Pieci kandidāti", "politiskā vakuuma diena"),
        ("14.05", "Krauze + demisija", "valdība krīt"),
    ]
    items = "\n".join(
        f"""<div class="event">
          <div class="date">{e(date)}</div>
          <div class="dot"></div>
          <div class="event-title">{e(title)}</div>
          <div class="event-note">{e(note)}</div>
        </div>"""
        for date, title, note in events
    )
    body = f"""
    <style>
      .head {{ position:absolute; left:64px; top:62px; right:64px; z-index:2; }}
      .title {{ font-size:62px; margin-top:30px; max-width:850px; }}
      .timeline {{ position:absolute; left:70px; right:70px; top:292px; height:248px; display:grid; grid-template-columns:repeat(6,1fr); gap:0; z-index:2; }}
      .timeline:before {{ content:""; position:absolute; left:36px; right:36px; top:75px; height:3px; background:#2d3148; }}
      .event {{ position:relative; padding-right:18px; }}
      .date {{ font-family:ui-monospace,Consolas,monospace; color:#eab308; font-size:19px; font-weight:800; }}
      .dot {{ width:22px; height:22px; border-radius:50%; background:#0d1014; border:4px solid #eab308; margin-top:37px; position:relative; z-index:2; }}
      .event-title {{ margin-top:28px; font-family:Georgia,serif; font-size:24px; line-height:1.05; font-weight:700; color:#f2f4f7; }}
      .event-note {{ margin-top:10px; color:#a5aaba; font-size:15px; line-height:1.3; max-width:155px; }}
      .strike {{ position:absolute; right:92px; top:154px; width:270px; height:270px; border:2px solid rgba(220,38,38,.34); transform:rotate(-17deg); z-index:0; }}
      .strike:after {{ content:""; position:absolute; left:24px; right:24px; top:132px; height:5px; background:#dc2626; box-shadow:0 0 22px rgba(220,38,38,.45); }}
    </style>
    <section class="head">
      <div class="kicker">Hronoloģija</div>
      <div class="rule"></div>
      <h1 class="headline title">No incidenta pārvaldīšanas līdz valdības krišanai</h1>
    </section>
    <div class="strike"></div>
    <section class="timeline">{items}</section>
    <div class="footer-left mono">6 publiski pagrieziena punkti · 7 dienas</div>
    <div class="brand">atmina.lv</div>
    """
    return page_html(body)


def card_03_candidates() -> str:
    candidates = [
        ("Melnis", "nepartisks AM kandidāts", "JV/Siliņa"),
        ("Šlesers", "profesionāļu valdība", "LPV"),
        ("Indriksone", "drosmes platforma", "NA"),
        ("Smiltēns", "AS+NA+ZZS kodols", "AS"),
        ("Zeltīts", "pagaidu valdība", "ASL"),
    ]
    rows = "\n".join(
        f"""<div class="candidate c{i}">
          <span class="num">0{i}</span>
          <strong>{e(name)}</strong>
          <span>{e(line)}</span>
          <em>{e(party)}</em>
        </div>"""
        for i, (name, line, party) in enumerate(candidates, start=1)
    )
    body = f"""
    <style>
      .left {{ position:absolute; left:70px; top:70px; width:415px; }}
      .title {{ font-size:64px; margin-top:44px; }}
      .sub {{ margin-top:22px; font-family:Georgia,serif; font-size:24px; line-height:1.35; color:#3d382e; }}
      .wheel {{ position:absolute; right:62px; top:64px; width:620px; height:520px; }}
      .center {{ position:absolute; left:205px; top:155px; width:205px; height:205px; border-radius:50%; border:7px solid #eab308; background:#071124; color:#f8f4ea; display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; }}
      .center strong {{ font-family:Georgia,serif; font-size:34px; line-height:1; }}
      .center span {{ margin-top:10px; font-size:13px; }}
      .candidate {{ position:absolute; width:236px; min-height:106px; border:1px solid rgba(7,17,36,.18); background:rgba(255,255,255,.26); padding:15px 16px 14px; box-shadow:0 12px 24px rgba(7,17,36,.08); }}
      .candidate strong {{ display:block; font-family:Georgia,serif; font-size:27px; line-height:1; color:#071124; }}
      .candidate span {{ display:block; margin-top:7px; font-size:14px; line-height:1.25; color:#3d382e; }}
      .candidate em {{ display:block; margin-top:9px; font-family:ui-monospace,Consolas,monospace; font-style:normal; font-size:11px; letter-spacing:1px; color:#b91c1c; }}
      .num {{ position:absolute; right:12px; top:10px; font-family:ui-monospace,Consolas,monospace; color:#d0a20a; font-weight:800; }}
      .c1 {{ left:190px; top:0; }}
      .c2 {{ right:0; top:126px; }}
      .c3 {{ right:52px; bottom:4px; }}
      .c4 {{ left:52px; bottom:4px; }}
      .c5 {{ left:0; top:126px; }}
      .ray {{ position:absolute; left:307px; top:257px; width:1px; height:246px; background:rgba(7,17,36,.2); transform-origin:top center; }}
      .r1 {{ transform:rotate(0deg); }} .r2 {{ transform:rotate(72deg); }} .r3 {{ transform:rotate(144deg); }} .r4 {{ transform:rotate(216deg); }} .r5 {{ transform:rotate(288deg); }}
    </style>
    <section class="left">
      <div class="kicker">13.05 · piedāvājumu lavīna</div>
      <div class="rule"></div>
      <h1 class="headline title">Pieci kandidāti vienā dienā</h1>
      <p class="sub">Politiskais vakuums izpildīja sevi piecās paralēlās līnijās.</p>
    </section>
    <section class="wheel">
      <span class="ray r1"></span><span class="ray r2"></span><span class="ray r3"></span><span class="ray r4"></span><span class="ray r5"></span>
      <div class="center mono"><strong>VAKUUMS</strong><span>PREMJERA PIEDĀVĀJUMI</span></div>
      {rows}
    </section>
    <div class="footer-left mono">Ne koordinēta akcija, bet publisks varas tukšums</div>
    <div class="brand dark-brand">atmina.lv</div>
    """
    return page_html(body, paper=True)


def card_04_krauze_paradox() -> str:
    body = """
    <style>
      .head { position:absolute; left:64px; top:62px; width:620px; }
      .title { font-size:64px; margin-top:30px; }
      .split { position:absolute; left:64px; right:64px; top:292px; display:grid; grid-template-columns:1fr 150px 1fr; gap:26px; align-items:stretch; }
      .pane { min-height:210px; background:#161a22; border:1px solid #2d3148; padding:28px; border-radius:4px; }
      .pane .label { color:#8b8fa3; font-size:15px; }
      .pane strong { display:block; margin-top:18px; font-family:Georgia,serif; font-size:40px; line-height:1.05; color:#f2f4f7; }
      .pane p { margin-top:18px; color:#a5aaba; font-size:18px; line-height:1.35; }
      .versus { display:flex; flex-direction:column; align-items:center; justify-content:center; color:#eab308; font-family:Georgia,serif; font-size:66px; line-height:1; }
      .versus span { margin-top:12px; font-family:ui-monospace,Consolas,monospace; font-size:12px; color:#8b8fa3; letter-spacing:1.2px; }
      .finding { position:absolute; left:64px; right:64px; bottom:78px; border-left:5px solid #eab308; padding-left:20px; font-family:Georgia,serif; font-size:28px; color:#e2e4e9; }
    </style>
    <section class="head">
      <div class="kicker">Krauzes paradokss · 14.05</div>
      <div class="rule"></div>
      <h1 class="headline title">Abi teikumi var būt patiesi</h1>
    </section>
    <section class="split">
      <div class="pane">
        <div class="label mono">Krauze X kontā</div>
        <strong>"Es neesmu aizturēts"</strong>
        <p>Apstrīd mediju naratīvu par aizturēšanu un saka, ka sadarbojas ar iestādēm.</p>
      </div>
      <div class="versus">≠<span>ne tas pats jēdziens</span></div>
      <div class="pane">
        <div class="label mono">Siliņas lēmums</div>
        <strong>"Atstādina no amata"</strong>
        <p>Administratīvs lēmums liegt ministra pienākumu pildīšanu krīzes laikā.</p>
      </div>
    </section>
    <div class="finding">Pretruna ir lingvistiska, ne faktoloģiska.</div>
    <div class="brand">atmina.lv</div>
    """
    return page_html(body, rail="red")


def card_05_contradictions() -> str:
    rows = [
        ("#34", "direct_contradiction", "Šuvajevs: kļūdu analīze → valdības krišana"),
        ("#33", "reversal", "Šuvajevs: pieci mēneši iespējas → valdība gāzta"),
        ("#32", "reversal", "Indriksone: valdība nesagāzīsies → demisija"),
        ("#29", "reversal", "Siliņa: krišanai nav pamata → pašas demisija"),
    ]
    items = "\n".join(
        f"""<div class="contradiction">
          <div class="id">{e(cid)}</div>
          <div>
            <div class="type mono">{e(kind)}</div>
            <div class="line">{e(line)}</div>
          </div>
        </div>"""
        for cid, kind, line in rows
    )
    body = f"""
    <style>
      .left {{ position:absolute; left:70px; top:70px; width:430px; }}
      .big {{ font-family:Georgia,serif; font-size:156px; line-height:.85; color:#b91c1c; margin-top:42px; }}
      .title {{ font-size:58px; margin-top:10px; }}
      .sub {{ margin-top:22px; font-family:Georgia,serif; font-size:24px; line-height:1.35; color:#3d382e; }}
      .list {{ position:absolute; right:70px; top:86px; width:570px; display:flex; flex-direction:column; gap:16px; }}
      .contradiction {{ min-height:96px; display:grid; grid-template-columns:92px 1fr; gap:18px; align-items:center; background:rgba(255,255,255,.28); border:1px solid rgba(7,17,36,.14); padding:16px 20px; }}
      .id {{ font-family:Georgia,serif; font-size:40px; color:#071124; font-weight:700; }}
      .type {{ font-size:12px; color:#b91c1c; letter-spacing:1.2px; text-transform:uppercase; font-weight:800; }}
      .line {{ margin-top:7px; font-family:Georgia,serif; font-size:22px; line-height:1.18; color:#071124; }}
      .average {{ position:absolute; right:70px; bottom:54px; width:570px; border-top:3px solid #eab308; padding-top:14px; color:#625d52; font-size:18px; }}
    </style>
    <section class="left">
      <div class="kicker">Atmina signāls</div>
      <div class="rule"></div>
      <div class="big">4</div>
      <h1 class="headline title">strukturālas pretrunas vienā krīzē</h1>
      <p class="sub">Tas ir koncentrēts pretrunu skaits vienā politiskā notikumā.</p>
    </section>
    <section class="list">{items}</section>
    <div class="average mono">Parasti: 2-3 jaunas pretrunas mēnesī · šeit: 4 vienā kaskādē</div>
    <div class="brand dark-brand">atmina.lv</div>
    """
    return page_html(body, paper=True, rail="red")


CARDS: list[tuple[str, str]] = [
    ("00-hero-sinteze.png", card_00_hero()),
    ("01-tris-spriedzes.png", card_01_three_tensions()),
    ("02-hronologija.png", card_02_timeline()),
    ("03-pieci-kandidati.png", card_03_candidates()),
    ("04-krauzes-paradokss.png", card_04_krauze_paradox()),
    ("05-cetras-pretrunas.png", card_05_contradictions()),
]


POST_COPY = [
    (
        "Septiņu dienu kaskāde",
        "7.05 droni Latgalē. 10.05 Sprūds atkāpjas. 13.05 publiski parādās pieci valdības piedāvājumi. 14.05 Siliņa demisionē.\n\n"
        "Šī nebija viena epizode, bet trīs spriedzes, kas vienlaikus saplūda vienā punktā.\n\n"
        "atmina.lv/sintezes/silinas-valdibas-krisana-2026-05.html",
    ),
    (
        "Trīs spriedzes",
        "Valdības krišana nebija tikai dronu stāsts.\n\n"
        "Drošības spriedze beidzās ar Sprūda atkāpšanos. Koalīcijas spriedze pārgāja PRO-JV lūzumā. Korupcijas spriedze 14.05 iedeva gala triecienu.\n\n"
        "atmina.lv/sintezes/silinas-valdibas-krisana-2026-05.html",
    ),
    (
        "Hronoloģija",
        "Septiņas dienas rindā rāda svarīgāko: incidents pārtop atbildībā, atbildība pārtop koalīcijas lūzumā, lūzums pārtop valdības krišanā.\n\n"
        "Datumi svarīgi, jo bez tiem šī krīze izskatās pēc trokšņa, nevis kaskādes.",
    ),
    (
        "Pieci kandidāti",
        "13.05 vienā dienā publiski parādījās pieci konkurējoši premjera vai valdības piedāvājumi.\n\n"
        "Tas neizskatās pēc vienotas opozīcijas operācijas. Tas izskatās pēc politiska vakuuma, kas uzreiz pats sevi aizpildīja.",
    ),
    (
        "Krauzes paradokss",
        "Krauze saka: neesmu aizturēts. Siliņa saka: atstādinu no amata.\n\n"
        "Tie nav viens un tas pats juridiskais vārds. Tāpēc paradokss ir lingvistisks, ne obligāti faktoloģisks.",
    ),
    (
        "Četras pretrunas",
        "Atmina šajā krīzē fiksēja četras strukturālas pretrunas: #34, #33, #32 un #29.\n\n"
        "Vidēji platformā top 2-3 jaunas pretrunas mēnesī. Te vienā politiskā notikumā koncentrējās četras.",
    ),
]


def render_cards() -> list[Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        for filename, markup in CARDS:
            out = OUT_DIR / filename
            page.set_content(markup, wait_until="domcontentloaded")
            page.screenshot(path=str(out), full_page=False, clip={"x": 0, "y": 0, "width": W, "height": H})
            paths.append(out)
        browser.close()
    return paths


def write_markdown(paths: list[Path]) -> Path:
    lines = [
        "# Siliņas valdības krišana · vizuāļu banka",
        "",
        "Pamats: `wiki/synthesis/silinas-valdibas-krisana-2026-05.md`.",
        "Stils: atmina.lv tumšā/avīžpapīra palete, Georgia virsraksti, mono metadati, dzintara un sarkanais krīzes akcents.",
        "",
    ]
    for i, path in enumerate(paths):
        title, copy = POST_COPY[i]
        rel = f"2026-05-14-silinas-valdibas-krisana/{path.name}"
        lines += [
            f"## {i}. {title}",
            "",
            f"![{title}]({rel})",
            "",
            "**X teksts:**",
            "",
            "```text",
            copy,
            "```",
            "",
        ]
    md = OUT_DIR.parent / "2026-05-14-silinas-valdibas-krisana.md"
    md.write_text("\n".join(lines), encoding="utf-8")
    return md


def copy_synthesis_hero(hero_path: Path) -> None:
    SYNTHESIS_IMAGE.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(hero_path, SYNTHESIS_IMAGE)
    try:
        from src.image_variants import make_variants

        make_variants(SYNTHESIS_IMAGE, force=True)
    except Exception as exc:  # variants are convenient, not needed for review
        print(f"[warn] could not generate synthesis variants: {exc}")


def main() -> None:
    paths = render_cards()
    md = write_markdown(paths)
    copy_synthesis_hero(paths[0])
    print(f"wrote {len(paths)} PNG cards to {OUT_DIR}")
    print(f"wrote {md}")
    print(f"wrote synthesis hero {SYNTHESIS_IMAGE}")


if __name__ == "__main__":
    main()
