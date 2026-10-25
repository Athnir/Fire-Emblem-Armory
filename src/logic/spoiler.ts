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
  /** The map of the chapter you're on. */
  now?: string
  /** The game's story as the block is walking it (the chosen route's, for a game that splits). */
  story?: StoryOrder
  /** The route chosen at the split, for a game that has one. */
  route?: string
}

/** No block: everything counts as reached. */
export const SEES_ALL: Reach = { on: false, at: Infinity, has: () => true, here: () => true }

export function reachOf(story: StoryOrder, at: number, route?: string): Reach {
  const index = new Map(story.maps.map((m, i) => [m.id, i]))
  const last = story.maps.length - 1
  const opens = (id: string) => (story.opensAt ? story.opensAt(id) <= at : at >= last)
  return {
    on: true,
    at,
    has: (id) => (index.has(id) ? index.get(id)! <= at : opens(id)),
    here: (id) => index.get(id) === at,
    now: story.maps[at]?.id,
    story,
    route,
  }
}

/**
 * The chapter (an index in the story) a source of an item turns up in: its map's own chapter, or the chapter after that for a foe
 * who arrives mid-chapter (what he carried is known once that chapter is over). A side map counts from the chapter that opens
 * it; Infinity when the story never reaches it.
 */
export function turnsUpAt(story: StoryOrder, mapId: string, arrives?: boolean): number {
  const own = story.maps.findIndex((m) => m.id === mapId)
  const at = own >= 0 ? own : (story.opensAt?.(mapId) ?? Infinity)
  return arrives ? at + 1 : at
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
