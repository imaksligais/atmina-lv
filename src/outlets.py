"""Read media-outlet definitions from sources.yaml.

Outlets are a config-driven entity (no DB table): the registry lives in
sources.yaml alongside the scraper source feeds. Each feed row may carry an
``outlet: <short_name>`` tag grouping it under an outlet; outlet identity +
sourced transparency facts live in a top-level ``outlets:`` block.

Pure read — mirrors how sources.yaml already seeds the ``sources`` table.
Transparency facts without a ``source_url`` are dropped, mirroring the claims
"no source_url -> dropped" provenance rule (CLAUDE.md Data Contract #2).
x_feeds saraksta X kontus (tracked org-feedus), kas pieder outletam — savienojums uz social_accounts.handle.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

SOURCES_YAML = Path(__file__).resolve().parent.parent / "sources.yaml"

# Controlled vocabularies — symmetry: the same field set for every outlet.
OUTLET_TYPES = ("public_tv", "private_tv", "radio", "print", "agency", "online", "official")
OUTLET_FACT_FIELDS = (
    "owner", "funding_model", "legal_form", "editorial_leadership", "founded",
)

# Publiskās LV etiķetes badge/chip virsmām; wiki/mediji.md paliek pie kodiem.
TYPE_LABELS = {
    "public_tv": "sabiedriskais medijs",
    "private_tv": "komerctelevīzija",
    "radio": "radio",
    "print": "drukātā prese",
    "agency": "ziņu aģentūra",
    "online": "interneta portāls",
    "official": "oficiālais izdevējs",
}


def _normalize_host(host: str) -> str:
    host = (host or "").strip().lower()
    return host[4:] if host.startswith("www.") else host


def load_outlets(path: str | Path = SOURCES_YAML) -> list[dict[str, Any]]:
    """Return outlets sorted by display name. Empty list if file/section absent."""
    p = Path(path)
    if not p.exists():
        return []
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}

    feeds_by_outlet: dict[str, list[str]] = {}
    for s in data.get("sources") or []:
        tag = s.get("outlet")
        if tag:
            feeds_by_outlet.setdefault(tag, []).append(s.get("url"))

    outlets: list[dict[str, Any]] = []
    for o in data.get("outlets") or []:
        short = o["short_name"]
        # de-dupe normalized hosts, preserving order
        seen: dict[str, None] = {}
        for h in (o.get("hosts") or []):
            nh = _normalize_host(h)
            if nh:
                seen.setdefault(nh, None)
        hosts = list(seen)
        facts = [
            {"field": f["field"], "value": f["value"],
             "source_url": f["source_url"], "as_of": f.get("as_of")}
            for f in (o.get("facts") or [])
            if f.get("field") in OUTLET_FACT_FIELDS and f.get("value") and f.get("source_url")
        ]
        outlets.append({
            "short_name": short,
            "slug": short.lower(),
            "name": o.get("name") or short,
            "type": o.get("type"),
            "type_label": TYPE_LABELS.get(o.get("type"), o.get("type") or ""),
            "language": o.get("language") or "lv",
            "hosts": hosts,
            "x_handle": o.get("x_handle"),
            "x_feeds": [str(h).strip().lstrip("@")
                        for h in (o.get("x_feeds") or [])
                        if str(h).strip().lstrip("@")],
            "website": o.get("website"),
            "description": o.get("description") or "",
            "volume_label": o.get("volume_label") or "raksti",
            "facts": facts,
            "feed_urls": feeds_by_outlet.get(short, []),
        })
    outlets.sort(key=lambda o: o["name"].lower())
    return outlets


def host_to_outlet(outlets: list[dict[str, Any]]) -> dict[str, str]:
    """Map normalized host -> outlet short_name."""
    m: dict[str, str] = {}
    for o in outlets:
        for h in o["hosts"]:
            m[h] = o["short_name"]
    return m
