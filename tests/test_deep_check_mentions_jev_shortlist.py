"""Prompta sargs: pēc zelta testa /deep-check un hunter lasa Jev īso sarakstu pirmo."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_deep_check_and_hunter_reference_shortlist_script():
    for rel in (".claude/commands/deep-check.md", ".claude/agents/contradiction-hunter.md",
                "wiki/operations/agenti/contradiction-hunter.md"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "scripts/jev_contradiction_shortlist.py" in text, rel
        assert "T9" in text or "balsojumu pusi" in text, rel   # balsojumu puse paliek strukturālā SQL


def test_shortlist_is_reading_order_not_verdict():
    text = (ROOT / ".claude/agents/contradiction-hunter.md").read_text(encoding="utf-8")
    i = text.index("scripts/jev_contradiction_shortlist.py")
    window = text[i - 200: i + 1500].lower()
    assert "devils-advocate" in window and "confirmed=0" in window


def test_prompts_quote_the_measured_recall_not_a_promise():
    # Skaitlis bez izcelsmes nav skaitlis: abos promptos stāv 16/18 + θ=0,3 + CHANGELOG atsauce.
    for rel in (".claude/commands/deep-check.md", ".claude/agents/contradiction-hunter.md"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "16/18" in text and "0,3" in text and "2026-09-18 (2)" in text, rel
