import asyncio

import src.db as _db_mod
from src.db import get_db, insert_document, insert_chunks, log_action
from src.embeddings import embed_document
from src.x_scraper import fetch_user_tweets, fetch_user_replies, fetch_all_x_accounts, reset_replies_flag
from src.x_pool import reset_pool
from src import x_mentions
from src.x_mentions import fetch_mentions
from src.ingest_log import append_ingest_entry


def _get_account(account_id: int) -> dict | None:
    db = get_db()
    row = db.execute("SELECT * FROM social_accounts WHERE id = ?", (account_id,)).fetchone()
    db.close()
    return dict(row) if row else None


def _update_cursor(account_id: int, last_post_id: str | None = None) -> None:
    from src.db import now_lv
    db = get_db()
    db.execute(
        "UPDATE social_accounts SET last_fetched = ?, last_post_id = ? WHERE id = ?",
        (now_lv(), last_post_id, account_id),
    )
    db.commit()
    db.close()


def _link_first_party_mentions(doc_id: int, text: str, author_pids: set[int]) -> list[int]:
    """Text-scan a stored FIRST-PARTY tweet for OTHER tracked politicians.

    Role is hard-coded ``'mentioned'`` — the matcher's own role (first match
    gets 'subject', see matcher.match_politicians) is deliberately DISCARDED.
    On a first-party document authorship is already settled by the handle
    match above; anyone else the author merely named is, by construction, not
    the speaker. Passing the matcher's role through would put non-speakers in
    the extractor's `role='subject'` queue.

    Why this lives here and not in ``link_politicians_to_documents``: that
    function's default branch selects documents with NO junction rows at all
    (``LEFT JOIN document_politicians ... WHERE dp.document_id IS NULL``), so a
    first-party tweet — which always leaves _store_tweets carrying its author
    junction — can never be offered to the text scan, on this run or any later
    one. Widening that selection would re-scan every already-linked document in
    the window on every ingest; a targeted call from the one place that knows
    the document is first-party is the smaller intervention. The relay branch
    is untouched: relay docs stay junction-free and the normal scan still picks
    them up (BACKLOG § Matcher, operator verdict 2026-08-17).

    ``author_pids`` are excluded, and so is anyone already linked to the
    document: ``document_politicians``' PK is (document_id, politician_id,
    role), so INSERT OR IGNORE would NOT stop a second row with a different
    role — the author would end up both 'subject' and 'mentioned'.

    Returns the politician ids newly linked.
    """
    from src.matcher import match_politicians

    matches = match_politicians(text)
    if not matches:
        return []

    db = _db_mod.get_db()
    try:
        already = {
            r["politician_id"]
            for r in db.execute(
                "SELECT politician_id FROM document_politicians WHERE document_id = ?",
                (doc_id,),
            ).fetchall()
        }
        added: list[int] = []
        for pid, _matcher_role in matches:
            if pid in author_pids or pid in already:
                continue
            db.execute(
                """INSERT OR IGNORE INTO document_politicians
                   (document_id, politician_id, role) VALUES (?, ?, 'mentioned')""",
                (doc_id, pid),
            )
            added.append(pid)
        db.commit()
    finally:
        db.close()
    return added


def _store_tweets(tweets: list[dict], opponent_id: int) -> list[dict]:
    """Store tweet dicts as documents with embeddings. Returns stored tweets.

    Role + feed_type behavior (resolved once per call from social_accounts):
    - feed_type='relay' (institutional media accounts like LTV Ziņas): no
      fetch-owner politician_link inserted. link_politicians_to_documents later
      scans the text and assigns subject from mentions, matching the RSS pipeline.
    - feed_type='first_party' (default — politicians, commentators, individual
      journalists): per-tweet handle match. role='subject' iff the source_url's
      author handle matches one of the politician's registered handles;
      otherwise role='mentioned' (twikit surfaced someone else's tweet via
      this timeline — retweet/quote-tweet/reply context — so the politician
      is mentioned but not speaking).

    2026-07-24 fix: the tweet author is now resolved against ALL twitter
    accounts, not just the fetch account. When a tracked politician's OWN tweet
    surfaces via ANOTHER politician's feed (reply/mention context), the author
    still gets a 'subject' junction — the fetch owner remains 'mentioned'. This
    closes the doc-72542 hole where a cross-feed author's subject junction was
    permanently lost (insert_document is content_hash-idempotent, so a later
    own-timeline fetch could never add it). Author handles owned by a RELAY
    account never get 'subject' this way — the relay convention defers them to
    the text scan. Handle ownership does not expire, so inactive accounts count.

    2026-08-18: first_party documents additionally get a text scan for OTHER
    tracked politicians, stored strictly as role='mentioned'
    (_link_first_party_mentions — see its docstring for why the scan cannot
    live in link_politicians_to_documents). Relay documents are unchanged.

    See wiki/CHANGELOG 2026-04-23 entries for the feed_type/role fixes.
    """
    from src.matcher import extract_twitter_author_handle

    # Module-attribute access so test fixtures can monkeypatch _db_mod.get_db.
    db = _db_mod.get_db()
    try:
        all_accounts = db.execute(
            "SELECT opponent_id, handle, feed_type FROM social_accounts "
            "WHERE platform = 'twitter'",
        ).fetchall()
    finally:
        db.close()

    own_rows = [r for r in all_accounts if r["opponent_id"] == opponent_id]
    own_handles = {r["handle"].lower() for r in own_rows if r["handle"]}
    feed_type = (own_rows[0]["feed_type"] if own_rows else "first_party") or "first_party"
    # lowercased handle -> (opponent_id, feed_type) across every account.
    author_map: dict[str, tuple[int, str]] = {
        r["handle"].lower(): (r["opponent_id"], (r["feed_type"] or "first_party"))
        for r in all_accounts
        if r["handle"]
    }

    stored = []
    for tweet in tweets:
        text = tweet.get("text", "")
        if len(text) < 50:
            continue
        lang = tweet.get("lang")
        if lang not in ("lv", "ru", "en"):
            lang = "lv"
        source_url = tweet.get("source_url")

        author_handle = extract_twitter_author_handle(source_url)

        if feed_type == "relay":
            # No fetch-owner link; text scan assigns mentions later.
            politician_links: list[tuple[int, str]] = []
        else:
            role = "subject" if (author_handle and author_handle in own_handles) else "mentioned"
            politician_links = [(opponent_id, role)]

        # Cross-feed author: if the tweet author is a DIFFERENT tracked
        # politician whose account is first_party, tag them 'subject' too.
        # Relay-owned author handles (org accounts) are skipped — the relay
        # convention defers them to the text scan.
        if author_handle:
            mapped = author_map.get(author_handle)
            if mapped and mapped[0] != opponent_id and mapped[1] == "first_party":
                politician_links.append((mapped[0], "subject"))

        doc_id = insert_document(
            content=text,
            politician_links=politician_links,
            source_id=None,
            platform="twitter",
            language=lang,
            source_url=source_url,
            published_at=tweet.get("created_at"),
            reply_count=tweet.get("reply_count"),
            retweet_count=tweet.get("retweet_count"),
            favorite_count=tweet.get("favorite_count"),
        )
        if doc_id:
            chunks = embed_document(text)
            insert_chunks(doc_id, chunks)
            # First-party documents leave here already carrying a junction, so
            # link_politicians_to_documents' unlinked-only selection will never
            # offer them to the text scan. Run it here instead, mentions only.
            if feed_type != "relay":
                _link_first_party_mentions(
                    doc_id, text, {pid for pid, _ in politician_links}
                )
            stored.append(tweet)
    return stored


def fetch_twitter(account_id: int) -> list[dict]:
    """Fetch tweets for a social account via twikit."""
    account = _get_account(account_id)
    if not account:
        raise ValueError(f"Social account {account_id} not found")

    handle = account["handle"]
    since_id = account.get("last_post_id")

    try:
        tweets = asyncio.run(fetch_user_tweets(handle, since_id=since_id, limit=20))
        replies = asyncio.run(fetch_user_replies(handle, limit=10))
    except Exception as e:
        log_action(
            "social_fetch",
            opponent_id=account["opponent_id"],
            status="failure",
            error_message=f"X scraper error: {e}",
        )
        raise

    all_posts = tweets + replies
    stored = _store_tweets(all_posts, account["opponent_id"])

    # Update cursor with newest tweet ID
    if tweets:
        newest_id = tweets[0]["id"]
        _update_cursor(account_id, newest_id)

    log_action(
        "social_fetch",
        opponent_id=account["opponent_id"],
        status="success",
        details={"platform": "twitter", "tweets": len(tweets), "replies": len(replies), "stored": len(stored)},
    )
    return all_posts


_FETCH_PRIORITY = {
    # Active politicians: same priority — 'tracked' is the unified
    # post-2026-04-11 value, legacy values kept for forked dev DBs.
    "tracked": 1,
    "opponent": 1,
    "coalition_partner": 1,
    "potential_ally": 1,
    # Audience / context accounts: lower priority.
    "neutral": 2,
    "influencer": 3,
    "journalist": 3,
    "organization": 3,
    "inactive": 9,
}


def _prioritize_accounts(accounts: list[dict]) -> list[dict]:
    """Sort accounts by political importance (MMN first, then opponents, etc.)."""
    db = get_db()
    pid_priority = {}
    for row in db.execute("SELECT id, relationship_type FROM tracked_politicians").fetchall():
        pid_priority[row["id"]] = _FETCH_PRIORITY.get(row["relationship_type"] or "", 7)
    db.close()
    return sorted(accounts, key=lambda a: pid_priority.get(a["opponent_id"], 7))


def fetch_all_twitter() -> dict[int, list[dict]]:
    """Fetch tweets for ALL active Twitter accounts. Called during daily routine."""
    reset_replies_flag()  # re-enable replies endpoint in case prior session disabled it
    db = get_db()
    accounts = db.execute(
        "SELECT id, opponent_id, handle, last_post_id FROM social_accounts WHERE platform = 'twitter' AND active = TRUE"
    ).fetchall()
    db.close()

    if not accounts:
        log_action("social_fetch_all", status="skipped", error_message="No active Twitter accounts")
        return {}

    account_dicts = _prioritize_accounts([dict(a) for a in accounts])

    try:
        results = asyncio.run(fetch_all_x_accounts(account_dicts))
    except Exception as e:
        log_action("social_fetch_all", status="failure", error_message=f"X batch fetch error: {e}")
        raise

    # Store all tweets and update cursors
    total_stored = 0
    for opponent_id, tweets in results.items():
        stored = _store_tweets(tweets, opponent_id)
        total_stored += len(stored)

        # Find the account(s) for this opponent and update cursor
        for acc in account_dicts:
            if acc["opponent_id"] == opponent_id:
                handle_tweets = [t for t in tweets if f"/{acc['handle']}/" in t.get("source_url", "")]
                if handle_tweets:
                    _update_cursor(acc["id"], handle_tweets[0]["id"])

    log_action(
        "social_fetch_all",
        status="success",
        details={"accounts": len(account_dicts), "stored": total_stored},
    )
    total_added = sum(len(tweets) for tweets in results.values())
    append_ingest_entry(
        source_name="X/Twitter",
        source_tier=0,
        documents_added=total_added,
        documents_skipped=0,
        status="success",
        extra=f"{len(results)} politiķi",
    )
    return results


def fetch_all_social(opponent_id: int) -> list[dict]:
    db = get_db()
    accounts = db.execute(
        "SELECT * FROM social_accounts WHERE opponent_id = ? AND active = TRUE",
        (opponent_id,),
    ).fetchall()
    db.close()

    all_posts = []
    # X only — Data Contract #11: `social_accounts` is X-only, one row per
    # politician (FB/website live in `external_profiles`). The `youtube` and
    # `facebook` fetchers that used to sit here were removed 2026-08-15: no
    # caller outside this dict, no `social_accounts` row has ever carried
    # either platform (DB 2026-08-15: twitter 108, nothing else), and neither
    # `googleapiclient` nor `facebook` is installed — so both would have died
    # on import inside the `except Exception` below, i.e. silently.
    fetchers = {
        "twitter": fetch_twitter,
    }

    for account in accounts:
        platform = account["platform"]
        fetcher = fetchers.get(platform)
        if not fetcher:
            continue
        try:
            posts = fetcher(account["id"])
            all_posts.extend(posts)
        except Exception as e:
            # Log but don't crash
            log_action(
                "social_fetch",
                opponent_id=opponent_id,
                status="failure",
                error_message=f"{platform}: {e}",
            )

    return all_posts


def fetch_all_mentions() -> list[dict]:
    """Fetch X/Twitter mentions for all active tracked politicians.

    Builds handle_to_pid mapping from social_accounts, calls fetch_mentions(),
    stores results as documents with platform='x_mention' and politician junction links.

    Returns list of stored mention dicts.
    """
    db = get_db()
    accounts = db.execute(
        "SELECT opponent_id, handle FROM social_accounts WHERE platform = 'twitter' AND active = TRUE"
    ).fetchall()
    db.close()

    if not accounts:
        log_action("mentions_fetch", status="skipped", error_message="No active Twitter accounts")
        return []

    # Build handle -> politician_id mapping
    handle_to_pid = {a["handle"]: a["opponent_id"] for a in accounts}

    # Reset client before search — after fetch_all_twitter() the client's
    # transaction state can become stale, causing SearchTimeline 404 errors
    reset_pool()

    try:
        mentions, query_errors = asyncio.run(fetch_mentions(handle_to_pid))
    except Exception as e:
        log_action(
            "mentions_fetch",
            status="failure",
            error_message=f"Mentions fetch error: {e}",
            details={"strategy": x_mentions.last_run_strategy},
        )
        raise

    strategy = x_mentions.last_run_strategy

    # All queries failed — log as failure, not success
    total_queries = len(handle_to_pid)  # one timeline fetch per politician
    if query_errors > 0 and len(mentions) == 0:
        log_action(
            "mentions_fetch",
            status="failure",
            error_message=f"All {query_errors}/{total_queries} queries failed (API errors)",
            details={"fetched": 0, "stored": 0, "errors": query_errors, "strategy": strategy},
        )
        return []

    # Store each mention as a document
    stored = []
    for mention in mentions:
        text = mention.get("text", "")
        if len(text) < 30:  # lower threshold than regular tweets — mentions can be short
            continue

        lang = mention.get("lang")
        if lang not in ("lv", "ru", "en"):
            lang = "lv"

        # Build junction links: author as subject + all mention targets
        politician_links = []
        if mention.get("opponent_id"):
            politician_links.append((mention["opponent_id"], "subject"))
        for target_pid in mention["mention_target_ids"]:
            politician_links.append((target_pid, "mention_target"))

        if politician_links:
            doc_id = insert_document(
                content=text,
                politician_links=politician_links,
                source_id=None,
                platform="x_mention",
                language=lang,
                source_url=mention.get("source_url"),
                published_at=mention.get("created_at"),
                reply_count=mention.get("reply_count"),
                retweet_count=mention.get("retweet_count"),
                favorite_count=mention.get("favorite_count"),
            )
            if doc_id:
                chunks = embed_document(text)
                insert_chunks(doc_id, chunks)
                stored.append({**mention, "doc_id": doc_id})

    # „Atnesu daudz, saglabāju nulli" NAV panākums — tā ir klusa nomešana, un
    # tieši tā 2026-08-01 izmeklēšanā izrādījās 5 nulles dienas no 25. Cēlonis:
    # `timeline` stratēģija skenē izsekoto politiķu PAŠU taimlīnes, bet tos pašus
    # tvītus `fetch_all_twitter()` jau ir saglabājis dažas minūtes agrāk, tāpēc
    # katrs trāpa `insert_document()` content_hash dublikāta zarā un atgriež
    # None. Mērīts: 07-15 fetched 262 / stored 0, 07-20 fetched 258 / stored 0 —
    # abi ar errors 0 un statusu „success", un 0 mention_target junction rindām.
    fetched_n, stored_n = len(mentions), len(stored)
    error_msg = None
    if fetched_n and not stored_n:
        status = "failure"
        error_msg = (
            f"{fetched_n} pieminējumi atnesti, 0 saglabāti (stratēģija: {strategy}) — "
            "klusa nomešana; ja stratēģija ir 'timeline', tie visdrīzāk ir jau "
            "ievāktie izsekoto politiķu tvīti, kurus content_hash dedup noraida"
        )
    elif query_errors:
        status = "partial"
    else:
        status = "success"

    # `timeline` nav līdzvērtīga `search`: tā redz TIKAI izsekoto autoru
    # savstarpējos pieminējumus, ne publisko sarunu par politiķiem. Pārslēgšanās
    # uz to notiek klusi (pūla veselības fallback), tāpēc seguma sašaurinājumam
    # jābūt redzamam pašam par sevi, arī tad, kad kaut kas tika saglabāts.
    coverage_note = None
    if strategy == "timeline":
        coverage_note = (
            "stratēģija timeline — šaurs segums: tikai izsekoto autoru savstarpējie "
            "pieminējumi, publiskā saruna par politiķiem netiek meklēta"
        )

    log_action(
        "mentions_fetch",
        status=status,
        error_message=error_msg or coverage_note,
        details={"fetched": fetched_n, "stored": stored_n, "errors": query_errors,
                 "strategy": strategy},
    )

    # Auto-classify new mentions
    if stored:
        try:
            from src.reply_strategy import classify_all_pending
            classify_result = classify_all_pending(days=1)
            print(f"Auto-classified {classify_result['classified']} mentions: {classify_result['by_category']}")
        except ImportError:
            pass

    # `status` bija iekodēts cieti kā "success", tāpēc wiki ingest žurnāls rādīja
    # zaļu X/Mentions rindu arī dienās, kad saglabāti 0 dokumenti — operatora
    # galvenā virsma melo tieši tad, kad tai vajadzētu brīdināt.
    append_ingest_entry(
        source_name="X/Mentions",
        source_tier=0,
        documents_added=stored_n,
        documents_skipped=fetched_n - stored_n,
        status=status,
        error=error_msg,
        extra=coverage_note,
    )
    return stored
