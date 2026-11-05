import { expect, mock, test } from 'claude-code/testing'
import type { On } from 'claude-code'

const PANE = {
  plugin: 'dsa-coach-pane',
  component: 'Pane',
  requestId: 'dsa-coach',
  props: {
    title: 'DSA coach',
    isFocused: false,
    bodyColumns: 40,
    placement: 'dock',
    scroll: { offset: 0, bodyRows: 30 },
    view: {},
  },
} as const

const T0 = Date.parse('2026-11-05T10:00:00+05:30')
const MIN = 60_000

const live = (labeled: boolean) =>
  JSON.stringify({
    problem: 'two-sum',
    pattern: 'arrays-hashing',
    pattern_name: 'Arrays & Hashing',
    labeled,
    difficulty: 'easy',
    url: 'https://leetcode.com/problems/two-sum/',
    file: 'problems/two-sum/2026-11-05.py',
    stage: 4,
    rung: 2,
    block_minutes: 15,
    blocks: [{ start: '2026-11-05T10:00:00+05:30', end: null }],
  })

const JOURNEY = JSON.stringify({
  due: { resolves: [], cards: [{ id: 'c0001' }], drafts: 7, inbox: [] },
  next_steps: ['Solve two-sum unaided to move Arrays & Hashing forward.'],
})

// The engine beneath the plugin: a notebook of these files, and a record of prompts and toasts.
function engine(on: On, files: Record<string, string>) {
  const sent: string[] = []
  const toasts: string[] = []
  // The engine hands the hooks absolute paths, resolved against the working directory.
  const find = (path: string) => Object.keys(files).find(rel => path.endsWith(`/${rel}`))
  on('fs.exists', (_, e) => ({ value: find(e.path) !== undefined }))
  on('fs.read', (_, e) => {
    const rel = find(e.path)
    if (rel === undefined) throw new Error(`ENOENT ${e.path}`)
    return { value: files[rel] }
  })
  on('command.register', () => ({ value: { command: 'coach' } }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
  on('ui.toast', (_, e) => {
    toasts.push(e.text)
    return { value: undefined }
  })
  on('prompt.submit', (_, e) => {
    sent.push(e.text)
    return { text: e.text }
  })
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('tool.call', () => ({ result: {} }))
  return { sent, toasts }
}

const files = (labeled: boolean | null) => ({
  'notebook/config.json': '{}',
  'notebook/journey.json': JOURNEY,
  ...(labeled === null ? {} : { 'notebook/sessions/current.json': live(labeled) }),
})

test('an unlabeled solve shows its stage, timer and rung but never its pattern', async ($, on) => {
  mock.clock(on, { now: T0 + 7 * MIN })
  engine(on, files(false))
  await $.session.start({ cwd: '/ws', surface: 'vscode', isInteractive: true })

  for (const surface of ['vscode', 'terminal'] as const) {
    const ui = await $.ui.mount({ ...PANE, surface })
    expect(await ui.find({ type: 'Text', text: /Arrays|arrays-hashing/ })).toBeUndefined()
    expect((await ui.find({ type: 'Text', text: /^Stage/ }))?.text).toBe('Stage 4/8 · Find the repeated work')
    expect((await ui.find({ type: 'Text', text: /^Block/ }))?.text).toBe('Block 1 · 7 of 15 min')
    expect((await ui.find({ type: 'Text', text: /^Hints/ }))?.text).toBe('Hints used: 2/7')
    await ui.unmount()
  }
})

test('a labeled solve names its pattern', async ($, on) => {
  mock.clock(on, { now: T0 + 7 * MIN })
  engine(on, files(true))
  await $.session.start({ cwd: '/ws', surface: 'vscode', isInteractive: true })

  const ui = await $.ui.mount({ ...PANE, surface: 'vscode' })
  expect((await ui.find({ type: 'Text', text: /Arrays/ }))?.text).toBe('easy · Arrays & Hashing')
  await ui.unmount()
})

test('the buttons talk to the coach in the chat', async ($, on) => {
  mock.clock(on, { now: T0 + 7 * MIN })
  const { sent } = engine(on, files(false))
  await $.session.start({ cwd: '/ws', surface: 'vscode', isInteractive: true })

  const ui = await $.ui.mount({ ...PANE, surface: 'vscode' })
  await ui.press({ key: 'hint' })
  await ui.press({ key: 'check' })
  expect(sent[0]).toBe("I'm stuck at stage 4 (Find the repeated work). Next hint rung, please.")
  expect(sent[1]).toContain('notebook/problems/two-sum/2026-11-05.py')
  expect(sent[1]).toContain('without fixing it')
  await ui.unmount()
})

test('a block that runs out is announced once', async ($, on) => {
  mock.clock(on, { now: T0 + 16 * MIN })
  const { toasts } = engine(on, files(false))
  await $.session.start({ cwd: '/ws', surface: 'vscode', isInteractive: true })
  await $.tool.call({ tool: 'Bash', command: 'python3 coach.py solve show' })

  expect(toasts.length).toBe(1)
  expect(toasts[0]).toContain('Focus block 1 is over')
  const ui = await $.ui.mount({ ...PANE, surface: 'vscode' })
  expect((await ui.find({ type: 'Text', text: /^Block/ }))?.text).toBe('Block 1 · 16 of 15 min · block over')
  await ui.unmount()
})

test('with no solve in progress it shows what is due and offers practice', async ($, on) => {
  mock.clock(on, { now: T0 })
  const { sent } = engine(on, files(null))
  await $.session.start({ cwd: '/ws', surface: 'vscode', isInteractive: true })

  const ui = await $.ui.mount({ ...PANE, surface: 'vscode' })
  expect((await ui.find({ type: 'Text', text: /^Due/ }))?.text).toBe('Due: 0 re-solve(s) · 1 card(s) · 7 draft(s)')
  expect(await ui.find({ key: 'quiz' })).toBeDefined()
  await ui.press({ key: 'practise' })
  expect(sent).toEqual(["Let's practise."])
  await ui.unmount()
})
