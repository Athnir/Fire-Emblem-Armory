import { storyOrder } from '../../logic/spoiler'
import type { MapSet, StoryFork, StoryOrder } from '../maps/mapSet'
import type { ChapterMap } from '../maps/types'
import { FE8_MAPS } from './fe8Maps'
import { FE8_MOVE_CLASSES, FE8_MOVE_CLASS_EXAMPLES } from './fe8Terrain'

const ROUTES = ['Eirika', 'Ephraim'] as const

function chapterName(m: ChapterMap) {
  const h = m.heading ?? `Ch.${m.chapter}`
  if (h === 'Prologue' || h.startsWith('Tower') || h.startsWith('Ruins')) return m.route === 'Extra' ? m.title : h
  if (h.startsWith('Final')) return h === 'Final' ? 'Final Chapter' : 'Final Chapter (part 2)'
  return `Chapter ${h.slice(3)}`
}

const words = { name: chapterName, short: (m: ChapterMap) => m.heading ?? `Ch.${m.chapter}` }
/** Without the block both routes are listed at once, so a route's chapter says whose it is. */
const wordsWithRoute = {
  name: (m: ChapterMap) => (m.route === 'Eirika' || m.route === 'Ephraim' ? `${chapterName(m)}, ${m.route}'s route` : chapterName(m)),
  short: words.short,
}

const SHARED = FE8_MAPS.filter((m) => m.route === 'Shared')
const ofRoute = (route: string) => FE8_MAPS.filter((m) => m.route === route)
/** The Tower of Valni and the Lagdou Ruins: optional maps, in the second dropdown. */
const SIDE = FE8_MAPS.filter((m) => m.route === 'Extra')

/** The story up to the split: nothing outside it opens. */
const upToSplit = (maps: ChapterMap[]): StoryOrder => ({ ...storyOrder(maps, words), opensAt: () => Infinity })

/** A route to its end: the side maps open once it's cleared (the game opens the Tower and the Ruins along the way; when isn't read
 * yet), the other route's chapters never. */
function toTheEnd(maps: ChapterMap[]): StoryOrder {
  const side = new Set(SIDE.map((m) => m.id))
  return { ...storyOrder(maps, words), opensAt: (id) => (side.has(id) ? maps.length - 1 : Infinity) }
}

/** The Sacred Stones as the spoiler block walks it: the Prologue to Chapter 8, then Eirika's route or Ephraim's. */
export const FE8_FORK: StoryFork = {
  before: upToSplit(SHARED),
  choices: ROUTES.map((route) => ({
    id: route.toLowerCase(),
    label: `${route}'s route`,
    proceed: `Proceed to Chapter 9 (${route}'s route)`,
    story: toTheEnd([...SHARED, ...ofRoute(route)]),
  })),
}

/** Every chapter in the order the map page lists them: the weapon page's chapter names without the block. */
export const FE8_STORY = storyOrder([...SHARED, ...ofRoute('Eirika'), ...ofRoute('Ephraim'), ...SIDE], wordsWithRoute)

/** The route a chapter is in, as the weapon page names it. */
export const FE8_ROUTE_NAME = (m: ChapterMap) =>
  m.route === 'Eirika' || m.route === 'Ephraim' ? `${m.route}'s route` : m.route === 'Extra' ? 'Side maps' : undefined

const label = (m: ChapterMap) => (m.route === 'Extra' ? m.title : `${chapterName(m)}: ${m.title}`)

/** The Sacred Stones on the map page: a button per route (each with the shared chapters first), Easy, Normal and Hard. */
export const FE8_MAP_SET: MapSet = {
  maps: FE8_MAPS,
  routes: {
    list: ROUTES,
    maps: (route) => [...SHARED, ...ofRoute(route)],
    side: () => SIDE,
    of: (m) => (m.route === 'Ephraim' ? 'Ephraim' : 'Eirika'),
    sideLabel: 'Side maps',
  },
  difficulties: [
    { value: 'Easy', label: 'Easy' },
    { value: 'Normal', label: 'Normal' },
    { value: 'Hard', label: 'Hard' },
  ],
  moveClasses: FE8_MOVE_CLASSES,
  moveClassExamples: FE8_MOVE_CLASS_EXAMPLES,
  lord: 'Eirika',
  terrainNote: 'Fliers get no Def or Avoid from terrain (their rows in the game are all 0); Res still applies.',
  chapterLabel: label,
  mapLabel: label,
}
