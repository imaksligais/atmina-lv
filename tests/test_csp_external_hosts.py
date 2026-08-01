"""CSP ārējo hostu allowlist vārti.

Konteksts (2026-08-09, BACKLOG § Dati/DB): dzīvā vietne servē striktu
Content-Security-Policy no ``assets/htaccess.template``. Jauna ĀRĒJA hosta
(script/style/font/image/connect kontekstā) pievienošana lapām lokāli neko
nelauž (preview galveni nesniedz), bet produkcijā resurss klusi nomirst.
2026-08-09 mērījums: vienīgās reālās nesakritības bija ``<link rel=preconnect>``
uz fonts.googleapis.com / fonts.gstatic.com ×900 lapas (CSP3 preconnect krīt
zem connect-src) — salabots htaccess.template, un šis tests sargā klasi.

Vārtu apgalvojums: katrs ārējais hosts, kas parādās fetch-direktīvas kontekstā
lapu avotos, ir CSP allowlistā. Allowlistu parsē no ``assets/htaccess.template``
(vienīgais patiesības avots — tas pats fails, ko servē produkcija), ne
hardkodē šeit. ``<a href>`` ir izņēmums (CSP neregulē navigāciju), tāpat
``og:image``/``twitter:image`` meta (to lasa boti, ne lapas CSP).
"""

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_HTACCESS = _ROOT / "assets" / "htaccess.template"

_DIRECTIVES = ("script-src", "style-src", "font-src", "img-src", "connect-src")

_TAG_RE = re.compile(r"<(\w+)\b([^>]*)>", re.IGNORECASE)
_ATTR_RE = re.compile(r"""\b(srcset|src|href|poster)\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
_STYLE_BLOCK_RE = re.compile(r"<style\b[^>]*>(.*?)</style>", re.IGNORECASE | re.DOTALL)
_CSS_URL_RE = re.compile(r"""url\(\s*["']?([^"')]+)["']?\s*\)""", re.IGNORECASE)
_FETCH_RE = re.compile(
    r"""(?:fetch|XMLHttpRequest\.open|sendBeacon|EventSource|WebSocket)\s*\(\s*["']([^"']+)["']""",
    re.IGNORECASE,
)
_HOST_RE = re.compile(r"^https?://([^/\s]+)", re.IGNORECASE)


def _parse_allowlist() -> dict[str, set[str]]:
    """Izvelk hostu kopas pa CSP direktīvām no htaccess.template."""
    text = _HTACCESS.read_text(encoding="utf-8")
    m = re.search(r'Content-Security-Policy\s+"([^"]+)"', text)
    assert m, "CSP galvene nav atrasta htaccess.template"
    allow: dict[str, set[str]] = {d: set() for d in _DIRECTIVES}
    for part in m.group(1).split(";"):
        tokens = part.split()
        if not tokens or tokens[0] not in allow:
            continue
        for tok in tokens[1:]:
            hm = _HOST_RE.match(tok)
            if hm:
                allow[tokens[0]].add(hm.group(1).lower())
    return allow


def _host(url: str) -> str | None:
    m = _HOST_RE.match(url.strip())
    return m.group(1).lower() if m else None


def _scan_html(text: str) -> list[tuple[str, str]]:
    """Atgriež (direktīva, hosts) pārus no HTML teksta."""
    out: list[tuple[str, str]] = []
    for block in _STYLE_BLOCK_RE.findall(text):
        out.extend(("css-url", h) for h in _css_hosts(block))
    for tag, attrs in _TAG_RE.findall(text):
        tag = tag.lower()
        attr_map = dict()
        for name, val in _ATTR_RE.findall(attrs):
            attr_map[name.lower()] = val
        if tag == "a" or (tag == "meta"):
            continue  # navigācija un og:/twitter: meta — ārpus fetch direktīvām
        for name, val in attr_map.items():
            if tag == "script" and name == "src":
                out.extend(("script-src", h) for h in _url_hosts(val))
            elif tag == "link" and name == "href":
                rel = re.search(r"""rel\s*=\s*["']([^"']+)["']""", attrs, re.IGNORECASE)
                relv = rel.group(1).lower() if rel else ""
                directive = {
                    "stylesheet": "style-src",
                    "preconnect": "connect-src",
                    "dns-prefetch": "connect-src",
                    "icon": "img-src",
                    "apple-touch-icon": "img-src",
                }.get(relv)
                if directive:
                    out.extend((directive, h) for h in _url_hosts(val))
            elif tag in ("img", "source", "video", "iframe", "embed") and name in (
                "src",
                "srcset",
                "poster",
            ):
                out.extend(("img-src", h) for h in _url_hosts(val))
        sm = re.search(r"""style\s*=\s*["']([^"']+)["']""", attrs, re.IGNORECASE)
        if sm:
            out.extend(("css-url", h) for h in _css_hosts(sm.group(1)))
    return out


def _url_hosts(val: str) -> list[str]:
    hosts = []
    for piece in val.split(","):  # srcset kandidāti
        url = piece.strip().split()[0] if piece.strip() else ""
        h = _host(url)
        if h:
            hosts.append(h)
    return hosts


def _css_hosts(css: str) -> list[str]:
    return [h for h in (_host(u) for u in _CSS_URL_RE.findall(css)) if h]


# og-card.html.j2 nav lapa — Playwright to renderē PNG'ā lokāli
# (src/render/contradictions.py) un tas NEKAD nenonāk output kokā, tāpēc uz to
# neattiecas ne CSP, ne apmeklētāja IP noplūde. Izslēgšanu sargā
# test_og_card_is_never_deployed: ja tas kādreiz sāks nonākt output/, vārti
# atkal ieslēdzas.
# quote_card.html.j2 pievienots 2026-08-15: tā pati klase kā og-card —
# `src/social_agent/visuals.py::render_quote_card` to renderē PNG'ā ar Playwright
# lokāli, output kokā tas nenonāk nekad. Līdz šim to izslēdza NEJAUŠI (plakans
# `templates/*.j2` glob to nesasniedza apakšmapē), tagad izslēgums ir apzināts
# un zem tā paša drošinātāja.
_NOT_SERVED = {"og-card.html.j2", "quote_card.html.j2"}

# Faila tipi, kas var nest ārēju hostu.
_SCANNED_EXTS = ("*.html", "*.js", "*.css", "*.svg")

# Minimālais saucējs SOURCE pusē (bez `output/`), lai vārti nevar klusi sarukt
# līdz tukšumam: 35 šabloni (36 mīnus quote_card) + 14 curated lapas +
# 26 assets `*.js` (t.sk. 4 vendorētie cuelume) + style.css = 76.
# Mērīts 2026-08-15; ja skaitlis krīt, kaut kas ir pazudis no skenējuma.
_MIN_SOURCE_FILES = 70


def _files():
    """Katrs fails, kas DZĪVAJĀ vietnē var nest ārēju hostu.

    Saucējs šeit ir pati būtība (CLAUDE.md § „vārti, kas nevar nokrist"). Līdz
    2026-08-15 šī funkcija ņēma `templates/*.j2` un `assets/*.js` PLAKANI, tāpēc
    klusi izlaida (a) 14 ar roku rakstītās `curated/atmina/` lapas, ko
    `src/render/_orchestrator.py` kopē burtiski uzbūvētajā kokā, un (b) 4
    vendorētos `assets/cuelume/*.js`, kas arī tiek deploytoti
    (`output/atmina/assets/cuelume/` eksistē). CI vidē, kur `output/` nav,
    saucējs bija 57 failu 71 vietā — un tieši curated lapas bija tās, kas
    2026-08-15 nesa svešu hostu (`4234fa1a`).
    """
    out_dir = _ROOT / "output" / "atmina"
    if out_dir.exists():
        for ext in _SCANNED_EXTS:
            yield from sorted(out_dir.rglob(ext))
    yield from _source_files()


def _source_files():
    """Avota puse — skenēta neatkarīgi no tā, vai `output/` ir uzbūvēts."""
    yield from sorted(
        p for p in (_ROOT / "templates").rglob("*.j2") if p.name not in _NOT_SERVED
    )
    for ext in _SCANNED_EXTS:
        yield from sorted((_ROOT / "curated").rglob(ext))
    yield from sorted((_ROOT / "assets").rglob("*.js"))
    yield _ROOT / "assets" / "style.css"


def test_scan_denominator_is_not_silently_empty():
    """Vārti bez saucēja nav pierādījums — šis tests sargā pašu skenējumu.

    Ja kāds sašaurina `_source_files()` (piem. atgriež plakanu glob), atradumu
    neesamība sāktu nozīmēt neskatīšanos, un tas izskatītos tieši tāpat kā tīrs
    rezultāts. Šis ir vienīgais tests failā, kas to atšķir.
    """
    files = list(_source_files())
    assert len(files) >= _MIN_SOURCE_FILES, (
        f"CSP skenējums saruka līdz {len(files)} failiem (gaidīts ≥{_MIN_SOURCE_FILES}) — "
        "vārti tagad ziņo 'tīrs' par to, ko tie vairs nelasa"
    )
    names = {p.name for p in files}
    assert "chrome-v1.js" in names, "assets/*.js pazudis no skenējuma"
    assert any(p.parent.name == "cuelume" or "cuelume" in p.parts for p in files), \
        "vendorētais assets/cuelume/ pazudis no skenējuma"
    assert any("curated" in p.parts for p in files), "curated/ lapas pazudušas no skenējuma"


def test_not_served_templates_are_never_deployed():
    """Drošinātājs zem _NOT_SERVED izslēgšanas (og-card + quote_card)."""
    out_dir = _ROOT / "output" / "atmina"
    if not out_dir.exists():
        import pytest
        pytest.skip("nav uzbūvēta koka — nav ko pārbaudīt")
    for name in _NOT_SERVED:
        stem = name.split(".")[0]
        stray = list(out_dir.rglob(f"{stem}*.html"))
        assert not stray, (
            f"{stem} nonācis servētajā kokā: {stray} — CSP izslēgšana vairs nav pamatota"
        )


def _collect():
    """Savāc (direktīva, hosts) pārus no visiem avotiem + saucēju metriku."""
    pairs: list[tuple[str, str]] = []
    files = list(_files())
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        if f.suffix in (".html", ".j2"):
            pairs.extend(_scan_html(text))
        if f.suffix in (".css", ".svg") or f.name == "style.css":
            pairs.extend(("css-url", h) for h in _css_hosts(text))
        if f.suffix == ".js":
            for url in _FETCH_RE.findall(text):
                h = _host(url)
                if h:
                    pairs.append(("connect-src", h))
    return files, pairs


def test_external_hosts_in_csp_allowlist():
    allow = _parse_allowlist()
    allow_hosts = set().union(*allow.values())
    files, pairs = _collect()

    # Tukšo-vārtu aizsargs: vārti bez nevienas atsauces ir salauzti, ne tīri.
    assert files, "nav neviena skenējama faila — vārti nevar būt tukši"
    assert pairs, "nav nevienas ārējās atsauces — vārti nevar būt tukši"

    violations: dict[str, set[str]] = {}
    for directive, host in pairs:
        if directive == "css-url":
            # CSS url() var būt fonts vai attēls — der, ja ir kādā no abām kopām
            if host not in allow["font-src"] and host not in allow["img-src"]:
                violations.setdefault("font-src/img-src", set()).add(host)
        elif host not in allow[directive]:
            violations.setdefault(directive, set()).add(host)

    report = ", ".join(f"{d}: {sorted(hs)}" for d, hs in sorted(violations.items()))
    assert not violations, (
        f"ārējie hosti ārpus CSP allowlist ({report}); "
        f"skenēti {len(files)} faili, {len(pairs)} atsauces, "
        f"{len(allow_hosts)} allowlistēti hosti"
    )


# Vienīgā trešā puse, ko servētās lapas drīkst aizsniegt. Kopš 2026-08-15
# fonti un D3 ir pašmitināti, tāpēc saraksts ir tieši viens ieraksts.
# Pievienot te jaunu hostu drīkst tikai apzināti — tas nozīmē, ka apmeklētāja
# IP sāk aiziet vēl vienam saņēmējam, un tas jāatspoguļo VISOS trijos
# nesējos: templates/about.html.j2 (§ Privātums), docs/data-policy.md (§ 11)
# un ARCHITECTURE.md. 2026-08-16: data-policy.md § 11 bija palicis pie
# "atmina neizmanto analītikas pakalpojumus" — nepatiess kopš Umami.
_EXPECTED_EXTERNAL_HOSTS = {"cloud.umami.is"}


def test_gate_reports_denominators():
    """Saucēja vārti + trešo pušu sprūdrats.

    Agrāk te bija `len(hosts) >= 2` kā "parsētājs nav salūzis" sargs. Pēc
    fontu/D3 pašmitināšanas patiesais skaits ir 1, tāpēc slieksnis ir
    aizstāts ar precīzu kopu: tā vienlaikus pieķer arī parsētāja avāriju
    (kopa kļūst tukša) UN jaunu trešo pusi, kas ielavījusies nemanot.
    """
    files, pairs = _collect()
    hosts = {h for _, h in pairs}
    print(f"\nskenēti {len(files)} faili, {len(pairs)} ārējās atsauces, "
          f"{len(hosts)} unikāli hosti: {sorted(hosts)}")
    assert hosts == _EXPECTED_EXTERNAL_HOSTS, (
        f"servēto lapu ārējo hostu kopa mainījusies: {sorted(hosts)} vs "
        f"{sorted(_EXPECTED_EXTERNAL_HOSTS)} — ja tas ir apzināti, atjauno arī "
        f"CSP allowlist, ARCHITECTURE.md un privātuma paziņojumu"
    )
