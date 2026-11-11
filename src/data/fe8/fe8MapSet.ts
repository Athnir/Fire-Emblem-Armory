import { storyOrder } from '../../logic/spoiler'
import type { MapSet, StoryFork, StoryOrder } from '../maps/mapSet'
import type { ChapterMap } from '../maps/types'
import { FE8_MAPS } from './fe8Maps'
import { FE8_MOVE_CLASSES, FE8_MOVE_CLASS_EXAMPLES } from './fe8Terrain'

const ROUTES = ['Eirika', 'Ephraim'] as const

function chapterName(m: ChapterMap) {
  if (m.route === 'Skirmish') return m.title
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
/** The world map's skirmishes: each location's monster line-ups on its chapter's map, destroyed. Optional maps to fight again,
 * listed with the Tower and the Ruins (the user's call). */
const SKIRMISHES = FE8_MAPS.filter((m) => m.route === 'Skirmish')
const skirmishesOf = (route: string) => SKIRMISHES.filter((m) => m.availableIn?.some((r) => r === route))

/** Where a skirmish opens in a story: once the chapter played at its location is cleared (when the world map starts sending
 * monsters isn't read); at the story's end where the story plays no chapter there (Melkaen Coast, which has none; the other
 * route's locations); never on a route that doesn't have it. */
function skirmishOpens(maps: ChapterMap[], last: number, route?: string): (id: string) => number | undefined {
  const index = new Map(maps.map((m, i) => [m.id, i]))
  const byId = new Map(SKIRMISHES.map((m) => [m.id, m]))
  return (id) => {
    const sk = byId.get(id)
    if (!sk) return undefined
    if (route && !sk.availableIn?.some((r) => r === route)) return Infinity
    const at = sk.skirmishOf === undefined ? undefined : index.get(sk.skirmishOf)
    return at === undefined ? last : Math.min(at + 1, last)
  }
}

/** The story up to the split: nothing outside it opens but the skirmishes at its own chapters' locations. */
function upToSplit(maps: ChapterMap[]): StoryOrder {
  const skirmish = skirmishOpens(maps, Infinity)
  return { ...storyOrder(maps, words), opensAt: (id) => skirmish(id) ?? Infinity }
}

/** A route to its end: the Tower and the Ruins open once it's cleared (the game opens them along the way; when isn't read yet), a
 * skirmish with its location, the other route's chapters never. */
function toTheEnd(maps: ChapterMap[], route: string): StoryOrder {
  const side = new Set(SIDE.map((m) => m.id))
  const skirmish = skirmishOpens(maps, maps.length - 1, route)
  return { ...storyOrder(maps, words), opensAt: (id) => (side.has(id) ? maps.length - 1 : (skirmish(id) ?? Infinity)) }
}

/** The Sacred Stones as the spoiler block walks it: the Prologue to Chapter 8, then Eirika's route or Ephraim's. */
export const FE8_FORK: StoryFork = {
  before: upToSplit(SHARED),
  choices: ROUTES.map((route) => ({
    id: route.toLowerCase(),
    label: `${route}'s route`,
    proceed: `Proceed to Chapter 9 (${route}'s route)`,
    story: toTheEnd([...SHARED, ...ofRoute(route)], route),
  })),
}

/** Every chapter in the order the map page lists them: the weapon page's chapter names without the block. */
export const FE8_STORY = storyOrder([...SHARED, ...ofRoute('Eirika'), ...ofRoute('Ephraim'), ...SIDE, ...SKIRMISHES], wordsWithRoute)

/** The route a chapter is in, as the weapon page names it. */
export const FE8_ROUTE_NAME = (m: ChapterMap) =>
  m.route === 'Eirika' || m.route === 'Ephraim' ? `${m.route}'s route` : m.route === 'Extra' || m.route === 'Skirmish' ? 'Side maps' : undefined

/** The map page's buttons, as Fates has them (the user's call): the chapters everyone plays first, then each route's own. */
const SECTIONS = ['Prologue', ...ROUTES] as const
const SHARED_IDS = new Set(SHARED.map((m) => m.id))
/** The skirmishes fought on a shared chapter's map (Za'ha Woods, Adlas Plains): listed with the shared chapters too. */
const SHARED_SKIRMISHES = SKIRMISHES.filter((m) => m.skirmishOf !== undefined && SHARED_IDS.has(m.skirmishOf))

/** A skirmish goes by its location and line-up, beside the Tower's floors and the Ruins'. */
const label = (m: ChapterMap) =>
  m.route === 'Extra' ? m.title : m.route === 'Skirmish' ? `Skirmish: ${m.title}` : `${chapterName(m)}: ${m.title}`

/** The Sacred Stones on the map page, as Fates is: a button for the chapters everyone plays (the Prologue to Chapter 8, with 5x)
 * leading into a button per route with its own chapters (9 to the end); Easy, Normal and Hard. */
export const FE8_MAP_SET: MapSet = {
  maps: FE8_MAPS,
  routes: {
    list: SECTIONS,
    maps: (route) => (route === 'Prologue' ? SHARED : ofRoute(route)),
    side: (route) => (route === 'Prologue' ? SHARED_SKIRMISHES : [...SIDE, ...skirmishesOf(route)]),
    of: (m) =>
      m.route === 'Shared' || (m.route === 'Skirmish' && SHARED_SKIRMISHES.includes(m))
        ? 'Prologue'
        : m.route === 'Ephraim' || (m.route === 'Skirmish' && m.availableIn?.[0] === 'Ephraim')
          ? 'Ephraim'
          : 'Eirika',
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
