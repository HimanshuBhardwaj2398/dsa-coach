// What the pane keeps in $.state. `Live` mirrors notebook/sessions/current.json, written by `coach.py solve`.
export type Block = { start: string; end: string | null; paused?: number } // paused: idle seconds, from solves before 0.9.0

export type Live = {
  problem: string
  session_id: string
  pattern_name: string
  labeled: boolean
  difficulty: string
  url: string
  stage: number
  rung: number
  block_minutes: number
  blocks: Block[]
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
