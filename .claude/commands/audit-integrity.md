---
name: audit-integrity
description: Read-only DB integrity sweep — matcher-collision risks (≤4-char forms), x_handle↔social_accounts divergence, orphaned contradiction refs, aging unreviewed/unconfirmed rows, stale-party language, party↔faction-record divergence, same-day duplicate claims, missing brief-image variants, truncated stubs, unresolvable provenance URLs + hand-written-row signatures. Emits a triage table + BACKLOG-ready blocks; fixes only with operator approval + paired rollback.
argument-hint: "[matcher|stale|orphans|briefs|all] [--fix]"
---

# Audit integrity — datu integritātes pārbaude

Run the read-only sweep over the scope in `$ARGUMENTS` (default `all`). Report findings; apply NOTHING without operator approval.

## Why this shape

The worst failures here return success: silent idempotency merges leave `failures` empty, denormalized fields go stale without any signal, and false junctions sit until someone happens to reread the doc. Historically these were caught only by ad-hoc consistency audits (that is how the Vergina stale-party bug and the aging `reviewed=0` contradictions surfaced). A scheduled sweep converts "noticed by luck" into "reported every run". Core queries validated against the live DB 2026-07-07 — the first run already surfaced 10 active politicians with ≤4-char forms (incl. the known Kols case) and one live x_handle divergence (id=62).

**Honest scope limit:** the T2 silent idempotency merge is invisible post-hoc by definition (the second claim never lands in the DB) — it can only be caught at extraction time via stored-count == intended-count (CLAUDE.md T2). This audit covers the closest detectable proxy (same-day cross-source duplicates) instead.

## Checks

1. **Matcher collision risk (T1).** For every active politician, list stored `name_forms` ≤4 chars AND generated forms ≤4 chars (apply `src/matcher.py::_latvian_surname_inflections` to each surname form). For each, sample-grep recent `documents.content` to show what it currently collides with. Output candidate `negative_patterns` — proposals only. Since the 2026-07-27 B2+D2+H package, single-word forms only match at word boundaries, so a ≤4-char form is a namesake risk rather than a substring bomb — keep flagging, but say which class.

   1b. **B2-veto journal (FP/FN candidate feed).** Re-run the matcher over the last 14 days of docs with the `veto_log` observability hook and tabulate every candidate the foreign-first-name veto discarded. Read the table BOTH ways: a tracked politician repeatedly vetoed next to the same capitalised token = coverage bug candidate (missing closed-class stop word or name-token declension — the "Pēcāk Ratnieks" class); a namesake vetoed = the guard working, and a NEW recurring namesake first name = full-name-twin early warning (the class code cannot fix — Bērziņš). Proposals only; `negative_patterns` / `_VETO_STOP_WORDS` additions are operator-review changes.

   ```python
   # read-only; ALWAYS .venv/Scripts/python.exe, run from repo root
   import sqlite3, sys, collections, logging
   sys.path.insert(0, ".")
   logging.getLogger("src.matcher").setLevel(logging.ERROR)  # mute ambiguity warnings
   from src.matcher import match_politicians, _clear_politician_cache
   from src.db import lv_cutoff
   _clear_politician_cache()
   db = sqlite3.connect("file:data/atmina.db?mode=ro", uri=True)
   db.row_factory = sqlite3.Row
   docs = db.execute(
       "SELECT id, content FROM documents WHERE scraped_at >= ? AND content IS NOT NULL",
       (lv_cutoff(14),)).fetchall()
   names = {r["id"]: r["name"] for r in db.execute("SELECT id, name FROM tracked_politicians")}
   db.close()
   by_pair = collections.defaultdict(list)   # (pid, preceding) -> [(doc, snippet)]
   for d in docs:
       log = []
       match_politicians(d["content"], veto_log=log)
       for e in log:
           by_pair[(e["pid"], e["preceding"])].append((d["id"], e["snippet"]))
   for (pid, prec), hits in sorted(by_pair.items(), key=lambda kv: -len(kv[1])):
       print(f"{names.get(pid, pid)} | veto pie '{prec}' | {len(hits)} doki | piem. {hits[0][0]}: {hits[0][1][:90]!r}")
   ```
2. **x_handle divergence.** `tracked_politicians.x_handle` vs active `social_accounts.handle` (`platform='twitter'`), case-insensitive mismatch.
3. **Orphans.** Contradictions whose `claim_old_id`/`claim_new_id` no longer resolve; `position` claims on `relationship_type='inactive'` politicians (informational — audit trail is expected, flag counts only).
4. **Aging review queues.** `contradictions` with `reviewed=0` older than 14 days; `confirmed=0` survivors (deep-check output) older than 30 days **AND `reviewed=0`** — a `reviewed=1 confirmed=0` row is a documented rejection that legitimately sits at confirmed=0 forever (#40 Judins is the reference: its summary carries its own verdict, and the unfiltered query re-flagged it on 2026-08-04 as if it were queue debt); open review claims older than 14 days.

   **Query `claims.review_status`, never `reasoning` text.** Since 2026-08-03 the flag is a column, derived from `reasoning` by two triggers (INSERT + UPDATE OF reasoning) so ad-hoc triage SQL cannot desynchronise it. Any `LIKE` against the prose is now a bug: the marker's spelling drifted three times and its position drifts per-agent, which is exactly why `LIKE 'NEEDS_REVIEW%'` once returned 20 of 119 rows and read as a short queue.

   ```sql
   SELECT CASE WHEN julianday('now') - julianday(created_at) > 30 THEN '>30d'
               WHEN julianday('now') - julianday(created_at) > 14 THEN '15-30d'
               WHEN julianday('now') - julianday(created_at) > 7  THEN '8-14d'
               ELSE '<=7d' END AS vecums,
          COUNT(*)
   FROM claims WHERE review_status = 'needs_review'
   GROUP BY 1 ORDER BY 2 DESC;
   ```

   **Baseline 2026-08-03: `needs_review=119` (76 at ≤7d, 43 at 8–14d, none older), `reviewed=234`.** Report the full distribution, not just the flagged bucket — the point of the column is that the queue finally has a denominator and an age.

   Sanity line worth keeping in the run, because it is the one thing that would prove the triggers stopped firing: `SELECT COUNT(*) FROM claims WHERE (review_status='needs_review') != (reasoning LIKE '%NEEDS_REVIEW%')` must be **0**.
5. **Stale party language (T6).** Claims from the last 30 days in topic `Koalīcija un partijas` whose stance/reasoning contains exit/switch language (`izstāj%`, `pamet%`, `pāriet%`, `jaunu partiju%`) where `tracked_politicians.party` is unchanged since before `stated_at` — cross-check candidates for manual party UPDATE.
6. **Same-day duplicates.** Same `(opponent_id, topic, DATE(stated_at))` with different `source_url` and near-identical stance (the Kulbergs X+LETA class) — trim candidates.
7. **Brief image variants — read DB→disk, not disk→DB.** For every `brief_images` row with `approved=1`, require all four `src.image_variants.VARIANTS` filenames under `output/atmina/` (strip a leading `atmina/` from `image_path` first; never require the source PNG — those live in `output/images/briefs/` and are not deployed). Baseline 2026-08-04: **checked=138 flagged=0**, with buckets `-1`×4, `0`×32, `1`×138, `2`×71.

   **Always read the flag count together with the bucket line** — the checked set itself can move under the check. The 2026-08-02 baseline was `137/2` (ids 93, 96, hero + `og:image` 404 live); on 2026-08-04 the run read `138/0` and was initially misread as "the two are repaired". They were not — both rows had moved to `approved=2`, out of the checked set. `approved=2` semantics, measured 2026-08-04: retired candidate (40 of 44 such notes carry an `approved=1` replacement; the 4 without one — incl. 93/96 — have their pages re-rendered onto the site fallback `og:image`, so a 2-only note is a legitimate no-image state, not a defect). A bucket shift between runs is the signal to investigate; a bare green is not evidence the old flags were fixed.

   This check used to scan the other way — "PNGs under `output/atmina/images/briefs/` without a `-hero.webp` sibling" — which put exactly **one** file in the candidate set, and that one had its sibling. It therefore reported clean forever while the dead DB rows stayed invisible. Worse than an absent check, because "`/audit-integrity` clean" was being read as evidence. Keep the disk scan only as a documented second direction.

   ```python
   from pathlib import Path
   from src.db import get_db
   from src.image_variants import VARIANTS, variant_filename
   out = Path("output/atmina")
   total = flagged = 0
   for r in get_db().execute(
       "SELECT id, note_id, image_path FROM brief_images WHERE approved=1 ORDER BY id"
   ):
       total += 1
       rel = Path(r["image_path"].removeprefix("atmina/"))
       missing = [
           v for v in VARIANTS
           if not (out / rel.with_name(variant_filename(rel.name, v))).exists()
       ]
       if missing:
           flagged += 1
           print(f"#{r['id']} note={r['note_id']} {rel} -> trūkst {missing}")
   buckets = get_db().execute(
       "SELECT approved, COUNT(*) FROM brief_images GROUP BY approved"
   ).fetchall()
   print(f"checked={total} flagged={flagged} buckets={[tuple(b) for b in buckets]}")
   ```

   Print the `checked=` total, not only the flags: a run that silently checked 0 rows is the failure mode this check was rewritten to escape.
8. **Truncated stubs.** Unreviewed `documents` with `word_count < 80` (pmo.ee paywall class) — re-ingest candidates, NOT extraction targets.
9. **Party ↔ Saeima faction record (T6, wrong-from-the-start variant).** Check 5 only fires when a claim *says* someone switched; a `party` that was wrong the day it was seeded never produces such a claim and can sit for months. Cross-check against the vote record instead: for every active politician, emit the faction timeline (`label, n, first, last`) when their party's `short_name` covers **<20 %** of their faction-labelled ballots. Skip parties whose `short_name` never appears as a faction label at all — alliances (AS members carrying LZP/LRA) and non-Saeima parties are silent by construction, not findings.

   ```sql
   SELECT tp.id, tp.name, tp.party, iv.faction, COUNT(*) n,
          MIN(v.vote_date) first, MAX(v.vote_date) last
   FROM tracked_politicians tp
   JOIN saeima_individual_votes iv ON iv.politician_id = tp.id
   JOIN saeima_votes v ON v.id = iv.vote_id
   WHERE tp.relationship_type != 'inactive' AND iv.faction IS NOT NULL
   GROUP BY tp.id, iv.faction ORDER BY tp.id, first;
   ```

   Label landscape since 2026-08-04: exactly one label per faction — the `ST!`/`ST` split (titania's own cell format drifted) was normalized to `ST` in data AND at the parser (`src/saeima/votes.py` `faction_normalize`), so a politician whose coverage computes low against `parties.short_name` is a real signal again, not a label artifact. If a NEW label variant ever appears, extend `faction_normalize`, don't special-case queries.

   **Triage by coverage inside the most recent labelled sitting window** — `rows with that label / total votes in the window`, NOT the politician's own row count (that denominator hides absences and makes a 17-row artifact look like 94 % certainty):
   - dense (≳80 %) and different from `party` → real switch, the field is stale → propose UPDATE + paired rollback;
   - thin, isolated (≲30 %) → scraper artifact, do not trust the label;
   - no label at all + `role` says "ārpus frakcijām" → expected, not a finding.

   **Worked reference (run 2026-07-26, 119 politicians with ≥50 labelled ballots, 4 flagged).** In the 2026-03-26…04-01 window (70 votes) Ābrama (id 77, ZZS 65/70), Kiršteins (96, LPV 57/70) and Ceļapīters (145, ZZS 65/70) matched their current `party` — genuine switches away from PRO/NA/JV, **leave them alone, they will flag again every run**. Šmits (150) carried `party='Stabilitātei!'` on 17/70 against 1 668 lifetime AS ballots and was the only defect — fixed via `data/{fix,rollback}_smits_party_2026-07-26.sql`.

10. **Provenance that resolves to nothing + hand-written-row signatures.** Every store function validates provenance before writing; a raw `INSERT` skips that. This check looks for rows that could not have come through the front door. Added 2026-07-30 after `political_tensions` #175: registered during a Claude outage with several session restarts, it cited a tweet status ID that appears in **no** document — exactly the guessed-ID class `store_tension()` raises `ValueError` on (`src/db.py:868`). It sat in a published brief's Spriedžu table. Nothing in the routine status showed it; the audit query found it across all 157 rows in seconds.

    All four queries validated against the live DB 2026-07-30 and **all returned 0** after the #175 fix — that is the clean baseline, so any non-zero result is a finding, not noise.

    ```sql
    -- A. tension source_url that no document carries (store_tension bypassed)
    SELECT t.id, substr(t.created_at,1,19) AS created_at, t.source_url
    FROM political_tensions t
    WHERE COALESCE(t.source_url,'') <> ''
      AND NOT EXISTS (SELECT 1 FROM documents d WHERE d.source_url = t.source_url)
    ORDER BY t.id DESC;

    -- B. a claim citing a URL other than its own provenance document's
    SELECT c.id, c.claim_type, c.document_id, c.source_url, d.source_url AS doc_url
    FROM claims c JOIN documents d ON d.id = c.document_id
    WHERE c.document_id IS NOT NULL
      AND COALESCE(c.source_url,'') <> COALESCE(d.source_url,'');

    -- C. saeima_vote claim whose source_url matches no saeima_votes.url
    SELECT c.id, c.source_url FROM claims c
    WHERE c.claim_type = 'saeima_vote' AND COALESCE(c.source_url,'') <> ''
      AND NOT EXISTS (SELECT 1 FROM saeima_votes v WHERE v.url = c.source_url);

    -- D. LV timestamp in a UTC-default column (bind ? = UTC now, not LV now)
    SELECT id, created_at FROM political_tensions WHERE created_at > ?
    UNION ALL SELECT id, created_at FROM analyses WHERE created_at > ?;
    ```

    Triage: A/B/C are **defects, not judgement calls** — a citation nobody can follow is unpublishable, so check whether the row's substance is backed by a stored claim and either repoint the URL at the real document or delete the row (paired rollback either way; #175 was repointed because claim #555782 backed it). For D, keep the limit in mind: comparing against UTC-now only catches a stamp written **within the last 3 hours**, i.e. the current session. Older hand-written rows are not detectable this way — an hour-of-day heuristic does not separate them (10 tension rows sit at ≥21:00 and all but #175 are ordinary UTC evening writes). So D is a same-session tripwire, not a historical audit. Convention itself: `political_tensions.created_at` and `analyses.created_at` are UTC; `claims`/`context_notes`/`documents` are LV via `now_lv()` (`src/schema.sql` documents it at the column).

11. **Datu kontrakts #4b vienādība (viena rinda, nulles interpretācija).** `COUNT(*) WHERE claim_type='saeima_vote'` **must equal** `COUNT(DISTINCT opponent_id, source_url, topic)`, because the contract promises one vote claim per cast ballot. Any delta is a duplicate set. There is no threshold and no judgement call here — the numbers match or they do not.

    ```sql
    SELECT COUNT(*) AS total,
           COUNT(DISTINCT opponent_id || '|' || source_url || '|' || topic) AS distinct_triples,
           COUNT(*) - COUNT(DISTINCT opponent_id || '|' || source_url || '|' || topic) AS delta
    FROM claims WHERE claim_type = 'saeima_vote';
    ```

    **Baseline 2026-08-02 (after cleanup): total 568 724, delta 0. The expected value is now 0 — any nonzero is new damage, not the known backlog.** The 4 087 duplicates were deleted on 2026-08-02 (`data/fix_dup_saeima_vote_claims_2026-08-02.sql`, paired rollback + snapshot `atmina.db.pre-dup-cleanup-20260802.db`). Cause, settled 2026-08-02 against the `atmina.db.pre-vote-url-fix-20260427` snapshot: the duplicates were not an idempotency bypass but two hand-run `UPDATE claims SET topic` migrations that **merged triples `store_claim()` would never have accepted** — `fix_claims_votes_topic_drift_2026-06-13.sql` for 3 991 groups and `fix_motif_topic_coverage_2026-06-12.sql` for the remaining 91. A topic UPDATE can manufacture duplicates where the write path cannot.

    **Know this check's blind spot before you trust a green.** It compares key collisions, not row duplication, so it reads clean at the moment the damage is done. The rows were physically doubled on **2026-05-27**, when a P3 re-run wrote a second full claim set for **46 of 64 April vote URLs** — but their topics still differed then, so this query's delta would have been ~0 through May and all of June. It only lit up once the June migrations aligned the topics. Duplication that leaves the key distinct is invisible here; **check 14 is the one that sees it, and it fires the same day.**

12. **`mentioned` runātājs, kas nekad nenonāk ekstrakcijas rindā.** `get_pending_politicians` walks `role='subject'` only, so a document whose ONLY quoted speaker carries `role='mentioned'` is never extracted — and because `reviewed_at` is per-DOCUMENT rather than per-politician, it looks processed. Read-only detector; a hit is a candidate, not a defect.

    Measure with `src.matcher._load_politician_forms` + `_occurrences` (matcher semantics, not a naive `LIKE`), scoping to `platform='web'` and the last 90 days: a politician "speaks" if one of their **nominative** forms falls within ~60 characters of a quotation cue (`teica`, `sacīja`, `norādīja`, `uzsvēra`, `pauda`, `atzina`, `apliecināja`, `aģentūrai LETA`, `intervijā`, `raidījumā`, …). Flag documents where some `mentioned` politician speaks and no `subject` politician does.

    **The nominative restriction is load-bearing, not a detail** — the all-forms version misses doc 78085, the reference case. **Baseline 2026-08-02: 282 of 1897 documents (14.9 %), ~1.4 per day.** Do NOT attribute this to LETA: LETA-marked documents are *less* often affected (10.9 % vs 17.9 %), so it is ordinary Latvian news structure — the article opens with the official it is about, and the quoted politician arrives later.

13. **`claim_vectors` novecošana.** `store_claim()` embeds `f"{topic}: {stance}"` and `embed_text` is deterministic, so recomputing and comparing bytes against the stored vector is a clean pass/fail — no threshold, no interpretation. Escalation rule 8 requires a re-embed after any hand edit of `topic`/`stance`, and a bare `UPDATE` raises nothing — `search_similar_claims` simply keeps ranking the claim by what it used to say.

    ```bash
    .venv/Scripts/python.exe scripts/audit_vector_staleness.py
    ```

    Default candidate set = every claim id a `data/fix_*.sql` file has touched in an EMBEDDED field (`stance`/`topic`/`quote`; `reasoning` edits cannot stale a vector and are excluded). Explicit sets via `--ids-from` / positional ids. Exit 0 clean · 1 stale found · 2 method unverified.

    **The control set is part of the method, not a nicety.** A broken compare reports EVERYTHING stale — the inverted gate-that-cannot-fail. The script self-verifies against `data/reembed_elektr_vectors_2026-08-03.ids` (re-embedded and byte-verified 08-03/08-04): a failing control marks the whole run as a method artifact (exit 2), and an all-stale sweep WITHOUT a control is refused the same way. An all-stale sweep WITH a passing control is a legitimate finding — that was the real shape of the 06-13 remainder (167/167 stale, closed 2026-08-04).

    **Baseline 2026-08-04 (after the 06-13 and audit-13 re-embeds): `checked=54 match=54 stale=0 missing=0`, control `25/25`.** Expected value is 0 — any stale row is a hand edit that skipped escalation rule 8's re-embed step. Tests: `tests/test_audit_vector_staleness.py` (hermetic — fake embed, plain-table stand-in).

14. **`saeima_vote` claims PER VOTE vs cast ballots.** Data Contract #4b promises one claim per cast ballot. Check 11 tests that promise globally and through the idempotency key, which is why it stays silent while a re-load doubles rows whose topics differ (see its blind spot). This is the per-vote form of the same promise, and it fires on the day the rows land — no threshold, no judgement call.

    ```sql
    WITH b AS (
        SELECT vote_id, COUNT(*) AS ballots
        FROM saeima_individual_votes
        WHERE vote IN ('Par','Pret','Atturas','Nebalsoja')
        GROUP BY vote_id
    ), c AS (
        SELECT source_url, COUNT(*) AS claims
        FROM claims WHERE claim_type = 'saeima_vote'
        GROUP BY source_url
    )
    SELECT v.id, v.vote_date, b.ballots, COALESCE(c.claims, 0) AS claims,
           ROUND(COALESCE(c.claims, 0) * 1.0 / b.ballots, 2) AS ratio
    FROM saeima_votes v
    JOIN b ON b.vote_id = v.id
    LEFT JOIN c ON c.source_url = v.url
    WHERE COALESCE(c.claims, 0) != b.ballots
    ORDER BY ratio DESC, v.vote_date;
    ```

    Aggregate both sides first, as written — `claims.source_url` has no index, so the correlated-subquery form of this query crawls while this one runs in ~1 s over the whole table.

    **Read the ratio, not the difference.** Exactly `2.0` = the vote was loaded twice. Below `1.0` = claims are missing, which is the partial-write signature (`store_vote()` commits BEFORE claim generation, so a wrong interpreter or a mid-run crash leaves votes without their claims — CLAUDE.md § Commands). Just above `1.0` = usually a deputy seeded after the load. `0` claims on a vote with ballots = generation never ran.

    **Baseline 2026-08-02 (after cleanup): `checked=6465 flagged=0`. Expected value is 0.** Before the cleanup this read `flagged=49` — 39 at exactly 2.0 (2026-03-26 ×28, 2026-04-01 ×11), excess 4 087 rows accounting for 100 % of check 11's delta. **`missing` was 0 then and must stay 0**, and that is the number to watch after every bulk ingest: it is the only line in this file that clears `store_vote()` of partial writes across the whole table.

    Run it over the FULL table **before and after every bulk ingest** — it is the cheapest gate that would have caught the 2026-05-27 event in May instead of in August.

15. **Junction role INVERSION — the quoted speaker is linked `mentioned`.** `get_pending_politicians` builds the extraction queue from `role='subject'`, so a politician linked `mentioned` never enters it, even when they are the article's only quoted source. The document is then stamped `reviewed_at` with zero positions and looks processed by every indicator we have. This is the mirror of check 2's class: there a slot sticks without a speaker, here a speaker is left without a slot.

    ```bash
    .venv/Scripts/python.exe scripts/audit_junction_role_inversion.py --days 90
    ```

    The discriminator is grammatical, not lexical: Latvian puts the speaker of "X teica" in the NOMINATIVE, so an oblique form beside the same verb ("par Xu teica") marks the person as the topic instead. The naive all-forms version does not flag doc 78085, the case that opened the class — `tests/test_audit_junction_inversion.py` locks that discrimination directly.

    **Baseline 2026-08-03: `checked=1273 flagged=280 (22.0 %)`.** Read the rate, not the count: the flag count is stable, the denominator is what people get wrong.

    **Correction to the recorded figure.** The ad-hoc 2026-08-02 measurement reported 282 / 1897 = 14.9 %. The flag count reproduces (280 vs 282, one day of drift), but **1897 counted documents whose only `mentioned` entity is an organization** — those cannot produce a human-speaker inversion, so they can never fire and only pad the base. Reproducing that padded candidate set today gives 1822, which is where 1897 came from. Excluding them is the honest denominator, and the class is therefore **~1.5× worse than BACKLOG records**, not better. This is the same defect the file warns about in its own header: a number is trustworthy only with the query that produced it.

    Proposals only. Nothing here changes a role — see BACKLOG § "Junction lomas apgrieztas" for the three fix candidates (a/b/c) and their measured cost; the queue-side fix runs ~1.4 extra extraction units/day. **Note the adjacent semantics that masked this class: `reviewed_at` is per-DOCUMENT, not per-politician**, so a document reviewed in one politician's slot looks finished even when another politician's position in it was never touched.

16. **Non-canonical `daily_brief` topic prefix.** `context_notes.topic` is the key every brief lookup filters on, and a wrong string does not raise — it just returns fewer rows. Four forms had accumulated (`dienas analīze` canonical, `dienas pārskats`, `dienas parskats` without diacritics, and a bare `daily`), so `LIKE 'dienas analīze %'` saw 70 of 119 rows and skipped 49 in silence. This is the same class that made the Telegram summary permanently empty and that the `NEEDS_REVIEW`/`REVIEWED` marker drift produced twice more; the point of this check is to catch form number five while it is one row, not forty-nine.

    ```sql
    SELECT COUNT(*) AS checked,
           SUM(topic NOT LIKE 'dienas analīze %') AS flagged
      FROM context_notes WHERE note_type = 'daily_brief';

    SELECT id, topic, created_at FROM context_notes
     WHERE note_type = 'daily_brief' AND topic NOT LIKE 'dienas analīze %'
     ORDER BY id;
    ```

    Never hand-write the prefix when fixing: `src.briefs.daily_brief_topic(date)` produces it, and the day itself comes from `src.briefs.brief_subject_date(topic, content, created_at)` — H1 fallback included, because a legacy row's own topic may not carry the date at all (id 192 was literally `daily`).

    **Baseline 2026-08-04: `checked=119 flagged=0`. Expected value is now 0.** The long-standing single permitted flag — id=131, `dienas pārskats 2026-04-14`, the same brief as id=135 stored twice — was **deleted 2026-08-04 with operator approval** (rollback `data/rollback_brief131_dedup_2026-08-04.sql`; its `approved=1` image row #4 went in the same transaction, because `brief_images.note_id` is a FK and would have dangled). Until then the expected value was exactly 1, and a `flagged=0` reading meant someone had deleted the row unrecorded — that history is why this paragraph documents the deletion explicitly. Any nonzero reading now means a new topic form has appeared.

17. **Re-scraped web documents that no longer contain a stored quote.** URL-first dedup rewrites `documents.content` in place when a publisher edits an article (CLAUDE.md § Schema invariants — `scraped_at` is mutable for `platform='web'`), so a verbatim `quote` captured earlier can silently lose its source text — and `validate_quote_against_source()` deliberately passes this class ("cannot verify" → allow), so nothing else will ever flag it. The class moves in BOTH directions: a later re-scrape can also restore text (#11210 flagged on 2026-08-03, findable again on 2026-08-05).

    Method (run verbatim; SQL narrows candidates, Python does the folded containment test):

    ```python
    # kandidāti: citāti uz web dokiem, kas pārskrāpēti PĒC claim izveides
    # (abas kolonnas LV laikā — tieša salīdzināšana ir pareiza)
    # SELECT c.id, c.quote, d.content FROM claims c
    #   JOIN documents d ON d.id = c.document_id
    #  WHERE c.quote IS NOT NULL AND c.quote != ''
    #    AND d.platform = 'web' AND d.scraped_at > c.created_at
    # karogs: norm(quote) not in norm(content), kur norm = diakritiku
    # salocīšana + tipogrāfisko pēdiņu normalizācija + lower + \s+ sabrukums
    ```

    **Baseline 2026-08-05: `checked=30 flagged=11`** (no 1 418 web citātiem kopā). The 11 known/accepted ids: 7481, 18095, 18096, 18377, 20450, 20538, 20802, 548162, 548267, 548268, 555829 (#555824 repaired against the new revision 2026-08-03 — the Butāna precedent; #11210 self-healed by a later re-scrape). A flagged id OUTSIDE this list means a fresh re-scrape ate another quote — triage it per-quote (repair against the new revision, or accept and add here with the date); never batch-fix, and never "correct" the quote's spelling.

## Output

- One triage table (check · count · top examples with ids).
- **Every row carries its denominator** — `checked=N flagged=M`, never `M` alone. Three of the checks in this file have at some point reported a confident all-clear while structurally unable to fire (check 7 scanned a directory holding one file; two `wiki_lint` checks read frontmatter keys nothing writes). A green without its denominator is not evidence, and it is worse than no check, because it stops people looking.
- For each non-empty class: a paste-ready BACKLOG.md block in the house `[OPEN]/[FIX] + apraksts + operatora review` style, so findings survive the session.
- Log the run: `db.log_action(action='integrity_audit', ...)`.

## Guardrails

- **Default read-only.** `--fix` applies ONLY items the operator approved one-by-one, each with a paired `data/rollback_*.sql`, in one transaction.
- Never auto-add `negative_patterns`, never change `party` — propose, don't apply (standing rule; CLAUDE.md Working Conventions).
- Findings in LV where they become stored text; grammar gate applies.
- Cadence: weekly-routine step + on demand before big publishes. Full sweep is cheap (read-only, <1 min).
