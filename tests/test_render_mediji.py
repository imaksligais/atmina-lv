from src.db import get_db, init_db
from src.render.mediji import _cross_outlet_avg_party_share, _fetch_coverage

OUTLETS = [
    {"short_name": "lsm", "slug": "lsm", "name": "LSM", "hosts": ["lsm.lv"],
     "type": "public_tv", "type_label": "sabiedriskais medijs", "language": "lv",
     "x_handle": None, "website": None,
     "description": "", "facts": [], "feed_urls": [], "x_feeds": ["tv3zinas_x"]},
    {"short_name": "nra", "slug": "nra", "name": "Neatkarīgā", "hosts": ["nra.lv"],
     "type": "print", "type_label": "drukātā prese", "language": "lv",
     "x_handle": None, "website": None,
     "description": "", "facts": [], "feed_urls": [], "x_feeds": []},
    {"short_name": "vestnesis", "slug": "vestnesis", "name": "Latvijas Vēstnesis",
     "hosts": ["vestnesis.lv"], "type": "official", "type_label": "oficiālais izdevējs",
     "language": "lv", "x_handle": None,
     "website": None, "description": "", "facts": [], "feed_urls": [], "x_feeds": [],
     "volume_label": "dokumenti"},
]


def _seed(db_path):
    init_db(db_path)
    db = get_db(db_path)
    db.execute("INSERT INTO tracked_politicians (id,name,party,relationship_type) VALUES (1,'A Kalns','JV','tracked')")
    db.execute("INSERT INTO tracked_politicians (id,name,party,relationship_type) VALUES (2,'B Lejas','NA','tracked')")
    db.execute("INSERT INTO tracked_politicians (id,name,party,relationship_type) VALUES (3,'TV3 Ziņas',NULL,'journalist')")
    db.execute("INSERT INTO documents (id,content,content_hash,platform,source_domain,source_url,scraped_at) "
               "VALUES (10,'c1','h1','web','www.lsm.lv','https://www.lsm.lv/a','2026-05-30')")
    db.execute("INSERT INTO documents (id,content,content_hash,platform,source_domain,source_url,scraped_at) "
               "VALUES (11,'c2','h2','web','lsm.lv','https://lsm.lv/b','2026-05-31')")
    db.execute("INSERT INTO documents (id,content,content_hash,platform,source_domain,source_url,scraped_at) "
               "VALUES (12,'c3','h3','web','nra.lv','https://nra.lv/c','2026-05-29')")
    # Latvijas Vēstnesis — official publisher, counts toward volume only (not comparisons)
    db.execute("INSERT INTO documents (id,content,content_hash,platform,source_domain,source_url,scraped_at) "
               "VALUES (13,'c4','h4','vestnesis','www.vestnesis.lv','https://www.vestnesis.lv/d','2026-05-28')")
    # web_scraper — normal journalism (LSM), counts everywhere
    db.execute("INSERT INTO documents (id,content,content_hash,platform,source_domain,source_url,scraped_at) "
               "VALUES (14,'c5','h5','web_scraper','lsm.lv','https://lsm.lv/e','2026-06-01')")
    for d, p in [(10, 1), (11, 1), (11, 2), (12, 2), (10, 3), (13, 1), (14, 2)]:
        db.execute("INSERT INTO document_politicians (document_id,politician_id,role) VALUES (?,?, 'subject')", (d, p))
    db.execute("INSERT INTO claims (opponent_id,document_id,topic,stance,claim_type,source_url,stated_at) "
               "VALUES (1,10,'Aizsardzība un drošība','x','position','https://www.lsm.lv/a','2026-05-30')")
    db.execute("INSERT INTO social_accounts (opponent_id,platform,handle,feed_type) "
               "VALUES (3,'twitter','TV3zinas_X','relay')")
    db.commit()
    return db


def test_fetch_coverage_volume_and_host_normalization(tmp_path):
    db = _seed(str(tmp_path / "t.db"))
    cov = _fetch_coverage(db, OUTLETS)
    # www.lsm.lv + lsm.lv (web) merged + doc14 (web_scraper) counted as journalism
    assert cov["lsm"]["volume"] == 3
    assert cov["nra"]["volume"] == 1


def test_fetch_coverage_excludes_audience_roles(tmp_path):
    db = _seed(str(tmp_path / "t.db"))
    cov = _fetch_coverage(db, OUTLETS)
    names = set(cov["lsm"]["by_politician"])
    assert "A Kalns" in names
    assert "TV3 Ziņas" not in names   # journalist role excluded


def test_fetch_coverage_by_party_and_topic(tmp_path):
    db = _seed(str(tmp_path / "t.db"))
    cov = _fetch_coverage(db, OUTLETS)
    # LSM: A(JV) in doc10+doc11 -> JV=2 distinct docs; B(NA) in doc11 (web) +
    # doc14 (web_scraper) -> NA=2 (web_scraper counts as journalism everywhere)
    assert cov["lsm"]["by_party"]["JV"] == 2
    assert cov["lsm"]["by_party"]["NA"] == 2
    assert cov["lsm"]["by_topic"]["Aizsardzība un drošība"] == 1


def test_vestnesis_volume_but_excluded_from_comparisons(tmp_path):
    db = _seed(str(tmp_path / "t.db"))
    cov = _fetch_coverage(db, OUTLETS)
    # doc13 (platform='vestnesis') counts toward volume ...
    assert cov["vestnesis"]["volume"] == 1
    # ... but official-publisher docs stay OUT of coverage comparisons
    assert cov["vestnesis"]["by_politician"] == {}
    assert cov["vestnesis"]["by_party"] == {}


def test_web_scraper_counts_as_journalism(tmp_path):
    db = _seed(str(tmp_path / "t.db"))
    cov = _fetch_coverage(db, OUTLETS)
    # doc14 web_scraper (lsm.lv, B/NA) is counted in LSM volume + by_party
    assert cov["lsm"]["volume"] == 3
    assert cov["lsm"]["by_party"]["NA"] == 2


def test_volume_phrase_lv_singular_plural():
    from src.render.mediji import _volume_phrase
    assert _volume_phrase(1421, "dokumenti") == "1421 dokuments"
    assert _volume_phrase(2, "raksti") == "2 raksti"
    assert _volume_phrase(11, "raksti") == "11 raksti"


def test_cross_outlet_avg_party_share(tmp_path):
    db = _seed(str(tmp_path / "t.db"))
    cov = _fetch_coverage(db, OUTLETS)
    avg = _cross_outlet_avg_party_share(cov)
    assert 0.0 <= avg.get("JV", 0) <= 1.0


def _env():
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    return Environment(
        loader=FileSystemLoader("templates"),
        autoescape=select_autoescape(["html", "j2"]),
    )


def test_render_mediji_writes_index_and_detail(tmp_path):
    from src.render.mediji import render_mediji
    db = _seed(str(tmp_path / "t.db"))
    out = tmp_path / "site"
    out.mkdir()
    render_mediji(_env(), db, out, OUTLETS)
    assert (out / "mediji.html").exists()
    assert (out / "mediji" / "lsm.html").exists()
    assert (out / "mediji" / "nra.html").exists()
    html = (out / "mediji" / "lsm.html").read_text(encoding="utf-8")
    assert "LSM" in html


def test_render_mediji_type_labels(tmp_path):
    from src.render.mediji import render_mediji
    db = _seed(str(tmp_path / "t.db"))
    out = tmp_path / "site"
    out.mkdir()
    render_mediji(_env(), db, out, OUTLETS)
    index = (out / "mediji.html").read_text(encoding="utf-8")
    # LV public labels on the index cards, never the raw English code
    assert "oficiālais izdevējs" in index
    assert "sabiedriskais medijs" in index
    assert ">agency<" not in index
    assert ">official<" not in index
    # detail chip shows the LV label
    vestnesis = (out / "mediji" / "vestnesis.html").read_text(encoding="utf-8")
    assert "oficiālais izdevējs" in vestnesis


def test_render_mediji_vestnesis_volume_label(tmp_path):
    from src.render.mediji import render_mediji
    db = _seed(str(tmp_path / "t.db"))
    out = tmp_path / "site"
    out.mkdir()
    render_mediji(_env(), db, out, OUTLETS)
    # index card shows LV singular "1 dokuments" for the Vēstnesis volume
    index = (out / "mediji.html").read_text(encoding="utf-8")
    assert "1 dokuments" in index
    # detail page heading uses the outlet's volume_label
    detail = (out / "mediji" / "vestnesis.html").read_text(encoding="utf-8")
    assert "Jaunākie dokumenti" in detail


def test_orchestrator_knows_mediji_domain():
    from src.render._orchestrator import KNOWN_DOMAINS
    assert "mediji" in KNOWN_DOMAINS


def test_fetch_outlet_feeds(tmp_path):
    from src.render.mediji import _fetch_outlet_feeds
    db = _seed(str(tmp_path / "t.db"))
    feeds = _fetch_outlet_feeds(db, OUTLETS)
    assert [f["name"] for f in feeds["lsm"]] == ["TV3 Ziņas"]
    assert feeds["lsm"][0]["pubs"] == 1        # doc10 junction rinda
    assert feeds["lsm"][0]["slug"] == "tv3-zinas"
    assert feeds["nra"] == []


def test_render_mediji_feed_section(tmp_path):
    from src.render.mediji import render_mediji
    db = _seed(str(tmp_path / "t.db"))
    out = tmp_path / "site"
    out.mkdir()
    render_mediji(_env(), db, out, OUTLETS)
    lsm = (out / "mediji" / "lsm.html").read_text(encoding="utf-8")
    assert "X konti un raidījumi" in lsm
    assert "../politiki/tv3-zinas.html" in lsm
    nra = (out / "mediji" / "nra.html").read_text(encoding="utf-8")
    assert "X konti un raidījumi" not in nra
