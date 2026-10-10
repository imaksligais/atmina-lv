"""Promptu SQL nedrīkst filtrēt rutīnas kolonnas pēc KALENDĀRA dienas.

Rutīna beidzas pēc pusnakts; `date(created_at) = ?` / `date(detected_at) = ?`
izmet 00:00–05:00 rindas (2026-09-25: 46/349 konteksta piezīmes, 41/366
spriedzes, 3/35 pretrunas). Fiksēta `+N hours` nobīde salūzt 2026-10-25.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_TEXT_SUFFIXES = {".md", ".js", ".json", ".py", ".txt"}
PROMPTS = sorted({
    *ROOT.glob(".claude/agents/*.md"),
    *ROOT.glob(".claude/commands/*.md"),
    *ROOT.glob(".claude/skills/**/*.md"),
    *ROOT.glob(".claude/references/**/*.md"),
    *(p for p in ROOT.glob(".claude/workflows/**/*")
      if p.is_file() and p.suffix in _TEXT_SUFFIXES),
})
# Jebkurš salīdzinājums ar kalendāra dienu — arī `>=`, `<`, `IN (…)` — ir tā pati
# kļūme: robeža stāv pusnaktī, nevis 05:00.
CAL_DAY = re.compile(
    r"date\(\s*(?:\w+\.)?(created_at|detected_at)\b[^)]*\)\s*(<=|>=|=|<|>|BETWEEN\b|IN\b)",
    re.I)
FIXED_OFFSET = re.compile(r"date(?:time)?\('now'\s*,\s*'[+-]\d+ hours?'\)", re.I)


def test_prompts_are_scanned():
    assert len(PROMPTS) >= 10, f"atrasti tikai {len(PROMPTS)} prompti — salūzis glob"


def test_no_calendar_day_filter_on_routine_columns():
    hits = [f"{p.relative_to(ROOT)}:{i}: {line.strip()}"
            for p in PROMPTS
            for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
            if CAL_DAY.search(line) or FIXED_OFFSET.search(line)]
    assert not hits, "kalendāra dienas filtri promptos:\n" + "\n".join(hits)
