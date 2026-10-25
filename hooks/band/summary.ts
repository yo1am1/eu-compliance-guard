import type { RunSummary } from '../../types'

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
