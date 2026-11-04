import type { NextStep, RunSummary } from '../../types'

const SAFE = /^[A-Za-z0-9][A-Za-z0-9_.:+-]{0,127}$/

// Fixed-format fields only: run data never reaches the band as free text.
const safe = (value: unknown) => (typeof value === 'string' && SAFE.test(value) ? value : 'unrecorded')

const count = (items: unknown, field: string, value: string) =>
  Array.isArray(items) ? items.filter(item => item !== null && typeof item === 'object' && item[field] === value).length : 0

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
  }
}

// Whole days between an ISO date and now; null when the date is not one.
export function daysOld(date: string, nowMs: number): number | null {
  const at = Date.parse(date + 'T00:00:00Z')
  return Number.isNaN(at) ? null : Math.max(0, Math.floor((nowMs - at) / 86_400_000))
}

const KINDS = ['retrieve', 'fact', 'source', 'applicability', 'mapping', 'family'] as const

// Parses `next --json` output into a fixed-format step; free-text actions never reach the band.
export function parseStep(dir: string, text: string): NextStep | null {
  let value: any
  try {
    value = JSON.parse(text)
  } catch {
    return null
  }
  const step = Array.isArray(value?.steps) ? value.steps[0] : undefined
  if (step === undefined || step === null || typeof step !== 'object') return null
  if (!KINDS.includes(step.kind)) return null
  const subject = step.subject === '' ? '' : SAFE.test(step.subject ?? '') ? step.subject : null
  if (subject === null || !Number.isInteger(step.unblocks) || step.unblocks < 0 || step.unblocks > 100_000) return null
  return { dir, kind: step.kind, subject, unblocks: step.unblocks }
}

export function describeStep(step: NextStep): string {
  const what = {
    retrieve: 'fetch official text',
    fact: `confirm ${step.subject}`,
    source: `review source ${step.subject}`,
    applicability: `decide ${step.subject}`,
    mapping: `map ${step.subject}`,
    family: 'screen legal families',
  }[step.kind]
  return `Next: ${what} · unblocks ${step.unblocks} open requirement${step.unblocks === 1 ? '' : 's'}`
}
