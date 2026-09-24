"""Partiju tests — D1 kodētāju saskaņa (READ-ONLY, tikai faili).

Salīdzina 2+ neatkarīgu kodētāju `kodejums`-formas failus (un pēc izvēles
esošo `kodejums.json` kā atsauci) šūnu pa šūnai un izdod:

* saucēju — cik šūnas (jautājumi × saraksti) salīdzinātas;
* pilnīgas sakritības skaitu (visi kodētāji vienādi);
* Fleisa kappa pār kodētājiem (3 kategorijas: par / pret / klusē);
* katra kodētāja sakritību ar atsauci (ja `--coding` dots);
* domstarpību tabulu operatoram (šūna / atsauce / K1..Kn / citāti).

    .venv/Scripts/python.exe scripts/partiju_tests_saskana.py \
        --coders content/partiju-tests/d1/K1.json content/partiju-tests/d1/K2.json \
                 content/partiju-tests/d1/K3.json \
        --coding content/partiju-tests/kodejums.json \
        --out docs/plans/2026-09-21-partiju-tests-d1-saskana.md

Vārts, kas nedrīkst klusēt: kodētāja fails, kurā trūkst kaut vienas šūnas,
ir `IncompleteCoding` kļūda (exit 2), nevis „saskaņa 100 %”. Nekas netiek
rakstīts DB vai `kodejums.json`.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import yaml

CATEGORIES = ("par", "pret", "klusē")


class IncompleteCoding(ValueError):
    """Kodētāja failā trūkst šūnu — saucējs nav pilns."""


@dataclass
class AgreementReport:
    n_cells: int
    n_coders: int
    unanimous: int
    kappa: float
    reference_agreement: list[int] | None
    disagreements: list[dict] = field(default_factory=list)
    distribution: list[Counter] = field(default_factory=list)


def _stance(coding: dict, q: str, p: str, coder_label: str) -> str:
    cell = (coding.get(q) or {}).get(p)
    if not isinstance(cell, dict) or cell.get("nostaja") not in CATEGORIES:
        raise IncompleteCoding(f"{coder_label}: trūkst vai nederīga šūna {q}/{p}")
    return cell["nostaja"]


def _quote(coding: dict, q: str, p: str) -> str:
    cell = (coding.get(q) or {}).get(p) or {}
    return (cell.get("citats") or cell.get("piezime") or "").replace("|", "¦").replace("\n", " ")


def fleiss_kappa(rows: list[Counter], n_coders: int) -> float:
    """Fleisa kappa; `rows[i]` = kategoriju skaits šūnā i (summa = n_coders)."""
    n = len(rows)
    if n == 0 or n_coders < 2:
        raise ValueError("kappa prasa ≥1 šūnu un ≥2 kodētājus")
    p_i = [(sum(c * c for c in r.values()) - n_coders) / (n_coders * (n_coders - 1)) for r in rows]
    p_bar = sum(p_i) / n
    totals = Counter()
    for r in rows:
        totals.update(r)
    p_e = sum((totals[c] / (n * n_coders)) ** 2 for c in CATEGORIES)
    if p_e == 1.0:
        return 1.0
    return (p_bar - p_e) / (1 - p_e)


def agreement(coders: list[dict], *, questions, parties, reference: dict | None = None) -> AgreementReport:
    if len(coders) < 2:
        raise ValueError("vajag ≥2 kodētājus")
    rows: list[Counter] = []
    unanimous = 0
    ref_agree = [0] * len(coders) if reference is not None else None
    disagreements: list[dict] = []
    for q in questions:
        for p in parties:
            votes = [_stance(c, q, p, f"kodētājs {i + 1}") for i, c in enumerate(coders)]
            ref = _stance(reference, q, p, "atsauce") if reference is not None else None
            rows.append(Counter(votes))
            all_same = len(set(votes)) == 1
            if all_same and (ref is None or ref == votes[0]):
                unanimous += 1
            else:
                disagreements.append({
                    "q": q, "party": p, "reference": ref, "coders": votes,
                    "quotes": [_quote(c, q, p) for c in coders],
                    "reference_quote": _quote(reference, q, p) if reference is not None else "",
                })
            if ref_agree is not None:
                for i, v in enumerate(votes):
                    if v == ref:
                        ref_agree[i] += 1
    return AgreementReport(
        n_cells=len(rows), n_coders=len(coders), unanimous=unanimous,
        kappa=fleiss_kappa(rows, len(coders)), reference_agreement=ref_agree,
        disagreements=disagreements, distribution=rows,
    )


def render_markdown(rep: AgreementReport, *, coder_names: list[str], reference_name: str | None = None) -> str:
    n = rep.n_cells
    lines = [
        f"# Kodētāju saskaņa — {rep.n_coders} kodētāji × {n} šūnas",
        "",
        f"- Šūnas salīdzinātas: **{n}** (saucējs = jautājumi × saraksti; katrs kodētāja fails pilns).",
        f"- Pilnīga sakritība{' (kodētāji + atsauce)' if reference_name else ''}: **{rep.unanimous} no {n} šūnām**.",
        f"- Fleisa kappa pār kodētājiem: **{rep.kappa:.3f}** (1 = pilnīga saskaņa; 0 = nejaušība).",
    ]
    if rep.reference_agreement is not None:
        parts = ", ".join(f"{name} {a} no {n}" for name, a in zip(coder_names, rep.reference_agreement, strict=True))
        lines.append(f"- Sakritība ar atsauci `{reference_name}`: {parts}.")
    totals = Counter()
    for r in rep.distribution:
        totals.update(r)
    lines.append("- Kodētāju balsu sadalījums: " + ", ".join(f"{c} {totals[c]}" for c in CATEGORIES) + ".")
    lines += ["", f"## Domstarpības ({len(rep.disagreements)} šūnas) — operatora rindu-lēmumi", ""]
    head = ["jautājums", "saraksts"] + (["atsauce"] if rep.reference_agreement is not None else []) + coder_names + ["citāti (atsauce ¦ kodētāji)"]
    lines.append("| " + " | ".join(head) + " |")
    lines.append("|" + "---|" * len(head))
    for d in rep.disagreements:
        quotes = " ¦ ".join(([d["reference_quote"]] if rep.reference_agreement is not None else []) + d["quotes"])
        row = [d["q"], d["party"]] + ([d["reference"] or ""] if rep.reference_agreement is not None else []) + d["coders"] + [quotes[:600]]
        lines.append("| " + " | ".join(row) + " |")
    if not rep.disagreements:
        lines.append("| — | — |" + " — |" * (len(head) - 2))
    return "\n".join(lines) + "\n"


def _load_json(p: str) -> dict:
    return json.loads(Path(p).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--questions", default="content/partiju-tests/jautajumi.yaml")
    ap.add_argument("--saraksti", default="content/partiju-tests/saraksti.yaml")
    ap.add_argument("--coding", default=None, help="atsauces kodējums (piem. kodejums.json); bez tā — tikai kodētāji")
    ap.add_argument("--coders", nargs="+", required=True, help="≥2 kodētāju JSON faili")
    ap.add_argument("--out", default=None, help="Markdown ziņojuma ceļš (noklusējums: stdout)")
    a = ap.parse_args(argv)

    questions = [q["id"] for q in yaml.safe_load(Path(a.questions).read_text(encoding="utf-8"))]
    parties = [s["short_name"] for s in yaml.safe_load(Path(a.saraksti).read_text(encoding="utf-8"))]
    coders = [_load_json(f) for f in a.coders]
    names = [Path(f).stem for f in a.coders]
    reference = _load_json(a.coding) if a.coding else None
    try:
        rep = agreement(coders, questions=questions, parties=parties, reference=reference)
    except IncompleteCoding as e:
        print(f"KĻŪDA: {e} — saucējs nav pilns, saskaņa netiek rēķināta.", file=sys.stderr)
        return 2
    md = render_markdown(rep, coder_names=names, reference_name=Path(a.coding).name if a.coding else None)
    if a.out:
        Path(a.out).write_text(md, encoding="utf-8")
        print(f"{rep.unanimous} no {rep.n_cells} šūnām sakrīt; kappa {rep.kappa:.3f}; "
              f"domstarpības {len(rep.disagreements)} → {a.out}")
    else:
        print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
