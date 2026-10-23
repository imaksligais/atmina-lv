"""Render the Pretrunas (contradictions) pages.

Phase F3a (refactor-plan-2026-04-29 § Fāze 3) prototype: carved out of
src/generate.py to validate the leaf-vs-fan-out split before tackling
the remaining nine sub-page groups. Imports flow from
``src.render._common`` plus ``src.briefs.contradiction_excerpt_text`` (the
collapsed register row previews the same words the briefs do) — no peer-module
dependencies.

Outputs:
- ``output/atmina/pretrunas.html`` — the index card grid + filters
- ``output/atmina/pretrunas/<id>.html`` — per-contradiction detail page
  (and, for ``confirmed = -1`` rows, a noindex withdrawal notice page)
- ``output/atmina/assets/og/pretruna-<id>.png`` — 1200×630 OG previews
  rendered via the shared ``_common.og_render`` (incremental: skipped when the
  card's content hash matches ``output/og-hashes.json`` — outside the deploy tree)
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

from jinja2 import Environment

from src.briefs import contradiction_excerpt_text
from src.contradiction_labels import SEVERITY_LV, lower_first
from src.render._common import (
    _topic_page_href,
    BASE_URL,
    _delta_days,
    _photo_data_uri,
    _render_page,
    _slugify,
    lv_date_locative,
    lv_gap_label,
    trailing_days_cutoff,
)
from src.render._common import og_render
from src.render._common.contradictions import fetch_contradictions
from src.render._common.og_render import og_role_line


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
                "href": _topic_page_href(topic),
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
    """Shared enriched rows plus vote text used only by contradiction OG cards."""
    results = fetch_contradictions(db)
    for d in results:
        # Pēc hronoloģiskās maiņas enrich iekšienē — puses jau ir galīgās.
        # Balsi meklē balsojuma claim politiķim, ne pretrunas `opponent_id`:
        # partijas pretrunā (scripts/partiju_pretrunas.py) tie atšķiras.
        for side in ("old", "new"):
            d[f"{side}_vote_text"] = (
                _og_vote_text(db, d.get(f"{side}_source"), d.get(f"{side}_opponent_id"))
                if d.get(f"{side}_claim_type") == "saeima_vote" else None
            )
    return results


# CLAUDE.md: balsis ieraksta, kā reģistrēta — «Atturas» nekad nav «balsoja pret».
_BALLOT_LV = {
    "Par": "Balsoja «Par»",
    "Pret": "Balsoja «Pret»",
    "Atturas": "Atturējās",
    "Nebalsoja": "Nebalsoja",
}


def _og_vote_text(
    db: sqlite3.Connection, url: str | None, politician_id: int | None,
) -> str | None:
    """OG kartītes balsojuma puse: «Balsoja «Par»: <motīvs> (47:8:18)».

    `saeima_vote` claim stance apraksta likumprojektu, ne šo balsojumu (T20),
    tāpēc kartīte lasa paša politiķa balsi un kopskaitu. None, ja balsojuma
    rindu vai balsi nevar atrast — tad kartīte rāda stance kā līdz šim.
    """
    if not url or politician_id is None:
        return None
    vote = db.execute(
        "SELECT id, motif, total_par, total_pret, total_atturas"
        " FROM saeima_votes WHERE url = ?", (url,),
    ).fetchone()
    if not vote:
        return None
    ballot = db.execute(
        "SELECT vote FROM saeima_individual_votes WHERE vote_id = ? AND politician_id = ?",
        (vote["id"], politician_id),
    ).fetchone()
    prefix = _BALLOT_LV.get(ballot["vote"]) if ballot else None
    if not prefix:
        return None
    totals = f" ({vote['total_par']}:{vote['total_pret']}:{vote['total_atturas']})"
    # Motīvu saīsina pirms skaitļiem, lai _og_text robeža tos nenogriež.
    motif, _ = _og_text(None, vote["motif"], _OG_TEXT_LIMIT - len(prefix) - len(totals) - 2)
    return f"{prefix}: {motif}{totals}" if motif else f"{prefix}{totals}"


def _fetch_withdrawn_contradictions(db: sqlite3.Connection) -> list[dict[str, Any]]:
    """Atsauktās publicētās pretrunas (``confirmed = -1``) labojuma lapām.

    Apzināti NEizmanto ``_enrich_contradiction``: pēc atsaukuma claim var būt
    dzēsts (``claim_old_id`` NULL), un lapa nerāda pozīciju pārus — tikai
    piezīmi un sākotnējo kopsavilkumu. ``profile_exists`` atkārto
    ``_fetch_politicians`` filtru, lai saite uz profilu nekad neved uz lapu,
    kuras kokā nav.
    """
    rows = db.execute("""
        SELECT ct.id, ct.topic, ct.summary, ct.detected_at,
               ct.withdrawn_at, ct.withdrawn_note,
               tp.name AS politician_name, tp.relationship_type
        FROM contradictions ct
        LEFT JOIN tracked_politicians tp ON ct.opponent_id = tp.id
        WHERE ct.confirmed = -1
        ORDER BY ct.id
    """).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        name = d.get("politician_name")
        d["slug"] = _slugify(name) if name else ""
        d["profile_exists"] = bool(name) and d.get("relationship_type") not in (
            "inactive", "commentator",
        )
        d["detected_date"] = (d.get("detected_at") or "")[:10]
        d["withdrawn_date"] = (d.get("withdrawn_at") or "")[:10]
        out.append(d)
    return out


def render_withdrawn_contradictions(
    env: Environment,
    atmina_dir: Path,
    withdrawn: list[dict[str, Any]],
) -> int:
    """Uzraksta ``pretrunas/<id>.html`` labojuma lapu katrai atsauktai pretrunai.

    Publicēti pārskati saista uz šīm lapām, tāpēc tās paliek sasniedzamas, bet
    ir noindex, nav sitemapā un nav nevienā sarakstā (tie lasa tikai
    ``_fetch_contradictions``). OG kartīte netiek renderēta.
    """
    out_dir = atmina_dir / "pretrunas"
    out_dir.mkdir(parents=True, exist_ok=True)
    for c in withdrawn:
        _render_page(env, "pretruna-atsaukta.html.j2", out_dir / f"{c['id']}.html", {
            "c": c,
            "BASE_URL": BASE_URL,
        })
    return len(withdrawn)


_OG_TEXT_LIMIT = 230
def _og_text(
    quote: str | None, stance: str | None, limit: int = _OG_TEXT_LIMIT,
) -> tuple[str, bool]:
    """(teksts, is_quote) kartītes kolonnai. Citāts burtiski; tikai beigu
    «,;:» → «…» un pārāk garu nogriež pie vārda robežas."""
    is_quote = bool((quote or "").strip())
    text = ((quote if is_quote else stance) or "").strip()
    # Saīsinātas saites (t.co) nav runātāja vārdi — kartītē tās tikai trokšņo.
    text = re.sub(r"\s*https?://\S+", "", text).strip()
    if len(text) > limit:
        window = text[:limit]
        sp = window.rfind(" ")
        text = (window[:sp] if sp > 0 else window).rstrip(" ,;:—–-") + "…"
    elif text and text[-1] in ",;:":
        text = text[:-1].rstrip() + "…"
    return text, is_quote


def _og_card_context(c: dict[str, Any]) -> dict[str, Any]:
    """Visi kartītes teksti, aprēķināti Python pusē (veidne paliek "muļķa")."""
    old_date, new_date = c.get("old_date") or "", c.get("new_date") or ""
    with_year = old_date[:4] != new_date[:4]
    # Balsojuma pusē — balss + kopskaits (_og_vote_text), ne likumprojekta apraksts.
    q_old, old_is_quote = (
        (c["old_vote_text"], False) if c.get("old_vote_text")
        else _og_text(c.get("old_quote"), c.get("old_stance")))
    q_new, new_is_quote = (
        (c["new_vote_text"], False) if c.get("new_vote_text")
        else _og_text(c.get("new_quote"), c.get("new_stance")))
    longest = max(len(q_old), len(q_new))
    role_line = og_role_line(c.get("role"), c.get("party") or c.get("party_short"))
    return {
        "id": c["id"],
        "name": c.get("politician_name") or "",
        "role_line": role_line,
        "photo": c.get("photo_data_uri"),
        "initials": c.get("initials") or "",
        "kind": c.get("category_label") or c.get("severity_lv") or "",
        "severity": lower_first(SEVERITY_LV.get(c.get("severity") or "", "")),
        "topic": c.get("headline") or c.get("topic") or "",
        "d_old": lv_date_locative(old_date, with_year),
        "d_new": lv_date_locative(new_date, with_year),
        "gap": lv_gap_label(_delta_days(old_date, new_date)),
        "q_old": q_old,
        "q_new": q_new,
        "old_is_quote": old_is_quote,
        "new_is_quote": new_is_quote,
        # Garāks teksts → mazāks burts, lai ietilpst 1200×630.
        "q_size": 37 if longest <= 115 else 31 if longest <= 170 else 27,
        "url": f"atmina.lv/pretrunas/{c['id']}",
    }


def _render_og_cards(
    contradictions: list[dict[str, Any]],
    env: Environment,
    out_dir: Path,
) -> int:
    """Render 1200x630 OG preview PNGs, one per contradiction, via the shared
    incremental renderer (``_common.og_render``; manifest ``<output>/og-hashes.json``).
    Returns cards rendered."""
    tpl = env.get_template("og-card.html.j2")
    jobs = []
    for c in contradictions:
        render_c = dict(c)
        render_c["photo_data_uri"] = _photo_data_uri(c["slug"])
        jobs.append((out_dir / f"pretruna-{c['id']}.png", tpl.render(card=_og_card_context(render_c))))
    return og_render.render_og_images(jobs, out_dir.parent.parent)


def render_contradictions(
    env: Environment,
    atmina_dir: Path,
    contradictions: list[dict[str, Any]],
    all_parties: list[str],
    withdrawn: list[dict[str, Any]] | None = None,
) -> None:
    """Write pretrunas.html, per-contradiction detail pages, and OG card PNGs.

    Mirrors the inline block previously at src/generate.py lines 3145-3195.
    The fan-out (PNG render) is best-effort: count is logged.

    ``withdrawn`` (``_fetch_withdrawn_contradictions``) — atsauktās publicētās
    pretrunas; katrai tiek uzrakstīta noindex labojuma lapa tajā pašā
    ``pretrunas/`` mapē, bet tās NEietilpst ``contradictions`` sarakstā,
    skaitos vai OG kartītēs.
    """
    pretrunas_persons = sorted(
        set(c["politician_name"] for c in contradictions if c.get("politician_name"))
    )

    week_cutoff = trailing_days_cutoff(7)  # today-6 … today (LV), not 8 days
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
    # Separate map, not a key on the shared dicts: the same list feeds the
    # detail pages and OG cards.
    excerpts = {c["id"]: contradiction_excerpt_text(c.get("summary")) for c in contradictions}
    _render_page(env, "pretrunas.html.j2", atmina_dir / "pretrunas.html", {
        "contradictions": contradictions,
        "excerpts": excerpts,
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
    n_withdrawn = render_withdrawn_contradictions(env, atmina_dir, withdrawn or [])
    print(f"  pretrunas/: {n_withdrawn} atsauktas (noindex) labojuma lapas")
