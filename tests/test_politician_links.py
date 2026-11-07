"""Politiķu saites Atraduma tekstā (`link_politicians`).

Kļūme, ko šis tests ķer: saite iešūta nepareizā vietā — esošas saites vai
virsraksta iekšā, uz locītu formu («Linda Liepiņas» → T1 klases nepareiza
piesaiste), katrā pieminēšanā, vai teksta entītijas pārserializētas
(`&lt;b&gt;` kļūst par īstu tagu). Un klusa veiksme: vārds, kas tekstā nav
atrasts, jāuzrāda report sarakstā, nevis jāpazūd.
"""

from __future__ import annotations

from src.render._common.politician_links import link_politicians

LINDA = {
    "name": "Linda Liepiņa",
    "slug": "linda-liepina",
    "data": {"party": 'Latvija "Pirmajā" Vietā & co', "stats": "3 pozīcijas"},
}
ANSIS = {"name": "Ansis Pūpols", "slug": "ansis-pupols", "data": {"party": "NA"}}
NOBODY = {"name": "Neesošs Cilvēks", "slug": "neesoss-cilveks", "data": {}}


def _links(html: str) -> int:
    return html.count('class="pol-link"')


def test_first_mention_linked_with_escaped_data():
    out, report = link_politicians("<p>Linda Liepiņa teica. Linda Liepiņa atkārtoja.</p>", [LINDA])
    # (a) pirmā pieminēšana → saite ar href un escapotiem data-*
    assert out.startswith('<p><a class="pol-link" href="../politiki/linda-liepina.html"')
    assert 'data-party="Latvija &quot;Pirmajā&quot; Vietā &amp; co"' in out
    assert 'data-stats="3 pozīcijas"' in out
    assert '>Linda Liepiņa</a> teica.' in out
    # (b) otrā pieminēšana neskarta
    assert _links(out) == 1
    assert out.endswith("Linda Liepiņa atkārtoja.</p>")
    assert report["linked"] == ["linda-liepina"]


def test_existing_anchor_and_heading_skipped_later_plain_mention_linked():
    # (c) vārds esošā <a> un virsrakstā neskarts; vēlākā vienkāršā pieminēšana saistīta
    src = (
        '<h2>Linda Liepiņa</h2>'
        '<p><a href="https://x.com/a">Linda Liepiņa</a> rakstīja.</p>'
        '<p>Vēlāk Linda Liepiņa runāja.</p>'
    )
    out, _ = link_politicians(src, [LINDA])
    assert _links(out) == 1
    assert out.startswith('<h2>Linda Liepiņa</h2><p><a href="https://x.com/a">Linda Liepiņa</a>')
    assert '<p>Vēlāk <a class="pol-link"' in out


def test_inflected_and_glued_forms_not_linked():
    # (d) ģenitīvs un vārds bez robežas neskarti — saite tikai pilnajai formai
    out, report = link_politicians(
        "<p>Lindas Liepiņas viedoklis. Ansis Pūpolsa. Ansis Pūpols (NA).</p>", [LINDA, ANSIS]
    )
    assert "Lindas Liepiņas viedoklis" in out
    assert "Ansis Pūpolsa." in out
    assert _links(out) == 1
    assert '>Ansis Pūpols</a> (NA)' in out
    assert report["missing"] == ["Linda Liepiņa"]


def test_entities_preserved_verbatim():
    # (e) entītijas paliek burtiski — nekas netiek pārserializēts
    src = "<p>&lt;b&gt; un &amp; — Ansis Pūpols &copy; &#8212;</p>"
    out, _ = link_politicians(src, [ANSIS])
    assert out.startswith("<p>&lt;b&gt; un &amp; — <a class=\"pol-link\"")
    assert out.endswith(">Ansis Pūpols</a> &copy; &#8212;</p>")


def test_missing_name_reported_with_denominator():
    # (f) neatrasts vārds report sarakstā; saucējs listed/resolved/linked
    out, report = link_politicians("<p>Ansis Pūpols.</p>", [ANSIS, NOBODY])
    assert _links(out) == 1
    assert report == {"resolved": 2, "linked": ["ansis-pupols"], "missing": ["Neesošs Cilvēks"]}
