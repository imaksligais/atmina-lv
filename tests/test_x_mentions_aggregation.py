"""``src/x_mentions.py`` — normalizācija, agregācija un kļūdu uzskaite.

**Saucēja korekcija pret 2026-09-05 auditu.** Audita § 3.1 (b) sauc
``src/x_mentions.py`` (472 rindas) par "lielāko nesegto moduli", jo tā simbolu
skenējums atrada tikai ``_normalize_mention`` vienā test failā. Skaitīts pa
failiem, tas nav taisnība: ``tests/test_x_mentions.py`` jau tur 16 testus, kas
sedz ``fetch_mentions``, ``_resolve_strategy`` (netieši), abas stratēģijas un
veselības zondes fallback, un ``tests/test_transaction_key_repair.py`` sedz
``_search_probe_with_key_repair``. **Segtas bija 6 no 8 definīcijām.**

Šis fails aizver atlikušo — un tikai to, kas TIEŠĀM nebija pinēts:

| Definīcija | Pirms | Šeit |
|---|---|---|
| ``_normalize_mention`` | ✅ 3 testi | + ``created_at`` formas, ``user=None``, ``None`` skaitītāji |
| ``_resolve_handle`` | ❌ | ✅ kļūdas zars |
| ``_fetch_mentions_via_timeline`` | ✅ laimīgais ceļš | + kļūdu uzskaite, 429 rotācija, slota izsīkums |
| ``_fetch_mentions_via_search`` | ✅ pakošana | + noklusējuma pakas izmērs, ``limit`` pārkartošana |
| ``_resolve_strategy`` | netieši | ✅ tieši (reģistrjutība, precedence) |
| ``_probe_search_slot_health`` | netieši | ✅ tieši (neinicializēts slots) |
| ``_search_probe_with_key_repair`` | ✅ citā failā | — |
| ``fetch_mentions`` | ✅ 10 testu | — |

Kopā pēc šī faila: **8 no 8 definīcijām** ir tiešs vai netiešs pins.

**Tīkls: nekad.** Pūls un klienti ir fake objekti; ``asyncio.sleep`` nekad
netiek gaidīts, jo visi testi padod ``delay=0``.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from twikit.errors import TooManyRequests, TwitterException

from src import x_mentions


class _Tweet:
    """Vienkāršs tvīta stubs.

    Apzināti NE ``MagicMock``: ``_normalize_mention`` lieto
    ``getattr(tweet, "lang", None)``, un ``MagicMock`` atgriež jaunu Mock
    KATRAM atribūtam, tāpēc "trūkstošs lauks" ar mock-u nav pārbaudāms.
    """

    def __init__(self, tid, screen_name="autors", name="Autors", text="",
                 full_text=None, created=None, user=True, **extra):
        self.id = tid
        self.text = text
        self.full_text = full_text if full_text is not None else text
        self.created_at_datetime = created
        if user:
            self.user = MagicMock()
            self.user.screen_name = screen_name
            self.user.name = name
        else:
            self.user = None
        for k, v in extra.items():
            setattr(self, k, v)


def _pool(client, slot_count=1):
    pool = MagicMock()
    pool.slot_count = slot_count
    pool.get_next_slot.return_value = 0
    pool.get_client.return_value = client
    return pool


@pytest.fixture(autouse=True)
def _no_ambient_strategy(monkeypatch):
    monkeypatch.delenv("X_MENTIONS_STRATEGY", raising=False)


# --- _normalize_mention: lauku formas -------------------------------------


def test_normalize_serialises_a_datetime_created_at_as_isoformat():
    tweet = _Tweet("1", text="@beta sveiki",
                   created=datetime(2026, 9, 4, 18, 30, 5))
    out = x_mentions._normalize_mention(tweet, {"beta": 2})
    assert out["created_at"] == "2026-09-04T18:30:05"


def test_normalize_stringifies_a_non_datetime_created_at():
    """Raksturojums: twikit dažkārt dod virkni; tā tiek nodota tālāk kā ir."""
    tweet = _Tweet("1", text="@beta sveiki", created="Fri Sep 04 18:30:05 +0000 2026")
    out = x_mentions._normalize_mention(tweet, {"beta": 2})
    assert out["created_at"] == "Fri Sep 04 18:30:05 +0000 2026"


def test_normalize_created_at_none_stays_none():
    out = x_mentions._normalize_mention(_Tweet("1", text="@beta"), {"beta": 2})
    assert out["created_at"] is None


def test_normalize_falls_back_from_full_text_to_text():
    tweet = _Tweet("1", text="@beta īsais", full_text=None)
    tweet.full_text = None
    assert x_mentions._normalize_mention(tweet, {"beta": 2})["text"] == "@beta īsais"


def test_normalize_handles_a_tweet_without_a_user_object():
    """``tweet.user is None`` → ``unknown`` handle, un source_url to nes iekšā.

    Raksturojums, ne apstiprinājums: iegūtais URL
    ``https://x.com/unknown/status/9`` ir 404. Ja tāds dokuments nonāktu DB,
    tā provenance būtu nederīga (Datu līgums #2 gars — bez izsekojama URL nav
    provenances), tāpēc šeit ir pinēts tieši tas, ka forma ir atpazīstama.
    """
    out = x_mentions._normalize_mention(_Tweet("9", text="@beta", user=False),
                                        {"beta": 2})
    assert out["mentioner_handle"] == "unknown"
    assert out["mentioner_name"] == "unknown"
    assert out["source_url"] == "https://x.com/unknown/status/9"
    assert out["opponent_id"] is None


def test_normalize_coerces_missing_or_none_engagement_counts_to_zero():
    tweet = _Tweet("1", text="@beta", reply_count=None, retweet_count=None)
    out = x_mentions._normalize_mention(tweet, {"beta": 2})
    assert out["reply_count"] == out["retweet_count"] == out["favorite_count"] == 0
    assert out["lang"] is None            # atribūta nav vispār


def test_normalize_matches_handles_case_insensitively_but_not_as_substrings_of_words():
    """Raksturojums: sakritība ir ``@handle`` apakšvirkne, BEZ vārda robežas.

    ``@beta`` tāpēc trāpa arī ``@betatesteris``. Tā ir tā pati T1 klase, ko
    ``src/matcher.py`` risināja ar vārda robežām 2026-07-27, bet
    ``_normalize_mention`` to NEDARA. Pinēts kā raksturojums — labojums pieder
    ``src/x_mentions.py``.
    """
    out = x_mentions._normalize_mention(
        _Tweet("1", text="Sveiki @BetaTesteris"), {"beta": 2},
    )
    assert out["mention_target_ids"] == [2]


# --- _resolve_strategy -----------------------------------------------------


@pytest.mark.parametrize("given,expect", [
    ("search", "search"), ("SEARCH", "search"),
    ("Timeline", "timeline"), ("timeline", "timeline"),
])
def test_resolve_strategy_lowercases_the_explicit_kwarg(given, expect):
    assert x_mentions._resolve_strategy(given) == expect


def test_resolve_strategy_reads_the_env_var_case_insensitively(monkeypatch):
    monkeypatch.setenv("X_MENTIONS_STRATEGY", "TIMELINE")
    assert x_mentions._resolve_strategy(None) == "timeline"


def test_resolve_strategy_defaults_to_search():
    assert x_mentions._resolve_strategy(None) == "search"


def test_resolve_strategy_kwarg_beats_env(monkeypatch):
    monkeypatch.setenv("X_MENTIONS_STRATEGY", "timeline")
    assert x_mentions._resolve_strategy("search") == "search"


# --- _resolve_handle -------------------------------------------------------


def test_resolve_handle_returns_none_and_logs_on_failure(caplog):
    client = MagicMock()
    client.get_user_by_screen_name = AsyncMock(side_effect=RuntimeError("404"))
    with caplog.at_level("WARNING"):
        assert asyncio.run(x_mentions._resolve_handle(client, "beta")) is None
    assert "handle resolution failed for @beta" in caplog.text


# --- timeline: kļūdu uzskaite ---------------------------------------------


def test_timeline_counts_one_error_per_unresolvable_handle(monkeypatch):
    """Neatrisināts handle → ``errors += 1`` UN handle vairs netiek skenēts.

    Bez šī skaitītāja diena, kurā X nomaina ``UserByScreenName``, izskatītos
    kā "0 pieminējumu", nevis kā salūzis skrāpis (T12 / eskalācijas likums 5).
    """
    client = MagicMock()
    client.get_user_by_screen_name = AsyncMock(side_effect=[
        RuntimeError("nav"), MagicMock(id="UID_B"),
    ])
    client.get_user_tweets = AsyncMock(return_value=[])
    monkeypatch.setattr(x_mentions, "get_pool", AsyncMock(return_value=_pool(client)))

    mentions, errors = asyncio.run(x_mentions._fetch_mentions_via_timeline(
        {"alpha": 1, "beta": 2}, delay=0,
    ))
    assert mentions == []
    assert errors == 1
    assert client.get_user_tweets.await_count == 1     # tikai atrisinātais


def test_timeline_counts_an_error_when_every_slot_fails_for_one_handle(monkeypatch):
    client = MagicMock()
    client.get_user_by_screen_name = AsyncMock(return_value=MagicMock(id="UID"))
    client.get_user_tweets = AsyncMock(side_effect=TwitterException("403"))
    monkeypatch.setattr(x_mentions, "get_pool", AsyncMock(return_value=_pool(client)))

    mentions, errors = asyncio.run(
        x_mentions._fetch_mentions_via_timeline({"alpha": 1}, delay=0)
    )
    assert (mentions, errors) == ([], 1)


def test_timeline_rotates_to_the_next_slot_after_a_rate_limit(monkeypatch):
    """429 vienā slotā → ziņo pūlam un mēģina nākamo; rezultāts nav zaudēts."""
    ok_tweet = _Tweet("10", screen_name="alpha", text="@beta sveiki")
    limited = MagicMock()
    limited.get_user_by_screen_name = AsyncMock(return_value=MagicMock(id="UID"))
    limited.get_user_tweets = AsyncMock(
        side_effect=TooManyRequests("429", headers={"x-rate-limit-reset": "1780000000"})
    )
    healthy = MagicMock()
    healthy.get_user_by_screen_name = AsyncMock(return_value=MagicMock(id="UID"))
    healthy.get_user_tweets = AsyncMock(return_value=[ok_tweet])

    clients = {0: limited, 1: healthy}
    cursor = {"i": 0}
    pool = MagicMock()
    pool.slot_count = 2
    pool.get_next_slot = lambda: (cursor.update(i=cursor["i"] + 1) or cursor["i"] - 1) % 2
    pool.get_client = lambda slot: clients[slot]
    monkeypatch.setattr(x_mentions, "get_pool", AsyncMock(return_value=pool))

    mentions, errors = asyncio.run(x_mentions._fetch_mentions_via_timeline(
        {"alpha": 1, "beta": 2}, delay=0,
    ))
    assert errors == 0
    assert [m["id"] for m in mentions] == ["10"]
    # Divi handli → slots 0 tiek izmēģināts un ziņots DIVREIZ. Pūls netiek
    # informēts "šis slots vairs nav rindā"; rotācija to piedāvā katram
    # nākamajam handlim no jauna, un cena ir viens lieks 429 uz handli.
    assert pool.report_rate_limit.call_count == 2
    for call in pool.report_rate_limit.call_args_list:
        slot, reset = call[0]
        assert slot == 0
        assert reset == 1780000000 + 2    # +2 s drošības rezerve


def test_timeline_counts_an_error_when_the_pool_is_exhausted(monkeypatch):
    """``get_next_slot`` met ``RuntimeError`` → uzskaitīts, ne norīts."""
    pool = MagicMock()
    pool.slot_count = 1
    pool.get_next_slot.side_effect = RuntimeError("all slots rate-limited")
    monkeypatch.setattr(x_mentions, "get_pool", AsyncMock(return_value=pool))

    mentions, errors = asyncio.run(
        x_mentions._fetch_mentions_via_timeline({"alpha": 1}, delay=0)
    )
    assert mentions == []
    assert errors >= 1


# --- search: pakošana un limitu pārkartošana -------------------------------


def test_search_default_batch_size_is_eight_handles_per_query(monkeypatch):
    queries: list[str] = []

    async def capture(query, product, count):
        queries.append(query)
        return []

    client = MagicMock()
    client.search_tweet = AsyncMock(side_effect=capture)
    monkeypatch.setattr(x_mentions, "get_pool", AsyncMock(return_value=_pool(client)))

    handles = {f"h{i}": i for i in range(11)}
    asyncio.run(x_mentions.fetch_mentions(handles, delay=0, strategy="search"))

    assert x_mentions.SEARCH_HANDLES_PER_BATCH == 8
    assert len(queries) == 2                        # 8 + 3
    assert queries[0].count(" OR ") == 7
    assert queries[1].count(" OR ") == 2
    assert all(q.endswith(" -filter:retweets") for q in queries)


def test_search_remaps_the_legacy_default_limit_of_20_to_50(monkeypatch):
    """Slazds, kas ir viegli palaižams garām lasot ``fetch_mentions``.

    ``limit=20`` ir ``fetch_mentions`` paraksta noklusējums (mantojums no
    timeline stratēģijas), un search zars to KLUSI pārraksta uz
    ``SEARCH_COUNT_PER_QUERY``. Tas nozīmē: EKSPLICĪTS ``limit=20`` arī kļūst
    par 50 — 20 tvītus uz vaicājumu ar šo API dabūt nevar.
    """
    counts: list[int] = []

    async def capture(query, product, count):
        counts.append(count)
        return []

    client = MagicMock()
    client.search_tweet = AsyncMock(side_effect=capture)
    monkeypatch.setattr(x_mentions, "get_pool", AsyncMock(return_value=_pool(client)))

    asyncio.run(x_mentions.fetch_mentions({"a": 1}, limit=20, delay=0, strategy="search"))
    asyncio.run(x_mentions.fetch_mentions({"a": 1}, limit=21, delay=0, strategy="search"))
    asyncio.run(x_mentions.fetch_mentions({"a": 1}, limit=500, delay=0, strategy="search"))

    assert counts == [50, 21, 50]       # 20→50 pārkartots; 500→50 nogriezts
    assert x_mentions.SEARCH_COUNT_PER_QUERY == 50


def test_search_counts_an_error_when_every_slot_fails_a_batch(monkeypatch):
    client = MagicMock()
    client.search_tweet = AsyncMock(side_effect=TwitterException("404"))
    monkeypatch.setattr(x_mentions, "get_pool", AsyncMock(return_value=_pool(client)))

    mentions, errors = asyncio.run(
        x_mentions._fetch_mentions_via_search({"a": 1}, delay=0)
    )
    assert (mentions, errors) == ([], 1)


# --- _probe_search_slot_health --------------------------------------------


def test_probe_counts_only_slots_that_answer_search_tweet(monkeypatch):
    clients = {}
    for slot in range(4):
        c = MagicMock()
        c.search_tweet = AsyncMock(
            return_value=[] if slot % 2 == 0 else None,
            side_effect=None if slot % 2 == 0 else RuntimeError("404"),
        )
        clients[slot] = c
    pool = MagicMock()
    pool.slot_count = 4
    pool.get_client = lambda slot: clients[slot]
    monkeypatch.setattr(x_mentions, "get_pool", AsyncMock(return_value=pool))

    assert asyncio.run(x_mentions._probe_search_slot_health()) == 2


def test_probe_treats_an_uninitialized_slot_as_unhealthy(monkeypatch):
    """``get_client`` met ``RuntimeError``, ja slotam nav ielādētu sīkdatņu."""
    healthy = MagicMock()
    healthy.search_tweet = AsyncMock(return_value=[])

    def get_client(slot):
        if slot == 0:
            raise RuntimeError("slot 0 uninitialized")
        return healthy

    pool = MagicMock()
    pool.slot_count = 3
    pool.get_client = get_client
    monkeypatch.setattr(x_mentions, "get_pool", AsyncMock(return_value=pool))

    assert asyncio.run(x_mentions._probe_search_slot_health()) == 2


def test_search_guardrail_threshold_and_probe_query_are_pinned():
    """Sliekšņa maiņa ir operatora lēmums, ne kosmētika (5 slotu pūls, 4 vārti)."""
    assert x_mentions.SEARCH_MIN_HEALTHY_SLOTS == 4
    assert x_mentions.SEARCH_PROBE_QUERY == "Latvija"
    assert x_mentions.SEARCH_PROBE_TIMEOUT_S == 5.0
