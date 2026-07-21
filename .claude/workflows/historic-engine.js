export const meta = {
  name: 'historic-engine',
  description:
    'Shared historic-content engine: per-politician WebSearch discovery -> backdated ingest (ingest_url.py) -> claim extraction (stated_at=published_at) -> OPTIONAL contradiction hunt (confirmed=0). Operates on a PRE-RESOLVED politician set passed via args.resolved; invoked through workflow() by historic-contradictions (hunt=true) and historic-backfill (hunt=false). It does NO name/coverage resolution of its own and MUST NOT call workflow() (one-level nesting rule).',
  phases: [
    { title: 'Discover', detail: 'WebSearch historic articles per politician' },
    { title: 'Ingest', detail: 'ingest_url.py — backdated insert + link' },
    { title: 'Extract', detail: '@claim-extractor, stated_at = published_at' },
    { title: 'Contradict', detail: '(if hunt) @contradiction-hunter -> @devils-advocate -> confirmed=0' },
  ],
}

// --- args ---------------------------------------------------------------------
// args may arrive as an object or, depending on the invocation path, a JSON string.
let A = args || {}
if (typeof A === 'string') {
  try {
    A = JSON.parse(A)
  } catch (_) {
    A = {}
  }
}
const RESOLVED = A.resolved || [] // [{ id, name, party, input?, existing_claim_count?, note? }]
const SINCE = A.since || '2018-01-01'
const UNTIL = A.until || 'roughly 6 months before today'
const TOPICS = A.topics || null
const PER = A.perPolitician || 12
const SEED = A.seedUrls || {}
const HUNT = A.hunt === true // default OFF — corpus + claims only; opt-in contradiction hunt
const PY = './.venv/Scripts/python.exe' // project venv (Windows layout)

// Empty resolved set is a valid call (engine "ping" used by wrappers' dry-run to
// validate workflow() name-resolution + nesting without touching the DB).
if (!RESOLVED.length) {
  log('historic-engine: empty resolved set — nothing to do (engine ping / no targets).')
  return { engine: 'historic-engine', report: [], totalDocs: 0, totalClaims: 0, totalSurvivors: 0, hunt: HUNT, note: 'empty resolved set' }
}
log(`historic-engine: ${RESOLVED.length} politician(s), hunt=${HUNT}, perPolitician=${PER}, range ${SINCE}..${UNTIL}`)

// --- schemas ------------------------------------------------------------------
const DISCOVER_SCHEMA = {
  type: 'object',
  properties: {
    urls: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          url: { type: 'string' },
          why: { type: 'string' },
          guessedDate: { type: ['string', 'null'] },
        },
        required: ['url'],
      },
    },
  },
  required: ['urls'],
}

const INGEST_SCHEMA = {
  type: 'object',
  properties: {
    linked_doc_ids: { type: 'array', items: { type: 'integer' } },
    dateless_doc_ids: { type: 'array', items: { type: 'integer' } },
    counts: { type: 'object' },
  },
  required: ['linked_doc_ids'],
}

const EXTRACT_SCHEMA = {
  type: 'object',
  properties: {
    claim_ids: { type: 'array', items: { type: 'integer' } },
    claims: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'integer' },
          topic: { type: 'string' },
          stance: { type: 'string' },
          stated_at: { type: ['string', 'null'] },
        },
      },
    },
    empty_doc_ids: { type: 'array', items: { type: 'integer' } },
    failures: { type: 'array', items: { type: 'object' } },
  },
  required: ['claim_ids'],
}

const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    candidates: { type: 'integer' },
    survivors: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: ['integer', 'null'] },
          old_claim_id: { type: ['integer', 'null'] },
          new_claim_id: { type: ['integer', 'null'] },
          severity: { type: 'string' },
          summary: { type: 'string' },
        },
        required: ['severity', 'summary'],
      },
    },
  },
  required: ['survivors'],
}

// --- per-politician pipeline: discover -> ingest -> extract -> (optional) contradict
// Each stage threads an accumulator forward so the final report sees everything.
// pipeline() has NO barrier between stages: politician A can be extracting while B is
// still discovering. Subagents run in clean contexts -> no shared diacritic drift.
const results = await pipeline(
  RESOLVED,

  // STAGE 1 — discover (WebSearch)
  (pol) => {
    const seeds = SEED[pol.name] || SEED[pol.input] || []
    return agent(
      `Historic article discovery for Latvian politician "${pol.name}" (id ${pol.id}, party ${pol.party}).
Find OLDER public articles/interviews/quotes published between ${SINCE} and ${UNTIL}${
        TOPICS ? `, focused on topics: ${TOPICS.join(', ')}` : ''
      }.
Use the WebSearch tool with several angles (multi-modal sweep):
  - "${pol.name}" intervija / komentē / paziņo / aicina  (vary by year across the range)
  - "${pol.name}" site:lsm.lv ; site:delfi.lv ; site:tvnet.lv ; site:nra.lv ; site:la.lv
  - "${pol.name}" <each likely topic>
Collect candidate article URLs. EXCLUDE tag/section/listing/search pages, paywalled stubs, and pages not
plausibly about this politician. Prefer URLs where the politician is the subject/speaker and a publication
date is establishable. Deduplicate. Cap at ${PER} best URLs.${
        seeds.length ? `\nAlso INCLUDE these operator-supplied seed URLs: ${JSON.stringify(seeds)}` : ''
      }
Return JSON {urls:[{url, why, guessedDate}]}. An EMPTY list is a valid, honest answer — do not invent URLs.`,
      { label: `discover:${pol.name}`, phase: 'Discover', schema: DISCOVER_SCHEMA, agentType: 'general-purpose', model: 'opus' }
    ).then((d) => ({ pol, urls: (d?.urls || []).slice(0, PER) }))
  },

  // STAGE 2 — ingest (Bash -> ingest_url.py)
  (s1) => {
    if (!s1.urls.length) return { ...s1, linked_doc_ids: [], ingest: null }
    const manifest = s1.urls
      .map((u) => JSON.stringify({ url: u.url, politician_id: s1.pol.id }))
      .join('\n')
    return agent(
      `Ingest historic articles for "${s1.pol.name}" (id ${s1.pol.id}).
1. Write this JSONL to a temp file (e.g. tmp/historic_${s1.pol.id}.jsonl in the repo):
---MANIFEST---
${manifest}
---END---
2. Run: ${PY} scripts/ingest_url.py --manifest <that file>
3. Read stdout. Each "RESULT_JSON:" line is one URL's outcome; the final "SUMMARY_JSON:" line aggregates
   counts + linked_to{pid:[doc_ids]} + dateless[doc_ids].
Return JSON: linked_doc_ids = the doc_ids linked to pid ${s1.pol.id} (SUMMARY linked_to["${s1.pol.id}"], may be empty);
dateless_doc_ids = SUMMARY dateless intersected with linked_doc_ids; counts = the SUMMARY count fields.
Do NOT publish, render, or deploy anything.`,
      { label: `ingest:${s1.pol.name}`, phase: 'Ingest', schema: INGEST_SCHEMA, agentType: 'general-purpose', model: 'opus' }
    ).then((ing) => ({ ...s1, ingest: ing, linked_doc_ids: ing?.linked_doc_ids || [] }))
  },

  // STAGE 3 — extract (@claim-extractor) — stated_at = published_at
  (s2) => {
    const ids = s2.linked_doc_ids || []
    if (!ids.length) return { ...s2, extract: { claim_ids: [], claims: [] } }
    return agent(
      `Extract pozīcijas for "${s2.pol.name}" (opponent_id ${s2.pol.id}) from these freshly-ingested HISTORIC
document ids ONLY: ${JSON.stringify(ids)}.
For each doc read content + published_at from the DB (documents.published_at).
CRITICAL HISTORIC RULE: set each claim's stated_at = that document's published_at (NOT today). These are old
articles; letting stated_at default to scrape time mis-dates the claim and destroys the over-time contradiction
signal. If a doc has no published_at, note it and leave stated_at null rather than guessing today.
Follow your normal contract: claim_type='position', preserve Latvian diacritics, run the indirect-reference
self-check, pass empty_doc_ids for every reviewed-but-empty doc, and call save_analysis exactly once. Respect the
12-doc quality envelope; if more than 12 ids, process the highest-salience 12 and note the remainder.
Return JSON {claim_ids, claims:[{id,topic,stance,stated_at}], empty_doc_ids, failures}. Check result["failures"].`,
      // model pinned to Opus: feedback_extraction_model_policy (Sonnet rejected — LV grammar errors ~30-40% in stance)
      { label: `extract:${s2.pol.name}`, phase: 'Extract', schema: EXTRACT_SCHEMA, agentType: 'claim-extractor', model: 'opus' }
    ).then((ex) => ({ ...s2, extract: ex }))
  },

  // STAGE 4 — contradict (deep-check pattern: hunt -> adversarial verify -> store confirmed=0)
  // Gated on HUNT: backfill (hunt=false) skips this and stops at the corpus + claims.
  async (s3) => {
    const newClaimIds = s3.extract?.claim_ids || []
    if (!HUNT) return { ...s3, candidates: 0, survivors: [], hunted: false }
    if (!newClaimIds.length) return { ...s3, candidates: 0, survivors: [], hunted: true }

    const hunt = await agent(
      `Hunt contradictions for "${s3.pol.name}" (opponent_id ${s3.pol.id}).
NEW historic claims just stored: ${JSON.stringify(s3.extract.claims || [])} (ids ${JSON.stringify(newClaimIds)}).
Run BOTH passes against the politician's FULL history:
A) RHETORIC-vs-RHETORIC: search_similar_claims directional (claim_type_filter) at the 0.80 threshold — old historic
   stance vs newer stance (reversals over time).
B) RHETORIC-vs-ACTION (STRUCTURAL — saeima_vote rows are NOT in claim_vectors, so similarity search returns nothing
   against them; an empty embedding result does NOT mean "no vote mismatch"). Run your structured SQL pass: for each
   position claim's topic/bill, keyword-match the politician's saeima_votes + saeima_individual_votes (join on
   opponent_id/politician_id), read the actual vote (count only Par/Pret/Atturas — Reģistrējies/Nebalsoja/
   Nereģistrējies are NOT votes), and flag where the vote opposes the stated rhetoric. Apply the MANDATORY faction
   check: a vote matching >80% of the faction is coalition discipline, NOT a personal contradiction — drop it.
Apply ALL your other false-positive filters (procedural/whip votes, tactical blocking, different subtopic, legitimate
evolution, role change, audience framing). Output structured CANDIDATES only — DO NOT store anything yet. For each
candidate give: kind (rhetoric_vs_rhetoric|rhetoric_vs_vote), old_claim_id, new_claim_id (or vote reference), topic,
proposed severity (direct_contradiction|reversal|minor_shift), a Latvian summary, salience, faction-agreement % for
vote candidates, and the journalist-test verdict.`,
      { label: `hunt:${s3.pol.name}`, phase: 'Contradict', agentType: 'contradiction-hunter', model: 'opus' }
    )

    const verdict = await agent(
      `Adversarially gate these contradiction candidates for "${s3.pol.name}" (opponent_id ${s3.pol.id}):
${hunt}
For EACH candidate: open the source_urls, read the original context, and try to REFUTE it (coalition discipline,
procedural/whip context, journalist paraphrase mistaken for a stance, combinable non-contradictory positions,
insufficient time gap). Keep ONLY robust survivors. Store each survivor:
  ${PY} -c "from src.tools import store_contradiction; print(store_contradiction(opponent_id=${s3.pol.id}, old_claim_id=OLD, new_claim_id=NEW, topic='T', summary='LV summary', severity='reversal', salience=0.5))"
store_contradiction defaults to confirmed=0 (UNPUBLISHED) — DO NOT set confirmed=1, DO NOT render or deploy.
Apply the LV grammar+stylistics gate to every stored summary (correct locījumi/garumzīmes, no anglicisms).
Return JSON {candidates:<total reviewed>, survivors:[{id, old_claim_id, new_claim_id, severity, summary}]}
where id is the contradiction id returned by store_contradiction.`,
      { label: `verify:${s3.pol.name}`, phase: 'Contradict', schema: VERDICT_SCHEMA, agentType: 'devils-advocate', model: 'opus' }
    )

    return { ...s3, candidates: verdict?.candidates || 0, survivors: verdict?.survivors || [], hunted: true }
  }
)

// --- assemble report (shape preserved for both wrappers) ----------------------
const clean = results.filter(Boolean)
const report = clean.map((r) => ({
  politician: r.pol?.name,
  id: r.pol?.id,
  urls_found: (r.urls || []).length,
  linked_docs: (r.linked_doc_ids || []).length,
  dateless_docs: (r.ingest?.dateless_doc_ids || []).length,
  new_claims: (r.extract?.claim_ids || []).length,
  empty_docs: (r.extract?.empty_doc_ids || []).length,
  candidates: r.candidates || 0,
  survivors: (r.survivors || []).map((s) => ({ id: s.id, severity: s.severity, summary: s.summary })),
}))

const totalDocs = report.reduce((n, r) => n + r.linked_docs, 0)
const totalClaims = report.reduce((n, r) => n + r.new_claims, 0)
const totalSurvivors = report.reduce((n, r) => n + r.survivors.length, 0)
log(`historic-engine done: ${report.length} politicians, ${totalDocs} docs linked, ${totalClaims} new claims, ${totalSurvivors} survivors (hunt=${HUNT}).`)

return {
  engine: 'historic-engine',
  scope: { since: SINCE, until: UNTIL, perPolitician: PER, hunt: HUNT },
  report,
  totalDocs,
  totalClaims,
  totalSurvivors,
}
