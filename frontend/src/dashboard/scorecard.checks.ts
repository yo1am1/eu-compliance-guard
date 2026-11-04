// Node's built-in runner with type stripping: `npm test` (not named *.test.ts, which `claude plugin test` collects).
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'

import { cells, parseScorecard, present, raiseText, reviewPoints } from './scorecard.ts'

const FIXTURE = readFileSync(new URL('../../../fixtures/scorecard-synthetic.json', import.meta.url), 'utf8')
const BANNED = ['compliant', 'compliance score', 'certified', 'approved', 'safe to', 'risk score', 'grade', 'healthy', 'violation']

function parsed() {
  const result = parseScorecard(FIXTURE)
  assert.equal(result.ok, true)
  return (result as { ok: true; card: any }).card
}

test('the synthetic scorecard renders the golden meters and no total', () => {
  const view = present(parsed())
  assert.deepEqual([view.hero, ...view.tiles].map(meter => meter.points), ['5/10', '10/10', '3/10', '5/10', '5/10', '5/10'])
  assert.equal(view.hero.line, '1 of 2 requirements supported')
  assert.equal(view.hero.hint, '+5 pts: close 1 more')
  assert.deepEqual(view.hero.reasons, ['no mapping ×1'])
  assert.equal(view.next, 'Map requirement-unmapped to a candidate obligation · unblocks 1 open requirement')
  assert.equal(view.tiles.find(meter => meter.focus)?.key, 'mapping')
  assert.equal(view.screening, '0 of 11 families screened')
  assert.equal(view.fictional, true)
  assert.equal(view.chips[0]?.text, 'fictional data')
  assert.equal(view.chips[1]?.text, '● In review')
  const words = JSON.stringify(view).replace(view.notice, '').toLowerCase()
  for (const word of BANNED) assert.equal(words.includes(word), false, word)
  assert.equal(words.includes('total'), words.includes('no total exists'))
  assert.equal(words.includes('average'), false)
})

test('points and hints follow the contract rule', () => {
  assert.deepEqual([reviewPoints(0, 0), reviewPoints(0, 3), reviewPoints(1, 3), reviewPoints(3, 3), reviewPoints(10, 11)],
    [null, 0, 3, 10, 9])
  assert.equal(raiseText(1, 200), '+1 pt: close 39 more')
  assert.equal(raiseText(2, 2), null)
  assert.deepEqual(cells(3, 5), ['on', 'on', 'on', 'off', 'off', 'cap', 'cap', 'cap', 'cap', 'cap'])
  assert.deepEqual(cells(null, null), Array(10).fill('off'))
})

test('anything that is not a consistent scorecard is refused', () => {
  const card = JSON.parse(FIXTURE)
  const broken = [
    'not json',
    JSON.stringify({ ...card, notice: 'A compliance score.' }),
    JSON.stringify({ ...card, status: 'compliant' }),
    JSON.stringify({ ...card, dimensions: card.dimensions.slice(1) }),
    JSON.stringify({ ...card, dimensions: [{ ...card.dimensions[0], points: 6 }, ...card.dimensions.slice(1)] }),
    JSON.stringify({ ...card, dimensions: [{ ...card.dimensions[0], reasons: [{ key: '<script>', count: 1 }] }, ...card.dimensions.slice(1)] }),
    JSON.stringify({ ...card, next_step: { ...card.next_step, kind: 'deploy' } }),
    JSON.stringify({ ...card, screening: { ...card.screening, screened: 12 } }),
    'x'.repeat(3 * 1024 * 1024),
  ]
  for (const text of broken) assert.equal(parseScorecard(text).ok, false, text.slice(0, 80))
})

test('declared ids and methods stay plain text', () => {
  const card = JSON.parse(FIXTURE)
  card.dimensions[5].open_items[0].method = '<img src=x onerror=alert(1)>'
  const result = parseScorecard(JSON.stringify(card))
  assert.equal(result.ok, true)
  const view = present((result as { ok: true; card: any }).card)
  assert.equal(view.tiles[4]?.openItems[0], 'obligation-unmapped · <img src=x onerror=alert(1)> — not started')
})
