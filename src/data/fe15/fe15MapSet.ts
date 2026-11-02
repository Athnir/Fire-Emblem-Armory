import { storyOrder } from '../../logic/spoiler'
import type { MapSet, StoryOrder } from '../maps/mapSet'
import type { ChapterMap } from '../maps/types'
import { FE15_MAPS } from './fe15Maps'
import { FE15_LISTS, FE15_OPENS } from './fe15Opens'
import { FE15_MOVE_CLASSES, FE15_MOVE_CLASS_EXAMPLES } from './fe15Terrain'

/** The story everyone plays: the Prologue and Acts 1-5's battles, Acts 3 and 4 with Alm's army's first where the game allows it
 * (Act 4: Alm's up to the Dragon's Maw, then Celica's, then the rest of Alm's). */
const MAIN = FE15_MAPS.filter((m) => !FE15_LISTS[m.id])
/** The optional battles: those you can leave unfought, Act 6 (after the Final Battle) and the amiibo ordeals. */
const SIDE = FE15_MAPS.filter((m) => FE15_LISTS[m.id] === 'optional')
/** The dungeons' skirmishes: the battles their wandering foes start, a list of their own (the user's call). */
const SKIRMISHES = FE15_MAPS.filter((m) => FE15_LISTS[m.id] === 'skirmishes')

const army = (m: ChapterMap) => (m.route === 'Alm' || m.route === 'Celica' ? m.route : '')
const name = (m: ChapterMap) => {
  if (m.heading === 'Prologue' || m.heading === 'amiibo') return m.heading === 'amiibo' ? m.title : 'Prologue'
  const who = army(m)
  return `${m.heading}${who && (m.heading === 'Act 3' || m.heading === 'Act 4') ? ` (${who})` : ''}, battle ${m.chapter}`
}
const short = (m: ChapterMap) => {
  if (m.heading === 'Prologue') return 'Prologue'
  if (m.heading === 'amiibo') return m.title
  const act = (m.heading ?? '').replace('Act ', 'A')
  const who = m.heading === 'Act 3' || m.heading === 'Act 4' ? army(m).slice(0, 1) : ''
  return `${act}${who}-${m.chapter}`
}
const words = { name, short }

/** Every map, for naming a source's chapter on the weapon page. */
export const FE15_STORY = storyOrder([...MAIN, ...SIDE, ...SKIRMISHES], words)

/** The spoiler block's story: the main battles. Each other map opens with the first story map after it on the world map, Act 6 with
 * the Final Battle (the story is over) and the amiibo dungeons with Act 3. */
export const FE15_BLOCK: StoryOrder = (() => {
  const story = storyOrder(MAIN, words)
  const index = new Map(MAIN.map((m, i) => [m.id, i]))
  return { ...story, opensAt: (id) => (FE15_OPENS[id] ? (index.get(FE15_OPENS[id]) ?? Infinity) : Infinity) }
})()

const label = (m: ChapterMap) => (m.heading === 'Prologue' ? `Prologue: ${m.title}` : m.heading === 'amiibo' ? m.title : `${name(m)}: ${m.title}`)

/** Echoes on the map page: the story in one list, the optional battles in the second, the skirmishes in the third; Normal and Hard. */
export const FE15_MAP_SET: MapSet = {
  maps: FE15_MAPS,
  extras: { label: 'Optional battles', maps: SIDE },
  third: { label: 'Skirmishes', maps: SKIRMISHES },
  difficulties: [
    { value: 'Normal', label: 'Normal' },
    { value: 'Hard', label: 'Hard' },
  ],
  moveClasses: FE15_MOVE_CLASSES,
  moveClassExamples: FE15_MOVE_CLASS_EXAMPLES,
  lord: 'Alm',
  noTerrainDef: true,
  healInHp: true,
  story: FE15_BLOCK,
  chapterLabel: label,
  mapLabel: label,
}
