"""``_common`` aktīvu plumbing — foto data-URI, JSON blakusfaili, CDN
lejupielādes, ``?v=`` kešbusteris un Jinja lapas primitīvs.

Izgriezts no vienfaila ``src/render/_common.py`` 2026-09-05 (plāna 5.8).
``_resolve_assets_version`` ir CLAUDE.md § Output Conventions nosauktais
CSP kešbusteris — tas paliek importējams arī no ``src.render._common``.
"""

from __future__ import annotations

import gzip as _gzip
import os
from pathlib import Path
from typing import Any

import brotli as _brotli
from jinja2 import Environment

from src.render._common.constants import ASSETS_DIR, BASE_URL, _logger

def _photo_data_uri(slug: str) -> str | None:
    """Read `assets/photos/<slug>.jpg` and return a base64 data URI, or None."""
    path = ASSETS_DIR / "photos" / f"{slug}.jpg"
    if not path.exists():
        return None
    import base64
    return "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode()

# ── Sidecar JSON emission ───────────────────────────────────────────


def _emit_json_compressed(payload: bytes, dest: Path) -> Path:
    """Write ``payload`` to ``dest`` plus pre-compressed ``.br``/``.gz`` siblings.

    Shared compress-and-write core for the render package's JSON sidecars
    (pozicijas-data, balsojumi-matrica, saites-data, sg-index). Callers pass
    the already-encoded ``payload`` bytes and the ``.json`` destination path;
    this writes ``dest``, ``dest + ".br"`` (brotli quality 11) and
    ``dest + ".gz"`` (gzip level 9). Brotli + gzip variants let the htaccess
    ``*.json`` rewrite pick the best for the Accept-Encoding header on the
    LiteSpeed shared host, which does not auto-compress application/json.
    Idempotent — overwrites each render. Does NOT create parent dirs or log;
    callers own ``mkdir`` and any ``logger.info``. Returns ``dest``.
    """
    dest.write_bytes(payload)
    dest.with_suffix(dest.suffix + ".br").write_bytes(_brotli.compress(payload, quality=11))
    dest.with_suffix(dest.suffix + ".gz").write_bytes(_gzip.compress(payload, compresslevel=9))
    return dest


# ── Asset versioning + downloads ────────────────────────────────────


def _download_chart_js(dest: Path) -> None:
    """Download Chart.js from CDN.

    Used by `generate_public_site` (index page chart) AND
    `generate_statistika` (CSP dashboard charts). Promoted to `_common`
    so the F3d statistika.py module does not have to back-import from
    the orchestrator (cycle).
    """
    try:
        import httpx
        resp = httpx.get(
            "https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js",
            follow_redirects=True,
            timeout=30,
        )
        resp.raise_for_status()
        dest.write_bytes(resp.content)
        _logger.info("Downloaded chart.min.js")
    except Exception as e:
        # No stub fallback: under additive deploy a stub ships and stays
        # broken on the live site with no reclaim path and no detector.
        raise RuntimeError(
            f"Could not download chart.min.js from CDN: {e} — refusing to "
            "write a stub; retry when the network is back."
        ) from e


def _download_annotation_plugin(dest: Path) -> None:
    """Download chartjs-plugin-annotation from CDN.

    Used by `generate_public_site` AND `generate_statistika` — same
    rationale as `_download_chart_js`.
    """
    try:
        import httpx
        resp = httpx.get(
            "https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3/dist/chartjs-plugin-annotation.min.js",
            follow_redirects=True,
            timeout=30,
        )
        resp.raise_for_status()
        dest.write_bytes(resp.content)
        _logger.info("Downloaded chartjs-plugin-annotation.min.js")
    except Exception as e:
        # Same rationale as _download_chart_js: a silent stub is the defect.
        raise RuntimeError(
            f"Could not download chartjs-plugin-annotation.min.js from CDN: {e} — "
            "refusing to write a stub; retry when the network is back."
        ) from e


def _download_d3(dest: Path) -> None:
    """Download D3 v7 from CDN so saites.html can serve it from our own host.

    Same contract as `_download_chart_js`. Until 2026-08-15 saites.html loaded
    d3 straight from d3js.org, which leaked every visitor's IP to a third party
    on page load; self-hosting removes the host from the CSP allowlist too.
    """
    try:
        import httpx
        resp = httpx.get(
            "https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js",
            follow_redirects=True,
            timeout=30,
        )
        resp.raise_for_status()
        dest.write_bytes(resp.content)
        _logger.info("Downloaded d3.v7.min.js")
    except Exception as e:
        # Same rationale as _download_chart_js: a silent stub is the defect.
        raise RuntimeError(
            f"Could not download d3.v7.min.js from CDN: {e} — refusing to "
            "write a stub; retry when the network is back."
        ) from e


def _resolve_assets_version() -> str:
    """Cache-bust version string for `?v=` query on style.css + every top-level assets/*.js.

    Defaults to ``max(mtime)`` across the versioned assets — Opera and
    some Chromium builds were serving a stale ``style.css`` against
    fresh HTML, leaving new hero-v2 classes unstyled. Picking max(mtime)
    across the bundle means a JS-only change still busts every ``?v=``
    query.

    Override via the ``ATMINA_ASSETS_VERSION`` env var to force a stable
    value — used by ``tests/test_render_chars.py`` so HTML byte-baselines
    do not drift on a fresh worktree where assets/* mtimes are
    arbitrary timestamps from the checkout.

    Empty-string semantics: ``ATMINA_ASSETS_VERSION=""`` is treated as
    unset and falls through to mtime. To force a literal empty/zero
    cache-bust value, set the variable to ``"0"`` (or any non-empty
    token); only truthy strings short-circuit the fallback.
    """
    forced = os.environ.get("ATMINA_ASSETS_VERSION")
    if forced:
        return forced
    # style.css + every top-level *.js in assets/ (glob so new JS files are
    # auto-versioned without touching this list). The cuelume/ subdir is
    # intentionally NOT versioned — it is imported by module URL, not a ?v= tag.
    versioned = [ASSETS_DIR / "style.css", *sorted(ASSETS_DIR.glob("*.js"))]
    mtimes = [int(p.stat().st_mtime) for p in versioned if p.exists()]
    return str(max(mtimes)) if mtimes else "0"


# ── Page primitive ──────────────────────────────────────────────────


def _render_page(
    env: Environment,
    template_name: str,
    output_path: Path,
    context: dict[str, Any],
) -> None:
    """Render a Jinja2 template to a file.

    Auto-injects ``canonical_url`` into the template context based on the
    path of ``output_path`` relative to the deploy root (the last ``atmina``
    directory in the path). Callers can override by setting ``canonical_url``
    in ``context`` explicitly.
    """
    if "canonical_url" not in context:
        parts = output_path.parts
        for i in range(len(parts) - 1, -1, -1):
            if parts[i] == "atmina":
                rel = "/".join(parts[i + 1:])
                canonical = f"{BASE_URL}/{rel}"
                if canonical.endswith("/index.html"):
                    canonical = canonical[: -len("index.html")]
                context["canonical_url"] = canonical
                break
    template = env.get_template(template_name)
    html = template.render(**context)
    output_path.write_text(html, encoding="utf-8")
