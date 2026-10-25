import { storyOrder } from '../../logic/spoiler'
import type { MapSet } from '../maps/mapSet'
import { FE10_MAPS } from './fe10Maps'
import { FE10_MOVE_CLASSES, FE10_MOVE_CLASS_EXAMPLES } from './fe10Terrain'

const label = (m: { heading?: string; title: string }) =>
  `${(m.heading ?? '').replace(/^(\d)-(\d+)$/, 'Part $1, Chapter $2').replace(/^(\d)-/, 'Part $1, ')}: ${m.title}`

const part = (m: { heading?: string }) => Number.parseInt(m.heading ?? '', 10)
/** '1-6' -> '6', '4-Endgame (2)' -> 'Endgame (2)': the chapter without its part. */
const rest = (m: { heading?: string }) => (m.heading ?? '').replace(/^\d-/, '')

/** Radiant Dawn's story, as the spoiler block opens it: the four parts' chapters in order. */
const STORY = storyOrder(FE10_MAPS, {
  name: (m) => `Part ${part(m)}, ${/^\d/.test(rest(m)) ? 'Chapter ' : ''}${rest(m)}`,
  short: (m) => (/^\d/.test(rest(m)) ? `Ch.${rest(m)}` : rest(m)),
  part,
})

/** Radiant Dawn on the map page. The scripts tell only Easy apart: Normal and Hard place the same units. */
export const FE10_MAP_SET: MapSet = {
  maps: FE10_MAPS,
  story: STORY,
  difficulties: [
    { value: 'Normal', label: 'Easy' },
    { value: 'Hard', label: 'Normal / Hard' },
  ],
  moveClasses: FE10_MOVE_CLASSES,
  moveClassExamples: FE10_MOVE_CLASS_EXAMPLES,
  lord: 'Micaiah',
  terrainNote: 'Fliers get no Def/Avo from terrain.',
  chapterLabel: label,
  mapLabel: label,
}
