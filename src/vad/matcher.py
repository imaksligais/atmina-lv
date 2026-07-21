"""Name split + role-based disambiguation for VID search.

Spec: docs/superpowers/specs/2026-05-02-vad-deklaracijas-design.md § 6
"""

from __future__ import annotations

import unicodedata
from typing import Iterable

# Edge-case overrides for politicians where naive last-token-as-surname is wrong.
# Key = tracked_politicians.id; value = (given_name, surname).
# Phase 0 default: empty. Add entries when a sweep produces 0 results for a known
# active politiķis (e.g. Hosams Abu Meri — "Abu Meri" is the surname, not "Meri").
# Verify pid via:
#   sqlite3 data/atmina.db "SELECT id FROM tracked_politicians WHERE name='Hosams Abu Meri'"
_NAME_OVERRIDES: dict[int, tuple[str, str]] = {
    161: ("Hosams", "Abu Meri"),  # Veselības ministrs (Phase 1.5 — VID search bez override atgriež 0)
}


def split_name(pid: int, full_name: str) -> tuple[str, str]:
    """Split politician.name uz (given, family) tuple priekš VID search.

    Hyphenated uzvārdi tiek saglabāti monolīti (Zariņa-Stūre, Kalniņa-Lukaševica).
    Multi-token vārdi: pēdējais token ir uzvārds; pirmie N-1 ir vārds(i).
    Edge case overrides — manuāli kuratorisks _NAME_OVERRIDES dict.
    """
    if pid in _NAME_OVERRIDES:
        return _NAME_OVERRIDES[pid]
    parts = full_name.strip().split()
    if len(parts) < 2:
        raise ValueError(f"vārds bez uzvārda: {full_name!r}")
    return " ".join(parts[:-1]), parts[-1]


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
