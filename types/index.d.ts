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
  kind: 'retrieve' | 'fact' | 'source' | 'applicability' | 'mapping' | 'review' | 'family'
  subject: string
  unblocks: number
}

// One review-progress meter of `score --json`: numbers only, points out of 10 (null: not scored).
export type ScoreMeter = {
  key: 'alignment' | 'law_text' | 'facts' | 'decisions' | 'mapping' | 'reviews'
  points: number | null
  done: number
  total: number
  // The most this run can reach for a structural reason (alignment only).
  ceiling: number | null
  raisePoints: number | null
  raiseBy: number | null
}

// Review progress of one run: separate meters and no total. Not a compliance score or verdict.
export type Scores = {
  status: 'declarations_incomplete' | 'needs_attention' | 'in_review' | 'steps_closed'
  synthetic: boolean
  meters: ScoreMeter[]
  screened: number
  attention: { key: 'reviewer_recorded_insufficient' | 're_review_after_change' | 'evidence_changed' | 'origin_changed'; count: number }[]
  // Point changes against the recorded parent run; null when not comparable.
  deltas: { key: ScoreMeter['key']; before: number | null; after: number | null }[] | null
}

// The ranked steps and review progress of one run directory; null when that part failed for that run.
export type NextSteps = { dir: string; steps: NextStep[] | null; scores: Scores | null }

export type Band = {
  isActive: boolean
  level: string
  stateDir: string
  run: RunSummary | null
  problem: string | null
  // Open items in the run before the newest, when there is one.
  previousGaps?: number | null
  // The run before the newest, which `score --against` compares with when it is the recorded parent.
  previousDir?: string | null
}

declare module 'claude-code' {
  interface PluginState {
    'eu-compliance-guard': { band: Shaped<Band>; isFolded: boolean; lastView: string | null; next: Shaped<NextSteps | null> }
  }
}
