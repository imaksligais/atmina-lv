"""Name split + role-based disambiguation for VID search.

Spec: docs/superpowers/specs/2026-05-02-vad-deklaracijas-design.md § 6
"""

from __future__ import annotations

import unicodedata
from typing import Iterable

# Vārda/uzvārda dalījums dzīvo `src.lv_text` (lapas modulis bez `src.vad`
# pakotnes — to lieto arī dienas pārskata skelets, 2026-10-14). Re-eksports
# saglabā šīs pakotnes un testu importus.
from src.lv_text import _NAME_OVERRIDES, split_name  # noqa: F401


def ascii_fallback(text: str) -> str:
    """Diakritiku-strip ASCII forma (Šlesers → Slesers).

    NFKD normalize + strip combining marks. Lietojam tikai pēc tam, kad search
    ar diakritikām atgrieza tukšu — defense-in-depth pret VID staff datu typing
    inkonsekvenci.
    """
    return "".join(
        c for c in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(c)
    )


def candidate_name_pairs(pid: int, full_name: str) -> Iterable[tuple[str, str]]:
    """Yield (given, family) candidate pairs to try in order.

    1. (given, family) ar diakritikām (vienmēr pirmais)
    2. (ASCII given, ASCII family) — fallback ja diakritika atgrieza tukšu
    """
    g, f = split_name(pid, full_name)
    yield g, f
    g_ascii = ascii_fallback(g)
    f_ascii = ascii_fallback(f)
    if (g_ascii, f_ascii) != (g, f):
        yield g_ascii, f_ascii


def role_matches(
    politician_role: str | None,
    vid_institution: str,
    vid_position: str,
) -> bool:
    """Always-True row acceptor (post-2026-05-02 production smoke decision).

    Sākotnējais nolūks: aizsargāt pret homonīmu (cita persona ar tādu pašu
    Vārds+Uzvārds) datu mix. Empīriski:

    - DB ir 5 homonīmu pāri (Šlesers Ainārs/Ričards, Judins Andrejs/Igors,
      Kļaviņa Jeļena/Līga, Kalniņa Inese/Irma, Zariņš Jānis/Viesturs) — visi
      ar dažādiem PIRMAJIEM vārdiem. VID search ar full Vārds+Uzvārds
      atgriež TIKAI vienu personu šajos gadījumos.
    - Production smoke (Šlesers, Pūpols, Kleinbergs) atklāja, ka
      role-keyword pārklāšanās dod false-negatives ar:
        * partijas amats DB ("LPV priekšsēdētājs") vs valdības amats VID
        * sinonīmu paši vārdi ("Rīgas mērs" DB vs "Valstspilsētas domes
          priekšsēdētājs" VID — tā pati amata loma, atšķirīgs label)
        * vēsturiskie amati (Pūpols EP deputāts šobrīd, bet VID glabā
          pirmsākumu Rīgas dome deklarācijas, kas atbilst tam pašam
          tracked politiķim)

    Risinājums: trust full Vārds+Uzvārds search uniqueness. Ja kādreiz
    novērojam, ka VID atgriež MULTIPLE distinct persons one search'ā
    (homonīms ar identisku first+last name) — re-introducē per-row check.
    Šobrīd return True vienmēr.

    Argument paliek šeit funkcijā, lai keep callers stable un dokumentē
    vēsturisko nodomu.
    """
    return True
