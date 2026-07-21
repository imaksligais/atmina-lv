"""src.render — public-site rendering package.

Phase F3g (refactor-plan-2026-04-29 § Fāze 3) closure: the package
now owns ``generate_public_site`` and is the canonical public path
for the site renderer. Re-exports from ``_orchestrator``.

Public contract: ``from src.render import generate_public_site``.

``src/generate.py`` is a thin re-export shim so historical imports
``from src.generate import generate_public_site`` continue working.

Sub-modules:
- ``_common`` — leaf: constants, Jinja filters, slug helpers,
  ``_enrich_contradiction``, ``_render_page``. No internal package imports.
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
top-down. ``_common`` defines all top-level symbols sequentially with
zero sibling imports, so the partial-init lookup from ``_orchestrator``
always succeeds.
"""

from src.render._orchestrator import (  # noqa: F401  re-exported for public contract
    _generate_og_image,
    _generate_sitemap,
    generate_public_site,
)
from src.render.statistika import generate_statistika  # noqa: F401  re-exported
