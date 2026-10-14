"""``src/vestnesis.py`` — Latvijas Vēstnesis JL divpakāpju fetčeris.

**Saucējs (plāna 6.1): 3 no 3 moduļa funkcijām** — ``fetch_jl_feed``,
``fetch_act_body``, ``extract_signers``. Segts arī ``ACT_URL_RE`` izlaišanas
zars un ``_SIGNER_RE`` trīs atpazīstamās parakstītāju formas.

**Tīkls: nekad.** ``httpx.Client`` ir aizvietots ar fake katrā testā, kas sauc
fetčeri. ``trafilatura`` savukārt tiek palaista ĪSTI pār lokālu HTML fikstūru —
tā ir tīra funkcija bez tīkla, un īsts izvilkums ir stiprāks pins nekā mock.

**Fikstūras (izcelsme godīgi):** ``tests/fixtures/vestnesis_jl_feed.xml`` un
``vestnesis_act.html`` ir KONSTRUĒTI pēc moduļa gaidītās struktūras (RSS
``item``/``link``/``pubDate``; MK noteikumu teksts ar parakstītāju rindām), nevis
notverti no dzīvās vestnesis.lv. Tie pin parsētāja līgumu, ne vestnesis.lv HTML.

**Laiks:** ``fetch_jl_feed`` griež pēc ``datetime.now()``, tāpēc katrs datuma
tests iet zem ``freeze_time("2026-09-05 12:00:00")`` — bez tā fikstūra kļūtu
sarkana pati no sevis, kad paiet nedēļa.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from freezegun import freeze_time

from src import vestnesis

FIXTURES = Path(__file__).resolve().parent / "fixtures"
FEED_XML = (FIXTURES / "vestnesis_jl_feed.xml").read_text(encoding="utf-8")
ACT_HTML = (FIXTURES / "vestnesis_act.html").read_text(encoding="utf-8")

NOW = "2026-09-05 12:00:00"


class _Resp:
    def __init__(self, text: str, status: int = 200):
        self.text = text
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "boom", request=httpx.Request("GET", "https://example.invalid"),
                response=httpx.Response(self.status_code),
            )


def _client_factory(resp, record: list | None = None):
    """Fake ``httpx.Client`` kontekstpārvaldnieks."""

    class _Client:
        def __init__(self, **kwargs):
            if record is not None:
                record.append(kwargs)

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def get(self, url):
            if record is not None:
                record.append({"url": url})
            if isinstance(resp, Exception):
                raise resp
            return resp

    return _Client


# --- fetch_jl_feed ---------------------------------------------------------


@freeze_time(NOW)
def test_fetch_jl_feed_parses_act_ids_and_keeps_feed_order(monkeypatch):
    monkeypatch.setattr(vestnesis.httpx, "Client", _client_factory(_Resp(FEED_XML)))
    items = vestnesis.fetch_jl_feed()

    # Saucējs: fikstūrā 6 ``item`` elementi. 4 iziet cauri, 2 tiek izmesti
    # (viens bez /ta/id/ ceļa, viens ārpus 7 dienu loga) — abi zari pinēti zemāk.
    assert [i["act_id"] for i in items] == ["360111", "360112", "360113", "360114"]
    assert items[0]["url"].endswith("360111-grozijumi-mk-noteikumos-nr-158")
    assert items[0]["title"] == "Grozījumi Ministru kabineta noteikumos Nr. 158"
    assert set(items[0]) == {"act_id", "title", "url", "published_at"}


@freeze_time(NOW)
def test_fetch_jl_feed_skips_links_without_an_act_id(monkeypatch):
    """Kategorijas lapa nav akts — bez ``/ta/id/N`` tā netiek ingestēta."""
    monkeypatch.setattr(vestnesis.httpx, "Client", _client_factory(_Resp(FEED_XML)))
    urls = [i["url"] for i in vestnesis.fetch_jl_feed()]
    assert not any("kategorija" in u for u in urls)


@freeze_time(NOW)
def test_fetch_jl_feed_drops_items_older_than_max_age_days(monkeypatch):
    monkeypatch.setattr(vestnesis.httpx, "Client", _client_factory(_Resp(FEED_XML)))
    assert "359001" not in {i["act_id"] for i in vestnesis.fetch_jl_feed()}
    # Ar plašāku logu tas pats akts atgriežas — vārts ir logs, ne saturs.
    wide = {i["act_id"] for i in vestnesis.fetch_jl_feed(max_age_days=60)}
    assert "359001" in wide


@freeze_time(NOW)
def test_fetch_jl_feed_max_age_days_is_actually_applied(monkeypatch):
    """Saucējs mainās līdz ar logu: 1 diena → tikai bezdatuma ieraksti."""
    monkeypatch.setattr(vestnesis.httpx, "Client", _client_factory(_Resp(FEED_XML)))
    narrow = vestnesis.fetch_jl_feed(max_age_days=1)
    assert [i["act_id"] for i in narrow] == ["360113", "360114"]


@freeze_time(NOW)
def test_fetch_jl_feed_keeps_items_whose_pubdate_cannot_be_parsed(monkeypatch):
    """Raksturojums: nesaprotams vai trūkstošs ``pubDate`` NEIZMET ierakstu.

    Tas ir apzināti (T12: formāta maiņa nav pazušana) — bet ar sekām: šādam
    ierakstam ``published_at`` ir ``None``, tātad tas apiet arī vecuma logu un
    parādīsies KATRĀ skrējienā, līdz kāds to nodedupē pēc ``act_id``.
    """
    monkeypatch.setattr(vestnesis.httpx, "Client", _client_factory(_Resp(FEED_XML)))
    by_id = {i["act_id"]: i for i in vestnesis.fetch_jl_feed()}
    assert by_id["360113"]["published_at"] is None      # "nezināms datums"
    assert by_id["360114"]["published_at"] is None      # nav pubDate elementa


@freeze_time(NOW)
def test_fetch_jl_feed_drops_the_timezone_instead_of_converting_it(monkeypatch):
    """Raksturojums: ``+0300`` tiek NOMESTS, ne pārrēķināts uz UTC/LV.

    ``parsedate_to_datetime(...).replace(tzinfo=None)`` patur SIENAS laiku no
    plūsmas. Fikstūras ``08:15:00 +0300`` tāpēc kļūst par ``08:15:00`` naivu.
    Rezultātā ``published_at`` ir "kā vestnesis.lv to uzrakstīja", un salīdzinot
    to ar ``now_lv()`` kolonnām, tas sakrīt tikai tāpēc, ka Latvija arī ir +03.
    """
    monkeypatch.setattr(vestnesis.httpx, "Client", _client_factory(_Resp(FEED_XML)))
    by_id = {i["act_id"]: i for i in vestnesis.fetch_jl_feed()}
    assert by_id["360111"]["published_at"] == "2026-09-03T08:15:00"


@freeze_time(NOW)
def test_fetch_jl_feed_sends_the_bot_user_agent(monkeypatch):
    record: list = []
    monkeypatch.setattr(vestnesis.httpx, "Client", _client_factory(_Resp(FEED_XML), record))
    vestnesis.fetch_jl_feed()
    kwargs = record[0]
    assert kwargs["headers"]["User-Agent"] == vestnesis.USER_AGENT
    assert kwargs["follow_redirects"] is True
    assert record[1]["url"] == vestnesis.JL_FEED_URL


@freeze_time(NOW)
def test_fetch_jl_feed_raises_on_a_non_200_feed(monkeypatch):
    """Plūsmas kļūme ir kļūme, nevis "šodien nekas nav publicēts" (T12/E5)."""
    monkeypatch.setattr(vestnesis.httpx, "Client", _client_factory(_Resp("", 503)))
    with pytest.raises(httpx.HTTPStatusError):
        vestnesis.fetch_jl_feed()


# --- fetch_act_body --------------------------------------------------------


def test_fetch_act_body_extracts_the_act_text(monkeypatch):
    """Īsta trafilatura pār lokālu HTML — bez tīkla, bez mock-a izvilkumam."""
    monkeypatch.setattr(vestnesis.httpx, "Client", _client_factory(_Resp(ACT_HTML)))
    body = vestnesis.fetch_act_body("https://www.vestnesis.lv/ta/id/360111")
    assert body is not None
    assert len(body) > 200
    assert "energoefektivitātes" in body
    assert "Ministru prezidente: E. Siliņa" in body
    # Navigācija un kājene ir izgrieztas — tas ir viss trafilatura mērķis.
    assert "Sākums" not in body


def test_fetch_act_body_returns_none_on_non_200(monkeypatch):
    monkeypatch.setattr(vestnesis.httpx, "Client", _client_factory(_Resp("", 404)))
    assert vestnesis.fetch_act_body("https://www.vestnesis.lv/ta/id/1") is None


def test_fetch_act_body_returns_none_on_transport_error(monkeypatch):
    monkeypatch.setattr(
        vestnesis.httpx, "Client",
        _client_factory(httpx.ConnectError("nav savienojuma")),
    )
    assert vestnesis.fetch_act_body("https://www.vestnesis.lv/ta/id/1") is None


def test_fetch_act_body_rejects_bodies_under_200_chars(monkeypatch):
    """Raksturojums: īss izvilkums = ``None``, un tas NEATŠĶIRAS no 404.

    Abi ceļi atgriež ``None``, tāpēc izsaucējs (``scripts/ingest_vestnesis.py``)
    nevar pateikt, vai lapa bija nepieejama vai tikai īsa. Klusās neveiksmes
    klase; pinēts, lai maiņa būtu apzināta.
    """
    monkeypatch.setattr(
        vestnesis.httpx, "Client",
        _client_factory(_Resp("<html><body><p>Ļoti īss.</p></body></html>")),
    )
    assert vestnesis.fetch_act_body("https://www.vestnesis.lv/ta/id/1") is None


# --- extract_signers -------------------------------------------------------


def test_extract_signers_finds_the_three_forms_in_a_real_extraction():
    import trafilatura

    text = trafilatura.extract(
        ACT_HTML, include_comments=False, include_tables=True, favor_recall=True
    )
    assert vestnesis.extract_signers(text) == ["E. Siliņa", "K. Melnis", "V. Valainis"]


@pytest.mark.parametrize("line,expect", [
    ("Ministru prezidente: E. Siliņa", ["E. Siliņa"]),
    ("Klimata un enerģētikas ministrs K. Melnis", ["K. Melnis"]),
    ("Valsts prezidents E. Rinkēvičs", ["E. Rinkēvičs"]),
    ("Saeimas priekšsēdētāja D. Mieriņa", ["D. Mieriņa"]),
    ("Tieslietu ministre I. Lībiņa-Egnere", ["I. Lībiņa-Egnere"]),
])
def test_extract_signers_recognized_forms(line, expect):
    assert vestnesis.extract_signers(line) == expect


def test_extract_signers_deduplicates_and_preserves_first_seen_order():
    body = (
        "Ministru prezidente: E. Siliņa\n"
        "Ekonomikas ministrs V. Valainis\n"
        "Ministru prezidente E. Siliņa\n"
    )
    assert vestnesis.extract_signers(body) == ["E. Siliņa", "V. Valainis"]


def test_extract_signers_collapses_whitespace_inside_a_name():
    assert vestnesis.extract_signers("Ministru prezidente:  E.   Siliņa") == ["E. Siliņa"]


def test_extract_signers_returns_empty_when_no_signature_block():
    assert vestnesis.extract_signers("Noteikumi stājas spēkā 2026. gada 1. oktobrī.") == []


def test_extract_signers_requires_the_initial_surname_form():
    """Raksturojums: bez ``I. Uzvārds`` formas paraksts NETIEK atpazīts.

    Pilns vārds ("Ministru prezidente Evika Siliņa") neatbilst ``_SIGNER_RE``
    otrajai grupai un pazūd klusi — nav ne brīdinājuma, ne skaitītāja. Ja
    vestnesis.lv kādreiz pāriet uz pilnajiem vārdiem, ``extract_signers`` sāks
    atgriezt tukšu sarakstu, un tas izskatīsies pēc "aktam nav parakstītāju".
    """
    assert vestnesis.extract_signers("Ministru prezidente Evika Siliņa") == []
