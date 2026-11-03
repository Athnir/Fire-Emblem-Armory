import { storyOrder } from '../../logic/spoiler'
import type { MapSet, StoryFork, StoryOrder } from '../maps/mapSet'
import type { ChapterMap } from '../maps/types'
import { FE16_MAPS } from './fe16Maps'
import { FE16_MOVE_CLASSES, FE16_MOVE_CLASS_EXAMPLES } from './fe16Terrain'

const byId = new Map(FE16_MAPS.map((m) => [m.id, m]))
const pick = (...ids: string[]) =>
  ids.map((id) => {
    const m = byId.get(id)
    if (!m) throw new Error(`no Three Houses map ${id}`)
    return m
  })

const words = {
  name: (m: ChapterMap) => (m.chapter === 0 ? 'Prologue' : `Chapter ${m.chapter}`),
  short: (m: ChapterMap) => (m.chapter === 0 ? 'Prologue' : `Ch.${m.chapter}`),
}

/** The houses: the Prologue is everyone's, then the house you lead from Chapter 1 (its students, and the other houses in Chapters 1
 * and 7's mock battles); every other White Clouds chapter is the same for all three. The routes part at Chapter 12 (not built yet). */
const HOUSES = [
  { id: 'be', label: 'Black Eagles' },
  { id: 'bl', label: 'Blue Lions' },
  { id: 'gd', label: 'Golden Deer' },
]
const SHARED_2_6 = ['fe16-2', 'fe16-3', 'fe16-4', 'fe16-5', 'fe16-6']
const SHARED_8_11 = ['fe16-8', 'fe16-9', 'fe16-10', 'fe16-11']
const houseMaps = (h: string) => pick(`fe16-1-${h}`, ...SHARED_2_6, `fe16-7-${h}`, ...SHARED_8_11)

const ordered = (maps: ChapterMap[]): StoryOrder => storyOrder(maps, words)

/** Three Houses as the spoiler block walks it: the Prologue, then a house, its White Clouds chapters (1 to 11). */
export const FE16_FORK: StoryFork = {
  before: { ...ordered(pick('fe16-0')), opensAt: () => Infinity },
  choices: HOUSES.map((h) => ({
    id: h.id,
    label: h.label,
    proceed: `Proceed to Chapter 1 with the ${h.label}`,
    story: { ...ordered([...pick('fe16-0'), ...houseMaps(h.id)]), opensAt: () => Infinity },
  })),
}

/** Every chapter in the order the map page lists them (Chapters 1 and 7 once per house): the weapon page's chapter names without
 * the block. */
export const FE16_STORY = ordered(FE16_MAPS)

const label = (m: ChapterMap) => `${m.heading === 'Prologue' ? 'Prologue' : `Chapter ${m.chapter}`}${m.id.match(/-(be|bl|gd)$/) ? ` (${HOUSES.find((h) => m.id.endsWith(h.id))!.label})` : ''}: ${m.title}`

/** Three Houses on the map page: White Clouds (the Prologue and Chapters 1 to 11) for now; Normal, Hard and Maddening each change
 * which units the battle places and their levels. */
export const FE16_MAP_SET: MapSet = {
  maps: FE16_MAPS,
  difficulties: [
    { value: 'Normal', label: 'Normal' },
    { value: 'Hard', label: 'Hard' },
    { value: 'Maddening', label: 'Maddening' },
  ],
  moveClasses: FE16_MOVE_CLASSES,
  moveClassExamples: FE16_MOVE_CLASS_EXAMPLES,
  lord: 'Byleth',
  terrainNote: "Terrain gives Prt (Def), Rsl (Res) and Avoid by kind; a healing tile restores a share of max HP at each turn's start.",
  story: FE16_STORY,
  chapterLabel: label,
  mapLabel: label,
}
