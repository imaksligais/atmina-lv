"""Zāles kvadrātiņš rāda deputātu; «Kā balsoja katrs deputāts» kārtojams (2026-10-16).

Kļūme, ko šis tests ķer: krāsainais kvadrātiņš kartītes zāles vai frakcijas
joslā nepasaka, KURŠ deputāts tā balsoja — vai pasaka nepareizo (cita kārtība
grupā, deputāta jaunākā frakcija `p.f` frakcijas PIE BALSOJUMA vietā (T6),
indekss no cita JSON šķembas). Pieskāriens nedrīkst aizvest prom; bezprofila
deputātam nav saites (agrāk 404); saraksta kārtošana tiešām pārkārto.

Plāns: docs/superpowers/plans/archive/2026-10-16-matrica-iznemsana.md § Task 2b,
Astras recenzija docs/audits/2026-10-16-matrica-likumprojekti/astra-plans-task2b.md.

Fikstūra (pilnais JSON indeksi 0…4, vid = 1000 + indekss; recent = 1…4):
galvenais balsojums V = vid 1003. Tajā: JV Par ×2 (Bite, Cīrule — Cīrulei
NAV profila), ZZS Par (Ābele), JV Pret (Zariņa — vienīgā izveidotā profila
lapa), NA Atturas (Dūmiņa — `f`=PRO, frakcija pie V = NA), ārpusfrakciju
Nebalsoja (Gulbis — `f`=AS), Jansons bez ieraksta. Vārdu, frakciju un balsu
secības savstarpēji atšķiras; gaidītās secības ierakstītas zemāk ar roku.

Serveris sūta produkcijas CSP galveni (assets/_headers); tests ķer
`pageerror`, konsoles kļūdas un `securitypolicyviolation`.
"""
import functools
import json
import re
import shutil
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from tests.test_balsojumi_client_render import _MINIMAL_CTX, _env

sync_api = pytest.importorskip("playwright.sync_api")

WAIT = 6000
NO_F = "ārpusfrakciju"
DAYS = ["2026-08-03", "2026-09-01", "2026-09-08", "2026-09-15", "2026-09-22"]
V = 1003                         # galvenais balsojums
N_OLD = 1                        # tikai pilnajā JSON

# pid: (vārds, slug, pp, balsis 0…4, frakcija pie katra balsojuma 0…4)
DEPS = {
    "11": ("Anna Ābele", "anna-abele", 1, "PNPP.", ["ZZS"] * 5),
    "12": ("Ārija Bite", "arija-bite", 1, "NPAP.", ["JV"] * 5),
    "13": ("Cilda Cīrule", "cilda-cirule", 0, "PPNP.", ["JV"] * 5),
    "14": ("Dace Dūmiņa", "dace-dumina", 1, "PPPAP", ["NA", "NA", "NA", "NA", "PRO"]),
    "15": ("Gatis Gulbis", "gatis-gulbis", 1, "PPPX.", ["AS", "AS", "AS", NO_F, None]),
    "16": ("Juris Jansons", "juris-jansons", 1, "PPP.P", ["JV"] * 5),
    "17": ("Zane Zariņa", "zane-zarina", 1, "PPANP", ["JV"] * 5),
}
PROFILE_PID = "17"

# ── Gaidītais V balsojumā (ierakstīts ar roku, ne ar produkcijas komparatoru) ──
# Zāle: balss grupās Par, Pret, Atturas, Nebalsoja; grupā frakcija pie
# balsojuma (JV < ZZS), tad vārds.
CHAMBER_V = ["12", "13", "11", "17", "14", "15"]
# Frakciju joslas: balss secībā, grupā pēc vārda.
BANDS_V = {"JV": ["12", "13", "17"], "ZZS": ["11"], "NA": ["14"], "ārpus": ["15"]}
POP_V = {
    "11": ("Anna Ābele", "ZZS · Par"),
    "12": ("Ārija Bite", "JV · Par"),
    "13": ("Cilda Cīrule", "JV · Par"),
    "14": ("Dace Dūmiņa", "NA · Atturas"),
    "15": ("Gatis Gulbis", "ārpus frakcijām · Nebalsoja"),
    "17": ("Zane Zariņa", "JV · Pret"),
}
SORT_V = {
    "Pēc vārda": ["Anna Ābele", "Ārija Bite", "Cilda Cīrule", "Dace Dūmiņa",
                  "Gatis Gulbis", "Zane Zariņa"],
    "Pēc frakcijas": ["Ārija Bite", "Cilda Cīrule", "Zane Zariņa", "Dace Dūmiņa",
                      "Anna Ābele", "Gatis Gulbis"],
    "Pēc balss": ["Anna Ābele", "Ārija Bite", "Cilda Cīrule", "Zane Zariņa",
                  "Dace Dūmiņa", "Gatis Gulbis"],
}

_CSP = re.search(r"^\s*Content-Security-Policy:\s*(.+)$",
                 Path("assets/_headers").read_text(encoding="utf-8"), re.M).group(1).strip()


def _fr(facs):
    """Izpildes kodējums kā votes_matrix.py: jauns ieraksts tikai pie maiņas."""
    out = []
    for i, f in enumerate(facs):
        if f is not None and (not out or out[-1][1] != f):
            out.append([i, f])
    return out


def _fixture_pair():
    votes = []
    for i, day in enumerate(DAYS):
        tot = [0, 0, 0]
        fb = {}
        for _, _, _, v, facs in DEPS.values():
            ch = v[i]
            if ch == ".":
                continue
            if ch in "PNA":
                tot["PNA".index(ch)] += 1
            row = fb.setdefault(facs[i], {"f": facs[i], "p": 0, "n": 0, "a": 0, "x": 0})
            row["pnax"["PNAX".index(ch)]] += 1
        votes.append({
            "i": i, "vid": 1000 + i, "d": day, "t": "10:00",
            "m": f"Grozījumi likumā Nr. {i}", "r": "Pieņemts", "tp": "Valsts pārvalde",
            "tot": tot, "uni": False, "co": 0,
            "f": sorted(fb.values(), key=lambda r: (r["f"] == NO_F, r["f"])),
        })
    pols = {}
    for pid, (name, slug, pp, v, facs) in DEPS.items():
        latest = [f for f, ch in zip(facs, v, strict=True) if ch != "." and f != NO_F]
        pols[pid] = {"n": name, "f": latest[-1], "s": slug, "v": v, "fr": _fr(
            [f if ch != "." else None for f, ch in zip(facs, v, strict=True)]),
            "sum": [0, 0, 0, 0], "att": 100}
        if pp:
            pols[pid]["pp"] = 1
    meta = {"version": 1, "generated_at": "2026-10-16T12:00:00", "votes_total": len(votes),
            "encoding": "P=Par,N=Pret,A=Atturas,X=Nebalsoja,.=absent",
            "all_dates": DAYS[::-1]}
    full = {"meta": meta, "votes": votes, "coalitions": [["JV", "NA", "ZZS"]],
            "factions": [], "politicians": pols}
    rvotes = [dict(v, i=j) for j, v in enumerate(votes[N_OLD:])]
    rpols = {}
    for pid, p in pols.items():
        facs = DEPS[pid][4][N_OLD:]
        rv = p["v"][N_OLD:]
        rpols[pid] = dict(p, v=rv, fr=_fr([f if ch != "." else None for f, ch in zip(facs, rv, strict=True)]))
    recent = dict(full, votes=rvotes, politicians=rpols,
                  meta=dict(meta, votes_total=len(rvotes), all_dates=DAYS[N_OLD:][::-1]))
    return full, recent


class _CspHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Content-Security-Policy", _CSP)
        super().end_headers()

    def log_message(self, *args):
        pass


def _site(tmp_path):
    out = tmp_path / "site"
    (out / "data").mkdir(parents=True)
    (out / "politiki").mkdir()
    ctx = dict(
        _MINIMAL_CTX,
        vote_topics=["Valsts pārvalde"],
        deputies=[{"name": d[0], "faction": d[4][0]} for d in DEPS.values()],
        vote_months=["2026-09", "2026-08"],
        vote_sessions=DAYS[::-1],
        metrics=dict(_MINIMAL_CTX["metrics"], total=len(DAYS)),
    )
    (out / "balsojumi.html").write_text(
        _env().get_template("balsojumi.html.j2").render(**ctx), encoding="utf-8")
    full, recent = _fixture_pair()
    (out / "data" / "balsojumi-matrica.json").write_text(
        json.dumps(full, ensure_ascii=False), encoding="utf-8")
    (out / "data" / "balsojumi-matrica-recent.json").write_text(
        json.dumps(recent, ensure_ascii=False), encoding="utf-8")
    name, slug = DEPS[PROFILE_PID][0], DEPS[PROFILE_PID][1]
    (out / "politiki" / f"{slug}.html").write_text(
        f"<!doctype html><html lang=\"lv\"><meta charset=\"utf-8\">"
        f"<title>{name}</title><h1>{name}</h1></html>",
        encoding="utf-8")
    shutil.copytree("assets", out / "assets", dirs_exist_ok=True)
    return out


_INIT = """window.__csp = [];
document.addEventListener('securitypolicyviolation',
  e => window.__csp.push(e.violatedDirective + ' ' + e.blockedURI));"""


class _Ctx:
    """Konteksts + lapa ar kļūdu savācēju; probe = media query vērtības."""

    def __init__(self, browser, errors, **kw):
        # reduced_motion: lapā citādi `scroll-behavior: smooth` — Playwright
        # ritina pie kvadrātiņa, un tas aizslīd no kursora, kamēr lodziņš jau
        # atvērts (zem slodzes tas lika gadījumiem (b)/(f) nejauši krist).
        self.ctx = browser.new_context(reduced_motion="reduce", **kw)
        self.ctx.add_init_script(_INIT)
        self.page = self.ctx.new_page()
        self.page.set_default_timeout(WAIT)
        self.errors = errors
        self.page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
        self.page.on("console", lambda m: errors.append(f"console: {m.text}")
                     if m.type == "error" else None)

    def open(self, url):
        self.page.goto(url)
        self.page.wait_for_selector(f"#vote-{V} .vote-chamber")
        return self.page

    def close(self):
        try:
            csp = self.page.evaluate("window.__csp || []")
        except sync_api.Error:
            csp = []
        self.errors.extend(f"csp: {c}" for c in csp)
        self.ctx.close()


def _seats(page, band_sel):
    return page.eval_on_selector_all(
        band_sel + " [data-p]", "els => els.map(e => e.dataset.p)")


def _pop(page):
    return page.evaluate("""() => { const p = document.getElementById('seat-pop');
      if (!p || !p.matches(':popover-open')) return null;
      const a = p.querySelector('a');
      return { pid: p.dataset.pid || null, vid: p.dataset.vid || null,
               name: (p.querySelector('.seat-pop-name') || {}).textContent || '',
               meta: (p.querySelector('.seat-pop-meta') || {}).textContent || '',
               link: a ? a.getAttribute('href') : null, linkText: a ? a.textContent : null }; }""")


def _wait_pop(page, pid, case):
    try:
        page.wait_for_function(
            "pid => { const p = document.getElementById('seat-pop');"
            " return !!p && p.matches(':popover-open') && p.dataset.pid === pid; }", arg=pid)
    except sync_api.TimeoutError:
        pytest.fail(f"{case}: lodziņš deputātam {pid} neatvērās; ir {_pop(page)}")
    return _pop(page)


def _wait_closed(page, case):
    try:
        page.wait_for_function(
            "() => { const p = document.getElementById('seat-pop');"
            " return !!p && !p.matches(':popover-open'); }")
    except sync_api.TimeoutError:
        pytest.fail(f"{case}: lodziņš neaizvērās; ir {_pop(page)}")


def _adjacent(page, seat_sel):
    """Lodziņš pieslēgts kvadrātiņam: mala pie malas (arī pēc flip)."""
    g = page.locator(seat_sel).evaluate("""el => { const s = el.getBoundingClientRect();
      const p = document.getElementById('seat-pop').getBoundingClientRect();
      return [s.left, s.top, s.right, s.bottom, p.left, p.top, p.right, p.bottom]; }""")
    sl, st, sr, sb, pl, pt, pr, pb = g
    horiz = abs(pl - sl) <= 2 or abs(pr - sr) <= 2
    vert = 0 <= pt - sb <= 14 or 0 <= st - pb <= 14
    return horiz and vert, g


def _mouse_to(page, sel):
    box = page.locator(sel).bounding_box()
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)


def _seat_sel(band, pid):
    return f"#vote-{V} {band} [data-p=\"{pid}\"]"


CHAMBER = ".vote-chamber"


def _frow(label):
    return f".vote-frow:has(.vote-fname:text-is(\"{label}\")) .vote-fseats"


def _case_a(browser, base, errors, notes):
    # (a) Pele uz katra kvadrātiņa katrā joslā: vārds, frakcija PIE balsojuma, balss.
    c = _Ctx(browser, errors, viewport={"width": 1280, "height": 900})
    page = c.open(base)
    notes["mouse_media"] = page.evaluate(
        "matchMedia('(hover: hover) and (pointer: fine)').matches")
    notes["position_area"] = page.evaluate("CSS.supports('position-area: block-end')")
    bands = {CHAMBER: CHAMBER_V}
    for label, pids in BANDS_V.items():
        bands[_frow(label)] = pids
    for band, expected in bands.items():
        sel = f"#vote-{V} {band}"
        got = _seats(page, sel)
        assert got == expected, f"(a) {band}: kvadrātiņu secība {got} ≠ {expected}"
        assert len(set(got)) == len(got), f"(a) {band}: data-p atkārtojas"
        n_empty = page.eval_on_selector_all(sel + " .vs-e[data-p]", "els => els.length")
        assert n_empty == 0, f"(a) {band}: tukšai vietai ir data-p"
        for pid in expected:
            page.keyboard.press("Escape")
            page.hover(_seat_sel(band, pid))
            pop = _wait_pop(page, pid, f"(a) {band}")
            assert (pop["name"], pop["meta"]) == POP_V[pid], f"(a) {band} {pid}: {pop}"
            assert pop["vid"] == str(V), f"(a) {band} {pid}: lodziņa vid {pop['vid']}"
    # Nebalsoja kvadrātiņš ir piesaistīts un nosaukts.
    assert page.get_attribute(_seat_sel(CHAMBER, "15"), "class").split()[-1] == "vs-x"
    return c


def _case_b(browser, base, errors, notes):
    # (b) A→B: teksts UN enkurs mainās; pāreja uz lodziņu to neaizver; Esc aizver.
    c = _Ctx(browser, errors, viewport={"width": 1280, "height": 900})
    page = c.open(base)
    a, b = _seat_sel(CHAMBER, "12"), _seat_sel(_frow("ārpus"), "15")
    # A un B abi skatā, kursoru pārvieto ar mouse.move (Playwright hover() mēdz
    # ritināt arī redzamu elementu). Ja lapa ritinātu, A aizslīdētu no kursora,
    # lodziņš aizvērtos pa taimeri, un A→B ceļš (atvērta lodziņa enkura maiņa)
    # netiktu pārbaudīts — tā mutācija «showPopover bez hide» sākumā palika zaļa.
    page.eval_on_selector(f"#vote-{V}", "el => el.scrollIntoView({block: 'center'})")
    y0 = page.evaluate("scrollY")
    _mouse_to(page, a)
    _wait_pop(page, "12", "(b) A")
    if notes.get("position_area"):
        ok, g = _adjacent(page, a)
        assert ok, f"(b) lodziņš nav pie A: {g}"
    _mouse_to(page, b)
    assert page.evaluate("scrollY") == y0, "(b) lapa ritināja — A→B nav pārbaudīts"
    pop = _wait_pop(page, "15", "(b) B")
    assert pop["name"] == "Gatis Gulbis", f"(b) B teksts: {pop}"
    if notes.get("position_area"):
        notes["geometry_branch"] = "izpildīts"
        ok, g = _adjacent(page, b)
        assert ok, f"(b) enkurs nepārcēlās uz B: {g}"
    else:
        notes["geometry_branch"] = "izlaists (nav position-area)"
    _mouse_to(page, "#seat-pop")
    page.wait_for_timeout(600)
    assert _pop(page) and _pop(page)["pid"] == "15", "(b) pāreja uz lodziņu to aizvēra"
    page.keyboard.press("Escape")
    _wait_closed(page, "(b) Esc")
    assert page.locator(".is-seat-active").count() == 0, "(b) Esc neattīrīja stāvokli"
    _mouse_to(page, b)   # tas pats kvadrātiņš pēc Esc atkal atveras
    _wait_pop(page, "15", "(b) pēc Esc")
    page.mouse.move(2, 2)
    page.wait_for_timeout(600)
    assert _pop(page) is None, "(b) kursors prom — lodziņš palika vaļā"
    return c


def _case_c(browser, base, errors, notes):
    # (c) Peles klikšķis: ar profilu → profila lapa; bez profila → paliek, saites nav.
    c = _Ctx(browser, errors, viewport={"width": 1280, "height": 900})
    page = c.open(base)
    page.click(_seat_sel(CHAMBER, "13"))
    page.wait_for_timeout(400)
    assert page.url == base, f"(c) bezprofila klikšķis navigēja: {page.url}"
    pop = _pop(page)
    assert pop and pop["pid"] == "13" and pop["link"] is None, f"(c) bezprofila lodziņš: {pop}"
    page.keyboard.press("Escape")
    page.click(f"#vote-{V} .vote-who")
    page.wait_for_selector(f"#vote-{V} .vote-tracked tbody tr")
    links = page.eval_on_selector_all(f"#vote-{V} .vote-tracked tbody a",
                                      "els => els.map(e => e.textContent)")
    assert sorted(links) == sorted(n for n, _ in POP_V.values() if n != "Cilda Cīrule"), \
        f"(c) saraksta saites: {links}"
    page.click(_seat_sel(CHAMBER, PROFILE_PID))
    try:
        page.wait_for_url(f"**/politiki/{DEPS[PROFILE_PID][1]}.html")
    except sync_api.TimeoutError:
        pytest.fail(f"(c) klikšķis uz profila kvadrātiņa nenavigēja: {page.url}")
    assert page.inner_text("h1") == DEPS[PROFILE_PID][0]
    return c


def _touch(browser, base, errors, notes, key, **kw):
    c = _Ctx(browser, errors, has_touch=True, **kw)
    page = c.open(base)
    notes[key] = page.evaluate("matchMedia('(hover: hover) and (pointer: fine)').matches")
    page.locator(_seat_sel(CHAMBER, PROFILE_PID)).tap()
    pop = _wait_pop(page, PROFILE_PID, f"(d) {key}")
    assert pop["linkText"] == "Profils →", f"(d) {key}: saite {pop}"
    assert pop["link"] == f"politiki/{DEPS[PROFILE_PID][1]}.html", f"(d) {key}: {pop}"
    page.wait_for_timeout(400)
    assert page.url == base, f"(d) {key}: pieskāriens navigēja uz {page.url}"
    page.locator(_seat_sel(CHAMBER, "14")).tap()      # cits kvadrātiņš → cits deputāts
    _wait_pop(page, "14", f"(d) {key} A→B")
    page.locator(f"#vote-{V} .vote-title").tap()     # pieskāriens citur aizver
    _wait_closed(page, f"(d) {key} citur")
    assert page.url == base, f"(d) {key}: {page.url}"
    return c


def _case_d_phone(browser, base, errors, notes):
    # (d) Telefons: has_touch + is_mobile, 390 px.
    return _touch(browser, base, errors, notes, "touch_phone_media",
                  viewport={"width": 390, "height": 844}, is_mobile=True)


def _case_d_laptop(browser, base, errors, notes):
    # (d) Skārienekrāna klēpjdators: peles media query var atbilst, notikums — pirksts.
    return _touch(browser, base, errors, notes, "touch_laptop_media",
                  viewport={"width": 1280, "height": 900})


def _names(page):
    return page.eval_on_selector_all(
        f"#vote-{V} .vote-tracked tbody tr td:first-child", "els => els.map(e => e.textContent)")


def _case_e(browser, base, errors, notes):
    # (e) Kārtošana: precīzas secības, viena aria-pressed=true, fokuss uz pogas.
    c = _Ctx(browser, errors, viewport={"width": 1280, "height": 900})
    page = c.open(base)
    page.click(f"#vote-{V} .vote-who")
    page.wait_for_selector(f"#vote-{V} .vote-tracked tbody tr")
    assert _names(page) == SORT_V["Pēc vārda"], f"(e) noklusējums: {_names(page)}"
    for label in ("Pēc balss", "Pēc frakcijas", "Pēc vārda"):
        btn = page.locator(f"#vote-{V} .vote-tracked button", has_text=label)
        btn.click()
        assert _names(page) == SORT_V[label], f"(e) {label}: {_names(page)}"
        pressed = page.eval_on_selector_all(
            f"#vote-{V} .vote-tracked button[aria-pressed=\"true\"]",
            "els => els.map(e => e.textContent)")
        assert pressed == [label], f"(e) {label}: aria-pressed {pressed}"
        assert page.evaluate("document.activeElement && document.activeElement.textContent") \
            == label, f"(e) {label}: fokuss nav uz pogas"
    facs = dict(page.eval_on_selector_all(
        f"#vote-{V} .vote-tracked tbody tr",
        "els => els.map(e => [e.cells[0].textContent, e.cells[1].textContent])"))
    assert facs["Dace Dūmiņa"] == "NA" and facs["Gatis Gulbis"] == "ārpus frakcijām", \
        f"(e) frakcija pie balsojuma sarakstā: {facs}"
    return c


def _case_f(browser, base, errors, notes):
    # (f) Pēc «Rādīt vairāk» (pilnā arhīva ielāde, indeksi nobīdās par 1)
    #     agrākas kartītes kvadrātiņš joprojām dod pareizo deputātu.
    c = _Ctx(browser, errors, viewport={"width": 1280, "height": 900})
    page = c.open(base)
    page.wait_for_function(
        "() => document.getElementById('votes-archive-info').textContent"
        " === 'Rāda 4 no 5 balsojumiem.'")
    page.click("#votes-archive-more")
    page.wait_for_selector("#vote-1000")
    for pid in ("15", "17", "14"):
        page.keyboard.press("Escape")
        page.hover(_seat_sel(CHAMBER, pid))
        pop = _wait_pop(page, pid, "(f)")
        assert (pop["name"], pop["meta"]) == POP_V[pid], f"(f) {pid} pēc pilnā arhīva: {pop}"
    return c


_CASES = [_case_a, _case_b, _case_c, _case_d_phone, _case_d_laptop, _case_e, _case_f]


def test_seat_shows_deputy_and_list_sorts(tmp_path):
    """Viens e2e; gadījumi izpildās visi, krītošie nosaukti kopā (mutāciju atskaitei)."""
    out = _site(tmp_path)
    handler = functools.partial(_CspHandler, directory=str(out))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}/balsojumi.html"
    failures, errors, notes = [], [], {}
    try:
        with sync_api.sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except Exception as exc:  # pragma: no cover — nav instalēta pārlūka
                pytest.skip(f"Chromium nav pieejams: {exc}")
            notes["chromium"] = browser.version
            for case in _CASES:
                c = None
                try:
                    c = case(browser, base, errors, notes)
                except (AssertionError, pytest.fail.Exception, sync_api.Error) as exc:
                    lines = str(exc).splitlines()
                    why = [ln.strip() for ln in lines if "intercepts pointer events" in ln][:1]
                    failures.append(f"{case.__name__}: {' | '.join(lines[:1] + why)}")
                finally:
                    if c is not None:
                        c.close()
            browser.close()
    finally:
        server.shutdown()
    print("piezīmes:", notes)
    if errors:
        failures.append("kļūdas/CSP: " + "; ".join(errors))
    assert not failures, "Krītošie gadījumi:\n" + "\n".join(failures)
