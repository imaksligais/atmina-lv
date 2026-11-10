"""The committed render fixture must not carry foreign tweet text.

`scripts/build_render_fixture.py` copies whole `documents` rows into
the committed render fixture under `tests/fixtures/`, which can reach
the public mirror. `documents.context_json` holds the text of OTHER people's
tweets (reply parents, quoted tweets — plan 2026-11-10-citetais-tvits), which
by operator decision is never published. The builder writes it as NULL.

Drives the real script (subprocess, its env-var path overrides) against a tiny
DB built by init_db — never the live DB.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from src.db import get_db, init_db
from src.saeima.schema import init_saeima_bills, init_saeima_tables

ROOT = Path(__file__).resolve().parent.parent
FOREIGN = "Svešā autora teksts, kas nedrīkst nonākt fiksturā"


def test_builder_blanks_context_json(tmp_path):
    db_path = str(tmp_path / "live.db")
    init_db(db_path)
    init_saeima_tables(db_path)
    init_saeima_bills(db_path)
    db = get_db(db_path)
    db.execute("INSERT INTO tracked_politicians (id, name, relationship_type) "
               "VALUES (10, 'A Kalns', 'tracked')")
    ctx = json.dumps([{"kind": "reply", "author": "Svesais", "id": "1",
                       "url": "https://x.com/Svesais/status/1", "text": FOREIGN}],
                     ensure_ascii=False)
    db.execute(
        "INSERT INTO documents (id, content, content_hash, platform, source_url, context_json) "
        "VALUES (1, 'Paša teksts.', 'h1', 'twitter', 'https://x.com/a/status/2', ?)", (ctx,))
    db.execute("INSERT INTO document_politicians (document_id, politician_id, role) "
               "VALUES (1, 10, 'subject')")
    db.commit()
    db.close()

    out_sql = tmp_path / "fixture.sql"
    env = {**os.environ, "ATMINA_FIXTURE_LIVE_DB": db_path,
           "ATMINA_FIXTURE_OUT_SQL": str(out_sql), "PYTHONPATH": str(ROOT)}
    r = subprocess.run([sys.executable, "scripts/build_render_fixture.py"], cwd=ROOT,
                       env=env, capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr[-2000:]

    sql = out_sql.read_text(encoding="utf-8")
    doc_rows = [ln for ln in sql.splitlines() if ln.startswith("INSERT INTO documents ")]
    assert len(doc_rows) == 1, "the document itself must still be copied"
    assert "Paša teksts." in doc_rows[0]
    assert FOREIGN not in sql, "foreign context text leaked into the fixture"
