import type { NextStep, NextSteps, RunSummary } from '../../types'

const SAFE = /^[A-Za-z0-9][A-Za-z0-9_.:+-]{0,127}$/

// Fixed-format fields only: run data never reaches the band as free text.
const safe = (value: unknown) => (typeof value === 'string' && SAFE.test(value) ? value : 'unrecorded')

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
  const facts = [...list(scope?.roles), ...list(scope?.size_and_sector)]
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
    state: safe(bundle.run.state),
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

const KINDS = ['retrieve', 'fact', 'source', 'applicability', 'mapping', 'family'] as const

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
  return { dir, steps }
}

// A safe id in words: "fact-accounts-basis" -> "accounts basis". Ids are validated, never free text.
export function words(id: string): string {
  return id.replace(/^(fact|obl|obligation|req|requirement|target|source|activity)[-_]/, '').replace(/[-_.:]+/g, ' ').trim()
}

export function describeStep(step: NextStep): string {
  const what = {
    retrieve: 'Fetch the official law text',
    fact: `Confirm the ${words(step.subject)}`,
    source: `Read and approve the ${words(step.subject)} text`,
    applicability: `Decide whether ${words(step.subject)} applies`,
    mapping: `Link ${words(step.subject)} to a legal duty`,
    family: 'Check which areas of EU law apply',
  }[step.kind]
  return `${what} · unblocks ${step.unblocks} open requirement${step.unblocks === 1 ? '' : 's'}`
}

// "████░░░░░░ 3/12": a fixed-width bar of supported requirements.
export function progressBar(done: number, total: number, width = 10): string {
  const filled = total > 0 ? Math.round((done / total) * width) : 0
  return `${'█'.repeat(filled)}${'░'.repeat(width - filled)} ${done}/${total}`
}
