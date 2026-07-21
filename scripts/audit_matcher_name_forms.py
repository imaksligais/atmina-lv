"""Audit: unmatched deputy_name values in saeima_individual_votes.

Iet pār ``saeima_individual_votes.deputy_name`` DISTINCT vērtībām un izsauc
``match_politician(name)`` uz katras. Ja matcher atgriež ``None``, atrod top-3
tuvākos kandidātus no ``tracked_politicians`` pēc difflib ASCII-fold līdzības.

Mērķis: atklāt diakritikas-only un citas substring-only nesakritības, kuras
neredzami zaudē claims un balsojumus. Tipiskā nesakritība:

    Saeima padod  : 'Ilja Ivanovs'
    DB name_forms : ['Iļja Ivanovs', 'Ivanovs', ...]
    → match_politicians count=1 uz bare 'Ivanovs', bet shared-surname
      proximity check noraida, jo 'Ilja' nesakrīt ar pol_first_name='Iļja'.

Read-only — DB netiek modificēta. Output ir manuāli inspectējams, un fix
izpilda ``scripts/fix_matcher_name_forms.py`` (atsevišķs).

Lietošana:
    .venv/Scripts/python.exe scripts/audit_matcher_name_forms.py
"""
from __future__ import annotations

import difflib
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db import get_db
from src.matcher import _clear_politician_cache, match_politician


def ascii_fold(s: str) -> str:
    """Strip Latvian diacritics for similarity scoring. NOT used by matcher itself."""
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    ).lower()


def main() -> int:
    _clear_politician_cache()
    db = get_db("data/atmina.db")

    names = [
        r[0] for r in db.execute(
            "SELECT DISTINCT deputy_name FROM saeima_individual_votes "
            "WHERE deputy_name IS NOT NULL ORDER BY deputy_name"
        ).fetchall()
    ]
    politicians = db.execute(
        "SELECT id, name FROM tracked_politicians "
        "WHERE relationship_type != 'inactive' AND name IS NOT NULL"
    ).fetchall()
    folded_pols = {p["id"]: (p["name"], ascii_fold(p["name"])) for p in politicians}
    db.close()

    matched: list[tuple[str, int]] = []
    unmatched: list[tuple[str, list[tuple[int, str, float]]]] = []

    for name in names:
        pid = match_politician(name)
        if pid is None:
            folded_name = ascii_fold(name)
            scored = sorted(
                folded_pols.items(),
                key=lambda kv: difflib.SequenceMatcher(
                    None, folded_name, kv[1][1]
                ).ratio(),
                reverse=True,
            )[:3]
            cands = [
                (pid_, real_name, round(
                    difflib.SequenceMatcher(None, folded_name, folded).ratio(), 3
                ))
                for pid_, (real_name, folded) in scored
            ]
            unmatched.append((name, cands))
        else:
            matched.append((name, pid))

    total = len(names)
    match_rate = len(matched) / total if total else 0

    print("== Saeima deputy_name → tracked_politicians audit ==")
    print(f"Distinct deputy_name values   : {total}")
    print(f"Matched (match_politician ok) : {len(matched)} ({match_rate:.1%})")
    print(f"Unmatched                     : {len(unmatched)}")
    print()

    if not unmatched:
        print("Visas Saeimas deputātu vārdu formas atrod pid. Audit clean.")
        return 0

    print("=== Unmatched (top-3 candidates by ASCII-fold similarity) ===")
    print()
    diacritic_only = 0
    for name, candidates in unmatched:
        print(f"  '{name}'")
        for pid, real_name, score in candidates:
            marker = ""
            if score >= 0.98:
                marker = "  ⟵ diakritikas-only nesakritība (likely fix: add ASCII form)"
                if pid == candidates[0][0]:
                    diacritic_only += 1
            elif score >= 0.85:
                marker = "  ⟵ probable match, verify"
            print(f"      pid={pid:>3}  {real_name!r:<40} score={score}{marker}")
        print()

    print(f"Diakritikas-only nesakritības (auto-fix kandidāti): {diacritic_only}")
    print(
        "Manuāli inspectē listu un izpilda ``scripts/fix_matcher_name_forms.py`` "
        "ar piedāvāto patch list."
    )
    return 1 if unmatched else 0


if __name__ == "__main__":
    sys.exit(main())
