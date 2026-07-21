"""Render the Personas (politician/persona index) page.

Phase F3b (refactor-plan-2026-04-29 § Fāze 3) carve-out from
src/generate.py. Imports flow strictly from ``src.render._common`` —
no peer-module dependencies. Sibling ``src.render.politicians`` shares
``_get_last_activity`` via ``_common`` (F4 leaf rule).

Output:
- ``output/atmina/personas.html`` — unified index of all tracked
  people (Deputāti, Amatpersonas, Žurnālisti, Ietekmētāji, Analītiķi,
  Mediji, Iestādes, Citi). Drives global search and category-filtered views.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from jinja2 import Environment

from src.render._common import (
    ASSETS_DIR,
    PARTY_COLORS,
    _get_last_activity,
    _outlet_feed_map,
    _party_short_name,
    _persona_category,
    _render_page,
    _slugify,
    _split_org_category,
)


def _fetch_personas(db: sqlite3.Connection) -> list[dict[str, Any]]:
    """Fetch + enrich all active tracked politicians for the Personas page.

    Returns a list of dicts with:
      id, name, slug, party, party_short, party_color, coalition_status,
      role, x_handle, category,
      claims_count, contradictions_count, docs_count, votes_count,
      has_photo, last_activity (dict or None), last_activity_iso (str for sort).
    """
    from src.coalition import get_coalition_map

    rows = db.execute("""
        SELECT tp.id, tp.name, tp.party, tp.relationship_type, tp.x_handle, tp.role,
               (SELECT COUNT(*) FROM claims
                WHERE opponent_id = tp.id AND claim_type = 'position') AS claims_count,
               (SELECT COUNT(*) FROM document_politicians
                WHERE politician_id = tp.id) AS docs_count,
               (SELECT COUNT(*) FROM contradictions
                WHERE opponent_id = tp.id) AS contradictions_count,
               (SELECT COUNT(*) FROM saeima_individual_votes
                WHERE politician_id = tp.id) AS votes_count
        FROM tracked_politicians tp
        WHERE tp.relationship_type NOT IN ('inactive', 'commentator')
        ORDER BY tp.name
    """).fetchall()

    coalition_map = get_coalition_map(db)
    media_feed_ids = set(_outlet_feed_map(db))
    photo_dir = ASSETS_DIR / "photos"
    photo_dir_exists = photo_dir.exists()

    personas: list[dict[str, Any]] = []
    for r in rows:
        p: dict[str, Any] = dict(r)
        p["slug"] = _slugify(p["name"])
        p["party_short"] = _party_short_name(p["party"]) if p.get("party") else ""
        p["party_color"] = PARTY_COLORS.get(p.get("party") or "", "#8b8fa3")
        # UI bucket: collapse 'not_in_saeima' into 'other' — the rail shows
        # one "Bez Saeimas frakcijas" group (līdz 2026-07-22 "Ārpus Saeimas")
        # covering both (non-Saeima parties + null-party personas). Pārsaukts,
        # jo bucketā ir arī deputāti bez frakcijas (Burovs/GKR) — sk. briefs.py.
        raw_status = coalition_map.get(p.get("party") or "", "other")
        p["coalition_status"] = "other" if raw_status == "not_in_saeima" else raw_status
        p["category"] = _persona_category(
            p["votes_count"], p.get("relationship_type"), p.get("party"), p.get("role")
        )
        p["category"] = _split_org_category(p["category"], p["id"], media_feed_ids)
        p["has_photo"] = photo_dir_exists and (photo_dir / f"{p['slug']}.jpg").exists()
        p["last_activity"] = _get_last_activity(db, p["id"], p["name"])
        p["last_activity_iso"] = (p["last_activity"] or {}).get("date", "") or ""
        personas.append(p)
    # Default ordering: most recent activity first (matches the default
    # sort button in personas.html). Server-side sort avoids an alphabetic
    # → activity flash before pnv1.js re-sorts on load.
    personas.sort(key=lambda p: (p["last_activity_iso"], p["name"]), reverse=True)
    return personas


def _fetch_personas_metrics(personas: list[dict[str, Any]]) -> dict[str, int]:
    """Header metrics for the Personas page. Pure-function over enriched rows.

    `with_contradictions` is a SUM of contradictions_count, not a count of
    distinct people-with-contradictions — so it matches the global pretrunas.html
    headline ("11 pretrunas") instead of "6 personas have contradictions",
    which read as 6 contradictions and confused readers (2026-04-25).
    """
    return {
        "total": len(personas),
        "deputies": sum(1 for p in personas if p.get("category") == "Deputāti"),
        "with_contradictions": sum(int(p.get("contradictions_count") or 0) for p in personas),
        "coalition": sum(1 for p in personas if p.get("coalition_status") == "coalition"),
        "opposition": sum(1 for p in personas if p.get("coalition_status") == "opposition"),
    }


def render_personas(
    env: Environment,
    db: sqlite3.Connection,
    atmina_dir: Path,
) -> None:
    """Render personas.html with category + party rails.

    Mirrors the inline block previously at ``src/generate.py`` lines
    2807-2831. Self-contained: fetches personas + metrics + computes
    facet counts + emits one HTML page.
    """
    personas = _fetch_personas(db)
    personas_metrics = _fetch_personas_metrics(personas)

    # Kanoniskā raila secība — cilvēki pirms institūcijām; ievietošanas
    # secība iepriekš bija nejauša (dict pēc pirmās sastapšanas).
    _CATEGORY_ORDER = [
        "Deputāti", "Amatpersonas", "Žurnālisti", "Analītiķi",
        "Ietekmētāji", "Mediji", "Iestādes", "Citi",
    ]
    raw_counts: dict[str, int] = {}
    for p in personas:
        raw_counts[p["category"]] = raw_counts.get(p["category"], 0) + 1
    category_counts: dict[str, int] = {
        c: raw_counts[c] for c in _CATEGORY_ORDER if c in raw_counts
    }
    for c, n in raw_counts.items():  # nezināmas kategorijas nepazūd
        category_counts.setdefault(c, n)

    # Rail facets: parties_with_counts mirrors pzv1 shape
    # (name, short, color, count), sorted by count desc.
    parties_with_counts: list[tuple[str, str, str, int]] = []
    for pname in sorted({p["party"] for p in personas if p.get("party")}):
        parties_with_counts.append((
            pname,
            _party_short_name(pname),
            PARTY_COLORS.get(pname, "#8b8fa3"),
            sum(1 for p in personas if p.get("party") == pname),
        ))
    parties_with_counts.sort(key=lambda x: -x[3])

    _render_page(env, "personas.html.j2", atmina_dir / "personas.html", {
        "personas": personas,
        "category_counts": category_counts,
        "parties_with_counts": parties_with_counts,
        "metrics": personas_metrics,
    })
