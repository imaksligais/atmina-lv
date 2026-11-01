"""Profile cards must classify vote/statement pairs from their actual claim types."""
import re

from src.db import get_db, init_db, store_claim, store_contradiction
from src.saeima.schema import init_saeima_bills, init_saeima_tables


def test_profile_vote_contradiction_has_words_deeds_badge_and_chronological_panes(
    tmp_path, monkeypatch,
):
    import src.render._orchestrator as orch
    from src.render._common import og_render

    db_path = str(tmp_path / "profile.db")
    init_db(db_path)
    init_saeima_tables(db_path)
    init_saeima_bills(db_path)
    db = get_db(db_path)
    db.executescript("""
        INSERT INTO tracked_politicians (id, name, role, relationship_type)
            VALUES (1, 'Testa Politiķis', 'Saeimas deputāts', 'tracked');
        INSERT INTO documents (id, source_url, title, content, content_hash, platform)
            VALUES (1, 'https://example.lv/statement', 'Budžets',
                    'Iebilst budžeta deficītam.', 'profile-contradiction', 'web');
    """)
    db.close()
    common = dict(
        opponent_id=1, topic="Budžets un finanses", quote=None,
        confidence=0.8, reasoning="Testa pozīcija.", salience=0.8,
        db_path=db_path,
    )
    statement = store_claim(
        **common, document_id=1, stance="Iebilst budžeta deficītam.",
        source_url="https://example.lv/statement", stated_at="2026-09-20",
        embedding_bytes=bytes(384 * 4),
    )
    vote = store_claim(
        **common, document_id=None, stance="Atbalsta budžeta deficītu.",
        source_url="https://example.lv/vote", stated_at="2026-09-01",
        claim_type="saeima_vote",
    )
    # Detection order is reversed: the backfilled vote must appear on the left.
    cid = store_contradiction(
        opponent_id=1, old_claim_id=statement, new_claim_id=vote,
        topic=common["topic"], summary="Mainīta nostāja par budžeta deficītu.",
        severity="reversal", salience=0.8, db_path=db_path,
    )
    db = get_db(db_path)
    db.execute("UPDATE contradictions SET confirmed = 1 WHERE id = ?", (cid,))
    db.commit()
    db.close()

    monkeypatch.setattr(orch, "_download_chart_js", lambda *a, **k: None)
    monkeypatch.setattr(orch, "_download_annotation_plugin", lambda *a, **k: None)
    monkeypatch.setattr(og_render, "render_og_images", lambda *a, **k: 0)
    orch.generate_public_site(
        db_path=db_path, output_dir=str(tmp_path / "site"), only={"politiki"},
    )
    html = (tmp_path / "site/atmina/politiki/testa-politikis.html").read_text(encoding="utf-8")
    cards = re.findall(r'<article class="prv2-card\b[^>]*>(.*?)</article>', html, re.S)
    assert len(cards) == 1, "The seeded contradiction must render on the politician profile"
    badge = re.search(r'class="prv2-sevbadge"[^>]*>(.*?)</span>', cards[0], re.S)
    assert badge and "Vārdi pret darbiem" in badge[1]
    kickers = re.findall(
        r'class="prv2-pane prv2-pane-(?:old|new)">\s*'
        r'<div class="prv2-kicker[^\"]*">([^<]+)</div>', cards[0],
    )
    assert kickers == ["Darbi", "Vārdi"]
