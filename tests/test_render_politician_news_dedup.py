"""Politiķa profila «Ziņas» saraksta dublikātu tests (`src/render/politicians.py`).

Spec: profila Publikācijas cilnes ziņu vaicājums (`platform='web'`, LIMIT 10)
rāda katru dokumentu VIENU reizi. `document_politicians` PK ir
`(document_id, politician_id, role)`, tāpēc vienam (dokuments, politiķis)
pārim var būt vairākas rindas ar dažādām lomām — tipiski 'subject' +
'mentioned'. Vaicājums bez lomu sabrukšanas renderēja tādu dokumentu
divreiz, un dublikāts apēda vienu no TOP-10 slotiem (backlog/vietne-ui.md:
3 689 dok×politiķis pāri ar >1 lomu; 4 profili ar dublikātu TOP-10 logā).

Ja lomas jāapvieno, 'subject' ir prioritārs — templote pēc `n.role` rāda
«pieminēts» birku, un 'mentioned' par dokumentu, kur politiķis ir subjekts,
būtu maldinoša etiķete.

Fikstūru paterns aizgūts no test_render_x_author_role.py /
test_render_own_pubs.py.
"""
from src.db import get_db, init_db
from src.render.politicians import _fetch_politician_detail
from src.saeima.schema import init_saeima_tables


def _seed(db_path):
    init_db(db_path)
    init_saeima_tables(db_path)
    db = get_db(db_path)
    db.execute("INSERT INTO tracked_politicians (id,name,party,relationship_type) "
               "VALUES (1,'Viesturs Kalns','JV','tracked')")
    return db


def _add_web_doc(db, doc_id, scraped_at, roles):
    db.execute("INSERT INTO documents (id,content,content_hash,platform,source_domain,"
               "source_url,scraped_at) "
               "VALUES (?,?,?,'web','delfi.lv',?,?)",
               (doc_id, f"Raksts {doc_id}", f"h{doc_id}",
                f"https://delfi.lv/{doc_id}", scraped_at))
    for role in roles:
        db.execute("INSERT INTO document_politicians (document_id,politician_id,role) "
                   "VALUES (?,?,?)", (doc_id, 1, role))


def test_dual_role_doc_appears_once_with_subject_role(tmp_path):
    """(doc, pid) ar 'subject'+'mentioned' rindām → viens ieraksts, loma 'subject'."""
    db = _seed(str(tmp_path / "t.db"))
    _add_web_doc(db, 10, "2026-09-20", ("subject", "mentioned"))
    db.commit()
    detail = _fetch_politician_detail(db, 1, profile_kind="politician")
    rows = [n for n in detail["news"] if n["id"] == 10]
    assert len(rows) == 1, (
        f"dokuments 10 renderējas {len(rows)} reizes — divas lomas rada dublikātu"
    )
    assert rows[0]["role"] == "subject"


def test_news_limit_counts_distinct_documents(tmp_path):
    """LIMIT 10 skaita dokumentus, ne junction rindas: dublikāts neēd slotu."""
    db = _seed(str(tmp_path / "t.db"))
    # Jaunākais dokuments ar divām lomām + 10 'mentioned' dokumenti = 11 dok.
    _add_web_doc(db, 20, "2026-09-20", ("subject", "mentioned"))
    for i in range(21, 31):
        _add_web_doc(db, i, f"2026-09-{40 - i:02d}", ("mentioned",))
    db.commit()
    detail = _fetch_politician_detail(db, 1, profile_kind="politician")
    ids = [n["id"] for n in detail["news"]]
    assert len(ids) == 10
    assert len(set(ids)) == 10, (
        f"TOP-10 logā ir dublikāts: {sorted(ids)}"
    )
    # Vecākais (id=30) ir izgrūsts; pārējie 10 klāt.
    assert 30 not in ids


def test_subject_doc_sorts_before_newer_mentioned_doc(tmp_path):
    """Secība saglabāta: 'subject' dokuments pirmais arī tad, ja pieminējums jaunāks."""
    db = _seed(str(tmp_path / "t.db"))
    _add_web_doc(db, 40, "2026-09-10", ("subject", "mentioned"))
    _add_web_doc(db, 41, "2026-09-19", ("mentioned",))
    db.commit()
    detail = _fetch_politician_detail(db, 1, profile_kind="politician")
    assert [n["id"] for n in detail["news"]] == [40, 41]
