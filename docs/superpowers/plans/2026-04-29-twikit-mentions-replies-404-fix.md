# Twikit Mentions/Replies 404 Fix Implementation Plan

> **STATUS:** ✅ RESOLVED 2026-04-29 via Phase B (architectural pivot).
> Phase A (request-shape patch) izrādījās NAV iespējama bez pilna TID generator-a rebuilds.
> Saturs zem `## Phase A:` ir saglabāts kā vēsturisks references (varbūt nederīgs, ja kāds vēlāk atjauno TID).

## Faktiskais root cause un risinājums

**Root cause:** X selektīvi noraida `patch_twikit.py` Patch 4 stub `x-client-transaction-id` uz `SearchTimeline` un `UserTweetsAndReplies`. Apstiprināts ar hardcoded reālu browser TID — endpoint atbild 200 OK uzreiz. `UserTweets` un `UserByScreenName` paliek lenient.

**Risinājums (Phase B):** `src/x_mentions.py` pārstrādāts uz **per-politician `UserTweets` timeline scan + tekstuāls `@mention` filter**. `Replies` produkts kodā nebija aktīvs lietotājs — netika dziedēts.

**Verifikācija:**
- 7/7 unit tests `tests/test_x_mentions.py` GREEN.
- Live integration: 3 politiķi → 3 timeline fetches → 0 errors.
- Probe `python scripts/probe_x_cookies.py` paplašināts uz visiem 4 endpoint-iem per slot — pareizs regression-detection rīks nākotnei.

**Trade-off (zināms blind spot):** Mentions FROM untracked autoriem (žurnālisti) netiek savākti, kamēr X TID generator nav atjaunots. Tracked-to-tracked interakcijas — pretrunu signāla pamats — saglabājas.

**Long-term TODO:** Reverse-engineer modern X TID generator. Indices pārvietojušies no `ondemand.s.*a.js` uz iekšēju webpack chunk (regex `(\w[(\d{1,2})], 16)` `main.js`-ā atrod tikai 1 match no nepieciešamajiem 4+). Ja tas tiek atjaunots → twikit `search_tweet` un `Replies` automātiski darbosies bez papildu koda izmaiņām.

**Skat.:**
- CHANGELOG § 2026-04-29
- `wiki/operations/twikit-notes.md` § 2026-04-29
- Memory: `project_x_mentions_timeline_scan.md`

---

> **For agentic workers (zem šī ir vēsturisks plans, ko izstrādājām PIRMS root-cause apstiprinājuma):** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Atjaunot `@mentions-monitor` darba spēju — `fetch_mentions()` šobrīd 404'o uz visiem 6 slotiem, jo `SearchTimeline` un `UserTweetsAndReplies` GraphQL endpoint-i noraida `twikit 2.3.3` payload formātu.

**Architecture:** Diviem solījumiem — (A) atrast precīzu request-shape drift un papildināt `scripts/patch_twikit.py` ar Patch 5, (B) ja A neizdodas, pārveidot `fetch_mentions` uz darbojošā `UserTweets` endpoint-a (per-politician timeline + tekstuāls @-mention filter). Pēdējais arī ir `replies` ceļa solid fallback: `TweetDetail` ar konversācijas pavedienu vietā UserTweetsAndReplies.

**Tech Stack:** Python 3.11, twikit 2.3.3, httpx (debug), pytest, X.com web Network capture (DevTools manuālā soļa veikšanai).

---

## Pre-flight: Diagnostikas pierādījumi (jau savākti 2026-04-29)

| Endpoint | Status | Slot pārklājums |
|----------|--------|-----------------|
| `UserByScreenName` (`get_user_by_screen_name`) | ✓ 200 OK | 6/6 sloti |
| `UserTweets` (`get_user_tweets(..., 'Tweets')`) | ✓ 15 tweets | 6/6 sloti |
| `UserTweetsAndReplies` (`get_user_tweets(..., 'Replies')`) | ✗ 404 (empty body) | 6/6 sloti |
| `SearchTimeline` (`search_tweet`) | ✗ 404 (empty body) | 6/6 sloti |

**Pierādītie negatīvie hipotēzes (NAV root cause):**
1. **Cookies expired.** Noraidīts: tā paša klienta `UserTweets` strādā.
2. **GraphQL queryId drift.** Noraidīts: `scripts/patch_twikit.py --refresh` 2026-04-29 atgrieza identiskus hashus kā jau ielādētajā `gql.py` (`XN_HccZ9SU-miQVvwTAlFQ` SearchTimeline, `YhE6S_TtdhVxLtpokXrRaA` UserTweetsAndReplies).
3. **`fieldToggles` trūkst.** Noraidīts (daļēji): manuāli pievienojot 8 toggles no JS bundle metadata, 404 saglabājas. Bet pievienošana joprojām pareiza — variables/features kopā ar toggles var būt bloķētājs.
4. **Endpoint pazudis.** Noraidīts: `x-rate-limit-limit: 50` un `x-rate-limit-remaining: 48` headers nāk atpakaļ → X dispečers atpazīst queryId un trekē rate-limitus, tikai noraida request shape.

**Aktīvās hipotēzes (jāpārbauda Phase 0):**
- **H1:** `variables` payload trūkst kāda šobrīd obligāta lauka (piem., `withClientEventToken`, `referrer`, jauns slēdzis SearchTimeline gadījumā).
- **H2:** X kombinētā features+toggles validācija ir stingrāka par to, ko publicē JS bundle metadata; trūkst kāds nesen pievienots flag.
- **H3:** Šie endpoint-i ir pieejami tikai *blue/premium* tier kontiem; mūsu 6 sloti ir non-premium → 404 vietā tikai šim auth tier-am.

---

## Task 0: Manuāla X.com browser-network capture (LIVE diff)

**Files:**
- Create: `data/x_cookies/_diag/searchtimeline_browser.curl` (gitignored — `_diag/` jau būtu data/-ē)
- Create: `data/x_cookies/_diag/usertweetsandreplies_browser.curl`
- Create: `data/x_cookies/_diag/usertweets_browser.curl`

**Mērķis:** Iegūt eksaktu reālu webapp request-u no logged-in pārlūkprogrammas, lai diff-otu pret to, ko sūta twikit. Bez šī mēs hipotēzes meklējam acliniski.

- [ ] **Step 1: Atvērt X.com Chrome/Firefox kā jebkurš no slot kontiem** (piem. @gggundega vai @atmina_lv).

- [ ] **Step 2: Atvērt DevTools → Network tab → filtrēt pēc `i/api/graphql`.**

- [ ] **Step 3: Veikt darbības, kas trigeros visus 3 endpoint-us:**
  1. Klikšķināt search ikonu, ievadīt `Latvija`, izvēlēties **Latest** tabu → trigerē `SearchTimeline`.
  2. Atvērt `@AtminaLV` profilu → klikšķināt **Replies** tabu → trigerē `UserTweetsAndReplies`.
  3. Tajā pat profilā paliek **Posts** tabā → trigerē `UserTweets` (kontroles paraugs, kas STRĀDĀ).

- [ ] **Step 4: Katram no 3 request-iem labais klikšķis → "Copy" → "Copy as cURL (bash)" un saglabāt attiecīgā `_diag/*.curl` failā.**

- [ ] **Step 5: Diff-ot URL un body komponentus.**

```bash
# No katra cURL faila izvilkt URL un decode-ot variables, features, fieldToggles
# Salīdzināt pret to, ko twikit sūta (no DEBUG logiem).
# Konkrēti pierakstīt diff:
#   - missing variables fields
#   - missing/extra features flags
#   - missing fieldToggles
#   - jauni headers (x-client-uuid v2, x-twitter-client-language, ...)
```

- [ ] **Step 6: Dokumentēt secinājumu vienā teikumā** failā `data/x_cookies/_diag/diff-summary.md`. Variants A: "fixable drift — X obligātais lauks Y trūkst twikit-ā" → ej uz Phase A. Variants B: "non-premium konts neder uz šiem endpointiem" → ej uz Phase B (architecture pivot).

- [ ] **Step 7: Commit** (tikai bez cURL failiem — tie satur cookies + bearer; pievienot `_diag/` uz `.gitignore` ja nav).

```bash
echo "data/x_cookies/_diag/" >> .gitignore
git add .gitignore docs/superpowers/plans/2026-04-29-twikit-mentions-replies-404-fix.md
git commit -m "docs(plans): add twikit mentions/replies 404 fix plan + ignore diag captures"
```

---

## Phase A: Patch twikit payload (ja Task 0 atklāj fixable drift)

### Task A1: Failing test — extended probe across 3 endpoints

**Files:**
- Modify: `scripts/probe_x_cookies.py:1-64` (paplašināt — pievienot `UserTweetsAndReplies` un baseline `UserTweets`)

- [ ] **Step 1: Pārliecināties, ka esošais probe palaiž visus 3 endpointus.**

```python
# scripts/probe_x_cookies.py — pievienot probes
async def probe_one(slot: int, cookie_path: Path) -> dict:
    res = {
        "slot": slot, "file": cookie_path.name,
        "get_user": None, "user_tweets": None,
        "user_replies": None, "search_tweet": None, "error": None,
    }
    try:
        client = Client("en-US")
        client.load_cookies(str(cookie_path))

        try:
            user = await client.get_user_by_screen_name("AtminaLV")
            res["get_user"] = f"ok ({user.screen_name})"
        except Exception as e:
            res["get_user"] = f"FAIL: {type(e).__name__}: {str(e)[:100]}"
            return res  # nav jēgas turpināt bez user_id

        try:
            t = await client.get_user_tweets(user.id, "Tweets", count=2)
            res["user_tweets"] = f"ok ({len(t)})"
        except Exception as e:
            res["user_tweets"] = f"FAIL: {type(e).__name__}: {str(e)[:100]}"

        try:
            r = await client.get_user_tweets(user.id, "Replies", count=2)
            res["user_replies"] = f"ok ({len(r)})"
        except Exception as e:
            res["user_replies"] = f"FAIL: {type(e).__name__}: {str(e)[:100]}"

        try:
            s = await client.search_tweet("Latvija", "Latest", count=1)
            res["search_tweet"] = f"ok ({len(s)})"
        except Exception as e:
            res["search_tweet"] = f"FAIL: {type(e).__name__}: {str(e)[:100]}"

    except Exception as e:
        res["error"] = f"{type(e).__name__}: {str(e)[:120]}"
    return res
```

- [ ] **Step 2: Palaist probe pirms patcha — apstiprināt baseline.**

```bash
.venv/Scripts/python scripts/probe_x_cookies.py
```

Expected: 6 slots, visiem `user_tweets: ok`, `search_tweet: FAIL`, `user_replies: FAIL`.

- [ ] **Step 3: Commit baseline probe.**

```bash
git add scripts/probe_x_cookies.py
git commit -m "test(twikit): probe all 4 endpoints per slot for 404 isolation"
```

### Task A2: Patch 5 — pievienot trūkstošos lauks `patch_twikit.py`

**Files:**
- Modify: `scripts/patch_twikit.py` (pievienot Patch 5 funkciju, kura pārraksta `gql.search_timeline` un `gql._get_user_tweets`)

**Pieņēmums:** Task 0 diff parāda, ka SearchTimeline+UserTweetsAndReplies prasa, piem., `fieldToggles` ar 8 wert nosaukumiem (no bundle metadata) PLUS variables jaunu lauku (piem., `withSafetyModeUserFields`, `withClientEventToken` vai `referrer`). Konkrētie nosaukumi tiks aizpildīti pēc Task 0.

- [ ] **Step 1: Pievienot Patch 5 funkciju `patch_twikit.py` apakšā (pirms `clear_pyc`).**

```python
# ---------------------------------------------------------------------------
# Patch 5: SearchTimeline + UserTweetsAndReplies request shape (gql.py)
#
# X tightened payload validation on these endpoints ~2026-04-29. JS bundle
# metadata declares 8 mandatory fieldToggles for both. UserTweets is lenient
# and works without them, but SearchTimeline / UserTweetsAndReplies return
# 404 (empty body) with rate-limit headers proxied through.
# ---------------------------------------------------------------------------

REQUIRED_FIELD_TOGGLES = {
    "withPayments": False,
    "withAuxiliaryUserLabels": False,
    "withArticleRichContentState": True,
    "withArticlePlainText": False,
    "withArticleSummaryText": False,
    "withArticleVoiceOver": False,
    "withGrokAnalyze": False,
    "withDisallowedReplyControls": False,
}

# AIZPILDĪT no Task 0 diff! Šobrīd tukšs — sample after capture.
ADDITIONAL_SEARCH_VARS = {
    # piem.: "withClientEventToken": False,
}
ADDITIONAL_USER_TWEETS_VARS = {
    # piem.: "withCommunity": False,
}

PATCH5_SEARCH = """    async def search_timeline(
        self,
        query: str,
        product: str,
        count: int,
        cursor: str | None
    ):
        variables = {
            'rawQuery': query,
            'count': count,
            'querySource': 'typed_query',
            'product': product,
        }
        # Patch 5: ADDITIONAL_SEARCH_VARS placeholder
        variables.update(__ADDITIONAL_SEARCH_VARS__)
        if cursor is not None:
            variables['cursor'] = cursor
        return await self.gql_get(
            Endpoint.SEARCH_TIMELINE, variables, FEATURES,
            extra_params={'fieldToggles': __REQUIRED_FIELD_TOGGLES__},
        )"""

PATCH5_USER_TWEETS = """    async def _get_user_tweets(self, user_id, count, cursor, endpoint):
        variables = {
            'userId': user_id,
            'count': count,
            'includePromotedContent': True,
            'withQuickPromoteEligibilityTweetFields': True,
            'withVoice': True,
            'withV2Timeline': True,
        }
        # Patch 5: ADDITIONAL_USER_TWEETS_VARS placeholder
        variables.update(__ADDITIONAL_USER_TWEETS_VARS__)
        if cursor is not None:
            variables['cursor'] = cursor
        return await self.gql_get(
            endpoint, variables, FEATURES,
            extra_params={'fieldToggles': __REQUIRED_FIELD_TOGGLES__},
        )"""


def patch_search_and_replies(root: Path) -> bool:
    """Patch SearchTimeline + _get_user_tweets request shape. Returns True if changed."""
    gql = root / "client" / "gql.py"
    text = gql.read_text(encoding="utf-8")
    if "Patch 5: ADDITIONAL_SEARCH_VARS placeholder" in text:
        return False

    new_search = (PATCH5_SEARCH
                  .replace("__ADDITIONAL_SEARCH_VARS__", repr(ADDITIONAL_SEARCH_VARS))
                  .replace("__REQUIRED_FIELD_TOGGLES__", repr(REQUIRED_FIELD_TOGGLES)))
    new_user = (PATCH5_USER_TWEETS
                .replace("__ADDITIONAL_USER_TWEETS_VARS__", repr(ADDITIONAL_USER_TWEETS_VARS))
                .replace("__REQUIRED_FIELD_TOGGLES__", repr(REQUIRED_FIELD_TOGGLES)))

    # Replace search_timeline def
    pat_s = re.compile(
        r"    async def search_timeline\(.*?return await self\.gql_get\(Endpoint\.SEARCH_TIMELINE, variables, FEATURES\)",
        re.DOTALL,
    )
    if not pat_s.search(text):
        print("  WARNING: search_timeline def not found")
        return False
    text = pat_s.sub(new_search, text, count=1)

    # Replace _get_user_tweets def
    pat_u = re.compile(
        r"    async def _get_user_tweets\(self, user_id, count, cursor, endpoint\):.*?return await self\.gql_get\(endpoint, variables, FEATURES\)",
        re.DOTALL,
    )
    if not pat_u.search(text):
        print("  WARNING: _get_user_tweets def not found")
        return False
    text = pat_u.sub(new_user, text, count=1)

    gql.write_text(text, encoding="utf-8")
    print("  gql.py: SearchTimeline + _get_user_tweets request shape patched (Patch 5)")
    return True
```

- [ ] **Step 2: Reģistrēt patch funkciju `main()`.**

```python
# patch_twikit.py main() pievienot pirms clear_pyc:
print("\n--- Patch 5: SearchTimeline + UserTweetsAndReplies request shape ---")
changes += int(patch_search_and_replies(root))
```

Un `--check` blokā:
```python
gtext = (root / "client" / "gql.py").read_text(encoding="utf-8")
if "Patch 5: ADDITIONAL_SEARCH_VARS placeholder" not in gtext:
    print("  MISSING: Patch 5 (search/replies request shape)")
    ok = False
```

- [ ] **Step 3: Aizpildīt `ADDITIONAL_SEARCH_VARS` un `ADDITIONAL_USER_TWEETS_VARS` no Task 0 diff.**

Ja Task 0 diff parāda, piemēram, ka browseris sūta `withSafetyModeUserFields: true`:
```python
ADDITIONAL_SEARCH_VARS = {
    "withSafetyModeUserFields": True,
}
```

- [ ] **Step 4: Pielietot patch.**

```bash
.venv/Scripts/python scripts/patch_twikit.py
```

Expected: `Patch 5: SearchTimeline + _get_user_tweets request shape patched`.

- [ ] **Step 5: Probe pēc patcha — sagaidām GREEN visiem 6 slotiem.**

```bash
.venv/Scripts/python scripts/probe_x_cookies.py
```

Expected: visiem 6 slotiem `search_tweet: ok (1)` un `user_replies: ok (2)`.

- [ ] **Step 6: Ja vēl FAIL — palaist ar HTTP debug, salīdzināt URL pret browser cURL, atrast atlikušo lauku, atgriezties uz Step 3.**

```bash
.venv/Scripts/python -c "
import asyncio, logging; logging.basicConfig(level=logging.DEBUG)
from twikit import Client
async def m():
  c = Client('en-US'); c.load_cookies('data/x_cookies/2.json')
  await c.search_tweet('Latvija', 'Latest', count=1)
asyncio.run(m())
" 2>&1 | grep "graphql/.*SearchTimeline"
```

- [ ] **Step 7: Commit.**

```bash
git add scripts/patch_twikit.py
git commit -m "fix(twikit): patch 5 — SearchTimeline + UserTweetsAndReplies request shape

X tightened GraphQL payload validation on these endpoints ~2026-04-29.
Adds required fieldToggles + variables fields captured from live web
session (data/x_cookies/_diag/*.curl). Restores @mentions-monitor + reply
fetch across all 6 cookie slots."
```

### Task A3: End-to-end verification — `fetch_all_mentions()` integration test

**Files:**
- Create: `tests/test_x_mentions_integration.py`

- [ ] **Step 1: Uzrakstīt failing test, kas izsauc `fetch_mentions` ar mazu handle dict.**

```python
# tests/test_x_mentions_integration.py
"""Live integration smoke test for fetch_mentions.
Skips if cookies missing or in CI. Run manually: pytest -m integration -k mentions"""
import asyncio
import pytest
from pathlib import Path

pytestmark = pytest.mark.integration

@pytest.mark.skipif(
    not (Path(__file__).resolve().parent.parent / "data" / "x_cookies" / "1.json").exists(),
    reason="No X cookies available",
)
def test_fetch_mentions_returns_at_least_one_query_success():
    from src.x_mentions import fetch_mentions
    from src.x_pool import reset_pool
    reset_pool()
    handle_to_pid = {"AtminaLV": 1}  # known handle, expected to find mentions
    mentions, errors = asyncio.run(fetch_mentions(handle_to_pid, limit=5, batch_size=1))
    assert errors == 0, f"Some queries returned errors: {errors}"
    # Don't assert on len(mentions) — depends on real X data; assert no errors
```

- [ ] **Step 2: Palaist test — pirms Patch 5 jābūt FAIL ar `errors > 0`.**

```bash
.venv/Scripts/python -m pytest tests/test_x_mentions_integration.py -v -m integration
```

Expected (post-patch): PASS.

- [ ] **Step 3: Palaist visu test suite — verificēt nav regresijas.**

```bash
.venv/Scripts/python -m pytest tests/ -v 2>&1 | tail -20
```

Expected: visi pre-eksistējošie testi joprojām PASS (baseline no commit `e43d22e`: 859/3).

- [ ] **Step 4: Commit.**

```bash
git add tests/test_x_mentions_integration.py
git commit -m "test(x_mentions): live smoke test pinning fetch_mentions success after Patch 5"
```

### Task A4: Atjaunot wiki + memory

**Files:**
- Modify: `wiki/operations/twikit-notes.md`
- Create memory: `project_twikit_search_replies_patch5.md`

- [ ] **Step 1: Pievienot ierakstu `wiki/operations/twikit-notes.md`** par to, kas tika atklāts un kā fix pielietojams.

```markdown
## 2026-04-29: Patch 5 — SearchTimeline + UserTweetsAndReplies 404

X pastiprināja payload validāciju šiem diviem endpointiem. Symptom: visi sloti
`search_tweet` / `get_user_tweets(..., 'Replies')` → 404 ar empty body, kamēr
`get_user_tweets(..., 'Tweets')` un `get_user_by_screen_name` strādā.

**Diagnostikas signāli:**
- `x-rate-limit-limit/remaining` headers ir klāt → endpoint atpazīts, request shape
  noraidīts.
- `--refresh` neuzlabo (hashes jau aktuāli).

**Fix:** `scripts/patch_twikit.py` Patch 5 pievieno required `fieldToggles` un
papildu variables `gql.search_timeline()` un `gql._get_user_tweets()`. Pielieto
ar `python scripts/patch_twikit.py` pēc katras `pip install --upgrade twikit`.

**Verifikācija:** `python scripts/probe_x_cookies.py` — gaidāms `ok` visiem 4
endpointiem visiem slotiem.
```

- [ ] **Step 2: Pievienot CHANGELOG ierakstu `wiki/CHANGELOG.md` (sadaļa 2026-04-29).**

```markdown
### 2026-04-29 — Twikit Patch 5: SearchTimeline + UserTweetsAndReplies request shape
**Symptom:** `@mentions-monitor` un visu replies fetch 404'oja kopš ~2026-04-29 visiem 6 cookie slotiem.
**Cause:** X mainīja payload validāciju, prasot tagad `fieldToggles` (un papildu variables) tiem 2 endpointiem; `UserTweets` palika lenient.
**Fix:** `patch_twikit.py` Patch 5 pārraksta abu funkciju request shape. UserByScreenName + UserTweets nemainīti.
**Apdrošināšana pret atkārtošanos:** `probe_x_cookies.py` tagad testē visus 4 endpointus per slot, lai nākamajai drift detection tiktu agrīna.
```

- [ ] **Step 3: Saglabāt memory.**

`memory/project_twikit_search_replies_patch5.md`:
```markdown
---
name: twikit Patch 5 search/replies request shape
description: Pelietojama 2026-04-29 fix kad mentions/replies 404 visiem slotiem; UserTweets paliek lenient
type: project
---

2026-04-29: Patch 5 risināja SearchTimeline + UserTweetsAndReplies 404 visiem 6 cookie slotiem (UserTweets strādāja). Required fieldToggles + papildu variables iegūti no Task 0 X.com browser-cURL diff. Ja recurē, sākt ar `probe_x_cookies.py` un meklēt jaunus drift signāļus tieši šiem 2 endpointiem.

**Why:** Lai `@mentions-monitor` rutīna spētu darboties — tā ir dienas brief sastāvā un kompenses politiķu interakciju signāls.

**How to apply:** Ja nākotnē mentions/replies atkal 404, pirmais solis: `python scripts/probe_x_cookies.py`. Ja UserTweets strādā bet pārējie nē → drift uz tiem pašiem 2 endpointiem; refresh hashes (probably won't help) un atkārtot Task 0 browser capture, lai atrastu jaunu obligāto lauku.
```

- [ ] **Step 4: Commit.**

```bash
git add wiki/operations/twikit-notes.md wiki/CHANGELOG.md "../.claude/projects/C--Users-The-User-atmina/memory/project_twikit_search_replies_patch5.md" "../.claude/projects/C--Users-The-User-atmina/memory/MEMORY.md"
git commit -m "docs(twikit): document Patch 5 — search/replies 404 fix"
```

---

## Phase B: Architecture pivot (ja Task 0 atklāj nelabojamu auth-tier requirement)

**Trigger:** Task 0 diff parāda, ka X.com browseris kā non-premium konts arī NEVAR izpildīt SearchTimeline/UserTweetsAndReplies — tikai Blue/Premium konti var. Tad Phase A nav iespējama bez premium subscription.

### Task B1: Refactor `fetch_mentions` uz per-politician timeline scan

**Files:**
- Modify: `src/x_mentions.py:96-168`
- Modify: `src/x_mentions.py:23-46` (vairs nevajag `_build_mention_queries`)
- Test: `tests/test_x_mentions.py` (ja eksistē — pielāgot; ja nav — radīt)

**Stratēģija:** Strādājošā `UserTweets` endpoint-a vietā skenējam katru tracked politiķi un filtrējam viņu tweets pēc `@mention` teksta. Misses: trešo personu mentions; iegūst: visus mentions starp tracked politiķiem un visus, kuros tracked politiķis ir AUTORS.

- [ ] **Step 1: Failing test — verify timeline-scan strategy.**

```python
# tests/test_x_mentions.py
"""Unit test: fetch_mentions uses UserTweets per politician + text-filter."""
from unittest.mock import AsyncMock, MagicMock
import asyncio
from src import x_mentions


def test_fetch_mentions_via_timeline_scan(monkeypatch):
    # Mock pool + client.get_user_tweets to return 2 fake tweets, one mentioning another tracked
    fake_tweets_a = [
        MagicMock(
            id="100", full_text="Sveiki @evikasilina ko domājat?", created_at_datetime=None,
            user=MagicMock(screen_name="krisjaniskarins", name="K Kariņš"),
            lang="lv", reply_count=0, retweet_count=0, favorite_count=0,
        )
    ]
    fake_tweets_b = []  # no tweets

    fake_client = MagicMock()
    fake_client.get_user_tweets = AsyncMock(side_effect=[fake_tweets_a, fake_tweets_b])
    fake_client.get_user_by_screen_name = AsyncMock(return_value=MagicMock(id="USERID"))

    fake_pool = MagicMock()
    fake_pool.slot_count = 1
    fake_pool.get_next_slot.return_value = 0
    fake_pool.get_client.return_value = fake_client

    async def fake_get_pool():
        return fake_pool
    monkeypatch.setattr(x_mentions, "get_pool", fake_get_pool)

    handle_to_pid = {"krisjaniskarins": 1, "evikasilina": 2}
    mentions, errors = asyncio.run(
        x_mentions.fetch_mentions(handle_to_pid, limit=20)
    )
    assert errors == 0
    assert len(mentions) == 1
    assert mentions[0]["mentioner_handle"] == "krisjaniskarins"
    assert 2 in mentions[0]["mention_target_ids"]
    assert mentions[0]["opponent_id"] == 1
```

- [ ] **Step 2: Palaist testu — sagaidu FAIL (`fetch_mentions` joprojām search-based).**

```bash
.venv/Scripts/python -m pytest tests/test_x_mentions.py -v
```

- [ ] **Step 3: Pārrakstīt `fetch_mentions` uz timeline-scan.**

```python
# src/x_mentions.py — pilna jaunā implementācija
"""
X/Twitter mentions monitor (timeline-scan strategy).

X 2026-04-29 ierobežoja `SearchTimeline` ne-premium tier. Tā vietā skenējam
katra tracked politiķa pēdējos N tweets caur strādājošo `UserTweets` endpoint-u
un filtrējam @mention tekstu pret tracked-handle map.

Trade-off: zaudējam mentions FROM ne-tracked autoriem (piem., žurnālisti);
saglabājam visu starp tracked politiķiem + viņu pašu autorētos mentions.
"""
import asyncio
import logging
import time
from datetime import datetime

from twikit.errors import TooManyRequests, TwitterException

from src.x_pool import get_pool

logger = logging.getLogger(__name__)

REQUEST_DELAY = 2  # seconds between per-politician fetches


def _normalize_mention(tweet, handle_to_pid: dict[str, int]) -> dict:
    """Convert a twikit Tweet to a mention dict (unchanged from search-based)."""
    handle = tweet.user.screen_name if tweet.user else "unknown"
    display_name = tweet.user.name if tweet.user else "unknown"
    created = tweet.created_at_datetime
    text = tweet.full_text or tweet.text or ""

    mention_target_ids = []
    text_lower = text.lower()
    for h, pid in handle_to_pid.items():
        if f"@{h.lower()}" in text_lower or f"@{h}" in text:
            mention_target_ids.append(pid)

    author_pid = handle_to_pid.get(handle)
    opponent_id = author_pid

    if author_pid and author_pid in mention_target_ids:
        mention_target_ids.remove(author_pid)

    return {
        "id": str(tweet.id),
        "text": text,
        "created_at": created.isoformat() if isinstance(created, datetime) else (str(created) if created else None),
        "platform": "x_mention",
        "lang": getattr(tweet, "lang", None),
        "reply_count": getattr(tweet, "reply_count", 0) or 0,
        "retweet_count": getattr(tweet, "retweet_count", 0) or 0,
        "favorite_count": getattr(tweet, "favorite_count", 0) or 0,
        "source_url": f"https://x.com/{handle}/status/{tweet.id}",
        "mentioner_handle": handle,
        "mentioner_name": display_name,
        "opponent_id": opponent_id,
        "mention_target_ids": mention_target_ids,
    }


async def fetch_mentions(
    handle_to_pid: dict[str, int],
    limit: int = 20,
    batch_size: int = None,  # ignored — kept for backward signature compat
    delay: float = REQUEST_DELAY,
) -> tuple[list[dict], int]:
    """Fetch mentions via per-politician UserTweets timeline scan + text filter.

    Strategy: for each tracked handle, fetch their last `limit` tweets via the
    working `UserTweets` endpoint, then filter for tweets whose text mentions
    ANY OTHER tracked handle. The mentioning author becomes `opponent_id`,
    the mentioned subject(s) become `mention_target_ids`.

    Args:
        handle_to_pid: {handle: politician_id} mapping
        limit: max tweets per politician
        batch_size: ignored (legacy signature kept)
        delay: seconds between per-politician fetches

    Returns:
        Tuple of (deduplicated mention dicts, error count).
    """
    if not handle_to_pid:
        return [], 0

    pool = await get_pool()
    seen_ids: set[str] = set()
    all_mentions: list[dict] = []
    errors = 0

    # Resolve handles → user_ids first via working get_user_by_screen_name
    handles = list(handle_to_pid.keys())
    handle_to_uid: dict[str, str] = {}
    for handle in handles:
        try:
            slot = pool.get_next_slot()
            client = pool.get_client(slot)
            user = await client.get_user_by_screen_name(handle)
            handle_to_uid[handle] = user.id
        except Exception as e:
            logger.warning("fetch_mentions: handle resolution failed for @%s (%s)", handle, e)
            errors += 1
        await asyncio.sleep(0.5)

    # Per-politician timeline fetch
    for handle, uid in handle_to_uid.items():
        success = False
        for _retry in range(pool.slot_count):
            try:
                slot = pool.get_next_slot()
                client = pool.get_client(slot)
            except RuntimeError:
                logger.warning("fetch_mentions: all pool slots exhausted")
                errors += 1
                break

            try:
                tweets = await client.get_user_tweets(uid, "Tweets", count=min(limit, 40))
                success = True
                for tweet in tweets:
                    mention = _normalize_mention(tweet, handle_to_pid)
                    if mention["id"] in seen_ids:
                        continue
                    if not mention["mention_target_ids"]:
                        continue  # tweet doesn't mention anyone tracked
                    seen_ids.add(mention["id"])
                    all_mentions.append(mention)
                break
            except TooManyRequests as e:
                reset = e.rate_limit_reset if e.rate_limit_reset else time.time() + 60
                pool.report_rate_limit(slot, reset + 2)
                continue
            except TwitterException as e:
                logger.warning("fetch_mentions: slot %d API error on @%s (%s)", slot, handle, e)
                continue
            except Exception:
                logger.exception("fetch_mentions: unexpected error fetching @%s", handle)
                errors += 1
                break

        if not success:
            errors += 1

        await asyncio.sleep(delay)

    logger.info(
        "fetch_mentions: %d unique mentions across %d politiķi, %d errors",
        len(all_mentions), len(handle_to_uid), errors,
    )
    return all_mentions, errors
```

- [ ] **Step 4: Re-palaist unit test — sagaidu PASS.**

```bash
.venv/Scripts/python -m pytest tests/test_x_mentions.py -v
```

- [ ] **Step 5: Palaist visu testu komplektu — verificēt nav regresijas.**

```bash
.venv/Scripts/python -m pytest tests/ -v 2>&1 | tail -20
```

Expected: ≥ 859 passing (baseline + jaunais).

- [ ] **Step 6: Commit.**

```bash
git add src/x_mentions.py tests/test_x_mentions.py
git commit -m "fix(x_mentions): switch to per-politician timeline scan after SearchTimeline 404

X restricted SearchTimeline to premium tier ~2026-04-29. Pivot to scanning
each tracked politician's last N tweets via working UserTweets endpoint,
then filter for @mentions of other tracked handles. Trade-off: misses
mentions FROM untracked authors; preserves all tracked-to-tracked
interactions which is the contradiction signal we actually want."
```

### Task B2: Replies fetch — pārveidot uz `TweetDetail`

**Files:**
- Grep first: `grep -rn "user_tweets_and_replies\|UserTweetsAndReplies\|get_user_tweets.*Replies" src/`
- Modify: visi atrastie call sites

- [ ] **Step 1: Atrast visus `Replies` lietojumus.**

```bash
grep -rn "get_user_tweets.*['\"]Replies" src/ tests/
```

- [ ] **Step 2: Katram call site novērtēt:** vai vajag pilnu replies-tab vēsturi (tagad nav iespējams), vai pietiek ar `TweetDetail` konversācijas pavedienu konkrētam tweet ID.

  - Ja konkrēta tweet konversācija: aizvietot ar `client.get_tweet_by_id(tweet_id).replies` kas izmanto `TweetDetail`.
  - Ja vajag visu politiķa replies plūsmu: dokumentēt zaudējumu wiki, atslēgt loģiku.

- [ ] **Step 3: Smoke-test atjauninātās call sites caur unit test mock + manuāla integration probe.**

- [ ] **Step 4: Commit.**

```bash
git commit -m "fix(twitter): replace UserTweetsAndReplies fetch with TweetDetail conversation fetch

X restricted UserTweetsAndReplies to premium tier ~2026-04-29. Where we
previously pulled a politician's reply timeline, we now either (a) fetch
specific conversation threads via TweetDetail, or (b) drop the call where
full reply timeline is no longer essential."
```

### Task B3: Atjaunot wiki + memory (Phase B variants)

**Files:**
- Modify: `wiki/operations/twikit-notes.md`, `wiki/CHANGELOG.md`
- Create memory: `project_x_mentions_timeline_scan.md`, atjaunot `project_twikit_cookie_search_endpoint.md` ar pivot atzīmi

- [ ] **Step 1: Atjaunot `wiki/operations/operacijas.md`** — `@mentions-monitor` rutīna tagad apraksta jauno strategy un trūkstošo 3rd-party mentions blind spot.

- [ ] **Step 2: Atzīmēt CHANGELOG-ā Phase B fix.**

- [ ] **Step 3: Memory: jauns ieraksts par timeline-scan stratēģiju + atjaunot esošo `project_twikit_cookie_search_endpoint.md` (un `project_twikit_antibot_drift.md` kā related).**

- [ ] **Step 4: Commit.**

---

## Verification Acceptance Criteria

**Pirms uzskatīt par done:**

1. `python scripts/probe_x_cookies.py` rāda `ok` visiem 4 endpointiem visiem 6 slotiem (Phase A) **VAI** dokumentēts un akceptēts non-premium ierobežojums (Phase B).
2. `python -m pytest tests/ -v` 100% pass — ≥ 859 testi (e43d22e baseline) plus jaunie integration smoke + unit test.
3. Manuāli palaists `from src.social import fetch_all_mentions; print(fetch_all_mentions())` — atgriež `errors == 0` un nullā vai vairāk faktiskos mentions.
4. `python -c "from src.routine import print_routine; print_routine()"` neziņo par mentions step nedarbošanos.
5. wiki/CHANGELOG.md satur ierakstu par fixu.
6. memory satur project ierakstu ar root-cause + apply-recipe.

## Rollback Plan

**Ja Patch 5 sabojā UserByScreenName vai UserTweets (tagad strādājošos):**
```bash
.venv/Scripts/pip install --force-reinstall twikit==2.3.3
.venv/Scripts/python scripts/patch_twikit.py  # bez Patch 5 — tikai 1-4
git revert <patch5-commit>
```

**Ja Phase B refactor pasliktina mentions kvalitāti:**
- `fetch_mentions` aiz `feature_flag X_MENTIONS_STRATEGY = "search"|"timeline"` (atstājot abus codepaths līdz pārliecībai par jauno).

## Post-mortem Items

Pēc fix:

- [ ] Mērīt: cik mentions/dienā pirms vs pēc (ja Phase B). Sagaidu samazinājumu (3rd-party mentions zaudējums).
- [ ] Aktualizēt `data/x_cookies/manifest.json` `updated_at: 2026-04-29` ja Phase A pielietota.
- [ ] Apsvērt: vai pietiek ar 6 slotiem Phase B režīmā (per-politician fetch reizina request count × N_politicians).
