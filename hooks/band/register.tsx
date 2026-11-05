import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Band, NextSteps } from '../../types'
import {
  daysOld, describeMeter, describeStep, meterRow, parseScores, parseSteps, progressBar, progressLine, SCORE_NOTICE, statusWord,
  summarize, words, errorCode, baseName, parseCandidates,
} from './summary'

const LEVELS = ['lite', 'full', 'strict', 'off']
const PROJECT_ID = /^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/
const EMPTY: Band = { isActive: false, level: 'full', stateDir: '', run: null, problem: null }
// Shape tags decline values an earlier version stored, which outlive a reload.
const band = atom({ plugin: 'eu-compliance-guard', key: 'band' } as const, EMPTY, { shape: 'band-3' })
const isFolded = atom({ plugin: 'eu-compliance-guard', key: 'isFolded' } as const, false)
const lastView = atom({ plugin: 'eu-compliance-guard', key: 'lastView' } as const, null)
const nextSteps = atom({ plugin: 'eu-compliance-guard', key: 'next' } as const, null as NextSteps | null, { shape: 'next-5' })
// Run directories being ranked now, so turns that end while the CLI runs start no second process.
const ranking = new Set<string>()
const PANE = 'eucg-panel'
const PANE_TITLE = 'EU Compliance Guard'

// The same default level the SessionStart hook reads: EUCG_DEFAULT_MODE, then the config file.
async function readLevel($: EngineInterface, home: string): Promise<string> {
  let level = ((await $.env.get('EUCG_DEFAULT_MODE')) ?? '').trim().toLowerCase()
  if (level === '') {
    const config = `${(await $.env.get('XDG_CONFIG_HOME')) || `${home}/.config`}/eu-compliance-guard/config.json`
    try {
      const parsed = JSON.parse(await $.fs.read(config))
      level = typeof parsed?.defaultMode === 'string' ? parsed.defaultMode.toLowerCase() : ''
    } catch {
      level = ''
    }
  }
  return LEVELS.includes(level) ? level : 'full'
}

// Finds the newest completed run (latest completion, then name) and summarizes it.
// The declared project_id keys run storage, exactly as `eu-compliance-guard state-dir` and the session hook do.
async function declaredProject($: EngineInterface, project: string): Promise<string | null> {
  try {
    const value = JSON.parse(await $.fs.read(`${project}/.eu-compliance-guard/declarations.json`))?.project_id
    return typeof value === 'string' && PROJECT_ID.test(value) ? value : null
  } catch {
    return null
  }
}

// An empty or relative XDG_STATE_HOME counts as unset (XDG Base Directory spec), as in the session hook and the CLI.
// `rerank` (Refresh, /eucg-panel) retries a ranking that failed for the newest run.
async function refresh($: EngineInterface, rerank = false): Promise<void> {
  const home = (await $.env.get('HOME')) ?? ''
  // The session's project root, like the hook's CLAUDE_PROJECT_DIR; a worktree is its own project.
  const project = await $.session.root()
  const level = await readLevel($, home)
  const entries = await $.fs.list(project).catch(() => [])
  const isActive = level !== 'off' && entries.some(entry => entry.name === '.eu-compliance-guard' && entry.kind === 'dir')
  const identity = isActive ? await declaredProject($, project) : null
  const configured = (await $.env.get('XDG_STATE_HOME')) ?? ''
  const stateHome = configured.startsWith('/') ? configured : `${home}/.local/state`
  const stateDir = identity ? `${stateHome}/eu-compliance-guard/${identity}` : ''
  let run = null
  let problem = null
  let previousGaps: number | null = null
  let previousDir: string | null = null
  if (identity !== null) {
    const runs = (await $.fs.list(stateDir).catch(() => []))
      .filter(entry => entry.kind === 'dir' && !entry.isLink && entry.name.startsWith('run-'))
      // Newest completion first: a run folder changes last when its completion marker is written.
      .sort((a, b) => b.mtimeMs - a.mtimeMs || (a.name < b.name ? 1 : a.name > b.name ? -1 : 0))
      .map(entry => entry.name)
    for (const name of runs) {
      const files = await $.fs.list(`${stateDir}/${name}`).catch(() => [])
      if (!files.some(file => file.name === 'complete.json' && file.kind === 'file')) continue
      if (run !== null) {
        // The run before the newest, for progress since then.
        const previous = summarize(`${stateDir}/${name}`, await $.fs.read(`${stateDir}/${name}/bundle.json`).catch(() => ''))
        if (previous?.projectId === identity) {
          previousGaps = previous.gaps
          previousDir = `${stateDir}/${name}`
        }
        break
      }
      run = summarize(`${stateDir}/${name}`, await $.fs.read(`${stateDir}/${name}/bundle.json`).catch(() => ''))
      if (run === null) problem = 'latest run could not be summarized'
      else if (run.projectId !== identity) {
        run = null
        problem = 'latest run belongs to another project'
      }
      if (run === null) break
    }
  }
  await update($, band, () => ({ isActive, level, stateDir, run, problem, previousGaps, previousDir }))
  // Scored once per run, in the background, so a slow interpreter start never holds the session.
  const ranked = run === null ? null : await read($, nextSteps)
  if (run !== null && (ranked?.dir !== run.dir || (rerank && (ranked.steps === null || ranked.scores === null)))) {
    void rankScore($, run.dir, previousDir)
  }
}

// Runs the plugin's own CLI: uv with the locked environment when available, else python3 on PYTHONPATH.
// -P keeps the session's directory off sys.path, so a project's own package cannot stand in for the CLI.
async function cli($: EngineInterface, args: string[], timeoutMs = 120_000) {
  const root = $.plugin.root
  const hasUv = await $.process.run(['uv', '--version']).then(r => r.exitCode === 0).catch(() => false)
  const argv = hasUv
    ? ['uv', 'run', '--project', root, '--locked', '--no-dev', 'python', '-P', '-m', 'eu_compliance_guard', ...args]
    : ['python3', '-P', '-m', 'eu_compliance_guard', ...args]
  return $.process.run(argv, { timeoutMs, ...(hasUv ? {} : { env: { PYTHONPATH: root } }) }).catch(() => undefined)
}

// The CLI refuses symlinked path components; a home folder may be one (for example /home -> /var/home).
async function resolve($: EngineInterface, linked: string) {
  const resolved = await $.process.run(['realpath', '--', linked]).catch(() => undefined)
  return resolved?.exitCode === 0 && resolved.stdout.trim() !== '' ? resolved.stdout.trim() : linked
}

// Ranks and scores a run once (`score --json` carries both): a failure is stored for that run too,
// so it is not retried on every turn. Against the previous run only for its display-only deltas.
async function rankScore($: EngineInterface, dir: string, previousDir: string | null) {
  if (ranking.has(dir)) return
  ranking.add(dir)
  try {
    const against = previousDir === null ? [] : ['--against', await resolve($, previousDir)]
    const result = await cli($, ['score', '--run', await resolve($, dir), '--json', '--top', '3', ...against], 60_000)
    const ok = result?.exitCode === 0
    // Each open fact's best code line, for the panel; the CLI validates nothing here, the parser does.
    const project = await $.session.root()
    const grounded = await cli($, ['ground', '--input', await resolve($, `${project}/.eu-compliance-guard/declarations.json`),
      '--json', '--top', '1'], 60_000)
    const candidates = grounded?.exitCode === 0 ? parseCandidates(grounded.stdout) : null
    const ranked = { dir, steps: (ok ? parseSteps(dir, result.stdout)?.steps : null) ?? null, scores: ok ? parseScores(result.stdout) : null,
      candidates }
    // A slow ranking of an older run never replaces the newest run's.
    if ((await read($, band))?.run?.dir === dir) await update($, nextSteps, () => ranked)
  } finally {
    ranking.delete(dir)
  }
}

// Plugin skills may be listed bare or under the plugin's namespace.
async function runSkill($: EngineInterface, name: string) {
  const commands = await $.command.list()
  const found = commands.find(command => command.name === name || command.name.endsWith(`:${name}`))
  if (found === undefined) {
    $.ui.toast(`EU Compliance Guard: /${name} is not available in this session`)
    return
  }
  await $.command.run({ command: found.name })
}

// Writes the run's HTML view with the plugin's own CLI and opens it in the default browser.
// The dashboard is one static page the CLI writes beside the report and opens in the browser, like the report.
async function openReport($: EngineInterface, linked: string, dashboard = false) {
  const result = await cli($, ['view', '--run', await resolve($, linked), ...(dashboard ? ['--dashboard'] : []), '--open'])
  const path = result?.exitCode === 0 ? result.stdout.trim().split('\n').pop() ?? '' : ''
  if (path === '') {
    // stderr carries only the CLI's fixed safe code.
    const code = errorCode(result?.stderr) ?? 'view-failed'
    $.ui.toast(`EU Compliance Guard: report view failed (${code})`)
    return
  }
  if (!dashboard) await update($, lastView, () => path)
  const what = dashboard ? 'Dashboard' : 'Report'
  $.ui.toast(result?.stderr.includes('no-browser') ? `${what} written: ${path}` : `${what} opened in your browser`)
}

// The project graph is one static page in the state folder, written from the checked-out code.
async function openGraph($: EngineInterface) {
  const project = await $.session.root()
  const declarations = await resolve($, `${project}/.eu-compliance-guard/declarations.json`)
  const result = await cli($, ['graph', '--input', declarations, '--view', '--open'])
  const path = result?.exitCode === 0 ? result.stdout.trim().split('\n').pop() ?? '' : ''
  if (path === '') {
    $.ui.toast(`EU Compliance Guard: graph view failed (${errorCode(result?.stderr) ?? 'graph-failed'})`)
    return
  }
  $.ui.toast(result?.stderr.includes('no-browser') ? `Graph written: ${path}` : 'Graph opened in your browser')
}

// "▓▓▓░░░ 3/12 requirements supported · 94 open items (−7 since last run)": progress first, never a verdict.
function summaryLine(run: NonNullable<Band['run']>, previousGaps: number | null): string {
  const delta = previousGaps === null ? '' : run.gaps < previousGaps ? ` (−${previousGaps - run.gaps} since last run)`
    : run.gaps > previousGaps ? ` (+${run.gaps - previousGaps} since last run)` : ' (same as last run)'
  return `${progressBar(run.requirements.supported, run.requirements.total)} requirements supported · ${run.gaps} open items${delta}`
}

async function openPanel($: EngineInterface) {
  const { isPlaced } = await $.ui.open({ id: PANE, title: PANE_TITLE })
  if (!isPlaced) $.ui.toast('EU Compliance Guard: this surface cannot show the panel now')
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    const started = await next(e)
    await $.command.register({ name: 'eucg-panel', description: 'Show the latest EU Compliance Guard run in a side panel' })
    await refresh($)
    return started
  })

  on('command.run', { command: 'eucg-panel' }, async $ => {
    await refresh($, true)
    const { isPlaced } = await $.ui.open({ id: PANE, title: PANE_TITLE })
    return { text: isPlaced ? 'EU Compliance Guard panel opened.' : 'This surface cannot show the panel now.' }
  })

  // The panel: the band's run plus ranked steps, owner questions and gaps by area, all fixed-format.
  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Button, Text } = $.ui.resolve(e)
    const b = { ...EMPTY, ...(await read($, band)) }
    const run = b.run
    if (!b.isActive || run === null) {
      return (
        <Box flexDirection="column" gap={1}>
          <Text dimColor>{b.isActive ? b.problem ?? 'No completed run yet.'
            : b.level === 'off' ? 'The default level is off; resume with /eucg.' : 'No .eu-compliance-guard/ declarations in this project.'}</Text>
          {b.isActive ? <Button key="audit" label="Run an audit" variant="primary" onPress={() => runSkill($, 'eucg-audit')} /> : null}
        </Box>
      )
    }
    const ranked = await read($, nextSteps)
    const isRanked = ranked?.dir === run.dir
    const steps = isRanked ? ranked.steps : null
    const scores = isRanked ? ranked.scores ?? null : null
    const age = daysOld(run.assessmentDate, await $.clock.now())
    const questions = run.questions ?? []
    const questionsTotal = run.questionsTotal ?? questions.length
    const areas = run.areas ?? []
    return (
      <Box flexDirection="column" gap={1}>
        <Box flexDirection="column">
          <Text bold>{summaryLine(run, b.previousGaps ?? null)}</Text>
          <Text dimColor>run {run.id} · state {run.state} · assessed {run.assessmentDate}{age === null ? '' : ` (${age}d ago)`}</Text>
          {run.synthetic ? <Text color="yellow">fictional data</Text> : null}
        </Box>
        {scores ? (
          <Box flexDirection="column">
            <Text bold>{`Review progress · ● ${statusWord(scores)}${scores.synthetic ? ' · fictional data' : ''}`}</Text>
            {scores.meters.map(meter => <Text>{describeMeter(meter)}</Text>)}
            <Text>{`Screening  ${scores.screened} of 11 families screened (not scored)`}</Text>
            <Text dimColor>{SCORE_NOTICE}</Text>
          </Box>
        ) : null}
        <Box flexDirection="column">
          <Text bold>Next best steps</Text>
          {!isRanked ? <Text dimColor>ranking…</Text> : steps === null ? <Text dimColor>Ranking unavailable; see the report.</Text>
            : steps.length === 0 ? <Text dimColor>No recorded step is open.</Text> : null}
          {(steps ?? []).map((step, index) => <Text>{`${index + 1}. ${describeStep(step)}`}</Text>)}
          {steps && steps.length > 0 ? <Button key="next" label="Work on step 1" variant="primary" onPress={() => runSkill($, 'eucg-next')} /> : null}
        </Box>
        <Box flexDirection="column">
          <Text bold>Questions for the owner ({questionsTotal})</Text>
          {questions.length === 0 ? <Text dimColor>Every declared fact is declared or observed.</Text> : null}
          {questions.slice(0, 12).map(item => {
            const code = (isRanked ? ranked.candidates ?? [] : []).find(candidate => candidate.fact === item.id)
            return <Text>{`${words(item.id)}? · now ${item.basis}${code ? ` · code ${code.location}` : ''}`}</Text>
          })}
          {questionsTotal > 12 ? <Text dimColor>{`and ${questionsTotal - 12} more in the report`}</Text> : null}
          {isRanked && (ranked.candidates ?? []).some(candidate => questions.some(item => item.id === candidate.fact))
            ? <Button key="confirm" label="Confirm code evidence" onPress={() => runSkill($, 'eucg-next')} /> : null}
        </Box>
        <Box flexDirection="column">
          <Text bold>Open gaps by area</Text>
          {areas.length === 0 ? <Text dimColor>No open gaps recorded.</Text> : null}
          {areas.map(item => <Text>{`${item.count} · ${item.area}`}</Text>)}
        </Box>
        <Box flexDirection="row" gap={1}>
          <Button key="dashboard" label="Dashboard" variant="primary" onPress={() => openReport($, run.dir, true)} />
          <Button key="graph" label="Graph" onPress={() => openGraph($)} />
          <Button key="report" label="Open report" onPress={() => openReport($, run.dir)} />
          <Button key="gaps" label="Gaps" onPress={() => runSkill($, 'eucg-gaps')} />
          <Button key="refresh" label="Refresh" onPress={() => refresh($, true)} />
        </Box>
        <Text dimColor>Workflow guidance from the recorded run; not a compliance verdict or legal advice.</Text>
      </Box>
    )
  })

  // A run usually finishes inside a turn (/eucg-audit), so the band rereads after each one.
  on('turn.complete', async ($, e, next) => {
    const done = await next(e)
    await refresh($)
    return done
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const b = { ...EMPTY, ...(await read($, band)) }
    if (e.props.hasSurvey || !b.isActive) return next(e)
    const { Box, Button, Link, Text } = $.ui.resolve(e)
    const folded = await read($, isFolded)
    const run = b.run
    const age = run ? daysOld(run.assessmentDate, await $.clock.now()) : null
    const fold = (
      <Button key="fold" label={folded ? '+' : '–'} plain onPress={() => update($, isFolded, value => !value)} />
    )
    const ranked = await read($, nextSteps)
    const stepForRun = run && ranked?.dir === run.dir ? ranked.steps?.[0] ?? null : null
    const scores = run && ranked?.dir === run.dir ? ranked.scores ?? null : null
    const status = !run ? b.problem ?? 'no completed run yet' : scores ? progressLine(scores) : summaryLine(run, b.previousGaps ?? null)
    if (folded) {
      const alignment = scores?.meters[0]
      const brief = scores && alignment
        ? `${statusWord(scores)} · Alignment ${alignment.points === null ? 'not scored' : `${alignment.points}/10`}`
          + (stepForRun ? ` · Next: ${describeStep(stepForRun)}` : '') + (scores.synthetic ? ' · fictional data' : '')
        : status
      return (
        <Box flexDirection="row" gap={1}>
          <Text dimColor>EU Compliance Guard · {brief}</Text>
          {fold}
        </Box>
      )
    }
    const view = await read($, lastView)
    const context = run ? (
      <Text dimColor>
        {`${scores ? '' : ' · '}assessed ${run.assessmentDate}${age === null ? '' : ` (${age}d ago)`}`}
        {run.attempts.total > 0 ? ` · sources ${run.attempts.retrieved}/${run.attempts.total} retrieved` : ''}
      </Text>
    ) : null
    // A view written for an older run must not stand for the newest run the band summarizes.
    const runName = run ? baseName(run.dir) : null
    const viewForRun = view && runName && view.endsWith(`/views/${runName}.html`) ? view : null
    return (
      <Box flexDirection="column">
        <Box flexDirection="row" gap={1}>
          <Text bold>EU Compliance Guard</Text>
          <Text dimColor>default level {b.level}</Text>
          {run?.synthetic ? <Text color="yellow">fictional data</Text> : null}
          {fold}
        </Box>
        <Text>
          {status}
          {run ? <Text dimColor>{` · state ${run.state}`}</Text> : null}
          {run && !scores ? context : null}
        </Text>
        {scores ? <Text dimColor>{meterRow(scores)}</Text> : null}
        {/* With meters the context gets its own row, so each row fits the band's width. */}
        {scores ? <Text dimColor>{context}{` · ${scores.screened} of 11 families screened`}</Text> : null}
        {stepForRun ? <Text color="cyan">Next: {describeStep(stepForRun)}</Text> : null}
        <Box flexDirection="row" gap={1}>
          {stepForRun ? <Button key="next" label="Next step" variant="primary" hotkey="n" onPress={() => runSkill($, 'eucg-next')} /> : null}
          <Button key="audit" label="Audit" variant={stepForRun ? undefined : 'primary'} hotkey="a" onPress={() => runSkill($, 'eucg-audit')} />
          <Button key="review" label="Review diff" hotkey="r" onPress={() => runSkill($, 'eucg-review')} />
          {run ? <Button key="gaps" label="Gaps" hotkey="g" onPress={() => runSkill($, 'eucg-gaps')} /> : null}
          {run ? <Button key="dashboard" label="Dashboard" hotkey="d" onPress={() => openReport($, run.dir, true)} /> : null}
          {run ? <Button key="report" label="Open report" hotkey="o" onPress={() => openReport($, run.dir)} /> : null}
          {run ? <Button key="panel" label="Panel" hotkey="p" onPress={() => openPanel($)} /> : null}
          <Button key="help" label="Help" hotkey="h" onPress={() => runSkill($, 'eucg-help')} />
        </Box>
        {viewForRun ? <Link href={`file://${viewForRun}`} label={`Report view: ${viewForRun}`} /> : null}
        <Text dimColor>{scores ? SCORE_NOTICE : 'Processing state is not a compliance verdict.'}</Text>
      </Box>
    )
  })
}
