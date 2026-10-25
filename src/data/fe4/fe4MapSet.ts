import { storyOrder } from '../../logic/spoiler'
import type { MapSet } from '../maps/mapSet'
import { FE4_MAPS } from './fe4Maps'
import { FE4_MOVE_CLASSES, FE4_MOVE_CLASS_EXAMPLES } from './fe4Terrain'

const label = (m: { heading?: string; title: string }) => `${(m.heading ?? '').replace(/^Ch\./, 'Chapter ')}: ${m.title}`

/** The story as the spoiler block opens it: the twelve chapters in order (the game has no side maps). */
export const FE4_STORY = storyOrder(FE4_MAPS, {
  name: (m) => (m.heading === 'Prologue' ? 'Prologue' : m.heading === 'Final' ? 'Final Chapter' : `Chapter ${m.chapter}`),
  short: (m) => m.heading ?? `Ch.${m.chapter}`,
})

/** Genealogy of the Holy War on the map page: twelve chapters, one difficulty. */
export const FE4_MAP_SET: MapSet = {
  maps: FE4_MAPS,
  difficulties: [{ value: 'Normal', label: 'Normal' }],
  moveClasses: FE4_MOVE_CLASSES,
  moveClassExamples: FE4_MOVE_CLASS_EXAMPLES,
  lord: 'Sigurd',
  noTerrainDef: true,
  story: FE4_STORY,
  chapterLabel: label,
  mapLabel: label,
}
