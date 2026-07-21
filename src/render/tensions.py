"""Render spriedzes.html — political tensions index page.

Pass-through pattern: ``tensions`` is pre-fetched once in
``generate_public_site`` and reused by ``render_links`` (saites.html).
Self-contained data fetcher ``_fetch_tensions`` lives here so the F3g
orchestrator-lift can keep one canonical location.

Sub-page boundary: imports only from ``src.render._common`` and stdlib.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from src.render._common import _render_page, _slugify


def _fetch_tensions(db: sqlite3.Connection) -> list[dict[str, Any]]:
    """Fetch political tensions between politicians."""
    rows = db.execute("""
        SELECT t.id, t.topic, t.description, t.tension_type, t.source_url, t.target_url,
               t.created_at,
               s.name AS source_name, s.party AS source_party,
               tgt.name AS target_name, tgt.party AS target_party
        FROM political_tensions t
        JOIN tracked_politicians s ON t.source_pid = s.id
        JOIN tracked_politicians tgt ON t.target_pid = tgt.id
        WHERE s.relationship_type NOT IN ('inactive', 'commentator')
          AND tgt.relationship_type NOT IN ('inactive', 'commentator')
        ORDER BY t.created_at DESC
    """).fetchall()
    result = []
    TYPE_LV = {"uzbrukums": "Uzbrukums", "spriedze": "Spriedze", "atbalsts": "Atbalsts"}
    for r in rows:
        d = dict(r)
        d["source_slug"] = _slugify(d["source_name"])
        d["target_slug"] = _slugify(d["target_name"])
        d["type_lv"] = TYPE_LV.get(d["tension_type"], d["tension_type"])
        d["date"] = (d["created_at"] or "")[:10]
        result.append(d)
    return result


def render_tensions(
    env, db: sqlite3.Connection, atmina_dir: Path, tensions: list[dict[str, Any]]
) -> None:
    """Emit ``atmina_dir/spriedzes.html``."""
    tension_parties = sorted(set(
        [t["source_party"] for t in tensions if t.get("source_party")] +
        [t["target_party"] for t in tensions if t.get("target_party")]
    ))
    tension_types = sorted(set(t["tension_type"] for t in tensions if t.get("tension_type")))
    spriedze_persons = sorted(set(
        [t["source_name"] for t in tensions if t.get("source_name")] +
        [t["target_name"] for t in tensions if t.get("target_name")]
    ))
    _render_page(env, "spriedzes.html.j2", atmina_dir / "spriedzes.html", {
        "tensions": tensions,
        "parties": tension_parties,
        "tension_types": tension_types,
        "persons": spriedze_persons,
    })
