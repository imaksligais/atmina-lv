"""``_common`` konstantes — ceļu saknes, krāsu/etiķešu tabulas, SQL palīgs.

Izgriezts no vienfaila ``src/render/_common.py`` 2026-09-05 (strukturas
plāna 5.8). Šis ir pakotnes dziļākais lapu-modulis: importē tikai stdlib +
``src.db`` / ``src.lv_text``, nekad nevienu māsu-moduli ``src.render.*``
(``src/render/__init__.py:22-30`` daļējās inicializācijas līgums).
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

from src.db import LV_OFFSET
from src.lv_text import LV_TRANS

# Logger nosaukums pieķīlēts pie pakotnes, NE pie ``__name__`` — pirms
# 2026-09-05 sadalīšanas šis bija ``src.render._common``, un log-ierakstu
# vārdi ir vienīgais, ko sadalīšana nedrīkst mainīt.
_logger = logging.getLogger("src.render._common")


# ── Path roots ──────────────────────────────────────────────────────

# Četri ``.parent`` soļi, ne trīs: fails dzīvo ``src/render/_common/constants.py``
# (viens līmenis dziļāk nekā bijušais ``src/render/_common.py``).
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

DEFAULT_DB_PATH = str(PROJECT_ROOT / "data" / "atmina.db")
DEFAULT_OUTPUT_DIR = str(PROJECT_ROOT / "output")
TEMPLATES_DIR = str(PROJECT_ROOT / "templates")
ASSETS_DIR = PROJECT_ROOT / "assets"
WIKI_DIR = PROJECT_ROOT / "wiki"
CONTENT_DIR = PROJECT_ROOT / "content"


# ── Site-wide constants ─────────────────────────────────────────────

BASE_URL = "https://atmina.lv"

ELECTION_DATE = date(2026, 10, 3)


def norm_source_domain_sql(col: str = "d.source_domain") -> str:
    """SQL izteiksme, kas nostrippo ``www.`` priedēkli no source_domain, lai
    dokumentus grupētu pēc normalizēta hosta. Vienots avots — agrāk inline
    ``src/render/mediji.py``, tagad to importē arī politicians.py own_pubs
    vaicājums. ``col`` ļauj norādīt citu aliasa kvalifikāciju, defaults
    ``d.source_domain``."""
    return (f"CASE WHEN {col} LIKE 'www.%' THEN substr({col}, 5) "
            f"ELSE lower({col}) END")

PARTY_COLORS = {
    'Jaunā Vienotība': '#3b82f6', 'Zaļo un Zemnieku savienība': '#84cc16',
    'Nacionālā apvienība': '#22c55e', 'Progresīvie': '#a855f7',
    'Latvija Pirmajā Vietā': '#ef4444', 'Apvienotais saraksts': '#06b6d4',
    'Stabilitātei!': '#f97316', 'MMN': '#f97316', 'Latvijas attīstībai': '#14b8a6',
}

# 33 canonical topic groups (topic_map.TOPIC_GROUPS keys) → chip colors.
# Single source of truth, promoted here from positions.py so both the
# Pozīcijas feed (``positions.PZV1_TOPIC_COLORS`` alias) and the Tēmas
# destination pages (``topics.py``) share one map without a sibling
# import (F4 leaf rule). First 16 entries match the handoff palette
# (atmina-handoff/…/pozicijas-data.jsx); next 10 are HSL-derived (L=62%,
# S=52%) at 36° intervals, avoiding PARTY_COLORS; last 5 added 2026-04-25
# for the new canonical topics (semantic affinity, distinct from
# PARTY_COLORS and the existing 26).
TOPIC_COLORS: dict[str, str] = {
    "Aizsardzība un drošība":      "#dc2626",
    "airBaltic":                   "#2563eb",
    "Koalīcija un partijas":       "#a856f7",
    "Ukraina un Krievija":         "#eab308",
    "Valsts pārvalde":             "#64748b",
    "Ārpolitika":                  "#0891b2",
    "Vēlēšanas":                   "#ec4899",
    "Degviela un enerģētika":      "#f97317",
    "Tieslietas":                  "#16a34a",
    "Budžets un finanses":         "#85cc16",   # #84cc16 clashes with ZZS party color
    "Pašvaldības":                 "#06b6d5",   # #06b6d4 clashes with AS party color
    "Imigrācija":                  "#d946ef",
    "Transports":                  "#15b8a6",   # #14b8a6 clashes with LA party color
    "Sabiedriskie mediji":         "#f43f5e",
    "Droni":                       "#6366f1",
    "Sociālā politika":            "#8b5cf6",
    # handoff palette ends here — next 10 derived HSL rotation
    "ES politika":                 "#e17055",
    "Rail Baltica":                "#b89a5b",
    "Mežsaimniecība":              "#6b8e4e",
    "Valsts kapitālsabiedrības":   "#4fa58a",
    "Izglītība":                   "#5b8fb8",
    "Valodu politika":             "#7a6fb8",
    "Vide":                        "#b85b8f",
    "Pensijas":                    "#b87a5b",
    "Lauksaimniecība":             "#8fa55b",
    "Kultūra":                     "#5bb88e",
    # 2026-04-25 — 5 new canonical topics
    "Klimats":                     "#5b8eb8",   # sky-atmosphere blue
    "Veselības aprūpe":            "#5b9b8e",   # medical teal (avoids LA #14b8a6)
    "Pilsētvide":                  "#708090",   # slate, urban
    "Korupcija un KNAB":           "#6b5b8e",   # weighty deep purple
    "Digitālā politika":           "#5bb8b8",   # cyan-tech (avoids AS #06b6d4)
    # 2026-07-04 — 32. kanoniskā tēma
    "Sports":                      "#c9803d",   # medal bronze (avoids Degviela #f97317, Rail Baltica #b89a5b)
    # 2026-08-06 — 33. kanoniskā tēma
    "NVO un pilsoniskā sabiedrība": "#8e6b4f",  # zemes brūns, grassroots (avoids Pensijas #b87a5b, Rail Baltica #b89a5b)
}

SEVERITY_LV = {
    "direct_contradiction": "Tieša pretruna",
    "reversal": "Apvērsums",
    "minor_shift": "Pozīcijas maiņa",
}

# Category derived from claim_type pair. Canonical key: sorted types joined by "_".
# Drives the main badge text on OG cards, pretrunas list, detail page, politician page.
CATEGORY_LV = {
    "position_position": "Pozīcijas maiņa",
    "position_saeima_vote": "Vārdi vs. Darbi",
    "saeima_vote_saeima_vote": "Balsojuma maiņa",
}

# Label for a single claim panel when the pair is mixed-type.
# For same-type pairs we fall back to chronological "Iepriekš" / "Pašlaik".
CLAIM_TYPE_LABEL = {
    "position": "Vārdi",
    "saeima_vote": "Darbi",
}

_SEVERITY_GLYPHS: dict[str, str] = {
    "direct_contradiction": "⇄",
    "reversal": "↺",
    "minor_shift": "≈",
}

# Vēsturiskais privātais nosaukums. Tabula dzīvoja te līdz 2026-09-05 (plāna
# 4.3); `src/render/*` un testi to importē no šejienes, tāpēc alias paliek.
# Vienīgā definīcija: `src/lv_text.py`.
_LV_TRANS = LV_TRANS

# Tweet timestamps render in Latvia time so the X feed shows real post times.
# Derived from the single definition in src.db — not re-typed. The DST switch
# then lands in one file instead of six (2026-08-15 consolidation).
_LV_OFFSET_HOURS = int(LV_OFFSET.total_seconds() // 3600)

# Conjunctions that stay lowercase in title-cased party names unless
# they're the first word (e.g. "Zaļo un Zemnieku savienība").
_PARTY_LOWERCASE_WORDS = {"un"}

