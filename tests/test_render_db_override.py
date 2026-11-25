"""`generate_public_site(db_path=<kopija>)` lasa TIKAI kopiju.

Kļūme (atrasta 2026-11-10): palīgi, kas DB atver paši bez argumenta
(`src.coalition._short_name_map` → `get_db()`), lasīja `src.db.DB_PATH`, t. i.,
dzīvo DB, kamēr pārējais renders lasīja `--db` kopiju. Testos `DB_PATH` ir
bloķētais ceļš, tāpēc bez labojuma partijas īsvārds no kopijas pazūd.
"""
from __future__ import annotations

from pathlib import Path


def _fixture_db(tmp_path) -> str:
    from src.db import get_db, init_db
    from src.saeima.schema import init_saeima_bills, init_saeima_tables

    db_path = str(tmp_path / "kopija.db")
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
    conn.execute(
        "INSERT INTO parties (name, short_name) VALUES ('Kopijas Testa Partija', 'KTPX')"
    )
    conn.commit()
    conn.close()
    return db_path


def test_render_helpers_read_the_db_passed_to_generate_public_site(tmp_path, monkeypatch):
    import src.db as dbmod
    import src.render._orchestrator as orch
    from src.coalition import clear_party_short_name_cache, lookup_party_short_name
    from src.render import generate_public_site

    db_path = _fixture_db(tmp_path)
    live_before = dbmod.DB_PATH
    clear_party_short_name_cache()

    seen = {}

    def _record(*a, **k):
        seen["short"] = lookup_party_short_name("Kopijas Testa Partija")

    monkeypatch.setattr(orch, "render_positions", _record)
    for name in ("_download_chart_js", "_download_annotation_plugin", "_download_d3"):
        if hasattr(orch, name):
            monkeypatch.setattr(
                orch, name, lambda dest, *a, **k: Path(dest).write_text("", encoding="utf-8")
            )

    generate_public_site(db_path=db_path, output_dir=str(tmp_path / "site"), only={"pozicijas"})

    assert seen.get("short") == "KTPX", f"īsvārds nav no kopijas: {seen.get('short')!r}"
    assert dbmod.DB_PATH == live_before, "DB_PATH pēc rendera nav atjaunots"
