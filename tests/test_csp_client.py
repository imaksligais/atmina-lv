"""``src/csp/client.py`` — PxWeb v1 klients + JSON-stat2 parseris.

**Saucējs (plāna 6.1): 2 no 2 moduļa publiskajām funkcijām** —
``fetch_table``, ``parse_jsonstat2``. Privātu funkciju modulī nav; segts arī
modulī esošais globālais rate-limit stāvoklis (``_last_request_time``).

Kāpēc šie vārti vispār: līdz 2026-09-05 viss ``src/csp/`` klasteris (614 rindas,
5 moduļi) bija bez neviena testa un bez ieejas punkta — tieši tā klase, ko
CLAUDE.md sauc par "IZPILDĪTS nozīmē, ka kods ir kokā, ne ka tas jebkad
skrēja". Ja ``sync_all()`` kādreiz palaidīs pār ``data/csp.db`` (izsekots
binārs, kas aiziet publiskajā spogulī), tas notiktu bez neviena vārta.

**Tīkls: nekad.** ``httpx.post`` ir monkeypatchots katrā testā, kas sauc
``fetch_table``; ``time.sleep`` arī, citādi rate-limit + backoff sagulētu ~7 s.

**Fikstūru izcelsme (godīgi):** ``tests/fixtures/csp_jsonstat2_*.json`` ir
KONSTRUĒTI pēc ``parse_jsonstat2`` dokumentētās gaidītās struktūras (dim ``id``
saraksts, ``size``, ``dimension[*].category.index`` kā dict), NEVIS notverti no
dzīvā CSP API. Tie pin parsera līgumu, ne CSP vada formātu. ``ContentsCode``
kods fikstūrās ir ``"EliminatedValue"``, jo tieši to ``src/csp/tables.py``
sagaida kā ``value_indicator`` filtra vērtību visos 10 galdos.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from src.csp import client as csp_client

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def _no_sleep_no_rate_limit_bleed(monkeypatch):
    """Modulis tur rate-limit laiku MODUĻA globālajā mainīgajā.

    Bez atiestates testu secība maina to, cik ilgi nākamais tests "guļ", un
    ``sleep`` izsaukumu skaits vairs nav deterministisks. Šeit gan miegs, gan
    globālais laiks tiek fiksēts.
    """
    slept: list[float] = []
    monkeypatch.setattr(csp_client.time, "sleep", lambda s: slept.append(s))
    monkeypatch.setattr(csp_client, "_last_request_time", 0.0)
    yield slept
    monkeypatch.setattr(csp_client, "_last_request_time", 0.0)


# --- parse_jsonstat2 -------------------------------------------------------


def test_parse_2d_contentscode_x_time():
    """2D atbilde: viena rinda uz periodu, ``breakdown`` = ``_total_``."""
    rows = csp_client.parse_jsonstat2(_load("csp_jsonstat2_2d.json"))
    assert [r["period"] for r in rows] == ["2026M03", "2026M04", "2026M05", "2026M06"]
    assert {r["breakdown"] for r in rows} == {"_total_"}
    assert {r["indicator"] for r in rows} == {"EliminatedValue"}
    assert [r["value"] for r in rows] == [6.4, 6.2, 6.0, None]
    # `updated` ir kopīgs visām rindām un aiziet uz csp_metadata.csp_updated
    assert {r["updated"] for r in rows} == {"2026-08-28T07:00:00Z"}


def test_parse_2d_keeps_null_values_for_the_caller_to_drop():
    """Parseris NEmet ārā ``None`` — to dara ``sync.upsert_rows``.

    Svarīgi, jo tas nozīmē: ja kāds jauns lasītājs paņem ``parse_jsonstat2``
    izvadi tieši, tam pašam jātiek galā ar tukšajiem periodiem.
    """
    rows = csp_client.parse_jsonstat2(_load("csp_jsonstat2_2d.json"))
    assert any(r["value"] is None for r in rows)


def test_parse_3d_breakdown_is_the_first_non_time_non_contents_dimension():
    """3D atbilde: ``GRS_NET`` kļūst par ``breakdown``, row-major kārtībā."""
    rows = csp_client.parse_jsonstat2(_load("csp_jsonstat2_3d.json"))
    assert len(rows) == 6
    grs = [r for r in rows if r["breakdown"] == "GRS"]
    net = [r for r in rows if r["breakdown"] == "NET"]
    assert [r["value"] for r in grs] == [1710.0, 1745.0, 1780.0]
    assert [r["value"] for r in net] == [1240.0, 1265.0, 1290.0]
    assert [r["period"] for r in grs] == ["2026M04", "2026M05", "2026M06"]


def test_parse_orders_codes_by_category_index_not_json_key_order():
    """Kodu secību nosaka ``category.index`` vērtība, ne JSON atslēgu secība.

    Šis ir īstais row-major dekodēšanas balsts: ja kāds "sakārtotu" kodus
    alfabētiski, vērtības klusi pieskaitītos nepareizajiem periodiem.
    """
    data = _load("csp_jsonstat2_2d.json")
    # Apgriezta atslēgu secība, TĀ PATI index karte -> tas pats rezultāts.
    time_cat = data["dimension"]["TIME"]["category"]
    time_cat["index"] = dict(reversed(list(time_cat["index"].items())))
    rows = csp_client.parse_jsonstat2(data)
    assert [r["period"] for r in rows] == ["2026M03", "2026M04", "2026M05", "2026M06"]


def test_parse_without_contentscode_uses_default_indicator():
    """Bez ``ContentsCode`` dimensijas indikators ir ``_default_``."""
    data = _load("csp_jsonstat2_2d.json")
    data["id"] = ["TIME"]
    data["size"] = [4]
    del data["dimension"]["ContentsCode"]
    rows = csp_client.parse_jsonstat2(data)
    assert {r["indicator"] for r in rows} == {"_default_"}
    assert {r["breakdown"] for r in rows} == {"_total_"}


def test_parse_requires_a_time_dimension():
    """Bez ``TIME`` parseris krīt skaļi (``ValueError``), nevis atgriež tukšu.

    Tas ir vēlamā puse no T12 ("upstream formāta maiņa, ne noņemšana"): klusa
    tukša atbilde izskatītos pēc tukšas dienas.
    """
    data = _load("csp_jsonstat2_2d.json")
    data["id"] = ["ContentsCode"]
    with pytest.raises(ValueError):
        csp_client.parse_jsonstat2(data)


# --- fetch_table -----------------------------------------------------------


class _Resp:
    def __init__(self, payload: dict, status: int = 200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "boom", request=httpx.Request("POST", "https://example.invalid"),
                response=httpx.Response(self.status_code),
            )

    def json(self):
        return self._payload


def test_fetch_table_posts_expected_url_and_body(monkeypatch):
    calls: list[tuple] = []

    def fake_post(url, json=None, timeout=None):  # noqa: A002
        calls.append((url, json, timeout))
        return _Resp({"ok": True})

    monkeypatch.setattr(csp_client.httpx, "post", fake_post)
    out = csp_client.fetch_table("EMP/NBBA/NVA/NVA011m", [{"code": "ContentsCode"}])

    assert out == {"ok": True}
    assert len(calls) == 1
    url, body, timeout = calls[0]
    assert url == f"{csp_client.BASE_URL}/EMP/NBBA/NVA/NVA011m"
    assert body == {
        "query": [{"code": "ContentsCode"}],
        "response": {"format": "json-stat2"},
    }
    assert timeout == csp_client.TIMEOUT


def test_fetch_table_base_url_is_the_csp_pxweb_host():
    """Hosta maiņa ir apzināts lēmums, ne drifts (CSP allowlist blakusefekts)."""
    assert csp_client.BASE_URL == (
        "https://data.stat.gov.lv/api/v1/lv/OSP_PUB/START"
    )


def test_fetch_table_retries_transport_errors_with_exponential_backoff(monkeypatch, _no_sleep_no_rate_limit_bleed):
    slept = _no_sleep_no_rate_limit_bleed
    attempts = {"n": 0}

    def flaky_post(url, json=None, timeout=None):  # noqa: A002
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise httpx.TransportError("connection reset")
        return _Resp({"attempt": attempts["n"]})

    monkeypatch.setattr(csp_client.httpx, "post", flaky_post)
    out = csp_client.fetch_table("X/Y", [])

    assert out == {"attempt": 3}
    assert attempts["n"] == 3
    # Divi miegu veidi sajaukti vienā sarakstā: backoff ir vesels skaitlis
    # (``2 ** attempt``), rate-limit gaidīšana ir float (``RATE_LIMIT_SEC -
    # elapsed``). Tips tos atšķir; pin tieši backoff eksponenti.
    assert [s for s in slept if isinstance(s, int)] == [1, 2]


def test_fetch_table_raises_after_max_retries(monkeypatch):
    attempts = {"n": 0}

    def always_fail(url, json=None, timeout=None):  # noqa: A002
        attempts["n"] += 1
        raise httpx.TransportError("down")

    monkeypatch.setattr(csp_client.httpx, "post", always_fail)
    with pytest.raises(httpx.TransportError):
        csp_client.fetch_table("X/Y", [])
    assert attempts["n"] == csp_client.MAX_RETRIES == 3


def test_fetch_table_retries_http_status_errors_too(monkeypatch):
    """500 iet cauri tam pašam retry ceļam kā transporta kļūda."""
    attempts = {"n": 0}

    def failing(url, json=None, timeout=None):  # noqa: A002
        attempts["n"] += 1
        return _Resp({}, status=500)

    monkeypatch.setattr(csp_client.httpx, "post", failing)
    with pytest.raises(httpx.HTTPStatusError):
        csp_client.fetch_table("X/Y", [])
    assert attempts["n"] == 3


def test_fetch_table_rate_limits_between_calls(monkeypatch, _no_sleep_no_rate_limit_bleed):
    """Otrs izsaukums uzreiz pēc pirmā gaida līdz ``RATE_LIMIT_SEC``."""
    slept = _no_sleep_no_rate_limit_bleed
    monkeypatch.setattr(csp_client.httpx, "post",
                        lambda url, json=None, timeout=None: _Resp({}))  # noqa: A002
    clock = {"t": 1000.0}
    monkeypatch.setattr(csp_client.time, "time", lambda: clock["t"])

    csp_client.fetch_table("A", [])
    slept.clear()
    clock["t"] += 0.25          # tikai 0,25 s vēlāk
    csp_client.fetch_table("B", [])

    assert slept and slept[0] == pytest.approx(csp_client.RATE_LIMIT_SEC - 0.25)
