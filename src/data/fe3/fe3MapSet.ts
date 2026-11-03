import { storyOrder } from '../../logic/spoiler'
import type { MapSet } from '../maps/mapSet'
import type { ChapterMap } from '../maps/types'
import { FE3_MAPS } from './fe3Maps'
import { FE3_MOVE_CLASSES, FE3_MOVE_CLASS_EXAMPLES } from './fe3Terrain'

/** The four maps the status screen calls Book 2's "Final Chapter", in the order they're played. */
const FINAL = FE3_MAPS.filter((m) => m.heading === 'Book 2, Final Chapter').map((m) => m.id)

/** "Book 1, Ch.4" -> "Book 1, Chapter 4", as the status screen names it. A short name leaves the book out: the weapon page says it
 * with each source's book ("Sold at the armory (Book 1): Ch.1"). */
const words = {
  name: (m: ChapterMap) => (m.heading ?? `Ch.${m.chapter}`).replace('Ch.', 'Chapter '),
  short: (m: ChapterMap) =>
    FINAL.includes(m.id) ? `Final Ch. (part ${FINAL.indexOf(m.id) + 1})` : (m.heading ?? `Ch.${m.chapter}`).replace(/^Book \d, /, ''),
}

/**
 * Mystery of the Emblem as it's played: Book 1's twenty chapters, then Book 2's twenty and its final chapter's four maps (Endgame 1
 * and Endgame 2's three parts). Book 2 starts the army afresh; the last four open only on a condition (said in the first one's
 * notes). The status screen gives the four one name, so they're named "(part 1)" to "(part 4)".
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
  terrainNote:
    'Terrain gives no Def. Fliers get no avoid from it (their row in the game is all 0), nor does anyone against a tome or the ' +
    'Levin Sword.',
  noTerrainDef: true,
  story: FE3_STORY,
  chapterLabel: label,
  mapLabel: label,
}
