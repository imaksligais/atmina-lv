"""Deterministic weekly movers chart as hand-rolled SVG.

No matplotlib (not in the default venv — see tests/conftest.py). The chart is
DATA, not creative work: it never enters the brief_images approval loop. The
caller writes the returned bytes to output/images/briefs/<date>-nedelas-movers.svg
and references it from the markdown via <img>/![]().

Palette: cream background, ink-navy bars (weekly chrome accent). Delta labels
use ASCII +/- (not Unicode arrows — the SVG serif font drops U+2191/2193, which
rendered "↑6" as a bare "6").
"""
from __future__ import annotations

from xml.sax.saxutils import escape

_CREAM = "#f4efe4"
_NAVY = "#1f2d4d"
_OPP = "#b9402f"
_INK = "#222222"
_POS = "#2e7d32"   # delta up (green)
_NEG = "#b9402f"   # delta down (red)
_MUTE = "#777777"  # delta zero / no baseline
_W = 760
_ROW_H = 34
_PAD = 16
_LABEL_W = 210     # label column width; bars start here
_BAR_MAX = 420

# Minimal party short-codes; fallback truncates the raw party name.
_PARTY_SHORT = {
    "Jaunā Vienotība": "JV", "Nacionālā apvienība": "NA", "Progresīvie": "PRO",
    "Apvienotais saraksts": "AS", "Zaļo un Zemnieku savienība": "ZZS",
    "Latvija Pirmajā Vietā": "LPV", "Stabilitātei!": "S!", "Bezpartejisks": "Bezp.",
}


def _short_party(party: str | None) -> str:
    if not party:
        return "—"
    return _PARTY_SHORT.get(party, party[:5])


def _label(m: dict) -> str:
    """Surname + party short-code, e.g. 'Kulbergs (AS)'."""
    name = (m.get("name") or "").strip()
    surname = name.split()[-1] if name else "—"
    return f"{surname} ({_short_party(m.get('party'))})"


def _delta(d):
    """Return (text, colour) for a delta value. ASCII only."""
    if d == "jauns":
        return "jauns", _MUTE
    if isinstance(d, int) and d > 0:
        return f"+{d}", _POS
    if isinstance(d, int) and d < 0:
        return f"-{abs(d)}", _NEG
    return "—", _MUTE


def make_movers_svg(movers: list[dict], coalition: dict[str, int]) -> bytes:
    """Render a horizontal-bar movers chart. `movers` = list of
    {name, party, count, delta}. `coalition` = {"coalition": n, "opposition": n}."""
    rows = movers[:6]
    chart_h = _PAD * 2 + max(1, len(rows)) * _ROW_H + 72  # + strip + legend
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        # width/height attrs (not viewBox alone) give the SVG intrinsic
        # dimensions. Without them WebKit/Safari treats an <img>'d viewBox-only
        # SVG as 0×0, so under `.weekly-body img { width:100% }` the layout box
        # collapses while the SVG still paints full-size — overlapping the
        # movers list below it (the "Kas kustējās" desktop bug). Chromium
        # tolerates viewBox-only; Safari does not.
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {_W} {chart_h}" '
        f'width="{_W}" height="{chart_h}" font-family="Georgia, serif">',
        f'<rect width="{_W}" height="{chart_h}" fill="{_CREAM}"/>',
    ]
    if not rows:
        parts.append(f'<text x="{_W / 2}" y="{chart_h / 2}" text-anchor="middle" '
                     f'fill="{_INK}" font-size="18">Nav datu</text>')
    else:
        max_count = max(m["count"] for m in rows) or 1
        for i, m in enumerate(rows):
            y = _PAD + i * _ROW_H
            bar_w = int(_BAR_MAX * m["count"] / max_count)
            parts.append(f'<text x="{_PAD}" y="{y + 20}" fill="{_INK}" '
                         f'font-size="15">{escape(_label(m))}</text>')
            parts.append(f'<rect class="bar" x="{_LABEL_W}" y="{y + 6}" '
                         f'width="{bar_w}" height="20" rx="2" fill="{_NAVY}"/>')
            dtext, dcol = _delta(m["delta"])
            parts.append(f'<text x="{_LABEL_W + bar_w + 8}" y="{y + 21}" '
                         f'fill="{_INK}" font-size="14" font-weight="bold">{m["count"]}</text>')
            parts.append(f'<text x="{_LABEL_W + bar_w + 8 + 11 * len(str(m["count"]))}" '
                         f'y="{y + 21}" fill="{dcol}" font-size="13">{dtext}</text>')
        # coalition vs opposition strip
        total = (coalition.get("coalition", 0) + coalition.get("opposition", 0)) or 1
        sy = _PAD + len(rows) * _ROW_H + 18
        coal_w = int(_BAR_MAX * coalition.get("coalition", 0) / total)
        parts.append(f'<text x="{_PAD}" y="{sy + 14}" fill="{_INK}" font-size="13">'
                     f'Koalīcija / Opozīcija</text>')
        parts.append(f'<rect x="{_LABEL_W}" y="{sy}" width="{coal_w}" height="18" fill="{_NAVY}"/>')
        parts.append(f'<rect x="{_LABEL_W + coal_w}" y="{sy}" width="{_BAR_MAX - coal_w}" '
                     f'height="18" fill="{_OPP}"/>')
        # legend
        ly = sy + 36
        parts.append(f'<rect x="{_LABEL_W}" y="{ly - 10}" width="11" height="11" fill="{_NAVY}"/>')
        parts.append(f'<text x="{_LABEL_W + 16}" y="{ly}" fill="{_INK}" font-size="12">Koalīcija</text>')
        parts.append(f'<rect x="{_LABEL_W + 100}" y="{ly - 10}" width="11" height="11" fill="{_OPP}"/>')
        parts.append(f'<text x="{_LABEL_W + 116}" y="{ly}" fill="{_INK}" font-size="12">Opozīcija</text>')
    parts.append("</svg>")
    return "\n".join(parts).encode("utf-8")
