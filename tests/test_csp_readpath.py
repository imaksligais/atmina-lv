"""``src/csp/tables.py`` konfigurācija + ``src/csp/insights.py`` + tas, ko no
tiem tiešām lasa ``src/render/statistika.py``.

**Saucējs (plāna 6.1):**
- ``src/csp/tables.py`` — **4 no 4** moduļa eksportiem (``TABLES``,
  ``FREQ_PERIODS_PER_YEAR``, ``DOMAIN_COLORS``, ``DASHBOARD_ORDER``). Funkciju
  modulī nav; segtas arī abas ``format_*`` lambdas visos 10 galdos.
- ``src/csp/insights.py`` — **1 no 1** publiskās (``generate_insight``) un
  **3 no 3** privātajām (``_freq_label``, ``_extract_year``, ``_yoy_change``).

Lasīšanas ceļš ir ``src/render/statistika.py:29-30`` imports plus TIEŠI tie trīs
SQL vaicājumi, ko tas izpilda (``statistika.py:120``, ``:224``, ``:258``). Testi
tos atkārto burtiski pār pagaidu ``csp.db``, nevis sauc ``generate_statistika``
— pilnais renderis vilktu Jinja vidi, Chart.js lejupielādi un ``output/`` koku,
un tad vārti mērītu renderi, ne CSP klasteri.

**DB: pagaidu** (``tmp_path`` → ``<repo>/.pytest-tmp``). **Tīkls: nav.**
"""

from __future__ import annotations

import pytest

from src.csp import db as csp_db
from src.csp import sync as csp_sync
from src.csp.insights import (
    _extract_year,
    _freq_label,
    _yoy_change,
    generate_insight,
)
from src.csp.tables import (
    DASHBOARD_ORDER,
    DOMAIN_COLORS,
    FREQ_PERIODS_PER_YEAR,
    TABLES,
)

# Renderis (src/render/statistika.py) katram galdam pieprasa tieši šīs atslēgas.
RENDERER_REQUIRED_KEYS = {
    "path", "label", "domain", "freq", "unit", "history_years", "query",
    "value_indicator", "topics", "keywords", "trend_direction",
    "format_value", "format_short",
}

# Burtiskie vaicājumi no src/render/statistika.py.
SQL_SERIES = (
    "SELECT period, value FROM csp_data WHERE table_id=? AND geo='LV' ORDER BY period"
)
SQL_UPDATED = "SELECT csp_updated FROM csp_metadata WHERE table_id=?"
SQL_META = "SELECT * FROM csp_metadata WHERE table_id=?"


# --- tables.py -------------------------------------------------------------


def test_dashboard_order_covers_every_table_exactly_once():
    """Saucējs: 10 galdi. Renderis iterē ``DASHBOARD_ORDER``, ne ``TABLES``.

    Galds, kas ir ``TABLES``, bet nav ``DASHBOARD_ORDER``, tiek sinhronizēts
    un nekad neparādās — klusa nulle, ne kļūda.
    """
    assert len(DASHBOARD_ORDER) == len(set(DASHBOARD_ORDER)) == len(TABLES) == 10
    assert set(DASHBOARD_ORDER) == set(TABLES)


def test_every_table_carries_every_key_the_renderer_reads():
    for table_id, cfg in TABLES.items():
        missing = RENDERER_REQUIRED_KEYS - set(cfg)
        assert not missing, f"{table_id} trūkst: {sorted(missing)}"


def test_every_freq_resolves_in_freq_periods_per_year():
    """Nezināms ``freq`` uzsprāgtu ``_build_query_with_time`` ar KeyError."""
    for table_id, cfg in TABLES.items():
        assert cfg["freq"] in FREQ_PERIODS_PER_YEAR, table_id


def test_every_domain_has_a_color():
    """Trūkstoša krāsa renderī izietu kā tukšs stils, ne kā kļūda."""
    domains = {cfg["domain"] for cfg in TABLES.values()}
    assert domains <= set(DOMAIN_COLORS)
    assert domains == {"economy", "social", "prices", "state"}


def test_format_lambdas_survive_negative_zero_and_large_values():
    """Renderis sauc abas formatētājas pār dzīvām vērtībām bez try/except."""
    for table_id, cfg in TABLES.items():
        for value in (-1234.5, 0.0, 0.1, 1_500_000.0):
            assert isinstance(cfg["format_value"](value), str), (table_id, value)
            assert isinstance(cfg["format_short"](value), str), (table_id, value)


def test_trend_direction_values_are_the_three_insights_accepts():
    assert {cfg["trend_direction"] for cfg in TABLES.values()} <= {
        "higher_is_better", "lower_is_better", "neutral",
    }


def test_configured_topics_are_pinned_including_the_one_that_is_not_canonical():
    """Raksturojums, ne apstiprinājums.

    ``populate_metadata_and_topics`` raksta ``topic_links.topic`` NEIZEJOT caur
    ``src.topic_map.normalize_topic`` — atšķirībā no ``store_claim()``. 19 no 20
    ievadītajām tēmām normalizējas pašas uz sevi; ``'Demogrāfija'`` (IRS010m,
    IBE010) normalizētos uz ``'Sociālā politika'``, tāpēc DB glabājas forma,
    kas nesakrīt ar 33 kanonisko grupu konvenciju. Šodien tas nevienam nesāp,
    jo ``topic_links`` nav neviena lasītāja (grep pār ``src/``: 0), bet tas ir
    tieši tāda forma, kas sabojā tēmu grupēšanu, tiklīdz lasītājs parādās.
    """
    from src.topic_map import normalize_topic

    drifting = {
        (table_id, topic)
        for table_id, cfg in TABLES.items()
        for topic in cfg["topics"]
        if normalize_topic(topic) != topic
    }
    assert drifting == {("IRS010m", "Demogrāfija"), ("IBE010", "Demogrāfija")}
    assert normalize_topic("Demogrāfija") == "Sociālā politika"


# --- insights.py -----------------------------------------------------------


def test_generate_insight_needs_at_least_two_points():
    assert generate_insight([]) == ""
    assert generate_insight([("2026M01", 1.0)]) == ""


def test_generate_insight_reports_an_upward_streak_and_the_record_high():
    values = [(f"2021M0{i}", float(i)) for i in range(1, 7)]
    assert generate_insight(values) == "aug 5 mēn. pēc kārtas. augstākais kopš 2021"


def test_generate_insight_reports_a_downward_streak_and_the_record_low():
    periods = [f"2021M0{i}" for i in range(1, 7)]
    values = list(zip(periods, [6.0, 5.0, 4.0, 3.0, 2.0, 1.0], strict=True))
    assert generate_insight(values) == "sarūk 5 mēn. pēc kārtas. zemākais kopš 2021"


@pytest.mark.parametrize("periods,expect_word", [
    (["2021Q1", "2021Q2", "2021Q3", "2021Q4", "2022Q1"], "cet."),
    (["2019", "2020", "2021", "2022", "2023"], "g."),
])
def test_generate_insight_frequency_label_comes_from_the_FIRST_period(periods, expect_word):
    """``_freq_label(values[0][0])`` — pirmais, ne pēdējais periods.

    Jauktā sērijā (gada vēsture + mēneša aste) etiķete nāktu no vēstures gala.
    """
    values = list(zip(periods, [1.0, 2.0, 3.0, 4.0, 5.0], strict=True))
    assert expect_word in generate_insight(values)


def test_generate_insight_falls_back_to_year_over_year_when_no_streak_or_record():
    values = [
        ("2024M01", 100.0), ("2024M02", 90.0), ("2024M03", 120.0),
        ("2024M04", 95.0), ("2025M01", 50.0), ("2025M02", 130.0),
        ("2025M03", 105.0),
    ]
    assert generate_insight(values) == "-12.5% g/g"


@pytest.mark.parametrize("last,expect", [(5.0, "nemainās"), (6.0, "pieaug"), (4.0, "sarūk")])
def test_generate_insight_last_resort_direction(last, expect):
    """Divi punkti, nav g/g pāra → vienkāršs virziens."""
    assert generate_insight([("2026M05", 5.0), ("2026M06", last)]) == expect


def test_generate_insight_joins_clauses_with_a_dot_that_also_ends_an_abbreviation():
    """Raksturojums: izvadi NEDRĪKST dalīt pēc ``". "``.

    Savienotājs ir ``". "``, bet biežuma etiķete pati beidzas ar punktu
    (``mēn.`` / ``cet.`` / ``g.``), tāpēc "aug 5 mēn. pēc kārtas. augstākais
    kopš 2021" pēc ``". "`` sadalās TRĪS daļās, ne divās. Klauzulu vairāk par
    divām būt nevar — ``generate_insight`` pievieno maksimums divas (g/g zars
    darbojas tikai ``if not parts``), tāpēc ``parts[:2]`` griezums nekad
    nenostrādā. Vārts te ir tieši pret to, ka kāds lasītājs sāktu skaitīt
    klauzulas pēc punkta.
    """
    values = [(f"2021M0{i}", float(i)) for i in range(1, 7)]
    out = generate_insight(values)
    assert out.count(". ") == 2                      # divas klauzulas, trīs punkti
    assert out.split(". ") == ["aug 5 mēn", "pēc kārtas", "augstākais kopš 2021"]


def test_generate_insight_ignores_the_direction_argument():
    """``direction`` ir pieņemts, bet NElietots (``# noqa: ARG001``).

    Renderis padod ``cfg['trend_direction']`` katrā izsaukumā, tāpēc ir viegli
    noticēt, ka tas kaut ko maina. Nemaina.
    """
    values = [(f"2021M0{i}", float(i)) for i in range(1, 7)]
    base = generate_insight(values)
    assert generate_insight(values, "lower_is_better") == base
    assert generate_insight(values, "higher_is_better") == base
    assert generate_insight(values, "neutral") == base


@pytest.mark.parametrize("period,expect", [
    ("2026M01", "mēn."), ("2026Q1", "cet."), ("2026", "g."),
])
def test_freq_label(period, expect):
    assert _freq_label(period) == expect


def test_extract_year_takes_the_first_four_chars():
    assert _extract_year("2025M01") == _extract_year("2025Q1") == _extract_year("2025") == "2025"


def test_yoy_change_matches_the_same_quarter_last_year():
    assert _yoy_change([("2025Q2", 200.0), ("2026Q2", 220.0)]) == pytest.approx(10.0)


def test_yoy_change_is_none_when_the_prior_period_is_zero_or_absent():
    assert _yoy_change([("2025M06", 0.0), ("2026M06", 5.0)]) is None   # dalīšana ar 0
    assert _yoy_change([("2024M06", 5.0), ("2026M06", 7.0)]) is None   # nav pāra


def test_yoy_change_raises_on_a_non_numeric_annual_period():
    """ATRADUMS, pinēts kā raksturojums — NAV apstiprinājums, ka tā ir pareizi.

    ``_yoy_change`` sargā M un Q zarus ar regex un atgriež ``None``, ja tie
    nesakrīt, bet GADA zars dara kailu ``int(latest_period)``. Negaidīta perioda
    etiķete no CSP (T12 klase: "formāta maiņa, ne noņemšana") uzspridzina visu
    ``generate_statistika`` renderi ar ``ValueError``, nevis degradējas.
    Labojums pieder ``src/csp/insights.py`` (ārpus šī testa autora tvēruma);
    kad tas notiks, šis tests jāapgriež uz ``is None``.
    """
    with pytest.raises(ValueError):
        _yoy_change([("nezināms", 1.0), ("arī-nezināms", 2.0)])


# --- renderer read path over a tiny csp.db --------------------------------


@pytest.fixture
def tiny_csp_db(tmp_path):
    """``csp.db`` ar diviem galdiem: viens ar datiem, viens tukšs."""
    conn = csp_db.init_db(str(tmp_path / "csp.db"))
    csp_sync.populate_metadata_and_topics(conn)
    csp_sync.upsert_rows(conn, "NVA011m", "M", [
        {"period": p, "value": v, "breakdown": "_total_"}
        for p, v in [("2026M03", 6.4), ("2026M04", 6.2), ("2026M05", 6.0)]
    ])
    conn.execute(
        "UPDATE csp_metadata SET csp_updated=?, last_sync=? WHERE table_id='NVA011m'",
        ("2026-08-28T07:00:00Z", "2026-08-28T09:00:00+00:00"),
    )
    conn.commit()
    yield conn
    conn.close()


def test_renderer_series_query_returns_ordered_period_value_pairs(tiny_csp_db):
    rows = tiny_csp_db.execute(SQL_SERIES, ("NVA011m",)).fetchall()
    assert [(r[0], r[1]) for r in rows] == [
        ("2026M03", 6.4), ("2026M04", 6.2), ("2026M05", 6.0),
    ]


def test_renderer_skips_a_table_with_no_rows(tiny_csp_db):
    """``if not rows: continue`` — konfigurēts, bet nesinhronizēts galds
    vienkārši pazūd no dashboard. Klusa izlaišana pēc dizaina; pinēts, lai
    neviens to nesajauktu ar renderēšanas kļūdu."""
    assert tiny_csp_db.execute(SQL_SERIES, ("PCI021m",)).fetchall() == []


def test_renderer_metadata_queries_return_what_the_template_needs(tiny_csp_db):
    updated = tiny_csp_db.execute(SQL_UPDATED, ("NVA011m",)).fetchone()
    assert (updated[0] or "")[:10] == "2026-08-28"

    meta = dict(tiny_csp_db.execute(SQL_META, ("NVA011m",)).fetchone())
    assert {"table_id", "label_lv", "domain", "freq", "unit",
            "last_sync", "csp_updated"} <= set(meta)
    assert meta["label_lv"] == TABLES["NVA011m"]["label"]


def test_renderer_end_to_end_slice_produces_a_card(tiny_csp_db):
    """Tas pats aprēķins, ko dara ``statistika.py`` katrai kartītei."""
    cfg = TABLES["NVA011m"]
    rows = [{"period": r[0], "value": r[1]}
            for r in tiny_csp_db.execute(SQL_SERIES, ("NVA011m",))]
    latest, prev = rows[-1], rows[-2]
    values_tuples = [(r["period"], r["value"]) for r in rows if r["value"] is not None]

    assert cfg["format_short"](latest["value"]) == "6.0%"
    assert latest["value"] - prev["value"] == pytest.approx(-0.2)
    assert generate_insight(values_tuples, cfg["trend_direction"]) == "sarūk"


def test_renderer_series_query_does_not_filter_breakdown(tiny_csp_db):
    """ATRADUMS, pinēts kā raksturojums.

    ``csp_data`` PK ietver ``breakdown``, bet renderis vaicā TIKAI pēc
    ``table_id`` + ``geo``. Ja kāds galds kādreiz sinhronizētu vairāk nekā vienu
    breakdown (3D atbilde, sk. ``tests/fixtures/csp_jsonstat2_3d.json``),
    ``rows[-1]`` un ``rows[-2]`` salīdzinātu DAŽĀDAS sērijas viena perioda
    ietvaros, un "izmaiņa" būtu GRS↔NET starpība, ne laika izmaiņa. Šodien to
    novērš tikai tas, ka katra ``TABLES`` konfigurācija fiksē breakdown
    dimensiju savā ``query`` (piem. DSV010m: ``GRS_NET`` → ``["GRS"]``) — tas ir
    konvencijas, ne koda, vārts.
    """
    csp_sync.upsert_rows(tiny_csp_db, "NVA011m", "M", [
        {"period": "2026M05", "value": 4.0, "breakdown": "NET"},
    ])
    rows = tiny_csp_db.execute(SQL_SERIES, ("NVA011m",)).fetchall()
    assert len(rows) == 4
    assert [r[0] for r in rows[-2:]] == ["2026M05", "2026M05"]
