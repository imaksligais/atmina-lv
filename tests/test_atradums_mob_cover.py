"""Atraduma vāks telefonā: ja blakus vākam ir <stem>-mob.png, lapa to rāda
caur <picture> (≤700px), nevis samazina 16:9 hero līdz nesalasāmam.

Kļūme, ko tas ķer: veidne rāda tikai -hero.webp, un telefonā vāka avotu
rinda ir ~3 px (LZA un S-Baltic atradumi 2026-10-24).
"""
from __future__ import annotations

from src.render import _orchestrator as orch
from src.render.analyses import render_analyses
from src.render._orchestrator import _make_env


def _env():

    env = _make_env()
    for name in ("lv_date", "lv_date_short", "lv_dates_in_text"):
        env.filters[name] = getattr(orch, name)
    env.globals["assets_version"] = "test"
    return env


def _analysis(slug: str) -> dict:
    return {
        "slug": slug, "title": "T", "date": "2026-10-24", "description": "D",
        "kind": "tematiska", "image_filename": f"{slug}-vaks.png",
        "content_html": "<p>x</p>",
    }


def test_mob_cover_used_only_when_file_exists(tmp_path):
    img = tmp_path / "images" / "analizes"
    img.mkdir(parents=True)
    (img / "ar-mob-vaks-mob.png").write_bytes(b"png")
    render_analyses(_env(), tmp_path, [_analysis("ar-mob"), _analysis("bez-mob")])

    with_mob = (tmp_path / "analizes" / "ar-mob.html").read_text(encoding="utf-8")
    assert 'media="(max-width: 700px)" srcset="../images/analizes/ar-mob-vaks-mob.png"' in with_mob
    assert "brief-hero--mob" in with_mob

    without = (tmp_path / "analizes" / "bez-mob.html").read_text(encoding="utf-8")
    assert "-mob.png" not in without
    assert "brief-hero--mob" not in without
