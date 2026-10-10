"""Citētā runātāja detektors — koplietots starp auditu un ekstrakcijas rindu.

Pārcelts no ``scripts/audit_junction_role_inversion.py`` 2026-08-04 (junction
inversijas plāna 4. solis), lai rindas vaicājums un audits lieto VIENU UN TO
PAŠU nominatīva-pie-citāta loģiku — divas kopijas te nozīmētu, ka audits mēra
citu klasi nekā rinda apstrādā. Audita skripts importē no šejienes; bāzlīnijas
vārti (checked/flagged identisks pirms/pēc refaktora) dzīvo plāna § Vārti.

KĀPĒC TIKAI NOMINATĪVS. Diskriminators ir gramatisks: latviešu ziņās "X teica"
runātājs stāv nominatīvā; slīpā forma pie tā paša verba ("par Xu teica")
marķē personu kā tematu, ne runātāju. Naivā visu-formu versija NEuzrāda
doc 78085 — gadījumu, kas šo klasi atvēra.
"""

from __future__ import annotations

import json
import re
from typing import Any

from src.db import lv_cutoff
from src.lv_text import LV_TRANS, fold_lower
from src.matcher import _occurrences

# Vēsturiskais privātais nosaukums; vienīgā definīcija `src/lv_text.py`
# (2026-09-05, plāna 4.3). Te bija 22-zīmju tabula BEZ ``ō``/``ŗ`` — vienīgā
# apzinātā uzvedības maiņa visā 4.3: tagad arī tās loka. Mērījums pirms
# apvienošanas: 0 atšķirību pār 922 reālām rindām (225 `tracked_politicians`
# vārdi + 697 `name_forms`), jo mūsdienu ortogrāfijā šo zīmju nav. Vārti:
# tests/test_lv_text.py::TestDivergentTablesWereSafeToMerge.
_FOLD = LV_TRANS

# Citātu signāli. Latviešu ziņas runu attiecina ar ziņošanas verbu, aģentūras
# birku vai norises vietu. Sastopama gan pagātne, gan tagadne; katrs signāls
# skaitās tikai VĀRDA SĀKUMĀ (kreisā robeža), bet galotnes drīkst turpināties
# ("pauž"→"paužot", "skaidro"→"skaidrots" — likumīga morfoloģija). Bez kreisās
# robežas "raksta" trāpīja iekš "saraksta" un vēlēšanu sezonas sarakstu raksti
# šo klasi ražoja sistemātiski (14 % FP, doc 80038; BACKLOG #30, 2026-08-04).
CITATION_SIGNALS: frozenset[str] = frozenset({
    "teica", "saka", "sacīja", "norādīja", "norāda", "uzsvēra", "uzsver",
    "pauda", "pauž", "atzina", "atzīst", "apliecināja", "apgalvoja", "apgalvo",
    "skaidroja", "skaidro", "stāstīja", "stāsta", "piebilda", "piebilst",
    "uzskata", "aicināja", "aicina", "brīdināja", "brīdina", "atgādināja",
    "vērtēja", "vērtē", "solīja", "sola", "informēja", "ziņoja", "rakstīja",
    "raksta", "atbildēja", "atbild", "jautāts", "jautāta", "akcentēja",
    "minēja", "izteicās", "papildināja", "secināja", "secina", "komentējot",
    "komentēja", "aģentūrai leta", "intervijā", "raidījumā", "ierakstā",
    "preses konferencē", "sarunā ar", "portālam", "laikrakstam",
})

# Signāla sākumam jābūt vārda sākumā ((?<!\w) — pirms tā nav burta/cipara);
# meklēts pa VISU nolaisto tekstu, ne izgrieztu logu, jo loga robeža var
# pārcirst vārdu un radīt viltus vārda sākumu ("laik|rakstam" → "rakstam").
_SIGNAL_RE = re.compile(
    r"(?<!\w)(?:"
    + "|".join(sorted(map(re.escape, CITATION_SIGNALS), key=len, reverse=True))
    + r")"
)

CITATION_WINDOW = 60


def _fold(text: str) -> str:
    return fold_lower(text)


def nominative_forms(name: str, forms: list[str]) -> list[str]:
    """Subset of `forms` whose surname token is in the NOMINATIVE.

    A form qualifies when its last token, diacritic-folded and lowercased,
    equals the politician's surname folded the same way. That keeps the full
    name, the bare surname and their ASCII variants (sources strip diacritics)
    while dropping every generated oblique inflection — genitive `Jurēvica`,
    dative `Jurēvicam`, accusative `Jurēviču`.

    `name` itself and its bare surname are always included, so a politician
    with an empty `name_forms` still resolves.
    """
    tokens = (name or "").split()
    if not tokens:
        return []
    surname_key = _fold(tokens[-1])

    out: list[str] = []
    seen: set[str] = set()
    for candidate in [name, tokens[-1], *(forms or [])]:
        if not candidate or candidate in seen:
            continue
        cand_tokens = candidate.split()
        if not cand_tokens:
            continue
        if _fold(cand_tokens[-1]) == surname_key:
            seen.add(candidate)
            out.append(candidate)
    return out


def speaks(text: str, forms: list[str], window: int = CITATION_WINDOW) -> bool:
    """True when a nominative form sits within `window` chars of a citation signal.

    `forms` must already be nominative-filtered — this function does not fold
    cases itself, because the whole point of the check is that an oblique form
    is NOT evidence of speech.
    """
    if not text or not forms:
        return False
    signal_starts = [m.start() for m in _SIGNAL_RE.finditer(text.lower())]
    if not signal_starts:
        return False
    for form in forms:
        for idx in _occurrences(text, form):
            lo = max(0, idx - window)
            hi = idx + len(form) + window
            if any(lo <= s < hi for s in signal_starts):
                return True
    return False


# Platformas, kur citēts runātājs ir sagaidāms. Līdz 2026-08-27 josla bija
# `platform='web'` ONLY, un tas maksāja veselu dienu: 2026-08-26 vakarā LTV1
# priekšvēlēšanu līderu debates pārstāstīja RELEJA TVĪTI ar skaidru atribūciju
# («Juris Pūce (LA) aicina palielināt iemaksas 2. pensiju līmenī»), un astoņi
# doki (95235, 95236, 95238, 95241, 95243, 95245, 95246, 95247) palika ar
# `role='mentioned'`, `reviewed_at IS NULL` un 0 claims. Trīs neatkarīgi vārti
# to nenoķēra, jo diviem bija VIENA aklā zona: `get_pending_politicians()`
# staigā pa `subject`, šī funkcija filtrēja `web`, un orkestratora apsekojuma
# vaicājums tajā dienā atkārtoja to pašu `platform='web'` filtru. Divi vārti ar
# vienu aklo zonu nav divi vārti.
DEFAULT_INVERSION_PLATFORMS: tuple[str, ...] = ("web", "twitter", "x_mention")


def find_inversions(
    db, days: int = 90, platforms: tuple[str, ...] | None = None
) -> dict[str, Any]:
    """Scan recent documents for the inversion.

    Returns ``{"checked": N, "inversions": [...]}``. The denominator is part of
    the return value on purpose: a caller cannot report findings without also
    reporting how many documents were examined (CLAUDE.md — a gate that cannot
    fire is not evidence, and three checks in this repo have already shipped a
    confident all-clear while structurally unable to fail).

    Candidate set: documents on `platforms` (default
    ``DEFAULT_INVERSION_PLATFORMS``) from the last `days` days that carry at
    least one non-inactive `subject` AND at least one non-inactive,
    non-organization `mentioned` politician. An institution named in a citation
    line is not a lost human speaker, so organizations are excluded from the
    `mentioned` side.

    **Mērogs un ražas kvalitāte, pirms tu šo lasi kā tīru ieguvumu (mērīts
    2026-08-27 uz dzīvās DB).** `days=7`: `web` vien deva `checked=74`,
    13 inversijas; ar tvītiem `checked=283`, 22 inversijas — t.i. ~+1,3 pāri
    dienā, tajā pašā kārtā kā web joslas mērītais ~1,4/dienā. Bet deviņu jauno
    tvītu triāža deva aptuveni **pusi viltus pozitīvu, un tos dominē SATĪRA**:
    doc 92493 nes izdomātu «citātu» Siliņai, doc 94448/94372 izdomātu Ašeradenam,
    93641/93181 Lapsas asprātības. Strukturāla filtra tam NAV — Stendzenieks ir
    `relationship_type='tracked'` (īsts Rīgas domes deputāts, kas tur satīras
    kontu), tāpēc SQL šo nešķir. Josla ir RINDA, ne glabātuve: šķirotājs ir
    `@claim-extractor` satīras/RT vārti, un tieši tur tas jāpalicina. Nekad
    neuzskati šīs joslas pāri par apstiprinātu pozīciju.
    """
    cutoff = lv_cutoff(days)
    platforms = tuple(platforms) if platforms else DEFAULT_INVERSION_PLATFORMS
    placeholders = ",".join("?" for _ in platforms)

    candidates = db.execute(
        f"""
        SELECT d.id, d.content, d.source_url, d.platform
        FROM documents d
        WHERE d.platform IN ({placeholders})
          AND d.content IS NOT NULL
          AND d.scraped_at >= ?
          AND EXISTS (
              SELECT 1 FROM document_politicians dp
              JOIN tracked_politicians tp ON tp.id = dp.politician_id
              WHERE dp.document_id = d.id AND dp.role = 'subject'
                AND tp.relationship_type != 'inactive')
          AND EXISTS (
              SELECT 1 FROM document_politicians dp
              JOIN tracked_politicians tp ON tp.id = dp.politician_id
              WHERE dp.document_id = d.id AND dp.role = 'mentioned'
                AND tp.relationship_type NOT IN ('inactive', 'organization'))
        ORDER BY d.id DESC
        """,
        (*platforms, cutoff),
    ).fetchall()

    inversions: list[dict[str, Any]] = []
    for doc in candidates:
        links = db.execute(
            """SELECT dp.role, tp.id, tp.name, tp.name_forms, tp.relationship_type
               FROM document_politicians dp
               JOIN tracked_politicians tp ON tp.id = dp.politician_id
               WHERE dp.document_id = ? AND dp.role IN ('subject', 'mentioned')
                 AND tp.relationship_type != 'inactive'""",
            (doc["id"],),
        ).fetchall()

        content = doc["content"] or ""
        subject_ids: list[int] = []
        speaking_subjects: list[int] = []
        speaking_mentioned: list[int] = []

        for row in links:
            try:
                forms = json.loads(row["name_forms"]) if row["name_forms"] else []
            except (TypeError, ValueError):
                forms = []
            nom = nominative_forms(row["name"], forms)

            if row["role"] == "subject":
                subject_ids.append(row["id"])
                if speaks(content, nom):
                    speaking_subjects.append(row["id"])
            elif row["relationship_type"] != "organization" and speaks(content, nom):
                speaking_mentioned.append(row["id"])

        if speaking_mentioned and not speaking_subjects:
            names = {r["id"]: r["name"] for r in links}
            inversions.append({
                "document_id": doc["id"],
                # Platforma ir daļa no atraduma, ne kosmētika: tvītu joslā satīra
                # dominē viltus pozitīvos (sk. docstring), tāpēc triāžētājam
                # jāredz, no kuras joslas pāris nāk, pirms viņš to lasa.
                "platform": doc["platform"],
                "source_url": doc["source_url"],
                "subject_ids": sorted(subject_ids),
                "speaking_mentioned": sorted(speaking_mentioned),
                "subject_names": [names.get(p, "") for p in sorted(subject_ids)],
                "speaker_names": [names.get(p, "") for p in sorted(speaking_mentioned)],
            })

    return {"checked": len(candidates), "inversions": inversions}


def pending_quoted_mentioned(
    db, days: int = 1, pid: int | None = None,
    platforms: tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    """(dokuments, politiķis) pāri ekstrakcijas rindas OTRAJAI joslai.

    Atgriež inversijas klases pārus — citēts `mentioned` runātājs dokā bez
    neviena runājoša `subject` —, kuriem attiecīgā junction rinda vēl NAV
    apstrādāta (``dp.extracted_at IS NULL``). `documents.reviewed_at` šeit
    APZINĀTI netiek skatīts: tieši reviewed_at dokumenta-līmeņa semantika šo
    klasi maskēja (subject apstrāde noņem doku no rindas, pirms mentioned
    runātājs to jebkad redz).

    Semantika = ``find_inversions`` (tas pats kandidātu filtrs, tā pati
    inversijas prasība) — apstiprinātais apjoms (~1,4 vienības dienā) ir
    mērīts tieši šai klasei, un plašāka "jebkurš citēts mentioned" josla
    būtu cits, lielāks lēmums.

    Katrs ieraksts: {document_id, politician_id, platform}.
    """
    result = find_inversions(db, days=days, platforms=platforms)
    pairs: list[dict[str, Any]] = []
    for inv in result["inversions"]:
        for spk in inv["speaking_mentioned"]:
            if pid is not None and spk != pid:
                continue
            row = db.execute(
                """SELECT 1 FROM document_politicians
                   WHERE document_id = ? AND politician_id = ?
                     AND role = 'mentioned' AND extracted_at IS NULL
                   LIMIT 1""",
                (inv["document_id"], spk),
            ).fetchone()
            if row:
                pairs.append({
                    "document_id": inv["document_id"],
                    "politician_id": spk,
                    "platform": inv["platform"],
                })
    return pairs


# Tikai atgūšanas apsekojumam: sēdes/komisijas pārskatos deputāts bieži
# «jautāja», «prasīja» vai «sprieda», un 2026-09-23 vakarā šie verbi (plus
# divdabis «norādot») palaida garām Šuvajevu (114870), Sprūdu un Dineviču
# (114881). `CITATION_SIGNALS` un `find_inversions` apzināti NEmainās — audita
# bāzlīnija paliek tā pati (kontroliera lēmums 2026-09-24).
RECOVERY_EXTRA_SIGNALS: frozenset[str] = frozenset({
    "jautāja", "jautā", "prasīja", "prasa", "sprieda", "norādot",
})

# Signāli skaitās vārda SĀKUMĀ un drīkst turpināties (sk. `_SIGNAL_RE`), bet
# divi papildu celmi tad aprij lietvārdus/divdabjus: «jautā» → «jautājums/
# jautājumu/jautājumā» (dzīvajā DB 7 no 11 Kulberga «signāliem» doc 114082 un
# viss Bražes pāris tur bija šis lietvārds, 2026-09-24 pārrecenzija), «prasa» →
# «prasamais». Negatīvā priekšskatīšanās atstāj darbības vārdu, noraida šos.
_RECOVERY_SIGNAL_OVERRIDES: dict[str, str] = {
    "jautā": r"jautā(?!jum)",
    "prasa": r"prasa(?!m)",
}

_RECOVERY_SIGNAL_RE = re.compile(
    r"(?<!\w)(?:"
    + "|".join(
        _RECOVERY_SIGNAL_OVERRIDES.get(sig, re.escape(sig))
        for sig in sorted(CITATION_SIGNALS | RECOVERY_EXTRA_SIGNALS,
                          key=len, reverse=True))
    + r")"
)


def count_speech_signals(
    text: str, forms: list[str], window: int = CITATION_WINDOW,
    signal_re: re.Pattern[str] = _SIGNAL_RE,
) -> int:
    """Number of distinct `_SIGNAL_RE` hits within `window` chars of a form.

    Same geometry as :func:`speaks` (which stays a short-circuiting bool for
    the audit baseline); this variant counts, so a survey row can say how much
    speech evidence it rests on. `forms` must already be nominative-filtered.
    `signal_re` defaults to the audit's `_SIGNAL_RE`; `recovery_survey` passes
    `_RECOVERY_SIGNAL_RE` (+ `RECOVERY_EXTRA_SIGNALS`).
    """
    if not text or not forms:
        return 0
    signal_starts = [m.start() for m in signal_re.finditer(text.lower())]
    if not signal_starts:
        return 0
    hits: set[int] = set()
    for form in forms:
        for idx in _occurrences(text, form):
            lo = max(0, idx - window)
            hi = idx + len(form) + window
            hits.update(s for s in signal_starts if lo <= s < hi)
    return len(hits)


def _nominative_from_row(name: str, name_forms_raw: str | None) -> list[str]:
    try:
        forms = json.loads(name_forms_raw) if name_forms_raw else []
    except (TypeError, ValueError):
        forms = []
    return nominative_forms(name, forms)


# Pēc junction-atgūšanas apsekojuma izslēgtie `relationship_type`. Žurnālisti
# ir releja kanāli (CLAUDE.md inv #11, operatora lēmums 2026-08-21), iestādes
# citātu rindā nav zaudēts cilvēks-runātājs. `twitter`/`x_mention` platformas
# PALIEK — satīras brīdinājums dzīvo prasmē, ne SQL (sk. find_inversions).
_SURVEY_EXCLUDED_REL: tuple[str, ...] = ("inactive", "journalist", "organization")


def recovery_survey(db, days: int = 1) -> dict[str, Any]:
    """Junction-atgūšanas apsekojums: citētie `mentioned` runātāji, ko neviens
    ekstrakcijas slots nav apstrādājis (``extracted_at IS NULL``).

    KĀPĒC. ``get_pending_politicians`` staigā pa `subject`, un
    ``documents.reviewed_at`` ir per-DOKUMENTA — subjekta apstrāde noņem doku
    no rindas visiem. ``pending_quoted_mentioned`` (inversijas josla) redz
    tikai dokus, kur subjekts KLUSĒ; 2026-09-23 vakarā tas deva 0 pārus, kamēr
    rokas vaicājums atrada 31 web `mentioned` pāri (18 ar runas signālu) un
    atgūšana saglabāja 9 pozīcijas no 11 pāriem — visi dokos, kur runāja arī
    subjekts. Šī funkcija ir tas rokas vaicājums kodā.

    Joslas (savstarpēji nepārklājas):

    * ``inversion`` — tieši ``pending_quoted_mentioned(db, days)``.
    * ``beside_subject`` — `role='mentioned'`, ``extracted_at IS NULL``,
      politiķis nav ``_SURVEY_EXCLUDED_REL``, dokā ≥1 ne-inactive `subject`,
      ``scraped_at`` logā, runas signāls ≥1. **Platformu nefiltrē** — divi vārti
      ar vienu aklo zonu nav divi vārti (2026-08-26). Inversijas pāri te
      neatkārtojas.
    * ``blind_no_subject`` — doki ar tādu pašu neapstrādātu `mentioned` pāri,
      bet bez neviena aktīva subjekta; tikai skaitlis (doku), ne rinda.

    Runas signāls = ``CITATION_SIGNALS | RECOVERY_EXTRA_SIGNALS`` trāpījums ±``CITATION_WINDOW`` zīmēs ap
    politiķa NOMINATĪVA formu no ``tracked_politicians.name_forms`` (matcher
    dati caur :func:`nominative_forms` — slīpā forma pie verba ir temats, ne
    runātājs; paša stemmers te apzināti netiek rakstīts, CLAUDE.md T18).

    ``checked`` = (doks, mentioned) pāri TIKAI dokos, kuros IR aktīvs
    subjekts (∪ inversijas pāri) — arī tie ar 0 signāliem, kas netiek
    atgriezti. Aklās zonas doku pāri šeit NEieskaitās; tie ir atsevišķi
    ``blind_no_subject.docs``. Saucējs 0 pie netukšas dienas = salauzts vārts.

    Zināmās robežas: inversijas josla manto ``find_inversions`` izslēgumus
    (tā neizslēdz `journalist`); formas ir tikai ``name_forms`` — politiķis,
    kas tvītā piesaistīts tikai ar @handle, signālu nedod.

    Josla ir RINDA, ne glabātuve: katrs pāris iet caur `@claim-extractor`
    (satīras/RT vārti), nekad netiek uzskatīts par apstiprinātu pozīciju.
    """
    cutoff = lv_cutoff(days)
    excl = ",".join("?" for _ in _SURVEY_EXCLUDED_REL)
    rows = db.execute(
        f"""
        SELECT dp.document_id, dp.politician_id, tp.name, tp.name_forms,
               d.platform, d.content,
               EXISTS (
                   SELECT 1 FROM document_politicians s
                   JOIN tracked_politicians st ON st.id = s.politician_id
                   WHERE s.document_id = d.id AND s.role = 'subject'
                     AND COALESCE(st.relationship_type, '') != 'inactive'
               ) AS has_subject
        FROM document_politicians dp
        JOIN tracked_politicians tp ON tp.id = dp.politician_id
        JOIN documents d ON d.id = dp.document_id
        WHERE dp.role = 'mentioned'
          AND dp.extracted_at IS NULL
          AND COALESCE(tp.relationship_type, '') NOT IN ({excl})
          AND d.content IS NOT NULL
          AND d.scraped_at >= ?
        ORDER BY dp.document_id DESC, dp.politician_id
        """,
        (*_SURVEY_EXCLUDED_REL, cutoff),
    ).fetchall()

    def _pair(doc_id, pid, name, platform, content, forms_raw) -> dict[str, Any]:
        return {
            "document_id": doc_id,
            "politician_id": pid,
            "name": name,
            "platform": platform,
            "signals": count_speech_signals(content or "",
                                            _nominative_from_row(name, forms_raw),
                                            signal_re=_RECOVERY_SIGNAL_RE),
        }

    inversion: list[dict[str, Any]] = []
    for p in pending_quoted_mentioned(db, days=days):
        r = db.execute(
            """SELECT tp.name, tp.name_forms, d.content FROM tracked_politicians tp,
                      documents d WHERE tp.id = ? AND d.id = ?""",
            (p["politician_id"], p["document_id"]),
        ).fetchone()
        inversion.append(_pair(p["document_id"], p["politician_id"], r["name"],
                               p["platform"], r["content"], r["name_forms"]))
    inversion_keys = {(p["document_id"], p["politician_id"]) for p in inversion}

    checked_keys = set(inversion_keys)
    beside: list[dict[str, Any]] = []
    blind_docs: set[int] = set()
    for r in rows:
        key = (r["document_id"], r["politician_id"])
        if not r["has_subject"]:
            blind_docs.add(r["document_id"])
            continue
        checked_keys.add(key)
        if key in inversion_keys:
            continue
        pair = _pair(r["document_id"], r["politician_id"], r["name"],
                     r["platform"], r["content"], r["name_forms"])
        if pair["signals"] > 0:
            beside.append(pair)

    by_platform: dict[str, dict[str, int]] = {
        p: {"inversion": 0, "beside_subject": 0} for p in DEFAULT_INVERSION_PLATFORMS
    }
    for band, pairs in (("inversion", inversion), ("beside_subject", beside)):
        for p in pairs:
            by_platform.setdefault(p["platform"], {"inversion": 0, "beside_subject": 0})
            by_platform[p["platform"]][band] += 1

    return {
        "checked": len(checked_keys),
        "bands": {
            "inversion": inversion,
            "beside_subject": beside,
            "blind_no_subject": {"docs": len(blind_docs)},
        },
        "by_platform": by_platform,
    }


def format_recovery_line(survey: dict[str, Any]) -> str:
    """«ATGŪŠANA: X pāri (web a / twitter b / x_mention c), aklā zona N doku».

    Platformas ārpus ``DEFAULT_INVERSION_PLATFORMS`` pievienojas iekavās, ja
    tām ir pāri — neviens pāris nedrīkst pazust no summas.
    """
    bp = survey.get("by_platform", {})
    order = list(DEFAULT_INVERSION_PLATFORMS) + sorted(
        p for p in bp if p not in DEFAULT_INVERSION_PLATFORMS)
    parts = []
    for p in order:
        n = sum(bp.get(p, {}).values())
        if p in DEFAULT_INVERSION_PLATFORMS or n:
            parts.append(f"{p} {n}")
    bands = survey["bands"]
    total = len(bands["inversion"]) + len(bands["beside_subject"])
    blind = bands["blind_no_subject"]["docs"]
    return (f"ATGŪŠANA: {total} {lv_pairs(total)} ({' / '.join(parts)}), "
            f"aklā zona {blind} {_lv_plural(blind, 'doks', 'doku')}")


def _lv_plural(n: int, singular: str, plural: str) -> str:
    # Tas pats noteikums kā `src/render/_common/filters.py::_lv_plural`;
    # importēt no render slāņa nozīmētu vilkt bleach/markdown rutīnas statusā.
    return singular if (n % 10 == 1 and n % 100 != 11) else plural


def lv_pairs(n: int) -> str:
    """«pāris» / «pāri» pēc skaitļa (1, 21, 141 → vsk.; 11 → dsk.)."""
    return _lv_plural(n, "pāris", "pāri")
