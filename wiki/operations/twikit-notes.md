# twikit patches

Cookie-based X/Twitter auth library. atmina patches it locally to cope with X API drift.

## Reinstall procedure

Ja `twikit` tiek atjaunots (piem., `pip install -U`), patches pazūd. Atjauno ar:

```bash
.venv/Scripts/python.exe scripts/patch_twikit.py
```

## Ko tieši patch dara

1. **GraphQL endpoint hashes** — X rotē šos regulāri. Patches atjauno aktuālos `UserTweets`, `UserByScreenName` u.c. hash-us.
2. **FEATURES dict** — jaunās feature flag atslēgas, ko X gaida no klienta (ja trūkst, pieprasījumi atgriež 400).
3. **User object `core` field migration** — X pārvietoja `created_at`, `name`, `screen_name` no `legacy` uz `core`; patch pielāgo attribute lookup, lai kods nestrādātu tikai ar vecajiem response-iem.
4. **`ClientTransaction.init()` graceful fallback** (pievienots 2026-04-28) — X izņēma `ondemand.s` referenci no home page ~04-25, kā rezultātā `get_indices()` raise-o `Couldn't get KEY_BYTE indices`, atstājot `self.key` nesetotu. Patch wrapē init() try/except — sākotnējais ceļš paliek (gadījumā, ja X to atjauno), un uz exception fallback uz stub key/animation_key (32-char base64 stub). **2026-04-29 atklāts:** stub strādā tikai uz **lenient endpoints** (`UserTweets`, `UserByScreenName`); **strict endpoints** (`SearchTimeline`, `UserTweetsAndReplies`) noraida stub TID ar 404 (empty body). Skat. § 2026-04-29 zemāk.

## 2026-04-29: SearchTimeline + UserTweetsAndReplies 404 — TID strict validation

**Simptoms:** `@mentions-monitor` (caur `fetch_mentions` → `search_tweet`) un visi `get_user_tweets(uid, 'Replies')` izsaukumi atgriež `404 NotFound` ar **empty body** visiem 6 cookie slotiem. `get_user_by_screen_name` un `get_user_tweets(uid, 'Tweets')` strādā normāli.

**Diagnostikas signāli:**
- `x-rate-limit-limit: 50`, `x-rate-limit-remaining: 48` rate-limit headers IR redzami pat ar 404 — endpoint atpazīts, tikai request shape noraidīts.
- `scripts/patch_twikit.py --refresh` 2026-04-29 atgrieza identiskus hashes kā ielādētajā gql.py (queryId drift IZSLĒGTS).
- Variables/features mutāciju grids (7 varianti, ieskaitot fieldToggles no JS bundle) — neatrisina.
- **Pierādījums root-cause:** hardcodējot reālu browser `x-client-transaction-id` (no DevTools cURL capture), `SearchTimeline` strādā uzreiz. Patch 4 stub TID **selektīvi** noraidīts.

**Risinājums:** `src/x_mentions.py` pārstrādāts uz **per-politician timeline scan** caur strādājošo `UserTweets` endpoint + tekstuāls `@mention` filter (sk. `wiki/operations/agenti/mentions-monitor.md`). `Replies` produkts kodā vairs netiek izmantots.

**Trade-off:** mentions FROM untracked autoriem (žurnālisti, sabiedrība) vairs netiek savākti. Tracked-to-tracked interakcijas — pretrunu signāls — saglabājas pilnībā.

**Statuss 2026-05-16:** pēc Patch 5 (sk. § 2026-05-08) SearchTimeline atkal lietojams, bet `src/x_mentions.py` palika uz timeline-scan kā default, gaidot A/B. **ATRISINĀTS 2026-06-12:** pēc A/B (06-10..06-12, 0 kļūdu, ~5–7× ātrāk) default ir `search`; timeline = guardrail fallback + opt-in (sk. `wiki/CHANGELOG.md § 2026-06-12`). Augšminētais trade-off vairs neattiecas uz default ceļu.

**Long-term TODO:** ~~Reverse-engineer modern X TID generator~~ → **ATRISINĀTS 2026-05-08, sk. § zemāk.**

**Diagnostika nākotnē:** `.venv/Scripts/python.exe scripts/probe_x_cookies.py` testē visus 4 endpoint-us per slot. Ja atkal `UserTweets` strādā bet pārējie nē → tas pats simptoms, atgriezties pie šī ieraksta.

## 2026-05-08: Patch 5 — ondemand.s.js two-stage parser (real TID atjaunots)

**Korekcija pie 2026-04-29 diagnozes:** X **NEnoņēma** `ondemand.s` referenci no home page. X to **pārformatēja** 2026-03-18 — single-stage `"ondemand.s":"<hash>"` → divposmu `,<idx>:"ondemand.s"` ... `,<idx>:"<hash>"`. Twikit 2.3.3 regex vairs nesakrita.

**Patch 5 (`scripts/patch_twikit.py`)** pielieto upstream `d60/twikit#410` PR izmaiņas:
- `ON_DEMAND_FILE_REGEX` matches `,(\d+):["']ondemand\.s["']` (capture index).
- `ON_DEMAND_HASH_PATTERN = r',{}:"([0-9a-f]+)"'` — second-stage hash lookup pēc indeksa.
- `INDICES_REGEX = r"\[(\d+)\],\s*16"` (simplified, captures group 1).
- `get_indices()` pārrakstīts: find index → resolve hash → fetch `ondemand.s.<hash>a.js`.

Patch 4 try/except wrapper paliek kā safety-net — ja regex atkal driftē, fallback uz stub TID darbojas.

**Verificēts 2026-05-08:** 5/5 slot-i ražo reālu TID. `SearchTimeline`, `UserTweetsAndReplies`, `UserTweets` — visi strādā. `_replies_broken_slots` paliek tukšs.

**Pārskata signāls:** ja `client.client_transaction.key == "AAAA..."` pēc request-a, X atkal mainījis. Palaid `.venv/Scripts/python.exe scripts/patch_twikit.py --refresh`. Ja regex driftē, atjauno regex divus pattern-us patch_twikit.py.

**Saistītie:** commit `9d5a26a`, `wiki/CHANGELOG.md § 2026-05-08`, upstream PR https://github.com/d60/twikit/pull/410.

## 2026-06-12: Viena slota 404 uz user_replies + search_tweet — ~~novecojis ct0~~ ATSAUKTS 2026-07-25

> **ŠĪ SADAĻA BIJA NEPAREIZA. Nesāc ar ct0 refresh.** Skat. § 2026-07-25 zemāk — cēlonis ir klienta transaction atslēga, un tas tagad salabojas pats kodā. Sadaļa atstāta, jo tās kļūdainā argumentācija atkārtojās mēnešiem.

**Simptoms:** viens cookie slots atgriež `404 NotFound` tikai uz strict-TID endpointiem (`user_replies`, `search_tweet`), kamēr `get_user` + `user_tweets` strādā.

**Toreizējais secinājums (nepareizs):** „pārējie sloti veseli → tātad NE TID drifts, jo tas sit visus slotus vienādi" → novecojis `ct0`, refresh palīdz. Kļūda ir premisā: TID atslēgu būvē KATRS `Client` atsevišķi, tāpēc bojāta atslēga skar tieši vienu slotu, nevis visus. Refresh pēc tam „palīdzēja" tikai tāpēc, ka jauns process uzbūvēja jaunu klientu ar jaunu atslēgu — post hoc, ne cēlonis.

## 2026-07-25: STRICT-404 īstais cēlonis — slikta transaction atslēga bootstrapā

**Cēlonis:** katrs twikit `Client` izveido `x-client-transaction-id` atslēgu VIENREIZ (pirmajā pieprasījumā, no X mājaslapas) un kešo uz visu klienta mūžu. Daļa bootstrapu dod atslēgu, ko X noraida: STRICT endpointi atbild ar tukšu 404, LENIENT to nepārbauda. Tāpēc slots izskatās pa pusei dzīvs, un „bojātais" slots lec starp skrējieniem — katrs process būvē jaunus klientus.

**Izslēgts ar mērījumiem:** novecojis ct0 (bojātais slots lec bez sīkfailu maiņas; vecais ct0 pēc tam iet 4/4) · twikit stub fallback (kritējam bija īsta atslēga, bez izņēmuma) · konts (3 svaigi klienti ar tiem pašiem sīkfailiem — visi gāja) · katra pieprasījuma nejaušība (viens klients 5/5 kritienu) · rate limits (404 atbildēs `x-rate-limit-remaining: 482/500`, tukšs ķermenis, 10 ms). **Izšķirošais:** apļveida tests 1→2→3→4→5 ar iesaldētiem klientiem — 75 s garumā viena slota klients krita 10/10 apļos, pārējie četri gāja 10/10 tajās pašās sekundēs (kolonna, ne rinda).

**Fix (kodā, automātisks):** `src/x_pool.py::reset_transaction_key()` notīra kešoto bootstrapu → twikit uzbūvē jaunu atslēgu; kritējs atgūstas pēc 1–3 pārbūvēm (3/3 reproducēts). Lietots `x_scraper.fetch_user_replies` (slotu nosoda tikai pēc `TRANSACTION_KEY_ATTEMPTS=4` neveiksmēm), `x_mentions._probe_search_slot_health` (pārbūve pirms slota skaitīšanas par neveselu) un `scripts/probe_x_cookies.py`.

**Diagnostikas secība slot-404 gadījumā (2026-07-25 redakcija):**
1. **Palaid `.venv/Scripts/python.exe scripts/probe_x_cookies.py` un izlasi rindu `transaction key: recovered after N rebuild(s)`.** Ja tā parādās un slots ir OK — nekas nav jādara, tā ir normāla pašatgūšanās.
2. Slots joprojām BROKEN pēc 4 pārbūvēm → tikai TAGAD skaties uz sīkfailiem. **ct0 maina PĀRĪ ar `auth_token` no tās pašas pārlūka sesijas** — tikai ct0 dod `403 code 353 "This request requires a matching csrf cookie"` (2026-07-25 mācība).
3. VISI sloti krīt → TID ģeneratora drifts, `.venv/Scripts/python.exe scripts/patch_twikit.py --refresh` + § 2026-04-29/05-08.
4. Pārejošs pēc `fetch_all_twitter` slodzes → rate-limit izsmelšana, nogaidi 15 min logu (guardrail `fetch_mentions` iekšā tāpat atkritīs uz timeline).

**Saistītie:** `wiki/CHANGELOG.md § 2026-07-25 — twikit STRICT-404 cēlonis`, commit `2ee98668`.

## Kad šis trūkst, simptomi

- `KeyError: 'core'` vai `AttributeError: 'NoneType' object has no attribute 'screen_name'`
- 400 Bad Request no GraphQL endpoint-a
- `AttributeError: 'ClientTransaction' object has no attribute 'key'` (Patch 4 trūkst)

## Skatīt arī

- `data/x_cookies.json` — auth, gitignored. `auth_token` + `ct0` ir kritiskie. Ja expire, ekstrahē no pārlūka DevTools.
- `src/social.py` — `fetch_all_twitter()` + `fetch_all_mentions()` izsaukumi. Pēdējais jāpalaiž pēc pirmā rate limit secības dēļ.
