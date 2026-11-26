import { useSyncExternalStore } from 'react'

/**
 * The DLC side stories a game keeps apart (the user's call, 2026-11-26): Engage's Fell Xenologue and Three Houses' Cindered Shadows
 * are off until their switch is ticked, on the weapon page, the map page and the battalions alike (one switch per game, remembered on
 * the device). Shown, each opens as the game opens it: Fell Xenologue all at once with the Somniel's Ancient Well once Chapter 6 is
 * cleared, Cindered Shadows all at once from the main menu's Side Story, its own save.
 */
const KEY = 'fe-armory-side-stories'
const listeners = new Set<() => void>()
const NONE: Record<string, boolean> = {}

function load(): Record<string, boolean> {
  try {
    const raw = JSON.parse(localStorage.getItem(KEY) ?? '{}') as unknown
    return raw && typeof raw === 'object' ? (raw as Record<string, boolean>) : NONE
  } catch {
    return NONE
  }
}

let shown = load()

export const sideStoryShown = (game: string) => !!shown[game]

export function setSideStoryShown(game: string, on: boolean): void {
  shown = { ...shown, [game]: on }
  try {
    localStorage.setItem(KEY, JSON.stringify(shown))
  } catch {
    // Not remembered this time.
  }
  listeners.forEach((l) => l())
}

const subscribe = (listener: () => void) => {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

/** Which games' side stories are shown, kept in step across the pages that read it. */
export function useSideStories(): Record<string, boolean> {
  return useSyncExternalStore(subscribe, () => shown, () => NONE)
}
