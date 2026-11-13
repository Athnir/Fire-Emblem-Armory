import { storyOrder } from '../../logic/spoiler'
import type { MapSet, StoryOrder } from '../maps/mapSet'
import type { ChapterMap } from '../maps/types'
import { FE2_MAPS } from './fe2Maps'
import { FE2_OPENS } from './fe2Opens'
import { FE2_MOVE_CLASSES, FE2_MOVE_CLASS_EXAMPLES } from './fe2Terrain'

/** The story: each chapter's battles on the world map, Alm's army's first where both armies have their own (Chapters 3 and 4). */
const MAIN = FE2_MAPS.filter((m) => m.route !== 'Dungeon')
/** The towns' and dungeons' encounters: a list of their own, each opening with the story battle after the one beside its place. */
const DUNGEONS = FE2_MAPS.filter((m) => m.route === 'Dungeon')

const army = (m: ChapterMap) => (m.route === 'Alm' || m.route === 'Celica' ? m.route : '')
const name = (m: ChapterMap) =>
  m.route === 'Dungeon' ? `${m.title}, encounter ${m.chapter}` : `${m.heading}${army(m) ? ` (${army(m)})` : ''}, battle ${m.chapter}`
const short = (m: ChapterMap) =>
  m.route === 'Dungeon' ? `E${m.chapter}` : `${(m.heading ?? '').replace('Chapter ', 'Ch.')}${army(m).slice(0, 1)}-${m.chapter}`
const words = { name, short }

/** Every map, for naming a source's chapter on the weapon page. */
export const FE2_STORY = storyOrder([...MAIN, ...DUNGEONS], words)

/** The spoiler block's story: the world map's battles; each encounter opens with the story battle after the one beside its place. */
export const FE2_BLOCK: StoryOrder = (() => {
  const story = storyOrder(MAIN, words)
  const index = new Map(MAIN.map((m, i) => [m.id, i]))
  return { ...story, opensAt: (id) => (FE2_OPENS[id] ? (index.get(FE2_OPENS[id]) ?? Infinity) : Infinity) }
})()

const label = (m: ChapterMap) => (m.route === 'Dungeon' ? name(m) : `${name(m)}: ${m.title}`)

/** Gaiden on the map page: the story in one list, the dungeons' encounters in another; one difficulty (the game has no modes). */
export const FE2_MAP_SET: MapSet = {
  maps: FE2_MAPS,
  third: { label: 'Dungeons', maps: DUNGEONS },
  difficulties: [{ value: 'Normal', label: 'Normal' }],
  moveClasses: FE2_MOVE_CLASSES,
  moveClassExamples: FE2_MOVE_CLASS_EXAMPLES,
  lord: 'Alm',
  terrainNote:
    'Terrain gives Avoid, never Def. Pegasus and Falcon Knights (and the Gargoyles and Necrodragons of their classes) get no Avoid from it. A unit on a fort recovers 5 HP at the start of each turn; a swamp takes 5 HP from all but fliers and some monsters.',
  noTerrainDef: true,
  healInHp: true,
  story: FE2_BLOCK,
  chapterLabel: label,
  mapLabel: label,
}
