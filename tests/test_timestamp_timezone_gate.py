"""`DATE(kolonna, 'localtime')` drīkst stāvēt tikai uz UTC kolonnas.

`CLAUDE.md` § Schema invariants: šajā DB laika zīmogi NAV viena konvencija.
`claims`, `context_notes`, `documents`, `contradictions` glabā **LV** laiku
(rakstīts ar `now_lv()`); `political_tensions.created_at` un
`analyses.created_at` glabā **UTC** (paļaujas uz `DEFAULT CURRENT_TIMESTAMP`).
Tātad UTC kolonnai modifikators ir OBLIGĀTS, bet LV kolonnai tas ir DEFEKTS —
un abi virzieni jau ir bijuši dzīvas kļūdas (`briefs.py` 2026-07-29 lasīja
spriedzes kaili; paneļa backlog 2026-08-01 lika modifikatoru uz `scraped_at`).

Kļūda pati par sevi ir necaurredzama: tā pārbīda rindas par vienu dienu tikai
21:00–23:59 UTC logā, kas ir tieši tas laiks, kad strādā vakara rutīna.

**Šie vārti ir laika zonas ziņā neatkarīgi — tie lasa avota kodu, ne pulksteni.**
Uzvedības tests (`tests/test_dashboard_backlog.py`) šo klasi noķer tikai tur, kur
mašīnas lokālā zona atšķiras no UTC, tāpēc CI (UTC) uz to paļauties nedrīkst.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"

# Vienīgās UTC kolonnas shēmā (`src/schema.sql` komentārs pie political_tensions).
UTC_COLUMNS = {"created_at"}
# `created_at` kā vārds dzīvo arī LV tabulās, tāpēc ar kolonnas vārdu vien nepietiek:
# vaicājumam ar 'localtime' jānosauc arī tabula, kurai tā kolonna tiešām ir UTC.
UTC_TABLES = {"political_tensions", "analyses"}

_SQL_COMMENT = re.compile(r"--[^\n]*")
_LOCALTIME_CALL = re.compile(r"\bdate\s*\(\s*([\w.]+)\s*,\s*'localtime'\s*\)", re.I)
_BARE_DATE_CALL = re.compile(r"\bdate\s*\(\s*([\w.]+)\s*\)", re.I)


def _sql_literals() -> list[tuple[Path, int, str]]:
    """Katrs virknes literālis `src/**/*.py` — ar SQL komentāriem nogrieztiem.

    `ast` saliek blakus stāvošus literāļus vienā mezglā, tāpēc daudzrindu
    vaicājums, kas kodā salikts no gabaliem, šeit atnāk kā viens teksts —
    citādi predikāts blakus rindā izskatītos pēc cita vaicājuma.
    """
    out: list[tuple[Path, int, str]] = []
    for path in sorted(SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                raw = node.value
            elif isinstance(node, ast.JoinedStr):  # f-string SQL (src/briefs.py)
                raw = "".join(
                    v.value for v in node.values
                    if isinstance(v, ast.Constant) and isinstance(v.value, str)
                )
            else:
                continue
            if raw:
                out.append((path, node.lineno, _SQL_COMMENT.sub("", raw)))
    return out


def _named_utc_tables(sql: str) -> set[str]:
    return {t for t in UTC_TABLES if re.search(rf"\b{t}\b", sql)}


def test_localtime_modifier_only_on_utc_columns():
    """LV kolonnai 'localtime' pieskaita svešas dienas rindas un noslēpj savas."""
    offenders = []
    for path, lineno, sql in _sql_literals():
        if "localtime" not in sql.lower():
            continue
        for raw_col in _LOCALTIME_CALL.findall(sql):
            col = raw_col.split(".")[-1]
            if col not in UTC_COLUMNS:
                offenders.append(
                    f"{path.relative_to(SRC.parent)}:{lineno} — DATE({raw_col}, 'localtime'): "
                    f"`{col}` ir LV kolonna (rakstīta ar now_lv()), modifikators to pārbīda"
                )
    assert not offenders, (
        "'localtime' uz LV kolonnas:\n  " + "\n  ".join(offenders)
        + "\nNoņem modifikatoru. NEKAD nelabo pretējā virzienā — now_lv() rakstīšana "
        "UTC kolonnā ir defekts, ne remonts (CLAUDE.md § Schema invariants)."
    )


def test_localtime_query_names_the_utc_table():
    """`created_at` ir arī LV tabulās, tāpēc vārdam vien nedrīkst ticēt."""
    offenders = []
    for path, lineno, sql in _sql_literals():
        if not _LOCALTIME_CALL.search(sql):
            continue
        if not _named_utc_tables(sql):
            offenders.append(
                f"{path.relative_to(SRC.parent)}:{lineno} — 'localtime' vaicājumā, kas "
                f"nenosauc nevienu UTC tabulu ({', '.join(sorted(UTC_TABLES))})"
            )
    assert not offenders, (
        "'localtime' bez UTC tabulas vaicājumā:\n  " + "\n  ".join(offenders)
        + "\nJa tabula tiešām ir UTC, pievieno to UTC_TABLES kopai šajā testā."
    )


def test_utc_column_is_never_read_bare():
    """Pretējais virziens — 2026-07-29 `briefs.py` kļūda.

    UTC kolonna bez modifikatora attiecina 00:00–02:59 LV rindas uz iepriekšējo
    dienu; tieši tāpēc viena spriedze reizē bija pārskatā un „trūka" rutīnā.
    `ORDER BY created_at` modifikatoru neprasa un šeit netiek ķerts — tikai
    `date()`/`DATE()` izsaukumi.
    """
    offenders = []
    for path, lineno, sql in _sql_literals():
        if not _named_utc_tables(sql):
            continue
        without_ok_calls = _LOCALTIME_CALL.sub("", sql)
        for raw_col in _BARE_DATE_CALL.findall(without_ok_calls):
            if raw_col.split(".")[-1] in UTC_COLUMNS:
                offenders.append(
                    f"{path.relative_to(SRC.parent)}:{lineno} — DATE({raw_col}) bez "
                    "'localtime' uz UTC kolonnas"
                )
    assert not offenders, (
        "UTC kolonna lasīta kaili:\n  " + "\n  ".join(offenders)
        + "\nPievieno , 'localtime' — sk. CLAUDE.md § Schema invariants."
    )


def test_every_localtime_occurrence_is_understood():
    """Vārti, kuru zaļā gaisma nav pierādījums, ir sliktāki par nekādiem vārtiem.

    Ja kāds uzraksta 'localtime' formā, ko augšējie regexi neatpazīst, šie
    vārti klusi izietu cauri. Tāpēc katram literālī atrastam 'localtime' ir
    jābūt piesaistītam atpazītam `date(kolonna, 'localtime')` izsaukumam.
    """
    unparsed = []
    for path, lineno, sql in _sql_literals():
        occurrences = sql.lower().count("localtime")
        if not occurrences:
            continue
        matched = len(_LOCALTIME_CALL.findall(sql))
        if matched != occurrences:
            unparsed.append(
                f"{path.relative_to(SRC.parent)}:{lineno} — atpazīti {matched} no "
                f"{occurrences} 'localtime' gadījumiem"
            )
    assert not unparsed, (
        "Neatpazīta 'localtime' forma — vārti to nepārbauda:\n  " + "\n  ".join(unparsed)
        + "\nVai nu pārraksti vaicājumu atpazīstamā formā, vai paplašini regexu."
    )
