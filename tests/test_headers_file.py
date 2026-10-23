"""`assets/_headers` (Cloudflare) sargi: lasa to, ko rakstītājs raksta.

`assets/_headers` ir vienīgais galveņu avots (kopš 2026-10-19).
`script-src` nekad nesatur 'unsafe-inline' (CLAUDE.md § No inline JavaScript).
"""
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_HEADERS = _ROOT / "assets" / "_headers"

_REQUIRED_SECURITY_HEADERS = (
    "Strict-Transport-Security",
    "X-Content-Type-Options",
    "X-Frame-Options",
    "Referrer-Policy",
    "Content-Security-Policy",
)


def _parse_headers_file(text: str) -> dict[str, dict[str, str]]:
    """{ceļa_paterns: {nosaukums: vērtība}} — Cloudflare `_headers` formāts."""
    rules: dict[str, dict[str, str]] = {}
    current = None
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if not raw.startswith((" ", "\t")):
            current = raw.strip()
            rules[current] = {}
            continue
        assert current is not None, f"galvene bez ceļa: {raw!r}"
        name, _, value = raw.strip().partition(":")
        rules[current][name.strip()] = value.strip()
    return rules


def test_headers_file_exists_and_has_root_rule():
    rules = _parse_headers_file(_HEADERS.read_text(encoding="utf-8"))
    assert "/*" in rules, f"nav /* kārtulas; ir: {list(rules)}"
    assert len(_HEADERS.read_text(encoding="utf-8").splitlines()) <= 100


def test_root_rule_carries_every_security_header():
    """Līdz 2026-10-19 šo sargāja salīdzinājums ar htaccess.template; tagad nosaukumi ir šeit."""
    root = _parse_headers_file(_HEADERS.read_text(encoding="utf-8"))["/*"]
    missing = [h for h in _REQUIRED_SECURITY_HEADERS if not root.get(h)]
    assert not missing, f"/* trūkst {missing} (pārbaudīti {len(_REQUIRED_SECURITY_HEADERS)})"


def test_script_src_has_no_unsafe_inline():
    root = _parse_headers_file(_HEADERS.read_text(encoding="utf-8"))["/*"]
    csp = root["Content-Security-Policy"]
    script_src = next(p for p in csp.split(";") if p.strip().startswith("script-src"))
    assert "'unsafe-inline'" not in script_src


def test_cache_rules_cover_json_and_assets():
    rules = _parse_headers_file(_HEADERS.read_text(encoding="utf-8"))
    assert "/*.json" in rules and "max-age=300" in rules["/*.json"]["Cache-Control"]
    assert "/assets/*" in rules and "max-age=86400" in rules["/assets/*"]["Cache-Control"]
    assert "/images/*" in rules and "max-age=604800" in rules["/images/*"]["Cache-Control"]
