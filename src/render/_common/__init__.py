"""Shared rendering helpers — leaf package for src/render/.

Phase F3a (refactor-plan-2026-04-29 § Fāze 3) carve-out from src/generate.py.
Hosts constants, security filters, slug/format helpers, and cross-page
domain enrichment that any sub-page renderer in src/render/ may import.

**Architectural rule (F4 lesson):** _common imports nothing from
src.render.* — it is the leaf. Sub-page modules (e.g. contradictions.py)
import from _common but never from each other. If two sub-pages share a
helper, promote it here.

Canonical import path is ``from src.render._common import _slugify``
(``PARTY_COLORS``, …). The historical ``src/generate.py`` re-export
shim was retired 2026-09-05 (strukturas plāna 5.10).

**2026-09-05 (strukturas plāna 5.8):** bijušais 1322-rindu ``_common.py``
kļuva par pakotni ``_common/`` ar septiņiem lapu-apakšmoduļiem
(``constants``, ``filters``, ``slugs``, ``dates``, ``text``, ``enrich``,
``assets``). Neviens importa ceļš nemainījās — šis ``__init__`` re-eksportē
VISU bijušo moduļa vārdtelpu 1:1, tāpēc 25 esošie
``from src.render._common import …`` izsaukumi paliek neskarti.

**Daļējās inicializācijas līgums (``src/render/__init__.py:22-30``):**
apakšmoduļi tiek importēti atkarību secībā (constants → filters/slugs/dates/
text → enrich → assets), un neviens no tiem neimportē māsu-moduli
``src.render.<page>``. Tāpēc, kad ``_orchestrator`` puslādētā stāvoklī
meklē kādu ``_common`` simbolu, tas jau ir definēts.
"""

from __future__ import annotations

# ── Vēsturiskā moduļa vārdtelpa ─────────────────────────────────────
# Pirms sadalīšanas ``_common.py`` bija viens fails, tāpēc tā vārdtelpā
# dzīvoja arī importētie moduļi un tipi (``re``, ``json``, ``Path``,
# ``Markup``, ``ProfileKind``, ``slugify``, …). Daļa no tiem ir apzināti
# re-eksporti (``ProfileKind``/``derive_profile_kind`` — F4 lapu-noteikums;
# ``LV_TRANS``/``slugify`` — ``src/lv_text.py`` vienīgā definīcija;
# ``lookup_party_short_name`` — T6 patiesības avots), pārējie ir vēsturiskā
# virsma, ko sadalīšana nedrīkst klusi noņemt. Tāpēc tie tiek atjaunoti šeit
# tieši tādi paši, un pirms/pēc ``dir()`` saraksti sakrīt.
import gzip as _gzip  # noqa: F401  vēsturiskā vārdtelpa
import json  # noqa: F401  vēsturiskā vārdtelpa
import logging  # noqa: F401  vēsturiskā vārdtelpa
import os  # noqa: F401  vēsturiskā vārdtelpa
import re  # noqa: F401  vēsturiskā vārdtelpa
import sqlite3  # noqa: F401  vēsturiskā vārdtelpa
import sys  # noqa: F401  vēsturiskā vārdtelpa
from datetime import date, datetime, timedelta, timezone  # noqa: F401  vēsturiskā vārdtelpa
from pathlib import Path  # noqa: F401  vēsturiskā vārdtelpa
from typing import Any, Optional  # noqa: F401  vēsturiskā vārdtelpa
from urllib.parse import quote as _quote, urlparse  # noqa: F401  vēsturiskā vārdtelpa

import bleach  # noqa: F401  vēsturiskā vārdtelpa
import brotli as _brotli  # noqa: F401  vēsturiskā vārdtelpa
import markdown  # noqa: F401  vēsturiskā vārdtelpa
import yaml  # noqa: F401  vēsturiskā vārdtelpa
from jinja2 import Environment  # noqa: F401  vēsturiskā vārdtelpa
from markupsafe import Markup  # noqa: F401  vēsturiskā vārdtelpa

from src.db import LV_OFFSET  # noqa: F401  vēsturiskā vārdtelpa

# Re-export from src.profile_kind so sub-page renderers (politicians.py
# under F4 leaf rule) import everything domain-related through _common.
from src.coalition import lookup_party_short_name  # noqa: F401  re-eksports
from src.profile_kind import ProfileKind, derive_profile_kind  # noqa: F401
# Leaf modulis ārpus `src.render.*` — neapdraud `src/render/__init__.py:22-30`
# daļējās inicializācijas līgumu (aizliegti ir TIKAI māsu-moduļu importi).
from src.lv_text import LV_TRANS, slugify  # noqa: F401  re-eksports

# ── Apakšmoduļi atkarību secībā ─────────────────────────────────────
# 1) constants — nekādu pakotnes iekšējo atkarību.
from src.render._common.constants import (  # noqa: F401  re-eksportēts
    ASSETS_DIR,
    BASE_URL,
    CATEGORY_LV,
    CLAIM_TYPE_LABEL,
    CONTENT_DIR,
    DEFAULT_DB_PATH,
    DEFAULT_OUTPUT_DIR,
    ELECTION_DATE,
    PARTY_COLORS,
    PROJECT_ROOT,
    SEVERITY_LV,
    TEMPLATES_DIR,
    TOPIC_COLORS,
    WIKI_DIR,
    _LV_OFFSET_HOURS,
    _LV_TRANS,
    _PARTY_LOWERCASE_WORDS,
    _SEVERITY_GLYPHS,
    _logger,
    norm_source_domain_sql,
)

# 2) filters / slugs / dates / text — atkarīgi tikai no constants (vai neko).
from src.render._common.filters import (  # noqa: F401  re-eksportēts
    _BILL_REF_RE,
    _CLAIM_ID_RE,
    _SAFE_HTML_ATTRS,
    _SAFE_HTML_TAGS,
    _autolink_bills_filter,
    _clean_context_note,
    _load_wiki_profile,
    _lv_plural,
    _salience_label,
    _parse_frontmatter,
    _safe_json_filter,
    _safe_url_filter,
    _sanitize_html,
    _wrap_tables,
)
from src.render._common.slugs import (  # noqa: F401  re-eksportēts
    _bill_slug,
    _outlet_feed_map,
    _party_page_slug,
    _party_short_name,
    _persona_category,
    _slugify,
    _split_org_category,
    _topic_page_href,
)
from src.render._common.dates import (  # noqa: F401  re-eksportēts
    _confidence_tier,
    _date_sort_key,
    _delta_days,
    _domain_from_url,
    _domain_label,
    _format_tweet_time,
    _initials_from_name,
    _normalize_date,
    _titlecase_party_name,
)
from src.render._common.text import (  # noqa: F401  re-eksportēts
    _BRACKET_RE,
    _CLAUSE_PUNCT,
    _SENTENCE_SPLIT_RE,
    _clause_truncate,
    _latvian_quotes,
    _normalize_ws,
    _split_summary,
    hero_excerpt,
)

# 3) enrich — DB klasteris; patērē constants + slugs + dates + text.
from src.render._common.enrich import (  # noqa: F401  re-eksportēts
    _activity_display_date,
    _enrich_contradiction,
    _get_last_activity,
    _source_to_internal_link,
    vote_alignment_data,
)

# 4) assets — patērē constants (ASSETS_DIR, BASE_URL, _logger).
from src.render._common.assets import (  # noqa: F401  re-eksportēts
    _download_annotation_plugin,
    _download_chart_js,
    _download_d3,
    _emit_json_compressed,
    _photo_data_uri,
    _render_page,
    _resolve_assets_version,
)
