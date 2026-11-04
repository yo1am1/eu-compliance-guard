// Pure parsing and presentation of a run's `views/<run>.scorecard.json` for the dashboard page.
// Types come from the generated contract; words come from the generated labels. No I/O here.
import type { ScoreDimension, Scorecard, ScoreNextStep } from '../lib/contract.ts'
import {
  ATTENTION_LABELS, HOW_TO_RAISE, HYGIENE_LABELS, LABELS, MAX_OPEN_ITEMS, NOTICE, STATUS_LABELS, STEP_TEXT, TAG_LABELS, UNITS,
} from './labels.ts'

export const MAX_FILE_BYTES = 2 * 1024 * 1024
const MAX_COUNT = 2 ** 53 - 1
const KEYS = Object.keys(LABELS) as (keyof typeof LABELS)[]

export type Parsed = { ok: true; card: Scorecard } | { ok: false; error: string }

// Same rule as models.review_points: null when nothing is declared, 0 and 10 reserved for none and all.
export function reviewPoints(done: number, total: number): number | null {
  if (total === 0) return null
  if (done === 0) return 0
  if (done === total) return 10
  return Math.min(9, Math.max(1, Math.floor((10 * done) / total)))
}

const isCount = (value: unknown, max = MAX_COUNT): value is number =>
  typeof value === 'number' && Number.isInteger(value) && value >= 0 && value <= max
const isText = (value: unknown, max = 256): value is string => typeof value === 'string' && value.length > 0 && value.length <= max
const has = (table: object, key: unknown): boolean => typeof key === 'string' && Object.hasOwn(table, key)

function dimensionProblem(item: any, index: number): string | null {
  if (item === null || typeof item !== 'object' || item.key !== KEYS[index]) return 'meters are missing or out of order'
  if (!isCount(item.done) || !isCount(item.total) || item.done > item.total) return 'meter counts are not valid'
  if (item.points !== reviewPoints(item.done, item.total)) return 'meter points disagree with its counts'
  if (item.ceiling !== null && (index !== 0 || !isCount(item.ceiling?.points, 10) || item.ceiling.points < item.points)) {
    return 'a ceiling is not valid'
  }
  for (const list of [item.counts, item.reasons]) {
    if (!Array.isArray(list) || list.some((entry: any) => !has(TAG_LABELS, entry?.key) || !isCount(entry.count) || entry.count < 1)) {
      return 'meter counts use unknown words'
    }
  }
  if (!Array.isArray(item.open_items) || item.open_items.length > MAX_OPEN_ITEMS || !isCount(item.open_total)
    || item.open_total !== item.total - item.done) return 'open items are not valid'
  for (const entry of item.open_items) {
    if (!isText(entry?.id, 128) || !(entry.method === null || isText(entry.method)) || !Array.isArray(entry.reasons)
      || entry.reasons.length === 0 || entry.reasons.some((tag: unknown) => !has(TAG_LABELS, tag))) return 'open items are not valid'
  }
  return null
}

// Checks the shape and arithmetic the contract guarantees; anything else is refused, never guessed.
export function parseScorecard(text: string): Parsed {
  if (text.length > MAX_FILE_BYTES) return { ok: false, error: 'The file is too large for a scorecard.' }
  let card: any
  try {
    card = JSON.parse(text)
  } catch {
    return { ok: false, error: 'The file is not JSON.' }
  }
  const refuse = (why: string): Parsed => ({ ok: false, error: `Not a scorecard this page can show: ${why}.` })
  if (card === null || typeof card !== 'object' || card.schema_version !== 1 || card.scorer_version !== 1) return refuse('unknown version')
  if (card.notice !== NOTICE) return refuse('the notice is missing')
  if (!has(STATUS_LABELS, card.status) || typeof card.synthetic !== 'boolean' || typeof card.offline !== 'boolean') return refuse('unknown status')
  if (!isText(card.run_id, 128) || !isText(card.project_id, 128) || !isText(card.run_state, 32)) return refuse('run is not named')
  if (!Array.isArray(card.dimensions) || card.dimensions.length !== KEYS.length) return refuse('meters are missing')
  for (const [index, item] of card.dimensions.entries()) {
    const problem = dimensionProblem(item, index)
    if (problem) return refuse(problem)
  }
  const screening = card.screening
  if (!isCount(screening?.screened, 11) || screening.total !== 11 || !isCount(screening.applicable, 11)
    || !isCount(screening.not_applicable, 11) || !isCount(screening.withdrawn, 11)) return refuse('screening is not valid')
  if (!Array.isArray(card.hygiene) || card.hygiene.length !== 3
    || card.hygiene.some((item: any) => !has(HYGIENE_LABELS, item?.key) || !isCount(item.done) || !isCount(item.total) || item.done > item.total)) {
    return refuse('record hygiene is not valid')
  }
  if (!Array.isArray(card.attention) || card.attention.some((item: any) => !has(ATTENTION_LABELS, item?.key) || !isCount(item.count))) {
    return refuse('attention is not valid')
  }
  const step = card.next_step
  if (step !== null && (!has(STEP_TEXT, step?.kind) || !(step.subject === null || isText(step.subject, 128)) || !isCount(step.unblocks))) {
    return refuse('the next step is not valid')
  }
  if (!isCount(card.notes_outside) || !(card.assessed_days_before_run === null || isCount(card.assessed_days_before_run))) {
    return refuse('counts are not valid')
  }
  return { ok: true, card: card as Scorecard }
}

export type Cell = 'on' | 'off' | 'cap'
export type Tone = 'status' | 'plain' | 'bad' | 'fiction'
export type MeterView = {
  key: string
  label: string
  points: string
  cells: Cell[]
  ariaLabel: string
  line: string
  hint: string | null
  counts: string[]
  reasons: string[]
  ceiling: string | null
  focus: boolean
  openItems: string[]
  openMore: number
}
export type DashboardView = {
  run: string
  fictional: boolean
  chips: { text: string; tone: Tone }[]
  hero: MeterView
  tiles: MeterView[]
  next: string
  screening: string
  screeningDetail: string
  hygiene: string[]
  trend: string | null
  notice: string
  howItWorks: { label: string; text: string }[]
}

export function cells(points: number | null, ceiling: number | null): Cell[] {
  if (points === null) return Array(10).fill('off')
  const reachable = ceiling ?? 10
  return [...Array(points).fill('on'), ...Array(reachable - points).fill('off'), ...Array(10 - reachable).fill('cap')]
}

const pointsText = (points: number | null) => (points === null ? 'not scored: nothing declared' : `${points}/10`)

// Same rule as models.raise_hint: the fewest items to close for the next point step.
export function raiseText(done: number, total: number): string | null {
  const points = reviewPoints(done, total)
  if (points === null || points === 10) return null
  for (let more = 1; done + more <= total; more++) {
    const after = reviewPoints(done + more, total)!
    if (after > points) return `+${after - points} pt${after - points === 1 ? '' : 's'}: close ${more} more`
  }
  return null
}

export function describeStep(step: ScoreNextStep): string {
  const what = STEP_TEXT[step.kind].replace('{subject}', step.subject ?? '')
  return `${what} · unblocks ${step.unblocks} open requirement${step.unblocks === 1 ? '' : 's'}`
}

function ceilingText(item: ScoreDimension, offline: boolean): string | null {
  const ceiling = item.ceiling
  if (!ceiling) return null
  const parts = []
  if (ceiling.technical) parts.push(`${ceiling.technical} rest on technical checks this workflow never runs`)
  if (ceiling.unconfirmed_sources) {
    parts.push(`${ceiling.unconfirmed_sources} rest on real sources ${offline
      ? 'an offline run cannot confirm (run revalidate --fetch-official)' : 'the official retrieval did not confirm'}`)
  }
  return `max reachable in this run: ${ceiling.points}/10; ${parts.join('; ')}.`
}

function meter(item: ScoreDimension, card: Scorecard): MeterView {
  const key = item.key as keyof typeof LABELS
  return {
    key,
    label: LABELS[key],
    points: pointsText(item.points),
    cells: cells(item.points, item.ceiling?.points ?? null),
    ariaLabel: item.points === null ? 'not scored' : `${item.points} of 10 points`,
    line: `${item.done} of ${item.total} ${UNITS[key]}`,
    hint: raiseText(item.done, item.total),
    counts: item.counts.map(entry => `${TAG_LABELS[entry.key]} ×${entry.count}`),
    reasons: item.reasons.map(entry => `${TAG_LABELS[entry.key]} ×${entry.count}`),
    ceiling: ceilingText(item, card.offline),
    focus: card.next_step?.focus === item.key,
    openItems: item.open_items.map(entry => `${entry.id}${entry.method ? ` · ${entry.method}` : ''} — ${
      entry.reasons.map(tag => TAG_LABELS[tag]).join(', ')}`),
    openMore: item.open_total - item.open_items.length,
  }
}

// Everything the page shows, as plain strings: React renders them as text, never as HTML.
export function present(card: Scorecard): DashboardView {
  const chips: DashboardView['chips'] = [
    { text: `● ${STATUS_LABELS[card.status]}`, tone: 'status' },
    { text: `assembly: ${card.run_state} (processing state)`, tone: 'plain' },
    { text: card.offline ? 'offline' : 'official retrieval', tone: 'plain' },
  ]
  if (card.assessed_days_before_run !== null) chips.push({ text: `assessed ${card.assessed_days_before_run} days before run`, tone: 'plain' })
  chips.push({ text: `notes outside the meters: ${card.notes_outside}`, tone: 'plain' })
  for (const item of card.attention) {
    chips.push({ text: `${ATTENTION_LABELS[item.key]} ×${item.count}`, tone: item.key === 'reviewer_recorded_insufficient' ? 'bad' : 'plain' })
  }
  if (card.synthetic) chips.unshift({ text: 'fictional data', tone: 'fiction' })
  const [hero, ...rest] = card.dimensions.map(item => meter(item, card))
  const trend = card.trend
  return {
    run: `Project ${card.project_id} · run ${card.run_id} · assessment date ${card.assessment_date}`,
    fictional: card.synthetic,
    chips,
    hero: hero!,
    tiles: rest,
    next: card.next_step ? describeStep(card.next_step) : 'No recorded step is open. That is not a compliance conclusion.',
    screening: `${card.screening.screened} of ${card.screening.total} families screened`,
    screeningDetail: `applies ${card.screening.applicable} · does not apply ${card.screening.not_applicable} · withdrawn ${card.screening.withdrawn}`,
    hygiene: card.hygiene.map(item => `${HYGIENE_LABELS[item.key]}: ${item.done} of ${item.total}`),
    trend: !trend ? null : trend.comparable
      ? `Since the parent run: ${trend.deltas.map(item => `${LABELS[item.key]} ${pointsText(item.points_before)} → ${pointsText(item.points_after)}`).join(' · ')}`
      : 'Trend unavailable: that run is not comparable with this one.',
    notice: NOTICE,
    howItWorks: KEYS.map(key => ({ label: LABELS[key], text: `${UNITS[key]}. ${HOW_TO_RAISE[key]}` })),
  }
}
