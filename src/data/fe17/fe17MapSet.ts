import { storyOrder } from '../../logic/spoiler'
import type { MapSet } from '../maps/mapSet'
import type { ChapterMap } from '../maps/types'
import { FE17_MAPS } from './fe17Maps'
import { FE17_MOVE_CLASSES, FE17_MOVE_CLASS_EXAMPLES } from './fe17Terrain'

/** "Prologue", "Chapter 4": the game's own headings. */
const name = (m: ChapterMap) => m.heading ?? m.title
const short = (m: ChapterMap) => (m.chapter === 0 ? 'Prologue' : `Ch.${m.chapter}`)

/** Engage as it's played: the Prologue, then Chapters 1-26. */
export const FE17_STORY = storyOrder(FE17_MAPS, { name, short })

const label = (m: ChapterMap) => `${name(m)}: ${m.title}`

/** Engage on the map page: the story's chapters in one list, on its three difficulties. */
export const FE17_MAP_SET: MapSet = {
  maps: FE17_MAPS,
  difficulties: (['Normal', 'Hard', 'Maddening'] as const).map((value) => ({ value, label: value })),
  moveClasses: FE17_MOVE_CLASSES,
  moveClassExamples: FE17_MOVE_CLASS_EXAMPLES,
  lord: 'Alear',
  story: FE17_STORY,
  chapterLabel: label,
  mapLabel: label,
}
