"""Partiju tests — godīguma audits (tikai LASA).

Plāna § 2 diagnoze kā atkārtojams ziņojums (`docs/plans/2026-09-14-partiju-tests-v1-godigums.md`):

* katram jautājumam: nolasāmas šūnas (par+pret), mazākuma grupa, verdikts pret
  quiz vārtu § 3.3 (nolasāmas ≥ 8 UN mazākums ≥ 3);
* „piekrītu visam” un „nepiekrītu visam” rangs ar § 3.4 `score()` — rāda, kuri
  saraksti krīt zem `M ≥ ⌈A/2⌉` (rangs tad būtu pēc saucēja, ne satura);
* `par`:`pret` šūnu kopskaits visos jautājumos (virziena bilance § 3.3).

Ziņojums, ne vārts — exit kods vienmēr 0. Saucējs katrā tabulā.

Lietošana:
    .venv/Scripts/python.exe scripts/partiju_tests_audit.py
        [--questions content/partiju-tests/jautajumi.yaml]
        [--coding content/partiju-tests/kodejums.json]
        [--saraksti content/partiju-tests/saraksti.yaml]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.partiju_tests_validate import load_saraksti, question_gate  # noqa: E402
from scripts.partiju_tests_validate import QUIZ_MIN_READABLE, QUIZ_MIN_MINORITY  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
MIN_ANSWERED = 4        # § 3.4.3: < 4 atbildētiem rezultāta nav


def score(answers: dict[str, str | None], coding: dict, saraksti: list[dict]) -> list[tuple[str, int, int, int]]:
    """§ 3.4: atgriež rangā esošos sarakstus (short_name, N, M, K), N/M dilstoši,
    vienādas daļas iekšienē `saraksti` secībā. Rangā tikai M ≥ ⌈A/2⌉; lasītājam
    ar < MIN_ANSWERED atbildēm rezultāta nav (tukšs saraksts)."""
    answered = {qid: a for qid, a in answers.items() if a in ("par", "pret")}
    a = len(answered)
    if a < MIN_ANSWERED:
        return []
    out = []
    for s in saraksti:
        p = s["short_name"]
        n = m = k = 0
        for qid, ans in answered.items():
            cell = coding.get(qid, {}).get(p)
            if cell is None or cell["nostaja"] == "klusē":
                continue
            m += 1
            if cell.get("avots", "cvk") == "cvk":
                k += 1
            if cell["nostaja"] == ans:
                n += 1
        out.append((p, n, m, k))
    order = {s["short_name"]: i for i, s in enumerate(saraksti)}
    out.sort(key=lambda r: (-(r[1] / r[2]) if r[2] else 0.0, order[r[0]]))
    threshold = math.ceil(a / 2)
    return [r for r in out if r[2] >= threshold]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", default=str(REPO / "content" / "partiju-tests" / "jautajumi.yaml"))
    ap.add_argument("--coding", default=str(REPO / "content" / "partiju-tests" / "kodejums.json"))
    ap.add_argument("--saraksti", default=str(REPO / "content" / "partiju-tests" / "saraksti.yaml"))
    a = ap.parse_args(argv)
    questions = yaml.safe_load(Path(a.questions).read_text(encoding="utf-8"))
    coding = json.loads(Path(a.coding).read_text(encoding="utf-8"))
    saraksti = load_saraksti(a.saraksti)

    print(f"Audits: {len(questions)} jautājumi × {len(saraksti)} saraksti")
    print()

    rows = question_gate(questions, coding, saraksti)
    n_fail = sum(1 for r in rows if not r["ok"])
    print(f"Quiz vārts (nolasāmas ≥ {QUIZ_MIN_READABLE}, mazākums ≥ {QUIZ_MIN_MINORITY}) — {len(rows)} jautājumi:")
    for r in rows:
        verdict = "ok" if r["ok"] else "FAIL"
        print(f"  {r['id']}  piekrīt {r['par']:2d}  iebilst {r['pret']:2d}  "
              f"nolasāmas {r['readable']:2d}/{len(saraksti)}  mazākums {r['minority']:2d}  {verdict}")
    print(f"  → {n_fail} no {len(rows)} jautājumiem vārtu neiziet (FAIL)")
    old = question_gate(questions, coding, saraksti, min_readable=6, min_minority=2)
    print(f"  (09-10 kritērijs ≥6/≥2 — § 2 diagnoze: {sum(1 for r in old if not r['ok'])} no {len(old)} FAIL)")
    print()

    for label, ans in [("piekrītu visam", "par"), ("nepiekrītu visam", "pret")]:
        answers = {q["id"]: ans for q in questions}
        ranked = score(answers, coding, saraksti)
        in_rank = {r[0] for r in ranked}
        print(f"Rangs «{label}» (A={len(answers)}, rangā M ≥ ⌈A/2⌉ = {math.ceil(len(answers) / 2)}; {len(ranked)} no {len(saraksti)} sarakstiem):")
        for i, (p, n, m, k) in enumerate(ranked, 1):
            print(f"  {i:2d}. {p:6s} sakrīt {n:2d} no {m:2d} (cvk {k:2d})")
        below = [(s["short_name"],
                  sum(1 for q in questions
                      if coding.get(q["id"], {}).get(s["short_name"], {}).get("nostaja") in ("par", "pret")))
                 for s in saraksti if s["short_name"] not in in_rank]
        if below:
            print(f"  zem vārta (M < {math.ceil(len(answers) / 2)}): "
                  + ", ".join(f"{p} (M={m})" for p, m in below))
        print()

    n_par = n_pret = 0
    for q in questions:
        for s in saraksti:
            v = coding.get(q["id"], {}).get(s["short_name"], {}).get("nostaja")
            n_par += v == "par"
            n_pret += v == "pret"
    print(f"Virziena bilance visos jautājumos ({len(questions)} jautājumi × {len(saraksti)} saraksti): "
          f"par {n_par}, pret {n_pret}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
