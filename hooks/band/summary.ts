import type { NextStep, NextSteps, RunSummary, ScoreMeter, Scores } from '../../types'

const SAFE = /^[A-Za-z0-9][A-Za-z0-9_.:+-]{0,127}$/

// Fixed-format fields only: run data never reaches the band as free text.
const safe = (value: unknown) => (typeof value === 'string' && SAFE.test(value) ? value : 'unrecorded')

// A completed run's processing state is one of the terminal states, as in models.TERMINAL_RUN_STATES.
const RUN_STATES = ['completed', 'partial', 'cancelled', 'interrupted']

const count = (items: unknown, field: string, value: string) =>
  Array.isArray(items) ? items.filter(item => item !== null && typeof item === 'object' && item[field] === value).length : 0

// Gap prefixes the report groups by, in its order; anything else is coverage.
export const AREAS = [
  ['Requirement', 'requirements'], ['Obligation', 'obligations'], ['Historical', 'changed since previous run'],
  ['Source target', 'source targets'], ['Source', 'selected sources'], ['Evidence', 'evidence'], ['Fact', 'facts'],
  ['Family', 'legal families'],
] as const

function areas(gaps: unknown): { area: string; count: number }[] {
  const counts = new Map<string, number>()
  for (const gap of Array.isArray(gaps) ? gaps : []) {
    if (typeof gap !== 'string') continue
    const found = AREAS.find(([prefix]) => gap.startsWith(`${prefix} `))
    const area = found ? found[1] : 'coverage and scope'
    counts.set(area, (counts.get(area) ?? 0) + 1)
  }
  const order = [...AREAS.map(([, area]) => area as string), 'coverage and scope']
  return order.filter(area => counts.has(area)).map(area => ({ area, count: counts.get(area)! }))
}

// The same explicit fact occurrences as models.scope_facts, by id and basis only.
function questions(scope: any): { id: string; basis: string }[] {
  // Every open fact; the summary keeps the first 50 and the total.
  const list = (value: unknown) => (Array.isArray(value) ? value : [])
  const facts = [...list(scope?.roles), ...list(scope?.size_and_sector), ...list(scope?.technical)]
  for (const activity of list(scope?.activities)) {
    facts.push(activity?.lawful_basis, ...list(activity?.roles), ...list(activity?.recipients),
      ...list(activity?.locations), ...list(activity?.stores), ...list(activity?.retention))
  }
  const seen = new Set<string>()
  const found = []
  for (const fact of facts) {
    if (fact === null || typeof fact !== 'object') continue
    const open = fact.basis === 'assumed' || fact.basis === 'unknown' || (Array.isArray(fact.conflicts) && fact.conflicts.length > 0)
    const id = safe(fact.id)
    if (!open || id === 'unrecorded' || seen.has(id)) continue
    seen.add(id)
    found.push({ id, basis: fact.basis === 'assumed' || fact.basis === 'unknown' ? fact.basis : 'conflicting' })
  }
  return found
}

// Parses a run's bundle.json text into the band's summary; null when it is not a bundle.
export function summarize(dir: string, text: string): RunSummary | null {
  let bundle: any
  try {
    bundle = JSON.parse(text)
  } catch {
    return null
  }
  if (bundle === null || typeof bundle !== 'object' || typeof bundle.run !== 'object' || bundle.run === null) return null
  const requirements = Array.isArray(bundle.requirement_assessments) ? bundle.requirement_assessments : []
  const attempts = Array.isArray(bundle.source_attempts) ? bundle.source_attempts : []
  return {
    dir,
    projectId: safe(bundle.project_id),
    id: safe(bundle.run.id),
    state: RUN_STATES.includes(bundle.run.state) ? bundle.run.state : 'unrecorded',
    endedAt: safe(bundle.run.ended_at),
    assessmentDate: safe(bundle.declarations?.scope?.assessment_date),
    synthetic: bundle.synthetic === true,
    gaps: Array.isArray(bundle.gaps) ? bundle.gaps.length : 0,
    requirements: {
      supported: count(requirements, 'state', 'supported'),
      conflicting: count(requirements, 'state', 'conflicting'),
      unresolved: count(requirements, 'state', 'unresolved'),
      total: requirements.length,
    },
    attempts: { retrieved: count(attempts, 'state', 'retrieved'), total: attempts.length },
    areas: areas(bundle.gaps),
    ...(() => {
      const open = questions(bundle.declarations?.scope)
      return { questions: open.slice(0, 50), questionsTotal: open.length }
    })(),
  }
}

// Whole days between an ISO date and now; null when the date is not one.
export function daysOld(date: string, nowMs: number): number | null {
  const at = Date.parse(date + 'T00:00:00Z')
  return Number.isNaN(at) ? null : Math.max(0, Math.floor((nowMs - at) / 86_400_000))
}

const KINDS = ['retrieve', 'fact', 'source', 'applicability', 'mapping', 'review', 'family'] as const

// Parses `next --json` output into fixed-format steps; free-text actions never reach the band.
export function parseSteps(dir: string, text: string): NextSteps | null {
  let value: any
  try {
    value = JSON.parse(text)
  } catch {
    return null
  }
  if (!Array.isArray(value?.steps)) return null
  const steps: NextStep[] = []
  for (const step of value.steps.slice(0, 5)) {
    if (step === null || typeof step !== 'object' || !KINDS.includes(step.kind)) return null
    const subject = step.subject === '' ? '' : SAFE.test(step.subject ?? '') ? step.subject : null
    if (subject === null || !Number.isInteger(step.unblocks) || step.unblocks < 0 || step.unblocks > 100_000) return null
    steps.push({ kind: step.kind, subject, unblocks: step.unblocks })
  }
  return { dir, steps, scores: null }
}

// A safe id in words: "fact-accounts-basis" -> "accounts basis". Ids are validated, never free text.
const ID_PREFIXES = ['fact', 'obl', 'obligation', 'req', 'requirement', 'target', 'source', 'activity']

export function words(id: string): string {
  let rest = id
  for (const prefix of ID_PREFIXES) {
    const separator = rest[prefix.length]
    if (rest.startsWith(prefix) && (separator === '-' || separator === '_')) {
      rest = rest.slice(prefix.length + 1)
      break
    }
  }
  const parts: string[] = []
  let part = ''
  for (const char of rest) {
    if ('-_.:'.includes(char)) {
      if (part !== '') parts.push(part)
      part = ''
    } else part += char
  }
  if (part !== '') parts.push(part)
  return parts.join(' ').trim()
}

// "eu-compliance-guard: unsafe-path: ..." -> "unsafe-path"; stderr carries only the CLI's fixed codes.
export function errorCode(stderr: string | undefined): string | null {
  const marker = 'eu-compliance-guard: '
  if (stderr === undefined) return null
  for (let start = stderr.indexOf(marker); start !== -1; start = stderr.indexOf(marker, start + 1)) {
    let end = start + marker.length
    while (end < stderr.length && (stderr[end] === '-' || (stderr[end] >= 'a' && stderr[end] <= 'z'))) end += 1
    if (end > start + marker.length && stderr[end] === ':') return stderr.slice(start + marker.length, end)
  }
  return null
}

// "/state/run-1///" -> "run-1"
export function baseName(path: string): string {
  let end = path.length
  while (end > 0 && path[end - 1] === '/') end -= 1
  return path.slice(path.lastIndexOf('/', end - 1) + 1, end)
}

export function describeStep(step: NextStep): string {
  const what = {
    retrieve: 'Fetch the official law text',
    fact: `Confirm the ${words(step.subject)}`,
    source: `Read and approve the ${words(step.subject)} text`,
    applicability: `Decide whether ${words(step.subject)} applies`,
    mapping: `Link ${words(step.subject)} to a legal duty`,
    review: `Review the evidence for ${words(step.subject)}`,
    family: 'Check which areas of EU law apply',
  }[step.kind]
  return `${what} · unblocks ${step.unblocks} open requirement${step.unblocks === 1 ? '' : 's'}`
}

// "████░░░░░░ 3/12": a fixed-width bar of supported requirements.
export function progressBar(done: number, total: number, width = 10): string {
  const filled = total > 0 ? Math.round((done / total) * width) : 0
  return `${'█'.repeat(filled)}${'░'.repeat(width - filled)} ${done}/${total}`
}

// Closed sets of the generated contract (tests/test_plugin.py checks them against contract.schema.json).
export const SCORE_KEYS = ['alignment', 'law_text', 'facts', 'decisions', 'mapping', 'reviews'] as const
export const SCORE_STATUSES = ['declarations_incomplete', 'needs_attention', 'in_review', 'steps_closed'] as const
export const SCORE_ATTENTION = ['reviewer_recorded_insufficient', 're_review_after_change', 'evidence_changed', 'origin_changed'] as const
export const SCORE_NOTICE = 'Points count recorded review steps in this run. They are not a compliance score or verdict.'

const LABELS: Record<ScoreMeter['key'], string> = {
  alignment: 'Alignment', law_text: 'Law text', facts: 'Facts', decisions: 'Decisions', mapping: 'Mapping', reviews: 'Reviews',
}
const SHORT: Record<ScoreMeter['key'], string> = {
  alignment: 'Alignment', law_text: 'Law', facts: 'Facts', decisions: 'Decisions', mapping: 'Mapping', reviews: 'Reviews',
}
const UNITS: Record<ScoreMeter['key'], string> = {
  alignment: 'requirements', law_text: 'obligations', facts: 'facts', decisions: 'obligations', mapping: 'requirements',
  reviews: 'methods',
}
const STATUS_WORDS: Record<Scores['status'], string> = {
  declarations_incomplete: 'Declarations incomplete', needs_attention: 'Needs attention', in_review: 'In review',
  steps_closed: 'Recorded steps closed',
}

const MAX_COUNT = 100_000
const isCount = (value: unknown, max = MAX_COUNT): value is number =>
  typeof value === 'number' && Number.isInteger(value) && value >= 0 && value <= max
const isPoints = (value: unknown): value is number | null => value === null || isCount(value, 10)

// Parses `score --json` into numbers and closed words only; null when anything is off. No run text is kept.
export function parseScores(text: string): Scores | null {
  let value: any
  try {
    value = JSON.parse(text)
  } catch {
    return null
  }
  const card = value?.scorecard
  if (card === null || typeof card !== 'object' || !SCORE_STATUSES.includes(card.status) || typeof card.synthetic !== 'boolean') return null
  if (!Array.isArray(card.dimensions) || card.dimensions.length !== SCORE_KEYS.length) return null
  const meters: ScoreMeter[] = []
  for (const [index, item] of card.dimensions.entries()) {
    if (item === null || typeof item !== 'object' || item.key !== SCORE_KEYS[index]) return null
    const ceiling = item.ceiling === null || item.ceiling === undefined ? null : item.ceiling?.points
    if (!isPoints(item.points) || !isCount(item.done) || !isCount(item.total) || item.done > item.total
      || !isPoints(ceiling) || !isPoints(item.raise_points) || !(item.raise_by === null || isCount(item.raise_by))) return null
    meters.push({ key: item.key, points: item.points, done: item.done, total: item.total, ceiling,
      raisePoints: item.raise_points, raiseBy: item.raise_by })
  }
  if (!isCount(card.screening?.screened, 11) || !Array.isArray(card.attention) || card.attention.length > SCORE_ATTENTION.length) return null
  const attention: Scores['attention'] = []
  for (const item of card.attention) {
    if (!SCORE_ATTENTION.includes(item?.key) || !isCount(item.count) || item.count < 1) return null
    attention.push({ key: item.key, count: item.count })
  }
  let deltas: Scores['deltas'] = null
  if (card.trend?.comparable === true) {
    const items = card.trend.deltas
    if (!Array.isArray(items) || items.length !== SCORE_KEYS.length) return null
    deltas = []
    for (const [index, item] of items.entries()) {
      if (item?.key !== SCORE_KEYS[index] || !isPoints(item.points_before) || !isPoints(item.points_after)) return null
      deltas.push({ key: item.key, before: item.points_before, after: item.points_after })
    }
  }
  return { status: card.status, synthetic: card.synthetic, meters, screened: card.screening.screened, attention, deltas }
}

// "■■■■■□□□□□": filled to the points, hatched above a ceiling, dots when not scored.
export function meterBar(points: number | null, ceiling: number | null = null): string {
  if (points === null) return '·'.repeat(10)
  const reachable = ceiling ?? 10
  return `${'■'.repeat(points)}${'□'.repeat(reachable - points)}${'▨'.repeat(10 - reachable)}`
}

const pointsWord = (points: number | null) => (points === null ? '–' : String(points))

export function statusWord(scores: Scores): string {
  return STATUS_WORDS[scores.status]
}

// "Review progress · In review · Alignment ■■■■■□□□□□ 5/10 (1 of 2)": the main meter and the status.
export function progressLine(scores: Scores): string {
  const alignment = scores.meters[0]!
  const ceiling = alignment.ceiling === null ? '' : ` · max ${alignment.ceiling}/10 this run`
  const points = alignment.points === null ? 'not scored' : `${alignment.points}/10`
  return `Review progress · ${STATUS_WORDS[scores.status]} · Alignment ${meterBar(alignment.points, alignment.ceiling)} ${points}`
    + ` (${alignment.done} of ${alignment.total})${ceiling}`
}

// "Law 10 · Facts 3 (+3) · ... (points of 10)": the other meters, never summed.
export function meterRow(scores: Scores): string {
  const parts = scores.meters.slice(1).map(meter => {
    const delta = scores.deltas?.find(item => item.key === meter.key)
    const change = delta && delta.before !== null && delta.after !== null && delta.before !== delta.after
      ? ` (${delta.after > delta.before ? '+' : '−'}${Math.abs(delta.after - delta.before)})` : ''
    return `${SHORT[meter.key]} ${pointsWord(meter.points)}${change}`
  })
  return `${parts.join(' · ')} (points of 10)`
}

// "Facts      ■■■□□□□□□□  3/10  1 of 3 facts  +3: 1 more": one fixed-format panel line per meter.
export function describeMeter(meter: ScoreMeter): string {
  const points = meter.points === null ? 'not scored' : `${meter.points}/10`
  const raise = meter.raisePoints === null ? '' : `  +${meter.raisePoints}: ${meter.raiseBy} more`
  return `${LABELS[meter.key].padEnd(10)} ${meterBar(meter.points, meter.ceiling)} ${points.padStart(5)}  ${meter.done} of ${meter.total} ${UNITS[meter.key]}${raise}`
}

// "app/web.py:12": plain path segments (letters, digits, _ . -), no "..", no leading slash, a line number.
export function safeLocation(value: unknown): string | null {
  if (typeof value !== 'string' || value.length > 200) return null
  const cut = value.lastIndexOf(':')
  const path = value.slice(0, cut)
  const line = value.slice(cut + 1)
  if (cut <= 0 || line === '' || line.length > 9 || [...line].some(char => char < '0' || char > '9') || line[0] === '0') return null
  const segments = path.split('/')
  const plain = (segment: string) => segment !== '' && segment !== '..' && segment !== '.'
    && [...segment].every(char => (char >= 'a' && char <= 'z') || (char >= 'A' && char <= 'Z') || (char >= '0' && char <= '9') || '_.-'.includes(char))
  return segments.every(plain) ? value : null
}

// Parses `ground --json`: each open fact's top code candidate, ids and locations validated; nothing else is kept.
export function parseCandidates(text: string): { fact: string; location: string }[] | null {
  let value: any
  try {
    value = JSON.parse(text)
  } catch {
    return null
  }
  if (!Array.isArray(value?.facts)) return null
  const found: { fact: string; location: string }[] = []
  for (const fact of value.facts.slice(0, 200)) {
    const id = typeof fact?.fact === 'string' && SAFE.test(fact.fact) ? fact.fact : null
    const location = Array.isArray(fact?.candidates) ? safeLocation(fact.candidates[0]?.location) : null
    if (id !== null && location !== null) found.push({ fact: id, location })
  }
  return found
}
