import { storyOrder } from '../../logic/spoiler'
import type { MapSet } from '../maps/mapSet'
import type { ChapterMap } from '../maps/types'
import { FE1_MAPS } from './fe1Maps'
import { FE1_MOVE_CLASSES, FE1_MOVE_CLASS_EXAMPLES } from './fe1Terrain'

const words = {
  name: (m: ChapterMap) => `Chapter ${m.chapter}`,
  short: (m: ChapterMap) => `Ch.${m.chapter}`,
}

/** Shadow Dragon and the Blade of Light as it's played: its 25 chapters in order, with no splits and no side chapters. */
export const FE1_STORY = storyOrder(FE1_MAPS, words)

const label = (m: ChapterMap) => `${words.name(m)}: ${m.title}`

/** Shadow Dragon and the Blade of Light on the map page: one list, one difficulty (the game has no modes). */
export const FE1_MAP_SET: MapSet = {
  maps: FE1_MAPS,
  difficulties: [{ value: 'Normal', label: 'Normal' }],
  moveClasses: FE1_MOVE_CLASSES,
  moveClassExamples: FE1_MOVE_CLASS_EXAMPLES,
  lord: 'Marth',
  terrainNote:
    'Pegasus and Wyvern Knights always fight as if in the sky: terrain gives them no Avoid. Terrain gives no Def. A unit on a fortress, castle gate or throne recovers 3 to 10 HP at the start of each turn.',
  noTerrainDef: true,
  story: FE1_STORY,
  chapterLabel: label,
  mapLabel: label,
}
