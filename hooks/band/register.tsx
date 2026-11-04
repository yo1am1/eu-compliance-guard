import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Band, NextStep } from '../../types'
import { daysOld, describeStep, parseStep, summarize } from './summary'

const LEVELS = ['lite', 'full', 'strict', 'off']
const PROJECT_ID = /^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/
const EMPTY: Band = { isActive: false, level: 'full', stateDir: '', run: null, problem: null }
const band = atom({ plugin: 'eu-compliance-guard', key: 'band' } as const, EMPTY)
const isFolded = atom({ plugin: 'eu-compliance-guard', key: 'isFolded' } as const, false)
const lastView = atom({ plugin: 'eu-compliance-guard', key: 'lastView' } as const, null)
const nextStep = atom({ plugin: 'eu-compliance-guard', key: 'next' } as const, null as NextStep | null)

// The same default level the SessionStart hook reads: EUCG_DEFAULT_MODE, then the config file.
async function readLevel($: EngineInterface, home: string): Promise<string> {
  let level = ((await $.env.get('EUCG_DEFAULT_MODE')) ?? '').trim().toLowerCase()
  if (level === '') {
    const config = `${(await $.env.get('XDG_CONFIG_HOME')) ?? `${home}/.config`}/eu-compliance-guard/config.json`
    try {
      const parsed = JSON.parse(await $.fs.read(config))
      level = typeof parsed?.defaultMode === 'string' ? parsed.defaultMode.toLowerCase() : ''
    } catch {
      level = ''
    }
  }
  return LEVELS.includes(level) ? level : 'full'
}

// Finds the newest run (by its timestamped name) that has a completion marker, and summarizes it.
// The declared project_id keys run storage, exactly as `eu-compliance-guard state-dir` and the session hook do.
async function declaredProject($: EngineInterface, project: string): Promise<string | null> {
  try {
    const value = JSON.parse(await $.fs.read(`${project}/.eu-compliance-guard/declarations.json`))?.project_id
    return typeof value === 'string' && PROJECT_ID.test(value) ? value : null
  } catch {
    return null
  }
}

async function refresh($: EngineInterface): Promise<void> {
  const home = (await $.env.get('HOME')) ?? ''
  // The session's project root, like the hook's CLAUDE_PROJECT_DIR; a worktree is its own project.
  const project = await $.session.root()
  const level = await readLevel($, home)
  const entries = await $.fs.list(project).catch(() => [])
  const isActive = level !== 'off' && entries.some(entry => entry.name === '.eu-compliance-guard' && entry.kind === 'dir')
  const identity = isActive ? await declaredProject($, project) : null
  const stateDir = identity ? `${(await $.env.get('XDG_STATE_HOME')) ?? `${home}/.local/state`}/eu-compliance-guard/${identity}` : ''
  let run = null
  let problem = null
  if (identity !== null) {
    const runs = (await $.fs.list(stateDir).catch(() => []))
      .filter(entry => entry.kind === 'dir' && !entry.isLink && entry.name.startsWith('run-'))
      .map(entry => entry.name)
      .sort()
      .reverse()
    for (const name of runs) {
      const files = await $.fs.list(`${stateDir}/${name}`).catch(() => [])
      if (!files.some(file => file.name === 'complete.json' && file.kind === 'file')) continue
      run = summarize(`${stateDir}/${name}`, await $.fs.read(`${stateDir}/${name}/bundle.json`).catch(() => ''))
      if (run === null) problem = 'latest run could not be summarized'
      else if (run.projectId !== identity) {
        run = null
        problem = 'latest run belongs to another project'
      }
      break
    }
  }
  await update($, band, () => ({ isActive, level, stateDir, run, problem }))
  // Ranked once per run, in the background, so a slow interpreter start never holds the session.
  if (run !== null && (await read($, nextStep))?.dir !== run.dir) void rankNext($, run.dir)
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

async function rankNext($: EngineInterface, dir: string) {
  const result = await cli($, ['next', '--run', await resolve($, dir), '--json', '--top', '1'], 60_000)
  const step = result?.exitCode === 0 ? parseStep(dir, result.stdout) : null
  await update($, nextStep, () => step ?? null)
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
async function openReport($: EngineInterface, linked: string) {
  const result = await cli($, ['view', '--run', await resolve($, linked), '--open'])
  const path = result?.exitCode === 0 ? result.stdout.trim().split('\n').pop() ?? '' : ''
  if (path === '') {
    // stderr carries only the CLI's fixed safe code.
    const code = result?.stderr.match(/eu-compliance-guard: ([a-z-]+):/)?.[1] ?? 'view-failed'
    $.ui.toast(`EU Compliance Guard: report view failed (${code})`)
    return
  }
  await update($, lastView, () => path)
  $.ui.toast(result?.stderr.includes('no-browser') ? `Report written: ${path}` : 'Report opened in your browser')
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    const started = await next(e)
    await refresh($)
    return started
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
    const status = run
      ? `${run.state} · ${run.gaps} gaps · ${run.requirements.supported}/${run.requirements.total} requirements supported`
      : b.problem ?? 'no completed run yet'
    if (folded) {
      return (
        <Box flexDirection="row" gap={1}>
          <Text dimColor>EU Compliance Guard · {status}</Text>
          {fold}
        </Box>
      )
    }
    const view = await read($, lastView)
    const step = await read($, nextStep)
    const stepForRun = run && step?.dir === run.dir ? step : null
    // A view written for an older run must not stand for the newest run the band summarizes.
    const runName = run ? run.dir.replace(/\/+$/, '').split('/').pop() : null
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
          {run ? <Text dimColor>{` · assessed ${run.assessmentDate}${age === null ? '' : ` (${age}d ago)`}`}</Text> : null}
          {run && run.attempts.total > 0 ? <Text dimColor>{` · sources ${run.attempts.retrieved}/${run.attempts.total} retrieved`}</Text> : null}
        </Text>
        {stepForRun ? <Text color="cyan">{describeStep(stepForRun)}</Text> : null}
        <Box flexDirection="row" gap={1}>
          {stepForRun ? <Button key="next" label="Next step" variant="primary" hotkey="n" onPress={() => runSkill($, 'eucg-next')} /> : null}
          <Button key="audit" label="Audit" variant={stepForRun ? undefined : 'primary'} hotkey="a" onPress={() => runSkill($, 'eucg-audit')} />
          <Button key="review" label="Review diff" hotkey="r" onPress={() => runSkill($, 'eucg-review')} />
          {run ? <Button key="gaps" label="Gaps" hotkey="g" onPress={() => runSkill($, 'eucg-gaps')} /> : null}
          {run ? <Button key="report" label="Open report" hotkey="o" onPress={() => openReport($, run.dir)} /> : null}
          <Button key="help" label="Help" hotkey="h" onPress={() => runSkill($, 'eucg-help')} />
        </Box>
        {viewForRun ? <Link href={`file://${viewForRun}`} label={`Report view: ${viewForRun}`} /> : null}
        <Text dimColor>Processing state is not a compliance verdict.</Text>
      </Box>
    )
  })
}
