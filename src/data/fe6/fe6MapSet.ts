import { storyOrder } from '../../logic/spoiler'
import type { MapSet, StoryFork, StoryOrder } from '../maps/mapSet'
import type { ChapterMap } from '../maps/types'
import { FE6_MAPS } from './fe6Maps'
import { FE6_MOVE_CLASSES, FE6_MOVE_CLASS_EXAMPLES } from './fe6Terrain'

const byId = new Map(FE6_MAPS.map((m) => [m.id, m]))
const pick = (...ids: string[]) =>
  ids.map((id) => {
    const m = byId.get(id)
    if (!m) throw new Error(`no FE6 map ${id}`)
    return m
  })

const words = {
  name: (m: ChapterMap) => (m.heading === 'Final' ? 'Final Chapter' : `Chapter ${(m.heading ?? `Ch.${m.chapter}`).slice(3)}`),
  short: (m: ChapterMap) => m.heading ?? `Ch.${m.chapter}`,
}

const STORY_MAPS = FE6_MAPS.filter((m) => m.route === 'Story')
const TRIALS = FE6_MAPS.filter((m) => m.route === 'Trial')

// The story's stretches: everyone plays the first nine chapters (and 8x, once it opens), then Chapter 9's villages pick 10A and 11A
// or 10B and 11B; 12 to 16x are shared again, then the EXP of Thea and Juno against Sue and Sin picks Ilia (17A-20Ax) or Sacae
// (17B-20Bx); 21 to the Final Chapter are shared. The gaiden chapters are listed where they come, as every GBA game's are.
const BEFORE = pick('fe6-1', 'fe6-2', 'fe6-3', 'fe6-4', 'fe6-5', 'fe6-6', 'fe6-7', 'fe6-8', 'fe6-8x', 'fe6-9')
const ROUTE_A = pick('fe6-10a', 'fe6-11a')
const ROUTE_B = pick('fe6-10b', 'fe6-11b')
const MIDDLE = pick('fe6-12', 'fe6-12x', 'fe6-13', 'fe6-14', 'fe6-14x', 'fe6-15', 'fe6-16', 'fe6-16x')
const ILIA = pick('fe6-17a', 'fe6-18a', 'fe6-19a', 'fe6-20a', 'fe6-20ax')
const SACAE = pick('fe6-17b', 'fe6-18b', 'fe6-19b', 'fe6-20b', 'fe6-20bx')
const END = pick('fe6-21', 'fe6-21x', 'fe6-22', 'fe6-23', 'fe6-24', 'fe6-final')

/** The story up to a split: nothing outside it opens. */
const upToSplit = (maps: ChapterMap[]): StoryOrder => ({ ...storyOrder(maps, words), opensAt: () => Infinity })

/** A whole story down one route: the trial maps open once it's cleared, the other routes' chapters never. */
function toTheEnd(maps: ChapterMap[]): StoryOrder {
  const trials = new Set(TRIALS.map((m) => m.id))
  return { ...storyOrder(maps, words), opensAt: (id) => (trials.has(id) ? maps.length - 1 : Infinity) }
}

function secondSplit(first: ChapterMap[]): StoryFork {
  return {
    before: upToSplit(first),
    choices: [
      { id: 'ilia', label: 'Ilia (17A–20A)', proceed: 'Proceed to Chapter 17A (Ilia)', story: toTheEnd([...first, ...ILIA, ...END]) },
      { id: 'sacae', label: 'Sacae (17B–20B)', proceed: 'Proceed to Chapter 17B (Sacae)', story: toTheEnd([...first, ...SACAE, ...END]) },
    ],
  }
}

function firstChoice(id: string, label: string, chapter: string, maps: ChapterMap[]) {
  const first = [...BEFORE, ...maps, ...MIDDLE]
  return { id, label, proceed: `Proceed to Chapter ${chapter}`, story: upToSplit(first), fork: secondSplit(first) }
}

/** The Binding Blade as the spoiler block walks it: Chapters 1 to 9, then 10A or 10B, then (after 16x) Ilia or Sacae. */
export const FE6_FORK: StoryFork = {
  before: upToSplit(BEFORE),
  choices: [firstChoice('a', '10A and 11A', '10A', ROUTE_A), firstChoice('b', '10B and 11B', '10B', ROUTE_B)],
}

/** Every chapter in the order the map page lists them (both routes' in turn): the weapon page's chapter names without the block. */
export const FE6_STORY = storyOrder(STORY_MAPS, words)

const label = (m: ChapterMap) => (m.route === 'Trial' ? `${m.heading}: ${m.title}` : `${words.name(m)}: ${m.title}`)

/** The Binding Blade on the map page: the story's chapters, the trial maps in their own list, Normal and Hard. */
export const FE6_MAP_SET: MapSet = {
  maps: FE6_MAPS,
  extras: { label: 'Trial maps', maps: TRIALS },
  difficulties: [
    { value: 'Normal', label: 'Normal' },
    { value: 'Hard', label: 'Hard' },
  ],
  moveClasses: FE6_MOVE_CLASSES,
  moveClassExamples: FE6_MOVE_CLASS_EXAMPLES,
  lord: 'Roy',
  terrainNote: 'Fliers get no Def or Avoid from terrain (their rows in the game are all 0); Res still applies.',
  chapterLabel: label,
  mapLabel: label,
}
