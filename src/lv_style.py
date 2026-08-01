"""LV-stilistikas linteris brief-writer aģentam.

Mērķis: noķert tipiskās rakstības kļūdas, ko 2026-05-06 dienas brief
(context_notes #195) prasīja labot post-publish — % atstarpi, anglicismus
`aksi/startā/ataka/polemika`, blakus teikumu uzvārda atkārtojumus.

Divi skenēšanas līmeņi (2026-08-09):

- **Mehāniskie noteikumi** (procentu atstarpe, anglicismi) skenē arī markdown
  tabulu šūnas. `stance` teksts tabulās ir MŪSU vārdi, ne citāts, tāpēc
  CLAUDE.md gramatikas vārti uz to attiecas; vienīgais izņēmums ir
  `claims.quote`. Līdz 2026-08-09 tabulas bija pilnībā aizsargātas, tāpēc
  linteris redzēja 37 % pārskata un „0 problēmu" nozīmēja „neskatījos".
- **Prozas noteikumi** (ol-trap, blakus-uzvārda atkārtojums) paliek tikai
  naratīvā. Tabulas rindā tie dod viltus pozitīvus — `adjacent-surname-repetition`
  nostrādā, kad handle sakrīt ar uzvārdu (novērots 2026-08-07 melnrakstā).

`<div class="context-box">` bloki (verbatim no `context_notes`) un HTML
komentāri netiek skenēti nevienā līmenī.

Saucējs: `lint_lv_style_report()` atgriež DIVAS asis, un abas ir vajadzīgas:

- `scanned_chars`/`total_chars` — cik teksta likumi redzēja;
- `rules_run`/`rules_total` + `rules_skipped` — cik likumu vispār skrēja.

Rakstzīmju ass viena pati melo. 2026-08-09 (tajā pašā commitā, kas ieviesa
saucēju) 4. likums CI-ā neskrēja NEVIENU reizi — `data/atmina.db` ir
gitignorēta, uzvārdu ielāde klusi atgrieza tukšu kopu, likums izlaidās, un
`coverage_pct` joprojām rādīja 100 %. Tieši tā klase, ko saucējam bija
jānoķer, tikai citā asī.

`lint_lv_style()` atgriešanas forma (saraksts; `[]` = tīrs) NAV mainīta —
`brief-writer` un `weekly-brief-writer` prompti to pārbauda ar `== []`.
Uzvārdu kopu drīkst padot ar `surnames=` (testiem un hermētiskiem
palaidieniem); `None` = ielasa no DB, kā līdz šim.
"""

from __future__ import annotations

import re
import sys

#: Cik likumu `lint_lv_style` satur. Saucējs `lint_lv_style_report()` to
#: salīdzina ar faktiski izpildītajiem — likums, kas klusi izlaižas, ir
#: neizpildīti vārti, ne tīrs rezultāts.
RULES_TOTAL = 4


def _load_tracked_surnames_report() -> tuple[set[str], str | None]:
    """Lasa tracked_politicians uzvārdus no DB.

    Return: `(uzvārdi, skip_reason)`. `skip_reason` ir `None` tikai tad, kad
    kopa tiešām ir ielasīta — tukša kopa VIENMĒR nāk ar iemeslu, jo klusa
    tukša kopa izslēdz 4. likumu, neatstājot nekādu pēdu.

    Ņem tikai pēdējo vārdu personvārdā (uzvārds), kas sākas ar lielo burtu —
    tas izfiltrē institucionālos slot-us (`Saeimas ziņas`, `IR žurnāls`),
    kuru otrais vārds ir mazo burtu lietvārds. Ģenitīva u.c. locījumi
    atstāti — adjacent-repetition pārbaude uztver tikai precīzus atkārtojumus.
    """
    try:
        from src.db import get_db
        db = get_db()
        names = set()
        rows = db.execute("SELECT name FROM tracked_politicians WHERE relationship_type != 'inactive'").fetchall()
        for r in rows:
            tokens = (r["name"] or "").split()
            if not tokens:
                continue
            last = tokens[-1].strip(",.;:()")
            if len(last) >= 5 and last[0].isupper():
                names.add(last)
        db.close()
    except Exception as exc:
        reason = f"uzvārdu ielāde neizdevās ({exc.__class__.__name__}: {exc})"
        print(f"WARNING: lv_style — {reason}; 4. likums NEskrien", file=sys.stderr)
        return set(), reason
    if not names:
        reason = "tracked_politicians atdeva 0 izmantojamu uzvārdu"
        print(f"WARNING: lv_style — {reason}; 4. likums NEskrien", file=sys.stderr)
        return set(), reason
    return names, None


def _load_tracked_surnames() -> set[str]:
    """Atpakaļsaderīgs apvalks — atgriež tikai kopu, bez iemesla."""
    return _load_tracked_surnames_report()[0]


ANGLICISMS = {
    "aksi": "asi",
    "aksis": "ass",
    "startā": "sākumā",
    "ataka": "uzbrukums",
    "atakas": "uzbrukumi/uzbrukšana",
    "atakām": "uzbrukumiem",
    "polemika": "diskusija",
    "polemiku": "diskusiju",
    "polemikā": "diskusijā",
    # "melīšana" nav LV — pareizais ir "melošana" (no melot+šana).
    "melīšana": "melošana",
    "melīšanu": "melošanu",
    "melīšanas": "melošanas",
    "melīšanā": "melošanā",
    # "konsenss" = anglicisms → "vienprātība"/"vienota nostāja"/"saskaņa".
    "konsenss": "vienprātība",
    "konsensu": "vienprātību",
    "konsensa": "vienprātības",
    "konsensā": "vienprātībā",
}


def _strip_protected_regions(content: str, protect_tables: bool = True) -> str:
    """Aizvieto aizsargātos apgabalus ar tukšām rindām.

    `protect_tables=True` (prozas līmenis) izņem arī markdown tabulu rindas;
    `protect_tables=False` (mehāniskais līmenis) tās atstāj. Context-box bloki
    un HTML komentāri tiek izņemti abos gadījumos.
    """
    lines = content.split("\n")
    out: list[str] = []
    in_context_box = False
    for line in lines:
        stripped = line.strip()
        # Context-box blok: <div class="context-box"> ... </div>
        # Bokss var atvērties UN aizvērties vienā rindā — tad karogs NEDRĪKST
        # palikt ieslēgts, citādi tas apēd visu tekstu līdz nākamajam `</div>`
        # (2026-08-17: coverage_pct 7,4 % ar „0 problēmu").
        open_idx = line.find("<div class=\"context-box\"")
        if open_idx != -1:
            in_context_box = "</div>" not in line[open_idx:]
            out.append("")
            continue
        if in_context_box:
            if "</div>" in line:
                in_context_box = False
            out.append("")
            continue
        # Markdown tabulas rindas — tikai prozas līmenī
        if protect_tables and stripped.startswith("|") and stripped.endswith("|"):
            out.append("")
            continue
        # HTML komentāri (DIENAS STATS, NARATĪVA MATERIĀLS u.c.)
        if stripped.startswith("<!--") and stripped.endswith("-->"):
            out.append("")
            continue
        out.append(line)
    return "\n".join(out)


def lint_lv_style(content: str, surnames: set[str] | None = None) -> list[dict]:
    """Atgriež problēmu sarakstu.

    Katra problēma: {"rule": str, "match": str, "context": str, "suggestion": str}.
    Empty list = brief tīrs.

    `surnames=None` ielasa izsekoto politiķu uzvārdus no DB (kā līdz šim);
    padota kopa tiek lietota tāpat, kas ļauj 4. likumam skriet arī tur, kur
    DB nav (CI, hermētiski testi) — bez tā likums klusi izlaižas.

    Saucēju (cik teksta skenēts UN cik likumu skrēja) dod
    `lint_lv_style_report()` — šī funkcija apzināti atgriež tikai sarakstu,
    jo aģentu prompti to pārbauda ar `== []`.
    """
    # Mehāniskie noteikumi (1–2) redz arī tabulu šūnas; prozas noteikumi (3–4)
    # tikai naratīvu.
    scan = _strip_protected_regions(content, protect_tables=False)
    prose = _strip_protected_regions(content, protect_tables=True)
    issues: list[dict] = []

    # 1. Atstarpe pirms % — meklē `<digit>%` bez priekšstāvošas atstarpes
    for m in re.finditer(r"\b(\d+(?:[.,]\d+)?)(%)", scan):
        # Konteksts ±25 simbolu
        ctx_start = max(0, m.start() - 25)
        ctx_end = min(len(scan), m.end() + 25)
        issues.append({
            "rule": "no-space-before-percent",
            "match": m.group(0),
            "context": scan[ctx_start:ctx_end].replace("\n", " "),
            "suggestion": f"{m.group(1)} %",
        })

    # 2. Anglicisms (case-insensitive, vārda robežās)
    for word, replacement in ANGLICISMS.items():
        for m in re.finditer(rf"\b{re.escape(word)}\b", scan, re.IGNORECASE):
            ctx_start = max(0, m.start() - 25)
            ctx_end = min(len(scan), m.end() + 25)
            issues.append({
                "rule": "anglicism",
                "match": m.group(0),
                "context": scan[ctx_start:ctx_end].replace("\n", " "),
                "suggestion": replacement,
            })

    # 3. Sakārtota-saraksta slazds — rindkopa, kas sākas ar "N. " (cipars +
    # punkts + atstarpe). Markdown to padara par <ol><li> un apēd ciparu, tāpēc
    # "4. jūnijā" pārlūkā parādās kā "1. jūnijā" (izskatās pēc datuma kļūdas).
    # Skenē tikai ne-bullet rindas; tabulas/context-box jau nostriptotas augšā.
    for line in prose.split("\n"):
        stripped = line.lstrip()
        if stripped.startswith("-"):
            continue
        m = re.match(r"\d+\.\s", stripped)
        if m:
            issues.append({
                "rule": "ol-trap",
                "match": m.group(0).strip(),
                "context": line.strip()[:50].replace("\n", " "),
                "suggestion": "Nesāc rindkopu ar 'N. ' — markdown to padara par sarakstu un apēd ciparu.",
            })

    # 4. Adjacent surname repetition — atrod tracked politiķu uzvārdus DB un
    # skenē, vai viens uzvārds parādās divreiz vienā teikumā/bullet-ā tuvāk
    # par 60 simboliem (paragrāfos) vai 30 simboliem (bullet rindās). Iestādes/
    # valstis (Saeima, Latvija) nav uzvārdi, jo `_load_tracked_surnames`
    # ņem tikai pēdējo personvārda tokenu.
    if surnames is None:
        surnames = _load_tracked_surnames()
    if surnames:
        # Sadalīt pa rindām un grupēt — bullet rinda = atsevišķs konteksts
        for line in prose.split("\n"):
            if not line.strip():
                continue
            is_bullet = line.lstrip().startswith("-")
            gap_threshold = 30 if is_bullet else 60
            for name in surnames:
                positions = [m.start() for m in re.finditer(rf"\b{re.escape(name)}\b", line)]
                if len(positions) < 2:
                    continue
                for i in range(len(positions) - 1):
                    gap = positions[i + 1] - positions[i]
                    if gap < gap_threshold:
                        ctx = line[max(0, positions[i] - 20):positions[i + 1] + len(name) + 20]
                        issues.append({
                            "rule": "adjacent-surname-repetition",
                            "match": name,
                            "context": ctx.replace("\n", " "),
                            "suggestion": f"Pārformulē, lai {name} neparādās divreiz tuvās klauzulās.",
                        })
                        break

    return issues


def _visible_chars(text: str) -> int:
    """Rakstzīmju skaits ne-tukšajās rindās — salīdzināms starp oriģinālu un
    nostriptoto versiju, jo striptēšana rindu aizvieto ar tukšu, ne izmet."""
    return sum(len(line) for line in text.split("\n") if line.strip())


def lint_lv_style_report(content: str, surnames: set[str] | None = None) -> dict:
    """`lint_lv_style()` + saucēji abās asīs.

    Atgriež `{"issues", "total_chars", "scanned_chars", "prose_scanned_chars",
    "coverage_pct", "rules_total", "rules_run", "rules_skipped",
    "surnames_loaded"}`.

    - Teksta ass: `scanned_chars` = cik rakstzīmju redzēja mehāniskie
      noteikumi, `prose_scanned_chars` = cik redzēja prozas noteikumi.
    - Likumu ass: `rules_run` / `rules_total`, un `rules_skipped` ar iemeslu
      katram izlaistajam likumam.

    Kāpēc VAJADZĪGAS ABAS: 2026-08-08 pārskatā #435 linteris skenēja 8 515 no
    22 839 zīmēm (37 %) un atgrieza 0 problēmu — teksta ass to noķer. Bet
    2026-08-09, tikko šis saucējs bija ieviests, izrādījās, ka 4. likums CI-ā
    neskrien nemaz (gitignorēta DB → tukša uzvārdu kopa → likums izlaižas),
    kamēr `coverage_pct` rādīja 100 %. Viena ass klusē par otras robu.
    """
    total = _visible_chars(content)
    scanned = _visible_chars(_strip_protected_regions(content, protect_tables=False))
    prose_scanned = _visible_chars(_strip_protected_regions(content, protect_tables=True))

    if surnames is None:
        surnames, skip_reason = _load_tracked_surnames_report()
    else:
        skip_reason = None if surnames else "padota tukša uzvārdu kopa"

    rules_skipped: list[dict] = []
    if not surnames:
        rules_skipped.append({
            "rule": "adjacent-surname-repetition",
            "reason": skip_reason or "uzvārdu kopa tukša",
        })

    return {
        "issues": lint_lv_style(content, surnames=surnames),
        "total_chars": total,
        "scanned_chars": scanned,
        "prose_scanned_chars": prose_scanned,
        "coverage_pct": round(100 * scanned / total, 1) if total else 0.0,
        "rules_total": RULES_TOTAL,
        "rules_run": RULES_TOTAL - len(rules_skipped),
        "rules_skipped": rules_skipped,
        "surnames_loaded": len(surnames),
    }
