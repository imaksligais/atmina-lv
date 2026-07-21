export const meta = {
  name: 'historic-backfill',
  description:
    'Auto-target the thinnest-coverage ACTIVE politicians (src/coverage.py dark_zone first) and backfill their HISTORIC corpus: WebSearch discovery -> backdated ingest -> claim extraction (stated_at=published_at). Corpus + claims only by default; contradiction hunt is opt-in (args.hunt=true). Built on the shared historic-engine. args: {count=6, since, until, topics, perPolitician=12, hunt=false, dryRun=false, seedUrls}.',
  phases: [
    { title: 'Target', detail: 'src/coverage.py -> thinnest-coverage politicians' },
    { title: 'Engine', detail: 'historic-engine: discover -> ingest -> extract (+ optional hunt)' },
    { title: 'Report', detail: 'corpus backfill summary' },
  ],
}

// --- args ---------------------------------------------------------------------
let A = args || {}
if (typeof A === 'string') {
  try {
    A = JSON.parse(A)
  } catch (_) {
    A = {}
  }
}
const COUNT = Number.isInteger(A.count) ? A.count : 6
const SINCE = A.since || '2018-01-01'
const UNTIL = A.until || 'roughly 6 months before today'
const TOPICS = A.topics || null
const PER = A.perPolitician || 12
const SEED = A.seedUrls || {}
const HUNT = A.hunt === true // default OFF — corpus backfill only
const DRY = A.dryRun === true
const PY = './.venv/Scripts/python.exe' // project venv (Windows layout)

// --- schema (same resolved shape the engine consumes) -------------------------
const TARGET_SCHEMA = {
  type: 'object',
  properties: {
    resolved: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          input: { type: 'string' },
          id: { type: ['integer', 'null'] },
          name: { type: ['string', 'null'] },
          party: { type: ['string', 'null'] },
          existing_claim_count: { type: 'integer' },
          note: { type: 'string' },
        },
        required: ['input', 'id'],
      },
    },
  },
  required: ['resolved'],
}

// --- Target (coverage gap -> thinnest-coverage politicians) -------------------
phase('Target')
const tgtOut = await agent(
  `Pick the ${COUNT} thinnest-coverage ACTIVE politicians for historic web-article backfill, using the atmina
coverage module. Run via the project venv WITH UTF-8 stdout (Latvian diacritics break cp1252 — the -X utf8 flag
is mandatory). One Bash call:
  ${PY} -X utf8 -c "import json; from src.coverage import compute_coverage; from src.db import get_db; cov=compute_coverage(); db=get_db(); dz_ids={r['id'] for r in cov['dark_zone']}; \
votes=lambda i: db.execute('SELECT COUNT(*) c FROM saeima_individual_votes WHERE politician_id=?',(i,)).fetchone()['c']; \
pos=lambda i: db.execute(\"SELECT COUNT(*) c FROM claims WHERE opponent_id=? AND claim_type='position'\",(i,)).fetchone()['c']; \
dz=sorted(cov['dark_zone'], key=lambda r: votes(r['id']), reverse=True); \
fill=[r for r in cov['no_position_claims'] if r['id'] not in dz_ids]; \
cand=(dz+fill)[:${COUNT}]; \
print(json.dumps([{'id':r['id'],'name':r['name'],'party':r['party'],'votes':votes(r['id']),'position_claims':pos(r['id'])} for r in cand], ensure_ascii=False))"
RANKING RATIONALE (thinnest first): 'dark_zone' = active, Saeima votes tracked, but 0 position claims + 0 X feed
-> web articles are the ONLY possible rhetoric channel for them, and their vote history is a ready contradiction
surface once rhetoric exists. Within dark_zone, MORE votes = more established = more historic media to find, so
rank by vote count DESC. If dark_zone has fewer than ${COUNT} rows, fill from 'no_position_claims' (minus dark_zone).
The one-liner above already does this — just run it, read its single JSON line, and map it through.
NEVER fold diacritics; keep exact Latvian names. Set input=name, existing_claim_count=position_claims (expect 0),
and note = "dark_zone, <votes> Saeimas balsojumi" (or "no_position_claims" for filler rows).
Return JSON {resolved:[{input,id,name,party,existing_claim_count,note}]}. Honest empty list if coverage has none.`,
  { label: 'target', phase: 'Target', schema: TARGET_SCHEMA, agentType: 'general-purpose', model: 'opus' }
)

const resolved = (tgtOut?.resolved || []).filter((r) => r.id != null).slice(0, COUNT)
if (!resolved.length) return { error: 'coverage produced no targets (no dark_zone / no_position_claims politicians?)' }
log(`Targeted ${resolved.length}: ${resolved.map((r) => `${r.name} (${r.note || ''})`).join(', ')}`)

// --- Dry run: validate engine name-resolution + one-level nesting, NO prod writes
if (DRY) {
  log('dryRun: pinging historic-engine with an empty set (no DB writes) to validate the workflow() path.')
  const ping = await workflow('historic-engine', { resolved: [], hunt: false })
  return { dryRun: true, count: COUNT, targets: resolved, enginePing: ping }
}

// --- Engine (shared stages: discover -> ingest -> extract -> optional hunt) ----
phase('Engine')
const eng = await workflow('historic-engine', {
  resolved,
  since: SINCE,
  until: UNTIL,
  topics: TOPICS,
  perPolitician: PER,
  seedUrls: SEED,
  hunt: HUNT,
})

// --- Report -------------------------------------------------------------------
phase('Report')
const report = eng?.report || []
const totalDocs = eng?.totalDocs || 0
const totalClaims = eng?.totalClaims || 0
const totalSurvivors = eng?.totalSurvivors || 0
log(
  `Backfill done. ${report.length} politicians, ${totalDocs} docs linked, ${totalClaims} new historic claims${
    HUNT ? `, ${totalSurvivors} contradiction survivors` : ''
  }.`
)

return {
  mode: 'backfill',
  hunt: HUNT,
  scope: { count: COUNT, since: SINCE, until: UNTIL, perPolitician: PER, targeting: 'coverage.dark_zone -> no_position_claims' },
  targets: resolved.map((r) => ({ id: r.id, name: r.name, party: r.party, note: r.note })),
  report,
  totalDocs,
  totalClaims,
  totalSurvivors,
  next_steps:
    totalClaims > 0
      ? `New historic position claims stored with stated_at=published_at. Render the affected pages narrowly + deploy additively: ${PY} -m src.render --only=pretrunas,pozicijas,dashboard,politiki,blog && bash deploy.sh --no-delete. ${
          HUNT
            ? totalSurvivors > 0
              ? 'Review the confirmed=0 contradiction survivors and UPDATE confirmed=1 the keepers before publishing pretrunas.'
              : 'Contradiction hunt ran but found no survivors (0 is a valid outcome).'
            : 'No contradiction hunt ran (hunt=false). To surface rhetoric-vs-vote pretrunas for these now-rhetoric-bearing deputies, run historic-contradictions on them or re-run with hunt:true.'
        }`
      : 'No new claims — thin/absent web coverage is a valid outcome for low-profile deputies. Try a different count, a wider since/until, or seedUrls.',
}
