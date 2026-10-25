import { storyOrder } from '../../logic/spoiler'
import { ALL_MAPS } from './index'
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
 * The chapter whose completion opens a paralogue. Paralogue 1 (Mozu's) opens after Chapter 8 (Gamer Guides). The children's
 * need their parents married (a support, which is the Unit Planner's business) and, per Gamer Guides, Chapter 14: not
 * confirmed in-game.
 */
export const paralogueOpensAfter = (paralogue: number) => (paralogue === 1 ? 8 : 14)

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
      if (m?.route === 'Paralogue' && m.availableIn?.some((r) => r === route)) return after(maps, paralogueOpensAfter(m.chapter))
      return Infinity
    },
  }
}

export const FATES_FORK: StoryFork = {
  before: { ...storyOrder(SHARED, words), opensAt: () => Infinity },
  choices: ROUTES.map((r) => ({ id: r, label: r, story: storyFor(r) })),
}
