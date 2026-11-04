export type RunSummary = {
  dir: string
  projectId: string
  id: string
  state: string
  endedAt: string
  assessmentDate: string
  synthetic: boolean
  gaps: number
  requirements: { supported: number; conflicting: number; unresolved: number; total: number }
  attempts: { retrieved: number; total: number }
  // Open gaps per fixed area, most actionable first.
  areas: { area: string; count: number }[]
  // Assumed, unknown or conflicting facts by id; their free-text questions stay in the report.
  questions: { id: string; basis: string }[]
  questionsTotal: number
}

export type NextStep = {
  kind: 'retrieve' | 'fact' | 'source' | 'applicability' | 'mapping' | 'family'
  subject: string
  unblocks: number
}

// The ranked steps of one run directory; null steps when ranking failed for that run.
export type NextSteps = { dir: string; steps: NextStep[] | null }

export type Band = {
  isActive: boolean
  level: string
  stateDir: string
  run: RunSummary | null
  problem: string | null
  // Open items in the run before the newest, when there is one.
  previousGaps?: number | null
}

declare module 'claude-code' {
  interface PluginState {
    'eu-compliance-guard': { band: Shaped<Band>; isFolded: boolean; lastView: string | null; next: Shaped<NextSteps | null> }
  }
}
