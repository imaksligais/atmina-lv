"""balsojumi.html: SSR vote-card path deleted, archive renderer is the only card path.

"Option 2" (2026-07-17): the vote list no longer SSRs the newest 200 cards
(~25 KB/card × 200 → 6.4 MB page). The compact matrix JSON + assets/bmv1.js
``window.balsojumiArchiveRender`` render SSR-identical cards client-side for the
WHOLE history. This test locks the template down to the static archive shell
(``#votes-archive`` + ``#votes-archive-cards`` + ``<noscript>``) and asserts the
SSR card loop is gone, plus the bmv1.js recent-shard option (``opts.wantFull``).
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

_TEMPLATE = Path("templates/balsojumi.html.j2")
_BMV1 = Path("assets/bmv1.js")


def _env() -> Environment:
    """Minimal env with the filters balsojumi.html.j2 uses (see _orchestrator)."""
    env = Environment(loader=FileSystemLoader("templates"), autoescape=True)
    env.globals["assets_version"] = "test"
    env.filters["lv_date"] = (
        lambda s: f"{s[8:10]}.{s[5:7]}.{s[:4]}"
        if s and len(str(s)) >= 10 and "-" in str(s)
        else s or ""
    )
    env.filters["safe_url"] = lambda u: u or ""
    env.filters["safe_json"] = lambda v: v
    return env


_MINIMAL_CTX = dict(
    votes=[],
    vote_topics=[],
    deputies=[],
    vote_sessions=[],
    metrics={"total": 0, "last_week": 0, "accepted_pct": 0},
    bills=[],
    bill_topics=[],
    laws_index_count=0,
)


def _render() -> str:
    return _env().get_template("balsojumi.html.j2").render(**_MINIMAL_CTX)


def test_archive_shell_present():
    html = _render()
    assert 'id="votes-archive"' in html
    assert 'id="votes-archive-cards"' in html
    # noscript fallback in the votes-list section.
    assert "<noscript>" in html
    assert "nepieciešams JavaScript" in html


def test_no_ssr_vote_card_loop():
    raw = _TEMPLATE.read_text(encoding="utf-8")
    html = _render()
    # No SSR `{% for v in votes[...] %}` card loop in the template source.
    assert "{% for v in votes[" not in raw
    # No SSR-rendered vote card in the output.
    assert 'class="vote-card"' not in html


def test_template_does_not_reference_tracked_votes():
    raw = _TEMPLATE.read_text(encoding="utf-8")
    assert "tracked_votes" not in raw


def test_bmv1_recent_shard_option():
    js = _BMV1.read_text(encoding="utf-8")
    assert "window.balsojumiArchiveRender" in js
    assert "opts.wantFull" in js
