"""Step 5 (Spriedzes) reports pending TypeSafe Saites proposals in the routine-day window."""
import json
import os
import tempfile
from datetime import datetime

from src.briefs import routine_day_window
from src.db import init_db, get_db
from src.routine import _check_tensions


def _routine_day_for_now() -> str:
    """The routine day that contains 'now' (05:00 LV boundary), so the
    fixture rows land inside the window whatever hour the suite runs."""
    now = datetime.now()
    today = now.date().isoformat()
    start, _ = routine_day_window(today)
    if now.strftime("%Y-%m-%d %H:%M:%S") >= start:
        return today
    from datetime import timedelta
    return (now.date() - timedelta(days=1)).isoformat()


def test_check_tensions_mentions_pending_proposals():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    db = get_db(path)
    for pid, name in [(10, "Andris Kulbergs"), (6, "Jānis Dombrava")]:
        db.execute("INSERT INTO tracked_politicians (id, name, name_forms) VALUES (?,?,?)", (pid, name, json.dumps([name])))
    db.execute("INSERT INTO documents (id, content, content_hash) VALUES (1, 'x', 'h1')")
    db.execute("INSERT INTO tension_proposals (document_id, source_pid, target_pid, relation, p_link, p_relation, p_speaks, created_at) "
               "VALUES (1, 10, 6, 'atbalsts', 0.95, 0.9, 0.95, datetime('now'))")
    day = _routine_day_for_now()
    for pid in (10, 6):
        db.execute("INSERT INTO claims (opponent_id, topic, stance, claim_type, created_at) "
                   "VALUES (?, 't', 's', 'position', ?)", (pid, f"{day} 12:00:00"))
    db.commit()
    res = _check_tensions(db, day)
    assert res["status"] == "missing"
    assert "1 TypeSafe priekšlikum" in res["details"]


def test_check_tensions_silent_without_proposals():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    db = get_db(path)
    for pid, name in [(10, "Andris Kulbergs"), (6, "Jānis Dombrava")]:
        db.execute("INSERT INTO tracked_politicians (id, name, name_forms) VALUES (?,?,?)", (pid, name, json.dumps([name])))
    day = _routine_day_for_now()
    for pid in (10, 6):
        db.execute("INSERT INTO claims (opponent_id, topic, stance, claim_type, created_at) "
                   "VALUES (?, 't', 's', 'position', ?)", (pid, f"{day} 12:00:00"))
    db.commit()
    res = _check_tensions(db, day)
    assert "TypeSafe" not in res["details"]


def test_pending_noun_declension():
    """LV: 1/21 priekšlikums, 2/11/16 priekšlikumi."""
    from src.routine import _check_tensions  # noqa: F401 — same helper, exercised via details
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    db = get_db(path)
    db.execute("INSERT INTO tracked_politicians (id, name, name_forms) VALUES (10, 'A B', '[\"B\"]')")
    db.execute("INSERT INTO tracked_politicians (id, name, name_forms) VALUES (6, 'C D', '[\"D\"]')")
    db.execute("INSERT INTO documents (id, content, content_hash) VALUES (1, 'x', 'h1')")
    day = _routine_day_for_now()
    for pid in (10, 6):
        db.execute("INSERT INTO claims (opponent_id, topic, stance, claim_type, created_at) "
                   "VALUES (?, 't', 's', 'position', ?)", (pid, f"{day} 12:00:00"))
    for i in range(11):
        db.execute("INSERT INTO documents (id, content, content_hash) VALUES (?, 'x', ?)", (100 + i, f"h{100 + i}"))
        db.execute("INSERT INTO tension_proposals (document_id, source_pid, target_pid, relation, p_link, p_relation, p_speaks, created_at) "
                   "VALUES (?, 10, 6, 'atbalsts', 0.9, 0.9, 0.9, datetime('now'))", (100 + i,))
    db.commit()
    assert "11 TypeSafe priekšlikumi gaida" in _check_tensions(db, day)["details"]
    db.execute("DELETE FROM tension_proposals WHERE document_id > 100")
    db.commit()
    assert "1 TypeSafe priekšlikums gaida" in _check_tensions(db, day)["details"]
