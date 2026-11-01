import xml.dom.minidom

from src.graphics.weekly_chart import make_movers_svg


def test_make_movers_svg_wellformed():
    movers = [
        {"name": "Aļģis", "party": "AS", "count": 20, "delta": 5},
        {"name": "Bērziņš", "party": "JV", "count": 12, "delta": "jauns"},
        {"name": "Cīrulis", "party": "NA", "count": 8, "delta": -3},
    ]
    coalition = {"coalition": 30, "opposition": 10}
    svg = make_movers_svg(movers, coalition).decode("utf-8")
    # well-formed XML
    xml.dom.minidom.parseString(svg)
    assert svg.startswith("<?xml") or svg.lstrip().startswith("<svg")
    # one bar per mover (rects with class bar)
    assert svg.count('class="bar"') == 3
    # names + counts rendered; delta annotations present (ASCII, not arrows)
    assert "Aļģis" in svg and "20" in svg
    assert "jauns" in svg          # no-baseline label
    assert "-3" in svg             # down delta as ASCII
    assert "+5" in svg             # up delta as ASCII
    assert "↑" not in svg and "↓" not in svg  # no Unicode arrows (font drops them)
    # coalition vs opposition strip present
    assert "Koalīcija" in svg and "Opozīcija" in svg


def test_make_movers_svg_empty_week():
    svg = make_movers_svg([], {"coalition": 0, "opposition": 0}).decode("utf-8")
    xml.dom.minidom.parseString(svg)   # still well-formed
    assert "Nav datu" in svg


def test_make_movers_svg_has_intrinsic_dimensions():
    """The <svg> must carry width/height attrs, not just a viewBox.

    Regression: a viewBox-only SVG inside <img> has no intrinsic size in
    WebKit/Safari, so `.weekly-body img { width:100% }` collapsed its layout
    box and the chart painted over the movers list below it on desktop.
    """
    movers = [{"name": "Aļģis", "party": "AS", "count": 20, "delta": 5}]
    svg = make_movers_svg(movers, {"coalition": 1, "opposition": 0}).decode("utf-8")
    root = xml.dom.minidom.parseString(svg).documentElement
    assert root.getAttribute("width"), "svg missing intrinsic width attr"
    assert root.getAttribute("height"), "svg missing intrinsic height attr"
    # viewBox must still be present and consistent (width == viewBox width)
    vb = root.getAttribute("viewBox").split()
    assert root.getAttribute("width") == vb[2]
    assert root.getAttribute("height") == vb[3]
