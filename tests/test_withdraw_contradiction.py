"""Atsaukta PUBLICĒTA pretruna (`confirmed = -1`) — rakstīšanas vārti un lapa.

Plāns docs/plans/2026-09-30-pretrunas-atsaukums.md. Kļūmes, ko šie testi ķer:

1. **Salauzta saite publicētā pārskatā.** Pārskati ir append-only un saista uz
   `/pretrunas/<id>.html`. Ja atsaukta pretruna vienkārši pazūd no rendera (kā
   `confirmed=0`), saite ved uz 404 un `check_output` bloķē deploy. Tāpēc
   atsauktajai rindai JĀBŪT lapai kokā — ar labojuma piezīmi un `noindex`.
2. **Atsaukta lapa sitemapā / sarakstā.** Labojuma lapa nedrīkst kļūt par
   indeksējamu saturu: nav sitemapā, nav `pretrunas.html` sarakstā, nav OG
   kartītes. Un `check_output` nedrīkst to prasīt sitemapā (citādi katrs
   atsaukums nogāž deploy no otras puses).
3. **Atsaukums, kas nav atsaukums.** `withdraw_contradiction` drīkst pārvērst
   tikai publicētu (`confirmed=1`) rindu — kandidātu (`0`) „atsaukt" nozīmētu
   uzrakstīt publisku labojuma lapu par kaut ko, kas nekad nav publicēts — un
   piezīmei (tā iet publiskajā lapā burtiski) jāiziet LV diakritikas vārtos.

Neviens tests neaiztiek produkcijas DB (tests/conftest.py § 4): viss iet caur
pagaidu DB `tmp_path`.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import timedelta
from pathlib import Path

import pytest

from src.db import get_db, init_db, today_lv, withdraw_contradiction
from src.saeima.schema import init_saeima_bills, init_saeima_tables

REPO = Path(__file__).resolve().parent.parent

NOTE = (
    "Pretruna atsaukta 2026-09-30. Tās agrākā puse bija Saeimas balsojums, "
    "kurā politiķis nerunā, tāpēc tas nav viņa izteikums, un pretruna nav pamatota."
)
# Tā pati piezīme bez garumzīmēm — T4 konteksta dreifa paraksts.
NOTE_STRIPPED = (
    "Pretruna atsaukta 2026-09-30. Tas agraka puse bija Saeimas balsojums, "
    "kura politikis neruna, tapec tas nav vina izteikums, un pretruna nav pamatota."
)


def _seed_db(path: str) -> str:
    init_db(path)
    init_saeima_tables(path)
    init_saeima_bills(path)
    db = get_db(path)
    yesterday = (today_lv() - timedelta(days=1)).strftime("%Y-%m-%d")
    db.executescript(f"""
        INSERT INTO parties (id, name, short_name) VALUES (1, 'Jaunā Vienotība', 'JV');
        INSERT INTO tracked_politicians (id, name, party, role, relationship_type)
            VALUES (1, 'Testa Politiķis', 'Jaunā Vienotība', 'Saeimas deputāts', 'tracked');
        INSERT INTO documents (id, source_url, title, content, content_hash, platform, scraped_at)
            VALUES (1, 'https://example.lv/a', 'A', 'teksts', 'h1', 'web', '{yesterday} 10:00:00');
        INSERT INTO claims (id, opponent_id, document_id, topic, stance, source_url, stated_at, claim_type)
            VALUES (1, 1, 1, 'Budžets un finanses', 'Atbalsta deficītu', 'https://example.lv/a', '{yesterday} 10:00:00', 'position'),
                   (2, 1, 1, 'Budžets un finanses', 'Iebilst deficītam', 'https://example.lv/a', '{yesterday} 11:00:00', 'position');
        -- #1 paliek publicēta, #2 publicēta → tiks atsaukta, #3 kandidāts
        INSERT INTO contradictions (id, opponent_id, claim_old_id, claim_new_id, topic, summary, severity, salience, reviewed, confirmed, detected_at)
            VALUES (1, 1, 1, 2, 'Budžets un finanses', 'Paliekoša pretruna', 'reversal', 0.8, 1, 1, '{yesterday} 12:00:00'),
                   (2, 1, 1, 2, 'Budžets un finanses', 'Sākotnējais atsauktās kopsavilkums', 'direct_contradiction', 0.9, 1, 1, '{yesterday} 13:00:00'),
                   (3, 1, 1, 2, 'Budžets un finanses', 'Kandidāte', 'minor_shift', 0.2, 1, 0, '{yesterday} 14:00:00');
    """)
    db.commit()
    db.close()
    return path


@pytest.fixture
def db_path(tmp_path):
    return _seed_db(str(tmp_path / "withdraw.db"))


def _row(db_path, cid):
    db = get_db(db_path)
    try:
        return dict(db.execute(
            "SELECT confirmed, withdrawn_at, withdrawn_note, claim_old_id, claim_new_id"
            " FROM contradictions WHERE id = ?", (cid,)).fetchone())
    finally:
        db.close()


# ── 3. withdraw_contradiction vārti ────────────────────────────────────────

def test_withdraw_sets_minus_one_note_and_lv_time_keeps_claim_refs(db_path):
    withdraw_contradiction(2, NOTE, db_path=db_path)
    r = _row(db_path, 2)
    assert r["confirmed"] == -1
    assert r["withdrawn_note"] == NOTE
    assert r["withdrawn_at"][:10] == today_lv().isoformat()  # LV kalendārs, now_lv()
    # Claim atsauces NEaiztiek — tās NULL-ē tikai datu skripts, ja claim dzēš.
    assert (r["claim_old_id"], r["claim_new_id"]) == (1, 2)


def test_withdraw_refuses_candidate_row(db_path):
    with pytest.raises(ValueError, match="confirmed=1"):
        withdraw_contradiction(3, NOTE, db_path=db_path)
    assert _row(db_path, 3)["confirmed"] == 0
    assert _row(db_path, 3)["withdrawn_note"] is None


def test_withdraw_refuses_already_withdrawn_row(db_path):
    """Otrs atsaukums klusi pārrakstītu publicēto labojuma piezīmi."""
    withdraw_contradiction(2, NOTE, db_path=db_path)
    with pytest.raises(ValueError, match="confirmed=1"):
        withdraw_contradiction(2, NOTE + " Papildinājums.", db_path=db_path)
    assert _row(db_path, 2)["withdrawn_note"] == NOTE


def test_withdraw_refuses_missing_row(db_path):
    with pytest.raises(ValueError, match="neeksistē"):
        withdraw_contradiction(999, NOTE, db_path=db_path)


@pytest.mark.parametrize("bad", ["", "   \n "])
def test_withdraw_refuses_empty_note(db_path, bad):
    with pytest.raises(ValueError, match="tukša"):
        withdraw_contradiction(2, bad, db_path=db_path)
    assert _row(db_path, 2)["confirmed"] == 1


def test_withdraw_refuses_stripped_diacritics_note(db_path):
    with pytest.raises(ValueError, match="diakritikas"):
        withdraw_contradiction(2, NOTE_STRIPPED, db_path=db_path)
    assert _row(db_path, 2)["confirmed"] == 1


def test_withdraw_with_caller_connection_does_not_commit(db_path):
    """Datu skripts dzēš claim tajā pašā `with db:` — atsaukumam jāatritinās līdzi."""
    db = get_db(db_path)
    try:
        withdraw_contradiction(2, NOTE, db=db)
        db.rollback()
    finally:
        db.close()
    assert _row(db_path, 2)["confirmed"] == 1


def test_tools_wrapper_reports_refusal_as_error(db_path, monkeypatch):
    import json

    import src.db as db_mod
    import src.tools as tools

    real = db_mod.withdraw_contradiction
    monkeypatch.setattr(
        tools, "db_withdraw_contradiction",
        lambda cid, note: real(cid, note, db_path=db_path),
    )
    assert json.loads(tools.withdraw_contradiction(3, NOTE))["status"] == "error"
    ok = json.loads(tools.withdraw_contradiction(2, NOTE))
    assert ok["status"] == "success" and ok["confirmed"] == -1


def test_migration_adds_columns_to_pre_existing_db(tmp_path):
    """Dzīvā DB ir vecāka par schema.sql kolonnām — tās pievieno TIKAI kāpnes."""
    import sqlite3

    from src.db_migrations import apply_migrations

    path = tmp_path / "old.db"
    init_db(str(path))
    db = sqlite3.connect(path)
    db.execute("ALTER TABLE contradictions DROP COLUMN withdrawn_at")
    db.execute("ALTER TABLE contradictions DROP COLUMN withdrawn_note")
    apply_migrations(db)
    apply_migrations(db)  # idempotenti
    cols = {r[1] for r in db.execute("PRAGMA table_info(contradictions)")}
    db.close()
    assert {"withdrawn_at", "withdrawn_note"} <= cols


# ── 1+2. Renders: labojuma lapa kokā, bet ne sitemapā / sarakstā ───────────

@pytest.fixture(scope="module")
def rendered(tmp_path_factory):
    """Viens renders (~8 s) visiem trim rendera testiem — caur ĪSTO orķestratoru,
    lai tiek pārbaudīta arī `generate_public_site` → `render_contradictions`
    sasaiste un `_generate_sitemap`, ne tikai veidne."""
    import src.render._orchestrator as orch
    import src.render.contradictions as contra_mod

    base = tmp_path_factory.mktemp("withdraw_render")
    db_path = _seed_db(str(base / "withdraw.db"))
    withdraw_contradiction(2, NOTE, db_path=db_path)
    og_ids: list[int] = []

    def _no_playwright(contradictions, env, out_dir):
        og_ids.extend(c["id"] for c in contradictions)
        return 0

    with pytest.MonkeyPatch.context() as mp:
        mp.chdir(REPO)
        mp.setattr(orch, "_download_chart_js", lambda *a, **k: None)
        mp.setattr(orch, "_download_annotation_plugin", lambda *a, **k: None)
        mp.setattr(contra_mod, "_render_og_cards", _no_playwright)
        orch.generate_public_site(
            db_path=db_path, output_dir=str(base / "site"), only={"pretrunas", "static"},
        )
    return base / "site" / "atmina", og_ids


def test_withdrawn_page_exists_with_note_and_noindex(rendered):
    site, _ = rendered
    page = site / "pretrunas" / "2.html"
    assert page.exists(), "atsauktajai pretrunai nav lapas — publicēta pārskata saite ved uz 404"
    html = page.read_text(encoding="utf-8")
    assert '<meta name="robots" content="noindex">' in html
    assert NOTE in html
    assert "Pretruna atsaukta" in html
    assert "Sākotnējais teksts (atsaukts)" in html
    assert "Sākotnējais atsauktās kopsavilkums" in html
    assert 'href="../politiki/testa-politikis.html"' in html
    assert "assets/og/pretruna-2.png" not in html  # nav savas OG kartītes


def test_withdrawn_page_not_in_sitemap_list_or_og(rendered):
    site, og_ids = rendered
    sitemap = (site / "sitemap.xml").read_text(encoding="utf-8")
    assert "/pretrunas/1.html" in sitemap  # saucējs: sitemap tiešām lists pretrunas
    assert "/pretrunas/2.html" not in sitemap
    listing = (site / "pretrunas.html").read_text(encoding="utf-8")
    assert "pretrunas/1.html" in listing or 'id="pretruna-1"' in listing or "Paliekoša pretruna" in listing
    assert "Sākotnējais atsauktās kopsavilkums" not in listing
    assert og_ids == [1]
    # Publicētā lapa nav noindex — citādi noindex izslēgšana check_output
    # pārbaudē klusi aprītu visu vertikāli.
    assert "noindex" not in (site / "pretrunas" / "1.html").read_text(encoding="utf-8")


def test_check_output_accepts_withdrawn_page_outside_sitemap(rendered, monkeypatch):
    site, _ = rendered
    spec = importlib.util.spec_from_file_location("check_output", REPO / "scripts" / "check_output.py")
    check_output = importlib.util.module_from_spec(spec)
    sys.modules["check_output_withdraw"] = check_output
    spec.loader.exec_module(check_output)
    monkeypatch.setattr(check_output, "ROOT", site)
    problems = check_output.check_sitemap([])
    assert not [p for p in problems if "pretrunas/" in p], problems
