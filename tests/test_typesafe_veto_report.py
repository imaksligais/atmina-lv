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


def test_all_unavailable_window_is_not_a_clean_shadow_day():
    # 2026-09-22: TypeSafe answered HTTP 402 for every call — judged 112,
    # vetoed 0, unavailable 112. "vetoed 0" must not read as a clean shadow
    # day; the window scored nothing and cannot count toward the 7 days.
    from scripts.typesafe_veto_report import shadow_verdict

    dead = [{"pid": 1, "p_same": None, "vetoed": False}] * 3
    assert shadow_verdict(summarize(dead)) == "no_evidence"
    assert shadow_verdict(summarize([])) == "no_evidence"
    ok = [{"pid": 1, "p_same": 0.9, "vetoed": False}]
    assert shadow_verdict(summarize(ok)) == "scored"
