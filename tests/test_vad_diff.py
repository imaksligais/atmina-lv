from src.vad.diff import compute_section_deltas


def test_position_renamed_in_same_entity_pairs_only_one_to_one():
    # Viens pret vienu tajā pašā iestādē → viena «mainījies» rinda ar abiem nosaukumiem.
    prev = [{"position_title": "Eiropas Parlamenta deputāte", "entity_name": "Eiropas Parlaments"}]
    curr = [{"position_title": "Deputāts", "entity_name": "Eiropas Parlaments"}]
    out = compute_section_deltas("positions", prev, curr)
    assert [(d.delta, d.diff_text) for d in out] == [
        ("modified", "amats: Eiropas Parlamenta deputāte → Deputāts")]
    # Divi pret diviem tajā pašā iestādē — nav zināms, kurš ar kuru; pāros neliek.
    prev = [{"position_title": "Rīgas domes deputāte", "entity_reg_number": "9", "entity_name": "Saeima"},
            {"position_title": "Komisijas priekšsēdētāja", "entity_reg_number": "9", "entity_name": "Saeima"}]
    curr = [{"position_title": "Deputāte", "entity_reg_number": "9", "entity_name": "Saeima"},
            {"position_title": "Sekretāre", "entity_reg_number": "9", "entity_name": "Saeima"}]
    out = compute_section_deltas("positions", prev, curr)
    assert sorted(d.delta for d in out) == ["new", "new", "removed", "removed"]
    # Iestādes rakstības variants (reģistrs) ir tā pati iestāde.
    prev = [{"position_title": "Deputāts", "entity_name": "Eiropas Parlaments"}]
    curr = [{"position_title": "Deputāts", "entity_name": "Eiropas parlaments"}]
    assert [d.delta for d in compute_section_deltas("positions", prev, curr)] == ["unchanged"]


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
    assert out[0].diff_text == "summa: 50\u00a0000 → 76\u00a0000 (+52\u00a0%)"


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


def test_debts_same_currency_rows_do_not_collapse():
    """Multiset regresija: divas parādu rindas ar tukšu kreditoru un to pašu
    valūtu (reālais VAD 3-kolonnu formāts) nedrīkst salipt vienā rindā."""
    prev = [{"creditor_name": "", "creditor_reg_number": None, "currency": "EUR", "amount": 10000.0}]
    curr = [
        {"creditor_name": "", "creditor_reg_number": None, "currency": "EUR", "amount": 10000.0},
        {"creditor_name": "", "creditor_reg_number": None, "currency": "EUR", "amount": 30000.0},
    ]
    out = compute_section_deltas("debts", prev, curr)
    assert len(out) == 2
    assert sorted(d.delta for d in out) == ["new", "unchanged"]


def test_loans_given_freeform_multi_currency_render_all():
    """Vecā 1-kolonnu formāta šūna '5 928 853 USD, 450 000 EUR, 7813 LVL'
    dod 3 rindas ar vienādu amount_in_words — visas jāparāda."""
    words = "5 928 853 USD, 450 000 EUR, 7813 LVL"
    curr = [
        {"currency": "USD", "amount": 5928853.0, "amount_in_words": words},
        {"currency": "EUR", "amount": 450000.0, "amount_in_words": words},
        {"currency": "LVL", "amount": 7813.0, "amount_in_words": words},
    ]
    out = compute_section_deltas("loans_given", [], curr)
    assert len(out) == 3
