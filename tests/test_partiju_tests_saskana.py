"""Partiju tests — D1 kodētāju saskaņas skripts (`scripts/partiju_tests_saskana.py`).

Fikstūras: 3 jautājumi × 2 partijas = 6 šūnas. Vārts: skripts KRĪT, ja kāds
kodētāja fails nesedz visas šūnas — tukšs fails nedrīkst izskatīties kā
„saskaņa 100 %” (denominatora princips, CLAUDE.md § Working Conventions).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


pts = _load("partiju_tests_saskana", REPO / "scripts" / "partiju_tests_saskana.py")

QS = ("q01", "q02", "q03")
PS = ("AAA", "BBB")


def _coding(values: dict[tuple[str, str], str]) -> dict:
    out: dict = {}
    for (q, p), v in values.items():
        cell = {"nostaja": v}
        if v == "klusē":
            cell["piezime"] = "nav"
        else:
            cell["citats"] = f"citāts {q} {p} {v}"
        out.setdefault(q, {})[p] = cell
    return out


BASE = {(q, p): "par" for q in QS for p in PS}


def test_full_agreement_kappa_is_one():
    coders = [_coding(BASE), _coding(BASE), _coding(BASE)]
    rep = pts.agreement(coders, questions=QS, parties=PS)
    assert rep.n_cells == 6
    assert rep.unanimous == 6
    assert rep.kappa == pytest.approx(1.0)
    assert rep.disagreements == []


def test_one_coder_opposite_everywhere_lowers_kappa_and_lists_every_cell():
    other = {k: "pret" for k in BASE}
    coders = [_coding(BASE), _coding(BASE), _coding(other)]
    rep = pts.agreement(coders, questions=QS, parties=PS)
    assert rep.n_cells == 6
    assert rep.unanimous == 0
    # 2 no 3 sakrīt katrā šūnā: P_bar = 1/3; P_e = (2/3)^2 + (1/3)^2 = 5/9;
    # kappa = (1/3 - 5/9) / (1 - 5/9) = -0.5
    assert rep.kappa == pytest.approx(-0.5)
    assert len(rep.disagreements) == 6
    assert rep.disagreements[0]["q"] == "q01" and rep.disagreements[0]["party"] == "AAA"
    assert rep.disagreements[0]["coders"] == ["par", "par", "pret"]


def test_reference_coding_gets_per_coder_agreement():
    ref = dict(BASE)
    ref[("q01", "AAA")] = "klusē"
    coders = [_coding(BASE), _coding(ref), _coding(BASE)]
    rep = pts.agreement(coders, questions=QS, parties=PS, reference=_coding(ref))
    assert rep.reference_agreement == [5, 6, 5]
    d = rep.disagreements[0]
    assert d["reference"] == "klusē"


def test_missing_cell_in_a_coder_file_is_an_error_not_agreement():
    short = _coding({k: v for k, v in BASE.items() if k != ("q03", "BBB")})
    with pytest.raises(pts.IncompleteCoding) as e:
        pts.agreement([_coding(BASE), short, _coding(BASE)], questions=QS, parties=PS)
    assert "q03" in str(e.value) and "BBB" in str(e.value) and "kodētājs 2" in str(e.value)


def test_empty_coder_file_is_an_error():
    with pytest.raises(pts.IncompleteCoding):
        pts.agreement([_coding(BASE), {}, _coding(BASE)], questions=QS, parties=PS)


def test_two_coders_without_reference_supported():
    other = dict(BASE)
    other[("q02", "AAA")] = "klusē"
    rep = pts.agreement([_coding(BASE), _coding(other)], questions=QS, parties=PS)
    assert rep.n_cells == 6 and rep.unanimous == 5 and len(rep.disagreements) == 1
    assert rep.reference_agreement is None


def test_render_markdown_has_denominator_and_table(tmp_path: Path):
    other = dict(BASE)
    other[("q02", "AAA")] = "klusē"
    rep = pts.agreement([_coding(BASE), _coding(other), _coding(BASE)],
                        questions=QS, parties=PS, reference=_coding(BASE))
    md = pts.render_markdown(rep, coder_names=["K1", "K2", "K3"])
    assert "no 6 šūnām" in md
    assert "| q02 | AAA |" in md
    assert "kappa" in md.lower()


def test_cli_end_to_end(tmp_path: Path):
    q = tmp_path / "jautajumi.yaml"
    q.write_text("".join(f"- id: {x}\n  apgalvojums: a\n" for x in QS), encoding="utf-8")
    s = tmp_path / "saraksti.yaml"
    s.write_text("".join(f"- short_name: {p}\n" for p in PS), encoding="utf-8")
    ref = tmp_path / "kodejums.json"
    ref.write_text(json.dumps(_coding(BASE), ensure_ascii=False), encoding="utf-8")
    other = dict(BASE)
    other[("q01", "BBB")] = "pret"
    files = []
    for i, c in enumerate([BASE, other, BASE]):
        f = tmp_path / f"K{i + 1}.json"
        f.write_text(json.dumps(_coding(c), ensure_ascii=False), encoding="utf-8")
        files.append(str(f))
    out = tmp_path / "out.md"
    rc = pts.main(["--questions", str(q), "--saraksti", str(s), "--coding", str(ref),
                   "--coders", *files, "--out", str(out)])
    assert rc == 0
    txt = out.read_text(encoding="utf-8")
    assert "5 no 6 šūnām" in txt and "| q01 | BBB |" in txt
