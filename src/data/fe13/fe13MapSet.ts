import { storyOrder } from '../../logic/spoiler'
import type { MapSet, StoryOrder } from '../maps/mapSet'
import type { ChapterMap } from '../maps/types'
import { FE13_MAPS } from './fe13Maps'
import { FE13_OPENS } from './fe13Opens'
import { FE13_MOVE_CLASSES, FE13_MOVE_CLASS_EXAMPLES } from './fe13Terrain'

/** The story everyone plays: Premonition, the Prologue, Chapters 1-25 and the Endgame. */
const MAIN = FE13_MAPS.filter((m) => m.route === 'Story')
/** What's optional: the paralogues (the children's once a parent is married, the SpotPass ones after Chapter 25) and the DLC maps. */
const SIDE = FE13_MAPS.filter((m) => m.route !== 'Story')

const name = (m: ChapterMap) => (m.route === 'DLC' ? m.title : (m.heading ?? `Chapter ${m.chapter}`))
const short = (m: ChapterMap) =>
  m.route === 'DLC'
    ? m.title
    : (m.heading ?? '').replace(/^Chapter (\d+)$/, 'Ch.$1').replace(/^Paralogue (\d+)$/, 'Par.$1')
const words = { name, short }

/** Every map, for naming a source's chapter on the weapon page. */
export const FE13_STORY = storyOrder([...MAIN, ...SIDE], words)

/** The spoiler block's story: the main chapters, with each side map opening once the chapter that opens it is cleared. */
export const FE13_BLOCK: StoryOrder = (() => {
  const story = storyOrder(MAIN, words)
  const index = new Map(MAIN.map((m, i) => [m.id, i]))
  return { ...story, opensAt: (id) => (FE13_OPENS[id] ? (index.get(FE13_OPENS[id]) ?? Infinity) + 1 : Infinity) }
})()

const label = (m: ChapterMap) => (m.route === 'DLC' ? `Xenologue: ${m.title}` : `${name(m)}: ${m.title}`)

/** Awakening on the map page: the story in one list, the paralogues and DLC maps in the second; Normal, Hard and Lunatic. */
export const FE13_MAP_SET: MapSet = {
  maps: FE13_MAPS,
  extras: { label: 'Paralogues and DLC', maps: SIDE },
  difficulties: [
    { value: 'Normal', label: 'Normal' },
    { value: 'Hard', label: 'Hard' },
    { value: 'Lunatic', label: 'Lunatic' },
  ],
  moveClasses: FE13_MOVE_CLASSES,
  moveClassExamples: FE13_MOVE_CLASS_EXAMPLES,
  lord: 'Chrom',
  terrainNote: 'Fliers get no Def or Avoid from terrain (the battle code drops the tile for any unit with the flying category).',
  story: FE13_BLOCK,
  chapterLabel: label,
  mapLabel: label,
}
