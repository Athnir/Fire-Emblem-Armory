import { storyOrder } from '../../logic/spoiler'
import type { MapSet } from '../maps/mapSet'
import { FE9_MAPS } from './fe9Maps'
import { FE9_MOVE_CLASSES, FE9_MOVE_CLASS_EXAMPLES } from './fe9Terrain'

const label = (m: { heading?: string; title: string }) => `${(m.heading ?? '').replace(/^Ch\./, 'Chapter ')}: ${m.title}`

const heading = (m: { heading?: string }) => m.heading ?? ''

/** Path of Radiance's story, as the spoiler block opens it: the chapters in order, without the trial maps. */
const STORY = storyOrder(FE9_MAPS.filter((m) => m.route !== 'Trial'), {
  name: (m) => heading(m).replace(/^Ch\./, 'Chapter '),
  // Chapter 17's four maps are one chapter to a shop list.
  short: (m) => heading(m).replace(/^(Ch\.17)-1$/, '$1'),
})

/** Path of Radiance on the map page. Each difficulty opens with its own placement records ('_m' on Easy), and Easy adds 2 levels
 * to the generic foes of every story chapter. */
export const FE9_MAP_SET: MapSet = {
  maps: FE9_MAPS,
  story: STORY,
  extras: { label: 'Trial maps', maps: FE9_MAPS.filter((m) => m.route === 'Trial') },
  difficulties: [
    { value: 'Easy', label: 'Easy' },
    { value: 'Normal', label: 'Normal' },
    { value: 'Hard', label: 'Hard' },
  ],
  moveClasses: FE9_MOVE_CLASSES,
  moveClassExamples: FE9_MOVE_CLASS_EXAMPLES,
  lord: 'Ike',
  // The battle code gives fliers the terrain's second set of bonuses, which is zero on every tile Path of Radiance's maps use.
  terrainNote: 'Fliers get no Def/Avo from terrain.',
  chapterLabel: label,
  mapLabel: label,
}
