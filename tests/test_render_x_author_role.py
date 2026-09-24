"""X plūsmas autora lomas tests (`src/render/x.py::_fetch_x_data`).

Spec: `x.html` plūsmā katrs tvīts parādās TIKAI zem tā autora. Šablons
(`templates/x.html.j2`) izvada `politician_name` kā ieraksta autoru, tāpēc
`document_politicians` rinda ar `role='mentioned'` renderētu sveša cilvēka
tvītu zem pieminētā politiķa vārda.

Kāpēc šis tests eksistē (2026-08-08): `post_rows` savienoja
`document_politicians` BEZ lomas filtra, un tā brīža plūsmas logā 635 no 1500
rindām bija ne-`subject`. Konkrētais gadījums, kas to atklāja: iekšlietu
ministra tvīts ar neverificētu apgalvojumu par nosauktu privātpersonu
renderējās divreiz — pareizi zem viņa un otrreiz zem cita politiķa, kuram tā
bija pilnīgi likumīga `role='mentioned'` saite (Datu līgums #11: relay/mention
saite nenozīmē autorību). Nepareiza autorība apmelojoša satura gadījumā nav
kosmētiska kļūda.

Fikstūru paterns aizgūts no test_render_own_pubs.py.
"""
from src.db import get_db, init_db
from src.render.x import _fetch_x_data
from src.saeima.schema import init_saeima_tables


def _seed(db_path):
    init_db(db_path)
    init_saeima_tables(db_path)
    db = get_db(db_path)
    db.execute("INSERT INTO tracked_politicians (id,name,party,relationship_type) "
               "VALUES (1,'Autors Ozols','NA','tracked')")
    db.execute("INSERT INTO tracked_politicians (id,name,party,relationship_type) "
               "VALUES (2,'Pieminētais Bērzs','JV','tracked')")
    db.execute("INSERT INTO social_accounts (opponent_id,platform,handle,feed_type,active) "
               "VALUES (1,'twitter','autors_ozols','first_party',1)")
    db.execute("INSERT INTO social_accounts (opponent_id,platform,handle,feed_type,active) "
               "VALUES (2,'twitter','piemin_berzs','first_party',1)")
    # Viens tvīts, ko rakstījis id=1 un kurā pieminēts id=2.
    db.execute("INSERT INTO documents (id,content,content_hash,platform,source_domain,"
               "source_url,scraped_at,published_at) "
               "VALUES (10,'Ozola paša tvīts, kurā minēts Bērzs.','h10','twitter','x.com',"
               "'https://x.com/autors_ozols/status/1','2026-08-08','2026-08-08T09:00:00')")
    db.execute("INSERT INTO document_politicians (document_id,politician_id,role) "
               "VALUES (10,1,'subject')")
    db.execute("INSERT INTO document_politicians (document_id,politician_id,role) "
               "VALUES (10,2,'mentioned')")
    db.commit()
    return db


def test_feed_shows_tweet_once_under_its_author(tmp_path):
    """Viens dokuments ar divām junction rindām → tieši viens plūsmas ieraksts."""
    db = _seed(str(tmp_path / "t.db"))
    data = _fetch_x_data(db)
    rows = [p for p in data["posts"] if p["id"] == 10]
    assert len(rows) == 1, (
        f"tvīts 10 renderējas {len(rows)} reizes — 'mentioned' saite rada dublikātu"
    )
    assert rows[0]["politician_name"] == "Autors Ozols"


def test_mentioned_politician_is_never_shown_as_author(tmp_path):
    """Pieminētais politiķis nedrīkst parādīties kā neviena tvīta autors."""
    db = _seed(str(tmp_path / "t.db"))
    data = _fetch_x_data(db)
    authors = {p["politician_name"] for p in data["posts"]}
    assert "Pieminētais Bērzs" not in authors


def test_query_filters_on_subject_role(tmp_path):
    """Sargs pret regresiju: ja lomas filtrs pazūd, šis tests krīt pat tad,
    ja fikstūra mainās — pārbaudām, ka NE-subject lomas plūsmā neienāk."""
    db = _seed(str(tmp_path / "t.db"))
    db.execute("INSERT INTO documents (id,content,content_hash,platform,source_domain,"
               "source_url,scraped_at,published_at) "
               "VALUES (11,'Cita konta tvīts.','h11','twitter','x.com',"
               "'https://x.com/kads_cits/status/2','2026-08-08','2026-08-08T10:00:00')")
    db.execute("INSERT INTO document_politicians (document_id,politician_id,role) "
               "VALUES (11,2,'mention_target')")
    db.commit()
    data = _fetch_x_data(db)
    assert all(p["id"] != 11 for p in data["posts"]), (
        "dokuments ar role='mention_target' nedrīkst parādīties plūsmā kā ieraksts"
    )
