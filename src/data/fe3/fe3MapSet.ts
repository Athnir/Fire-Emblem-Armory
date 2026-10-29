import { storyOrder } from '../../logic/spoiler'
import type { MapSet } from '../maps/mapSet'
import type { ChapterMap } from '../maps/types'
import { FE3_MAPS } from './fe3Maps'
import { FE3_MOVE_CLASSES, FE3_MOVE_CLASS_EXAMPLES } from './fe3Terrain'

/** "Book 1, Ch.4" -> "Book 1, Chapter 4"; Endgame names stay as the game writes them. */
const words = {
  name: (m: ChapterMap) => (m.heading ?? `Ch.${m.chapter}`).replace('Ch.', 'Chapter '),
  short: (m: ChapterMap) => (m.heading ?? `Ch.${m.chapter}`).replace('Book 1, ', 'B1 ').replace('Book 2, ', 'B2 '),
}

/**
 * Mystery of the Emblem as it's played: Book 1's twenty chapters, then Book 2's twenty, Endgame 1 and Endgame 2's three parts. Book 2
 * starts the army afresh; the Endgame opens only on a condition (said in Endgame 1's notes). Endgame 2's parts are each their own
 * map, so the spoiler block names them "(part 1)" to "(part 3)".
 */
export const FE3_STORY = storyOrder(FE3_MAPS, words)

const label = (m: ChapterMap) => `${FE3_STORY.name(m)}: ${m.title}`

/** Mystery of the Emblem on the map page: every chapter of both books in one list, one difficulty (the game has no modes). */
export const FE3_MAP_SET: MapSet = {
  maps: FE3_MAPS,
  difficulties: [{ value: 'Normal', label: 'Normal' }],
  moveClasses: FE3_MOVE_CLASSES,
  moveClassExamples: FE3_MOVE_CLASS_EXAMPLES,
  lord: 'Marth',
  terrainNote: 'Fliers get no avoid from terrain (their row in the game is all 0), and terrain gives no Def.',
  noTerrainDef: true,
  story: FE3_STORY,
  chapterLabel: label,
  mapLabel: label,
}
