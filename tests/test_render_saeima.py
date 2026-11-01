"""saeima.html (15. Saeimas pusloks) — viens e2e tests caur īsto ieejas punktu.

Renderē `generate_public_site(only={"saeima"})` no komitētās fixture DB un
fixture sastāva/rezultātu YAML. Kļūmes, ko tas noķer:
  (a) puslokā nav tieši 100 sēdvietu;
  (b) izsekotais deputāts nav sasaistīts ar profilu VAI neizsekotais saņem
      saiti uz neesošu profilu (404);
  (c) neizsekotais pozīciju lēcā izskatās kā «0» (zemākā krāsa), nevis «nav datu»;
  (d) nepilns sastāva fails (99) klusi renderē nepilnu lapu, nevis krīt.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

FIXTURES = Path(__file__).parent / "fixtures"
ELECTED = FIXTURES / "cvk_sv2026_ievēlētie.yaml"
RESULTS = FIXTURES / "cvk_sv2026_rezultati.yaml"


@pytest.fixture
def fixture_db(tmp_path):
    from src.db import get_db, init_db
    from src.saeima.schema import init_saeima_bills, init_saeima_tables
    from tests.fixture_sql import load_render_fixture_sql

    db_path = str(tmp_path / "fixture.db")
    init_db(db_path)
    init_saeima_tables(db_path)
    init_saeima_bills(db_path)
    conn = get_db(db_path)
    for ddl in (
        "ALTER TABLE tracked_politicians ADD COLUMN x_handle TEXT",
        "ALTER TABLE documents ADD COLUMN is_paywall BOOLEAN DEFAULT FALSE",
        "ALTER TABLE documents ADD COLUMN summary TEXT",
    ):
        try:
            conn.execute(ddl)
        except Exception:  # noqa: BLE001 — kolonna jau ir
            pass
    conn.executescript(load_render_fixture_sql())
    conn.commit()
    conn.close()
    return db_path


def _render(tmp_path, monkeypatch, db_path, elected_path):
    import src.render._orchestrator as orch
    import src.render.saeima as saeima_mod
    from src.render import generate_public_site

    def _stub(dest, *a, **k):
        Path(dest).write_text("/* stub */", encoding="utf-8")

    for name in ("_download_chart_js", "_download_annotation_plugin", "_download_d3"):
        if hasattr(orch, name):
            monkeypatch.setattr(orch, name, _stub)
    monkeypatch.setattr(saeima_mod, "ELECTED_PATH", elected_path)
    monkeypatch.setattr(saeima_mod, "RESULTS_PATH", RESULTS)
    out = tmp_path / "site"
    generate_public_site(db_path=db_path, output_dir=str(out), only={"saeima"})
    return (out / "atmina" / "saeima.html").read_text(encoding="utf-8")


def _tracked_names(db_path: str) -> set[str]:
    import sqlite3

    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT name FROM tracked_politicians "
        "WHERE relationship_type NOT IN ('inactive', 'commentator')"
    ).fetchall()
    conn.close()
    return {r[0] for r in rows}


def _seat(html: str, name: str) -> str:
    m = re.search(r'<a [^>]*class="seat"[^>]*aria-label="' + re.escape(name) + r',[^"]*"[^>]*>', html)
    assert m, f"sēdvieta {name!r} nav atrasta"
    return m.group(0)


def _row(html: str, slug: str) -> str:
    m = re.search(r'<details class="slv-dep[^"]*" id="dep-' + re.escape(slug) + r'".*?</details>', html, re.S)
    assert m, f"rinda dep-{slug} nav atrasta"
    return m.group(0)


def test_saeima_page_end_to_end(tmp_path, monkeypatch, fixture_db):
    from src.render._common import _slugify

    html = _render(tmp_path, monkeypatch, fixture_db, ELECTED)

    # (a) 100 sēdvietas
    assert len(re.findall(r'<a [^>]*class="seat"', html)) == 100

    elected = [e["name"] for e in yaml.safe_load(ELECTED.read_text(encoding="utf-8"))["elected"]]
    tracked = _tracked_names(fixture_db) & set(elected)
    untracked = [n for n in elected if n not in tracked]
    assert tracked and untracked, "fixture jāsatur abas klases"

    # (b) izsekotajam profila saite, neizsekotajam nav
    t = sorted(tracked)[0]
    assert f'href="politiki/{_slugify(t)}.html"' in _row(html, _slugify(t))
    u = untracked[0]
    u_row = _row(html, _slugify(u))
    assert "politiki/" not in u_row
    assert "Profils vēl nav izveidots." in u_row

    # (c) neizsekotajam pozīciju lēcā «nav datu», ne 0
    assert 'data-pos="nav"' in _seat(html, u)
    assert re.search(r'data-lens-val="pos"[^>]*>\s*nav datu\s*<', u_row)
    assert 'data-pos="nav"' not in _seat(html, t)


def test_saeima_incomplete_composition_fails(tmp_path, monkeypatch, fixture_db):
    doc = yaml.safe_load(ELECTED.read_text(encoding="utf-8"))
    doc["elected"] = doc["elected"][:99]
    bad = tmp_path / "ievēlētie_99.yaml"
    bad.write_text(yaml.safe_dump(doc, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ValueError, match="100"):
        _render(tmp_path, monkeypatch, fixture_db, bad)
