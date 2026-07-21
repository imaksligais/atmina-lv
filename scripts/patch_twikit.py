"""
Patch twikit after install/reinstall.

X/Twitter periodically rotates GraphQL endpoint hashes and changes response
structures. This script applies all necessary patches to the installed twikit
package so our scraper keeps working.

Usage:
    python scripts/patch_twikit.py           # apply patches
    python scripts/patch_twikit.py --check   # verify patches are applied
    python scripts/patch_twikit.py --refresh # fetch latest hashes from X and apply

Run after: pip install twikit  /  pip install --upgrade twikit
"""
import argparse
import re
import sys
from pathlib import Path


def _twikit_root() -> Path:
    import twikit
    return Path(twikit.__file__).parent


def _replace_in_file(path: Path, old: str, new: str) -> bool:
    """Replace first occurrence. Returns True if replaced, False if already current or not found."""
    text = path.read_text(encoding="utf-8")
    if new in text:
        return False  # already patched
    if old not in text:
        print(f"  WARNING: expected string not found in {path.name}, skipping")
        return False
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    return True


# ---------------------------------------------------------------------------
# Patch 1: GraphQL endpoint hashes (gql.py)
#
# X rotates these hashes when their GraphQL schema changes. When replies or
# search return 404, run --refresh to pull current hashes from X's JS bundle.
# ---------------------------------------------------------------------------

# Map of operation name -> current hash (updated 2026-04-29 via --refresh)
# IMPORTANT: running patch_twikit.py without --refresh applies these static values,
# which can revert newer hashes if they've drifted again. Run with --refresh to
# pull the latest from X's main JS bundle when search/replies start returning 404.
GQL_HASHES = {
    "SearchTimeline":          "XN_HccZ9SU-miQVvwTAlFQ",
    "UserTweets":              "naBcZ4al-iTCFBYGOAMzBQ",
    "UserTweetsAndReplies":    "YhE6S_TtdhVxLtpokXrRaA",
    "UserByScreenName":        "IGgvgiOx4QZndDHuD3x9TQ",
    "UserByRestId":            "VQfQ9wwYdk6j_u2O4vt64Q",
    "TweetDetail":             "QrLp7AR-eMyamw8D1N9l6A",
}


def patch_gql_hashes(root: Path, hashes: dict[str, str] | None = None) -> int:
    """Update GraphQL endpoint hashes. Returns count of changes."""
    hashes = hashes or GQL_HASHES
    gql = root / "client" / "gql.py"
    text = gql.read_text(encoding="utf-8")
    count = 0
    for op_name, new_hash in hashes.items():
        pattern = re.compile(r"url\('([^']+)/" + re.escape(op_name) + r"'\)")
        match = pattern.search(text)
        if match:
            old_hash = match.group(1)
            if old_hash != new_hash:
                text = text.replace(f"url('{old_hash}/{op_name}')", f"url('{new_hash}/{op_name}')")
                count += 1
                print(f"  gql.py: {op_name} {old_hash} -> {new_hash}")
    if count:
        gql.write_text(text, encoding="utf-8")
    return count


# ---------------------------------------------------------------------------
# Patch 2: FEATURES dict (constants.py)
#
# X validates the features dict and returns 404 if unknown/missing flags.
# ---------------------------------------------------------------------------

FEATURES_NEW = """\
FEATURES = {
    'rweb_video_screen_enabled': True,
    'rweb_cashtags_enabled': True,
    'profile_label_improvements_pcf_label_in_post_enabled': True,
    'responsive_web_profile_redirect_enabled': True,
    'rweb_tipjar_consumption_enabled': True,
    'verified_phone_label_enabled': False,
    'creator_subscriptions_tweet_preview_api_enabled': True,
    'responsive_web_graphql_timeline_navigation_enabled': True,
    'responsive_web_graphql_skip_user_profile_image_extensions_enabled': False,
    'premium_content_api_read_enabled': True,
    'communities_web_enable_tweet_community_results_fetch': True,
    'c9s_tweet_anatomy_moderator_badge_enabled': True,
    'responsive_web_grok_analyze_button_fetch_trends_enabled': True,
    'responsive_web_grok_analyze_post_followups_enabled': True,
    'responsive_web_jetfuel_frame': True,
    'responsive_web_grok_share_attachment_enabled': True,
    'responsive_web_grok_annotations_enabled': True,
    'articles_preview_enabled': True,
    'responsive_web_edit_tweet_api_enabled': True,
    'graphql_is_translatable_rweb_tweet_is_translatable_enabled': True,
    'view_counts_everywhere_api_enabled': True,
    'longform_notetweets_consumption_enabled': True,
    'responsive_web_twitter_article_tweet_consumption_enabled': True,
    'content_disclosure_indicator_enabled': True,
    'content_disclosure_ai_generated_indicator_enabled': True,
    'responsive_web_grok_show_grok_translated_post': True,
    'responsive_web_grok_analysis_button_from_backend': True,
    'post_ctas_fetch_enabled': True,
    'freedom_of_speech_not_reach_fetch_enabled': True,
    'standardized_nudges_misinfo': True,
    'tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled': True,
    'longform_notetweets_rich_text_read_enabled': True,
    'longform_notetweets_inline_media_enabled': True,
    'responsive_web_grok_image_annotation_enabled': True,
    'responsive_web_grok_imagine_annotation_enabled': True,
    'responsive_web_grok_community_note_auto_translation_is_enabled': True,
    'responsive_web_enhance_cards_enabled': False
}\
"""


def patch_features(root: Path) -> bool:
    """Replace FEATURES dict. Returns True if changed."""
    constants = root / "constants.py"
    text = constants.read_text(encoding="utf-8")
    # Find the main FEATURES dict block (not USER_FEATURES or others)
    pattern = re.compile(r"^FEATURES = \{.*?^\}", re.MULTILINE | re.DOTALL)
    match = pattern.search(text)
    if not match:
        print("  WARNING: FEATURES dict not found in constants.py")
        return False
    # Check if THIS block (not file-globally) has our marker flag
    if "responsive_web_grok_analyze_button_fetch_trends_enabled" in match.group():
        return False
    text = text[:match.start()] + FEATURES_NEW + text[match.end():]
    constants.write_text(text, encoding="utf-8")
    print("  constants.py: FEATURES dict updated (37 flags)")
    return True


# ---------------------------------------------------------------------------
# Patch 3: User object — core field migration (user.py)
#
# X moved created_at, name, screen_name from legacy to a new core object.
# Also makes all legacy field accesses use .get() with defaults.
# ---------------------------------------------------------------------------

USER_INIT_NEW = """\
    def __init__(self, client: Client, data: dict) -> None:
        self._client = client
        legacy = data['legacy']
        core = data.get('core', {})

        self.id: str = data['rest_id']
        self.created_at: str = core.get('created_at') or legacy.get('created_at', '')
        self.name: str = core.get('name') or legacy.get('name', '')
        self.screen_name: str = core.get('screen_name') or legacy.get('screen_name', '')
        self.profile_image_url: str = legacy.get('profile_image_url_https') or (data.get('avatar', {}).get('image_url', ''))
        self.profile_banner_url: str = legacy.get('profile_banner_url')
        self.url: str = legacy.get('url')
        self.location: str = legacy.get('location') or data.get('location', '')
        self.description: str = legacy.get('description') or (data.get('profile_bio', {}).get('description', ''))
        self.description_urls: list = legacy.get('entities', {}).get('description', {}).get('urls', [])
        self.urls: list = legacy.get('entities', {}).get('url', {}).get('urls')
        self.pinned_tweet_ids: list[str] = legacy.get('pinned_tweet_ids_str', [])
        self.is_blue_verified: bool = data.get('is_blue_verified', False)
        self.verified: bool = legacy.get('verified', False)
        self.possibly_sensitive: bool = legacy.get('possibly_sensitive', False)
        self.can_dm: bool = legacy.get('can_dm', False)
        self.can_media_tag: bool = legacy.get('can_media_tag', False)
        self.want_retweets: bool = legacy.get('want_retweets', False)
        self.default_profile: bool = legacy.get('default_profile', False)
        self.default_profile_image: bool = legacy.get('default_profile_image', False)
        self.has_custom_timelines: bool = legacy.get('has_custom_timelines', False)
        self.followers_count: int = legacy.get('followers_count', 0)
        self.fast_followers_count: int = legacy.get('fast_followers_count', 0)
        self.normal_followers_count: int = legacy.get('normal_followers_count', 0)
        self.following_count: int = legacy.get('friends_count', 0)
        self.favourites_count: int = legacy.get('favourites_count', 0)
        self.listed_count: int = legacy.get('listed_count', 0)
        self.media_count = legacy.get('media_count', 0)
        self.statuses_count: int = legacy.get('statuses_count', 0)
        self.is_translator: bool = legacy.get('is_translator', False)
        self.translator_type: str = legacy.get('translator_type', '')
        self.withheld_in_countries: list[str] = legacy.get('withheld_in_countries', [])
        self.protected: bool = legacy.get('protected', False)\
"""


def patch_user(root: Path) -> bool:
    """Patch User.__init__ for core field migration. Returns True if changed."""
    user_py = root / "user.py"
    text = user_py.read_text(encoding="utf-8")
    # Check if already patched
    if "core = data.get('core', {})" in text:
        return False
    # Find and replace __init__
    pattern = re.compile(
        r"    def __init__\(self, client: Client, data: dict\) -> None:.*?"
        r"self\.protected: bool = legacy\.get\('protected', False\)",
        re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        print("  WARNING: User.__init__ pattern not found in user.py")
        return False
    text = text[:match.start()] + USER_INIT_NEW + text[match.end():]
    user_py.write_text(text, encoding="utf-8")
    print("  user.py: User.__init__ patched (core field migration)")
    return True


# ---------------------------------------------------------------------------
# Patch 4: ClientTransaction.init() graceful fallback (transaction.py)
#
# X changed the "ondemand.s" anti-bot bootstrap format on x.com home page
# around 2026-03-18 (issue d60/twikit#408). twikit 2.3.3's old regex no
# longer matches → get_indices() raises "Couldn't get KEY_BYTE indices",
# leaving self.key unset → every subsequent request crashes with
# AttributeError on generate_transaction_id.
#
# Patch 5 (below) adopts the new regex from upstream PR d60/twikit#410 so
# real TID generation works again. Patch 4 here is the **safety net** —
# wraps init() in try/except so any future format change degrades to stubs
# instead of crashing. Empirically (2026-04-28) UserTweets endpoint accepts
# stub TIDs; SearchTimeline + Replies do NOT, so real TIDs from Patch 5
# are required for those endpoints.
# ---------------------------------------------------------------------------

INIT_NEW = """    async def init(self, session, headers):
        try:
            home_page_response = await handle_x_migration(session, headers)
            self.home_page_response = self.validate_response(home_page_response)
            self.DEFAULT_ROW_INDEX, self.DEFAULT_KEY_BYTES_INDICES = await self.get_indices(
                self.home_page_response, session, headers)
            self.key = self.get_key(response=self.home_page_response)
            self.key_bytes = self.get_key_bytes(key=self.key)
            self.animation_key = self.get_animation_key(
                key_bytes=self.key_bytes, response=self.home_page_response)
        except Exception:
            # X dropped ondemand.s anti-bot bootstrap (~2026-04-25).
            # Stub fallback: X no longer validates X-Client-Transaction-Id values.
            if not self.home_page_response:
                self.home_page_response = "stub"
            self.DEFAULT_ROW_INDEX = 0
            self.DEFAULT_KEY_BYTES_INDICES = [1, 2, 3]
            self.key = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
            self.key_bytes = list(b"\\x00" * 16)
            self.animation_key = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\""""


def patch_init_fallback(root: Path) -> bool:
    """Patch ClientTransaction.init() with graceful fallback. Returns True if changed."""
    tp = root / "x_client_transaction" / "transaction.py"
    text = tp.read_text(encoding="utf-8")
    if "X dropped ondemand.s anti-bot bootstrap" in text:
        return False
    pattern = re.compile(
        r"    async def init\(self, session, headers\):.*?"
        r"self\.animation_key = self\.get_animation_key\(\s*"
        r"key_bytes=self\.key_bytes, response=self\.home_page_response\)",
        re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        print("  WARNING: ClientTransaction.init pattern not found in transaction.py")
        return False
    text = text[:match.start()] + INIT_NEW + text[match.end():]
    tp.write_text(text, encoding="utf-8")
    print("  transaction.py: ClientTransaction.init() graceful fallback patched")
    return True


# ---------------------------------------------------------------------------
# Patch 5: ondemand.s.js parser — adopt upstream PR d60/twikit#410 logic
#   https://github.com/d60/twikit/pull/410
#
# X changed the home-page format around 2026-03-18:
#   old: "ondemand.s":"<hash>"
#   new: ,<index>:"ondemand.s"  ... ,<index>:"<hash>"   (two-stage lookup)
#
# Without this patch, get_indices() always raises "Couldn't get KEY_BYTE
# indices", Patch 4's try/except catches it, and we fall back to stub TIDs.
# Stubs work for UserTweets but cause 404 on SearchTimeline + Replies, so
# 3rd-party mentions ingest is broken. With this patch the real ondemand.s.js
# URL is resolved and proper key_byte_indices are extracted, restoring real
# TID generation.
#
# The Patch 4 try/except wrapper is preserved as a safety net for future
# format changes.
# ---------------------------------------------------------------------------

ONDEMAND_REGEX_OLD = (
    "ON_DEMAND_FILE_REGEX = re.compile(\n"
    "    r\"\"\"['|\\\"]{1}ondemand\\.s['|\\\"]{1}:\\s*['|\\\"]{1}([\\w]*)['|\\\"]{1}\"\"\", flags=(re.VERBOSE | re.MULTILINE))\n"
    "INDICES_REGEX = re.compile(\n"
    "    r\"\"\"(\\(\\w{1}\\[(\\d{1,2})\\],\\s*16\\))+\"\"\", flags=(re.VERBOSE | re.MULTILINE))"
)

ONDEMAND_REGEX_NEW = (
    "ON_DEMAND_FILE_REGEX = re.compile(\n"
    "    r\"\"\",(\\d+):[\"']ondemand\\.s[\"']\"\"\", flags=(re.VERBOSE | re.MULTILINE))\n"
    "ON_DEMAND_HASH_PATTERN = r',{}:\"([0-9a-f]+)\"'\n"
    "INDICES_REGEX = re.compile(r\"\\[(\\d+)\\],\\s*16\")"
)

GET_INDICES_OLD = """    async def get_indices(self, home_page_response, session, headers):
        key_byte_indices = []
        response = self.validate_response(
            home_page_response) or self.home_page_response
        on_demand_file = ON_DEMAND_FILE_REGEX.search(str(response))
        if on_demand_file:
            on_demand_file_url = f"https://abs.twimg.com/responsive-web/client-web/ondemand.s.{on_demand_file.group(1)}a.js"
            on_demand_file_response = await session.request(method="GET", url=on_demand_file_url, headers=headers)
            key_byte_indices_match = INDICES_REGEX.finditer(
                str(on_demand_file_response.text))
            for item in key_byte_indices_match:
                key_byte_indices.append(item.group(2))
        if not key_byte_indices:
            raise Exception("Couldn't get KEY_BYTE indices")
        key_byte_indices = list(map(int, key_byte_indices))
        return key_byte_indices[0], key_byte_indices[1:]"""

GET_INDICES_NEW = """    async def get_indices(self, home_page_response, session, headers):
        key_byte_indices = []
        response = self.validate_response(
            home_page_response) or self.home_page_response
        response_str = str(response)
        on_demand_file = ON_DEMAND_FILE_REGEX.search(response_str)
        if on_demand_file:
            on_demand_file_index = on_demand_file.group(1)
            hash_regex = re.compile(ON_DEMAND_HASH_PATTERN.format(on_demand_file_index))
            hash_match = hash_regex.search(response_str)
            if hash_match:
                filename = hash_match.group(1)
                on_demand_file_url = f"https://abs.twimg.com/responsive-web/client-web/ondemand.s.{filename}a.js"
                on_demand_file_response = await session.request(method="GET", url=on_demand_file_url, headers=headers)
                key_byte_indices_match = INDICES_REGEX.finditer(str(on_demand_file_response.text))
                for item in key_byte_indices_match:
                    key_byte_indices.append(item.group(1))
        if not key_byte_indices:
            raise Exception("Couldn't get KEY_BYTE indices")
        key_byte_indices = list(map(int, key_byte_indices))
        return key_byte_indices[0], key_byte_indices[1:]"""


def patch_ondemand_regex(root: Path) -> bool:
    """Patch ondemand.s.js parser to upstream PR #410 logic. Returns True if changed."""
    tp = root / "x_client_transaction" / "transaction.py"
    text = tp.read_text(encoding="utf-8")
    if "ON_DEMAND_HASH_PATTERN" in text:
        return False  # already patched
    changes = 0
    if ONDEMAND_REGEX_OLD in text:
        text = text.replace(ONDEMAND_REGEX_OLD, ONDEMAND_REGEX_NEW, 1)
        changes += 1
    else:
        print("  WARNING: old ON_DEMAND regex constants not found in transaction.py")
    if GET_INDICES_OLD in text:
        text = text.replace(GET_INDICES_OLD, GET_INDICES_NEW, 1)
        changes += 1
    else:
        print("  WARNING: old get_indices() body not found in transaction.py")
    if changes == 2:
        tp.write_text(text, encoding="utf-8")
        print("  transaction.py: ondemand.s.js parser updated to PR #410 logic")
        return True
    return False


# ---------------------------------------------------------------------------
# Refresh: fetch latest hashes from X's JavaScript bundle
# ---------------------------------------------------------------------------

def refresh_hashes() -> dict[str, str]:
    """Fetch current GraphQL operation hashes from X's main JS bundle."""
    import httpx

    print("Fetching X main page...")
    r = httpx.get(
        "https://x.com",
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        follow_redirects=True,
        timeout=15,
    )
    scripts = re.findall(r'src="(https://abs\.twimg\.com/responsive-web/client-web[^"]+main\.[^"]+\.js)"', r.text)
    if not scripts:
        print("ERROR: could not find main JS bundle URL")
        return {}

    print(f"Fetching {scripts[0]}...")
    r = httpx.get(scripts[0], headers={"User-Agent": "Mozilla/5.0"}, timeout=30)

    hashes = {}
    for op_name in GQL_HASHES:
        matches = re.findall(r'queryId:"([^"]+)",operationName:"' + op_name + '"', r.text)
        if matches:
            hashes[op_name] = matches[0]
            print(f"  {op_name}: {matches[0]}")
        else:
            print(f"  {op_name}: NOT FOUND (keeping current)")
            hashes[op_name] = GQL_HASHES[op_name]
    return hashes


# ---------------------------------------------------------------------------
# Clean up .pyc cache
# ---------------------------------------------------------------------------

def clear_pyc(root: Path):
    """Remove .pyc files so Python picks up patched .py files."""
    count = 0
    for pyc in root.rglob("*.pyc"):
        pyc.unlink()
        count += 1
    if count:
        print(f"  Cleared {count} .pyc files")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Patch twikit for X API compatibility")
    parser.add_argument("--check", action="store_true", help="Verify patches without applying")
    parser.add_argument("--refresh", action="store_true", help="Fetch latest hashes from X")
    args = parser.parse_args()

    root = _twikit_root()
    print(f"twikit location: {root}")

    if args.check:
        text = (root / "client" / "gql.py").read_text(encoding="utf-8")
        ok = True
        for op, h in GQL_HASHES.items():
            if h not in text:
                print(f"  MISSING: {op} hash {h}")
                ok = False
        ctext = (root / "constants.py").read_text(encoding="utf-8")
        features_match = re.search(r"^FEATURES = \{.*?^\}", ctext, re.MULTILINE | re.DOTALL)
        if not features_match or "responsive_web_grok_analyze_button_fetch_trends_enabled" not in features_match.group():
            print("  MISSING: FEATURES update (main FEATURES dict)")
            ok = False
        utext = (root / "user.py").read_text(encoding="utf-8")
        if "core = data.get('core', {})" not in utext:
            print("  MISSING: User core migration")
            ok = False
        ttext = (root / "x_client_transaction" / "transaction.py").read_text(encoding="utf-8")
        if "X dropped ondemand.s anti-bot bootstrap" not in ttext and "X changed the \"ondemand.s\"" not in ttext:
            print("  MISSING: ClientTransaction.init() graceful fallback (Patch 4)")
            ok = False
        if "ON_DEMAND_HASH_PATTERN" not in ttext:
            print("  MISSING: ondemand.s.js parser update (Patch 5, PR #410)")
            ok = False
        print("All patches applied." if ok else "Some patches missing — run without --check to apply.")
        sys.exit(0 if ok else 1)

    hashes = GQL_HASHES
    if args.refresh:
        hashes = refresh_hashes()
        if not hashes:
            sys.exit(1)

    changes = 0
    print("\n--- Patch 1: GraphQL hashes ---")
    changes += patch_gql_hashes(root, hashes)

    print("\n--- Patch 2: FEATURES dict ---")
    changes += int(patch_features(root))

    print("\n--- Patch 3: User core migration ---")
    changes += int(patch_user(root))

    print("\n--- Patch 4: ClientTransaction.init() graceful fallback ---")
    changes += int(patch_init_fallback(root))

    print("\n--- Patch 5: ondemand.s.js parser (PR #410) ---")
    changes += int(patch_ondemand_regex(root))

    print()
    clear_pyc(root)

    if changes:
        print(f"\nDone: {changes} patch(es) applied.")
    else:
        print("\nAll patches already applied.")


if __name__ == "__main__":
    main()
