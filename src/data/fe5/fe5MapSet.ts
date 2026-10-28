import { storyOrder } from '../../logic/spoiler'
import type { MapSet, StoryFork, StoryOrder } from '../maps/mapSet'
import type { ChapterMap } from '../maps/types'
import { FE5_MAPS } from './fe5Maps'
import { FE5_MOVE_CLASSES, FE5_MOVE_CLASS_EXAMPLES } from './fe5Terrain'

const byId = new Map(FE5_MAPS.map((m) => [m.id, m]))
const pick = (...ids: string[]) =>
  ids.map((id) => {
    const m = byId.get(id)
    if (!m) throw new Error(`no FE5 map ${id}`)
    return m
  })

const words = {
  name: (m: ChapterMap) => (m.heading === 'Final' ? 'Final Chapter' : `Chapter ${(m.heading ?? `Ch.${m.chapter}`).slice(3)}`),
  short: (m: ChapterMap) => m.heading ?? `Ch.${m.chapter}`,
}

// Chapters 1 to 15 with their gaiden chapters (each listed where it comes, with when it opens in its notes), then the exit Leif
// takes from Chapter 15 picks 16A and 17A or 16B and 17B, then Chapter 18 to the Final Chapter.
const BEFORE = pick(
  'fe5-1', 'fe5-2', 'fe5-2x', 'fe5-3', 'fe5-4', 'fe5-4x', 'fe5-5', 'fe5-6', 'fe5-7', 'fe5-8', 'fe5-8x', 'fe5-9', 'fe5-10', 'fe5-11',
  'fe5-11x', 'fe5-12', 'fe5-12x', 'fe5-13', 'fe5-14', 'fe5-14x', 'fe5-15',
)
const ROUTE_A = pick('fe5-16a', 'fe5-17a')
const ROUTE_B = pick('fe5-16b', 'fe5-17b')
const END = pick('fe5-18', 'fe5-19', 'fe5-20', 'fe5-21', 'fe5-21x', 'fe5-22', 'fe5-23', 'fe5-24', 'fe5-24x', 'fe5-final')

/** The story up to the split: nothing outside it opens. */
const upToSplit = (maps: ChapterMap[]): StoryOrder => ({ ...storyOrder(maps, words), opensAt: () => Infinity })
const toTheEnd = (maps: ChapterMap[]): StoryOrder => ({ ...storyOrder(maps, words), opensAt: () => Infinity })

/** Thracia 776 as the spoiler block walks it: Chapters 1 to 15, then 16A and 17A (Leif leaves by the west exit or the church) or 16B
 * and 17B (the south-east exit), then the rest. */
export const FE5_FORK: StoryFork = {
  before: upToSplit(BEFORE),
  choices: [
    { id: 'a', label: '16A and 17A', proceed: 'Proceed to Chapter 16A', story: toTheEnd([...BEFORE, ...ROUTE_A, ...END]) },
    { id: 'b', label: '16B and 17B', proceed: 'Proceed to Chapter 16B', story: toTheEnd([...BEFORE, ...ROUTE_B, ...END]) },
  ],
}

/** Every chapter in the order the map page lists them (both routes' in turn): the weapon page's chapter names without the block. */
export const FE5_STORY = storyOrder(FE5_MAPS, words)

const label = (m: ChapterMap) => `${words.name(m)}: ${m.title}`

/** Thracia 776 on the map page: every chapter in one list, one difficulty (the game has no modes). */
export const FE5_MAP_SET: MapSet = {
  maps: FE5_MAPS,
  difficulties: [{ value: 'Normal', label: 'Normal' }],
  moveClasses: FE5_MOVE_CLASSES,
  moveClassExamples: FE5_MOVE_CLASS_EXAMPLES,
  lord: 'Leif',
  terrainNote: 'Fliers get no Def or Avoid from terrain (their rows in the game are all 0).',
  chapterLabel: label,
  mapLabel: label,
}
