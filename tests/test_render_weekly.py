from src.render.blog import _parse_weekly_stats


def test_parse_weekly_stats():
    md = ("## Nedēļa skaitļos\n"
          "<!-- WEEKLY_STATS: positions=173 votes=94 contradictions=1 "
          "top_topic=Koalīcija un partijas top_party=Apvienotais saraksts -->\n")
    stats = _parse_weekly_stats(md)
    assert stats["positions"] == "173"
    assert stats["votes"] == "94"
    assert stats["top_topic"] == "Koalīcija un partijas"
    assert stats["top_party"] == "Apvienotais saraksts"


def test_parse_weekly_stats_absent_returns_none():
    assert _parse_weekly_stats("no marker here") is None


def test_weekly_stats_render_inline_under_heading():
    """Marker → stat cards inline, so '## Nedēļa skaitļos' is never orphaned."""
    import markdown
    from src.render.blog import _WEEKLY_STATS_RE, _weekly_stats_html
    content = ("## Nedēļa skaitļos\n\n"
               "<!-- WEEKLY_STATS: positions=173 votes=94 contradictions=1 "
               "top_topic=Koalīcija un partijas top_party=Nacionālā apvienība -->\n\n"
               "## Kas kustējās\n")
    stats = _parse_weekly_stats(content)
    content = _WEEKLY_STATS_RE.sub(lambda _m: _weekly_stats_html(stats), content)
    html = markdown.Markdown(extensions=["tables", "fenced_code"]).convert(content)
    assert '<section class="weekly-stats">' in html
    assert "<b>173</b>" in html
    assert "WEEKLY_STATS" not in html          # marker consumed
    # cards sit between the two headings (not orphaned)
    assert html.index("Nedēļa skaitļos") < html.index("weekly-stats") < html.index("Kas kustējās")


def test_weekly_stat_card_labels_decline_with_count():
    """Count cards must agree with the number (2026-07-27: a one-contradiction
    week rendered '1 pretrunas'). Latvian: numbers ending in 1 except 11 take
    the singular. The name cards carry no count and never decline."""
    from src.render.blog import _weekly_stats_html

    def labels(n: str) -> str:
        return _weekly_stats_html({
            "positions": n, "votes": n, "contradictions": n,
            "top_topic": "Tieslietas", "top_party": "Apvienotais saraksts",
        })

    one = labels("1")
    assert "<span>pozīcija</span>" in one
    assert "<span>balsojums</span>" in one
    assert "<span>pretruna</span>" in one

    for plural_n in ("0", "2", "11", "65", "290"):
        h = labels(plural_n)
        assert "<span>pozīcijas</span>" in h, plural_n
        assert "<span>balsojumi</span>" in h, plural_n
        assert "<span>pretrunas</span>" in h, plural_n

    # 21 ends in 1 (and is not 11) → singular
    assert "<span>pretruna</span>" in labels("21")

    # name cards stay fixed regardless of the counts around them
    assert "<span>top tēma</span>" in one
    assert "<span>aktīvākā partija</span>" in one
