"""End-to-end: a party whose short_name contains '/' renders to a
filename-safe path, and the index link points at the same slug.

Locks task-5 behavior: short_name 'X/Y' -> partijas/x-y.html, and the
partijas.html card's data-card-href target uses the identical slug.
"""

from jinja2 import Environment, FileSystemLoader

from src.db import get_db, init_db
from src.render._common import TEMPLATES_DIR, _party_page_slug
from src.render.parties import _fetch_parties_page, render_parties
from src.saeima.schema import init_saeima_tables


def _env():
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)
    env.filters["party_page_slug"] = _party_page_slug
    env.filters["lv_plural"] = lambda n, *a: ""
    env.globals["assets_version"] = "t"
    return env


def test_slash_short_name_renders_safe_path(tmp_path):
    db_path = str(tmp_path / "t.db")
    init_db(db_path)
    init_saeima_tables(db_path)
    db = get_db(db_path)
    db.execute(
        "INSERT INTO parties (id,name,short_name,coalition_status) "
        "VALUES (1,'Suverēnā vara/Jaunlatvieši','SV/AJ','opposition')"
    )
    db.commit()

    atmina_dir = tmp_path / "out"
    atmina_dir.mkdir()
    parties = _fetch_parties_page(db)
    render_parties(_env(), db, atmina_dir, parties)

    # Detail page written to the slugified path, NOT 'sv/aj.html'.
    assert (atmina_dir / "partijas" / "sv-aj.html").exists()
    assert not (atmina_dir / "partijas" / "sv").exists()  # no nested dir

    # Index card links to the same slug via data-card-href (no inline onclick).
    index_html = (atmina_dir / "partijas.html").read_text(encoding="utf-8")
    assert 'data-card-href="partijas/sv-aj.html"' in index_html
    assert "onclick" not in index_html


def test_plain_short_name_path_unchanged(tmp_path):
    db_path = str(tmp_path / "t.db")
    init_db(db_path)
    init_saeima_tables(db_path)
    db = get_db(db_path)
    db.execute(
        "INSERT INTO parties (id,name,short_name,coalition_status) "
        "VALUES (1,'Jaunā Vienotība','JV','coalition')"
    )
    db.commit()

    atmina_dir = tmp_path / "out"
    atmina_dir.mkdir()
    parties = _fetch_parties_page(db)
    render_parties(_env(), db, atmina_dir, parties)
    assert (atmina_dir / "partijas" / "jv.html").exists()
