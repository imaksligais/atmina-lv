"""`assets/_headers` (Cloudflare) sargi: lasa to, ko rakstītājs raksta.

Kamēr `assets/htaccess.template` eksistē (vecais hostings rezervē), abiem
failiem jānes IDENTISKA CSP un tie paši drošības galveņu nosaukumi.
`script-src` nekad nesatur 'unsafe-inline' (CLAUDE.md § No inline JavaScript).
"""
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_HEADERS = _ROOT / "assets" / "_headers"
_HTACCESS = _ROOT / "assets" / "htaccess.template"


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


def _htaccess_headers() -> dict[str, str]:
    text = _HTACCESS.read_text(encoding="utf-8")
    found = dict(re.findall(r'Header always set (\S+) "([^"]*)"', text))
    assert len(found) >= 5, f"htaccess.template denominators sabrucis: {found}"
    return found


def test_headers_file_exists_and_has_root_rule():
    rules = _parse_headers_file(_HEADERS.read_text(encoding="utf-8"))
    assert "/*" in rules, f"nav /* kārtulas; ir: {list(rules)}"
    assert len(_HEADERS.read_text(encoding="utf-8").splitlines()) <= 100


def test_every_htaccess_security_header_is_carried_over():
    root = _parse_headers_file(_HEADERS.read_text(encoding="utf-8"))["/*"]
    for name, value in _htaccess_headers().items():
        assert name in root, f"{name} trūkst _headers /* kārtulā"
        assert root[name] == value, f"{name} atšķiras:\n  htaccess: {value}\n  _headers: {root[name]}"


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
