"""Partiju tests — U2 migrācija (vienreizējs, idempotents).

* `kodejums.json`: katrai par/pret šūnai bez `avots` ieliek `"avots": "cvk"`.
* `jautajumi.yaml`: katram jautājumam bez `quiz` ieliek `quiz: false`
  (teksta līmenī, lai saglabātu komentārus).

Lietošana:
    .venv/Scripts/python.exe scripts/partiju_tests_migrate_u2.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
K_PATH = REPO / "content" / "partiju-tests" / "kodejums.json"
Q_PATH = REPO / "content" / "partiju-tests" / "jautajumi.yaml"


def migrate_coding() -> int:
    coding = json.loads(K_PATH.read_text(encoding="utf-8"))
    n = 0
    for cells in coding.values():
        for cell in cells.values():
            if cell.get("nostaja") in ("par", "pret") and "avots" not in cell:
                cell["avots"] = "cvk"
                n += 1
    if n:
        K_PATH.write_text(json.dumps(coding, ensure_ascii=False, indent=1) + "\n",
                          encoding="utf-8")
    return n


def migrate_questions() -> int:
    lines = Q_PATH.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    n = 0
    entry: list[str] = []

    def flush():
        nonlocal n
        if entry and not any(l.lstrip().startswith("quiz:") for l in entry):
            for i, l in enumerate(entry):
                if l.startswith("  piekrit_nozime:"):
                    entry.insert(i + 1, "  quiz: false")
                    n += 1
                    break
        out.extend(entry)

    for line in lines:
        if line.startswith("- id:"):
            flush()
            entry = [line]
        elif entry:
            entry.append(line)
        else:
            out.append(line)
    flush()
    if n:
        Q_PATH.write_text("\n".join(out) + "\n", encoding="utf-8")
    return n


def main() -> int:
    n_cells = migrate_coding()
    n_quiz = migrate_questions()
    print(f"migrētas {n_cells} šūnas (avots: cvk), {n_quiz} jautājumi (quiz: false)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
