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
from src.matcher import _occurrences

_FOLD = str.maketrans("āčēģīķļņšūžĀČĒĢĪĶĻŅŠŪŽ", "acegiklnsuzACEGIKLNSUZ")

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
    return text.translate(_FOLD).lower()


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


def find_inversions(db, days: int = 90) -> dict[str, Any]:
    """Scan recent web documents for the inversion.

    Returns ``{"checked": N, "inversions": [...]}``. The denominator is part of
    the return value on purpose: a caller cannot report findings without also
    reporting how many documents were examined (CLAUDE.md — a gate that cannot
    fire is not evidence, and three checks in this repo have already shipped a
    confident all-clear while structurally unable to fail).

    Candidate set: `platform='web'` documents from the last `days` days that
    carry at least one non-inactive `subject` AND at least one non-inactive,
    non-organization `mentioned` politician. An institution named in a citation
    line is not a lost human speaker, so organizations are excluded from the
    `mentioned` side.
    """
    cutoff = lv_cutoff(days)

    candidates = db.execute(
        """
        SELECT d.id, d.content, d.source_url
        FROM documents d
        WHERE d.platform = 'web'
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
        (cutoff,),
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
                "source_url": doc["source_url"],
                "subject_ids": sorted(subject_ids),
                "speaking_mentioned": sorted(speaking_mentioned),
                "subject_names": [names.get(p, "") for p in sorted(subject_ids)],
                "speaker_names": [names.get(p, "") for p in sorted(speaking_mentioned)],
            })

    return {"checked": len(candidates), "inversions": inversions}


def pending_quoted_mentioned(
    db, days: int = 1, pid: int | None = None
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

    Katrs ieraksts: {document_id, politician_id}.
    """
    result = find_inversions(db, days=days)
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
                })
    return pairs
