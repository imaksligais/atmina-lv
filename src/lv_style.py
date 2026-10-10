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

`<div class="context-box">` bloki: **mehāniskie likumi tos neredz**
(verbatim `context_notes` teksts — CLAUDE.md § Grammar gate izņēmums), bet
**prozas likumi redz** (tā ir mūsu rakstīta tendenču piezīme, tāpēc B garuma
forma uz to attiecas; operatora lēmums 2026-09-02). HTML komentāri netiek
skenēti nevienā līmenī.

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
RULES_TOTAL = 6


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


def _strip_protected_regions(
    content: str,
    protect_tables: bool = True,
    protect_context_box: bool = True,
) -> str:
    """Aizvieto aizsargātos apgabalus ar tukšām rindām.

    `protect_tables=True` (prozas līmenis) izņem arī markdown tabulu rindas;
    `protect_tables=False` (mehāniskais līmenis) tās atstāj.

    `protect_context_box` šķir DIVUS līgumus (operatora lēmums 2026-09-02),
    kas līdz tam bija sajaukti vienā:

    - **Mehāniskie likumi (% atstarpe, anglicismi) kastīti NEREDZ** — kastītes
      teksts nāk verbatim no `context_notes`, un CLAUDE.md § Grammar gate to
      izņem no laboto vietu saraksta. `protect_context_box=True`.
    - **Prozas likumi kastīti REDZ** — tā ir MŪSU rakstīta tendenču piezīme,
      tāpēc B garuma forma uz to attiecas. 2026-09-01 § Imigrācija palags
      dzīvoja tieši kastītē (206 vārdi). `protect_context_box=False`; tad
      izgriež tikai HTML tagu rindas, ne saturu.

    Ligzdoto `<div>` uzskaita ar dziļumu, ne ar pirmo `</div>`. Skelets raksta
    `<div class="context-box" markdown="1">` → `<div class="context-label">…
    </div>` → teksts → `</div>`, tāpēc pirmā-`</div>` loģika karogu izslēdza
    jau uz `context-label` rindas un VISA piezīme klusi nonāca mehāniskajos
    likumos (atrasts 2026-09-02; līdzšinējais tests lietoja vienkāršo formu,
    ko skelets neraksta nekad). Vienrindas bokss joprojām apēd tikai sevi —
    tur dziļums atgriežas 0 tajā pašā rindā (2026-08-17 regresija).
    """
    lines = content.split("\n")
    out: list[str] = []
    box_depth = 0
    for line in lines:
        stripped = line.strip()
        open_idx = line.find("<div class=\"context-box\"")
        if open_idx != -1 and box_depth == 0:
            tail = line[open_idx:]
            box_depth = tail.count("<div") - tail.count("</div>")
            out.append("")
            continue
        if box_depth > 0:
            box_depth += line.count("<div") - line.count("</div>")
            if box_depth < 0:
                box_depth = 0
            # Prozas līmenī kastītes SATURS paliek; nost iet tikai tagu rindas.
            keep = (
                not protect_context_box
                and stripped
                and not stripped.startswith("<div")
                and not stripped.startswith("</div")
            )
            out.append(line if keep else "")
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


#: A+B prozas forma (2026-09-02) — sk. brief-shared-rules.md § Prozas bloku
#: forma. B: neviens aģenta rakstīts prozas bloks nepārsniedz 120 vārdus.
PROSE_BLOCK_MAX_WORDS = 120
#: A: ja tēmai ir konteksta kastīte, sintēze zem tabulas ir VIENS teikums.
#: Vārti mēra vārdus, ne teikuma zīmes: LV kārtas skaitļi ("24. jūlijā")
#: padara punktu skaitīšanu nedrošu, bet 22 vārdi (09-01 Ukrainas sintēze pēc
#: labojuma) pret 149 (09-01 Imigrācijas sintēze pirms) dalās tīri.
SYNTHESIS_WITH_BOX_MAX_WORDS = 40
#: ...BET garums viens pats pāršauj piecas reizes. 2026-09-02 mērījums pār 30
#: pārskatiem: 80 garuma-trāpījumi, no tiem tikai 13 ar >=3 kopīgiem nosauktiem
#: aktieriem kastītē UN sintēzē; 39 ar NULLI kopīgu — tur kastīte ir fons un
#: sintēze nosauc dienas runātājus, t.i. papildinājums, ne dublējums. Tāpēc
#: vārtiem vajag ABAS puses. Slieksnis kalibrēts pret abiem zināmajiem īstajiem
#: dublējumiem (2026-09-01 § Imigrācija un § Ukraina — abi tieši uz 3).
#: NB: kopa satur nominatīvus, tāpēc locītās formas ("Edvīna Šnores") nesakrīt
#: — reālā pārklāšanās ir LIELĀKA par izmērīto, un slieksnis tādēļ konservatīvs.
SYNTHESIS_SHARED_ACTORS_MIN = 3


def _context_box_text(chunk: str) -> str:
    """Kastītes SATURS (bez `<div>` tagiem) vienā `### Tēma` gabalā."""
    kept = _strip_protected_regions(chunk, protect_tables=True,
                                    protect_context_box=False)
    outside = _strip_protected_regions(chunk, protect_tables=True,
                                       protect_context_box=True)
    outside_lines = set(outside.split("\n"))
    return "\n".join(ln for ln in kept.split("\n")
                     if ln.strip() and ln not in outside_lines)


def _named_actors(text: str, surnames: set[str]) -> set[str]:
    """Izsekoto politiķu uzvārdi, kas tekstā parādās pie vārda robežām."""
    return {n for n in surnames if re.search(rf"\b{re.escape(n)}\b", text)}


def _prose_units(prose: str) -> list[tuple[str, str]]:
    """Sadala prozu mērāmās vienībās: ``("bullet"|"paragraph", teksts)``.

    Aizzīmju rinda ir SAVA vienība — tas ir viss B noteikuma jēgas kodols:
    piecas 40 vārdu aizzīmes ir skenējamas, viena 200 vārdu rindkopa nav.
    Virsraksti un tukšās rindas noslēdz iesākto rindkopu.
    """
    units: list[tuple[str, str]] = []
    buf: list[str] = []

    def flush() -> None:
        if buf:
            units.append(("paragraph", " ".join(buf)))
            buf.clear()

    for line in prose.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            flush()
            continue
        if stripped.startswith("- ") or stripped.startswith("* "):
            flush()
            units.append(("bullet", stripped))
            continue
        buf.append(stripped)
    flush()
    return units


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
    scan = _strip_protected_regions(content, protect_tables=False,
                                    protect_context_box=True)
    prose = _strip_protected_regions(content, protect_tables=True,
                                     protect_context_box=False)
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

    # 5. Prozas bloks garāks par 120 vārdiem (B noteikums). Skenē prozas skatu,
    # tāpēc kastītes un tabulas te neiekrīt — kastīte pārskatā ir verbatim
    # `context_notes` teksts, ko aģents nedrīkst mainīt. Pašu piezīmi lintē
    # atsevišķi: bez `<div>` iesaiņojuma tā ir parasta proza un iekrīt šajā
    # pašā likumā (`/dienas-rutina` 6. solis).
    for _kind, text in _prose_units(prose):
        n_words = len(text.split())
        if n_words > PROSE_BLOCK_MAX_WORDS:
            issues.append({
                "rule": "prose-block-too-long",
                "match": f"{n_words} vārdi",
                "context": text[:60].replace("\n", " "),
                "suggestion": (
                    f"Bloks ir {n_words} vārdi (limits {PROSE_BLOCK_MAX_WORDS}). "
                    "Dali; 4+ nosaukti aktieri iet sarakstā, viens aktieris = viena rinda."
                ),
            })

    # 6. Tēmai ar konteksta kastīti sintēze zem tabulas ir viens teikums
    # (A noteikums). Skelets kastītes izvelk ar `routine_day_window(date)`,
    # tāpēc kastīte VIENMĒR ir tās pašas dienas piezīme, un pilna sintēze zem
    # tabulas stāsta to pašu dienu otrreiz. 2026-09-01 § Imigrācija: 206 vārdu
    # kastīte + 149 vārdu sintēze = 355 vārdi nepārtrauktas prozas.
    # Bez uzvārdu kopas 6. likums NESKRIEN (sk. `lint_lv_style_report`
    # `rules_skipped`) — kopīgo aktieru pārbaude bez tās nav izpildāma, un
    # klusi izlaists likums ir tieši tā klase, ko saucējs eksistē ķert.
    for chunk in (re.split(r"(?m)^###\s", content)[1:] if surnames else []):
        if '<div class="context-box"' not in chunk:
            continue
        # Kastīti un komentārus nost, tabulas atstāj — pēc pēdējās tabulas
        # rindas sākas tas, ko rakstīja aģents.
        chunk_box = _context_box_text(chunk)
        lines = _strip_protected_regions(chunk, protect_tables=False).split("\n")
        table_rows = [i for i, ln in enumerate(lines) if ln.strip().startswith("|")]
        if not table_rows:
            continue
        tail = "\n".join(lines[table_rows[-1] + 1:])
        box_actors = _named_actors(chunk_box, surnames)
        for _kind, text in _prose_units(tail):
            n_words = len(text.split())
            if n_words <= SYNTHESIS_WITH_BOX_MAX_WORDS:
                continue
            shared = box_actors & _named_actors(text, surnames)
            if len(shared) < SYNTHESIS_SHARED_ACTORS_MIN:
                continue
            issues.append({
                "rule": "context-box-synthesis-duplication",
                "match": f"{n_words} vārdi, {len(shared)} kopīgi aktieri",
                "context": text[:60].replace("\n", " "),
                "suggestion": (
                    "Kastīte un sintēze stāsta par tiem pašiem cilvēkiem ("
                    + ", ".join(sorted(shared))
                    + "), tāpēc lasītājs vienu dienu izlasa divreiz. Sintēze zem "
                    "tabulas ir ne vairāk kā viens teikums par to, kā kastītē NAV; "
                    "ja jaunā nav nekā, izlaid rindkopu."
                ),
            })

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
    scanned = _visible_chars(_strip_protected_regions(
        content, protect_tables=False, protect_context_box=True))
    prose_scanned = _visible_chars(_strip_protected_regions(
        content, protect_tables=True, protect_context_box=False))

    if surnames is None:
        surnames, skip_reason = _load_tracked_surnames_report()
    else:
        skip_reason = None if surnames else "padota tukša uzvārdu kopa"

    rules_skipped: list[dict] = []
    if not surnames:
        reason = skip_reason or "uzvārdu kopa tukša"
        # Abi likumi salīdzina nosauktus cilvēkus, tāpēc bez uzvārdu kopas
        # neviens no tiem nav izpildāms.
        rules_skipped.append({"rule": "adjacent-surname-repetition", "reason": reason})
        rules_skipped.append({"rule": "context-box-synthesis-duplication", "reason": reason})

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
