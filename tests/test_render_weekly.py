from src.render.blog import _parse_weekly_stats


def _movers_markdown():
    return (
        '## Kas kustējās\n\n'
        '<!-- WEEKLY_BLOC coalition=80 opposition=20 -->\n\n'
        '![Kas kustējās](../images/briefs/2026-10-05-nedelas-movers.svg)\n\n'
        '*Skaitlis = pozīciju skaits nedēļā · +/− = izmaiņa pret iepriekšējo '
        'nedēļu · «jauns» = iepriekšējā nedēļā nebija.*\n\n'
        + '\n'.join(f'- **Vārds {i}** (Jaunā Vienotība) — {12-i} ({delta})'
                    for i, delta in enumerate(('↑3', '↓2', 'jauns', '—', '↑1', '↓1')))
        + '\n\nRedakcijas skaidrojums.\n\n## Nākamā sadaļa\n\nSaglabāt.'
    )


def test_weekly_movers_merge_chart_list_and_frozen_bloc(tmp_path, monkeypatch):
    from bs4 import BeautifulSoup
    from src.render.blog import _weekly_content_for_render, _brief_markdown_to_html
    html = _brief_markdown_to_html(_weekly_content_for_render(_movers_markdown(), is_weekly=True))
    soup = BeautifulSoup(html, 'html.parser')
    assert not soup.select('img[src$="nedelas-movers.svg"]')
    rows = soup.select('ol.weekly-movers-list > li.weekly-mover')
    assert [(r.select_one('.weekly-mover-person').contents[0], r.b.text) for r in rows] == \
        [(f'Vārds {i}', str(12 - i)) for i in range(6)]
    assert all(r.select_one('.weekly-mover-bar')['aria-hidden'] == 'true' for r in rows)
    escaped = _movers_markdown().replace('**Vārds 0**', '**<i>Vārds</i>**')
    assert '&lt;i&gt;Vārds&lt;/i&gt;' in _weekly_content_for_render(escaped, is_weekly=True)
    for cls, label in (('up', '+3'), ('down', '−2'), ('new', 'jauns'), ('flat', '—')):
        assert soup.select_one(f'.weekly-mover-delta--{cls}').text == label
    assert 'Koalīcija 80' in soup.text and 'Opozīcija 20' in soup.text
    assert 'WEEKLY_BLOC' not in html
    assert 'Skaitlis = pozīciju skaits' in soup.select_one('.weekly-movers-caption').text
    assert soup.select_one('.weekly-mover-party').text == 'JV'
    assert soup.select_one('.weekly-mover-bar')['style'] == '--pct:100%'
    assert 'Saglabāt.' in soup.text
    assert 'Redakcijas skaidrojums.' in soup.text
    # Existing weeks use the frozen geometry, without inventing counts. Both
    # artifact locations work; missing or damaged artifacts omit only the strip.
    import src.render.blog as blog
    monkeypatch.setattr(blog, '__file__', str(tmp_path / 'src/render/blog.py'))
    raw = _movers_markdown().replace('<!-- WEEKLY_BLOC coalition=80 opposition=20 -->', '')
    for directory in ('output/atmina/images/briefs', 'output/images/briefs'):
        artifact = tmp_path / directory / '2026-10-05-nedelas-movers.svg'
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text('<svg><rect height="18" width="315" fill="#1f2d4d"/>'
                            '<rect height="18" width="105" fill="#b9402f"/></svg>', encoding='utf-8')
        historical = BeautifulSoup(_weekly_content_for_render(raw, is_weekly=True), 'html.parser')
        assert historical.select_one('.weekly-bloc-bar')['style'] == '--pct:75%'
        assert historical.select_one('.weekly-bloc-legend').get_text(' ') == 'Koalīcija Opozīcija'
        # Explicit marker wins over a conflicting artifact.
        assert '--pct:80%' in _weekly_content_for_render(_movers_markdown(), is_weekly=True)
        artifact.write_text('broken SVG', encoding='utf-8')
        assert 'weekly-bloc' not in _weekly_content_for_render(raw, is_weekly=True)
        artifact.unlink()
    assert 'weekly-bloc' not in _weekly_content_for_render(raw, is_weekly=True)
    # Published variants (2026-05-26, 06-29, 07-13): no legend, or editor prose
    # between image, legend and list — still merged, prose kept, default caption.
    legend = ('*Skaitlis = pozīciju skaits nedēļā · +/− = izmaiņa pret iepriekšējo '
              'nedēļu · «jauns» = iepriekšējā nedēļā nebija.*\n\n')
    for variant in (raw.replace(legend, ''),
                    raw.replace(legend, legend + 'Starp leģendu un sarakstu.\n\n')):
        out = _weekly_content_for_render(variant, is_weekly=True)
        assert 'nedelas-movers.svg)' not in out and out.count('class="weekly-mover"') == 6
        assert 'Skaitlis = pozīciju skaits' in out and 'Redakcijas skaidrojums.' in out
    assert 'Starp leģendu un sarakstu.' in out
    # A second «Skaitlis = …» paragraph is editor prose, not the legend — kept.
    extra = '*Skaitlis = metodikas piezīme.*'
    assert extra in _weekly_content_for_render(raw.replace(legend, legend + extra + '\n\n'),
                                               is_weekly=True)


def test_weekly_movers_malformed_section_keeps_image():
    from src.render.blog import _weekly_content_for_render
    raw = _movers_markdown().replace('(↓2)', '(nezināms)')
    out = _weekly_content_for_render(raw, is_weekly=True)
    assert '![Kas kustējās](../images/briefs/2026-10-05-nedelas-movers.svg)' in out
    assert '- **Vārds 1**' in out
    assert 'weekly-mover' not in out
    assert _weekly_content_for_render(raw.replace('![Kas kustējās]', '[Kas kustējās]'), is_weekly=True).count('- **Vārds') == 6


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


def test_weekly_stats_survive_the_real_render_pipeline():
    """Regresija 2026-08-24: `Nedēļa skaitļos` publicējās TUKŠA 19/19 nedēļas lapās.

    Cēlonis bija secība `src/render/blog.py` renderēšanas ciklā: `content` vispirms
    izgāja caur `strip_visual_brief_block()`, kas savā iekšienē izpilda
    `_HTML_COMMENT_RE.sub("", ...)` un tātad iznīcina `<!-- WEEKLY_STATS ... -->`
    marķieri PIRMS `_parse_weekly_stats()` to paspēj nolasīt. `weekly_stats` vienmēr
    bija None, kartītes nekad neuzģenerējās, un virsraksts palika bez satura.

    Iepriekšējie vārti to neredzēja pēc konstrukcijas: viens salīdzināja divu
    literāļu POZĪCIJAS avota failā (un `strip_visual_brief_block` tur neparādās),
    otrs būvēja `content` sintētiski un `strip_visual_brief_block` nemaz nesauca.
    Šis tests iet caur ĪSTO transformāciju.
    """
    from src.render.blog import _weekly_content_for_render

    raw = (
        "# Nedēļas analīze — 2026-08-17 līdz 2026-08-23\n\n"
        "## Nedēļas stāsts\n\nProza.\n\n"
        "## Nedēļa skaitļos\n\n"
        "<!-- WEEKLY_STATS: positions=314 votes=61 contradictions=0 "
        "top_topic=airBaltic top_party=Apvienotais saraksts -->\n\n"
        "## Kas kustējās\n\nSaraksts.\n\n"
        "<!-- AGENT: iekšēja piezīme, kurai jāpazūd -->\n\n"
        "## Vizuālais brief\n\n- **Tēma:** kaut kas\n- **Skaitlis:** –\n"
    )
    out = _weekly_content_for_render(raw, is_weekly=True)

    assert "weekly-stats" in out, "kartītes pazuda — marķieris nostrippots par agru"
    assert "<b>314</b>" in out
    assert "WEEKLY_STATS" not in out          # marķieris patērēts
    assert "AGENT:" not in out                # pārējie komentāri joprojām aiziet
    assert "Vizuālais brief" not in out       # iekšējais bloks joprojām aiziet
    assert out.index("Nedēļa skaitļos") < out.index("weekly-stats") < out.index("Kas kustējās")


def test_daily_brief_content_untouched_by_weekly_path():
    """Dienas pārskatam kartīšu nav, bet komentāriem un Vizuālajam brief tāpat jāaiziet."""
    from src.render.blog import _weekly_content_for_render

    raw = ("# Dienas analīze — 2026-08-23\n\n"
           "<!-- DIENAS STATS: 273 dokumenti -->\n\n## Galvenais\n\nProza.\n\n"
           "## Vizuālais brief\n\n- **Skaitlis:** –\n")
    out = _weekly_content_for_render(raw, is_weekly=False)
    assert "DIENAS STATS" not in out
    assert "Vizuālais brief" not in out
    assert "weekly-stats" not in out
    assert "Galvenais" in out
