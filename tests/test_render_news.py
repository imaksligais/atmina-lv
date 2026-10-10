"""_fetch_news grouping tests — viena kartīte per raksts (zinas dedup 2026-07-22)."""

from src.db import get_db, init_db
from src.render.news import _fetch_news


def _make_db(tmp_path):
    db_path = str(tmp_path / "atmina.db")
    init_db(db_path)
    db = get_db(db_path)
    db.executescript(
        """
        INSERT INTO tracked_politicians (id, name, party, relationship_type) VALUES
            (1, 'Andris Kulbergs', 'Apvienotais saraksts', 'tracked'),
            (2, 'Dace Melbārde', 'Nacionālā apvienība', 'tracked'),
            (3, 'Jānis Komentētājs', NULL, 'journalist'),
            (4, 'Vecais Neaktīvais', NULL, 'inactive');
        INSERT INTO documents (id, content, content_hash, source_url, source_domain,
                               platform, published_at, title, word_count, language) VALUES
            (10, 'saturs A', 'hA', 'https://nra.lv/a', 'nra.lv', 'web',
             '2026-07-20', 'Valsts kontrole atsaka dalību', 100, 'lv'),
            (11, 'saturs A2', 'hA2', 'https://diena.lv/a', 'diena.lv', 'web',
             '2026-07-19', 'Valsts kontrole atsaka dalību', 100, 'lv'),
            (12, 'saturs B', 'hB', 'https://lsm.lv/b', 'lsm.lv', 'web',
             '2026-07-18', 'Cits raksts', 100, 'lv'),
            (13, 'saturs C', 'hC', 'https://lsm.lv/c', 'lsm.lv', 'web',
             '2026-07-17', 'Neaktīvā raksts', 100, 'lv');
        INSERT INTO document_politicians (document_id, politician_id, role) VALUES
            (10, 1, 'subject'), (10, 2, 'mentioned'), (10, 3, 'mentioned'),
            (11, 2, 'subject'),
            (12, 2, 'subject'), (12, 4, 'mentioned'),
            (13, 4, 'subject');
        """
    )
    db.commit()
    return db


def test_one_card_per_document(tmp_path):
    """Doc 10 (3 linki) → VIENA kartīte ar abiem politiķiem + komentētāju."""
    db = _make_db(tmp_path)
    news = _fetch_news(db)
    cards_a = [n for n in news if n["source_url"] == "https://nra.lv/a"]
    assert len(cards_a) == 1
    names = [p["name"] for p in cards_a[0]["persons"]]
    assert names == ["Andris Kulbergs", "Dace Melbārde", "Jānis Komentētājs"]
    # politiķi alfabētiski pirms komentētājiem; komentētājam karodziņš
    assert cards_a[0]["persons"][2]["is_commentator"] is True
    assert cards_a[0]["persons_str"] == "Andris Kulbergs|Dace Melbārde|Jānis Komentētājs"
    assert cards_a[0]["parties_str"] == "Apvienotais saraksts|Nacionālā apvienība"
    db.close()


def test_republished_title_merges_persons(tmp_path):
    """Doc 11 (tas pats virsraksts citā avotā) pazūd; personas apvienojas jaunākajā."""
    db = _make_db(tmp_path)
    news = _fetch_news(db)
    urls = [n["source_url"] for n in news]
    assert "https://diena.lv/a" not in urls          # republikācija sakļauta
    assert urls[0] == "https://nra.lv/a"             # jaunākais paliek pirmais
    # Melbārde bija abos — nedublējas
    names = [p["name"] for p in news[0]["persons"]]
    assert names.count("Dace Melbārde") == 1
    db.close()


def test_inactive_link_never_tags_and_inactive_only_needs_claims(tmp_path):
    """Inactive links nedod tagu; tikai-inactive doc bez claims izkrīt, ar claims paliek."""
    db = _make_db(tmp_path)
    news = _fetch_news(db)
    urls = [n["source_url"] for n in news]
    card_b = next(n for n in news if n["source_url"] == "https://lsm.lv/b")
    assert [p["name"] for p in card_b["persons"]] == ["Dace Melbārde"]  # id=4 bez taga
    assert "https://lsm.lv/c" not in urls  # tikai-inactive, bez claims → ārā
    db.execute(
        "INSERT INTO claims (opponent_id, document_id, topic, stance, confidence, "
        "reasoning, salience, source_url, claim_type) VALUES "
        "(4, 13, 'Izglītība', 'Pozīcija ar garumzīmēm ā ē ī.', 0.8, "
        "'Pamatojums ar garumzīmēm ā ē ī.', 0.5, 'https://lsm.lv/c', 'position')"
    )
    db.commit()
    news2 = _fetch_news(db)
    card_c = next(n for n in news2 if n["source_url"] == "https://lsm.lv/c")
    assert card_c["persons"] == []                    # paliek, bet bez tagiem
    assert card_c["topics_list"] == ["Izglītība"]
    db.close()
