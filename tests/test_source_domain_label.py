"""Avota etiķete claim virsmās nāk no ``documents.source_domain``, ne URL hosta.

Verdikts 41 (2026-09-06): 2 125 doki un 176 pozīcijas nes ``pmo.ee`` URL, bet
visiem ``documents.source_domain`` ir ``tvnet.lv`` un tas ir pareizais izdevējs.
Līdz šim katra claim virsma etiķeti atvasināja no URL hosta, tāpēc lasītājam
izdevējs bija ``pmo.ee``. URL NEmigrē — tas ir idempotences trijnieka daļa —,
tāpēc labojums ir tikai etiķetes atvasināšanas vietās.

Ceļi, ko šis fails sedz: Pozīcijas plūsma, tēmas lapa, „Uzmanības centrā",
pretrunu bagātināšana un dienas pārskata skelets.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = (Path(__file__).resolve().parents[1] / "src" / "schema.sql").read_text(encoding="utf-8")

PMO_URL = "https://pmo.ee/8540463"
PMO_URL_2 = "https://pmo.ee/8540464"


def make_db() -> sqlite3.Connection:
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    return db


def seed_doc(db, doc_id: int, url: str, domain: str | None = "tvnet.lv") -> int:
    db.execute(
        "INSERT INTO documents (id, content, content_hash, source_url, source_domain,"
        " platform, scraped_at) VALUES (?,?,?,?,?, 'web', '2026-09-01 10:00:00')",
        (doc_id, "Raksta teksts.", f"hash-{doc_id}", url, domain),
    )
    return doc_id


def seed_pol(db, pid: int, name: str, party: str | None = "Partija A") -> None:
    db.execute(
        "INSERT INTO tracked_politicians (id, name, party, relationship_type)"
        " VALUES (?,?,?, 'tracked')",
        (pid, name, party),
    )


def seed_claim(
    db,
    claim_id: int,
    pid: int,
    doc_id: int | None,
    url: str,
    topic: str = "Budžets un finanses",
    stated_at: str = "2026-09-01 12:00:00",
    quote: str | None = None,
) -> int:
    db.execute(
        "INSERT INTO claims (id, opponent_id, document_id, topic, stance, quote,"
        " confidence, salience, stated_at, created_at, claim_type, source_url)"
        " VALUES (?,?,?,?,?,?, 0.9, 0.9, ?, ?, 'position', ?)",
        (claim_id, pid, doc_id, topic, f"atbalsta {topic}", quote,
         stated_at, stated_at, url),
    )
    return claim_id


# --- 1. Kopīgā palīgfunkcija ------------------------------------------------

def test_domain_label_prefers_stored_source_domain():
    from src.render._common import _domain_label

    assert _domain_label("tvnet.lv", PMO_URL) == "tvnet.lv"
    assert _domain_label("www.lsm.lv", "https://www.lsm.lv/a/1") == "lsm.lv"
    # Bez dokumenta rindas (piem. saeima_vote claim) paliek vecais ceļš.
    assert _domain_label(None, "https://titania.saeima.lv/x") == "titania.saeima.lv"
    assert _domain_label(None, None) is None


# --- 2. Pozīcijas plūsma ----------------------------------------------------

def test_positions_feed_labels_pmo_url_as_tvnet():
    from src.render.positions import _fetch_claims

    db = make_db()
    seed_pol(db, 1, "Anna Bērza")
    seed_doc(db, 501, PMO_URL)
    seed_claim(db, 9001, 1, 501, PMO_URL)

    claims = _fetch_claims(db)
    assert len(claims) == 1
    assert claims[0]["source_domain"] == "tvnet.lv"
    assert claims[0]["source_url"] == PMO_URL  # URL nemainās


# --- 3. Tēmas lapa ----------------------------------------------------------

def test_topic_detail_labels_pmo_url_as_tvnet():
    from src.render.topics import _fetch_topic_detail

    db = make_db()
    seed_pol(db, 1, "Anna Bērza")
    seed_doc(db, 502, PMO_URL)
    seed_claim(db, 9002, 1, 502, PMO_URL)

    detail = _fetch_topic_detail(
        db, "Budžets un finanses", syntheses=[], all_topics=[],
    )
    positions = detail["latest_positions"]
    assert len(positions) == 1
    assert positions[0]["source_domain"] == "tvnet.lv"


# --- 4. „Uzmanības centrā" citāts -------------------------------------------

def test_focus_quote_labels_pmo_url_as_tvnet():
    from src.render.focus import _quote_of_day

    db = make_db()
    seed_pol(db, 1, "Anna Bērza")
    seed_doc(db, 503, PMO_URL)
    db.execute(
        "INSERT INTO claims (id, opponent_id, document_id, topic, stance, quote,"
        " confidence, salience, stated_at, created_at, claim_type, source_url)"
        " VALUES (9003, 1, 503, 'Budžets un finanses', 'atbalsta', ?,"
        " 0.9, 0.9, DATETIME('now', '-1 days'), DATETIME('now', '-1 days'),"
        " 'position', ?)",
        ("A" * 80, PMO_URL),
    )

    card = _quote_of_day(db)
    assert card is not None
    assert card["source_domain"] == "tvnet.lv"


# --- 5. Pretrunu bagātināšana -----------------------------------------------

def test_contradiction_enrichment_labels_pmo_url_as_tvnet():
    from src.render._common.enrich import _enrich_contradiction

    db = make_db()
    seed_pol(db, 1, "Anna Bērza")
    seed_doc(db, 504, PMO_URL)
    seed_doc(db, 505, PMO_URL_2)

    d = {
        "severity": "reversal",
        "politician_name": "Anna Bērza",
        "party": "Partija A",
        "old_date": "2026-08-01",
        "new_date": "2026-09-01",
        "old_source": PMO_URL,
        "new_source": PMO_URL_2,
        "summary": "Kopsavilkums.",
    }
    _enrich_contradiction(d, db)
    assert d["old_source_domain"] == "tvnet.lv"
    assert d["new_source_domain"] == "tvnet.lv"


# --- 6. Dienas pārskata skelets ---------------------------------------------

def test_brief_skeleton_labels_pmo_url_as_tvnet(tmp_path):
    from src.briefs import generate_daily_brief

    db_path = str(tmp_path / "brief.db")
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    seed_pol(db, 1, "Anna Bērza")
    seed_doc(db, 506, PMO_URL)
    seed_claim(db, 9006, 1, 506, PMO_URL, stated_at="2026-09-01 12:00:00")
    db.commit()
    db.close()

    md = generate_daily_brief(db_path, date="2026-09-01")
    assert "[tvnet.lv](https://pmo.ee/8540463)" in md
    assert "[pmo.ee]" not in md
