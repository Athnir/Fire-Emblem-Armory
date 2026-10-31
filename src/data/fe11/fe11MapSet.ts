import { storyOrder } from '../../logic/spoiler'
import type { MapSet } from '../maps/mapSet'
import type { ChapterMap } from '../maps/types'
import { FE11_MAPS } from './fe11Maps'
import { FE11_MOVE_CLASSES, FE11_MOVE_CLASS_EXAMPLES } from './fe11Terrain'

/** "Prologue I", "Chapter 6x", "Endgame": the game's own headings. */
const name = (m: ChapterMap) => {
  if (m.heading === 'Prologue') return m.title
  if (m.heading === 'Endgame') return 'Endgame'
  return `Chapter ${m.id.replace('fe11-', '')}`
}
const short = (m: ChapterMap) => {
  if (m.heading === 'Prologue') return m.title.replace('Prologue ', 'P.')
  if (m.heading === 'Endgame') return 'Endgame'
  return `Ch.${m.id.replace('fe11-', '')}`
}

/**
 * Shadow Dragon as it's played: Prologue I-IV, Chapters 1-24 with each gaiden chapter (6x, 12x, 17x, 20x, 24x) where it comes, then
 * the Endgame. The gaiden chapters open only on a condition (said in their notes).
 */
export const FE11_STORY = storyOrder(FE11_MAPS, { name, short })

const label = (m: ChapterMap) => (m.heading === 'Prologue' ? m.title : `${name(m)}: ${m.title}`)

/** Shadow Dragon on the map page: every chapter in one list. */
export const FE11_MAP_SET: MapSet = {
  maps: FE11_MAPS,
  difficulties: [{ value: 'Normal', label: 'Normal' }],
  moveClasses: FE11_MOVE_CLASSES,
  moveClassExamples: FE11_MOVE_CLASS_EXAMPLES,
  lord: 'Marth',
  story: FE11_STORY,
  chapterLabel: label,
  mapLabel: label,
}
