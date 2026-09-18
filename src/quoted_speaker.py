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
