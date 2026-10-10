import json
import os
import sqlite3
import tempfile

from src.db import init_db, get_db


def _db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    db = get_db(path)
    for pid, name in [(10, "Andris Kulbergs"), (6, "Jānis Dombrava")]:
        db.execute("INSERT INTO tracked_politicians (id, name, name_forms) VALUES (?,?,?)", (pid, name, json.dumps([name])))
    db.execute("INSERT INTO documents (id, content, content_hash) VALUES (1, 'x', 'h1')")
    db.commit()
    return db


def test_tension_proposals_unique_pair():
    db = _db()
    cols = {r[1] for r in db.execute("PRAGMA table_info(tension_proposals)")}
    assert {"document_id", "source_pid", "target_pid", "relation", "p_link", "p_relation", "p_speaks", "status", "tension_id"} <= cols
    db.execute("INSERT INTO tension_proposals (document_id, source_pid, target_pid, relation, p_link, p_relation, p_speaks) "
               "VALUES (1, 10, 6, 'atbalsts', 0.97, 0.9, 0.95)")
    try:
        db.execute("INSERT INTO tension_proposals (document_id, source_pid, target_pid, relation, p_link, p_relation, p_speaks) "
                   "VALUES (1, 10, 6, 'uzbrukums', 0.9, 0.8, 0.9)")
        assert False, "duplicate pair must be rejected"
    except sqlite3.IntegrityError:
        pass


def test_tension_judged_marks_document_once():
    db = _db()
    db.execute("INSERT OR IGNORE INTO tension_judged (document_id) VALUES (1)")
    db.execute("INSERT OR IGNORE INTO tension_judged (document_id) VALUES (1)")
    assert db.execute("SELECT COUNT(*) FROM tension_judged").fetchone()[0] == 1
