import asyncio

import src.db as _db_mod
from src.credentials import get_credential
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


def _store_tweets(tweets: list[dict], opponent_id: int) -> list[dict]:
    """Store tweet dicts as documents with embeddings. Returns stored tweets.

    Role + feed_type behavior (resolved once per call from social_accounts):
    - feed_type='relay' (institutional media accounts like LTV Ziņas): no
      politician_links inserted. link_politicians_to_documents later scans
      the text and assigns subject from mentions, matching the RSS pipeline.
    - feed_type='first_party' (default — politicians, commentators, individual
      journalists): per-tweet handle match. role='subject' iff the source_url's
      author handle matches one of the politician's registered handles;
      otherwise role='mentioned' (twikit surfaced someone else's tweet via
      this timeline — retweet/quote-tweet/reply context — so the politician
      is mentioned but not speaking).

    See wiki/CHANGELOG 2026-04-23 entries for both fixes.
    """
    from src.matcher import extract_twitter_author_handle

    # Module-attribute access so test fixtures can monkeypatch _db_mod.get_db.
    db = _db_mod.get_db()
    try:
        accounts = db.execute(
            "SELECT handle, feed_type FROM social_accounts "
            "WHERE platform = 'twitter' AND opponent_id = ?",
            (opponent_id,),
        ).fetchall()
    finally:
        db.close()
    handles = {row["handle"].lower() for row in accounts if row["handle"]}
    feed_type = (accounts[0]["feed_type"] if accounts else "first_party") or "first_party"

    stored = []
    for tweet in tweets:
        text = tweet.get("text", "")
        if len(text) < 50:
            continue
        lang = tweet.get("lang")
        if lang not in ("lv", "ru", "en"):
            lang = "lv"
        source_url = tweet.get("source_url")

        if feed_type == "relay":
            politician_links: list[tuple[int, str]] = []
        else:
            author_handle = extract_twitter_author_handle(source_url)
            role = "subject" if (author_handle and author_handle in handles) else "mentioned"
            politician_links = [(opponent_id, role)]

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


def fetch_youtube(account_id: int) -> list[dict]:
    account = _get_account(account_id)
    if not account:
        raise ValueError(f"Social account {account_id} not found")

    api_key = get_credential("youtube_api_key")
    if not api_key:
        raise ValueError("YouTube credential not configured — set youtube_api_key")

    from googleapiclient.discovery import build

    youtube = build("youtube", "v3", developerKey=api_key)

    try:
        request = youtube.search().list(
            channelId=account["handle"],
            part="id,snippet",
            order="date",
            maxResults=10,
            type="video",
        )
        response = request.execute()
    except Exception as e:
        log_action(
            "social_fetch",
            opponent_id=account["opponent_id"],
            status="failure",
            error_message=f"YouTube API error: {e}",
        )
        raise

    posts = []
    for item in response.get("items", []):
        video_id = item["id"]["videoId"]
        snippet = item["snippet"]
        text = f"{snippet.get('title', '')} — {snippet.get('description', '')}"

        # Try to get captions
        is_auto_caption = False
        try:
            captions_response = youtube.captions().list(
                part="snippet", videoId=video_id
            ).execute()
            for cap in captions_response.get("items", []):
                if cap["snippet"]["language"] in ("lv", "ru", "en"):
                    is_auto_caption = cap["snippet"].get("trackKind") == "ASR"
                    break
        except Exception:
            pass

        posts.append({
            "id": video_id,
            "text": text,
            "created_at": snippet.get("publishedAt"),
            "platform": "youtube",
            "is_auto_caption": is_auto_caption,
        })

        if len(text) >= 50:
            doc_id = insert_document(
                content=text,
                politician_links=[(account["opponent_id"], "subject")],
                source_id=None,
                platform="youtube",
                language="lv",
                is_auto_caption=is_auto_caption,
            )
            if doc_id:
                chunks = embed_document(text)
                insert_chunks(doc_id, chunks)

    last_id = posts[0]["id"] if posts else None
    _update_cursor(account_id, last_id)

    log_action(
        "social_fetch",
        opponent_id=account["opponent_id"],
        status="success",
        details={"platform": "youtube", "posts": len(posts)},
    )
    return posts


def fetch_facebook(account_id: int) -> list[dict]:
    account = _get_account(account_id)
    if not account:
        raise ValueError(f"Social account {account_id} not found")

    page_token = get_credential("facebook_page_token")
    if not page_token:
        log_action(
            "social_fetch",
            opponent_id=account["opponent_id"],
            status="skipped",
            error_message="Facebook credential not configured",
        )
        return []

    import facebook

    graph = facebook.GraphAPI(access_token=page_token, version="3.1", timeout=15)

    try:
        feed = graph.get_connections(account["handle"], "posts", fields="message,created_time")
    except Exception as e:
        log_action(
            "social_fetch",
            opponent_id=account["opponent_id"],
            status="failure",
            error_message=f"Facebook API error: {e}",
        )
        raise

    posts = []
    for post in feed.get("data", []):
        text = post.get("message", "")
        if not text:
            continue

        posts.append({
            "id": post["id"],
            "text": text,
            "created_at": post.get("created_time"),
            "platform": "facebook",
        })

        if len(text) >= 50:
            doc_id = insert_document(
                content=text,
                politician_links=[(account["opponent_id"], "subject")],
                source_id=None,
                platform="facebook",
                language="lv",
            )
            if doc_id:
                chunks = embed_document(text)
                insert_chunks(doc_id, chunks)

    last_id = posts[0]["id"] if posts else None
    _update_cursor(account_id, last_id)

    log_action(
        "social_fetch",
        opponent_id=account["opponent_id"],
        status="success",
        details={"platform": "facebook", "posts": len(posts)},
    )
    return posts


def fetch_all_social(opponent_id: int) -> list[dict]:
    db = get_db()
    accounts = db.execute(
        "SELECT * FROM social_accounts WHERE opponent_id = ? AND active = TRUE",
        (opponent_id,),
    ).fetchall()
    db.close()

    all_posts = []
    fetchers = {
        "twitter": fetch_twitter,
        "youtube": fetch_youtube,
        "facebook": fetch_facebook,
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

    status = "success" if query_errors == 0 else "partial"
    log_action(
        "mentions_fetch",
        status=status,
        details={"fetched": len(mentions), "stored": len(stored), "errors": query_errors, "strategy": strategy},
    )

    # Auto-classify new mentions
    if stored:
        try:
            from src.reply_strategy import classify_all_pending
            classify_result = classify_all_pending(days=1)
            print(f"Auto-classified {classify_result['classified']} mentions: {classify_result['by_category']}")
        except ImportError:
            pass

    append_ingest_entry(
        source_name="X/Mentions",
        source_tier=0,
        documents_added=len(stored),
        documents_skipped=0,
        status="success",
    )
    return stored
