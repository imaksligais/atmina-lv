from src.render.blog import _parse_weekly_stats


def test_parse_weekly_stats():
    md = ("## Nedēļā skaitļos\n"
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
    """Marker → stat cards inline, so '## Nedēļā skaitļos' is never orphaned."""
    import markdown
    from src.render.blog import _WEEKLY_STATS_RE, _weekly_stats_html
    content = ("## Nedēļā skaitļos\n\n"
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
    assert html.index("Nedēļā skaitļos") < html.index("weekly-stats") < html.index("Kas kustējās")
