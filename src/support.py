"""`support` vārti: pozīcijas pamatojumam jābūt burtiski ŠĪ dokumenta tekstā.

2026-09-30 stance pret avotu mērījums (1 696 pozīcijas) parādīja, ka ekstraktors
regulāri raksta stance plašāku par avotu: nomet vilcinājumu, jautājumu pārvērš
apgalvojumā, ienes faktu no blakus dokumenta. Noteikumi pret to promptā jau
bija, bet lēmuma brīdī nedarbojās. Verifikatori, kuriem katram stance bija
jāpievieno burtisks avota fragments, deva 582 ticamus formulējumus — tāpēc
tas pats tiek prasīts ekstraktoram, un pārbaude ir kodā, ne tekstā.

`save_analysis()` izsauc `check_support()` katrai `position` pozīcijai un
neglabā to, ja fragmenta nav vai tas nav avota tekstā (`failures`).
"""

from __future__ import annotations

import re
import unicodedata

MIN_FRAGMENT_CHARS = 10


def norm(s: str) -> str:
    """Atstarpes un tipogrāfiskās pēdiņas nost — pieturzīmes PALIEK."""
    s = unicodedata.normalize("NFC", s)
    s = s.replace(" ", " ").replace("​", "")
    s = s.replace("„", '"').replace("“", '"').replace("”", '"')
    s = s.replace("«", '"').replace("»", '"').replace("’", "'")
    return re.sub(r"\s+", " ", s).strip()


def check_support(support, doc_text: str | None) -> tuple[str | None, str]:
    """Atgriež `(failure_type, detail)`; `(None, "")`, ja vārti iziet.

    `support` ir fragmentu saraksts (viena virkne arī tiek pieņemta). Katram
    fragmentam jābūt vismaz `MIN_FRAGMENT_CHARS` zīmes garam un nepārtrauktai
    `norm()` apakšvirknei dokumenta `title + content` tekstā.
    """
    if isinstance(support, str):
        support = [support]
    frags = [f for f in (support or []) if isinstance(f, str) and f.strip()]
    if not frags:
        return "missing_support", "claim has no support fragment"
    text = norm(doc_text or "")
    for f in frags:
        nf = norm(f)
        if len(nf) < MIN_FRAGMENT_CHARS:
            return "support_not_in_source", f"fragment shorter than {MIN_FRAGMENT_CHARS} chars: {f!r}"
        if nf not in text:
            return "support_not_in_source", f"fragment not in document text: {f[:120]!r}"
    return None, ""


# Atrunas vārdi («Šnores klase»: ekstraktors nomet «ja …» un raksta stance
# kategoriski). Atslēga = ziņotais vārds; «daļa» aptver visus «daļ-» locījumus
# un «daļēji», bet ne atvasinājumus kā «daļiņa».
QUALIFIERS: dict[str, re.Pattern] = {
    w: re.compile(p, re.IGNORECASE)
    for w, p in (
        ("ja", r"\bja\b"),
        ("varētu", r"\bvarētu\b"),
        ("iespējams", r"\biespējams\b"),
        ("šķiet", r"\bšķiet\b"),
        ("izskatās", r"\bizskatās\b"),
        ("daļa", r"\bdaļ(?:a|u|as|ai|ā|ām|ās|ēji)\b"),
        ("īsti", r"\bīsti\b"),
    )
}


def dropped_qualifiers(support, stance: str | None) -> list[str]:
    """Atrunas vārdi, kas ir `support` fragmentos, bet nav `stance` (tikai ziņošanai)."""
    if isinstance(support, str):
        support = [support]
    s_text = unicodedata.normalize("NFC", " ".join(f for f in (support or []) if isinstance(f, str)))
    st_text = unicodedata.normalize("NFC", stance or "")
    return [w for w, rx in QUALIFIERS.items() if rx.search(s_text) and not rx.search(st_text)]
