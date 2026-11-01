import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from src.db import get_db, init_db, store_claim
from src.saeima.schema import init_saeima_tables
from src.saeima.topics import (
    abandon_batch,
    apply_batch,
    document_key,
    freeze_batch,
    global_parity_mismatch,
    record_decision,
    rollback_batch,
    write_rollback_sql,
)

REPO = Path(__file__).resolve().parent.parent


def test_document_key_keeps_canonical_form():
    assert document_key("412/Lp14", "Grozījumi Notariāta likumā (412/Lp14)")[0] == "412/Lp14"


def test_document_key_repairs_bare_number_from_motif():
    key, _ = document_key("1179", "Grozījumi … likumā (1179/Lp14), 1.lasījums")
    assert key == "1179/Lp14"


def test_document_key_bare_number_ambiguous_returns_none():
    key, reason = document_key("1179", "Grozījumi … (1179/Lp14) … (1179/Lm14)")
    assert key is None and reason.startswith("kails numurs")


def test_document_key_from_motif_when_number_missing():
    assert document_key(None, "Grozījumi … (412/Lp14), 1.lasījums") == ("412/Lp14", "from-motif")


def test_document_key_ambiguous_motif_gets_own_key_and_flag():
    key, reason = document_key(None, "Par … (123/Lp14) un (152/Lp14) … (158/Lm14)")
    assert key.startswith("motif:") and reason == "multi"


def test_document_key_no_number_is_motif_hash():
    k1, _ = document_key(None, "Par sēdes sākšanu")
    k2, _ = document_key(None, "Par sēdes sākšanu")
    assert k1 == k2 and k1.startswith("motif:")


def test_saeimas_darbs_is_canonical():
    from src.topic_map import TOPIC_GROUPS, normalize_topic
    from src.render._common.constants import TOPIC_COLORS
    assert "Saeimas darbs" in TOPIC_GROUPS
    assert "Saeimas darbs" in TOPIC_COLORS
    assert normalize_topic("Saeimas darbs") == "Saeimas darbs"


# --- Partiju dzinējs (3. uzdevums) -----------------------------------------


@pytest.fixture
def topics_db(tmp_path):
    """Divi balsojumi par 412/Lp14, trīs `saeima_vote` ieraksti ar veco tēmu."""
    path = str(tmp_path / "topics.db")
    init_db(path)
    init_saeima_tables(path)
    db = get_db(path)
    db.execute("INSERT INTO tracked_politicians (id, name, party) VALUES (1, 'A Deputāts', 'JV')")
    db.execute("INSERT INTO tracked_politicians (id, name, party) VALUES (2, 'B Deputāts', 'NA')")
    for vid, url in ((1, "u1"), (2, "u2")):
        db.execute(
            "INSERT INTO saeima_votes (id, motif, url, document_nr, topic) VALUES (?,?,?,?,?)",
            (vid, f"Grozījumi Notariāta likumā (412/Lp14), {vid}.lasījums", url,
             "412/Lp14", "Valsts pārvalde"))
    db.commit()
    for opp, url in ((1, "u1"), (2, "u1"), (1, "u2")):
        store_claim(opp, None, "Valsts pārvalde", "Balsoja Par", None, 1.0, "r", 0.5,
                    url, "2026-01-01", claim_type="saeima_vote", db=db)
    db.commit()
    db.close()
    return path


def _decide_and_freeze(db, tmp_path):
    record_decision(db, "412/Lp14", "Tieslietas", method="human", model=None,
                    confidence=1.0, input_hash="h")
    freeze_batch(db, "b01", ["412/Lp14"])
    write_rollback_sql(db, "b01", tmp_path / "rb.sql")


def _counts(out):
    return out["votes"], out["claims"]


def _topics(db, table):
    return {r[0] for r in db.execute(f"SELECT topic FROM {table}")}


def test_apply_rewrites_votes_and_claims_and_rolls_back(topics_db, tmp_path):
    db = get_db(topics_db)
    _decide_and_freeze(db, tmp_path)
    report = apply_batch(db, "b01", require_tracked=False)
    assert report["votes"] == 2 and report["claims"] == 3
    assert report["parity_mismatch"] == 0 and report["parity_mismatch_global"] == 0
    assert _topics(db, "claims") == _topics(db, "saeima_votes") == {"Tieslietas"}
    db.executescript((tmp_path / "rb.sql").read_text(encoding="utf-8"))
    assert _topics(db, "claims") == _topics(db, "saeima_votes") == {"Valsts pārvalde"}
    assert db.execute("SELECT status FROM vote_topic_batches").fetchone()[0] == "rolled_back"


def test_rollback_batch_restores_and_refuses_twice(topics_db, tmp_path):
    db = get_db(topics_db)
    _decide_and_freeze(db, tmp_path)
    apply_batch(db, "b01", require_tracked=False)
    assert _counts(rollback_batch(db, "b01")) == (2, 3)
    assert _topics(db, "claims") == {"Valsts pārvalde"}
    with pytest.raises(RuntimeError, match="rolled_back"):
        rollback_batch(db, "b01")


def test_apply_refuses_when_topic_drifted(topics_db, tmp_path):
    db = get_db(topics_db)
    _decide_and_freeze(db, tmp_path)
    db.execute("UPDATE saeima_votes SET topic='Vide' WHERE id=1")
    db.commit()
    with pytest.raises(RuntimeError, match="drift"):
        apply_batch(db, "b01", require_tracked=False)
    assert db.execute("SELECT status FROM vote_topic_batches").fetchone()[0] == "snapshotted"
    assert _topics(db, "claims") == {"Valsts pārvalde"}


def test_apply_is_atomic_on_failure(topics_db, tmp_path, monkeypatch):
    db = get_db(topics_db)
    _decide_and_freeze(db, tmp_path)
    import src.saeima.topics as t
    monkeypatch.setattr(t, "_update_claims", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    with pytest.raises(RuntimeError, match="boom"):
        apply_batch(db, "b01", require_tracked=False)
    assert not db.in_transaction
    other = get_db(topics_db)  # cits savienojums redz tikai komitēto
    assert _topics(other, "saeima_votes") == _topics(other, "claims") == {"Valsts pārvalde"}
    assert other.execute("SELECT status FROM vote_topic_batches").fetchone()[0] == "snapshotted"


def test_apply_refuses_idempotency_collision(topics_db, tmp_path):
    """T2: politiķim 1 uz u1 jau ir ieraksts ar citu tēmu — pēc piemērošanas
    abi kļūtu par (1, u1, 'Tieslietas'), tātad atslēgas sadursme."""
    db = get_db(topics_db)
    store_claim(1, None, "Vide", "Balsoja Par", None, 1.0, "r", 0.5,
                "u1", "2026-01-01", claim_type="saeima_vote", db=db)
    db.commit()
    _decide_and_freeze(db, tmp_path)
    with pytest.raises(RuntimeError, match="sadursm"):
        apply_batch(db, "b01", require_tracked=False)
    assert db.execute("SELECT status FROM vote_topic_batches").fetchone()[0] == "snapshotted"


def test_apply_requires_committed_rollback(topics_db, tmp_path):
    db = get_db(topics_db)
    _decide_and_freeze(db, tmp_path)
    with pytest.raises(RuntimeError, match="nav komitēts"):
        apply_batch(db, "b01", require_tracked=True)


def test_freeze_refuses_duplicate_batch_and_empty_keys(topics_db, tmp_path):
    db = get_db(topics_db)
    _decide_and_freeze(db, tmp_path)
    with pytest.raises(ValueError, match="jau ir"):
        freeze_batch(db, "b01", ["412/Lp14"])
    record_decision(db, "999/Lp14", "Vide", method="human", model=None,
                    confidence=1.0, input_hash="h")
    with pytest.raises(ValueError, match="0 balsojumu"):
        freeze_batch(db, "b02", ["999/Lp14"])
    with pytest.raises(ValueError, match="nav lēmuma"):
        freeze_batch(db, "b03", ["123/Lp14"])
    with pytest.raises(ValueError, match="nav atslēgu"):
        freeze_batch(db, "bX", [])


def _second_batch(db, tmp_path, topic="Vide"):
    """Partija b02 uz tām pašām rindām (412/Lp14) ar citu tēmu, piemērota."""
    record_decision(db, "412/Lp14", topic, method="human", model=None,
                    confidence=1.0, input_hash="h")
    freeze_batch(db, "b02", ["412/Lp14"])
    write_rollback_sql(db, "b02", tmp_path / "rb2.sql")
    apply_batch(db, "b02", require_tracked=False)


def test_rollback_file_of_earlier_batch_is_noop_after_later_batch(topics_db, tmp_path):
    db = get_db(topics_db)
    _decide_and_freeze(db, tmp_path)
    apply_batch(db, "b01", require_tracked=False)
    _second_batch(db, tmp_path)
    db.executescript((tmp_path / "rb.sql").read_text(encoding="utf-8"))
    assert _topics(db, "claims") == _topics(db, "saeima_votes") == {"Vide"}
    assert db.execute("SELECT status FROM vote_topic_batches WHERE batch_id='b01'"
                      ).fetchone()[0] == "applied"


def test_rollback_batch_refuses_when_later_batch_overlaps(topics_db, tmp_path):
    db = get_db(topics_db)
    _decide_and_freeze(db, tmp_path)
    apply_batch(db, "b01", require_tracked=False)
    _second_batch(db, tmp_path)
    with pytest.raises(RuntimeError, match="vēlāk"):
        rollback_batch(db, "b01")
    assert _topics(db, "claims") == {"Vide"}
    assert _counts(rollback_batch(db, "b02")) == (2, 3)
    assert _counts(rollback_batch(db, "b01")) == (2, 3)
    assert _topics(db, "claims") == _topics(db, "saeima_votes") == {"Valsts pārvalde"}


def test_freeze_refuses_overlap_with_unapplied_batch(topics_db, tmp_path):
    db = get_db(topics_db)
    _decide_and_freeze(db, tmp_path)
    with pytest.raises(RuntimeError, match="iesaldētā"):
        freeze_batch(db, "b02", ["412/Lp14"])
    assert db.execute("SELECT count(*) FROM vote_topic_batches").fetchone()[0] == 1


def test_apply_refuses_new_vote_since_freeze(topics_db, tmp_path):
    db = get_db(topics_db)
    _decide_and_freeze(db, tmp_path)
    db.execute("INSERT INTO saeima_votes (id, motif, url, document_nr, topic) VALUES "
               "(3, 'Grozījumi Notariāta likumā (412/Lp14), 3.lasījums', 'u3', '412/Lp14',"
               " 'Valsts pārvalde')")
    db.commit()
    with pytest.raises(RuntimeError, match="drift: balsojumu kopa"):
        apply_batch(db, "b01", require_tracked=False)
    assert _topics(db, "claims") == {"Valsts pārvalde"}


def test_apply_refuses_new_vote_claim_since_freeze(topics_db, tmp_path):
    db = get_db(topics_db)
    _decide_and_freeze(db, tmp_path)
    store_claim(2, None, "Valsts pārvalde", "Balsoja Pret", None, 1.0, "r", 0.5,
                "u2", "2026-01-01", claim_type="saeima_vote", db=db)
    db.commit()
    with pytest.raises(RuntimeError, match="drift: 1 jauni"):
        apply_batch(db, "b01", require_tracked=False)


def test_apply_stops_on_batch_parity_mismatch(topics_db, tmp_path):
    """Snapshot, kurā ieraksta jaunā tēma atšķiras no balsojuma jaunās, → STOP."""
    db = get_db(topics_db)
    _decide_and_freeze(db, tmp_path)
    db.execute("UPDATE vote_topic_snapshot SET new_topic='Vide' WHERE table_name='claims'"
               " AND row_id=(SELECT min(row_id) FROM vote_topic_snapshot WHERE table_name='claims')")
    db.commit()
    with pytest.raises(RuntimeError, match="nesakrīt"):
        apply_batch(db, "b01", require_tracked=False)
    assert _topics(db, "claims") == {"Valsts pārvalde"}
    assert db.execute("SELECT status FROM vote_topic_batches").fetchone()[0] == "snapshotted"


def test_write_rollback_sql_refuses_to_overwrite(topics_db, tmp_path):
    db = get_db(topics_db)
    _decide_and_freeze(db, tmp_path)
    before = (tmp_path / "rb.sql").read_text(encoding="utf-8")
    with pytest.raises(RuntimeError, match="jau ir"):
        write_rollback_sql(db, "b01", tmp_path / "rb.sql")
    assert (tmp_path / "rb.sql").read_text(encoding="utf-8") == before


def test_rollback_batch_failing_midway_leaves_nothing_half_done(topics_db, tmp_path):
    db = get_db(topics_db)
    _decide_and_freeze(db, tmp_path)
    apply_batch(db, "b01", require_tracked=False)
    (tmp_path / "rb.sql").write_text("BEGIN;\nUPDATE claims SET topic='Vide';\nSELEKT 1;\n",
                                     encoding="utf-8")
    with pytest.raises(sqlite3.OperationalError):
        rollback_batch(db, "b01")
    assert not db.in_transaction
    assert _topics(db, "claims") == {"Tieslietas"}


def _store_post_apply_claim(db):
    """Atkārtota ielāde pēc piemērošanas: jauns deputāts uz u2 ar balsojuma JAUNO tēmu."""
    store_claim(2, None, "Tieslietas", "Balsoja Pret", None, 1.0, "r", 0.5,
                "u2", "2026-01-01", claim_type="saeima_vote", db=db)
    db.commit()


def _post_apply_topic(db):
    return db.execute("SELECT topic FROM claims WHERE opponent_id=2 AND source_url='u2'"
                      ).fetchone()[0]


def test_rollback_batch_resets_claim_created_after_apply(topics_db, tmp_path):
    db = get_db(topics_db)
    _decide_and_freeze(db, tmp_path)
    apply_batch(db, "b01", require_tracked=False)
    _store_post_apply_claim(db)
    out = rollback_batch(db, "b01")
    assert out["parity_mismatch"] == 0
    assert _post_apply_topic(db) == "Valsts pārvalde"
    assert _topics(db, "claims") == _topics(db, "saeima_votes") == {"Valsts pārvalde"}


def test_rollback_file_resets_claim_created_after_apply(topics_db, tmp_path):
    db = get_db(topics_db)
    _decide_and_freeze(db, tmp_path)
    apply_batch(db, "b01", require_tracked=False)
    _store_post_apply_claim(db)
    db.executescript((tmp_path / "rb.sql").read_text(encoding="utf-8"))
    assert _post_apply_topic(db) == "Valsts pārvalde"
    assert global_parity_mismatch(db) == 0


def test_freeze_refuses_pending_decision_unless_allowed(topics_db, tmp_path):
    db = get_db(topics_db)
    record_decision(db, "412/Lp14", "Tieslietas", method="keyword", model=None,
                    confidence=0.3, input_hash="h", review_status="pending")
    with pytest.raises(ValueError, match="pending"):
        freeze_batch(db, "b01", ["412/Lp14"])
    assert db.execute("SELECT count(*) FROM vote_topic_batches").fetchone()[0] == 0
    out = freeze_batch(db, "b01", ["412/Lp14"], allow_pending=True)
    assert out["pending"] == 1


def test_abandon_frees_overlap_and_refuses_applied(topics_db, tmp_path):
    db = get_db(topics_db)
    _decide_and_freeze(db, tmp_path)
    abandon_batch(db, "b01")
    assert db.execute("SELECT status FROM vote_topic_batches").fetchone()[0] == "abandoned"
    assert db.execute("SELECT count(*) FROM vote_topic_snapshot WHERE batch_id='b01'"
                      ).fetchone()[0] == 5  # snapshot paliek
    freeze_batch(db, "b02", ["412/Lp14"])  # pamestā partija vairs nebloķē
    write_rollback_sql(db, "b02", tmp_path / "rb2.sql")
    apply_batch(db, "b02", require_tracked=False)
    with pytest.raises(RuntimeError, match="applied"):
        abandon_batch(db, "b02")
    with pytest.raises(RuntimeError, match="abandoned"):
        apply_batch(db, "b01", require_tracked=False)


def test_record_decision_rejects_unknown_topic(topics_db):
    with pytest.raises(ValueError):
        record_decision(get_db(topics_db), "412/Lp14", "Nav tēma", method="jev",
                        model="jev-x", confidence=0.9, input_hash="h")


def test_cli_decide_freeze_apply_status(topics_db, tmp_path):
    """E2e caur `scripts/vote_topics.py` kā apakšprocesu (nekad pret ražošanas DB)."""
    env = {**os.environ, "PYTHONUTF8": "1"}

    def run(*args):
        return subprocess.run(
            [sys.executable, str(REPO / "scripts" / "vote_topics.py"), "--db", topics_db, *args],
            cwd=REPO, env=env, capture_output=True, text=True, encoding="utf-8")

    assert run("decide", "412/Lp14", "Nav tēma").returncode == 1
    ok = run("decide", "412/Lp14", "Tieslietas")
    assert ok.returncode == 0, ok.stderr
    keys = tmp_path / "keys.txt"
    keys.write_text("412/Lp14\n", encoding="utf-8")
    fr = run("freeze", "b01", "--keys-file", str(keys), "--rollback-dir", str(tmp_path))
    assert fr.returncode == 0, fr.stderr
    assert (tmp_path / "rollback_vote_topics_b01.sql").exists()
    assert run("apply", "b01").returncode == 1  # rollback fails nav komitēts
    ap = run("apply", "b01", "--no-require-tracked")
    assert ap.returncode == 0, ap.stderr
    assert "BRĪDINĀJUMS" in ap.stderr
    st = run("status")
    assert st.returncode == 0 and "applied" in st.stdout
    db = get_db(topics_db)
    assert _topics(db, "claims") == _topics(db, "saeima_votes") == {"Tieslietas"}
    rb = run("rollback", "b01")
    assert rb.returncode == 0, rb.stderr
    assert _topics(db, "claims") == {"Valsts pārvalde"}


def test_cli_freeze_rollback_write_failure_then_abandon(topics_db, tmp_path):
    """Rollback faila rakstīšana krīt → skaidrs ziņojums; `abandon` atbrīvo; jauna partija iet."""
    env = {**os.environ, "PYTHONUTF8": "1"}

    def run(*args):
        return subprocess.run(
            [sys.executable, str(REPO / "scripts" / "vote_topics.py"), "--db", topics_db, *args],
            cwd=REPO, env=env, capture_output=True, text=True, encoding="utf-8")

    assert run("decide", "412/Lp14", "Tieslietas").returncode == 0
    keys = tmp_path / "keys.txt"
    keys.write_text("412/Lp14\n", encoding="utf-8")
    (tmp_path / "rollback_vote_topics_b01.sql").write_text("-- aizņemts\n", encoding="utf-8")
    fr = run("freeze", "b01", "--keys-file", str(keys), "--rollback-dir", str(tmp_path))
    assert fr.returncode == 1 and "abandon b01" in fr.stderr and "Traceback" not in fr.stderr
    assert run("freeze", "b02", "--keys-file", str(keys),
               "--rollback-dir", str(tmp_path)).returncode == 1  # b01 vēl bloķē
    ab = run("abandon", "b01")
    assert ab.returncode == 0, ab.stderr
    fr2 = run("freeze", "b02", "--keys-file", str(keys), "--rollback-dir", str(tmp_path))
    assert fr2.returncode == 0, fr2.stderr
    assert '"pending": 0' in fr2.stdout


# --- Likumu tēmas seko lēmumiem (plāns, 10. uzd. 1.–2. solis) ----------------


def _run_cli(db_path, *args):
    env = {**os.environ, "PYTHONUTF8": "1"}
    return subprocess.run(
        [sys.executable, str(REPO / "scripts" / "vote_topics.py"), "--db", db_path, *args],
        cwd=REPO, env=env, capture_output=True, text=True, encoding="utf-8")


def _bill_topics(path):
    db = get_db(path)
    try:
        return dict(db.execute("SELECT document_nr, topic FROM saeima_bills"))
    finally:
        db.close()


def test_sync_bill_topics_from_decisions(topics_db, tmp_path):
    """E2e: lēmums → `bills-sync` (snapshot + rollback fails, nekas nemainās) →
    `bills-apply` → likuma tēma = lēmums; `pending` un bez lēmuma netiek aiztikti;
    `bills-rollback` atjauno."""
    from src.saeima.schema import init_saeima_bills
    init_saeima_bills(topics_db)
    db = get_db(topics_db)
    for nr, topic in (("412/Lp14", None), ("500/Lp14", "Vide"), ("600/Lp14", "Vide")):
        db.execute("INSERT INTO saeima_bills (document_nr, bill_type, title, topic)"
                   " VALUES (?, 'likumprojekts', 't', ?)", (nr, topic))
    db.execute("INSERT INTO saeima_votes (id, motif, url, document_nr, topic)"
               " VALUES (9, 'Grozījumi (500/Lp14)', 'u9', '500/Lp14', 'Vide')")
    db.commit()
    record_decision(db, "500/Lp14", "Izglītība", method="keyword", model=None,
                    confidence=None, input_hash="h", review_status="pending")
    db.close()
    assert _run_cli(topics_db, "decide", "412/Lp14", "Tieslietas").returncode == 0

    sy = _run_cli(topics_db, "bills-sync", "s01", "--rollback-dir", str(tmp_path))
    assert sy.returncode == 0, sy.stderr
    assert '"changed": 1' in sy.stdout and '"skipped_pending": 1' in sy.stdout
    assert '"no_decision": 1' in sy.stdout
    assert (tmp_path / "rollback_bill_topics_s01.sql").exists()
    assert _bill_topics(topics_db)["412/Lp14"] is None  # vēl nekas nav mainīts

    assert _run_cli(topics_db, "bills-apply", "s01").returncode == 1  # rollback nav komitēts
    ap = _run_cli(topics_db, "bills-apply", "s01", "--no-require-tracked")
    assert ap.returncode == 0, ap.stderr
    assert _bill_topics(topics_db) == {"412/Lp14": "Tieslietas", "500/Lp14": "Vide",
                                       "600/Lp14": "Vide"}

    rb = _run_cli(topics_db, "bills-rollback", "s01")
    assert rb.returncode == 0, rb.stderr
    assert _bill_topics(topics_db)["412/Lp14"] is None


def test_bill_sync_apply_refuses_when_topic_drifted(topics_db, tmp_path):
    from src.saeima.schema import init_saeima_bills
    from src.saeima.topics import apply_bill_sync, sync_bill_topics
    init_saeima_bills(topics_db)
    db = get_db(topics_db)
    db.execute("INSERT INTO saeima_bills (document_nr, bill_type, title, topic)"
               " VALUES ('412/Lp14', 'likumprojekts', 't', NULL)")
    db.commit()
    record_decision(db, "412/Lp14", "Tieslietas", method="human", model=None,
                    confidence=1.0, input_hash="h")
    sync_bill_topics(db, "s01", rollback_dir=tmp_path)
    db.execute("UPDATE saeima_bills SET topic='Vide' WHERE document_nr='412/Lp14'")
    db.commit()
    with pytest.raises(RuntimeError, match="drift"):
        apply_bill_sync(db, "s01", require_tracked=False)
    assert db.execute("SELECT topic FROM saeima_bills").fetchone()[0] == "Vide"


# --- Partiju plāns (plāns, 9. uzd.) -------------------------------------------


def _plan_db(path, order):
    """Dokumenti ar dažādu pašreizējo tēmu un balsojumu skaitu; `order` = ievietošanas secība."""
    init_db(path)
    init_saeima_tables(path)
    docs = {  # atslēga: (tēma, balsojumu skaits)
        "1/Lp14": ("Vide", 3), "2/Lp14": ("Valsts pārvalde", 1), "3/Lp14": ("Tieslietas", 5),
        "4/Lp14": ("Valsts pārvalde", 4), "5/Lp14": ("Izglītība", 2), "6/Lp14": ("Vide", 3),
        "152/Lp14": ("Budžets un finanses", 9),
    }
    db = get_db(path)
    vid = 0
    for key in order:
        topic, n = docs[key]
        title = ("Par valsts budžetu 2023. gadam un budžeta ietvaru 2023., 2024. un 2025. gadam"
                 if key == "152/Lp14" else "Grozījumi likumā")
        for _ in range(n):
            vid += 1
            db.execute("INSERT INTO saeima_votes (id, motif, url, document_nr, topic)"
                       " VALUES (?,?,?,?,?)", (vid, f"{title} ({key}), 2.lasījums", f"u{vid}", key, topic))
    db.commit()
    db.close()


def test_plan_orders_by_impact_deterministically_and_excludes_budget_laws(tmp_path):
    """E2e caur CLI: VP → Vide → pārējie, katrā grupā pēc balsojumu skaita (dilstoši,
    vienādos — atslēga); ievietošanas secība rezultātu nemaina; budžeta likums ārā."""
    keys = ["1/Lp14", "2/Lp14", "3/Lp14", "4/Lp14", "5/Lp14", "6/Lp14", "152/Lp14"]
    outs = []
    for i, order in enumerate((keys, keys[::-1])):
        path = str(tmp_path / f"plan{i}.db")
        _plan_db(path, order)
        out = tmp_path / f"batches{i}.csv"
        r = _run_cli(path, "plan", "--size", "3", "--out", str(out))
        assert r.returncode == 0, r.stderr
        assert "152/Lp14" in r.stdout  # izslēgtie nosaukti
        outs.append(out.read_text(encoding="utf-8"))
    assert outs[0] == outs[1]
    rows = [ln.split(",") for ln in outs[0].strip().splitlines()]
    assert rows[0] == ["batch_id", "document_key"]
    assert rows[1:] == [["b01", "4/Lp14"], ["b01", "2/Lp14"], ["b01", "1/Lp14"],
                        ["b02", "6/Lp14"], ["b02", "3/Lp14"], ["b02", "5/Lp14"]]


def test_budget_law_rule_matches_only_annual_budget_laws():
    from src.saeima.topics import is_budget_law
    for key, motif in (
        ("152/Lp14", "Par valsts budžetu 2023. gadam un budžeta ietvaru 2023., 2024. un 2025. gadam (152/Lp14), nodošana komisijām"),
        ("1130/Lp14", "Par valsts budžetu 2026. gadam un budžeta ietvaru 2026., 2027. un 2028. gadam (1130/Lp14), 3.lasījums"),
        ("9/Lp15", "Par vidēja termiņa budžeta ietvaru 2028., 2029. un 2030. gadam (9/Lp15)"),
    ):
        assert is_budget_law(key, motif), key
    for key, motif in (
        ("1130/Lm14", "Par Saeimas piekrišanu likumā “Par valsts budžetu 2026. gadam un budžeta "
                      "ietvaru 2026., 2027. un 2028. gadam” noteiktās apropriācijas pārdalei (1130/Lm14)"),
        ("851/Lm14", "Par priekšlikumu iesniegšanas kārtību (formu) 2026. gada valsts budžeta "
                     "likumprojektu paketei (851/Lm14)"),
        ("1319/Lp14", "Grozījums Likumā par budžetu un finanšu vadību (1319/Lp14)"),
    ):
        assert not is_budget_law(key, motif), key


# --- 9. uzd. 1.–2. solis: `classify` + `review-list` --------------------------


def _classify_db(path):
    """Partija b01: 412 (VP, Jev 0,75 → auto, mainīts), 413 (Tieslietas, Jev 0,95 → auto,
    nemainīts), 414 (Jev 0,5 → pending), multi motīvs, klātbūtne, 415 (jau ar lēmumu)."""
    from src.saeima.schema import init_saeima_bills
    init_db(path)
    init_saeima_tables(path)
    init_saeima_bills(path)
    votes = [
        ("Grozījumi Notariāta likumā (412/Lp14), 2.lasījums", "412/Lp14", "Valsts pārvalde"),
        ("Grozījumi Notariāta likumā (412/Lp14), 3.lasījums", "412/Lp14", "Valsts pārvalde"),
        ("Grozījumi Zemesgrāmatu likumā (413/Lp14), 2.lasījums", "413/Lp14", "Tieslietas"),
        ("Grozījumi Sporta likumā (414/Lp14), 2.lasījums", "414/Lp14", "Sports"),
        ("Par likumprojektiem (123/Lp14) un (152/Lp14), (158/Lm14)", None, "Valsts pārvalde"),
        ("Deputātu klātbūtnes reģistrācija", None, "Valsts pārvalde"),
        ("Grozījumi Pilsonības likumā (415/Lp14), 2.lasījums", "415/Lp14", "Valsts pārvalde"),
        ("Grozījumi Saeimas kārtības rullī (975/Lp14), nodošana komisijām", "975/Lp14",
         "Sociālā politika"),
    ]
    db = get_db(path)
    keys = []
    for i, (motif, nr, topic) in enumerate(votes, 1):
        db.execute("INSERT INTO saeima_votes (id, motif, url, document_nr, topic, summary)"
                   " VALUES (?,?,?,?,?,?)", (i, motif, f"https://v/{i}", nr, topic, f"Kops {i}"))
        k, _ = document_key(nr, motif)
        if k not in keys:
            keys.append(k)
    db.commit()
    record_decision(db, "415/Lp14", "Sociālā politika", method="human", model=None,
                    confidence=1.0, input_hash="manual", review_status="confirmed")
    db.close()
    return keys


def test_cli_classify_then_review_list(tmp_path, monkeypatch):
    """E2e (CLI main, bez tīkla): viens dokuments vienā Jev pieprasījumā, piesaistītais modelis;
    ≥ slieksnis → auto, zemāk → pending ar atslēgvārdu tēmu; multi bez klasifikatora;
    `review-list` atlasa pending + multi + mainītos zem 0,9, Jev ieteikums no keša."""
    import csv as _csv

    import scripts.vote_topics as vt
    import src.saeima.topic_classifiers as tc
    from src.saeima.topics import BATCH_CONFIDENCE_THRESHOLD as thr

    path = str(tmp_path / "cls.db")
    keys = _classify_db(path)
    batches = tmp_path / "batches.csv"
    batches.write_text("batch_id,document_key\n" + "".join(f"b01,{k}\n" for k in keys)
                       + "b02,999/Lp14\n", encoding="utf-8")
    monkeypatch.setattr(tc, "CACHE_PATH", tmp_path / "jev_cache.db")
    answers = {"Notariāta": ("Tieslietas", thr + 0.05), "Zemesgrāmatu": ("Tieslietas", 0.95),
               "Sporta": ("Sports", thr - 0.05)}
    calls = []

    def fake(state, questions, **kw):
        calls.append((kw.get("model"), [r["input_text"] for r in state["rows"]]))
        out = {}
        for i, r in enumerate(state["rows"]):
            topic, conf = next(v for w, v in answers.items() if w in r["input_text"])
            out[f"q{i}"] = {"type": "choice", "choice": topic, "confidence": conf}
        return {"model": kw.get("model"), "answers": out, "usage": {}}

    monkeypatch.setattr(tc, "system_one", fake)
    assert vt.main(["--db", path, "classify", "b01", "--batches", str(batches)]) == 0
    # 3 dokumenti → 3 pieprasījumi pa 1 tekstam (JEV_CHUNK_SIZE; paketē atbildes mainās).
    assert [(m, len(t)) for m, t in calls] == [("jev-1.14.0", 1)] * 3
    sent = [t[0] for _, t in calls]
    assert all(t.startswith("Virsraksts: ") and "Kopsavilkums: Kops" in t for t in sent)
    db = get_db(path)
    dec = {r[0]: tuple(r[1:]) for r in db.execute(
        "SELECT document_key, topic, method, review_status FROM saeima_document_topics")}
    db.close()
    multi_key, reg_key = keys[3], keys[4]
    assert dec["412/Lp14"] == ("Tieslietas", "jev", "auto")
    assert dec["413/Lp14"] == ("Tieslietas", "jev", "auto")
    assert dec["414/Lp14"][1:] == ("keyword", "pending")
    assert dec[multi_key][1:] == ("keyword", "pending")
    assert dec[reg_key] == ("Saeimas darbs", "keyword", "auto")
    assert dec["415/Lp14"] == ("Sociālā politika", "human", "confirmed")
    assert dec["975/Lp14"] == ("Valsts pārvalde", "keyword", "auto")  # bez zvana (3 zvani)
    # Atkārtots `classify` lēmumus nedublē un nezvana.
    assert vt.main(["--db", path, "classify", "b01", "--batches", str(batches)]) == 0
    assert len(calls) == 3

    out = tmp_path / "review.csv"
    assert vt.main(["--db", path, "review-list", "b01", "--batches", str(batches),
                    "--out", str(out)]) == 0
    with open(out, encoding="utf-8", newline="") as fh:
        rows = {r["document_key"]: r for r in _csv.DictReader(fh)}
    assert set(rows) == {"412/Lp14", "414/Lp14", multi_key}
    assert (rows["414/Lp14"]["jev_topic"], rows["414/Lp14"]["confidence"]) == ("Sports", f"{thr - 0.05:.3f}")
    assert rows["412/Lp14"]["current_topic"] == "Valsts pārvalde"
    assert rows["412/Lp14"]["url"] == "https://v/1"
    assert rows["412/Lp14"]["title"] == "Grozījumi Notariāta likumā"


def test_select_review_rows_boundaries():
    from scripts.vote_topics import select_review_rows

    def d(key, topic, status="auto", conf=0.8, multi=False, current="Vide"):
        return {"document_key": key, "current_topic": current, "topic": topic,
                "review_status": status, "confidence": conf, "multi": multi}

    picked = select_review_rows([
        d("chg-low", "Tieslietas", conf=0.89),          # mainīts, < 0,9 → jā
        d("chg-edge", "Tieslietas", conf=0.9),          # mainīts, tieši 0,9 → nē
        d("same-low", "Vide", conf=0.71),               # nemainīts → nē
        d("pend", "Vide", status="pending", conf=None),  # pending → jā
        d("multi", "Vide", status="pending", conf=None, multi=True),
        d("human", "Tieslietas", status="confirmed", conf=1.0, multi=True),  # cilvēks → nē
        d("reg", "Saeimas darbs", conf=None),             # noteikums, ne minējums → nē
    ])
    assert [(p["document_key"], p["reason"].split(":")[0].split(",")[0]) for p in picked] == [
        ("chg-low", "mainīta tēma"), ("pend", "pending"), ("multi", "multi")]
