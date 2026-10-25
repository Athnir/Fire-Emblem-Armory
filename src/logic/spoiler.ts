import type { StoryOrder } from '../data/maps/mapSet'
import type { ChapterMap } from '../data/maps/types'

/**
 * The spoiler block: with it on, a game opens at its first chapter and "Proceed" reveals the next one, so nothing
 * from a chapter you haven't reached shows up (a weapon you won't get for ten chapters, a map, a shop).
 */
export interface Reach {
  /** Whether the block is on for the game being shown. */
  on: boolean
  /** The index in the game's story of the chapter you're on (Infinity with the block off). */
  at: number
  /** Whether a map has been reached. A side map outside the story (the trial maps) counts once the story is cleared. */
  has: (mapId: string) => boolean
  /** Whether this map is the chapter you're on. The weapon list shows what that chapter gives, not what came before. */
  here: (mapId: string) => boolean
}

/** No block: everything counts as reached. */
export const SEES_ALL: Reach = { on: false, at: Infinity, has: () => true, here: () => true }

export function reachOf(story: StoryOrder, at: number): Reach {
  const index = new Map(story.maps.map((m, i) => [m.id, i]))
  const last = story.maps.length - 1
  return { on: true, at, has: (id) => (index.has(id) ? index.get(id)! <= at : at >= last), here: (id) => index.get(id) === at }
}

/** A game's story from its main chapters, naming each one the way the game numbers it. */
export function storyOrder(
  maps: ChapterMap[],
  words: Pick<StoryOrder, 'name' | 'short' | 'part'>,
): StoryOrder {
  const plain = maps.map(words.name)
  const shared = new Map<string, number>()
  for (const n of plain) shared.set(n, (shared.get(n) ?? 0) + 1)
  const placed = new Map<string, number>()
  const names = new Map(
    maps.map((m, i) => {
      const n = plain[i]
      if (shared.get(n) === 1) return [m.id, n] as const
      const k = (placed.get(n) ?? 0) + 1
      placed.set(n, k)
      return [m.id, `${n} (part ${k})`] as const
    }),
  )
  return { maps, ...words, name: (m) => names.get(m.id) ?? words.name(m) }
}
