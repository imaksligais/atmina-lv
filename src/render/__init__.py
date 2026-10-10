"""src.render — public-site rendering package.

Phase F3g (refactor-plan-2026-04-29 § Fāze 3) closure: the package
now owns ``generate_public_site`` and is the canonical public path
for the site renderer. Re-exports from ``_orchestrator``.

Public contract: ``from src.render import generate_public_site``.

Sub-modules:
- ``_common`` — leaf PACKAGE (``_common/``, split 2026-09-05, plāna 5.8):
  constants, Jinja filters, slug helpers, ``_enrich_contradiction``,
  ``_render_page``. Its ``__init__`` re-exports the whole historical
  namespace, so ``from src.render._common import X`` is unchanged. No
  sub-page (``src.render.<page>``) imports anywhere inside it.
- ``_orchestrator`` — owns ``generate_public_site`` + ``_generate_sitemap``
  + ``_generate_og_image``. Imports ``_common`` and every sub-page.
- Sub-page modules (one per output page family): ``contradictions``,
  ``politicians``, ``personas``, ``parties``, ``positions``, ``news``,
  ``statistika``, ``bills``, ``laws``, ``votes``, ``x``, ``tensions``,
  ``links``, ``analyses``, ``syntheses``, ``blog``, ``dashboard``.
  Each imports ``_common`` only — never peer sub-pages.

Cycle safety: ``_orchestrator`` imports ``_common`` (leaf) and every
sub-page (each a leaf relative to peers). When something does
``from src.render._common import X``, Python loads ``__init__.py``
first, which triggers ``_orchestrator`` load, which loads ``_common``
top-down. ``_common/__init__`` imports its own submodules in
dependency order (constants → filters/slugs/dates/text → enrich → assets)
and none of them imports a sibling sub-page, so every top-level symbol is
defined by the time the partial-init lookup from ``_orchestrator`` runs.
"""

from src.render._orchestrator import (  # noqa: F401  re-exported for public contract
    _generate_og_image,
    _generate_sitemap,
    generate_public_site,
)
from src.render.statistika import generate_statistika  # noqa: F401  re-exported
