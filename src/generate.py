"""src.generate — re-export shim.

Phase F3g (refactor-plan-2026-04-29 § Fāze 3) closure: the renderer
now lives at ``src.render``. ``src.generate`` is preserved as a
thin re-export shim so historical imports remain valid:

- ``from src.generate import generate_public_site`` (canonical pre-F3g)
- ``from src.generate import _fetch_x_data`` (private helpers used by
  tests and a handful of agents/scripts)
- ``from src.generate import generate_statistika`` (CSP dashboard)

The canonical public path is now ``from src.render import
generate_public_site``. New code should prefer it. Existing imports
from ``src.generate`` keep working through the shim widening below;
each sub-page module is the source of truth for its own helpers.
"""

# Re-exports from src.render — public entry-points and sitemap/og helpers.
from src.render import (  # noqa: F401  re-exported for shim contract
    _generate_og_image,
    _generate_sitemap,
    generate_public_site,
    generate_statistika,
)

# Re-exports from src.render._common — leaf helpers + constants.
from src.render._common import (  # noqa: F401  re-exported for shim contract
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
    WIKI_DIR,
    _BILL_REF_RE,
    _BRACKET_RE,
    _LV_OFFSET_HOURS,
    _LV_TRANS,
    _PARTY_LOWERCASE_WORDS,
    _SAFE_HTML_ATTRS,
    _SAFE_HTML_TAGS,
    _SEVERITY_GLYPHS,
    _autolink_bills_filter,
    _bill_slug,
    _confidence_tier,
    _date_sort_key,
    _delta_days,
    _domain_from_url,
    _download_annotation_plugin,
    _download_chart_js,
    _enrich_contradiction,
    _format_tweet_time,
    _get_last_activity,
    _initials_from_name,
    _latvian_quotes,
    _load_wiki_profile,
    _normalize_date,
    _parse_frontmatter,
    _persona_category,
    _photo_data_uri,
    _party_short_name,
    _render_page,
    _resolve_assets_version,
    _safe_json_filter,
    _safe_url_filter,
    _sanitize_html,
    _slugify,
    _source_to_internal_link,
    _split_summary,
    _titlecase_party_name,
)

# Re-exports from each sub-page module.
from src.render.contradictions import (  # noqa: F401
    _fetch_contradictions,
    _render_og_cards,
    render_contradictions,
)
from src.render.politicians import (  # noqa: F401
    _fetch_commentary_about,
    _fetch_politician_detail,
    _fetch_politicians,
    render_politicians,
)
from src.render.personas import (  # noqa: F401
    _fetch_personas,
    _fetch_personas_metrics,
    render_personas,
)
from src.render.parties import (  # noqa: F401
    _fetch_parties_page,
    _fetch_party_detail,
    render_parties,
)
from src.render.positions import (  # noqa: F401
    PZV1_TOPIC_COLORS,
    _fetch_claims,
    _fetch_pozicijas_metrics,
    render_positions,
)
from src.render.news import (  # noqa: F401
    _fetch_news,
    render_news,
)
from src.render.bills import (  # noqa: F401
    _fetch_bill_detail,
    _fetch_bills,
    _generate_bill_pages,
    _get_law_titles,
    render_bills,
)
from src.render.laws import (  # noqa: F401
    _LAW_BODY_STRIP_RE,
    _LAW_LIKUMI_LV_RE,
    _fetch_law_index_page,
    _fetch_law_pages,
    _generate_law_pages,
    render_laws,
)
from src.render.votes import (  # noqa: F401
    _build_matrix_data,
    _enrich_faction_breakdown,
    _fetch_votes,
    render_votes,
)
from src.render.x import (  # noqa: F401
    _fetch_x_data,
    render_x,
)
from src.render.tensions import (  # noqa: F401
    _fetch_tensions,
    render_tensions,
)
from src.render.links import (  # noqa: F401
    _fetch_graph_data,
    render_links,
)
from src.render.analyses import (  # noqa: F401
    _load_analyses,
    render_analyses,
)
from src.render.syntheses import (  # noqa: F401
    _load_syntheses,
    _map_syntheses_to_politicians,
    render_syntheses,
)
from src.render.blog import (  # noqa: F401
    _fetch_blog_posts,
    _fetch_context_notes,
    _rewrite_shortener_link_labels,
    render_blog,
)
from src.render.dashboard import (  # noqa: F401
    _fetch_hero_v2_data,
    _fetch_stats,
    _fetch_trends_data,
    _sparkline_svg,
    render_dashboard,
)


# CLI entry point — preserves `python -m src.generate` and
# `python src/generate.py` invocations.
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    generate_public_site()
