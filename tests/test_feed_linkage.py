from src.db import get_db, init_db
from src.render._common import _outlet_feed_map, _split_org_category

OUTLETS = [
    {"short_name": "lsm", "slug": "lsm", "name": "LSM",
     "x_feeds": ["ltvzinas", "ltvpanorama"]},
    {"short_name": "nra", "slug": "nra", "name": "Neatkarīgā", "x_feeds": []},
]


def _seed(db_path):
    init_db(db_path)
    db = get_db(db_path)
    # init_db (schema.sql) neizveido saeima_individual_votes — tā dzīvo
    # src/saeima/schema.py. _fetch_personas to vaicā votes_count apakšvaicājumā,
    # tāpēc minimālajā DB izveidojam to šeit.
    db.execute("CREATE TABLE IF NOT EXISTS saeima_individual_votes ("
               "id INTEGER PRIMARY KEY AUTOINCREMENT, vote_id INTEGER, "
               "politician_id INTEGER, vote TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS saeima_votes ("
               "id INTEGER PRIMARY KEY, vote_date TEXT, summary TEXT, topic TEXT)")
    db.execute("INSERT INTO tracked_politicians (id,name,relationship_type) "
               "VALUES (170,'LTV Ziņas','organization')")
    db.execute("INSERT INTO tracked_politicians (id,name,relationship_type) "
               "VALUES (204,'Latvijas armija (NBS)','organization')")
    # handle DB-ā ar citu burtu reģistru nekā x_feeds -> case-insensitive match;
    # platform='twitter' spoguļo reālo DB (sk. _outlet_feed_map IN-klauzulu)
    db.execute("INSERT INTO social_accounts (opponent_id,platform,handle,feed_type) "
               "VALUES (170,'twitter','LTVzinas','relay')")
    db.execute("INSERT INTO social_accounts (opponent_id,platform,handle,feed_type) "
               "VALUES (204,'x','Latvijas_armija','first_party')")
    db.commit()
    return db


def test_outlet_feed_map_matches_case_insensitive(tmp_path):
    db = _seed(str(tmp_path / "t.db"))
    m = _outlet_feed_map(db, OUTLETS)
    assert set(m) == {170}                      # NBS handle nav nevienā x_feeds
    assert m[170] == {"short_name": "lsm", "name": "LSM", "slug": "lsm", "hosts": []}


def test_outlet_feed_map_empty_without_x_feeds(tmp_path):
    db = _seed(str(tmp_path / "t.db"))
    assert _outlet_feed_map(db, [{"short_name": "nra", "slug": "nra",
                                  "name": "NRA", "x_feeds": []}]) == {}


def test_split_org_category():
    assert _split_org_category("Iestādes un mediji", 170, {170}) == "Mediji"
    assert _split_org_category("Iestādes un mediji", 204, {170}) == "Iestādes"
    # ne-org kategorijas iziet cauri nemainītas
    assert _split_org_category("Deputāti", 1, {170}) == "Deputāti"


def test_fetch_personas_splits_org_bucket(tmp_path, monkeypatch):
    import src.render.personas as personas_mod
    db = _seed(str(tmp_path / "t.db"))
    monkeypatch.setattr(
        personas_mod, "_outlet_feed_map",
        lambda d: {170: {"short_name": "lsm", "name": "LSM", "slug": "lsm"}})
    rows = personas_mod._fetch_personas(db)
    cats = {p["name"]: p["category"] for p in rows}
    assert cats["LTV Ziņas"] == "Mediji"
    assert cats["Latvijas armija (NBS)"] == "Iestādes"
