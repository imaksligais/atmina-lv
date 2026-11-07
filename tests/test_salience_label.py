"""Pretrunu «Nozīmīgums» kartītē ir vārds, ne kails skaitlis (2026-09-06)."""
from pathlib import Path

from src.render._common import _salience_label

TPL = Path(__file__).resolve().parents[1] / "templates"


def test_thresholds():
    assert _salience_label(0.8) == "augsta"
    assert _salience_label(0.7) == "augsta"
    assert _salience_label(0.5) == "vidēja"
    assert _salience_label(0.69) == "vidēja"
    assert _salience_label(0.49) == "zema"
    assert _salience_label(None) == ""
    assert _salience_label("x") == ""


def test_card_template_uses_label_not_raw_number():
    card = (TPL / "pretrunas.html.j2").read_text(encoding="utf-8")
    assert "salience|salience_label" in card
    assert "Nozīmīgums {{ '%.2f'" not in card


def test_detail_template_keeps_number_beside_label():
    detail = (TPL / "pretruna-detail.html.j2").read_text(encoding="utf-8")
    assert "salience|salience_label" in detail
    assert "'%.2f' % c.salience" in detail
