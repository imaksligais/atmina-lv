# @mentions-monitor

> Kanoniskais prompts (izpildei): [.claude/agents/mentions-monitor.md](../../../.claude/agents/mentions-monitor.md) — šī lapa ir īss apraksts cilvēkiem.

X/Twitter pieminējumu monitors.

**Ko dara:** Monitorē X/Twitter pieminējumus par izsekotajiem politiķiem, apkopo aktivitāti un ģenerē kopsavilkumu.

**Kad izmanto:** Dienas rutīnā pēc `fetch_all_twitter()` un `fetch_all_mentions()`.

**Ievade:** `fetch_all_mentions()` rezultāti no DB.

**Izvade:** Pieminējumu kopsavilkums, klasifikācija pēc kategorijām.

**Tehniski:** Izmanto XClientPool (5 cookie sloti; "6." izrādījās 2. slota dublikāts — sk. twikit-notes § 2026-06-14) ar round-robin rotāciju. **Strategy kopš 2026-06-12: default = `search`** (A/B uzvarētājs — ~5–7× ātrāk, 0 kļūdu); `timeline` (per-politician `UserTweets` scan + tekstuāls `@mention` filter, 2026-04-29 ieviesums pēc `SearchTimeline` noraidīšanas) paliek guardrail fallback + opt-in. `fetch_all_mentions()` VIENMĒR pēc `fetch_all_twitter()` (rate limit secība).

**Zināmais blind spot:** mentions FROM untracked autoriem (žurnālisti) netiek savākti, kamēr X TID generator nav atjaunots. Tracked-to-tracked interakcijas — pretrunu signāla pamats — saglabājas. Skat. `wiki/operations/twikit-notes.md` § 2026-04-29.

---
> Pilns aģenta prompts: `.claude/agents/mentions-monitor.md`
