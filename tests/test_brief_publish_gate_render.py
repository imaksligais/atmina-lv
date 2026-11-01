"""An unapproved daily brief is NOT rendered — on any surface.

2026-10-26: a daily brief stored in the DB but not yet approved
(`publish_approvals`, T15) blocked EVERY deploy. With the page in the tree the
deploy preflight (`scripts/check_output.py --publish-gate-only`) refused it;
with the page removed, `index.html`, `blog.html`, the previous day's prev/next
link and `sitemap.xml` still pointed at it and the link check failed. The
render must not emit the draft at all, so the tree is deployable while a
draft waits for proofreading. `include_drafts=True` (`--drafts`) is the
opt-in for proofreading the draft in rendered HTML.

Briefs dated before 2026-08-18 (the day the explicit approval was introduced)
were all published without an approval row and stay on the site.

Real orchestrator, temp DB; the live DB is never touched.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from src.db import get_db, init_db
from src.saeima.schema import init_saeima_bills, init_saeima_tables

APPROVED = "2031-10-24"   # far future: no collision with real content links
DRAFT = "2031-10-25"      # adjacent later day, no publish_approvals row
LEGACY = "2026-08-17"     # before the approval flag existed, no row either


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    init_saeima_tables(path)
    init_saeima_bills(path)
    db = get_db(path)
    for day in (LEGACY, APPROVED, DRAFT):
        db.execute(
            "INSERT INTO context_notes (topic, note_type, content, created_at)"
            " VALUES (?, 'daily_brief', ?, ?)",
            (f"dienas pārskats {day}", f"# Dienas pārskats — {day}\n\nTeksts.",
             f"{day} 21:00:00"),
        )
    db.execute(
        "INSERT INTO publish_approvals (subject_key, approved_at) VALUES (?, ?)",
        (APPROVED, f"{APPROVED} 22:00:00"),
    )
    db.commit()
    db.close()
    yield path
    try:
        os.remove(path)
    except OSError:
        pass


def _render(db_path: str, out: Path, **kw) -> Path:
    import src.render._orchestrator as orch
    from src.render._common import og_render

    def _fake_shoot(todo):
        for out_path, _html in todo:
            Path(out_path).write_bytes(b"png")
            yield out_path

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(og_render, "_shoot", _fake_shoot)
        for name in ("_download_chart_js", "_download_annotation_plugin", "_download_d3"):
            mp.setattr(orch, name, lambda *a, **k: None)
        orch.generate_public_site(
            db_path=db_path, output_dir=str(out),
            only={"blog", "dashboard", "static"}, **kw,
        )
    return out / "atmina"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def test_unapproved_brief_absent_from_every_surface(db_path, tmp_path):
    site = _render(db_path, tmp_path)
    # Bare file name: the index pages link `blog/<slug>.html`, a post's
    # prev/next links are relative (`<slug>.html`).
    draft_ref = f"{DRAFT}.html"

    leaks = [
        page for page in ("sitemap.xml", "index.html", "blog.html", f"blog/{APPROVED}.html")
        if draft_ref in _read(site / page)
    ]
    assert leaks == [], f"surfaces linking the unapproved draft: {leaks}"
    assert sorted(p.stem for p in (site / "blog").glob("*.html")) == [LEGACY, APPROVED]
    # Denominator: the same surfaces DO carry the approved brief.
    assert f"blog/{APPROVED}.html" in _read(site / "sitemap.xml")
    assert f"blog/{APPROVED}.html" in _read(site / "index.html")
    assert f"blog/{APPROVED}.html" in _read(site / "blog.html")
    assert f'href="{LEGACY}.html"' in _read(site / "blog" / f"{APPROVED}.html")  # prev link


def test_unapproved_brief_image_candidates_stay_out_of_the_tree(db_path, tmp_path):
    """The draft's page is gone, so its featured-image candidates must be too:
    a full-tree deploy would otherwise serve them at a guessable URL (2026-10-26)."""
    from PIL import Image

    src = tmp_path / "images" / "briefs"
    src.mkdir(parents=True)
    db = get_db(db_path)
    for day, approved in ((APPROVED, 1), (DRAFT, 0)):
        png = src / f"{day}-dienas-parskats-abc.png"
        Image.new("RGB", (64, 36)).save(png)
        note_id = db.execute(
            "SELECT id FROM context_notes WHERE topic = ?", (f"dienas pārskats {day}",)
        ).fetchone()[0]
        db.execute(
            "INSERT INTO brief_images (note_id, image_path, prompt, model, generated_at, approved)"
            " VALUES (?, ?, 'p', 'm', ?, ?)",
            (note_id, str(png), f"{day} 21:30:00", approved),
        )
    db.commit()
    db.close()

    site = _render(db_path, tmp_path)
    copied = sorted(p.name for p in (site / "images" / "briefs").iterdir())
    assert not [n for n in copied if n.startswith(DRAFT)], copied
    assert [n for n in copied if n.startswith(APPROVED)], copied  # denominator


def test_drafts_opt_in_emits_the_unapproved_brief(db_path, tmp_path):
    site = _render(db_path, tmp_path, include_drafts=True)

    assert (site / "blog" / f"{DRAFT}.html").exists()
