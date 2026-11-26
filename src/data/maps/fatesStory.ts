import { storyOrder } from '../../logic/spoiler'
import { ALL_MAPS } from './index'
import { FATES_JOINS, NO_CASTLE_AFTER, PARALOGUE_AFTER, PARALOGUE_PARENT } from './fatesJoins'
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

/**
 * Jakob joins in Chapter 6 for a female Corrin but only after Chapter 15 for a male one (the game's castle_join.bin puts him and
 * Felicia in the castle from Chapter 15 on every route), which only the player knows: his
 * son Dwyer's paralogue is held to the later date so it can't show early.
 */
const JOINS_LATE: Record<string, number> = { Jakob: 15 }

/** The first chapter from `chapter` with a My Castle visit after it: Revelation 16 goes straight on into 17 (its ending skips
 * the castle), so what opens there opens after 17. */
function castleAfter(chapter: number, route: string): number {
  let n = chapter
  while (NO_CASTLE_AFTER[route]?.includes(n)) n++
  return n
}

/**
 * The chapter whose completion opens a paralogue on a route, as the program checks it (0x3d2e6c): the chapter its record says to
 * clear first (Chapter 7; Birthright 15 for Paralogue 6) and, for a child's, the chapter its fixed parent joins your army for
 * good (the other parent is whoever you marry), whichever is later, at the next My Castle visit. Soleil's father Laslow joins in
 * Conquest 12, so hers opens in 13; Shigure follows his mother Azura, not his father; Corrin, Kana's parent, is always there.
 */
export function paralogueOpensAfter(paralogue: number, route: string): number {
  const parent = PARALOGUE_PARENT[paralogue]
  const joins = !parent || parent === 'Corrin' ? 0 : (JOINS_LATE[parent] ?? FATES_JOINS[route]?.[parent] ?? 0)
  return castleAfter(Math.max(PARALOGUE_AFTER[paralogue][route], joins), route)
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
      // A chapter's challenge can be scouted at the castle visit after that chapter (Revelation 16's after 17); a paralogue's as
      // soon as the paralogue opens.
      if (m?.route === 'Challenge' && m.availableIn?.some((r) => r === route)) {
        const base = byId.get(m.challengeOf!)!
        return after(maps, base.route === 'Paralogue' ? paralogueOpensAfter(base.chapter, route) : castleAfter(base.chapter, route))
      }
      return Infinity
    },
  }
}

export const FATES_FORK: StoryFork = {
  before: { ...storyOrder(SHARED, words), opensAt: () => Infinity },
  choices: ROUTES.map((r) => ({ id: r, label: r, story: storyFor(r) })),
}
