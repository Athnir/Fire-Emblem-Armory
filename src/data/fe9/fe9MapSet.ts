import type { MapSet } from '../maps/mapSet'
import { FE9_MAPS } from './fe9Maps'
import { FE9_MOVE_CLASSES, FE9_MOVE_CLASS_EXAMPLES } from './fe9Terrain'

const label = (m: { heading?: string; title: string }) => `${(m.heading ?? '').replace(/^Ch\./, 'Chapter ')}: ${m.title}`

/** Path of Radiance on the map page. Easy uses Normal's units; Hard has its own. */
export const FE9_MAP_SET: MapSet = {
  maps: FE9_MAPS,
  extras: { label: 'Trial maps', maps: FE9_MAPS.filter((m) => m.route === 'Trial') },
  difficulties: [
    { value: 'Normal', label: 'Easy / Normal' },
    { value: 'Hard', label: 'Hard' },
  ],
  moveClasses: FE9_MOVE_CLASSES,
  moveClassExamples: FE9_MOVE_CLASS_EXAMPLES,
  lord: 'Ike',
  chapterLabel: label,
  mapLabel: label,
}
