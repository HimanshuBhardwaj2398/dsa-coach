import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Block, Due, Live } from '../types'

// A view of the notebook, never a second copy of it: coach.py writes the files, the pane reads them.
// It shows state only: no buttons, no hint text, and the pattern only when the problem is labeled,
// because naming the pattern is hint rung 3. Coaching happens in the chat; the code is on LeetCode.
const PANE = 'dsa-coach'
const TITLE = 'DSA coach'
const NOTEBOOK = 'notebook' // relative to the folder Claude Code was started in
const TICK_MS = 30_000
const MIN = 60_000

const STAGES: readonly (readonly [string, string])[] = [
  ['Understand', 'Understand'],
  ['Find an approach', 'Devise a plan'],
  ['Build it', 'Carry out the plan'],
  ['Check and finish', 'Look back'],
]

// Change a tag when the fields of its value change: it declines what an earlier version stored.
const live = atom({ plugin: 'dsa-coach-pane', key: 'live' } as const, null, { shape: 'live-2' })
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

// Minutes in a block, as coach.py's block_minutes counts them: start to end (or now), less any idle time an
// older solve paused out, and at most the block's length. Unrounded, like coach.py: callers round.
function minutes(b: Block, at: number, length: number): number {
  const end = b.end ? Date.parse(b.end) : at
  return Math.min(length, Math.max(0, (end - Date.parse(b.start) - (b.paused ?? 0) * 1000) / MIN))
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
  const [current, journey] = (await Promise.all([
    readJson($, `${NOTEBOOK}/sessions/current.json`),
    readJson($, `${NOTEBOOK}/journey.json`),
  ])) as [Live | null, unknown]
  const at = await $.clock.now()
  await update($, live, () => current)
  await update($, due, () => toDue(journey))
  await update($, now, () => at)

  const block = current && openBlock(current)
  if (!current || !block || minutes(block, at, current.block_minutes) < current.block_minutes) return
  const id = `${current.session_id}#${current.blocks.length}`
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
      description: 'Show the DSA coach pane: the live solve, its focus-block timer and hint rung',
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
    const { Box, Text, Link } = $.ui.resolve(e)
    const l = await read($, live)
    const d = await read($, due)
    const at = await read($, now)

    if (!l) {
      const parts = d
        ? [`${d.resolves} re-solve(s)`, `${d.cards} card(s)`, ...(d.drafts ? [`${d.drafts} draft(s)`] : [])]
        : []

      return (
        <Box flexDirection="column" gap={1}>
          <Text dimColor>No solve in progress.</Text>
          {d && <Text>Due: {parts.join(' · ')}</Text>}
          {d?.next && <Text>Next: {d.next}</Text>}
        </Box>
      )
    }

    const [stage, phase] = STAGES[l.stage - 1] ?? ['?', '?']
    const block = openBlock(l)
    // As in coach.py's live_view: the total rounds the sum, the open block counts whole minutes.
    const total = Math.round(l.blocks.reduce((sum, b) => sum + minutes(b, at, l.block_minutes), 0))
    const elapsed = block ? Math.floor(minutes(block, at, l.block_minutes)) : 0
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
            Stage {l.stage}/{STAGES.length} · {stage}
          </Text>
          <Text>{'●'.repeat(l.stage) + '○'.repeat(Math.max(0, STAGES.length - l.stage))}</Text>
        </Box>
        <Box flexDirection="column">
          <Text color={isOver ? 'warning' : undefined}>{timer}</Text>
          <Text>Hints used: {l.rung}/7</Text>
        </Box>
      </Box>
    )
  })
}
