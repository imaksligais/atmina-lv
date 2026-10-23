"""`assets/_redirects` (Cloudflare) sargi.

Sakne `/` ir REWRITE (200) uz index.html — html_handling=none to neatvasina.
Neviena kārtula nedrīkst ņemt par avotu `.html` ceļu: publiskie URL nes .html
un atbild 200 bez redirect (CLAUDE.md / spec 2026-09-15).
"""
from pathlib import Path

_REDIRECTS = Path(__file__).resolve().parents[1] / "assets" / "_redirects"


def _rules() -> list[list[str]]:
    lines = _REDIRECTS.read_text(encoding="utf-8").splitlines()
    return [ln.split() for ln in lines if ln.strip() and not ln.lstrip().startswith("#")]


def test_root_is_rewritten_to_index_with_200():
    rules = _rules()
    assert ["/", "/index.html", "200"] in rules, rules


def test_no_rule_takes_an_html_path_as_source():
    for rule in _rules():
        assert not rule[0].endswith(".html"), f"{rule}: .html avots = redirect uz publisku URL"
