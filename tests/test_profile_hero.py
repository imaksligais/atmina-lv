"""Garš bio nedrīkst atstāt tukšu galveni vai pārbīdīt cilnes, to atverot."""
from pathlib import Path
import shutil

import pytest
import yaml

sync_api = pytest.importorskip("playwright.sync_api")


def test_long_bio_hero_columns_and_popover_keep_tabs_still(tmp_path, monkeypatch):
    from src.db import get_db, init_db
    from src.render._common import _lv_plural
    from src.render.politicians import render_politicians
    from src.saeima.schema import init_saeima_tables
    from tests.test_render_own_pubs import _env, _politician

    db_path = str(tmp_path / "fixture.db")
    init_db(db_path)
    init_saeima_tables(db_path)
    db = get_db(db_path)
    db.execute("INSERT INTO tracked_politicians (id,name,relationship_type) "
               "VALUES (1,'Aleksandrs Pārbaude','tracked')")
    db.commit()
    bio_path = tmp_path / "bio.yaml"
    bio_path.write_text(yaml.safe_dump([{
        "politician_id": 1, "name": "Aleksandrs Pārbaude", "status": "ok",
        "birth_year": 1983, "source_url": "https://example.com/cvk",
        "education": [{"institution": "Latvijas Universitāte", "year": 2007,
                       "degree": "Maģistra grāds politikā un starptautiskajās attiecībās"}] * 3,
        "workplaces": [{"position": "Valdes loceklis", "employer": employer} for employer in
                       ["Testa pašvaldība", "Testa politiskā partija",
                        "Testa politisko partiju apvienība"] * 5],
    }], allow_unicode=True), encoding="utf-8")
    monkeypatch.setattr("src.render.bio.CVK_BIO_PATH", bio_path)
    monkeypatch.setattr("src.render.bio.EP_BIO_PATH", tmp_path / "absent.yaml")
    out = tmp_path / "site"
    out.mkdir()
    env = _env()
    env.filters["lv_plural"] = _lv_plural
    person = _politician(1, "Aleksandrs Pārbaude", "testa-persona", "politician")
    person["role_label"] = "15. Saeimā ievēlēts — Testa saraksts, Rīga"
    render_politicians(env, db, out, [person], pid_to_syntheses={})
    db.close()
    shutil.copytree(Path(__file__).resolve().parents[1] / "assets", out / "assets", dirs_exist_ok=True)

    with sync_api.sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900}, reduced_motion="reduce")
        page.goto((out / "politiki/testa-persona.html").as_uri())
        page.evaluate("document.fonts.ready")
        geometry = page.evaluate("""() => {
          const hero = document.querySelector('.pp-hero');
          const identity = document.querySelector('.pp-identity') || document.querySelector('.pp-id');
          const bio = document.querySelector('.profile-bio');
          const h = hero.getBoundingClientRect(), i = identity.getBoundingClientRect();
          const b = bio.getBoundingClientRect(), css = getComputedStyle(hero);
          return {height: h.height, tallest: Math.max(i.height, b.height),
            padding: parseFloat(css.paddingBlockStart) + parseFloat(css.paddingBlockEnd),
            bottomGap: Math.abs(i.bottom - b.bottom),
            beside: i.right <= b.left, tabs: document.querySelector('.pp-tabs').getBoundingClientRect().top};
        }""")
        # Old <summary> is deliberately accepted here so the red run measures
        # the actual layout shift, rather than merely failing on a selector.
        page.get_by_text("Vēl:", exact=False).first.click()
        panel = page.locator(".profile-bio-rest[popover]")
        opened = panel.count() == 1 and panel.evaluate("e => e.matches(':popover-open')")
        tabs_after = page.locator(".pp-tabs").bounding_box()["y"]
        browser.close()
    print(f"\nHero: {geometry}; tabs after: {tabs_after}; popover: {opened}")
    failures = []
    if not geometry["beside"] or geometry["bottomGap"] > 40:
        failures.append(f"identity/bio bottom gap: {geometry['bottomGap']} px")
    if geometry["height"] > geometry["tallest"] + geometry["padding"] + 1:
        failures.append("hero exceeds its taller column plus padding")
    if not opened or abs(tabs_after - geometry["tabs"]) > 1:
        failures.append(f"popover={opened}; tab shift={tabs_after - geometry['tabs']} px")
    assert not failures, "; ".join(failures)
