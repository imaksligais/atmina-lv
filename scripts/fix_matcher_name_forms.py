"""Fix: pievieno trūkstošās diakritikas-only formas tracked_politicians.

Skripts izpilda DB UPDATE 3 politiķiem, kuriem ``scripts/audit_matcher_name_forms.py``
2026-05-16 atklāja Saeima→DB substring nesakritības:

| pid | DB name                | Saeima padod           | Problēma                           |
|-----|------------------------|------------------------|------------------------------------|
| 7   | Edvīns Šnore           | Edvīns Šnore           | name_forms ir palatalizēti (Šņore) |
| 92  | Iļja Ivanovs           | Ilja Ivanovs           | nav ASCII bare form                |
| 111 | Nataļja Marčenko-Jodko | Natalja Marčenko-Jodko | nav ASCII bare form                |

Visi 3 ir additive — saglabā esošās formas, pievieno trūkstošās. Atbilst
[[feedback_matcher_no_diacritic_strip]] noteikumam: name_forms MUST include
both diacritic + ASCII variants.

Idempotents: re-running atkārtoti nepievieno duplicates.

Lietošana:
    .venv/Scripts/python.exe scripts/fix_matcher_name_forms.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db import get_db

PATCHES: dict[int, list[str]] = {
    # pid=7 Edvīns Šnore: forms had ['Šņore', 'Šņores', 'Šņorem'] — palatalized
    # Ņ instead of N, plus no full-name or correct bare surname. Saeima produces
    # 'Edvīns Šnore' (correct N). Add full name + correct N forms; keep
    # palatalized as fallback for any historical sources that wrote 'Šņore'.
    7: ["Edvīns Šnore", "Šnore"],
    # pid=92 Iļja Ivanovs: forms had ['Iļja Ivanovs', 'Ivanovs', 'Ivanovs, Iļja']
    # — only diacritic Ļ variant. Saeima produces 'Ilja Ivanovs'. Adding full
    # ASCII form makes count>=2 so shared-surname first-name proximity check
    # is bypassed (multi-word form is unique enough). 'Ilja' bare added so
    # first-name proximity also works for occurrences like "Ilja paziņoja".
    92: ["Ilja Ivanovs", "Ilja"],
    # pid=111 Nataļja Marčenko-Jodko: same pattern as pid=92.
    111: ["Natalja Marčenko-Jodko", "Natalja"],
}


def main() -> int:
    db = get_db("data/atmina.db")
    changes = 0
    for pid, additions in PATCHES.items():
        row = db.execute(
            "SELECT name, name_forms FROM tracked_politicians WHERE id = ?", (pid,)
        ).fetchone()
        if row is None:
            print(f"SKIP pid={pid}: nav DB rindas")
            continue
        current = json.loads(row["name_forms"]) if row["name_forms"] else []
        merged = list(current)
        added_now: list[str] = []
        for form in additions:
            if form not in merged:
                merged.append(form)
                added_now.append(form)
        if not added_now:
            print(f"OK   pid={pid:>3} {row['name']!r}: visi forms jau pievienoti")
            continue
        db.execute(
            "UPDATE tracked_politicians SET name_forms = ? WHERE id = ?",
            (json.dumps(merged, ensure_ascii=False), pid),
        )
        changes += 1
        print(
            f"FIX  pid={pid:>3} {row['name']!r}: +{added_now} "
            f"(total {len(current)}→{len(merged)})"
        )
    if changes:
        db.commit()
        print(f"\nCommitted {changes} UPDATE(s).")
    else:
        print("\nNothing to change.")
    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
