"""Vārti: publiskajās lapās X rokturis ir @atminaLV, nekad @atmina_lv.

Kāpēc tests: `@atmina_lv` NEEKSISTĒ (twikit-verificēts 2026-07-22), bet
`templates/base.html.j2` to lika `twitter:site` metatagā KATRĀ lapā, un
`curated/` momentuzņēmumos tas bija iecepts 13 failos. Nekas to nenoķēra, jo
nepareizs rokturis nav ne renderēšanas kļūda, ne salauzta saite — lapa
izskatās normāli, tikai Twitter kartītes attiecinājums ved uz nekurieni.
Atrasts un labots 2026-09-08.

Divas puses ar saucēju: avota puse (`templates/`) un momentuzņēmuma puse
(`curated/`). Tikai viena no tām nesargātu — kurētās lapas renderu apiet.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WRONG = 'content="@atmina_lv"'
WRONG_BARE = "@atmina_lv"
RIGHT = "@atminaLV"


def _scan(paths: list[Path]) -> list[str]:
    # Skenē ATRIBŪTA formu, ne kailu virkni: base.html.j2 komentārs pats piemin
    # nepareizo rokturi, lai brīdinātu, un kails meklējums to nolasītu kā pārkāpumu.
    return [
        str(p.relative_to(ROOT))
        for p in paths
        if WRONG in p.read_text(encoding="utf-8", errors="ignore")
    ]


def test_templates_never_use_the_nonexistent_handle():
    files = sorted((ROOT / "templates").rglob("*.j2"))
    assert files, "nav neviena šablona — vārti ar 0 saucēju nav vārti"
    offenders = _scan(files)
    assert not offenders, (
        f"{WRONG_BARE} neeksistē; lieto {RIGHT}. Pārbaudīti {len(files)} šabloni, "
        f"pārkāpēji: {offenders}"
    )


def test_curated_snapshots_never_use_the_nonexistent_handle():
    files = sorted((ROOT / "curated").rglob("*.html"))
    assert files, "nav nevienas kurētās lapas — vārti ar 0 saucēju nav vārti"
    offenders = _scan(files)
    assert not offenders, (
        f"{WRONG_BARE} neeksistē; lieto {RIGHT}. Kurētās lapas renderu APIET, tāpēc "
        f"šablona labojums tās nesalabo — jālabo failā. Pārbaudītas {len(files)} "
        f"lapas, pārkāpēji: {offenders}"
    )


def test_base_template_actually_declares_the_right_handle():
    """Negatīvā puse viena nepietiek: fails bez roktura arī izietu abus augšējos."""
    base = (ROOT / "templates" / "base.html.j2").read_text(encoding="utf-8")
    assert f'content="{RIGHT}"' in base, (
        f"base.html.j2 vairs nedeklarē twitter:site={RIGHT}"
    )
