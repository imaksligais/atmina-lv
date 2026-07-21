export const meta = {
  name: 'historic-contradictions',
  description:
    'Discover historic articles for a small set of politicians via WebSearch, ingest them backdated, extract pozīcijas, and hunt contradictions vs full history (survivors stored confirmed=0 for operator review). Thin wrapper: resolves names -> ids, then runs the shared historic-engine with hunt=true.',
  phases: [
    { title: 'Resolve', detail: 'names -> politician ids' },
    { title: 'Engine', detail: 'historic-engine: discover -> ingest -> extract -> contradict (hunt=true)' },
    { title: 'Report', detail: 'operator review summary' },
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
const NAMES = A.politicians || []
const SINCE = A.since || '2018-01-01'
const UNTIL = A.until || 'roughly 6 months before today'
const TOPICS = A.topics || null
const PER = A.perPolitician || 12
const SEED = A.seedUrls || {}
const PY = './.venv/Scripts/python.exe' // project venv (Windows layout)

if (!NAMES.length) {
  log('No politicians passed in args.politicians — nothing to do.')
  return { error: 'args.politicians is required (array of names or ids)' }
}

// --- schema -------------------------------------------------------------------
const RESOLVE_SCHEMA = {
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

// --- Resolve ------------------------------------------------------------------
phase('Resolve')
const resolveOut = await agent(
  `Resolve each of these politician inputs to a tracked_politicians row in the atmina DB: ${JSON.stringify(NAMES)}.
For each input, run a Bash query against the LIVE DB, e.g.:
  ${PY} -X utf8 -c "from src.db import get_db; db=get_db(); rows=db.execute('SELECT id,name,party,relationship_type FROM tracked_politicians WHERE name LIKE ?', ('%<INPUT>%',)).fetchall(); print([dict(r) for r in rows])"
The matcher does NOT fold diacritics — try the exact Latvian spelling first. Skip rows with
relationship_type='inactive' unless that is the only match (then keep it and say so in note).
Also fetch existing_claim_count per resolved politician:
  SELECT COUNT(*) FROM claims WHERE opponent_id=? AND claim_type IN ('position','saeima_vote').
Return JSON {resolved:[{input,id,name,party,existing_claim_count,note}]} for the StructuredOutput tool.
Set id=null for any input you cannot resolve (with a note explaining why).`,
  { label: 'resolve', phase: 'Resolve', schema: RESOLVE_SCHEMA, agentType: 'general-purpose', model: 'opus' }
)

const resolved = (resolveOut?.resolved || []).filter((r) => r.id != null)
const unresolved = (resolveOut?.resolved || []).filter((r) => r.id == null)
if (unresolved.length) log(`Unresolved (skipped): ${unresolved.map((u) => u.input).join(', ')}`)
if (!resolved.length) return { error: 'no politicians resolved', unresolved }
log(`Resolved ${resolved.length}: ${resolved.map((r) => r.name).join(', ')}`)

// --- Engine (shared stages: discover -> ingest -> extract -> contradict) -------
phase('Engine')
const eng = await workflow('historic-engine', {
  resolved,
  since: SINCE,
  until: UNTIL,
  topics: TOPICS,
  perPolitician: PER,
  seedUrls: SEED,
  hunt: true,
})

// --- Report -------------------------------------------------------------------
phase('Report')
const report = eng?.report || []
const totalSurvivors = eng?.totalSurvivors || 0
log(`Done. ${report.length} politicians, ${totalSurvivors} contradiction survivors stored confirmed=0.`)

return {
  scope: { since: SINCE, until: UNTIL, perPolitician: PER },
  report,
  next_steps:
    totalSurvivors > 0
      ? 'Review confirmed=0 contradictions, UPDATE confirmed=1 the keepers, then: python -m src.render --only=pretrunas && deploy.sh --no-delete'
      : 'No survivors to publish. (0 is a valid outcome — see reference_contradiction_hunt_lessons.)',
}
