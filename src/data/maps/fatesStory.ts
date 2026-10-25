import { storyOrder } from '../../logic/spoiler'
import { ALL_MAPS } from './index'
import { FATES_JOINS } from './fatesJoins'
import type { StoryFork, StoryOrder } from './mapSet'
import type { ChapterMap } from './types'

/**
 * Fates as the spoiler block walks it: the five chapters everyone plays, then Birthright, Conquest or Revelation (each
 * route's chapters from 6). The block asks which route you're on after Chapter 5.
 */
const SHARED = ALL_MAPS.filter((m) => m.route === 'Shared')
const ROUTES = ['Birthright', 'Conquest', 'Revelation'] as const

/** The chapter whose completion opens the Dragon's Gate, which holds the DLC maps (Serenes Forest, "Downloadable Content"). */
export const DLC_OPENS_AFTER = 6
/** Paralogue 1 (Mozu's) opens after Chapter 8 (Gamer Guides): not confirmed in-game. */
const MOZU_OPENS_AFTER = 8

/**
 * Each child's fixed parent: the one who is always the same (the other is whoever you marry). A child's paralogue opens the
 * chapter after that parent joins your army for good: the user's rule, with Soleil's father Laslow joining in Conquest 12 so
 * hers opens in 13, and Shigure following his mother Azura, not his father. Paralogues 2 to 22, in the game's order;
 * the parents match who each child's chapter says to talk to.
 */
const FIXED_PARENT: Record<number, string> = {
  2: 'Avatar', 3: 'Azura', 4: 'Jakob', 5: 'Silas', 6: 'Kaze', 7: 'Ryoma', 8: 'Takumi', 9: 'Saizo', 10: 'Kaden', 11: 'Hinata',
  12: 'Azama', 13: 'Subaki', 14: 'Hayato', 15: 'Xander', 16: 'Leo', 17: 'Benny', 18: 'Keaton', 19: 'Arthur', 20: 'Odin',
  21: 'Laslow', 22: 'Niles',
}
/**
 * Jakob joins in Chapter 6 for a female Corrin but only after Chapter 15 for a male one, which only the player knows: his
 * son Dwyer's paralogue is held to the later date so it can't show early.
 */
const JOINS_LATE: Record<string, number> = { Jakob: 15 }

/** The chapter whose completion opens a paralogue on a route: its child's fixed parent has joined for good. */
export function paralogueOpensAfter(paralogue: number, route: string): number {
  if (paralogue === 1) return MOZU_OPENS_AFTER
  const parent = FIXED_PARENT[paralogue]
  const joins = JOINS_LATE[parent] ?? FATES_JOINS[route]?.[parent] ?? DLC_OPENS_AFTER
  // Nobody opens before the castle does (Chapter 6 completed), whatever chapter the parent joined in.
  return Math.max(joins, DLC_OPENS_AFTER)
}

const words = {
  name: (m: ChapterMap) => (m.chapter === 0 ? 'Prologue' : m.id.endsWith('-endgame') ? 'Endgame' : `Chapter ${m.chapter}`),
  short: (m: ChapterMap) => (m.chapter === 0 ? 'Prologue' : m.id.endsWith('-endgame') ? 'Endgame' : `Ch.${m.chapter}`),
}

/** The index of the first chapter after `chapter` is completed, or the last chapter if the story ends before. */
function after(maps: ChapterMap[], chapter: number): number {
  const i = maps.findIndex((m) => m.chapter > chapter)
  return i < 0 ? maps.length - 1 : i
}

function storyFor(route: (typeof ROUTES)[number]): StoryOrder {
  const maps = [...SHARED, ...ALL_MAPS.filter((m) => m.route === route)]
  const byId = new Map(ALL_MAPS.map((m) => [m.id, m]))
  return {
    ...storyOrder(maps, words),
    // The DLC and the paralogues this route can reach open by chapter; every other route's maps never do.
    opensAt: (id) => {
      const m = byId.get(id)
      if (m?.route === 'DLC') return after(maps, DLC_OPENS_AFTER)
      if (m?.route === 'Paralogue' && m.availableIn?.some((r) => r === route)) return after(maps, paralogueOpensAfter(m.chapter, route))
      return Infinity
    },
  }
}

export const FATES_FORK: StoryFork = {
  before: { ...storyOrder(SHARED, words), opensAt: () => Infinity },
  choices: ROUTES.map((r) => ({ id: r, label: r, story: storyFor(r) })),
}
