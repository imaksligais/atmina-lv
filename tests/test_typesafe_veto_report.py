from scripts.typesafe_veto_report import summarize


def test_summarize_counts_vetoes_per_politician():
    ev = [
        {"pid": 24, "p_same": 0.1, "vetoed": True},
        {"pid": 24, "p_same": 0.2, "vetoed": True},
        {"pid": 158, "p_same": 0.9, "vetoed": False},
        {"pid": 158, "p_same": None, "vetoed": False},
    ]
    s = summarize(ev)
    assert s == {"judged": 4, "vetoed": 2, "unavailable": 1, "by_pid": {24: 2}}
