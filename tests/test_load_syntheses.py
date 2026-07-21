"""Regression tests for `_load_syntheses` path resolution.

Locks down the F3g-pre invariant: synthesis-image existence check
resolves relative to the explicit `atmina_dir` arg, not CWD. Prevents
re-introduction of the pre-F3e fresh-worktree drift bug.
"""
from pathlib import Path

from src.render.syntheses import _enhance_synthesis_html, _load_syntheses


def test_load_syntheses_uses_atmina_dir_for_image_lookup(tmp_path):
    """`has_image=True` only when the PNG exists under the *passed* atmina_dir."""
    atmina_dir = tmp_path / "atmina"
    img_dir = atmina_dir / "images" / "synthesis"
    img_dir.mkdir(parents=True)

    syn_dir = Path("wiki/synthesis")
    if not syn_dir.exists():
        # No synthesis markdowns to test against — assert empty list and stop.
        assert _load_syntheses(atmina_dir) == []
        return

    md_files = sorted(syn_dir.glob("*.md"))
    assert md_files, "wiki/synthesis must contain at least one .md fixture"
    target_slug = md_files[0].stem
    (img_dir / f"{target_slug}.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    syntheses = _load_syntheses(atmina_dir)
    by_slug = {s["slug"]: s for s in syntheses}
    assert by_slug[target_slug]["image_filename"] == f"{target_slug}.png"
    for slug, s in by_slug.items():
        if slug != target_slug:
            assert s["image_filename"] is None


def test_load_syntheses_empty_atmina_dir_yields_no_images(tmp_path):
    """Empty `atmina_dir` → every synthesis returns `image_filename=None`."""
    atmina_dir = tmp_path / "atmina"
    atmina_dir.mkdir()

    syntheses = _load_syntheses(atmina_dir)
    for s in syntheses:
        assert s["image_filename"] is None, (
            f"synthesis {s['slug']} unexpectedly has image_filename "
            f"despite empty atmina_dir"
        )


def test_load_syntheses_default_path_is_cwd_relative(monkeypatch, tmp_path):
    """Default arg `Path('output/atmina')` resolves CWD-relative — preserves
    pre-fix behavior for any future caller that omits the arg."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "wiki" / "synthesis").mkdir(parents=True)
    (tmp_path / "wiki" / "synthesis" / "test.md").write_text(
        "---\ntitle: Test\n---\n# Heading\n\nbody\n", encoding="utf-8"
    )
    (tmp_path / "output" / "atmina" / "images" / "synthesis").mkdir(parents=True)
    (tmp_path / "output" / "atmina" / "images" / "synthesis" / "test.png").write_bytes(
        b"\x89PNG\r\n\x1a\n"
    )

    syntheses = _load_syntheses()  # default arg path

    assert len(syntheses) == 1
    assert syntheses[0]["slug"] == "test"
    assert syntheses[0]["image_filename"] == "test.png"


# ── _enhance_synthesis_html: post-sanitize enrichment ───────────────────

# The sanitized rendered form of a widget marker is literally
# ``<p>[vidžets:NAME]</p>`` — bleach leaves the square brackets and the LV
# ``ž`` untouched (verified 2026-07-09).
def _widgets_root(tmp_path, monkeypatch):
    """Point `_enhance_synthesis_html`'s widget lookup at a tmp WIKI_DIR."""
    import src.render.syntheses as syn_mod
    monkeypatch.setattr(syn_mod, "WIKI_DIR", tmp_path)
    return tmp_path / "synthesis" / "widgets"


def test_enhance_wraps_tables_in_scroll_div():
    html = (
        "<table>\n<thead><tr><th>A</th></tr></thead>"
        "<tbody><tr><td>x</td></tr></tbody>\n</table>"
    )
    out, toc = _enhance_synthesis_html(html, "some-slug")
    assert '<div class="table-scroll">' in out
    assert out.count("<table") == 1
    # Wrap opens before the table and closes after it.
    assert out.index('<div class="table-scroll">') < out.index("<table")
    assert out.strip().endswith("</div>")


def test_enhance_injects_existing_widget_unsanitized(tmp_path, monkeypatch):
    widgets = _widgets_root(tmp_path, monkeypatch)
    wdir = widgets / "my-slug"
    wdir.mkdir(parents=True)
    # Widget uses div+class that the bleach whitelist forbids — proves the
    # injected content is NOT re-sanitized.
    (wdir / "saraksti.html").write_text(
        '<div class="syn-w-saraksti"><span>JV</span></div>', encoding="utf-8"
    )
    html = "<p>intro</p>\n<p>[vidžets:saraksti]</p>\n<p>outro</p>"
    out, _toc = _enhance_synthesis_html(html, "my-slug")
    assert '<div class="syn-w-saraksti">' in out
    assert "[vidžets:saraksti]" not in out


def test_enhance_widget_content_is_not_sanitized(tmp_path, monkeypatch):
    """Widget div+class survives — the SEC-01 carve-out for trusted widgets."""
    widgets = _widgets_root(tmp_path, monkeypatch)
    wdir = widgets / "s"
    wdir.mkdir(parents=True)
    (wdir / "w.html").write_text(
        '<div class="syn-widget" id="w1">ok</div>', encoding="utf-8"
    )
    out, _toc = _enhance_synthesis_html("<p>[vidžets:w]</p>", "s")
    assert 'class="syn-widget"' in out
    assert 'id="w1"' in out


def test_enhance_missing_widget_drops_marker_without_crash(tmp_path, monkeypatch, caplog):
    _widgets_root(tmp_path, monkeypatch)  # empty — no widget files
    import logging
    html = "<p>before</p>\n<p>[vidžets:nope]</p>\n<p>after</p>"
    with caplog.at_level(logging.WARNING):
        out, _toc = _enhance_synthesis_html(html, "s")
    assert "[vidžets:nope]" not in out
    assert "<p>before</p>" in out and "<p>after</p>" in out
    assert any("nope" in r.message for r in caplog.records)


def test_enhance_h2_gets_id_and_toc_is_correct():
    html = "<h2>Konteksts</h2><p>a</p><h2>Karte</h2><p>b</p><h2>Klusēšana</h2>"
    out, toc = _enhance_synthesis_html(html, "s")
    assert '<h2 id="konteksts">Konteksts</h2>' in out
    assert '<h2 id="karte">Karte</h2>' in out
    assert toc == [
        {"id": "konteksts", "title": "Konteksts"},
        {"id": "karte", "title": "Karte"},
        {"id": "klusesana", "title": "Klusēšana"},
    ]


def test_enhance_h2_ids_are_unique():
    html = "<h2>Karte</h2><h2>Karte</h2><h2>Karte</h2>"
    out, toc = _enhance_synthesis_html(html, "s")
    assert [t["id"] for t in toc] == ["karte", "karte-2", "karte-3"]
    assert 'id="karte-2"' in out and 'id="karte-3"' in out


def test_enhance_empty_dash_cell_gets_cell_empty_class():
    html = "<table><tbody><tr><td>x</td><td>—</td></tr></tbody></table>"
    out, _toc = _enhance_synthesis_html(html, "s")
    assert '<td class="cell-empty">—</td>' in out
    # Non-empty cell untouched.
    assert "<td>x</td>" in out


def test_enhance_empty_dash_cell_with_align_attr():
    html = '<table><tbody><tr><td align="center">—</td></tr></tbody></table>'
    out, _toc = _enhance_synthesis_html(html, "s")
    assert '<td class="cell-empty" align="center">—</td>' in out


def test_enhance_does_not_double_wrap_widget_table(tmp_path, monkeypatch):
    """A widget that wraps its own table isn't wrapped again."""
    widgets = _widgets_root(tmp_path, monkeypatch)
    wdir = widgets / "s"
    wdir.mkdir(parents=True)
    (wdir / "m.html").write_text(
        '<div class="table-scroll"><table><tr><td>a</td></tr></table></div>',
        encoding="utf-8",
    )
    out, _toc = _enhance_synthesis_html("<p>[vidžets:m]</p>", "s")
    assert out.count("table-scroll") == 1
