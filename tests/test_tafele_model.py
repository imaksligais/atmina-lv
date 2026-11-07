"""Tāfeles datu vārti: katra saite ar avotu, rakstu un godīgu līmeni."""
from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from src.tafele.model import BoardError, load_board, validate_board

FIX = Path(__file__).parent / "fixtures" / "tafele_min.yaml"


@pytest.fixture
def articles_dir(tmp_path):
    (tmp_path / "testa-raksts.md").write_text("---\ntitle: T\ndate: 2026-01-01\n---\n\nTeksts\n", encoding="utf-8")
    return tmp_path


EXTRA = frozenset({"anna"})


def _board(tmp_path, mutate=None):
    raw = yaml.safe_load(FIX.read_text(encoding="utf-8"))
    if mutate:
        mutate(raw)
    p = tmp_path / "b.yaml"
    p.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    return load_board(p)


def test_fixture_is_valid(tmp_path, articles_dir):
    validate_board(_board(tmp_path), articles_dir, require_published=False, extra_persons=EXTRA)


def test_unknown_endpoint_fails(tmp_path, articles_dir):
    b = _board(tmp_path, lambda r: r["links"][0].update({"to": "nav-tada"}))
    with pytest.raises(BoardError, match="l1.*nav-tada"):
        validate_board(b, articles_dir, require_published=False, extra_persons=EXTRA)


def test_missing_source_url_fails(tmp_path, articles_dir):
    b = _board(tmp_path, lambda r: r["links"][0]["source"].update({"url": ""}))
    with pytest.raises(BoardError, match="l1.*avot"):
        validate_board(b, articles_dir, require_published=False, extra_persons=EXTRA)


def test_tier2_without_attribution_fails(tmp_path, articles_dir):
    b = _board(tmp_path, lambda r: r["links"][1].pop("caveat"))
    with pytest.raises(BoardError, match="l2.*atrun"):
        validate_board(b, articles_dir, require_published=False, extra_persons=EXTRA)


def test_tier3_without_caveat_fails(tmp_path, articles_dir):
    b = _board(tmp_path, lambda r: r["links"][3].pop("caveat"))
    with pytest.raises(BoardError, match="l4.*atrun"):
        validate_board(b, articles_dir, require_published=False, extra_persons=EXTRA)


def test_article_must_exist(tmp_path, articles_dir):
    b = _board(tmp_path, lambda r: r["links"][0].update({"article": "nav-raksta#a"}))
    with pytest.raises(BoardError, match="l1.*nav-raksta"):
        validate_board(b, articles_dir, require_published=False, extra_persons=EXTRA)


def test_article_link_needs_anchor(tmp_path, articles_dir):
    b = _board(tmp_path, lambda r: r["links"][0].update({"article": "testa-raksts"}))
    with pytest.raises(BoardError, match="l1.*enkur"):
        validate_board(b, articles_dir, require_published=False, extra_persons=EXTRA)


def test_person_not_in_allowlist_fails(tmp_path, articles_dir):
    def m(r):
        r["entities"].append({"id": "janis", "type": "person", "name": "Jānis X", "color": "neu",
                              "pos": [700, 500], "summary": "x"})
    b = _board(tmp_path, m)
    with pytest.raises(BoardError, match="janis.*publisk"):
        validate_board(b, articles_dir, require_published=False, extra_persons=EXTRA)


def test_position_outside_grid_fails(tmp_path, articles_dir):
    b = _board(tmp_path, lambda r: r["entities"][0].update({"pos": [1300, 10]}))
    with pytest.raises(BoardError, match="anna.*režģ"):
        validate_board(b, articles_dir, require_published=False, extra_persons=EXTRA)


def test_guide_unknown_link_fails(tmp_path, articles_dir):
    b = _board(tmp_path, lambda r: r["guides"][0]["links"].append("l99"))
    with pytest.raises(BoardError, match="l99"):
        validate_board(b, articles_dir, require_published=False, extra_persons=EXTRA)


def test_published_board_needs_published_articles(tmp_path, articles_dir):
    (articles_dir / "testa-raksts.md").write_text(
        "---\ntitle: T\ndate: 2026-01-01\ndraft: true\n---\n\nTeksts\n", encoding="utf-8")
    b = _board(tmp_path)
    with pytest.raises(BoardError, match="testa-raksts.*melnraksts"):
        validate_board(b, articles_dir, require_published=True, extra_persons=EXTRA)


def test_all_errors_reported_together(tmp_path, articles_dir):
    def m(r):
        r["links"][0]["to"] = "x1"
        r["links"][2]["to"] = "x2"
    b = _board(tmp_path, m)
    with pytest.raises(BoardError) as e:
        validate_board(b, articles_dir, require_published=False, extra_persons=EXTRA)
    assert "x1" in str(e.value) and "x2" in str(e.value)


@pytest.mark.parametrize("field,value", [
    ("entities", None), ("links", None), ("zones", None),
])
def test_null_collections_raise_board_error(tmp_path, field, value):
    with pytest.raises(BoardError):
        _board(tmp_path, lambda r: r.update({field: value}))


@pytest.mark.parametrize("pos", [[10], [10, "20"], [True, 20], "10,20"])
def test_malformed_position_raises_board_error(tmp_path, pos):
    with pytest.raises(BoardError):
        _board(tmp_path, lambda r: r["entities"][0].update(pos=pos))


@pytest.mark.parametrize("tier", ["1", True, None])
def test_non_integer_tier_raises_board_error(tmp_path, tier):
    with pytest.raises(BoardError):
        _board(tmp_path, lambda r: r["links"][0].update(tier=tier))


@pytest.mark.parametrize("where", ["link", "fact", "guide"])
def test_non_string_article_raises_board_error(tmp_path, where):
    def mutate(raw):
        row = {"link": raw["links"][0], "fact": raw["entities"][1]["facts"][0],
               "guide": raw["guides"][0]}[where]
        row["article"] = None
    with pytest.raises(BoardError):
        _board(tmp_path, mutate)


@pytest.mark.parametrize("header", [
    "---\ndraft: true\n", "---\n[broken\n---\n", "---\n- draft\n---\n", "---\n---\n",
])
def test_invalid_frontmatter_fails_closed(tmp_path, articles_dir, header):
    (articles_dir / "testa-raksts.md").write_text(header, encoding="utf-8")
    with pytest.raises(BoardError, match="testa-raksts.*frontmatter"):
        validate_board(_board(tmp_path), articles_dir, True, extra_persons=EXTRA)


def test_title_with_dashes_does_not_hide_draft(tmp_path, articles_dir):
    (articles_dir / "testa-raksts.md").write_text(
        '---\ntitle: "A --- B"\ndraft: true\n---\nTeksts', encoding="utf-8")
    with pytest.raises(BoardError, match="melnraksts"):
        validate_board(_board(tmp_path), articles_dir, True, extra_persons=EXTRA)


def test_data_cannot_extend_public_persons(tmp_path, articles_dir):
    board = _board(tmp_path, lambda r: r.update(extra_persons=["anna"]))
    with pytest.raises(BoardError, match="anna.*publisko"):
        validate_board(board, articles_dir, False)


@pytest.mark.parametrize("field,value", [("slug", "../escape"), ("draft", "false")])
def test_unsafe_output_metadata_fails(tmp_path, field, value):
    with pytest.raises(BoardError):
        _board(tmp_path, lambda r: r.update({field: value}))


def test_draft_board_is_removed_from_output(tmp_path, articles_dir):
    from src.render.tafeles import render_tafeles
    data = tmp_path / "tafeles"
    data.mkdir()
    (data / "t.yaml").write_text(FIX.read_text(encoding="utf-8"), encoding="utf-8")
    atmina = tmp_path / "atmina"
    (atmina / "analizes").mkdir(parents=True)
    stale = atmina / "analizes" / "saites-tests.html"
    stale.write_text("vecs", encoding="utf-8")
    assert render_tafeles(None, atmina, data, articles_dir) == 0
    assert not stale.exists()


@pytest.mark.parametrize("article_draft", [True, False])
def test_public_board_requires_published_articles(tmp_path, articles_dir, article_draft):
    from src.render._orchestrator import _make_env
    from src.render.tafeles import render_tafeles
    data = tmp_path / "tafeles"
    data.mkdir()
    raw = yaml.safe_load(FIX.read_text(encoding="utf-8"))
    raw["draft"] = False
    # Izdomātās personas atļauja nav pieejama publicēšanas ceļā.
    raw["entities"][0].update(type="company", name="SIA «Tests»")
    (data / "t.yaml").write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    (articles_dir / "testa-raksts.md").write_text(
        f"---\ntitle: T\ndraft: {str(article_draft).lower()}\n---\n## A\nTeksts", encoding="utf-8")
    out = tmp_path / "atmina"
    if article_draft:
        with pytest.raises(BoardError, match="melnraksts"):
            render_tafeles(_make_env(), out, data, articles_dir)
        assert not (out / "analizes" / "saites-tests.html").exists()
    else:
        assert render_tafeles(_make_env(), out, data, articles_dir) == 1
        assert (out / "analizes" / "saites-tests.html").exists()


def test_analyses_render_runs_draft_cleanup(tmp_path, monkeypatch):
    import src.render._orchestrator as orch
    from src.db import init_db
    from src.saeima import init_saeima_tables, init_saeima_bills
    db_path = str(tmp_path / "render.db")
    init_db(db_path)
    init_saeima_tables(db_path)
    init_saeima_bills(db_path)
    data = tmp_path / "content" / "tafeles"
    data.mkdir(parents=True)
    (data / "t.yaml").write_text(FIX.read_text(encoding="utf-8"), encoding="utf-8")
    output = tmp_path / "site"
    stale = output / "atmina" / "analizes" / "saites-tests.html"
    stale.parent.mkdir(parents=True)
    stale.write_text("vecs", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("src.render.analyses.CONTENT_DIR", tmp_path / "content")
    for name in ("_download_chart_js", "_download_annotation_plugin", "_download_d3", "_copy_curated"):
        monkeypatch.setattr(orch, name, lambda *args, **kwargs: None)
    monkeypatch.setattr(orch, "_load_analyses", lambda: [])
    monkeypatch.setattr(orch, "_load_syntheses", lambda *args: [])
    orch.generate_public_site(db_path=db_path, output_dir=str(output), only={"analizes"})
    assert not stale.exists(), "Parastajam analīžu renderam jāizdzēš tāfeles melnraksts."


@pytest.mark.parametrize("imports", [
    "from src.tafele.model import load_board; import src.render",
    "import src.render; from src.tafele.model import load_board",
])
def test_model_and_renderer_import_without_cycle(imports):
    import subprocess
    import sys
    result = subprocess.run([sys.executable, "-c", imports], capture_output=True, text=True,
                            cwd=FIX.parents[2], timeout=30)
    assert result.returncode == 0, result.stderr
