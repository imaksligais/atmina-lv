"""Kolektīvo iesniegumu balsojumu polaritāte (leaf-modulis, tīra loģika).

Mandātu, ētikas un iesniegumu komisijas lēmumprojekts par kolektīvo iesniegumu
saka vienu no trim: «nodot» (komisijai / valdībai), «noraidīt» vai «atstāt bez
virzības». Saeima balso par KOMISIJAS PRIEKŠLIKUMU, ne par iesnieguma prasību.
Ja lēmumprojekts noraida, bet `summary` apraksta prasību, katra deputāta stance
apgriežas: «Iebilst pret: <prasība>» tiek uzrakstīts tam, kurš balsoja pret
noraidīšanu (2026-10-07: 12 balsojumi, divas publicētas pretrunas atsauktas;
wiki/CHANGELOG.md 2026-10-08 (6)).

Šeit: (1) darbības vārda nolasīšana no «Lēmumprojekta teksts» un (2) pārbaude,
vai `summary` nosauc balsojamo objektu. Ielādes vads un Step 5 vārti —
`src.saeima.votes`.
"""

from __future__ import annotations

import re
from typing import Optional

DECISION_REJECT = "noraidīt"
DECISION_FORWARD = "nodot"
DECISION_SHELVE = "atstāt bez virzības"
REJECTING_DECISIONS = frozenset({DECISION_REJECT, DECISION_SHELVE})

# Lēmuma balsojums: «Par 11 391 Latvijas pilsoņa kolektīvā iesnieguma "…"
# turpmāko virzību (936/Lm14)». Procedurālie apakšbalsojumi ar to pašu numuru
# («Par iekļaušanu nākamās sēdes darba kārtībā. Par …», «Par nodošanu Ārlietu
# komisijai. Par …», «Par lēmuma projekta "Par …" iekļaušanu…») balso par CITU
# priekšlikumu — tie sākas ar vārdu, ne ar parakstītāju skaitu, un te neskaitās.
_DECISION_MOTIF = re.compile(r"^Par \d")
_LM_NR = re.compile(r"\(\d+/Lm\d+\)")

_QUOTED = re.compile(r"“[^”]*”|„[^”“]*[”“]|\"[^\"]*\"|«[^»]*»")
_ENUM = re.compile(r"^\s*:?\s*(?:\d+\)\s*)?")
_VERB = re.compile(r"\b(noraidīt|nodot|atstāt)\b")
_VERB_NORMAL = {"noraidīt": DECISION_REJECT, "nodot": DECISION_FORWARD,
                "atstāt": DECISION_SHELVE}

_OBJECT_PREFIX = "Komisijas priekšlikums "
# Iznākuma/noraidījuma formulējums prasības stila summary, ja lēmumprojekts
# ir «nodot» (973/Lm14: «… turpmākā virzība noraidīta» → Par balsotājs saņēma
# «Atbalsta: … virzība noraidīta»).
_REJECTION_WORDING = re.compile(
    r"noraidī|bez (?:turpmākas|tālākas) (?:virzības|izskatīšanas)", re.IGNORECASE)


def is_petition_decision_vote(motif: Optional[str]) -> bool:
    """Vai balsojums ir par komisijas lēmumprojektu kolektīvā iesnieguma lietā."""
    m = motif or ""
    low = m.casefold()
    return bool(_DECISION_MOTIF.match(m) and _LM_NR.search(m)
                and "kolektīv" in low and "iesniegum" in low)


def petition_decision_verb(draft_text: Optional[str]) -> Optional[str]:
    """«Lēmumprojekta teksts» → 'noraidīt' | 'nodot' | 'atstāt bez virzības' | None.

    Lasa tekstu pēc «nolemj». Pēdiņās liktais iesnieguma virsraksts tiek
    izmests pirms meklēšanas (virsraksts var saturēt «Noraidīt …»), un darbības
    vārds var stāvēt arī PĒC objekta (190/Lm14: «… iesniegumu "…" atstāt bez
    tālākas izskatīšanas»). Ja «nolemj» nav vai neviens no trim vārdiem netiek
    atrasts — None: tad lēmumprojekts jānolasa cilvēkam, nevis jāmin.
    """
    if not draft_text:
        return None
    text = re.sub(r"\s+", " ", draft_text)
    i = text.casefold().find("nolemj")
    if i < 0:
        return None
    window = text[i + len("nolemj"):]
    cut = window.find("Oriģinālais dokumenta saturs")
    if cut >= 0:
        window = window[:cut]
    window = _ENUM.sub("", _QUOTED.sub(" ", window)).casefold()
    m = _VERB.search(window)
    return _VERB_NORMAL[m.group(1)] if m else None


def petition_polarity_problem(summary: Optional[str], decision: Optional[str]) -> Optional[str]:
    """Kāpēc šis summary apgrieztu stance; None, ja kārtībā.

    - 'decision_missing'  — lēmumprojekta darbības vārds nav nolasīts;
    - 'object_unnamed'    — lēmumprojekts noraida / atstāj bez virzības, bet
                            summary nesākas ar «Komisijas priekšlikums noraidīt|atstāt»;
    - 'verb_mismatch'     — summary nosauc citu darbības vārdu nekā lēmumprojekts;
    - 'rejection_wording' — lēmumprojekts «nodot», bet prasības stila summary
                            runā par noraidīšanu.
    """
    if decision is None:
        return "decision_missing"
    s = (summary or "").strip()
    named = s.startswith(_OBJECT_PREFIX)
    named_verb = s[len(_OBJECT_PREFIX):].split(" ", 1)[0] if named else None
    if decision in REJECTING_DECISIONS:
        if not named:
            return "object_unnamed"
        if named_verb != decision.split(" ", 1)[0]:
            return "verb_mismatch"
        return None
    if named:
        return None if named_verb == DECISION_FORWARD else "verb_mismatch"
    if _REJECTION_WORDING.search(s):
        return "rejection_wording"
    return None
