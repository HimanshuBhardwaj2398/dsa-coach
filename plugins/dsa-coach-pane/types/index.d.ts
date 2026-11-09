// What the pane keeps in $.state. `Live` mirrors notebook/sessions/current.json, written by `coach.py solve`.
export type Block = { start: string; end: string | null; paused?: number } // paused: idle seconds, absent before 0.7.0

export type Live = {
  problem: string
  pattern_name: string
  labeled: boolean
  difficulty: string
  url: string
  file: string
  stage: number
  protocol?: number
  rung: number
  block_minutes: number
  blocks: Block[]
  last_active?: string
}

export type Due = { resolves: number; cards: number; drafts: number; next: string | null }

declare module 'claude-code' {
  interface PluginState {
    'dsa-coach-pane': {
      live: Shaped<Live | null>
      due: Shaped<Due | null>
      now: number
      toasted: string
    }
  }
}
