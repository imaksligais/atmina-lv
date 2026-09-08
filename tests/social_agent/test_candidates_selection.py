from src.social_agent.candidates import select_top_n


def test_select_top_n_respects_total_limit():
    pool = [
        {"pillar": "pretrunas", "score": 0.9, "payload": {"i": 1}},
        {"pillar": "pretrunas", "score": 0.85, "payload": {"i": 2}},
        {"pillar": "pretrunas", "score": 0.80, "payload": {"i": 3}},
        {"pillar": "stats", "score": 0.7, "payload": {"i": 4}},
        {"pillar": "highlights", "score": 0.6, "payload": {"i": 5}},
    ]
    top = select_top_n(pool, n=3, per_pillar_cap=2)
    assert len(top) == 3
    pretrunas_count = sum(1 for t in top if t["pillar"] == "pretrunas")
    assert pretrunas_count == 2, "pretrunas must cap at 2 per-pillar"
    # Bumped pretrunas #3 must be replaced by stats or highlights
    kinds = {t["pillar"] for t in top}
    assert "stats" in kinds or "highlights" in kinds


def test_select_top_n_sorts_by_score():
    pool = [
        {"pillar": "pretrunas", "score": 0.5, "payload": {"i": 1}},
        {"pillar": "stats", "score": 0.9, "payload": {"i": 2}},
        {"pillar": "highlights", "score": 0.7, "payload": {"i": 3}},
    ]
    top = select_top_n(pool, n=3, per_pillar_cap=2)
    assert [t["payload"]["i"] for t in top] == [2, 3, 1]


def test_select_top_n_empty_pool():
    assert select_top_n([], n=3, per_pillar_cap=2) == []
