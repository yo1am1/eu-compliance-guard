// Review-progress page for one run's `views/<run>.scorecard.json`, chosen from disk: nothing is fetched.
import { useState } from 'react'
import type { ChangeEvent, DragEvent } from 'react'

import './dashboard.css'
import { MAX_FILE_BYTES, parseScorecard, present } from './scorecard.ts'
import type { DashboardView, MeterView } from './scorecard.ts'

function Bar({ meter }: { meter: MeterView }) {
  return (
    <span className="bar" role="img" aria-label={meter.ariaLabel}>
      {meter.cells.map((cell, index) => <i key={index} className={cell} />)}
    </span>
  )
}

function OpenItems({ meter }: { meter: MeterView }) {
  if (meter.openItems.length === 0) return null
  return (
    <details>
      <summary>open items ({meter.openItems.length + meter.openMore})</summary>
      <ul>
        {meter.openItems.map(item => <li key={item}>{item}</li>)}
        {meter.openMore > 0 ? <li className="muted">and {meter.openMore} more</li> : null}
      </ul>
    </details>
  )
}

function Fiction({ view }: { view: DashboardView }) {
  return view.fictional ? <span className="chip fiction">fictional data</span> : null
}

function Tile({ meter, view }: { meter: MeterView; view: DashboardView }) {
  return (
    <section className={meter.focus ? 'tile focus' : 'tile'} aria-label={`${meter.label} meter`}>
      <h3><span>{meter.label}</span><span>{meter.points}</span></h3>
      <Bar meter={meter} /> <Fiction view={view} />
      <p>{meter.line}</p>
      {meter.counts.length ? <p className="muted">{meter.counts.join(' · ')}</p> : null}
      {meter.reasons.length ? <p className="muted">open: {meter.reasons.join(' · ')}</p> : null}
      {meter.hint ? <p>{meter.hint}</p> : null}
      {meter.focus ? <p className="muted">focus of the next step</p> : null}
      <OpenItems meter={meter} />
    </section>
  )
}

export function ScorecardView({ view }: { view: DashboardView }) {
  const hero = view.hero
  return (
    <section className="progress" aria-labelledby="review-progress">
      <div className="head">
        <h2 id="review-progress">Review progress</h2>
        <span className="muted">points out of 10 · from this run's records</span>
      </div>
      <p className="muted run">{view.run}</p>
      <div className="chips">{view.chips.map(chip => <span key={chip.text} className={`chip ${chip.tone}`}>{chip.text}</span>)}</div>
      <div className={hero.focus ? 'hero focus' : 'hero'}>
        <b>{hero.label.toUpperCase()}</b><span className="pts">{hero.points}</span><Bar meter={hero} /> <Fiction view={view} />
        <p>{hero.line}{hero.hint ? <span className="muted"> · {hero.hint}</span> : null}</p>
        {hero.reasons.length ? <p className="muted">blockers: {hero.reasons.join(' · ')}</p> : null}
        {hero.ceiling ? <p className="muted">{hero.ceiling}</p> : null}
        {hero.counts.length ? <p>{hero.counts.join(' · ')}</p> : null}
        <OpenItems meter={hero} />
      </div>
      <div className="cta"><b>▶ NEXT</b> {view.next}<br /><span className="muted">CLI: <code>eu-compliance-guard next</code> lists the ranked steps.</span></div>
      <p className="notice">{view.notice}</p>
      <div className="tiles">
        {view.tiles.map(meter => <Tile key={meter.key} meter={meter} view={view} />)}
        <section className="tile" aria-label="Screening">
          <h3><span>Screening</span><span className="muted">not scored</span></h3> <Fiction view={view} />
          <p>{view.screening}</p>
          <p className="muted">{view.screeningDetail}</p>
        </section>
        <section className="tile" aria-label="Record hygiene">
          <h3><span>Record hygiene</span><span className="muted">not scored</span></h3> <Fiction view={view} />
          {view.hygiene.map(line => <p key={line}>{line}</p>)}
        </section>
      </div>
      {view.trend ? <p className="muted">{view.trend}</p> : null}
      <details>
        <summary>How points work</summary>
        <p>Each meter counts closed items of one kind: none closed is 0, all closed is 10, otherwise ten times the closed
          share rounded down, kept between 1 and 9. A meter with nothing declared is not scored. Meters are never added or
          averaged; no total exists.</p>
        <ul>{view.howItWorks.map(item => <li key={item.label}><b>{item.label}</b>: {item.text}</li>)}</ul>
      </details>
    </section>
  )
}

export function Dashboard() {
  const [view, setView] = useState<DashboardView | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function open(file: File | undefined) {
    if (!file) return
    if (file.size > MAX_FILE_BYTES) {
      setError('The file is too large for a scorecard.')
      return
    }
    const parsed = parseScorecard(await file.text())
    setError(parsed.ok ? null : parsed.error)
    setView(parsed.ok ? present(parsed.card) : null)
  }

  return (
    <main
      onDragOver={(event: DragEvent) => event.preventDefault()}
      onDrop={(event: DragEvent) => {
        event.preventDefault()
        void open(event.dataTransfer.files[0])
      }}
    >
      <h1>EU Compliance Guard</h1>
      <p className="muted">
        Choose a run's <code>views/&lt;run&gt;.scorecard.json</code> (written by <code>eu-compliance-guard view</code>) or drop it
        here. The file is read in this browser only; nothing is uploaded or fetched.
      </p>
      <label className="pick">
        Open scorecard…
        <input type="file" accept=".json,application/json"
          onChange={(event: ChangeEvent<HTMLInputElement>) => void open(event.target.files?.[0])} />
      </label>
      {error ? <p className="error" role="alert">{error}</p> : null}
      {view ? <ScorecardView view={view} /> : null}
    </main>
  )
}
