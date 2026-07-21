"""Render the Pretrunas (contradictions) pages.

Phase F3a (refactor-plan-2026-04-29 § Fāze 3) prototype: carved out of
src/generate.py to validate the leaf-vs-fan-out split before tackling
the remaining nine sub-page groups. Imports flow strictly from
``src.render._common`` — no peer-module dependencies.

Outputs:
- ``output/atmina/pretrunas.html`` — the index card grid + filters
- ``output/atmina/pretrunas/<id>.html`` — per-contradiction detail page
- ``output/atmina/assets/og/pretruna-<id>.png`` — 1200×630 OG previews
  rendered via Playwright (incremental: skipped when PNG mtime newer
  than the contradiction's ``detected_at``)
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from jinja2 import Environment

from src.render._common import (
    BASE_URL,
    _enrich_contradiction,
    _photo_data_uri,
    _render_page,
    _slugify,
)


def _keep_digging_for_contradiction(
    c: dict[str, Any],
    by_topic: dict[str, list[dict[str, Any]]],
    party_people: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """"Turpini rakt" columns for a pretruna detail page (hrefs relative to
    ``pretrunas/<id>.html``). Deterministic — ordering follows the
    contradictions list, no randomness — so char baselines stay stable.
    """
    columns: list[dict[str, Any]] = []
    topic = c.get("topic")

    if topic:
        same_topic = [r for r in by_topic.get(topic, []) if r["id"] != c["id"]][:5]
        if same_topic:
            columns.append({
                "title": "Citi par šo tēmu",
                "links": [
                    {
                        "label": r["politician_name"],
                        "href": f"{r['id']}.html",
                        "sub": r.get("category_label") or r.get("severity_lv"),
                    }
                    for r in same_topic
                ],
            })
        columns.append({
            "title": "Tēma",
            "links": [{
                "label": topic,
                "href": f"../temas/{_slugify(topic)}.html",
                "sub": "visas pozīcijas →",
            }],
        })

    party = c.get("party")
    if party:
        people = [
            q for q in party_people.get(party, []) if q["slug"] != c.get("slug")
        ][:5]
        if people:
            columns.append({
                "title": "Citi šajā partijā",
                "links": [
                    {"label": q["name"], "href": f"../politiki/{q['slug']}.html", "sub": None}
                    for q in people
                ],
            })

    return {"columns": columns}


def _fetch_contradictions(db: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = db.execute("""
        SELECT
            ct.id, ct.opponent_id, ct.topic, ct.summary, ct.severity,
            ct.detected_at, ct.salience,
            tp.name AS politician_name, tp.party, tp.role,
            c_old.stance AS old_stance, c_old.stated_at AS old_date,
            c_old.source_url AS old_source, c_old.quote AS old_quote,
            c_old.claim_type AS old_claim_type,
            c_new.stance AS new_stance, c_new.stated_at AS new_date,
            c_new.source_url AS new_source, c_new.quote AS new_quote,
            c_new.claim_type AS new_claim_type
        FROM contradictions ct
        JOIN tracked_politicians tp ON ct.opponent_id = tp.id
        LEFT JOIN claims c_old ON ct.claim_old_id = c_old.id
        LEFT JOIN claims c_new ON ct.claim_new_id = c_new.id
        WHERE COALESCE(ct.confirmed, 1) = 1
        ORDER BY ct.detected_at DESC
    """).fetchall()

    results = []
    for r in rows:
        d = dict(r)
        _enrich_contradiction(d, db)
        results.append(d)
    return results


def _render_og_cards(
    contradictions: list[dict[str, Any]],
    env: Environment,
    out_dir: Path,
) -> int:
    """Render 1200x630 OG preview PNGs, one per contradiction.

    Headless Chromium via Playwright. One browser + one page reused
    across all cards. Skips rendering when the PNG already exists AND
    is newer than the contradiction's detected_at (incremental build).
    Returns the number of cards actually rendered.
    """
    from playwright.sync_api import sync_playwright

    out_dir.mkdir(parents=True, exist_ok=True)
    tpl = env.get_template("og-card.html.j2")
    rendered = 0

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": 1200, "height": 630},
            device_scale_factor=2,
        )
        page = context.new_page()

        for c in contradictions:
            out_path = out_dir / f"pretruna-{c['id']}.png"

            if out_path.exists():
                detected = c.get("detected_at") or ""
                try:
                    png_mtime = datetime.fromtimestamp(out_path.stat().st_mtime)
                    detected_dt = datetime.fromisoformat(
                        detected.replace("Z", "+00:00")[:19]
                    )
                    if png_mtime > detected_dt:
                        continue
                except (ValueError, TypeError):
                    pass

            render_c = dict(c)
            render_c["photo_data_uri"] = _photo_data_uri(c["slug"])

            html = tpl.render(c=render_c)
            page.set_content(html, wait_until="networkidle")
            page.screenshot(
                path=str(out_path),
                full_page=False,
                omit_background=False,
                type="png",
            )
            rendered += 1

        browser.close()

    return rendered


def render_contradictions(
    env: Environment,
    atmina_dir: Path,
    contradictions: list[dict[str, Any]],
    all_parties: list[str],
) -> None:
    """Write pretrunas.html, per-contradiction detail pages, and OG card PNGs.

    Mirrors the inline block previously at src/generate.py lines 3145-3195.
    The fan-out (PNG render) is best-effort: count is logged.
    """
    pretrunas_persons = sorted(
        set(c["politician_name"] for c in contradictions if c.get("politician_name"))
    )

    week_cutoff = (date.today() - timedelta(days=7)).isoformat()
    for c in contradictions:
        c["is_new"] = (c.get("detected_at") or "") >= week_cutoff
    sev_counts = {
        "direct_contradiction": sum(
            1 for c in contradictions if c.get("severity") == "direct_contradiction"
        ),
        "reversal": sum(1 for c in contradictions if c.get("severity") == "reversal"),
        "minor_shift": sum(
            1 for c in contradictions if c.get("severity") == "minor_shift"
        ),
    }
    pretrunas_metrics = {
        "total": len(contradictions),
        "last_week": sum(
            1 for c in contradictions if (c.get("detected_at") or "") >= week_cutoff
        ),
        "direct": sum(
            1 for c in contradictions if c.get("severity") == "direct_contradiction"
        ),
    }
    _render_page(env, "pretrunas.html.j2", atmina_dir / "pretrunas.html", {
        "contradictions": contradictions,
        "sev_counts": sev_counts,
        "parties": all_parties,
        "persons": pretrunas_persons,
        "metrics": pretrunas_metrics,
        "BASE_URL": BASE_URL,
    })

    # Render per-contradiction OG preview PNGs (1200x630, Playwright).
    og_cards_dir = atmina_dir / "assets" / "og"
    og_rendered = _render_og_cards(contradictions, env, og_cards_dir)
    print(f"  assets/og/: rendered {og_rendered}/{len(contradictions)} pretruna preview PNGs")

    # Render per-contradiction detail pages with per-pretruna og:* meta.
    pretrunas_detail_dir = atmina_dir / "pretrunas"
    pretrunas_detail_dir.mkdir(exist_ok=True)
    by_politician: dict[int, list[dict[str, Any]]] = {}
    by_topic: dict[str, list[dict[str, Any]]] = {}
    party_people: dict[str, list[dict[str, Any]]] = {}
    _seen_people: set[str] = set()
    for _c in contradictions:
        by_politician.setdefault(_c["opponent_id"], []).append(_c)
        _t = _c.get("topic")
        if _t:
            by_topic.setdefault(_t, []).append(_c)
        _pty = _c.get("party")
        _key = f"{_pty}|{_c.get('slug')}"
        if _pty and _key not in _seen_people:
            _seen_people.add(_key)
            party_people.setdefault(_pty, []).append(
                {"name": _c["politician_name"], "slug": _c["slug"]}
            )

    for c in contradictions:
        related = [r for r in by_politician[c["opponent_id"]] if r["id"] != c["id"]][:3]
        _render_page(
            env,
            "pretruna-detail.html.j2",
            pretrunas_detail_dir / f"{c['id']}.html",
            {
                "c": c,
                "related": related,
                "digging": _keep_digging_for_contradiction(c, by_topic, party_people),
                "BASE_URL": BASE_URL,
                "canonical_url": f"{BASE_URL}/pretrunas/{c['id']}.html",
            },
        )
    print(f"  pretrunas/: {len(contradictions)} detail pages")
