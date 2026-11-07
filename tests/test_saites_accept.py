import json
import os
import tempfile

from src.db import init_db, get_db
from scripts.saites_accept import accept, reject


def _db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    db = get_db(path)
    for pid, name in [(10, "Andris Kulbergs"), (6, "Jānis Dombrava")]:
        db.execute("INSERT INTO tracked_politicians (id, name, name_forms) VALUES (?,?,?)", (pid, name, json.dumps([name])))
    db.execute("INSERT INTO documents (id, content, content_hash, source_url) VALUES (1, 'x', 'h1', 'https://lsm.test/1')")
    db.execute("INSERT INTO tension_proposals (id, document_id, source_pid, target_pid, relation, p_link, p_relation, p_speaks) "
               "VALUES (5, 1, 10, 6, 'atbalsts', 0.95, 0.9, 0.97)")
    db.commit()
    db.close()
    return path


def test_accept_writes_tension_and_marks_proposal():
    path = _db_path()
    tid = accept(path, 5, topic="Iekšlietas", description="Kulbergs pauž pilnīgu atbalstu Dombravam.")
    db = get_db(path)
    t = db.execute("SELECT source_pid, target_pid, tension_type, source_url FROM political_tensions WHERE id = ?", (tid,)).fetchone()
    assert (t["source_pid"], t["target_pid"], t["tension_type"], t["source_url"]) == (10, 6, "atbalsts", "https://lsm.test/1")
    p = db.execute("SELECT status, tension_id, decided_at FROM tension_proposals WHERE id = 5").fetchone()
    assert (p["status"], p["tension_id"]) == ("accepted", tid)
    assert p["decided_at"] is not None


def test_accept_type_override_wins_over_hint():
    path = _db_path()
    tid = accept(path, 5, topic="Iekšlietas", description="Kulbergs iebilst Dombravam.", tension_type="spriedze")
    db = get_db(path)
    assert db.execute("SELECT tension_type FROM political_tensions WHERE id = ?", (tid,)).fetchone()[0] == "spriedze"


def test_reject_marks_proposal():
    path = _db_path()
    reject(path, 5)
    db = get_db(path)
    p = db.execute("SELECT status, decided_at FROM tension_proposals WHERE id = 5").fetchone()
    assert p["status"] == "rejected" and p["decided_at"] is not None
