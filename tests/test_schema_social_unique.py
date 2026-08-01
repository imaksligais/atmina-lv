from src.db import init_db, get_db


def test_fresh_db_has_social_accounts_unique_index(tmp_path):
    db_path = str(tmp_path / "fresh.db")
    init_db(db_path)
    db = get_db(db_path)
    names = {r[0] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type='index' "
        "AND tbl_name='social_accounts'"
    ).fetchall()}
    db.close()
    assert "idx_social_accounts_unique" in names
