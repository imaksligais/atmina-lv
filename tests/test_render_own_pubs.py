"""Medija paša publikāciju (own_pubs) tests organizāciju profiliem.

Spec: medija outletam (relationship_type='organization' + sources.yaml outlet,
kura X feeds saskan ar social_accounts.handle) profila Publikācijas cilnē
parādās domēna-bāzēts "paša publikāciju" saraksts (NE tikai matcher-saistītie
pieminējumi), un pieminējumu saraksts pārmarķēts uz "Pieminēts medijos".

Fikstūru paterns aizgūts no test_render_mediji.py (stub outlets, www.-prefiksēts
source_domain normalizācijai) un test_render_politicians_parskats.py.
"""
from jinja2 import Environment, FileSystemLoader

from src.db import get_db, init_db
from src.render._common import _safe_json_filter, _safe_url_filter
from src.render.politicians import _fetch_politician_detail, render_politicians
from src.saeima.schema import init_saeima_tables

# NRA gadījums: outletam ir hosts + X feeds (saskan ar social_accounts.handle),
# bet NAV neviena document_politicians saites uz outletu (pieminējumu = 0).
OUTLETS = [
    {"short_name": "nra", "slug": "nra", "name": "Neatkarīgā", "hosts": ["nra.lv"],
     "type": "print", "language": "lv", "x_handle": None, "website": None,
     "description": "", "facts": [], "feed_urls": [], "x_feeds": ["nra_x"]},
]


def _outlet_map():
    """opponent_id -> outlet dict, kā to atgriež _outlet_feed_map (ar hosts)."""
    return {
        3: {"short_name": "nra", "name": "Neatkarīgā", "slug": "nra",
            "hosts": ["nra.lv"]},
    }


def _seed(db_path):
    init_db(db_path)
    init_saeima_tables(db_path)
    db = get_db(db_path)
    # id=3 organizācijas profils (outlets feed); id=1 deputāts
    db.execute("INSERT INTO tracked_politicians (id,name,party,relationship_type) "
               "VALUES (1,'A Kalns','JV','tracked')")
    db.execute("INSERT INTO tracked_politicians (id,name,party,relationship_type) "
               "VALUES (3,'Neatkarīgā',NULL,'organization')")
    db.execute("INSERT INTO social_accounts (opponent_id,platform,handle,feed_type) "
               "VALUES (3,'twitter','NRA_X','relay')")
    # Outleta paša publikācijas (platform='web', source_domain=nra.lv) —
    # viena ar www. prefiksu, lai pārbaudītu normalizāciju.
    db.execute("INSERT INTO documents (id,content,content_hash,platform,source_domain,"
               "source_url,scraped_at,published_at) "
               "VALUES (20,'Raksts viens','h20','web','nra.lv','https://nra.lv/a',"
               "'2026-05-30','2026-05-30')")
    db.execute("INSERT INTO documents (id,content,content_hash,platform,source_domain,"
               "source_url,scraped_at,published_at) "
               "VALUES (21,'Raksts divi','h21','web','www.nra.lv','https://www.nra.lv/b',"
               "'2026-05-31','2026-05-31')")
    # Dokuments, ko outlets NEpieder (cits domēns) — nedrīkst ietvert own_pubs.
    db.execute("INSERT INTO documents (id,content,content_hash,platform,source_domain,"
               "source_url,scraped_at) "
               "VALUES (22,'Sveša','h22','web','lsm.lv','https://lsm.lv/c','2026-05-28')")
    db.commit()
    return db


# ── (a) own_pubs by domain + www. normalization ─────────────────────


def test_own_pubs_collected_by_domain_with_www_normalization(tmp_path):
    db = _seed(str(tmp_path / "t.db"))
    detail = _fetch_politician_detail(
        db, 3, profile_kind="organization", feed_outlets=_outlet_map()
    )
    ids = {d["id"] for d in detail["own_pubs"]}
    # Abi nra.lv dokumenti (tostarp www.nra.lv) iekļauti; svešais lsm.lv nē.
    assert ids == {20, 21}
    assert detail["own_pubs_outlet"] == {
        "name": "Neatkarīgā", "slug": "nra", "host": "nra.lv",
    }


def test_own_pubs_empty_for_deputy(tmp_path):
    db = _seed(str(tmp_path / "t.db"))
    detail = _fetch_politician_detail(
        db, 1, profile_kind="politician", feed_outlets=_outlet_map()
    )
    assert detail["own_pubs"] == []
    assert detail["own_pubs_outlet"] is None


# ── (b) has_publikacijas / tab present with ZERO mention links ───────


def test_has_publikacijas_with_zero_mentions_but_own_pubs(tmp_path):
    """NRA gadījums: nav neviena document_politicians saites (news tukšs),
    bet own_pubs eksistē → Publikācijas cilne klāt."""
    db = _seed(str(tmp_path / "t.db"))
    detail = _fetch_politician_detail(
        db, 3, profile_kind="organization", feed_outlets=_outlet_map()
    )
    assert detail["news"] == []          # nav matcher-saišu
    assert detail["own_pubs"]            # bet ir paša publikācijas
    assert "publikacijas" in detail["tab_set"]


# ── (c) rendered HTML labels ─────────────────────────────────────────


def _env():
    env = Environment(loader=FileSystemLoader("templates"), autoescape=True)
    env.filters["safe_url"] = _safe_url_filter
    env.filters["safe_json"] = _safe_json_filter
    env.filters["lv_date"] = (
        lambda s: f"{s[8:10]}.{s[5:7]}.{s[:4]}"
        if s and len(s) >= 10 and "-" in s else s or ""
    )
    env.filters["autolink_bills"] = lambda s, *a, **k: s
    env.filters["lv_plural"] = lambda n, *a, **k: ""
    env.globals["assets_version"] = "test"
    return env


def _politician(pid, name, slug, kind, party=None):
    return {
        "id": pid, "name": name, "slug": slug, "profile_kind": kind,
        "role_label": kind, "party": party, "x_handle": None,
    }


def test_rendered_org_has_pieminets_medijos_deputy_does_not(tmp_path, monkeypatch):
    db = _seed(str(tmp_path / "t.db"))
    # Deputātam viens web pieminējums → 'Ziņas' sekcija.
    db.execute("INSERT INTO documents (id,content,content_hash,platform,source_domain,"
               "source_url,scraped_at) "
               "VALUES (30,'Par Kalnu','h30','web','delfi.lv','https://delfi.lv/k',"
               "'2026-05-30')")
    db.execute("INSERT INTO document_politicians (document_id,politician_id,role) "
               "VALUES (30,1,'mentioned')")
    # Organizācijai viens cita medija pieminējums → 'Pieminēts medijos' sekcija.
    db.execute("INSERT INTO documents (id,content,content_hash,platform,source_domain,"
               "source_url,scraped_at) "
               "VALUES (31,'Par NRA','h31','web','delfi.lv','https://delfi.lv/n',"
               "'2026-05-29')")
    db.execute("INSERT INTO document_politicians (document_id,politician_id,role) "
               "VALUES (31,3,'mentioned')")
    db.commit()

    monkeypatch.setattr(
        "src.render.politicians._outlet_feed_map", lambda _db: _outlet_map()
    )

    out = tmp_path / "site" / "atmina"
    out.mkdir(parents=True)
    politicians = [
        _politician(3, "Neatkarīgā", "neatkariga", "organization"),
        _politician(1, "A Kalns", "a-kalns", "politician", party="JV"),
    ]
    render_politicians(_env(), db, out, politicians, pid_to_syntheses={})

    org_html = (out / "politiki" / "neatkariga.html").read_text(encoding="utf-8")
    assert "Pieminēts medijos" in org_html
    assert "Publikācijas vietnē nra.lv" in org_html
    assert "../mediji/nra.html" in org_html

    dep_html = (out / "politiki" / "a-kalns.html").read_text(encoding="utf-8")
    assert "Pieminēts medijos" not in dep_html
    assert "Ziņas (" in dep_html
