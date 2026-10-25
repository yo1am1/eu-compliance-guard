export type RunSummary = {
  dir: string
  id: string
  state: string
  endedAt: string
  assessmentDate: string
  synthetic: boolean
  gaps: number
  requirements: { supported: number; conflicting: number; unresolved: number; total: number }
  attempts: { retrieved: number; total: number }
}

export type Band = {
  isActive: boolean
  level: string
  stateDir: string
  run: RunSummary | null
  problem: string | null
}

declare module 'claude-code' {
  interface PluginState {
    'eu-compliance-guard': { band: Band; isFolded: boolean; lastView: string | null }
  }
}
