"""Render the Statistika (CSP statistical data) pages.

Phase F3d (refactor-plan-2026-04-29 § Fāze 3) carve-out from
src/generate.py. Imports flow strictly from ``src.render._common`` —
no peer-module dependencies.

Outputs (independent from ``generate_public_site``; `generate_statistika`
is its own entrypoint, called manually after CSP data sync):
- ``output/atmina/statistika.html`` — dashboard with one card per CSP
  series (10 series across 4 domains: ekonomika, sociālie, cenas, valsts)
- ``output/atmina/statistika/<table_id>.html`` — detail page per CSP
  series with full chart, event annotations, raw data table

Public API: ``generate_statistika(output_dir, csp_db_path, events_path)``
— all 3 args optional, default to project_root/output, /data/csp.db,
/data/events.yaml respectively.
"""

from __future__ import annotations

import json
import logging
import sqlite3 as _sqlite3
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader

from src.csp.insights import generate_insight as csp_generate_insight
from src.csp.tables import DASHBOARD_ORDER as CSP_ORDER, TABLES as CSP_TABLES
from src.render._common import (
    PROJECT_ROOT,
    TEMPLATES_DIR,
    _autolink_bills_filter,
    _download_annotation_plugin,
    _download_chart_js,
    _render_page,
    _resolve_assets_version,
    _safe_json_filter,
    _safe_url_filter,
)

logger = logging.getLogger(__name__)


_CSP_FREQ_LABELS = {"M": "Mēnesis", "Q": "Ceturksnis", "A": "Gads"}
_CSP_DOMAIN_LABELS = {
    "economy": "Ekonomika", "social": "Sociālie",
    "prices": "Cenas", "state": "Valsts",
}
_CSP_CATEGORY_LABELS = {
    "crisis": "Krīzes", "milestone": "Pagrieziena punkti",
    "policy": "Politika", "elections": "Vēlēšanas", "government": "Valdība",
}
_CSP_CATEGORY_COLORS = {
    "crisis": "#C62828", "milestone": "#22c55e",
    "policy": "#eab308", "elections": "#90A4AE", "government": "#f97316",
}


def generate_statistika(
    output_dir: str | None = None,
    csp_db_path: str | None = None,
    events_path: str | None = None,
) -> None:
    """Generate CSP statistika pages (dashboard + 10 detail pages).

    Designed to run independently from generate_public_site().
    Call after syncing CSP data (weekly/monthly).
    """
    output_dir = output_dir or str(PROJECT_ROOT / "output")
    csp_db_path = csp_db_path or str(PROJECT_ROOT / "data" / "csp.db")
    events_path = events_path or str(PROJECT_ROOT / "data" / "events.yaml")

    atmina_dir = Path(output_dir) / "atmina"
    stat_dir = atmina_dir / "statistika"
    stat_dir.mkdir(parents=True, exist_ok=True)

    # Ensure assets exist (chart.js + annotation plugin)
    assets_dir = atmina_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    chart_js = assets_dir / "chart.min.js"
    if not chart_js.exists():
        _download_chart_js(chart_js)
    annotation_js = assets_dir / "chartjs-plugin-annotation.min.js"
    if not annotation_js.exists():
        _download_annotation_plugin(annotation_js)

    csp_conn = _sqlite3.connect(csp_db_path)
    csp_conn.row_factory = _sqlite3.Row

    # Load events
    events = []
    ep = Path(events_path)
    if ep.exists():
        events = yaml.safe_load(ep.read_text(encoding="utf-8")).get("events", [])

    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=True,
    )
    env.filters["safe_json"] = _safe_json_filter
    env.filters["safe_url"] = _safe_url_filter
    env.filters["autolink_bills"] = _autolink_bills_filter
    env.globals["assets_version"] = _resolve_assets_version()

    # ── Helper functions (local) ──

    def _period_to_label(period: str) -> str:
        if "M" in period:
            parts = period.split("M")
            return f"{parts[0]}-{parts[1]}"
        if "Q" in period:
            parts = period.split("Q")
            return f"{parts[0]} Q{parts[1]}"
        return period

    def _get_data(table_id: str) -> list[dict]:
        rows = csp_conn.execute(
            "SELECT period, value FROM csp_data WHERE table_id=? AND geo='LV' ORDER BY period",
            (table_id,),
        ).fetchall()
        return [{"period": r[0], "value": r[1]} for r in rows]

    def _compute_change(latest, prev, trend_dir):
        result = {"change": None, "formatted": "", "positive": True}
        if not prev or prev.get("value") is None or latest.get("value") is None:
            return result
        diff = latest["value"] - prev["value"]
        if prev["value"] != 0:
            pct = (diff / abs(prev["value"])) * 100
            result["formatted"] = f"{pct:+.1f}%"
        else:
            result["formatted"] = f"{diff:+.1f}"
        result["change"] = diff
        if trend_dir == "higher_is_better":
            result["positive"] = diff >= 0
        elif trend_dir == "lower_is_better":
            result["positive"] = diff <= 0
        else:
            result["positive"] = True
        return result

    def _event_to_period_label(event_date, freq):
        year, month = event_date[:4], event_date[5:7]
        if freq == "M":
            return f"{year}-{month}"
        if freq == "Q":
            q = (int(month) - 1) // 3 + 1
            return f"{year} Q{q}"
        return year

    def _event_applies(event, table_id):
        tables = event.get("tables", "all")
        if tables == "all" or tables is None:
            return True
        if isinstance(tables, list):
            return table_id in tables
        return False

    def _date_label(d, freq):
        if freq == "M":
            return d[:7]
        if freq == "Q":
            q = (int(d[5:7]) - 1) // 3 + 1
            return f"{d[:4]} Q{q}"
        return d[:4]

    def _range_str(rows, _freq):
        if not rows:
            return ""
        first = _period_to_label(rows[0]["period"])
        last = _period_to_label(rows[-1]["period"])
        try:
            years = int(rows[-1]["period"][:4]) - int(rows[0]["period"][:4]) + 1
            return f"{first} → {last} · {years} g."
        except Exception:
            return f"{first} → {last}"

    def _build_events(table_id, freq, chart_labels_set):
        applicable = [e for e in events if _event_applies(e, table_id)]
        mapped = []
        for evt in applicable:
            pl = _event_to_period_label(evt["date"], freq)
            if pl not in chart_labels_set:
                continue
            cat = evt.get("category", "milestone")
            mapped.append({
                "label": pl, "text": evt["label"],
                "date_label": _date_label(evt["date"], freq),
                "category": cat,
                "color": _CSP_CATEGORY_COLORS.get(cat, "#90A4AE"),
            })
        mapped.sort(key=lambda e: e["label"])
        for i, m in enumerate(mapped):
            m["idx"] = i
        cat_counts: dict[str, int] = {}
        for m in mapped:
            cat_counts[m["category"]] = cat_counts.get(m["category"], 0) + 1
        event_categories = [
            {"id": c, "label": _CSP_CATEGORY_LABELS.get(c, c.title()), "count": n}
            for c, n in sorted(cat_counts.items(), key=lambda x: -x[1])
        ]
        events_json_data = [
            {"label": m["label"], "text": m["text"], "category": m["category"]}
            for m in mapped
        ]
        return {"events_list": mapped, "events_json_data": events_json_data, "event_categories": event_categories}

    # ── Dashboard ──

    cards = []
    for i, table_id in enumerate(CSP_ORDER):
        cfg = CSP_TABLES[table_id]
        rows = _get_data(table_id)
        if not rows:
            continue
        latest, prev = rows[-1], rows[-2] if len(rows) >= 2 else None
        change = _compute_change(latest, prev, cfg["trend_direction"])
        values_tuples = [(r["period"], r["value"]) for r in rows if r["value"] is not None]
        insight = csp_generate_insight(values_tuples, cfg["trend_direction"])
        spark = rows[-24:]
        meta_row = csp_conn.execute(
            "SELECT csp_updated FROM csp_metadata WHERE table_id=?", (table_id,)
        ).fetchone()
        csp_updated_short = (meta_row[0] or "")[:10] if meta_row and meta_row[0] else ""
        cards.append({
            "table_id": table_id, "label": cfg["label"], "domain": cfg["domain"],
            "formatted_value": cfg["format_short"](latest["value"]),
            "change": change["change"], "change_positive": change["positive"],
            "formatted_change": change["formatted"],
            "insight": insight,
            "sparkline_labels": [_period_to_label(r["period"]) for r in spark],
            "sparkline_values": [r["value"] for r in spark],
            "csp_updated_short": csp_updated_short,
            "index": i,
        })

    last_updated = max((c["csp_updated_short"] for c in cards if c["csp_updated_short"]), default="")
    cards_json = json.dumps(
        [{k: v for k, v in c.items() if k != "change_positive"} for c in cards],
        ensure_ascii=False,
    )

    _render_page(env, "statistika.html.j2", atmina_dir / "statistika.html", {
        "cards": cards, "cards_json": cards_json, "last_updated": last_updated,
    })
    logger.info("Generated statistika dashboard with %d cards", len(cards))

    # ── Detail pages ──

    for table_id in CSP_ORDER:
        cfg = CSP_TABLES[table_id]
        rows = _get_data(table_id)
        if not rows:
            continue

        meta_row = csp_conn.execute("SELECT * FROM csp_metadata WHERE table_id=?", (table_id,)).fetchone()
        meta = dict(meta_row) if meta_row else {}
        meta["freq_label"] = _CSP_FREQ_LABELS.get(cfg["freq"], cfg["freq"])
        meta["domain"] = cfg["domain"]
        meta["domain_label"] = _CSP_DOMAIN_LABELS.get(cfg["domain"], cfg["domain"])
        meta["label_lv"] = cfg["label"]
        meta["unit"] = cfg["unit"]
        meta["range_str"] = _range_str(rows, cfg["freq"])
        meta["csp_updated_short"] = (meta.get("csp_updated") or "")[:10]

        latest_row, prev_row = rows[-1], rows[-2] if len(rows) >= 2 else None
        change = _compute_change(latest_row, prev_row, cfg["trend_direction"])
        latest = {
            "formatted": cfg["format_value"](latest_row["value"]),
            "change_formatted": change["formatted"],
            "change_positive": change["positive"],
        }

        labels = [_period_to_label(r["period"]) for r in rows]
        values = [r["value"] for r in rows]

        evt_ctx = _build_events(table_id, cfg["freq"], set(labels))

        # Kombinēts JSON bloks CSP-drošam ārējam skriptam (stv1.js):
        # {"chart": {...}, "events": [...], "domain": "..."} — grafiks,
        # notikumu anotācijas un domēna krāsa vienā <script type=json> blokā.
        detail_json = json.dumps(
            {
                "chart": {"labels": labels, "values": values, "label": cfg["label"]},
                "events": evt_ctx["events_json_data"],
                "domain": cfg["domain"],
            },
            ensure_ascii=False,
        )

        values_tuples = [(r["period"], r["value"]) for r in rows if r["value"] is not None]
        insight = csp_generate_insight(values_tuples, cfg["trend_direction"])

        fmt = cfg["format_value"]
        data_rows = [
            {"period": _period_to_label(r["period"]),
             "formatted": fmt(r["value"]) if r["value"] is not None else "..."}
            for r in reversed(rows)
        ]

        _render_page(env, "statistika-detail.html.j2", stat_dir / f"{table_id}.html", {
            "meta": meta, "latest": latest, "detail_json": detail_json,
            "events_list": evt_ctx["events_list"],
            "event_categories": evt_ctx["event_categories"],
            "insight": insight, "data_rows": data_rows,
        })
        logger.info("Generated statistika detail: %s (%d events)", table_id, len(evt_ctx["events_list"]))

    csp_conn.close()
    logger.info("Statistika generation complete → %s", stat_dir)
