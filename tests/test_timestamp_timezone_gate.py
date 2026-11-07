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

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"

# Vienīgās UTC kolonnas shēmā (`src/schema.sql` komentārs pie political_tensions).
UTC_COLUMNS = {"created_at"}
# `created_at` kā vārds dzīvo arī LV tabulās, tāpēc ar kolonnas vārdu vien nepietiek:
# vaicājumam ar 'localtime' jānosauc arī tabula, kurai tā kolonna tiešām ir UTC.
# Saskaņots 2026-10-19 ar dzīvo shēmu (`PRAGMA table_info`, katrai tabulai ar
# `created_at`) un «Laika zona» komentāriem: `src/schema.sql`, `src/saeima/schema.py`,
# `src/db_migrations.py`. Visām šīm `created_at` = `DEFAULT CURRENT_TIMESTAMP`, ko
# neviens rakstītājs nepadod. `tension_judged` šeit NAV — tai nav `created_at`
# (tikai `judged_at`).
UTC_TABLES = {
    "political_tensions", "analyses", "tension_proposals",
    "document_politicians", "document_politician_suppressions", "document_chunks",
    "tracked_politicians", "parties", "external_profiles", "knab_donors",
    "saeima_sessions", "saeima_agenda_items", "saeima_deputy_positions",
    "saeima_debate_speeches", "saeima_questions", "saeima_question_politicians",
    "saeima_bills", "saeima_bill_stages", "saeima_bill_politicians",
    # 2026-10-22: tēmu partijas. `vote_topic_batches.created_at` = UTC. Tās pašas
    # tabulu grupas `decided_at` (saeima_document_topics) un `applied_at` arī ir UTC,
    # bet šie vārti redz tikai `created_at` (UTC_COLUMNS) — tās paliek ārpus tvēruma.
    "vote_topic_batches", "saeima_document_topics",
}

_SQL_COMMENT = re.compile(r"--[^\n]*")
# `datetime(...)` alongside `date(...)`: since 2026-08-27 the routine-day window
# (`src.briefs.routine_day_window`) compares a UTC column at MINUTE precision
# rather than day precision, so the live form is
# `datetime(created_at, 'localtime') >= ?`. The alternation must try the longer
# name FIRST — `date` matches the first four characters of `datetime` and then
# fails on the paren — and this extension is exactly what
# `test_every_localtime_occurrence_is_understood` demands: a 'localtime' written
# in a shape these regexes do not recognise must never pass silently. It caught
# this change on the first run (4 occurrences, 0 recognised).
_LOCALTIME_CALL = re.compile(
    r"\b(?:datetime|date)\s*\(\s*([\w.]+)\s*,\s*'localtime'\s*\)", re.I
)
_BARE_DATE_CALL = re.compile(r"\b(?:datetime|date)\s*\(\s*([\w.]+)\s*\)", re.I)
# UTC VĒRTĪBAS (ne kolonnas) pārrēķins uz LV — kopš 2026-09-24, kad fiksētais
# '+3 hours' nomainīts uz DST-pareizo 'localtime': trigeris raksta
# `datetime('now', 'localtime')` (src.db._REVIEW_STATUS_AT_EXPR); forma ar `?`
# ir parametra (UTC vērtības) pārrēķins. Tas nav kolonnas lasījums, tāpēc kolonnu vārti uz to neattiecas — bet tā ir
# atpazīta forma, ne klusa caurlaide.
_LOCALTIME_VALUE = re.compile(
    r"\b(?:datetime|date)\s*\(\s*(?:\?|'now')\s*,\s*'localtime'\s*\)", re.I
)


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
            continue
        offenders.extend(
            f"{path.relative_to(SRC.parent)}:{lineno} — DATE({raw_col}, 'localtime'): "
            "kolonna nepieder (vai nav droši piederīga) UTC tabulai"
            for raw_col in _localtime_cols_not_utc(sql)
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
        tables = _alias_tables(sql)
        without_ok_calls = _LOCALTIME_CALL.sub("", sql)
        for raw_col in _BARE_DATE_CALL.findall(without_ok_calls):
            alias, _, col = raw_col.rpartition(".")
            if col not in UTC_COLUMNS:
                continue
            # Kvalificēta kolonna pieder savai tabulai: `date(c.created_at)` uz
            # `claims c` ir LV, pat ja vaicājums pievieno `tracked_politicians`.
            # Nekvalificēta — karogo vienmēr (stop beats write).
            if not alias or tables.get(alias.lower()) in UTC_TABLES:
                offenders.append(
                    f"{path.relative_to(SRC.parent)}:{lineno} — DATE({raw_col}) bez "
                    "'localtime' uz UTC kolonnas"
                )
    assert not offenders, (
        "UTC kolonna lasīta kaili:\n  " + "\n  ".join(offenders)
        + "\nPievieno , 'localtime' — sk. CLAUDE.md § Schema invariants."
    )


# UTC kolonna salīdzināta ar parametru vai literāli BEZ jebkādas funkcijas
# (`t.created_at >= ?`). Abi virzieni un BETWEEN. Labā puse `datetime('now', …)`
# netiek ķerta — tas ir UTC pret UTC un ir pareizi (src/social_agent/candidates.py).
_UTC_COL = rf"(?:(\w+)\.)?(?:{'|'.join(sorted(UTC_COLUMNS))})"
_BARE_COMPARE = re.compile(
    rf"(?<![\w.])({_UTC_COL})\s*(?:>=|<=|<>|!=|=|<|>|\bBETWEEN\b)\s*(?:\?|')"
    rf"|(?:\?|')\s*(?:>=|<=|<>|!=|=|<|>)\s*({_UTC_COL})\b",
    re.I,
)
# Aizstājvārds nedrīkst "apēst" nākamo atslēgvārdu (`FROM claims JOIN …`),
# citādi tabula aiz JOIN netiek reģistrēta un īsts defekts paiet garām.
_FROM_JOIN = re.compile(
    r"\b(?:FROM|JOIN)\s+(\w+)"
    r"(?:\s+(?:AS\s+)?(?!(?:join|left|right|full|inner|outer|cross|natural|where|on"
    r"|using|group|order|limit|union|set|values)\b)(\w+))?",
    re.I,
)
# LV tabulas, kurām TIEŠĀM ir `created_at` un to raksta `now_lv()` (tie paši avoti
# kā UTC_TABLES). `documents` un `contradictions` arī ir LV, bet `created_at` tām
# nav (`scraped_at`, `detected_at`), tāpēc šeit tās nestāv. Nekvalificētu kolonnu
# izlaiž TIKAI, ja nosaukta kāda no šīm; citādi karogo (stop beats write).
LV_CREATED_AT_TABLES = {
    "claims", "context_notes", "social_drafts", "knab_alerts",
    "saeima_votes", "saeima_individual_votes",
}


def _alias_tables(sql: str) -> dict[str, str]:
    """`{aizstājvārds vai tabula: tabula}` no `FROM|JOIN tabula [AS] alias`."""
    tables: dict[str, str] = {}
    for table, alias in _FROM_JOIN.findall(sql):
        tables[table.lower()] = table.lower()
        if alias:
            tables[alias.lower()] = table.lower()
    return tables


_CLAUSE_END = re.compile(r"\b(?:WHERE|GROUP|ORDER|LIMIT|HAVING|UNION)\b|\)", re.I)


def _scope_tables(sql: str, pos: int) -> set[str] | None:
    """Tabulas nekvalificētas kolonnas paša SELECT tvērumā.

    Kolonna WHERE daļā: tabulas no pēdējā `FROM` pirms tās līdz tai (apakšvaicājums
    `(SELECT … FROM political_tensions WHERE datetime(created_at, …))` → tikai
    political_tensions, ne ārējā `claims`). Kolonna SELECT sarakstā: nākamais
    `FROM … JOIN …` posms līdz WHERE/GROUP/… vai `)`. None — literālī nav FROM
    (proza, docstring).
    """
    froms = [m for m in re.finditer(r"\bFROM\b", sql, re.I)]
    before = [m for m in froms if m.start() < pos]
    if before:
        segment = sql[before[-1].start():pos]
    else:
        after = [m for m in froms if m.start() > pos]
        if not after:
            return None
        rest = sql[after[0].start():]
        end = _CLAUSE_END.search(rest)
        segment = rest[: end.start()] if end else rest
    return {t.lower() for t, _ in _FROM_JOIN.findall(segment)}


def _localtime_cols_not_utc(sql: str) -> list[str]:
    """'localtime' kolonnas, kuras NEVAR piesaistīt UTC tabulai.

    Kvalificēta (`c.created_at`) — aizstājvārdam jānorāda uz UTC_TABLES locekli.
    Nekvalificēta — tās SELECT tvērumā (`_scope_tables`) jābūt UTC tabulai un
    nevienai LV tabulai ar `created_at`; divdomīgs → karogo (stop beats write).
    Bez tā `tracked_politicians`/`parties` UTC kopā padarītu `date(c.created_at,
    'localtime')` uz `claims c` neredzamu (re-review 2026-10-19). Literālis bez
    FROM (proza) paliek pie vecā noteikuma — jānosauc UTC tabula.
    """
    tables = _alias_tables(sql)
    bad = []
    for m in _LOCALTIME_CALL.finditer(sql):
        raw_col = m.group(1)
        alias, _, col = raw_col.rpartition(".")
        if col not in UTC_COLUMNS:
            continue  # LV kolonnas vārdu ķer test_localtime_modifier_only_on_utc_columns
        if alias:
            ok = tables.get(alias.lower()) in UTC_TABLES
        else:
            scope = _scope_tables(sql, m.start())
            if scope is None:
                ok = bool(_named_utc_tables(sql))
            else:
                ok = bool(scope & UTC_TABLES) and not scope & LV_CREATED_AT_TABLES
        if not ok:
            bad.append(raw_col)
    return bad


def _bare_utc_comparisons(sql: str) -> list[str]:
    """Kaili salīdzinātas kolonnas, kas TIEŠĀM pieder UTC tabulai.

    `created_at` ir arī LV tabulās, tāpēc tabulu nosaka pēc aizstājvārda
    (`FROM|JOIN tabula [AS] alias`): kvalificēta kolonna tiek karogota tikai,
    ja tās aizstājvārds norāda uz UTC tabulu; nekvalificēta — vienmēr, izņemot,
    ja literālis nosauc LV tabulu ar savu `created_at` (`LV_CREATED_AT_TABLES`).
    """
    tables = _alias_tables(sql)
    named = set(tables.values())
    hits = []
    for m in _BARE_COMPARE.finditer(_LOCALTIME_CALL.sub("", sql)):
        col = m.group(1) or m.group(3)
        alias = m.group(2) or m.group(4)
        if alias:
            if tables.get(alias.lower()) in UTC_TABLES:
                hits.append(col)
        elif named & UTC_TABLES and not named & LV_CREATED_AT_TABLES:
            hits.append(col)
    return hits


@pytest.mark.parametrize(
    ("sql", "flagged"),
    [
        # LV tabulas kolonna vaicājumā ar UTC tabulu — nav UTC salīdzinājums.
        ("SELECT pt.id FROM political_tensions pt JOIN claims c ON c.id = pt.claim_id "
         "WHERE c.created_at >= ?", []),
        ("SELECT t.id FROM political_tensions t WHERE t.created_at >= ?", ["t.created_at"]),
        ("SELECT * FROM political_tensions AS pt WHERE (pt.created_at >= ?)", ["pt.created_at"]),
        ("SELECT * FROM analyses WHERE ? <= created_at", ["created_at"]),
        # Nekvalificēta kolonna, ja nosaukta arī LV tabula — neskaidrs, netiek karogots.
        ("SELECT * FROM analyses a JOIN claims c ON 1 WHERE created_at >= ?", []),
        # Nosaukta LV tabula BEZ `created_at` — nekvalificēta kolonna tiek karogota.
        ("SELECT * FROM analyses JOIN documents d ON 1 WHERE created_at >= ?",
         ["created_at"]),
        # Tabula bez aizstājvārda pirms JOIN: JOIN nedrīkst kļūt par aizstājvārdu.
        ("SELECT * FROM claims JOIN political_tensions t ON 1 WHERE t.created_at >= ?",
         ["t.created_at"]),
        ("SELECT * FROM claims LEFT JOIN political_tensions t ON 1 WHERE t.created_at >= ?",
         ["t.created_at"]),
        ("SELECT * FROM political_tensions t WHERE t.created_at >= datetime('now', ?)", []),
        ("SELECT * FROM political_tensions t WHERE datetime(t.created_at, 'localtime') >= ?", []),
    ],
)
def test_bare_utc_comparison_matcher(sql, flagged):
    assert _bare_utc_comparisons(sql) == flagged


def test_utc_column_is_never_compared_bare():
    """Mutāciju izlases robs T3b (2026-09-24): `datetime(t.created_at,
    'localtime') >= ?` pārrakstīts par `t.created_at >= ?` izgāja cauri visiem
    šiem vārtiem, jo augšējais tests meklē tikai `date()` izsaukumus. Rutīnas
    dienas robeža `?` ir LV laiks, tāpēc kaila UTC kolonna nobīda 2–3 stundas.
    Uzvedības tests (`test_briefs.py::TestTensionDayBoundaryTimezone`) UTC
    mašīnā var izlaisties, tātad CI paliek tikai šie vārti.
    """
    offenders = [
        f"{path.relative_to(SRC.parent)}:{lineno} — `{col}` salīdzināts kaili ar LV vērtību"
        for path, lineno, sql in _sql_literals()
        if _named_utc_tables(sql)
        for col in _bare_utc_comparisons(sql)
    ]
    assert not offenders, (
        "UTC kolonna salīdzināta bez 'localtime':\n  " + "\n  ".join(offenders)
        + "\nIetin `datetime(kolonna, 'localtime')` — sk. CLAUDE.md § Schema invariants. "
        "Ja kolonna pieder LV tabulai, 'localtime' NELIEC — sadali vaicājumu vai "
        "kvalificē kolonnu ar tās tabulas aizstājvārdu."
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
        matched = len(_LOCALTIME_CALL.findall(sql)) + len(_LOCALTIME_VALUE.findall(sql))
        if matched != occurrences:
            unparsed.append(
                f"{path.relative_to(SRC.parent)}:{lineno} — atpazīti {matched} no "
                f"{occurrences} 'localtime' gadījumiem"
            )
    assert not unparsed, (
        "Neatpazīta 'localtime' forma — vārti to nepārbauda:\n  " + "\n  ".join(unparsed)
        + "\nVai nu pārraksti vaicājumu atpazīstamā formā, vai paplašini regexu."
    )


@pytest.mark.parametrize(
    ("sql", "flagged"),
    [
        # LV kolonna ar 'localtime' blakus UTC tabulai — jākarogo (re-review 2026-10-19).
        ("SELECT 1 FROM claims c JOIN tracked_politicians p ON p.id = c.opponent_id "
         "WHERE date(c.created_at, 'localtime') >= ?", ["c.created_at"]),
        ("SELECT 1 FROM political_tensions t JOIN claims c ON 1 "
         "WHERE datetime(t.created_at, 'localtime') >= ?", []),
        # Nekvalificēta, bet nosaukta arī LV tabula — divdomīgs, karogo.
        ("SELECT 1 FROM analyses a JOIN claims c ON 1 WHERE date(created_at, 'localtime') = ?",
         ["created_at"]),
        ("SELECT 1 FROM analyses WHERE date(created_at, 'localtime') = ?", []),
        # Apakšvaicājums: kolonna pieder savam FROM, ne ārējai `claims`.
        ("SELECT c.topic FROM claims c LEFT JOIN (SELECT topic FROM political_tensions "
         "WHERE datetime(created_at, 'localtime') >= ?) t ON t.topic = c.topic", []),
        # SELECT sarakstā — tvērums ir nākamais FROM.
        ("SELECT date(created_at, 'localtime') FROM claims WHERE 1", ["created_at"]),
    ],
)
def test_localtime_alias_matcher(sql, flagged):
    assert _localtime_cols_not_utc(sql) == flagged
