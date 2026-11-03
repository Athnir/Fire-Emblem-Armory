import { storyOrder } from '../../logic/spoiler'
import type { MapSet, StoryFork, StoryOrder } from '../maps/mapSet'
import type { ChapterMap, ThreeHousesRoute } from '../maps/types'
import { FE16_MAPS } from './fe16Maps'
import { FE16_MOVE_CLASSES, FE16_MOVE_CLASS_EXAMPLES } from './fe16Terrain'

const byId = new Map(FE16_MAPS.map((m) => [m.id, m]))
const pick = (...ids: string[]) =>
  ids.map((id) => {
    const m = byId.get(id)
    if (!m) throw new Error(`no Three Houses map ${id}`)
    return m
  })

const words = {
  name: (m: ChapterMap) => (m.chapter === 0 ? 'Prologue' : `Chapter ${m.chapter}`),
  short: (m: ChapterMap) => (m.chapter === 0 ? 'Prologue' : `Ch.${m.chapter}`),
}

/** The houses: the Prologue is everyone's, then the house you lead from Chapter 1. Chapters 1, 4, 7 and 11 are each house's own
 * (the mock battles' other houses, the Blue Lions' Rite of Rebirth, the Holy Tomb's commander); in the rest only the leader beside
 * Byleth differs. */
const HOUSES = [
  { id: 'be', label: 'Black Eagles' },
  { id: 'bl', label: 'Blue Lions' },
  { id: 'gd', label: 'Golden Deer' },
]
/** The routes from Chapter 12 (the game's fixed_flow.bin), each with the house it comes from and its id's suffix: the Black Eagles
 * part at Chapter 12, siding with Edelgard (Crimson Flower) or the Church (Silver Snow). */
const ROUTES: { route: ThreeHousesRoute; key: string; house: string }[] = [
  { route: 'Crimson Flower', key: 'cf', house: 'be' },
  { route: 'Silver Snow', key: 'ss', house: 'be' },
  { route: 'Azure Moon', key: 'am', house: 'bl' },
  { route: 'Verdant Wind', key: 'vw', house: 'gd' },
]
const ROUTE_LIST = ROUTES.map((r) => r.route)

/** The Prologue and a house's White Clouds chapters (1 to 11). */
const whiteClouds = (h: string) =>
  pick(
    'fe16-0', `fe16-1-${h}`, 'fe16-2', 'fe16-3', `fe16-4-${h}`, 'fe16-5', 'fe16-6', `fe16-7-${h}`, 'fe16-8', 'fe16-9', 'fe16-10',
    `fe16-11-${h}`,
  )
/** A route's own chapters, from Chapter 12 to its end, in order. */
const partTwo = (route: string) => FE16_MAPS.filter((m) => m.route === route)
/** A route as it's played: its house's White Clouds, then its own chapters. */
const routeMaps = (route: string) => {
  const r = ROUTES.find((x) => x.route === route)
  return r ? [...whiteClouds(r.house), ...partTwo(route)] : []
}

const ordered = (maps: ChapterMap[]): StoryOrder => storyOrder(maps, words)
/** A stretch of the story up to a split, or to a route's end: nothing outside it opens. */
const stretch = (maps: ChapterMap[]): StoryOrder => ({ ...ordered(maps), opensAt: () => Infinity })

/** Three Houses as the spoiler block walks it: the Prologue, then a house's White Clouds chapters (1 to 11); the Blue Lions go on to
 * Azure Moon and the Golden Deer to Verdant Wind, and the Black Eagles part once more at Chapter 12, into Crimson Flower or Silver
 * Snow. */
export const FE16_FORK: StoryFork = {
  before: stretch(pick('fe16-0')),
  choices: HOUSES.map((h) => {
    const routes = ROUTES.filter((r) => r.house === h.id)
    if (routes.length === 1) {
      return {
        id: h.id,
        label: `${h.label} (${routes[0].route})`,
        proceed: `Proceed to Chapter 1 with the ${h.label}`,
        story: stretch(routeMaps(routes[0].route)),
      }
    }
    const before = stretch(whiteClouds(h.id))
    return {
      id: h.id,
      label: h.label,
      proceed: `Proceed to Chapter 1 with the ${h.label}`,
      story: before,
      fork: {
        before,
        choices: routes.map((r) => ({
          id: r.key,
          label: r.route,
          proceed: `Proceed to Chapter 12 (${r.route})`,
          story: stretch(routeMaps(r.route)),
        })),
      },
    }
  }),
}

/** Every chapter in the order the map page lists them (Chapters 1, 4, 7 and 11 once per house, then each route's): the weapon page's
 * chapter names without the block. */
export const FE16_STORY = ordered(FE16_MAPS)

/** The house or route a map's id ends with, as the lists name it. */
const SUFFIX: Record<string, string> = {
  be: 'Black Eagles', bl: 'Blue Lions', gd: 'Golden Deer', cf: 'Crimson Flower', ss: 'Silver Snow', am: 'Azure Moon',
  vw: 'Verdant Wind',
}
const suffix = (m: ChapterMap) => SUFFIX[m.id.match(/-([a-z]{2})$/)?.[1] ?? '']
/** The route a map is listed under: its own from Chapter 12; a house's White Clouds chapter under the house's first route; a chapter
 * every house plays under Crimson Flower (each route lists it too). */
function routeOf(m: ChapterMap): string {
  if (ROUTE_LIST.includes(m.route as ThreeHousesRoute)) return m.route
  const key = m.id.match(/-(bl|gd)$/)?.[1]
  return key ? ROUTES.find((r) => r.house === key)!.route : ROUTE_LIST[0]
}

/** In a route's own list: 'Chapter 13: Hunting by Daybreak', a house's own White Clouds chapter with its house. */
const chapterLabel = (m: ChapterMap) => {
  const house = /-(be|bl|gd)$/.test(m.id) ? ` (${suffix(m)})` : ''
  return `${words.name(m)}${house}: ${m.title}`
}
/** In full: a route's chapter says whose ('Chapter 13 (Silver Snow): Hunting by Daybreak'). */
const mapLabel = (m: ChapterMap) => (suffix(m) ? `${words.name(m)} (${suffix(m)}): ${m.title}` : chapterLabel(m))

/** Three Houses on the map page: a button per route (each with its house's White Clouds chapters first); Normal, Hard and
 * Maddening each change which units the battle places and their levels. */
export const FE16_MAP_SET: MapSet = {
  maps: FE16_MAPS,
  routes: {
    list: ROUTE_LIST,
    maps: routeMaps,
    side: () => [],
    of: routeOf,
  },
  difficulties: [
    { value: 'Normal', label: 'Normal' },
    { value: 'Hard', label: 'Hard' },
    { value: 'Maddening', label: 'Maddening' },
  ],
  moveClasses: FE16_MOVE_CLASSES,
  moveClassExamples: FE16_MOVE_CLASS_EXAMPLES,
  lord: 'Byleth',
  terrainNote: "Terrain gives Prt (Def), Rsl (Res) and Avoid by kind; a healing tile restores a share of max HP at each turn's start.",
  story: FE16_STORY,
  chapterLabel,
  mapLabel,
}
