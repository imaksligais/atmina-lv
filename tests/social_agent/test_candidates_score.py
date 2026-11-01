from datetime import datetime, timedelta

from src.social_agent.candidates import interest_score


def test_interest_score_all_max():
    score = interest_score(
        salience=1.0,
        severity="critical",
        age_hours=0,
        candidate_topics={"a", "b"},
        recent_topics=set(),
    )
    assert abs(score - 1.0) < 0.001


def test_interest_score_all_zero():
    score = interest_score(
        salience=0.0,
        severity="none",
        age_hours=9999,
        candidate_topics=set(),
        recent_topics=set(),
    )
    # freshness clamps to 0; novelty with empty jaccard denominator → 1 by convention
    # salience 0 + severity 0 + freshness 0 + novelty 0.2 = 0.2
    # (empty candidate set has no overlap → novelty is 1.0; 0.2 * 1.0 = 0.2)
    assert abs(score - 0.2) < 0.001


def test_interest_score_severity_mapping():
    kw = dict(salience=0.0, age_hours=0, candidate_topics=set(), recent_topics=set())
    # freshness=1.0, novelty=1.0 → base = 0.4
    # severity_norm: critical=1.0 → +0.3 = 0.7
    assert abs(interest_score(severity="critical", **kw) - 0.7) < 0.001
    assert abs(interest_score(severity="major", **kw) - (0.4 + 0.3 * 0.7)) < 0.001
    assert abs(interest_score(severity="minor", **kw) - (0.4 + 0.3 * 0.4)) < 0.001
    assert abs(interest_score(severity="none", **kw) - 0.4) < 0.001
    # unknown → 0.6 default (treated as "default" for non-pretrunas pillars)
    assert abs(interest_score(severity=None, **kw) - (0.4 + 0.3 * 0.6)) < 0.001


def test_interest_score_freshness_decays_linearly():
    kw = dict(salience=0.0, severity="none", candidate_topics=set(), recent_topics=set())
    # freshness = max(0, 1 - age_hours/168)
    # age=0 → 1.0, age=84 → 0.5, age=168 → 0.0, age=200 → 0.0
    assert abs(interest_score(age_hours=0, **kw) - 0.4) < 0.001       # 0.2*1 + novelty 0.2
    assert abs(interest_score(age_hours=84, **kw) - 0.3) < 0.001      # 0.2*0.5 + 0.2
    assert abs(interest_score(age_hours=168, **kw) - 0.2) < 0.001     # 0 + 0.2
    assert abs(interest_score(age_hours=200, **kw) - 0.2) < 0.001     # clamp


def test_interest_score_novelty_jaccard():
    kw = dict(salience=0.0, severity="none", age_hours=0)
    # Full overlap → novelty 0 → base 0.2 (freshness only)
    s = interest_score(candidate_topics={"a", "b"}, recent_topics={"a", "b"}, **kw)
    assert abs(s - 0.2) < 0.001
    # Half overlap → jaccard = 1/3 → novelty = 2/3 → 0.2 + 0.2*(2/3)
    s = interest_score(candidate_topics={"a", "b"}, recent_topics={"a", "c"}, **kw)
    assert abs(s - (0.2 + 0.2 * (2/3))) < 0.01
