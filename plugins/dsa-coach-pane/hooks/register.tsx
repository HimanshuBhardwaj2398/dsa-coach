import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Block, Due, Live } from '../types'

// A view of the notebook, never a second copy of it: coach.py writes the files, the pane reads them.
// It shows state only. No hint text, no code, and the pattern only when the problem is labeled,
// because naming the pattern is hint rung 3.
const PANE = 'dsa-coach'
const TITLE = 'DSA coach'
const NOTEBOOK = 'notebook' // relative to the folder Claude Code was started in
const TICK_MS = 30_000
const MIN = 60_000
const IDLE_MIN = 5 // the same rule as coach.py: after 5 quiet minutes the clock stops at the last activity

const STAGES: readonly (readonly [string, string])[] = [
  ['Understand', 'Understand'],
  ['Find an approach', 'Devise a plan'],
  ['Build it', 'Carry out the plan'],
  ['Check and finish', 'Look back'],
]
// A solve started before 0.8.0 had eight stages; coach.py moves it to four on its next write.
const LEGACY_STAGE = [1, 1, 2, 2, 2, 2, 2, 3, 4]
const stageOf = (l: { stage: number; protocol?: number }) => (l.protocol === 2 ? l.stage : LEGACY_STAGE[l.stage] ?? l.stage)

// Change a tag when the fields of its value change: it declines what an earlier version stored.
const live = atom({ plugin: 'dsa-coach-pane', key: 'live' } as const, null, { shape: 'live-1' })
const due = atom({ plugin: 'dsa-coach-pane', key: 'due' } as const, null, { shape: 'due-1' })
const now = atom({ plugin: 'dsa-coach-pane', key: 'now' } as const, 0)
const toasted = atom({ plugin: 'dsa-coach-pane', key: 'toasted' } as const, '')

async function readJson($: EngineInterface, path: string): Promise<unknown> {
  try {
    return JSON.parse(await $.fs.read(path))
  } catch {
    return null
  }
}

function openBlock(l: Live): Block | null {
  const last = l.blocks[l.blocks.length - 1]
  return last && !last.end ? last : null
}

// Active minutes, as coach.py's block_minutes counts them: the span less the paused idle time.
// A block from before 0.7.0 (no `paused`) counted wall-clock time, so it is capped at the block length.
function minutes(b: Block, at: number, length: number): number {
  const end = b.end ? Date.parse(b.end) : at
  const m = Math.max(0, Math.floor((end - Date.parse(b.start) - (b.paused ?? 0) * 1000) / MIN))
  return b.paused === undefined ? Math.min(m, length) : m
}

function lastActivity(l: Live): number {
  if (l.last_active) return Date.parse(l.last_active)
  const last = l.blocks[l.blocks.length - 1]
  return last.end ? Date.parse(last.end) : Date.parse(last.start) + l.block_minutes * MIN
}

function countedUntil(l: Live, at: number): number {
  const last = lastActivity(l)
  return at - last <= IDLE_MIN * MIN ? at : last
}

function toDue(j: unknown): Due | null {
  const d = (j as { due?: Record<string, unknown>; next_steps?: unknown })?.due
  if (!d) return null
  const count = (v: unknown) => (Array.isArray(v) ? v.length : typeof v === 'number' ? v : 0)
  const steps = (j as { next_steps?: unknown }).next_steps
  return {
    resolves: count(d.resolves),
    cards: count(d.cards),
    drafts: count(d.drafts),
    next: Array.isArray(steps) && typeof steps[0] === 'string' ? steps[0] : null,
  }
}

async function refresh($: EngineInterface): Promise<void> {
  const current = (await readJson($, `${NOTEBOOK}/sessions/current.json`)) as Live | null
  const journey = await readJson($, `${NOTEBOOK}/journey.json`)
  const at = await $.clock.now()
  await update($, live, () => current)
  await update($, due, () => toDue(journey))
  await update($, now, () => at)

  const block = current && openBlock(current)
  if (!current || !block || minutes(block, countedUntil(current, at), current.block_minutes) < current.block_minutes) return
  const id = `${current.file}#${current.blocks.length}`
  let isNew = false
  await update($, toasted, last => {
    isNew = last !== id
    return id
  })
  if (isNew) {
    $.ui.toast(`Focus block ${current.blocks.length} is over. Take a five-minute break, then choose: another block, the next hint, or park it.`)
  }
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'coach',
      description: 'Show the DSA coach pane: the live solve, its focus-block timer and hint buttons',
    })
    if (await $.fs.exists(`${NOTEBOOK}/config.json`)) {
      await refresh($)
      $.clock.every(TICK_MS, () => void refresh($))
      // Open unasked only where a pane is a sidebar.
      if (e.surface === 'vscode' || e.surface === 'desktop') void $.ui.open({ id: PANE, title: TITLE })
    }

    return next(e)
  })

  on('command.run', { command: 'coach' }, async $ => {
    await refresh($)
    await $.ui.open({ id: PANE, title: TITLE })

    return { text: 'DSA coach pane opened.' }
  })

  // coach.py is the only writer, so a Bash call that ran it is the moment to re-read.
  // The pane is a view: if the re-read fails, the tool call still goes through as it settled.
  on('tool.call', { tool: 'Bash' }, async ($, e, next) => {
    const ran = await next(e)
    if (e.command.includes('coach.py')) await refresh($)

    return ran
  }).catch(($, e, next) => next(e))

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text, Button, Link } = $.ui.resolve(e)
    const l = await read($, live)
    const d = await read($, due)
    const at = await read($, now)
    const say = (text: string) => () => void $.prompt.submit({ text })

    if (!l) {
      const parts = d
        ? [`${d.resolves} re-solve(s)`, `${d.cards} card(s)`, ...(d.drafts ? [`${d.drafts} draft(s)`] : [])]
        : []

      return (
        <Box flexDirection="column" gap={1}>
          <Text dimColor>No solve in progress.</Text>
          {d && <Text>Due: {parts.join(' · ')}</Text>}
          {d?.next && <Text>Next: {d.next}</Text>}
          <Box flexDirection="row" flexWrap="wrap" gap={1}>
            <Button key="practise" hotkey="p" variant="primary" onPress={say("Let's practise.")}>
              Practise
            </Button>
            {!!d?.cards && (
              <Button key="quiz" hotkey="q" onPress={say('Quiz me.')}>
                Quiz me
              </Button>
            )}
            <Button key="where" hotkey="w" onPress={say('Where am I?')}>
              Where am I?
            </Button>
          </Box>
        </Box>
      )
    }

    const n = stageOf(l)
    const [stage, phase] = STAGES[n - 1] ?? ['?', '?']
    const block = openBlock(l)
    const until = countedUntil(l, at)
    const total = l.blocks.reduce((sum, b) => sum + minutes(b, until, l.block_minutes), 0)
    const elapsed = block ? minutes(block, until, l.block_minutes) : 0
    const isOver = !!block && elapsed >= l.block_minutes
    const timer = block
      ? `Block ${l.blocks.length} · ${elapsed} of ${l.block_minutes} min${isOver ? ' · block over' : ''}`
      : `On a break after block ${l.blocks.length} · ${total} min in all`

    return (
      <Box flexDirection="column" gap={1}>
        <Box flexDirection="column">
          <Link href={l.url} label={l.problem} />
          <Text dimColor>{l.labeled ? `${l.difficulty} · ${l.pattern_name}` : l.difficulty}</Text>
        </Box>
        <Box flexDirection="column">
          <Text dimColor>{phase}</Text>
          <Text weight="semibold">
            Stage {n}/{STAGES.length} · {stage}
          </Text>
          <Text>{'●'.repeat(n) + '○'.repeat(Math.max(0, STAGES.length - n))}</Text>
        </Box>
        <Box flexDirection="column">
          <Text color={isOver ? 'warning' : undefined}>{timer}</Text>
          <Text>Hints used: {l.rung}/7</Text>
          <Text dimColor>Attempt: {NOTEBOOK}/{l.file}</Text>
        </Box>
        <Box flexDirection="row" flexWrap="wrap" gap={1}>
          <Button key="check" hotkey="c" variant="primary"
            onPress={say(`Check my attempt in ${NOTEBOOK}/${l.file}: run it on edge cases and tell me what fails, without fixing it.`)}>
            Check my code
          </Button>
          <Button key="stage" hotkey="s" onPress={say(`I'm done with stage ${n} (${stage}). Check it, then move me on.`)}>
            Stage done
          </Button>
          <Button key="hint" hotkey="h" onPress={say(`I'm stuck at stage ${n} (${stage}). Next hint rung, please.`)}>
            Next hint
          </Button>
          {block ? (
            <Button key="block" hotkey="b" onPress={say("My focus block is over and it isn't solved yet.")}>
              Block over
            </Button>
          ) : (
            <Button key="block" hotkey="b" onPress={say("Break's over. Start another focus block.")}>
              New block
            </Button>
          )}
        </Box>
      </Box>
    )
  })
}
