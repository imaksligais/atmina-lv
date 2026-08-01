from src.vad.diff import compute_section_deltas


def test_new_company():
    prev = []
    curr = [{"reg_number": "40003555683", "company_name": "AVADEL", "capital_kind": "Kapitala dalas",
             "units": 1000.0, "total_value": 10000.0}]
    out = compute_section_deltas("companies", prev, curr)
    assert len(out) == 1
    assert out[0].delta == "new"


def test_income_modified_above_threshold():
    prev = [{"source": "Saeima", "income_type": "Alga", "currency": "EUR", "amount": 50000.0}]
    curr = [{"source": "Saeima", "income_type": "Alga", "currency": "EUR", "amount": 76000.0}]
    out = compute_section_deltas("income", prev, curr)
    assert len(out) == 1
    assert out[0].delta == "modified"
    assert out[0].diff_text is not None
    assert "amount: 50000 → 76000" in out[0].diff_text


def test_income_unchanged_below_threshold():
    prev = [{"source": "Saeima", "income_type": "Alga", "currency": "EUR", "amount": 76000.0}]
    curr = [{"source": "Saeima", "income_type": "Alga", "currency": "EUR", "amount": 76200.0}]
    out = compute_section_deltas("income", prev, curr)
    assert out[0].delta == "unchanged"


def test_removed_property():
    prev = [{"property_type": "Dzivoklis", "location": "Latvija, Jurmala", "ownership_status": "lietosana"}]
    curr = []
    out = compute_section_deltas("real_estate", prev, curr)
    assert len(out) == 1
    assert out[0].delta == "removed"


def test_ownership_change():
    prev = [{"property_type": "Zeme", "location": "Annenieku pag.", "ownership_status": "valdijuma"}]
    curr = [{"property_type": "Zeme", "location": "Annenieku pag.", "ownership_status": "ipasuma"}]
    out = compute_section_deltas("real_estate", prev, curr)
    deltas = sorted([d.delta for d in out])
    assert deltas == ["new", "removed"]


def test_family_unchanged():
    prev = [{"full_name": "INESE SLESERE", "relation": "Laulatais"}]
    curr = [{"full_name": "INESE SLESERE", "relation": "Laulatais"}]
    out = compute_section_deltas("family", prev, curr)
    assert out[0].delta == "unchanged"


def test_sort_order_modified_first():
    prev = [
        {"source": "A", "income_type": "Alga", "currency": "EUR", "amount": 100.0},
    ]
    curr = [
        {"source": "B", "income_type": "Davinajums", "currency": "EUR", "amount": 50.0},
        {"source": "A", "income_type": "Alga", "currency": "EUR", "amount": 200.0},
    ]
    out = compute_section_deltas("income", prev, curr)
    assert out[0].delta == "modified"
    assert out[1].delta == "new"
