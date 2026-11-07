"""Redzamie datumi veidnēs = `16.10.2026`, ne ISO (good-css 5. kārta, D1; 2026-10-21).

Operatora lēmums 2026-10-21: lasītājs visur redz `DD.MM.YYYY` (`lv_date`),
`<time datetime>` atribūts paliek ISO. Pirms labojuma 24+ veidņu vietās bija
ISO `2026-10-06` (pretrunu rindas, kartītes, profila plūsmas, partijas «10-20»
bez gada), citur `16.10.2026` — divi formāti vienā vietnē.

Tests skatās TIKAI veidņu datuma elementus (ne prozu, ne `claims.quote`, ne
markdown saturu — tur datumi paliek kā rakstīti) un katrai grupai pārbauda
saucēju: vismaz viens LV datums atrasts, citādi grupa nav nekas pārbaudījusi.
Renders: komitētā fikstūra (tests/conftest.py `rendered_site`).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

bs4 = pytest.importorskip("bs4")

# (?!\d), ne \b beigās: «2026-10-16T09:30» starp «6» un «T» nav vārda robežas —
# ar \b veidne, kas izdrukā neapstrādātu published_at, paslīdētu garām (M9).
ISO = re.compile(r"\b20\d\d-\d\d-\d\d(?!\d)")
LV = re.compile(r"\b\d\d\.\d\d\.20\d\d\b")
LV_SHORT = re.compile(r"\b\d\d\.\d\d\. \d\d:\d\d\b")  # X plūsmas šaurā kolonna

# (lapu glob, CSS selektors, gaidāmā forma). Selektors trāpa TIKAI datuma
# elementiem (vai meta rindām, kurās nav prozas).
GROUPS = [
    ("pretrunas.html", ".prv2-row-dates", LV),
    ("pretrunas.html", ".prv2-pane-meta time", LV),
    ("pretrunas.html", ".prv2-foot-meta", LV),
    ("pretrunas/*.html", ".prv2-pane-meta time", LV),
    ("pretrunas/*.html", ".prv2-foot-meta", LV),
    ("politiki/*.html", ".profile-feed-meta > span:last-child", LV),
    ("politiki/*.html", ".saites-card-date", LV),
    ("politiki/*.html", "td[style*='nowrap']", LV),
    ("politiki/*.html", ".prv2-pane-meta time", LV),
    ("partijas/*.html", ".party-activity-date", LV),
    ("partijas/*.html", ".party-tab .card span[style*='font-size:0.8rem']", LV),
    ("partijas/*.html", "td[style*='nowrap']", LV),
    ("spriedzes.html", ".spv-meta time", LV),
    ("temas/*.html", ".tema-pozicija-date", LV),
    ("index.html", ".hero-feature-pane-label", LV),
    ("index.html", ".latest-card-date", LV),
    ("index.html", ".brief-featured-date", LV),
    ("index.html", ".focus-quote-meta", LV),
    ("index.html", ".analysis-feat-date", LV),
    ("analizes.html", ".analysis-feat-date", LV),
    ("analizes.html", ".ctx-date", LV),
    ("blog/*.html", ".brief-pagehead-date", LV),
    ("blog/*.html", ".brief-footnav-link", LV),
    ("blog.html", ".blog-entry .date", LV),
    # mūsu ģenerētie virsraksti «Dienas analīze — 2026-10-20» (lv_dates_in_text)
    ("blog.html", ".blog-entry h2", LV),
    ("mediji/*.html", ".recent-date", LV),
    ("mediji/*.html", ".fact-foot .muted", LV),
    ("zinas.html", ".news-card div[style*='font-size:0.82rem'] > span:first-child", LV),
    ("x.html", ".xv1-item-when", LV_SHORT),
]

# Statistika: «Atj. 07.09.2026». Dzīvā vietne rāda curated/ iesaldētās lapas;
# veidnes (generate_statistika) — tās pašas klases.
STAT_GROUPS = [
    ("statistika.html", ".stat-footer span", LV),
    ("statistika.html", ".stat-hero-meta strong", LV),
    ("statistika/*.html", ".stat-detail-meta span", LV),
]


def check_visible_dates(site: Path, counts: dict | None = None, groups=None) -> list[str]:
    """Atgriež kļūdu sarakstu; tukšs = visi grupu datumi latviski.
    `counts` (ja dots) saņem pārbaudīto LV datumu skaitu katrai grupai."""
    errors: list[str] = []
    cache: dict[Path, object] = {}
    for pattern, selector, want in (GROUPS if groups is None else groups):
        found = iso = 0
        sample = ""
        for f in sorted(site.glob(pattern)):
            soup = cache.get(f)
            if soup is None:
                soup = cache[f] = bs4.BeautifulSoup(f.read_text(encoding="utf-8"), "html.parser")
            for el in soup.select(selector):
                text = el.get_text(" ", strip=True)
                if ISO.search(text):
                    iso += 1
                    sample = sample or f"{f.name}: {text[:60]}"
                if want.search(text):
                    found += 1
        if counts is not None:
            counts[f"{pattern} {selector}"] = found
        if iso:
            errors.append(f"{pattern} {selector}: {iso} ISO datumi (piem. {sample})")
        elif not found:
            errors.append(f"{pattern} {selector}: 0 datumu — grupa neko nepārbauda")
    return errors


def test_template_dates_are_latvian(rendered_site):
    counts: dict[str, int] = {}
    errors = check_visible_dates(rendered_site, counts)
    print(f"\n{len(GROUPS)} grupas pārbaudītas, {len(errors)} kļūdas")
    for k, n in counts.items():
        print(f"  {n:5} {k}")
    assert not errors, "\n".join(errors)


def test_time_datetime_attribute_stays_iso(rendered_site):
    """`<time datetime>` paliek mašīnlasāms ISO — mainās tikai redzamais teksts."""
    soup = bs4.BeautifulSoup((rendered_site / "pretrunas.html").read_text(encoding="utf-8"),
                             "html.parser")
    times = soup.select(".prv2-pane-meta time")
    assert times, "pretrunu kartītēs nav <time> — gadījums tukšs"
    for t in times:
        assert re.fullmatch(r"20\d\d-\d\d-\d\d", t["datetime"]), t["datetime"]
        assert LV.fullmatch(t.get_text(strip=True)), t.get_text(strip=True)


@pytest.mark.parametrize("where", ["curated", "generator"])
def test_statistika_update_dates_are_latvian(rendered_site, where):
    """Recenzija M2: «Atj. 2026-09-07» ×21 iesaldētajās curated lapās un
    generate_statistika veidnēs (statistika.py `[:10]`)."""
    root = (Path(__file__).resolve().parents[1] / "curated" / "atmina"
            if where == "curated" else rendered_site)
    counts: dict[str, int] = {}
    errors = check_visible_dates(root, counts, STAT_GROUPS)
    print(f"\n{where}: " + ", ".join(f"{k} {n}" for k, n in counts.items()))
    assert not errors, "\n".join(errors)
