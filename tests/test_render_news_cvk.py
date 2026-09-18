"""CVK datu portāli izslēgti no ziņu plūsmas (operatora verdikts 2026-08-17).

Izslēgšana ir READ-SIDE: dokumenti paliek DB, tikai `zinas.html` tos
nerāda. Kritērijs ir domēns, nevis virsraksts — CVK `<title>` mainās
katru vēlēšanu ciklu ("SV2026", "EPV2024"), domēns ne.
"""

import pytest

from src.db import get_db, init_db
from src.render.news import _fetch_news, _is_cvk_domain


@pytest.mark.parametrize(
    "domain",
    ["cvk.lv", "dati.cvk.lv", "epv2024.cvk.lv", "www.cvk.lv", "CVK.LV", "cvk.gov.lv"],
)
def test_cvk_domains_recognised(domain):
    assert _is_cvk_domain(domain) is True


@pytest.mark.parametrize(
    "domain",
    [None, "", "lsm.lv", "nra.lv", "delfi.lv", "cvk.lv.piemers.lv", "necvk.lv"],
)
def test_non_cvk_domains_not_recognised(domain):
    assert _is_cvk_domain(domain) is False


def _make_db(tmp_path):
    db_path = str(tmp_path / "atmina.db")
    init_db(db_path)
    db = get_db(db_path)
    db.executescript(
        """
        INSERT INTO tracked_politicians (id, name, party, relationship_type) VALUES
            (1, 'Andris Kulbergs', 'Apvienotais saraksts', 'tracked'),
            (2, 'Dace Melbārde', 'Nacionālā apvienība', 'tracked');
        INSERT INTO documents (id, content, content_hash, source_url, source_domain,
                               platform, published_at, title, word_count, language) VALUES
            (10, 'saturs A', 'hA', 'https://nra.lv/a', 'nra.lv', 'web',
             '2026-08-16', 'Parasts ziņu raksts', 100, 'lv'),
            (11, 'kandidātu saraksts', 'hB', 'https://dati.cvk.lv/sv2026/lists/1',
             'dati.cvk.lv', 'web', '2026-08-15',
             'SV2026 - 2026. gada Saeimas vēlēšanas', 2500, 'lv'),
            (12, 'kandidātu saraksts EP', 'hC', 'https://epv2024.cvk.lv/lists/2',
             'epv2024.cvk.lv', 'web', '2026-08-14',
             'EPV2024 - Eiropas Parlamenta vēlēšanas 2024', 60, 'lv');
        INSERT INTO document_politicians (document_id, politician_id, role) VALUES
            (10, 1, 'subject'),
            (11, 1, 'mentioned'), (11, 2, 'mentioned'),
            (12, 2, 'mentioned');
        """
    )
    db.commit()
    return db


def test_cvk_documents_excluded_from_feed(tmp_path):
    """Saucējs: 3 dokumenti plūsmas vaicājumā → 2 CVK ārā, 1 raksts paliek."""
    db = _make_db(tmp_path)
    news = _fetch_news(db)
    assert [n["source_url"] for n in news] == ["https://nra.lv/a"]
    assert all(not _is_cvk_domain(n["source_domain"]) for n in news)
    db.close()


def test_cvk_documents_remain_in_db(tmp_path):
    """Izslēgšana ir renderī — dokumenti NAV dzēsti."""
    db = _make_db(tmp_path)
    _fetch_news(db)
    (still_there,) = db.execute(
        "SELECT COUNT(*) FROM documents WHERE source_domain LIKE '%cvk%'"
    ).fetchone()
    assert still_there == 2
    db.close()
