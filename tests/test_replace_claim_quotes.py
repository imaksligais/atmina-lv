"""scripts/replace_claim_quotes.py — citāts drīkst mainīties TIKAI uz burtisku
teksta fragmentu no paša claim dokumenta (operatora lēmums 2026-09-23)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db import get_db, init_db  # noqa: E402
import scripts.replace_claim_quotes as rq  # noqa: E402

DOC = ("Virsraksts — žurnālista ievads par ministru. "
       "\"Mums ir jābūt  pietiekami elastīgiem un pašpietiekamiem,\" sacīja ministrs. "
       "Nodokļu &quot;slogs&quot; nemainīsies.")


@pytest.fixture
def db_path(tmp_path):
    p = str(tmp_path / "t.db")
    init_db(db_path=p)
    db = get_db(p)
    db.execute("INSERT INTO tracked_politicians (id, name) VALUES (1, 'Ministrs')")
    db.execute("INSERT INTO documents (id, content, content_hash, platform, source_url) "
               "VALUES (10, ?, 'h', 'web', 'https://x.lv/1')", (DOC,))
    db.execute("INSERT INTO claims (id, opponent_id, document_id, topic, stance, quote) "
               "VALUES (100, 1, 10, 'Tēma', 'nostāja', 'žurnālista ievads par ministru')")
    db.commit()
    db.close()
    return p


def _quote(p, cid=100):
    db = get_db(p)
    q = db.execute("SELECT quote FROM claims WHERE id=?", (cid,)).fetchone()[0]
    db.close()
    return q


GOOD = "Mums ir jābūt pietiekami elastīgiem un pašpietiekamiem,"


def test_verbatim_quote_is_accepted_and_written_with_rollback_first(db_path, tmp_path):
    rb = tmp_path / "rb.sql"
    s = rq.run([{"claim_id": 100, "quote": GOOD}], db_path=db_path,
               apply=True, rollback_path=str(rb))
    assert s["updated"] == 1
    assert _quote(db_path) == GOOD
    assert "žurnālista ievads par ministru" in rb.read_text(encoding="utf-8")


def test_rollback_restores_old_quote(db_path, tmp_path):
    rb = tmp_path / "rb.sql"
    rq.run([{"claim_id": 100, "quote": GOOD}], db_path=db_path,
           apply=True, rollback_path=str(rb))
    db = get_db(db_path)
    db.executescript(rb.read_text(encoding="utf-8"))
    db.commit()
    db.close()
    assert _quote(db_path) == "žurnālista ievads par ministru"


@pytest.mark.parametrize("bad", [
    "Mums ir jābūt […] pašpietiekamiem",                     # izgriezums
    "mums ir jābūt pietiekami elastīgiem un pašpietiekamiem",  # reģistrs
    "Mums ir jabut pietiekami elastigiem un pasietiekamiem",  # bez garumzīmēm
    "Mums ir jābūt ļoti elastīgiem un pašpietiekamiem valstij",  # izdomāts
])
def test_non_verbatim_is_refused_and_db_untouched(db_path, tmp_path, bad):
    s = rq.run([{"claim_id": 100, "quote": bad}], db_path=db_path,
               apply=True, rollback_path=str(tmp_path / "rb.sql"))
    assert s.get("not_verbatim") == 1 and "updated" not in s
    assert _quote(db_path) == "žurnālista ievads par ministru"


def test_entities_and_whitespace_in_stored_text_are_normalized(db_path):
    s = rq.run([{"claim_id": 100, "quote": 'Nodokļu "slogs" nemainīsies.'}],
               db_path=db_path)
    assert s["ok"] == 1


def test_dry_run_writes_nothing(db_path):
    s = rq.run([{"claim_id": 100, "quote": GOOD}], db_path=db_path)
    assert s["ok"] == 1
    assert _quote(db_path) == "žurnālista ievads par ministru"


def test_missing_claim_and_short_quote_are_classified(db_path):
    s = rq.run([{"claim_id": 999, "quote": GOOD}, {"claim_id": 100, "quote": "Mums"}],
               db_path=db_path)
    assert s["claim_missing"] == 1 and s["too_short"] == 1


def test_apply_without_rollback_raises(db_path):
    with pytest.raises(ValueError):
        rq.run([{"claim_id": 100, "quote": GOOD}], db_path=db_path, apply=True)
