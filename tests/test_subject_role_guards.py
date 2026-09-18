"""Subject-role guards — operatora verdikti 36 + 38 (2026-09-07).

Two write-path guards, one shared owner (``src/roles.py``):

* **36** — a RELAY MEDIA slot (``relationship_type='organization'`` AND a
  ``feed_type='relay'`` social account: LETA, LTV Ziņas, NRA, TV3, Panorāma,
  De Facto, IR, Krustpunktā, Saeimas ziņas, KNL, LLatviesiem) never receives
  ``role='subject'``. Its name in a text is an agency credit line, not a
  speech act, and the resulting junction closed 934 unreviewed web documents
  into a queue nobody could ever empty (`backlog/matcher.md` § «`subject`»
  lomai vajag runātāja pierādījumu).

* **38** — a bare retweet of an OFFICE VOICE account (@Brivibas36, the
  Cabinet's communications handle) never confers ``subject`` on the
  retweeter. The retweeted text is a third-person chronicle written by the
  office, not the politician speaking (`backlog/matcher.md` § 2026-08-26 (b)).

The third test class is the counter-guard for verdict 37, which asked for the
same treatment for NBS (pid=204). NBS is ``organization`` but
``feed_type='first_party'`` and it produced 22 position claims in August 2026
alone — gating it would close a live extraction channel, so the predicate must
stay the narrow AND that ``src/scope.py`` already documents.
"""

import sqlite3

import pytest

import src.db as db_mod


@pytest.fixture
def tmp_roles_db(tmp_path, monkeypatch):
    """Isolated DB whose get_db is redirected in db, matcher and social.

    Mirrors tests/test_social.py — insert_document's frozen ``db_path=DB_PATH``
    default is bound at definition time, so patching DB_PATH alone is not
    enough.
    """
    db_path = str(tmp_path / "atmina_roles.db")
    db_mod.init_db(db_path)

    orig_get_db = db_mod.get_db

    def _redirected_get_db(db_path_arg: str = db_path) -> sqlite3.Connection:
        return orig_get_db(db_path)

    monkeypatch.setattr(db_mod, "get_db", _redirected_get_db)
    monkeypatch.setattr(db_mod, "DB_PATH", db_path)

    import src.matcher as matcher_mod
    import src.social as social_mod
    monkeypatch.setattr(matcher_mod, "get_db", _redirected_get_db)
    monkeypatch.setattr(social_mod, "get_db", _redirected_get_db)
    matcher_mod._clear_politician_cache()
    monkeypatch.setattr(social_mod, "embed_document", lambda text: [])
    monkeypatch.setattr(social_mod, "insert_chunks", lambda *a, **kw: None)

    conn = orig_get_db(db_path)
    # 1 — ordinary tracked politician with an own first_party X account.
    conn.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms, relationship_type) "
        "VALUES (1, 'Aivars Zvaigznītis', ?, 'tracked')",
        ('["Aivars Zvaigznītis", "Zvaigznītis"]',),
    )
    conn.execute(
        "INSERT INTO social_accounts (opponent_id, platform, handle, active, feed_type) "
        "VALUES (1, 'twitter', 'AivarsZ', 1, 'first_party')"
    )
    # 2 — relay MEDIA slot (organization + relay account) = the LETA class.
    conn.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms, relationship_type) "
        "VALUES (2, 'LETA', ?, 'organization')",
        ('["LETA"]',),
    )
    conn.execute(
        "INSERT INTO social_accounts (opponent_id, platform, handle, active, feed_type) "
        "VALUES (2, 'twitter', 'letanewslv', 1, 'relay')"
    )
    # 3 — institution that is an organization but NOT a relay (the NBS class).
    conn.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms, relationship_type) "
        "VALUES (3, 'Latvijas armija (NBS)', ?, 'organization')",
        ('["NBS", "Nacionālie bruņotie spēki"]',),
    )
    conn.commit()
    conn.close()

    yield db_path

    matcher_mod._clear_politician_cache()


def _roles(db_path: str, doc_id: int) -> dict[int, set[str]]:
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT politician_id, role FROM document_politicians WHERE document_id = ?",
        (doc_id,),
    ).fetchall()
    conn.close()
    out: dict[int, set[str]] = {}
    for pid, role in rows:
        out.setdefault(pid, set()).add(role)
    return out


class TestRelayMediaSlotNeverSubject:
    """Verdikts 36 — the agency credit-line class."""

    def test_link_politicians_gives_relay_media_only_mentioned(self, tmp_roles_db):
        from src.matcher import link_politicians_to_documents

        doc_id = db_mod.insert_document(
            content=(
                "Sestdien Jelgavas novadā notika satiksmes negadījums, kurā "
                "cietis viens cilvēks, aģentūrai LETA pastāstīja Valsts "
                "policijas pārstāve."
            ),
            source_id=None,
            platform="web",
            source_url="https://example.lv/negadijums-jelgava",
        )
        assert doc_id is not None
        link_politicians_to_documents(days=2)
        assert _roles(tmp_roles_db, doc_id) == {2: {"mentioned"}}

    def test_insert_document_demotes_a_relay_media_subject_link(self, tmp_roles_db):
        doc_id = db_mod.insert_document(
            content="LETA ziņo par vakardienas notikumiem Saeimā.",
            source_id=None,
            platform="web",
            source_url="https://example.lv/leta-zino",
            politician_links=[(2, "subject")],
        )
        assert _roles(tmp_roles_db, doc_id) == {2: {"mentioned"}}


class TestNonRelayInstitutionKeepsSubject:
    """Verdikts 37 counter-guard — NBS-class institutions stay extractable."""

    def test_organization_without_relay_account_still_gets_subject(self, tmp_roles_db):
        from src.matcher import link_politicians_to_documents

        doc_id = db_mod.insert_document(
            content=(
                "NBS komandieris skaidro, ka mācības turpināsies visu nedēļu "
                "un iedzīvotājiem nav jāsatraucas par troksni."
            ),
            source_id=None,
            platform="web",
            source_url="https://example.lv/nbs-macibas",
        )
        assert doc_id is not None
        link_politicians_to_documents(days=2)
        assert _roles(tmp_roles_db, doc_id) == {3: {"subject"}}


class TestOfficeVoiceRetweetNeverSubject:
    """Verdikts 38 — @Brivibas36 chronicles are the office speaking."""

    def _rt_text(self) -> str:
        return (
            "RT @Brivibas36: Ministru prezidents Aivars Zvaigznītis tikās ar "
            "Igaunijas premjerministru, lai pārrunātu drošības situāciju "
            "reģionā un atbalstu Ukrainai."
        )

    def test_store_tweets_gives_retweeter_only_mentioned(self, tmp_roles_db):
        from src.social import _store_tweets

        _store_tweets(
            [{
                "text": self._rt_text(),
                "source_url": "https://x.com/AivarsZ/status/2092676682142433653",
                "lang": "lv",
                "created_at": "2026-08-26 12:00:00",
            }],
            opponent_id=1,
        )
        conn = sqlite3.connect(tmp_roles_db)
        doc_id = conn.execute("SELECT id FROM documents").fetchone()[0]
        conn.close()
        assert _roles(tmp_roles_db, doc_id) == {1: {"mentioned"}}

    def test_own_tweet_is_still_subject(self, tmp_roles_db):
        from src.social import _store_tweets

        _store_tweets(
            [{
                "text": (
                    "Šodien Saeimā runāju par budžeta prioritātēm un "
                    "aizsardzības finansējuma palielināšanu nākamgad."
                ),
                "source_url": "https://x.com/AivarsZ/status/2092676682142433999",
                "lang": "lv",
                "created_at": "2026-08-26 13:00:00",
            }],
            opponent_id=1,
        )
        conn = sqlite3.connect(tmp_roles_db)
        doc_id = conn.execute("SELECT id FROM documents").fetchone()[0]
        conn.close()
        assert _roles(tmp_roles_db, doc_id) == {1: {"subject"}}

    def test_link_politicians_also_demotes_an_office_voice_retweet(self, tmp_roles_db):
        from src.matcher import link_politicians_to_documents

        doc_id = db_mod.insert_document(
            content=self._rt_text(),
            source_id=None,
            platform="twitter",
            source_url="https://x.com/AivarsZ/status/2092676682142433700",
        )
        assert doc_id is not None
        link_politicians_to_documents(days=2)
        assert _roles(tmp_roles_db, doc_id) == {1: {"mentioned"}}
