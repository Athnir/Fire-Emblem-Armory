import { storyOrder } from '../../logic/spoiler'
import type { MapSet, StoryFork, StoryOrder } from '../maps/mapSet'
import type { ChapterMap } from '../maps/types'
import { FE12_MAPS } from './fe12Maps'
import { FE12_MOVE_CLASSES, FE12_MOVE_CLASS_EXAMPLES } from './fe12Terrain'

const ROMAN = ['', 'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII']
/** The prologue chapters played on the answer at the end of the chapter before ('Yes': the game's second version, bmap204B...). */
const ANSWERED: Record<string, string> = { 'fe12-p4b': 'Yes', 'fe12-p4': 'No', 'fe12-p6b': 'Yes', 'fe12-p6': 'No', 'fe12-p7b': 'Yes', 'fe12-p7': 'No' }

/** "Prologue IV (Yes)", "Chapter 6x", "Endgame", "Chronicles 2", "DLC 1": the game's own headings. */
const name = (m: ChapterMap) => {
  if (m.heading === 'Prologue') return `Prologue ${ROMAN[m.chapter ?? 0]}` + (ANSWERED[m.id] ? ` (${ANSWERED[m.id]})` : '')
  if (m.heading === 'Endgame') return 'Endgame'
  if (m.heading === 'Chronicles') return `Archanean Chronicles ${m.chapter}`
  if (m.heading === 'DLC') return `DLC ${m.chapter}`
  return `Chapter ${m.id.replace('fe12-', '')}`
}
const short = (m: ChapterMap) => {
  if (m.heading === 'Prologue') return `P.${ROMAN[m.chapter ?? 0]}` + (ANSWERED[m.id] ? ` (${ANSWERED[m.id]})` : '')
  if (m.heading === 'Endgame') return 'Endgame'
  if (m.heading === 'Chronicles') return `Chronicles ${m.chapter}`
  if (m.heading === 'DLC') return `DLC ${m.chapter}`
  return `Ch.${m.id.replace('fe12-', '')}`
}
const words = { name, short }

const STORY_MAPS = FE12_MAPS.filter((m) => m.route === 'Story')
const EXTRAS = FE12_MAPS.filter((m) => m.route !== 'Story')
const byId = new Map(FE12_MAPS.map((m) => [m.id, m]))
const pick = (ids: string[]) =>
  ids.map((id) => {
    const m = byId.get(id)
    if (!m) throw new Error(`no FE12 map ${id}`)
    return m
  })

// The story's stretches: Prologue I-III; then each of three answers picks a version of the next chapter (Prologue IV after III's end,
// VI after V's, VII after VI's), the stretches between shared; Prologue VIII to the Endgame, with the gaiden chapters where they come.
const BEFORE = pick(['fe12-p1', 'fe12-p2', 'fe12-p3'])
const SPLITS: [string, string, string][] = [
  ['fe12-p4', 'fe12-p4b', 'Prologue IV'],
  ['fe12-p6', 'fe12-p6b', 'Prologue VI'],
  ['fe12-p7', 'fe12-p7b', 'Prologue VII'],
]
const SPLIT_IDS = new Set(SPLITS.flatMap(([a, b]) => [a, b]))
const firstOf = (id: string) => STORY_MAPS.findIndex((m) => m.id === id)
const AFTER = [pick(['fe12-p5']), [], STORY_MAPS.slice(firstOf('fe12-p8')).filter((m) => !SPLIT_IDS.has(m.id))]

/** The story up to a split: nothing outside it opens. */
const upToSplit = (maps: ChapterMap[]): StoryOrder => ({ ...storyOrder(maps, words), opensAt: () => Infinity })

/** A whole story down one set of answers: the extra chapters open once it's cleared. */
function toTheEnd(maps: ChapterMap[]): StoryOrder {
  const extras = new Set(EXTRAS.map((m) => m.id))
  return { ...storyOrder(maps, words), opensAt: (id) => (extras.has(id) ? maps.length - 1 : Infinity) }
}

function fork(before: ChapterMap[], k: number): StoryFork {
  const [no, yes, chapter] = SPLITS[k]
  const choice = (id: string, answer: string) => {
    const maps = [...before, ...pick([id]), ...AFTER[k]]
    const last = k === SPLITS.length - 1
    return {
      id: answer.toLowerCase(),
      label: `${chapter} (${answer})`,
      proceed: `Proceed to ${chapter} (answered ${answer})`,
      story: last ? toTheEnd(maps) : upToSplit(maps),
      ...(last ? {} : { fork: fork(maps, k + 1) }),
    }
  }
  return { before: upToSplit(before), choices: [choice(yes, 'Yes'), choice(no, 'No')] }
}

/** New Mystery of the Emblem as the spoiler block walks it: the prologue's three answers, each picking a version of a chapter. */
export const FE12_FORK: StoryFork = fork(BEFORE, 0)

/** Every chapter in the order the map page lists them (both versions of each prologue chapter in turn): the weapon page's names. */
export const FE12_STORY = storyOrder(STORY_MAPS, words)

const label = (m: ChapterMap) => `${name(m)}: ${m.title}`

/** New Mystery of the Emblem on the map page: the story's chapters, and the Archanean Chronicles and downloadable chapters in a list
 * of their own; its five modes (the translation's names), each its own: their foes, items and gaiden turn limits differ. */
export const FE12_MAP_SET: MapSet = {
  maps: FE12_MAPS,
  extras: { label: 'Extra chapters', maps: EXTRAS },
  difficulties: (['Normal', 'Hard', 'Maniac', 'Lunatic', 'Reverse Lunatic'] as const).map((value) => ({ value, label: value })),
  moveClasses: FE12_MOVE_CLASSES,
  moveClassExamples: FE12_MOVE_CLASS_EXAMPLES,
  lord: 'Marth',
  terrainNote: 'Fliers get no Def or Avoid from terrain.',
  story: FE12_STORY,
  chapterLabel: label,
  mapLabel: label,
}
