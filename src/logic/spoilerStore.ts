const BLOCK_KEY = 'fe-armory-spoiler-block'
const PROGRESS_KEY = 'fe-armory-spoiler-progress'

/** Whether the spoiler block is on. Off when nothing is saved: the app opens as it always has. */
export function savedBlock(): boolean {
  try {
    return localStorage.getItem(BLOCK_KEY) === 'on'
  } catch {
    // Storage can be blocked (private mode); the block is then off.
    return false
  }
}

export function saveBlock(on: boolean): void {
  try {
    localStorage.setItem(BLOCK_KEY, on ? 'on' : 'off')
  } catch {
    // Not remembered this time.
  }
}

/** The chapter each game's block has been opened to, as an index into that game's story. */
export function savedProgress(): Record<string, number> {
  try {
    const raw = JSON.parse(localStorage.getItem(PROGRESS_KEY) ?? '{}') as unknown
    if (!raw || typeof raw !== 'object') return {}
    return Object.fromEntries(Object.entries(raw).filter(([, v]) => Number.isInteger(v) && (v as number) >= 0))
  } catch {
    return {}
  }
}

export function saveProgress(progress: Record<string, number>): void {
  try {
    localStorage.setItem(PROGRESS_KEY, JSON.stringify(progress))
  } catch {
    // Not remembered this time.
  }
}
