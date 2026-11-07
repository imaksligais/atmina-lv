"""`content/analizes/*.md` ar `draft: true` NEdrīkst nonākt indeksā.

T15 vārts (2026-09-10): deploy.sh pārnes visu `output/`, tāpēc rutīnas
renders aizvestu nepublicētu analīzi live, ja kartīte būtu indeksā. Tests
pierāda abus virzienus — bez karoga kartīte ir, ar karogu nav.
"""

from __future__ import annotations

import pytest

from src.render import analyses


def _write(dirpath, name, draft):
    flag = "draft: true\n" if draft else ""
    (dirpath / f"{name}.md").write_text(
        f"---\ntitle: T {name}\ndate: 2026-09-10\nstandalone: true\n{flag}---\n\nteksts\n",
        encoding="utf-8",
    )


@pytest.fixture
def analizes_dir(tmp_path, monkeypatch):
    d = tmp_path / "analizes"
    d.mkdir()
    monkeypatch.setattr(analyses, "CONTENT_DIR", tmp_path)
    return d


def test_draft_card_is_excluded_and_published_card_is_included(analizes_dir):
    _write(analizes_dir, "publiska", draft=False)
    _write(analizes_dir, "melnraksts", draft=True)
    slugs = [a["slug"] for a in analyses._load_analyses()]
    assert slugs == ["publiska"], slugs


def test_gate_actually_fails_without_the_flag(analizes_dir):
    """Mutācija: tas pats fails bez karoga IR indeksā — vārts nav kosmētisks."""
    _write(analizes_dir, "melnraksts", draft=False)
    assert [a["slug"] for a in analyses._load_analyses()] == ["melnraksts"]
