"""Citētais tvīts un atbildes vecāks tiek glabāti kā KONTEKSTS, ne kā runātāja vārdi.

Plāns `docs/plans/2026-11-10-citetais-tvits.md`. Divas kļūdas, ko šis tests ķer:

1. twikit `get_user_tweets(..., 'Replies')` sarunas blokā par tvītu atdod
   PIRMO elementu (svešu vecāku), bet politiķa paša atbildi ieliek
   `tweet.replies`. `fetch_user_replies` lasīja tikai pirmo: svešs tvīts tika
   glabāts kā dokuments, politiķa atbilde pazuda.
2. Citētais tvīts (`tweet.quote`) un atbildes vecāks netika glabāti vispār,
   tāpēc ekstraktors redzēja reakciju «bez redzama konteksta».

Konteksts dzīvo `documents.context_json`, nekad `content`: matcher, `support`
vārti un embeddingi to neredz. Publiski rāda tikai «Atbild @x» / «Citē @x» ar
saiti, svešo tekstu ne (operatora lēmums 2026-11-10).

Ceļš iet caur īsto ieejas punktu `src.social.fetch_twitter` ar viltotu twikit
pūlu (bez tīkla) uz izolētu DB.

Mutācija: ja konteksta tekstu pieliek `content` (`_store_tweets`),
`test_quoted_text_never_links_or_supports` un `test_relay_reply_*` krīt —
Ozoliņš dabū junction rindu.
"""
from __future__ import annotations

import json
from datetime import datetime

import pytest

import src.db as db_mod
# Import modules that bind `get_db` by name BEFORE the fixture patches
# src.db.get_db (tests/conftest.py § 5).
import src.analyze  # noqa: F401
import src.ingest  # noqa: F401
import src.render.politicians  # noqa: F401
import src.render.x  # noqa: F401
import src.tools  # noqa: F401
from tests.test_social import tmp_social_db  # noqa: F401  (pytest fixture)

# Account ids as seeded by tmp_social_db: 1 TestaPolitikis (pid 1),
# 2 OtrsPolitikis (pid 2), 3 LTVZinas (pid 3, relay). pid 4 Andris Ozoliņš has
# no account — he is only ever NAMED in someone else's text.
ACC_TESTA, ACC_OTRS, ACC_RELAY = 1, 2, 3

OZOLINS_TEXT = (
    "Andris Ozoliņš šodien paziņoja, ka atbalsta jauno nodokļu reformu un "
    "aicina koalīciju to pieņemt vēl šonedēļ."
)
OWN_QUOTE_TEXT = "Tas nav pareizi. Mēs šādu soli neatbalstīsim, kamēr nav ietekmes aprēķinu."


class FakeUser:
    def __init__(self, screen_name):
        self.screen_name = screen_name


class FakeTweet:
    """twikit Tweet stand-in with the conversation fields the scraper reads."""

    def __init__(self, id, author, text, *, in_reply_to=None, quote=None,
                 is_quote_status=False, replies=None, retweeted_tweet=None):
        self.id = id
        self.user = FakeUser(author)
        self.full_text = text
        self.text = text
        self.lang = "lv"
        self.created_at_datetime = datetime(2026, 11, 10, 12, 0, 0)
        self.reply_count = self.retweet_count = self.favorite_count = 0
        self.in_reply_to = in_reply_to
        self.quote = quote
        self.is_quote_status = is_quote_status or quote is not None
        self.replies = replies
        self.retweeted_tweet = retweeted_tweet


class _User:
    statuses_count = 10

    def __init__(self, handle):
        self.id = handle


def _install_pool(monkeypatch, timelines: dict[tuple[str, str], list]):
    """timelines: (handle, 'Tweets'|'Replies') -> list of top-level FakeTweet."""
    from src import x_scraper

    class Client:
        async def get_user_by_screen_name(self, handle):
            return _User(handle)

        async def get_user_tweets(self, user_id, tweet_type, count):
            return list(timelines.get((user_id, tweet_type), []))

    class Pool:
        slot_count = 1

        def get_next_slot(self):
            return 0

        def get_client(self, slot):
            return Client()

        def report_rate_limit(self, *a):
            pass

    async def fake_get_pool():
        return Pool()

    monkeypatch.setattr(x_scraper, "get_pool", fake_get_pool)


@pytest.fixture
def db(tmp_social_db, monkeypatch):  # noqa: F811
    from src import analyze
    path = db_mod.DB_PATH
    monkeypatch.setattr(analyze, "get_db", lambda: db_mod.get_db(path))
    return tmp_social_db


def _docs(conn) -> dict[str, dict]:
    rows = conn.execute(
        "SELECT id, content, source_url, context_json FROM documents").fetchall()
    return {r["source_url"]: dict(r) for r in rows}


def _links(conn, doc_id) -> set[tuple[int, str]]:
    return {(r[0], r[1]) for r in conn.execute(
        "SELECT politician_id, role FROM document_politicians WHERE document_id=?",
        (doc_id,))}


def _render_profile(conn, tmp_path, pid=1, name="Testa Politiķis",
                    slug="testa-politikis") -> str:
    from src.render.politicians import render_politicians
    from src.saeima.schema import init_saeima_tables
    from tests.test_profile_topic_deeplink import _env

    init_saeima_tables(db_mod.DB_PATH)
    out = tmp_path / "site" / "atmina"
    out.mkdir(parents=True, exist_ok=True)
    render_politicians(_env(), conn, out, [{
        "id": pid, "name": name, "slug": slug, "profile_kind": "politician",
        "role_label": "deputāts", "party": None, "x_handle": None,
    }], pid_to_syntheses={})
    return (out / "politiki" / f"{slug}.html").read_text(encoding="utf-8")


def _fetch(account_id):
    from src.social import fetch_twitter
    return fetch_twitter(account_id)


def test_quoted_text_never_links_or_supports(db, monkeypatch, tmp_path):
    from src.analyze import get_politician_documents, save_analysis
    from src.matcher import link_politicians_to_documents
    from src.render.x import _fetch_x_data

    quoted = FakeTweet("500", "SvesaisAutors", OZOLINS_TEXT)
    own = FakeTweet("501", "TestaPolitikis", OWN_QUOTE_TEXT, quote=quoted)
    _install_pool(monkeypatch, {("TestaPolitikis", "Tweets"): [own]})

    _fetch(ACC_TESTA)
    link_politicians_to_documents(days=1)

    docs = _docs(db)
    assert set(docs) == {"https://x.com/TestaPolitikis/status/501"}, \
        "only the speaker's own tweet is a document"
    doc = docs["https://x.com/TestaPolitikis/status/501"]
    assert doc["content"] == OWN_QUOTE_TEXT, "context must stay out of content"
    assert _links(db, doc["id"]) == {(1, "subject")}, \
        "a politician named only in the quoted tweet must not be linked"
    ctx = json.loads(doc["context_json"])
    assert [(c["kind"], c["author"], c["id"]) for c in ctx] == \
        [("quote", "SvesaisAutors", "500")]

    # Extractor sees the quoted text, labelled, separate from content.
    pending = get_politician_documents(1, days=1)
    assert len(pending) == 1
    assert "Citē @SvesaisAutors" in pending[0]["context"]
    assert OZOLINS_TEXT in pending[0]["context"]
    assert OZOLINS_TEXT not in pending[0]["content"]

    def claim(support):
        return {"document_id": doc["id"], "topic": "Nodokļi",
                "stance": "Neatbalsta nodokļu reformu, kamēr nav ietekmes aprēķinu.",
                "quote": None, "confidence": 0.6, "reasoning": "tests",
                "salience": 0.5, "stated_at": "2026-11-10", "support": [support]}

    # Mutation guard (passes before the fix too): support from the quoted
    # tweet is refused, support from the speaker's own words is stored.
    refused = save_analysis(pid=1, analysis_date="2026-11-10", sentiment=0.0,
                            topics=["Nodokļi"], quotes=[], brief="t",
                            confidence=0.6, claims=[claim("atbalsta jauno nodokļu reformu")])
    assert [f["type"] for f in refused["failures"]] == ["support_not_in_source"]
    stored = save_analysis(pid=1, analysis_date="2026-11-10", sentiment=0.0,
                           topics=["Nodokļi"], quotes=[], brief="t",
                           confidence=0.6, claims=[claim("Mēs šādu soli neatbalstīsim")])
    assert not stored["failures"] and len(stored["claim_ids"]) == 1

    # Checkers that judge the claim against its source see the same block.
    from src.analyze import get_claim_source
    source = get_claim_source(stored["claim_ids"][0])
    assert source["content"] == OWN_QUOTE_TEXT
    assert "Citē @SvesaisAutors" in source["context"]

    # Public page: a label with a link, never the foreign text.
    html = _render_profile(db, tmp_path)
    assert "Citē @SvesaisAutors" in html
    assert "https://x.com/SvesaisAutors/status/500" in html
    assert "atbalsta jauno nodokļu reformu" not in html

    post = [p for p in _fetch_x_data(db)["posts"] if p["source_url"].endswith("/501")]
    assert post and post[0]["ctx_links"] == [
        {"label": "Citē @SvesaisAutors", "url": "https://x.com/SvesaisAutors/status/500"}]
    assert "context_json" not in post[0], "raw context must not reach templates"

    from src.render.x import render_x
    from tests.test_profile_topic_deeplink import _env
    render_x(_env(), db, tmp_path)
    feed_html = (tmp_path / "x.html").read_text(encoding="utf-8")
    assert "Citē @SvesaisAutors" in feed_html
    assert "atbalsta jauno nodokļu reformu" not in feed_html

    log = json.loads(db.execute(
        "SELECT details FROM logs WHERE action='social_fetch' ORDER BY id DESC"
    ).fetchone()[0])
    assert log["ctx_quote"] == 1 and log["ctx_reply"] == 0 and log["ctx_missing"] == 0


def test_reply_block_stores_own_reply_with_parent_and_root(db, monkeypatch, tmp_path):
    from src.analyze import get_politician_documents

    root = FakeTweet("600", "Sakne", "Sarunas sākums: vai pašvaldību vēlēšanas jāpārceļ uz rudeni?")
    parent = FakeTweet("601", "Vecaks", "@Sakne Nē, tas būtu pret Satversmi, un Ozoliņš to zina.",
                       in_reply_to="600")
    own = FakeTweet("602", "TestaPolitikis",
                    "@Vecaks @Sakne Piekrītu, termiņu mainīt nedrīkst, un mēs to neatbalstīsim.",
                    in_reply_to="601")
    root.replies = [parent, own]
    _install_pool(monkeypatch, {("TestaPolitikis", "Replies"): [root]})

    _fetch(ACC_TESTA)

    docs = _docs(db)
    assert set(docs) == {"https://x.com/TestaPolitikis/status/602"}, \
        "foreign parents are context only, never their own documents"
    doc = docs["https://x.com/TestaPolitikis/status/602"]
    assert _links(db, doc["id"]) == {(1, "subject")}
    ctx = json.loads(doc["context_json"])
    assert [(c["kind"], c["author"], c["id"]) for c in ctx] == \
        [("reply", "Vecaks", "601"), ("reply_root", "Sakne", "600")]

    pending = get_politician_documents(1, days=1)
    assert "Atbild @Vecaks" in pending[0]["context"]

    html = _render_profile(db, tmp_path)
    assert "Atbild @Vecaks" in html
    assert "https://x.com/Vecaks/status/601" in html
    assert "tas būtu pret Satversmi" not in html

    log = json.loads(db.execute(
        "SELECT details FROM logs WHERE action='social_fetch' ORDER BY id DESC"
    ).fetchone()[0])
    assert log["ctx_reply"] == 1 and log["foreign_parents_skipped"] == 2
    assert log["replies"] == 1


def test_self_thread_stores_each_own_tweet_once(db, monkeypatch, tmp_path):
    first_text = "Pirmā daļa: šodien Saeimā iesniedzām grozījumus par mājokļu pabalstiem."
    first = FakeTweet("700", "TestaPolitikis", first_text)
    second = FakeTweet("701", "TestaPolitikis",
                       "Otrā daļa: grozījumi paredz pabalstu indeksāciju katru gadu janvārī.",
                       in_reply_to="700")
    block_head = FakeTweet("700", "TestaPolitikis", first_text, replies=[second])
    _install_pool(monkeypatch, {
        ("TestaPolitikis", "Tweets"): [first],
        ("TestaPolitikis", "Replies"): [block_head],
    })

    _fetch(ACC_TESTA)

    rows = db.execute(
        "SELECT source_url, COUNT(*) FROM documents GROUP BY source_url").fetchall()
    assert {r[0]: r[1] for r in rows} == {
        "https://x.com/TestaPolitikis/status/700": 1,
        "https://x.com/TestaPolitikis/status/701": 1,
    }
    # An own parent is not context: no entry, no public «Atbild @self».
    assert _docs(db)["https://x.com/TestaPolitikis/status/701"]["context_json"] is None
    assert "Atbild @TestaPolitikis" not in _render_profile(db, tmp_path)


def test_same_reply_text_to_different_parents_stays_separate_documents(db, monkeypatch):
    """content_hash is UNIQUE and used to drop the second identical text
    silently. Two accounts, or one account to two parents, are separate posts."""
    text = "@Vecaks Pilnīgi piekrītu, šis jautājums ir jārisina tūlīt un bez kavēšanās!"
    p1 = FakeTweet("801", "Vecaks", "@x Pirmais vecāka tvīts par budžeta grozījumiem.")
    p2 = FakeTweet("802", "Vecaks", "@x Otrais vecāka tvīts par pensiju indeksāciju.")
    p3 = FakeTweet("803", "Vecaks", "@x Trešais vecāka tvīts par skolu tīklu.")
    p1.replies = [FakeTweet("811", "TestaPolitikis", text, in_reply_to="801")]
    p2.replies = [FakeTweet("812", "OtrsPolitikis", text, in_reply_to="802")]
    p3.replies = [FakeTweet("813", "TestaPolitikis", text, in_reply_to="803")]
    _install_pool(monkeypatch, {
        ("TestaPolitikis", "Replies"): [p1, p3],
        ("OtrsPolitikis", "Replies"): [p2],
    })

    _fetch(ACC_TESTA)
    _fetch(ACC_OTRS)
    _fetch(ACC_OTRS)  # a routine re-read must not add rows
    _fetch(ACC_TESTA)

    docs = _docs(db)
    expected = {"https://x.com/TestaPolitikis/status/811": ("801", 1),
                "https://x.com/OtrsPolitikis/status/812": ("802", 2),
                "https://x.com/TestaPolitikis/status/813": ("803", 1)}
    assert set(docs) == set(expected)
    for url, (parent_id, pid) in expected.items():
        assert json.loads(docs[url]["context_json"])[0]["id"] == parent_id, url
        assert _links(db, docs[url]["id"]) == {(pid, "subject")}, url


def test_relay_reply_stores_own_reply_only_and_context_is_not_scanned(db, monkeypatch):
    from src.matcher import link_politicians_to_documents

    parent = FakeTweet("900", "Skatitajs", "@LTVZinas " + OZOLINS_TEXT)
    own = FakeTweet("901", "LTVZinas",
                    "@Skatitajs Paldies par jautājumu, raidījumā par to runāsim plašāk šovakar.",
                    in_reply_to="900")
    parent.replies = [own]
    _install_pool(monkeypatch, {("LTVZinas", "Replies"): [parent]})

    _fetch(ACC_RELAY)
    link_politicians_to_documents(days=1)

    docs = _docs(db)
    assert set(docs) == {"https://x.com/LTVZinas/status/901"}
    doc = docs["https://x.com/LTVZinas/status/901"]
    assert _links(db, doc["id"]) == set(), \
        "relay: no fetch-owner link, and the parent's names are not scanned"
    assert json.loads(doc["context_json"])[0]["author"] == "Skatitajs"


def test_context_fill_on_refetch_keeps_review_stamp(db, monkeypatch):
    """A tweet first stored without context (e.g. via the Tweets timeline)
    gets its context on the next Replies read; reviewed_at is not touched."""
    text = "@Vecaks Šis priekšlikums ir pretrunā ar budžeta likumu un mēs to neatbalstīsim."
    bare = FakeTweet("951", "TestaPolitikis", text, in_reply_to="950")
    _install_pool(monkeypatch, {("TestaPolitikis", "Tweets"): [bare]})
    _fetch(ACC_TESTA)
    db.execute("UPDATE documents SET reviewed_at='2026-11-10 15:00:00'")
    db.commit()

    parent = FakeTweet("950", "Vecaks", "Budžetā paredzēts jauns nodoklis mājsaimniecībām.")
    parent.replies = [FakeTweet("951", "TestaPolitikis", text, in_reply_to="950")]
    _install_pool(monkeypatch, {("TestaPolitikis", "Replies"): [parent]})
    _fetch(ACC_TESTA)

    row = db.execute("SELECT COUNT(*), MAX(context_json), MAX(reviewed_at) FROM documents").fetchone()
    assert row[0] == 1
    assert json.loads(row[1])[0]["id"] == "950"
    assert row[2] == "2026-11-10 15:00:00"


def test_retweet_with_quote_flag_is_not_counted_missing(db, monkeypatch):
    original = FakeTweet("990", "Autors", "Oriģināls ar citātu par aizsardzības budžetu un iepirkumiem.")
    rt = FakeTweet("991", "TestaPolitikis", "RT @Autors: Oriģināls ar citātu par aizsardzības…",
                   is_quote_status=True, retweeted_tweet=original)
    missing = FakeTweet("992", "TestaPolitikis", "Paskatieties, ko viņi raksta — tas ir absurds un nepieņemami.",
                        is_quote_status=True)
    _install_pool(monkeypatch, {("TestaPolitikis", "Tweets"): [rt, missing]})

    _fetch(ACC_TESTA)

    log = json.loads(db.execute(
        "SELECT details FROM logs WHERE action='social_fetch' ORDER BY id DESC"
    ).fetchone()[0])
    assert log["ctx_missing"] == 1, "only the non-retweet quote without payload counts"


def test_daily_batch_path_stores_own_reply_and_logs_counts(db, monkeypatch):
    """The routine runs fetch_all_twitter -> fetch_all_x_accounts, not fetch_twitter."""
    from src.social import fetch_all_twitter

    db.execute("UPDATE social_accounts SET active = 0 WHERE id != ?", (ACC_TESTA,))
    db.commit()
    parent = FakeTweet("1001", "Vecaks", "Vai budžetā paliks nauda reģionu ceļiem nākamgad?")
    parent.replies = [FakeTweet("1002", "TestaPolitikis",
                                "@Vecaks Paliks, mēs to iestrādājām budžeta grozījumos šonedēļ.",
                                in_reply_to="1001")]
    _install_pool(monkeypatch, {("TestaPolitikis", "Replies"): [parent]})

    fetch_all_twitter()

    docs = _docs(db)
    assert set(docs) == {"https://x.com/TestaPolitikis/status/1002"}
    assert json.loads(docs["https://x.com/TestaPolitikis/status/1002"]["context_json"])[0]["id"] == "1001"
    log = json.loads(db.execute(
        "SELECT details FROM logs WHERE action='social_fetch_all' ORDER BY id DESC"
    ).fetchone()[0])
    assert log["ctx_reply"] == 1 and log["foreign_parents_skipped"] == 1
    assert log["replies_before_floor"] == 0


def test_replies_before_floor_date_are_not_stored(db, monkeypatch):
    """Operator floor (2026-11-10): the replies path stores no own reply whose
    LV date is before 2026-11-03 — the fix would otherwise pull in a backlog of
    old replies. The cut is the LV calendar day, not UTC."""
    from datetime import timezone

    def reply(tid, parent_id, when_utc):
        parent = FakeTweet(parent_id, "Vecaks", "Jautājums par skolu tīkla reformu reģionos.")
        own = FakeTweet(tid, "TestaPolitikis",
                        f"@Vecaks Reforma reģionos jāpārskata, un mēs to prasīsim komisijā {tid}.",
                        in_reply_to=parent_id)
        own.created_at_datetime = when_utc
        parent.replies = [own]
        return parent

    utc = timezone.utc
    _install_pool(monkeypatch, {("TestaPolitikis", "Replies"): [
        reply("2001", "2000", datetime(2026, 11, 2, 21, 30, tzinfo=utc)),  # 23:30 LV, 11-02
        reply("2003", "2002", datetime(2026, 11, 2, 22, 30, tzinfo=utc)),  # 00:30 LV, 11-03
    ]})

    _fetch(ACC_TESTA)

    assert set(_docs(db)) == {"https://x.com/TestaPolitikis/status/2003"}
    log = json.loads(db.execute(
        "SELECT details FROM logs WHERE action='social_fetch' ORDER BY id DESC"
    ).fetchone()[0])
    assert log["replies_before_floor"] == 1 and log["replies"] == 1
