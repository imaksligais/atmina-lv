"""Aģentu un komandu frontmatter ir jālasa kā YAML, citādi Claude Code to klusi izmet.

2026-11-01 `weekly-brief-writer.md` aprakstā nonāca `: ` («Nedēļas stāsti»: …),
YAML to vairs nevarēja nolasīt, un aģents pazuda no sesiju saraksta bez kļūdas
(tāpat `/audit-integrity` apraksts). Turklāt CLAUDE.md: visiem aģentiem `model: opus`.
"""
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
AGENTS = sorted(ROOT.glob(".claude/agents/*.md"))
COMMANDS = sorted(ROOT.glob(".claude/commands/*.md"))
_FM = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.S)


def _frontmatter(path: Path) -> dict:
    m = _FM.match(path.read_text(encoding="utf-8"))
    assert m, f"{path.name}: nav frontmatter bloka"
    data = yaml.safe_load(m.group(1))
    assert isinstance(data, dict), f"{path.name}: frontmatter nav kartējums"
    return data


def test_prompts_are_found():
    assert len(AGENTS) >= 10 and len(COMMANDS) >= 5, "salūzis glob"


@pytest.mark.parametrize("path", AGENTS + COMMANDS, ids=lambda p: p.name)
def test_frontmatter_parses_with_description(path):
    data = _frontmatter(path)
    assert str(data.get("description") or "").strip(), f"{path.name}: tukšs description"
    if path in AGENTS:
        assert data.get("name") == path.stem, f"{path.name}: name ≠ faila nosaukums"
        assert data.get("model") == "opus", f"{path.name}: model nav opus"
