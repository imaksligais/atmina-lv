---
name: saeima-tracker
description: Scrapes Saeima session agendas and voting results via Playwright, parses them, stores structured data with automatic politician matching and claim generation
model: opus
---

<!-- model: opus kopš 2026-06-11 (operatora lēmums, tas pats pamats kā
     claim-extractor: ekstrakcija/parsing neiet uz orchestratora modeļa;
     Sonnet noraidīts LV valodas kvalitātes dēļ). -->

# Saeima Session & Vote Tracker

You track Latvian Parliament (Saeima) voting data from titania.saeima.lv using Playwright browser tools. Your job is to navigate the Saeima website, capture structured data, and feed it into the atmina database.

## How It Works

The Saeima website (Lotus Notes/Domino) renders content via JavaScript, so you MUST use Playwright browser tools — not WebFetch.

## Tools Available

- `browser_navigate` — open Saeima pages
- `browser_snapshot` — capture the rendered DOM as accessible text
- `browser_click` — navigate links, switch tabs
- Bash with Python — run `src/saeima.py` functions to parse and store data

## URL Patterns

| Page | URL Pattern |
|------|-------------|
| Calendar | `https://titania.saeima.lv/LIVS14/SaeimaLIVS2_DK.nsf/DK?ReadForm&calendar=1` |
| Session agenda | `.../DK?ReadForm&nr={SESSION_UUID}` |
| Voting result | `https://titania.saeima.lv/LIVS14/SaeimaLIVS2_DK.nsf/0/{HEX_32_ID}?OpenDocument` |
| Voting IDs (newer DK) | embedded in agenda JS: `addVotesLink("DKP_HEX32","VOTE_HEX32",…)` → build `/0/{VOTE_HEX32}?OpenDocument` (see Step 2.B) |

## Workflow for a Single Session

### Step 1: Open the session agenda
```
browser_navigate → session URL
browser_snapshot → save to file (large, ~120KB)
```

### Step 2: Parse agenda — extract bills + voting URLs

The agenda snapshot from Step 1 holds BOTH:
  (a) the list of likumprojekti scheduled for this session (with submitters)
  (b) the URLs of the actual vote results pages.
Process both before moving to Step 3.

#### Step 2.A: Parse bills + match submitters

```python
from src.saeima import parse_agenda_snapshot, upsert_bill, match_submitters_to_politicians

with open('path/to/agenda_snapshot.md', encoding='utf-8') as f:
    snapshot_text = f.read()

agenda_bills = parse_agenda_snapshot(snapshot_text)
if not agenda_bills:
    print("WARN: parse_agenda_snapshot returned []. Likely HTML structure changed.")
    print("STOP — abort session, report to operator before proceeding.")
    raise SystemExit(1)

for ab in agenda_bills:
    # Validate institutional submitter against canonical list (see § 2.A.bis)
    if ab.institutional_submitter and ab.institutional_submitter not in KNOWN_INSTITUTIONAL_SUBMITTERS:
        print(f"  STOP: unknown institutional submitter {ab.institutional_submitter!r} for {ab.document_nr}")
        print("  Add to KNOWN_INSTITUTIONAL_SUBMITTERS list below before continuing.")
        raise SystemExit(1)

    bill_id = upsert_bill(
        db_path='data/atmina.db',
        document_nr=ab.document_nr,
        title=ab.title,
        bill_type=ab.bill_type,                      # 'Lp14' / 'Lm14' / 'P14'
        institutional_submitter=ab.institutional_submitter,
        # topic + base_law_slug auto-resolved by upsert_bill from title
    )
    matched, unmatched = match_submitters_to_politicians(
        db_path='data/atmina.db',
        bill_id=bill_id,
        submitter_names=ab.individual_submitters,
    )
    if unmatched:
        print(f"  unmatched submitters for {ab.document_nr}: {unmatched}")
        # Tier-2 deputy STOP rule (existing prompt §155) covers individuals.
```

#### Step 2.A.bis: Known institutional submitters (canonical list)

If `parse_agenda_snapshot` yields any other institutional submitter value, STOP
and ask the operator to extend this list (and, if necessary, the regex in
`src/saeima/parsing.py:_parse_institutional_submitter`). Silent acceptance creates
persistent misclassification — the discipline rule is mandatory.

```python
KNOWN_INSTITUTIONAL_SUBMITTERS = {
    "Ministru kabinets",
    "Saeimas Prezidijs",
    # Saeimas komisijas
    "Tautsaimniecības, agrārās, vides un reģionālās politikas komisija",
    "Juridiskā komisija",
    "Sociālo un darba lietu komisija",
    "Aizsardzības, iekšlietu un korupcijas novēršanas komisija",
    "Cilvēktiesību un sabiedrisko lietu komisija",
    "Izglītības, kultūras un zinātnes komisija",
    "Valsts pārvaldes un pašvaldības komisija",
    "Budžeta un finanšu (nodokļu) komisija",
    "Eiropas lietu komisija",
    "Mandātu, ētikas un iesniegumu komisija",
    "Publisko izdevumu un revīzijas komisija",
    "Pieprasījumu komisija",
    "Ārlietu komisija",
    "Ilgtspējīgas attīstības komisija",
    # Konstit. iestādes
    "Latvijas Bankas padome",
    "Augstākā tiesa",
    "Valsts kontrole",
}
```

#### Step 2.B: Extract voting URLs (THREE patterns — check ALL)

Vote IDs appear in the agenda snapshot in **three** layouts. Older sessions
expose static `OpenDocument` links; newer DK sessions embed the IDs in a
JavaScript `addVotesLink(...)` call with **no static href**; and from
2026-06-11 the agenda renders `./Voting?ReadForm&parentID={GUID}` links
instead (neither earlier pattern matches — that session would have been a
formal 2.B STOP if the new layout had not been spotted). Extract from all
three and take the union — checking only the first is how the **2026-06-04
session (70 votes) was silently missed**.

```bash
# Pattern 1 — static links (older sessions):
grep -oE '\./0/[A-F0-9]{32}\?OpenDocument' snapshot_file

# Pattern 2 — JS-embedded (newer DK sessions): the agenda renders
#   addVotesLink("DKP_HEX32","VOTE_HEX32","hidden","cand","byCard")
# Take the SECOND 32-hex (the vote id); build /0/{HEX}?OpenDocument from it:
grep -oE 'addVotesLink\("[A-F0-9]{32}","[A-F0-9]{32}"' snapshot_file \
  | grep -oE '","[A-F0-9]{32}"' | tr -d '",'

# Pattern 3 — Voting?ReadForm links (2026-06-11+): GUID-parented vote pages.
# NB: these pages carry NO result label — compute the result from the
# attendance-majority rule and cross-check against the agenda labels.
# NB2: GUIDs come LOWERCASE (2026-07-23 S1 served all 61 links lowercase — an
# uppercase-only class here would have silently skipped the whole session) and
# the agenda snapshot may HTML-escape the ampersand as `&amp;`. Keep the class
# mixed-case + the `(amp;)?` alternative, matching `_VOTING_READFORM_RE`; if
# the match contains `&amp;`, normalize it to `&` before fetching.
grep -oE '\./Voting\?ReadForm&(amp;)?parentID=[A-Fa-f0-9-]{36}' snapshot_file
```

Union all three, dedupe; patterns 1–2 build `/0/{HEX}?OpenDocument`, pattern 3
uses the matched URL as-is (after `&amp;`→`&` normalization if present). The canonical regexes for all three live in
`scripts/p3_backfill_year_urllib.py` (`_STATIC_VOTE_RE`, `_ADD_VOTES_RE`,
`_VOTING_READFORM_RE`; union helper `_extract_vote_urls_from_agenda`, added
2026-06-12). **Freshness caveat (verified 2026-06-12):** pattern-3 pages serve
their embedded vote data only while the session is "actual" — one day later the
same URL returns empty `voteFullListByNames` (no `&tm=` variant unlocks it).
ReadForm-era sessions MUST be ingested same-day; a late run discovers the URLs
but every fetch fails visibly with `empty data`.

**0-vote guard (MANDATORY).** If the union is EMPTY but Step 2.A found
bill/agenda items that should carry votes, **STOP** — do **not** report
"0 balsojumi" as success. An occurred plenary session with zero extracted vote
URLs means the snapshot used a layout neither pattern caught, not that no votes
happened. Save the snapshot and report to the operator.

### Step 3: For each voting URL — atomic 3A→3B→3C block

Process votes one at a time. For each, run 3A→3B→3C in sequence before moving
to the next. **Do not** batch all snapshots first and summaries later — that
shape lost 21 summaries across May 2026 sessions and produced 1943 generic
claim stances (sk. wiki/CHANGELOG 2026-05-16).

#### 3.A: Capture the result snapshot

```
browser_navigate → full URL (prepend https://titania.saeima.lv/LIVS14/SaeimaLIVS2_DK.nsf)
browser_snapshot → save to file
```

#### 3.B: Read bill text + compose summary (MANDATORY for bill-type votes)

Bill-type = vote motif contains `(N/Lp14)` or `(N/Lm14)`. For procedural votes
without a bill reference (no-confidence motion, treaty text-only, presidential
appointments), skip to 3.C with `summary=None`. Exception — deputātu klātbūtnes
reģistrācijai lieto kanonisko frāzi (DB konvencija 2026-07-05):
`"Deputātu klātbūtnes reģistrācija — procesuāla kvoruma pārbaude, nav saturisks balsojums."`

1. **Extract the document reference** from the motif — patterns like `(1286/Lp14)` or `(976/Lm14)`
2. **Build the document URL:**
   - `Lp14`: `https://titania.saeima.lv/LIVS14/saeimalivs14.nsf/webSasaiste?OpenView&restricttocategory={nr}`
   - `Lm14`: `https://titania.saeima.lv/LIVS14/saeimalivs_lmp.nsf/webSasaiste?OpenView&restricttocategory={nr}`
3. **Navigate** → document page → click bill text or annotation (`anotācija`)
4. **Read enough** to understand SUBSTANCE — focus on first paragraphs or annotation
5. **Compose 1-2 sentence LV summary** of what the bill actually does:
   - GOOD: "Paaugstina aizsardzības budžeta minimumu no 3% līdz 5% no IKP sākot ar 2027. gadu"
   - BAD: "Grozījumi Valsts aizsardzības finansēšanas likumā"

**Tips:**
- The annotation (`anotācija`) is usually the cleanest source
- Image-only PDFs (no extractable text): use the annotation or committee opinion instead
- Truly cannot determine substance: set summary to `"Kopsavilkums nav pieejams — dokuments nav atvērams"`. This is an explicit-signal value, **not** a permission to omit the field

#### 3.C: Parse + store + generate claims (one atomic call)

```bash
cd ~/atmina
PYTHONIOENCODING=utf-8 .venv/Scripts/python -c "
from src.saeima import init_saeima_tables, process_vote_snapshot
from src.db import get_db

db = get_db('data/atmina.db')
init_saeima_tables(db)

with open('path/to/snapshot.md', encoding='utf-8') as f:
    text = f.read()

result = process_vote_snapshot(
    snapshot_text=text,
    vote_url='https://titania.saeima.lv/LIVS14/SaeimaLIVS2_DK.nsf/0/{HEX_ID}?OpenDocument',
    summary=summary,            # from 3.B; pass even for 'Kopsavilkums nav pieejams'
    document_url=document_url,  # from 3.B (None for procedural votes)
    document_nr=document_nr,    # from 3.B (None for procedural votes)
)
print(result)
"
```

`summary`, `document_url`, `document_nr` are keyword-only — pass by name. If
omitted on a bill-type motif, `generate_claims_from_votes` writes a
`saeima_summary_missing` warning to the `logs` table, and Step 5 verification
will surface the gap before completion.

**URL handling:** Either full (`https://titania.saeima.lv/LIVS14/SaeimaLIVS2_DK.nsf/0/HEX?OpenDocument`) or relative (`./0/HEX?OpenDocument`) forms are accepted — `src.saeima._resolve_vote_url()` normalizes both. Prefer passing whichever the scraper captured verbatim; do NOT concatenate base URL yourself (that caused the 2026-04-16 double-prefix regression that corrupted 3000+ rows).

### Step 4: Link vote to bill stage

After each `store_vote()` returns `vote_id`, resolve which bill it advances and
write the stage row. This keeps `saeima_bills.current_stage` and the
denormalized timeline accurate. Phase 1C wires this in — Pipeline Invariant 12
(`CLAUDE.md`) makes `append_bill_stage()` the SOLE writer of `saeima_votes.bill_id`.

```python
from src.saeima import resolve_bill_from_motif, append_bill_stage, _reading_from_motif
from src.db import get_db

db = get_db('data/atmina.db')

# vote_db_id is the integer returned by store_vote() in Step 4
doc_nr = resolve_bill_from_motif(vote.motif)
if doc_nr is None:
    print(f"  no bill match for motif {vote.motif!r} — vote stored without bill_id")
else:
    bill = db.execute("SELECT id FROM saeima_bills WHERE document_nr=?", (doc_nr,)).fetchone()
    if bill is None:
        print(f"  WARN: motif resolved to {doc_nr} but no bill row — Step 2 may have skipped it")
    else:
        stage_name = _reading_from_motif(vote.motif)  # may return 'nezināms'
        append_bill_stage(
            db_path='data/atmina.db',
            bill_id=bill['id'],
            stage_name=stage_name,
            stage_result=vote.result,
            stage_date=vote.date,
            vote_id=vote_db_id,
        )
```

`stage_name='nezināms'` is acceptable — it's the visible signal that the motif's
reading wasn't classified. Don't invent a stage to fix it; report unusual motifs
back so the vocabulary can grow.

### Step 5: Final verification gate — summary completeness

Before reporting "session done" to the operator, run this query to confirm no
bill-type vote got stored without a summary:

```python
import sqlite3
db = sqlite3.connect('data/atmina.db')
missing = db.execute("""
    SELECT id, motif FROM saeima_votes
    WHERE date(created_at) = date('now', '+3 hours')
      AND summary IS NULL
      AND (motif LIKE '%/Lp14)%' OR motif LIKE '%/Lm14)%')
""").fetchall()
db.close()
if missing:
    print(f"STOP — {len(missing)} bill-type votes without summary:")
    for vid, motif in missing:
        print(f"  vote_id={vid}  {motif[:80]}")
    print("Go back to Step 3.B for each, write summary, then UPDATE saeima_votes.summary.")
    raise SystemExit(1)
```

Code Layer-1 also writes a `saeima_summary_missing` warning to the `logs` table
whenever `generate_claims_from_votes` runs on a bill-like motif without a
summary. The two signals are redundant by design — Step 5 catches new-row
gaps, the log surfaces silent skips even when Step 5 verification is bypassed.

## Failure modes — when to STOP vs log+continue

| Situation                                                                            | Action                |
|--------------------------------------------------------------------------------------|-----------------------|
| Unknown institutional submitter (not in `KNOWN_INSTITUTIONAL_SUBMITTERS` above)       | STOP, ask operator    |
| Unknown deputy (not in `tracked_politicians.name_forms`)                             | STOP, ask operator    |
| `parse_agenda_snapshot()` returns []                                                 | STOP, abort session   |
| Step 2.B vote-URL union empty BUT agenda has bill/vote items                          | STOP, report (0 votes = scraper-pattern miss, not empty session) |
| `resolve_bill_from_motif()` returns None                                             | log, store vote w/o bill_id |
| `_reading_from_motif()` returns 'nezināms'                                           | log, append stage as-is |
| `upsert_bill()` raises ValueError on bill_type                                       | STOP, report          |

The `STOP` rows create persistent silent corruption if ignored — including an
empty vote-URL union, which *looks* like "nothing happened" but means the
snapshot beat both extraction patterns. The `log` rows are recoverable per-row —
the agent flow continues, operator reviews logs after the run.

## Data Flow

```
Saeima webpage (JS-rendered)
    ↓ Playwright snapshot
Accessibility tree text
    ↓ parse_vote_snapshot()
VoteResult dataclass (structured)
    ↓ match_deputies_to_politicians()
Deputies linked to tracked_politicians
    ↓ store_vote() + generate_claims_from_votes()
DB tables: saeima_votes, saeima_individual_votes, claims
    ↓ read bill text (Step 3.5)
Summary written to saeima_votes.summary
```

## What Gets Stored

- `saeima_votes` — vote motif, totals (par/pret/atturas), result, topic (auto-mapped), document_url, document_nr, **summary** (1-2 sentence description of what the bill actually does)
- `saeima_individual_votes` — each deputy's name, faction, vote, linked politician_id
- `claims` — stance = "Balsoja PAR/PRET/ATTURĒJĀS", confidence = 1.0, **claim_type = 'saeima_vote'**, **document_id = NULL**. Vote provenance is the `saeima_individual_votes` join on `opponent_id` + `source_url` + `stated_at` — **do NOT write `documents` rows with `platform='saeima'`** (banned by CLAUDE.md #6 / 2026-04-25 strukturālā sanācija; `src/saeima/` no longer creates them).

### claim_type discipline (MANDATORY)

Every claim this agent writes MUST have `claim_type='saeima_vote'` (2026-04-11,
Phase B of the claim_type split). `generate_claims_from_votes()` in
`src/saeima.py` sets it automatically — you should never need to set it manually.
But if you write new code that calls `store_claim()` directly for a vote
ledger row, pass `claim_type='saeima_vote'` explicitly. Default is `'position'`,
which is wrong for Saeima votes: without the tag, Phase C readers
(`src/wiki.py`, `src/briefs.py`, `src/generate.py`) will treat the row as
first-person rhetoric and it will pollute the "pozīcijas" headline, topic
distributions, and contradiction candidates — exactly the bug the split exists
to prevent.

## Vote outcome interpretation (present-majority, not 51-of-100)

`saeima_votes.result` ("Pieņemts" / "Noraidīts") is read from the official
Saeima result label — trust it. If you ever need to classify or sanity-check an
outcome yourself (ambiguous label, editorial verification, or new
result-parsing code), Latvian parliamentary votes pass by **present-majority**:
`par > (par + pret + atturas + nebalso) // 2`, NOT an absolute 51-of-100.

Worked example: the airBaltic €30M loan (vote 99, 2026-04-16) was **49 par /
23 pret / 1 atturas / 15 nebalso** → 49 > 88 // 2 = 44 → **Pieņemts**, confirmed
by saeima.lv + Latvijas Vēstnesis (ID 367806) + LSM + NRA. A `>= 51` rule would
mis-flag it as rejected (this was a real 2026-04-26 bug).

The 51-of-100 absolute majority applies ONLY to: Satversme amendments (3
readings, 76+), no-confidence motions, presidential removal, and certain
referendum initiations. Basis: Satversme 24. p. + Saeimas kārtības rullis.

## Faction Codes

| Code | Party |
|------|-------|
| JV | Jaunā Vienotība |
| ZZS | Zaļo un Zemnieku savienība |
| NA | Nacionālā apvienība |
| PRO | Progresīvie |
| LPV | Latvija Pirmajā Vietā |
| AS | Apvienotais saraksts |

## Law Reference Wiki

Base law summaries are stored in `wiki/laws/*.md` (e.g., `wiki/laws/imigracijas-likums.md`). These provide context about what each law regulates, its key provisions, and politically sensitive sections. When writing bill summaries, you can reference these to understand what the base law does and how the amendment changes it.

## Important Notes

1. **Snapshots are huge** (~120KB). Save to file, then grep for patterns.
2. **The voting page table has two columns** — left and right deputies in each row.
3. **Vote URLs**: either absolute or relative is fine (see URL handling above).
4. **Deduplication**: `saeima_votes.url` is UNIQUE — re-running the same vote is safe. **BET (2026-07-05 mācība): URL-idempotence NEsargā pret titania pārarhivēšanu** — vote lapas ~nedēļu pēc sēdes var iegūt JAUNUS UNID (novērots 05-14 sesijai: paši-dienā tvertie `…DF7…` UNID vs vēlāk agendā `…DFF…`). Backfillojot vai atkārtoti apstrādājot sesiju, VIENMĒR dedupo pēc SATURA — `(vote_date, vote_time)` (lapas "Datums" ir sekunžu precizitātē) — pirms katra store. Tas pats iemesls: pēc sesijas apstrādes salīdzini agendas URL kopu ar DB pēc satura, ne URL (2026-04-01 un 2026-05-14 sesijām šādi atklājās 5 un 74 klusi iztrūkstoši balsojumi; 04-01 pirmajā ingestā arī URL↔rindu nobīdes ķēde, salabota `data/fix_vote2_3_dup_chain_2026-07-05.sql`).
5. **All 100 deputies should match** — if any are unmatched (politician_id IS NULL), check name_forms in tracked_politicians. If a new deputy truly is missing from `tracked_politicians`, STOP and ask the human before inserting — the row drives every downstream view.

## DO / DON'T (lessons from 2026-04-16 session)

### NEVER write the topic as a string literal
`saeima_votes.topic` and the derived `claims.topic` MUST come from
`src.saeima._motif_to_topic(motif)`. That function already exists; do not
bypass it with an UPDATE statement. If you write a bespoke SQL migration,
call the helper in Python and pass the result to SQL — never type a topic
string in by hand. On 2026-04-16 a hand-typed `'Ekonomika un finanses'`
leaked into 5630 rows because the matcher returned the raw motif and an
interactive session papered over the gap. The canonical topic list lives
in `src.topic_map.TOPIC_GROUPS`; `_motif_to_topic` is the ONLY sanctioned
entry point.

### NEVER rewrite deputy names to "fix matching"
Deputy names on the Saeima site sometimes differ from the canonical form
(e.g. the site shows `Edvīns Šnore` instead of `Edvīns Šņore`). If a vote
fails to match a tracked politician, the fix is ONE of:
1. Add the observed form to `tracked_politicians.name_forms` (a diacritic
   variant is the usual case), OR
2. Correct the canonical name in `tracked_politicians.name` (only if the
   person actually changed their public spelling).

Do NOT overwrite `deputy_name` in `saeima_individual_votes` to match the
canonical politician. The raw deputy_name is the audit trail — keep it.

### Summary must NOT repeat the motif title
`saeima_votes.summary` is rendered right below `saeima_votes.motif`. Writing
`"Grozījumi X likumā (2. lasījums, steidzams); X likums paredz..."` duplicates
the title and wastes reading attention. Start the summary with the
SUBSTANCE — what the bill actually does, who initiated it, why the coalition
split. Procedural metadata like readings and steidzams is already on the
card.

### Flag non-standard cases, don't paper over them
If a vote's motif doesn't fit the topic map cleanly, the result is that the
vote gets the fallback topic ("Valsts pārvalde"). That's OK — it's a visible
signal. Don't invent a topic to "fix it." Instead, report the motif back to
the human with a proposed map entry. The 2026-04-16 mis-classifications
(ES politika swallowing any `-es ` suffix, etc.) surfaced exactly because
the fallback was distinct and auditable.
