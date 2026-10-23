"""`balsojumi.html#vote-N` saraksts atver pats, arī ārpus pirmajām 200 kartītēm (2026-10-16).

Kļūme, ko šis tests ķer: saite no likumprojekta lapas uz vecu balsojumu
(ārpus sākuma 200 kartītēm vai tikai pilnajā arhīvā) neatrod kartīti. Agrāk
saraksts tad pārslēdzās uz Matricas cilni; pēc Matricas izņemšanas tas pats
uzliek balsojuma sēdes dienas filtru (mēnesis + sēde) un, ja dienā ir >200
balsojumu, ielādē nākamo lapu līdz mērķim.

Trešā (Task 2): vecā `?tab=matrix` saite pēc Matricas izņemšanas atver parasto
sarakstu — `tab` parametrs noņemts, pārējie parametri un hash paliek, lapā nav
cilņu joslas un Matricas paneļa, konsolē 0 kļūdu.

Otrā kļūme (Astra #1): novēlota recent atbilde pēc pilnā arhīva ielādes
pazemināja datus — pēc tam vecās dienas filtrs deva 0 kartīšu.

Plāns: docs/superpowers/plans/archive/2026-10-16-matrica-iznemsana.md § Task 1.
Fikstūra: 5 vecākās dienas balsojumi (tikai pilnajā) + 205 vidējās dienas +
20 jaunākās dienas = 230; recent = bez vecākajiem 5. Vecākā un vidējā diena
ir vienā mēnesī — lai (e) sēdes maiņa paliek tā paša mēneša ietvaros.
"""
import functools
import json
import shutil
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlparse

import pytest

from tests.test_balsojumi_client_render import _MINIMAL_CTX, _env
from tests.test_balsojumi_readability import _FIXTURE, _vote

sync_api = pytest.importorskip("playwright.sync_api")

OLD_DAY, MID_DAY, NEW_DAY = "2026-08-03", "2026-08-13", "2026-09-02"
N_OLD, N_MID, N_NEW = 5, 205, 20
N_ALL = N_OLD + N_MID + N_NEW          # 230
TOPIC_A, TOPIC_B = "Valsts pārvalde", "Izglītība"
WAIT = 8000                             # ms — mutācija krīt ātri, ne pēc 30 s

# vid = 1000 + pilnā JSON indekss (hronoloģiski augošs).
VID_OLD = 1002          # tikai pilnajā
VID_MID_203 = 1007      # vidējās dienas 203. kartīte (dilstošā secībā)
VID_MID = 1020          # vidējās dienas 190. kartīte; nefiltrētajā sarakstā 210.
VID_MISSING = 999999999
VID_NEW_B = 1210        # jaunākās dienas TOPIC_B balsojums — pirmajā renderā ar tema=TOPIC_B


def _fixture_pair():
    votes = []
    for i in range(N_ALL):
        day = OLD_DAY if i < N_OLD else MID_DAY if i < N_OLD + N_MID else NEW_DAY
        v = _vote(i, day, f"Grozījumi likumā Nr. {i}", "Pieņemts")
        # Jaunākajā dienā daļa balsojumu ir otrā tēmā — (c) tēma ir zināma un
        # sašaurina sarakstu, bet mērķim (VID_MID, TOPIC_A) neatbilst.
        if day == NEW_DAY and i % 2 == 0:
            v["tp"] = TOPIC_B
        votes.append(v)
    pols = {
        "1": {"n": "Anna Ābele", "f": "JV", "s": "anna-abele", "v": "P" * N_ALL},
        "2": {"n": "Cilda Cīrule", "f": "ZZS", "s": "cilda-cirule", "v": "N" * N_ALL},
    }
    full = {
        "meta": dict(_FIXTURE["meta"], votes_total=N_ALL,
                     all_dates=[NEW_DAY, MID_DAY, OLD_DAY]),
        "votes": votes,
        "coalitions": _FIXTURE["coalitions"],
        "factions": _FIXTURE["factions"],
        "politicians": {k: dict(p, sum=[0, 0, 0, 0], att=100, dis=[])
                        for k, p in pols.items()},
    }
    recent_votes = []
    for j, v in enumerate(votes[N_OLD:]):
        recent_votes.append(dict(v, i=j))
    recent = dict(full, votes=recent_votes,
                  meta=dict(full["meta"], votes_total=len(recent_votes),
                            all_dates=[NEW_DAY, MID_DAY]),
                  politicians={k: dict(p, v=p["v"][N_OLD:])
                               for k, p in full["politicians"].items()})
    return full, recent


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def _site(tmp_path):
    out = tmp_path / "site"
    (out / "data").mkdir(parents=True)
    ctx = dict(
        _MINIMAL_CTX,
        vote_topics=[TOPIC_B, TOPIC_A],
        deputies=[{"name": "Anna Ābele", "faction": "JV"},
                  {"name": "Cilda Cīrule", "faction": "ZZS"}],
        vote_months=["2026-09", "2026-08"],
        vote_sessions=[NEW_DAY, MID_DAY, OLD_DAY],
        metrics=dict(_MINIMAL_CTX["metrics"], total=N_ALL),
    )
    html = _env().get_template("balsojumi.html.j2").render(**ctx)
    (out / "balsojumi.html").write_text(html, encoding="utf-8")
    full, recent = _fixture_pair()
    (out / "data" / "balsojumi-matrica.json").write_text(
        json.dumps(full, ensure_ascii=False), encoding="utf-8")
    (out / "data" / "balsojumi-matrica-recent.json").write_text(
        json.dumps(recent, ensure_ascii=False), encoding="utf-8")
    shutil.copytree("assets", out / "assets", dirs_exist_ok=True)
    return out


FULL_GLOB = "**/data/balsojumi-matrica.json"
RECENT_GLOB = "**/data/balsojumi-matrica-recent.json"


def _open(browser, url, *, full_status=None, hold_recent=None):
    """Jauna lapa (jauns konteksts) + pilnā JSON pieprasījumu skaitītājs."""
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.set_default_timeout(WAIT)
    counter = {"full": 0}

    def on_full(route):
        counter["full"] += 1
        if full_status:
            route.fulfill(status=full_status, body="kļūda")
        else:
            route.continue_()

    page.route(FULL_GLOB, on_full)
    if hold_recent is not None:
        # Aiztur recent atbildi: maršruts paliek neatrisināts, līdz tests to atlaiž.
        page.route(RECENT_GLOB, lambda route: hold_recent.append(route))
    page.goto(url, wait_until="domcontentloaded" if hold_recent is not None else "load")
    return page, counter


def _info(page):
    return page.inner_text("#votes-archive-info")


def _wait_info(page, text, case):
    try:
        page.wait_for_function(
            "t => document.getElementById('votes-archive-info').textContent === t", arg=text)
    except sync_api.TimeoutError:
        pytest.fail(f"{case}: gaidīja info «{text}», ir «{_info(page)}» (adrese {page.url})")


def _wait_highlight(page, vid, case):
    try:
        page.wait_for_function(
            "id => { const el = document.getElementById('vote-' + id);"
            " return !!el && el.style.outline.indexOf('2px') !== -1; }", arg=vid)
    except sync_api.TimeoutError:
        pytest.fail(f"{case}: kartīte vote-{vid} nav iezīmēta; info «{_info(page)}», "
                    f"adrese {page.url}")


def _query(page):
    return parse_qs(urlparse(page.url).query)


def _selected(page, select_id):
    return page.eval_on_selector_all(
        f"#{select_id} .multi-select-option.selected", "els => els.map(e => e.dataset.value)")


def _case_0(browser, base):
    # (0) Saucējs: bez hash pirmā lapa ir 200 no 230 — mērķi ārpus tās eksistē.
    page, counter = _open(browser, base)
    _wait_info(page, f"Rāda 200 no {N_ALL} balsojumiem.", "(0)")
    assert counter["full"] == 0, "(0) nefiltrēts sākums nedrīkst ielādēt pilno arhīvu"
    for vid in (VID_OLD, VID_MID_203, VID_MID):
        assert page.query_selector(f"#vote-{vid}") is None, \
            f"(0) vote-{vid} jābūt ārpus pirmās lapas, citādi gadījums ir tukšs"
    return page


def _case_a_e(browser, base):
    # (a) Vecākās dienas balsojums (tikai pilnajā arhīvā).
    page, counter = _open(browser, f"{base}#vote-{VID_OLD}")
    _wait_highlight(page, VID_OLD, "(a)")
    _wait_info(page, f"Rāda {N_OLD} no {N_OLD} balsojumiem.", "(a)")
    u = urlparse(page.url)
    assert u.query == f"menesis=2026-08&sede={OLD_DAY}", f"(a) adrese: {page.url}"
    assert u.fragment == f"vote-{VID_OLD}", f"(a) hash: {page.url}"
    assert _selected(page, "session-select") == [OLD_DAY], "(a) sēdes vadīkla"
    assert _selected(page, "month-select") == ["2026-08"], "(a) mēneša vadīkla"
    assert counter["full"] == 1, f"(a) pilnais arhīvs jāielādē tieši vienreiz, ir {counter['full']}"
    shared = page.url

    # (a) Tās pašas adreses atvēršana jaunā lapā dod to pašu.
    page2, _ = _open(browser, shared)
    try:
        _wait_highlight(page2, VID_OLD, "(a) atkārtota atvēršana")
        _wait_info(page2, f"Rāda {N_OLD} no {N_OLD} balsojumiem.", "(a) atkārtota atvēršana")
        assert page2.url == shared, f"(a) atkārtota atvēršana mainīja adresi: {page2.url}"
    finally:
        page2.close()

    # (e) Pēc (a) lietotājs pats izvēlas CITU tā paša mēneša sēdi →
    #     hash apstrāde vairs nepārslēdz filtrus atpakaļ.
    page.click("#session-trigger")
    page.click(f'#session-select .multi-select-option[data-value="{OLD_DAY}"]')
    page.click(f'#session-select .multi-select-option[data-value="{MID_DAY}"]')
    page.wait_for_timeout(300)
    _wait_info(page, f"Rāda 200 no {N_MID} balsojumiem.", "(e)")
    assert _query(page) == {"menesis": ["2026-08"], "sede": [MID_DAY]}, \
        f"(e) adrese neatbilst lietotāja izvēlei: {page.url}"
    assert _selected(page, "session-select") == [MID_DAY], "(e) sēdes vadīkla"
    assert _selected(page, "month-select") == ["2026-08"], "(e) mēneša vadīkla"
    dates = set(page.eval_on_selector_all(
        "#votes-archive-cards .vote-card", "els => els.map(e => e.dataset.date)"))
    assert dates == {MID_DAY}, f"(e) kartītes no citām dienām: {dates}"
    return page


def _case_b(browser, base):
    # (b) Vidējās dienas 203. kartīte → automātiska otrā lapa; recent pietiek.
    page, counter = _open(browser, f"{base}#vote-{VID_MID_203}")
    _wait_highlight(page, VID_MID_203, "(b)")
    _wait_info(page, f"Rāda {N_MID} no {N_MID} balsojumiem.", "(b)")
    assert _query(page) == {"menesis": ["2026-08"], "sede": [MID_DAY]}, f"(b) adrese: {page.url}"
    assert counter["full"] == 0, \
        f"(b) diena ir recent shardā — pilnais arhīvs nav vajadzīgs, pieprasīts {counter['full']}×"
    return page


def _case_c(browser, base):
    # (c) Zināma, mērķim neatbilstoša tēma adresē → sēdes filtrs to aizstāj.
    page, _ = _open(browser, f"{base}?tema={quote(TOPIC_B)}#vote-{VID_MID}")
    _wait_highlight(page, VID_MID, "(c)")
    assert _query(page) == {"menesis": ["2026-08"], "sede": [MID_DAY]}, f"(c) adrese: {page.url}"
    assert _selected(page, "topic-select") == [], "(c) tēmas vadīkla nav notīrīta"
    assert page.inner_text("#topic-trigger span").strip() == "Visas tēmas", "(c) tēmas etiķete"
    return page


def _case_c2(browser, base):
    # (c2) Pretrunīgi deputāta/meklēšanas/«Tikai dalītie» filtri adresē.
    page, _ = _open(
        browser, f"{base}?deputats={quote('Anna Ābele')}&q=zzz&dalitie=1#vote-{VID_OLD}")
    _wait_highlight(page, VID_OLD, "(c2)")
    assert _query(page) == {"menesis": ["2026-08"], "sede": [OLD_DAY]}, f"(c2) adrese: {page.url}"
    assert page.input_value("#vote-search") == "", "(c2) meklēšanas lauks nav notīrīts"
    assert page.get_attribute("#vote-split-toggle", "aria-pressed") == "false", "(c2) dalītie"
    assert _selected(page, "deputy-select") == [], "(c2) deputātu vadīkla nav notīrīta"
    return page


def _case_d(browser, base):
    # (d) Neeksistējošs vid → «nav atrasts», filtri un adrese nemainās.
    page, counter = _open(browser, f"{base}#vote-{VID_MISSING}")
    _wait_info(page, "Balsojums nav atrasts arhīvā.", "(d)")
    assert urlparse(page.url).query == "", f"(d) adrese mainīta: {page.url}"
    assert counter["full"] == 1, f"(d) pilnais arhīvs pārbaudīts {counter['full']}×"
    return page


def _case_d2(browser, base):
    # (d2) Pilnā arhīva ielādes kļūda ≠ «nav atrasts»; bez atkārtotas cilpas.
    page, counter = _open(browser, f"{base}#vote-{VID_OLD}", full_status=500)
    _wait_info(page, "Balsojumus neizdevās ielādēt: HTTP 500", "(d2)")
    page.wait_for_timeout(300)
    assert _info(page) == "Balsojumus neizdevās ielādēt: HTTP 500", "(d2) teksts mainījās"
    assert urlparse(page.url).query == "", f"(d2) adrese mainīta: {page.url}"
    assert counter["full"] == 1, f"(d2) pilnais arhīvs pieprasīts {counter['full']}×"
    return page


def _case_f(browser, base):
    # (f) Ielādes secība (Astra #1): recent aizkavējas, pilnais pienāk pirmais.
    held = []
    page, counter = _open(browser, base, hold_recent=held)
    page.wait_for_function("() => document.getElementById('vote-search') !== null")
    assert len(held) == 1, "(f) recent pieprasījums nav aizturēts"
    page.fill("#vote-search", "likumā")
    _wait_info(page, f"Rāda 200 no {N_ALL} balsojumiem.", "(f) meklēšana")
    assert counter["full"] == 1, "(f) meklēšana neielādēja pilno arhīvu"
    held[0].continue_()
    page.wait_for_timeout(400)   # novēlotā recent atbilde tiek apstrādāta
    page.click("#month-trigger")
    page.click('#month-select .multi-select-option[data-value="2026-08"]')
    page.click("#session-trigger")
    page.click(f'#session-select .multi-select-option[data-value="{OLD_DAY}"]')
    _wait_info(page, f"Rāda {N_OLD} no {N_OLD} balsojumiem.", "(f)")
    return page


def _case_g(browser, base):
    # (g) Vecā Matricas saite: `tab` noņemts, tēmas filtrs + hash paliek; mērķis
    #     ir pirmajā renderā, tāpēc filtri netiek mainīti. Cilņu nav, 0 kļūdu.
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.set_default_timeout(WAIT)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.goto(f"{base}?tab=matrix&tema={quote(TOPIC_B)}#vote-{VID_NEW_B}")
    _wait_highlight(page, VID_NEW_B, "(g)")
    _wait_info(page, f"Rāda {N_NEW // 2} no {N_NEW // 2} balsojumiem.", "(g)")
    u = urlparse(page.url)
    assert parse_qs(u.query) == {"tema": [TOPIC_B]}, f"(g) adrese: {page.url}"
    assert u.fragment == f"vote-{VID_NEW_B}", f"(g) hash: {page.url}"
    assert _selected(page, "topic-select") == [TOPIC_B], "(g) tēmas vadīkla"
    for sel in ("#votes-matrix-tab", ".subtab-bar", "#matrix-root", '[role="tablist"]'):
        assert page.query_selector(sel) is None, f"(g) lapā vēl ir {sel}"
    assert page.is_visible("#votes-list-tab"), "(g) saraksts nav redzams"
    assert errors == [], f"(g) konsoles kļūdas: {errors}"
    return page


def _case_h(browser, base):
    # (h) good-css 5. kārta A3: ritinot sēdes dienas galvene pielīp ZEM lipīgās
    #     nav (agrāk `top: 0` → paslēpta zem tās, datums nekad neredzams).
    page, _ = _open(browser, base)
    _wait_info(page, f"Rāda 200 no {N_ALL} balsojumiem.", "(h)")
    page.evaluate("""() => {
      const cards = document.querySelectorAll('#votes-archive-cards .vote-card');
      window.scrollTo({top: cards[10].getBoundingClientRect().top + window.scrollY, behavior: 'instant'});
    }""")
    page.wait_for_timeout(100)
    g = page.evaluate("""() => {
      const nav = document.querySelector('.nav').getBoundingClientRect();
      const h = document.querySelector('#votes-archive-cards .vote-day-group');
      return {pos: getComputedStyle(h).position, top: h.getBoundingClientRect().top,
              navBottom: nav.bottom, scrollY: window.scrollY};
    }""")
    assert g["pos"] == "sticky", f"(h) dienas galvene nav lipīga: {g}"
    assert g["scrollY"] > 300, f"(h) lapa nav ritināta — gadījums tukšs: {g}"
    assert abs(g["top"] - g["navBottom"]) <= 1, (
        f"(h) pielipusī dienas galvene top={g['top']:.0f}px, nav apakša {g['navBottom']:.0f}px")
    return page


_CASES = [_case_0, _case_a_e, _case_b, _case_c, _case_c2, _case_d, _case_d2, _case_f, _case_g,
          _case_h]


def test_vote_deeplink_opens_session_day_in_list(tmp_path):
    """Viens e2e; gadījumi (0)…(f) izpildās visi, un krītošie tiek nosaukti kopā —
    tā mutāciju atskaitē redzams, KURŠ gadījums katru mutāciju noķer."""
    out = _site(tmp_path)
    handler = functools.partial(_QuietHandler, directory=str(out))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}/balsojumi.html"
    failures = []
    try:
        with sync_api.sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except Exception as exc:  # pragma: no cover — nav instalēta pārlūka
                pytest.skip(f"Chromium nav pieejams: {exc}")
            for case in _CASES:
                try:
                    case(browser, base).close()
                except (AssertionError, pytest.fail.Exception, sync_api.Error) as exc:
                    failures.append(str(exc).splitlines()[0])
            browser.close()
    finally:
        server.shutdown()
    assert not failures, "Krītošie gadījumi:\n" + "\n".join(failures)
