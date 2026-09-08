"""`fetch_all_mentions()` nedrīkst saukt par panākumu dienu, kurā nekas nenonāca DB.

2026-08-01 izmeklēšana: 25 dienās **5 dienas ar 0 pieminējumiem** un vēl viena
ar 1, un neviena virsma par to nesūdzējās. Divi cēloņi, abi klusi:

**A. `timeline` stratēģija atnes, bet nesaglabā neko.** Kad X sīkfailu pūlā
veselo slotu skaits nokrīt zem sliekšņa, dispečers klusi pārslēdzas no `search`
uz `timeline`. Tās nav līdzvērtīgas: `search` meklē pieminējumus no JEBKURA
autora, bet `timeline` skenē izsekoto politiķu PAŠU taimlīnes un patur tvītus,
kas piemin citu izsekoto politiķi — un tie paši tvīti dažas minūtes agrāk jau ir
saglabāti ar `fetch_all_twitter()`. Tāpēc katrs trāpa `insert_document()`
`content_hash` dublikāta zarā un atgriež `None`.

Mērīts dzīvajā DB: 07-15 `fetched 262, stored 0`; 07-20 `fetched 258, stored 0`
— abi ar `errors: 0` un statusu **success**. Pārbaudīts arī, ka junction rindas
NEizdzīvo: tajās dienās `mention_target` savienojumu ir **0** (strādājošās
dienās 264–469), tātad zudums ir pilnīgs, ne daļējs.

**B. Wiki žurnāla ieraksts bija ar cieti iekodētu `status="success"`** — tāpēc
`wiki/log-ingest/` rādīja zaļu `X/Mentions` rindu arī tad, kad saglabāti 0.

Šie vārti tur abas robežas. Piezīme par tvērumu: `timeline` ir arī likumīga
skaidra izvēle (`X_MENTIONS_STRATEGY=timeline`), tāpēc tā pati par sevi nav
kļūda — bet tās segums ir šaurāks, un tam jābūt REDZAMAM, nevis jāizskatās
identiski parastam skrējienam.
"""

from __future__ import annotations

import pytest

from src import social


class _Row(dict):
    """sqlite3.Row aizstājējs — atbalsta ["handle"] piekļuvi."""


@pytest.fixture
def harness(monkeypatch):
    """Novirza visu ap `fetch_all_mentions` uz testa dubultniekiem."""
    calls = {"log_action": [], "ingest_entry": [], "inserted": 0}

    fake_db = type("DB", (), {
        "execute": lambda self, *a, **k: type("C", (), {
            "fetchall": lambda self: [_Row(handle="politikis", opponent_id=1)]
        })(),
        "close": lambda self: None,
    })()
    monkeypatch.setattr(social, "get_db", lambda *a, **k: fake_db)
    monkeypatch.setattr(social, "reset_pool", lambda *a, **k: None)
    monkeypatch.setattr(social, "embed_document", lambda *a, **k: [])
    monkeypatch.setattr(social, "insert_chunks", lambda *a, **k: None)

    def _log_action(action, **kw):
        calls["log_action"].append({"action": action, **kw})

    def _ingest_entry(**kw):
        calls["ingest_entry"].append(kw)

    monkeypatch.setattr(social, "log_action", _log_action)
    monkeypatch.setattr(social, "append_ingest_entry", _ingest_entry)
    return calls, monkeypatch


def _mention(i: int) -> dict:
    return {
        "id": str(i),
        "text": "Šis ir pietiekami garš pieminējuma teksts par politiku." + str(i),
        "created_at": "2026-08-01T10:00:00+00:00",
        "lang": "lv",
        "reply_count": 0, "retweet_count": 0, "favorite_count": 0,
        "source_url": f"https://x.com/kads/status/{i}",
        "opponent_id": 1,
        "mention_target_ids": [2],
    }


def _wire(monkeypatch, mentions, errors, strategy, insert_returns):
    async def _fake_fetch(handle_to_pid, *a, **k):
        social.x_mentions.last_run_strategy = strategy
        return mentions, errors

    monkeypatch.setattr(social, "fetch_mentions", _fake_fetch)
    monkeypatch.setattr(social, "insert_document", lambda **kw: insert_returns())


def test_fetched_many_stored_none_is_not_success(harness):
    """Tieši 07-15 / 07-20 gadījums: 262 atnesti, 0 saglabāti, statuss success."""
    calls, monkeypatch = harness
    _wire(monkeypatch, [_mention(i) for i in range(20)], 0, "timeline", lambda: None)

    social.fetch_all_mentions()

    entry = next(c for c in calls["log_action"] if c["action"] == "mentions_fetch")
    assert entry["status"] != "success", (
        "20 atnesti / 0 saglabāti nav panākums — tā ir klusa nomešana"
    )
    assert entry["status"] == "failure"
    assert "timeline" in str(entry.get("error_message", "")), (
        "ziņojumam jānosauc stratēģija — tā ir vienīgā pēda, pēc kuras atšķirt cēloni"
    )


def test_wiki_log_entry_is_not_hardcoded_success(harness):
    """`append_ingest_entry(status="success")` bija iekodēts cieti."""
    calls, monkeypatch = harness
    _wire(monkeypatch, [_mention(i) for i in range(20)], 0, "timeline", lambda: None)

    social.fetch_all_mentions()

    entry = calls["ingest_entry"][-1]
    assert entry["status"] == "failure", (
        "wiki žurnāls rādīja zaļu X/Mentions rindu arī pie 0 saglabātiem"
    )
    assert entry["documents_added"] == 0


def test_normal_search_run_still_reports_success(harness):
    """Regresijas vārti — strādājoša diena nedrīkst kļūt par kļūdu."""
    calls, monkeypatch = harness
    ids = iter(range(100, 200))
    _wire(monkeypatch, [_mention(i) for i in range(5)], 0, "search", lambda: next(ids))

    stored = social.fetch_all_mentions()

    assert len(stored) == 5
    entry = next(c for c in calls["log_action"] if c["action"] == "mentions_fetch")
    assert entry["status"] == "success"
    assert calls["ingest_entry"][-1]["status"] == "success"


def test_partial_query_errors_still_reported_as_partial(harness):
    """Daļējas kļūmes semantika saglabājas — tā nav šī labojuma daļa."""
    calls, monkeypatch = harness
    ids = iter(range(100, 200))
    _wire(monkeypatch, [_mention(i) for i in range(3)], 2, "search", lambda: next(ids))

    social.fetch_all_mentions()

    entry = next(c for c in calls["log_action"] if c["action"] == "mentions_fetch")
    assert entry["status"] == "partial"


def test_timeline_strategy_is_visible_even_when_it_stores(harness):
    """`timeline` segums ir šaurāks — tam jābūt redzamam, ne identiskam parastam.

    Šis ir otrs cēlonis: pārslēgšanās uz timeline notiek klusi, un pēc tam
    neviena virsma nerāda, ka tās dienas pieminējumu segums bija cits.
    """
    calls, monkeypatch = harness
    ids = iter(range(100, 200))
    _wire(monkeypatch, [_mention(i) for i in range(4)], 0, "timeline", lambda: next(ids))

    social.fetch_all_mentions()

    entry = calls["ingest_entry"][-1]
    note = f"{entry.get('extra') or ''} {entry.get('error') or ''}".lower()
    assert "timeline" in note, (
        "ievākšanas žurnālam jāatzīmē, ka skrējiens gāja pa šaurā seguma ceļu"
    )
