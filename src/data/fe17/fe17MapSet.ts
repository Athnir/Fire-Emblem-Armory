import { storyOrder } from '../../logic/spoiler'
import type { MapSet } from '../maps/mapSet'
import type { ChapterMap } from '../maps/types'
import { FE17_MAPS } from './fe17Maps'
import { FE17_OPENS } from './fe17Opens'
import { FE17_MOVE_CLASSES, FE17_MOVE_CLASS_EXAMPLES } from './fe17Terrain'

const STORY_MAPS = FE17_MAPS.filter((m) => m.route === 'Story')
const PARALOGUES = FE17_MAPS.filter((m) => m.route === 'Paralogue')

/** "Prologue", "Chapter 4", "Paralogue": the game's own headings. */
const name = (m: ChapterMap) => m.heading ?? m.title
const short = (m: ChapterMap) => (m.route === 'Paralogue' ? m.title : m.chapter === 0 ? 'Prologue' : `Ch.${m.chapter}`)

/** Engage as it's played: the Prologue, then Chapters 1-26. A paralogue opens on the world map once the chapter it names is cleared,
 * so it's played before the next chapter's battle (fe17Opens.ts). */
export const FE17_STORY = {
  ...storyOrder(STORY_MAPS, { name, short }),
  opensAt: (id: string) => {
    const at = FE17_OPENS[id]
    return at ? STORY_MAPS.findIndex((m) => m.id === at) : Infinity
  },
}

const label = (m: ChapterMap) => (m.route === 'Paralogue' ? `${m.heading}: ${m.title}` : `${name(m)}: ${m.title}`)

/** Engage on the map page: the story's chapters in one list, the paralogues in a second, on its three difficulties. */
export const FE17_MAP_SET: MapSet = {
  maps: FE17_MAPS,
  extras: { label: 'Paralogues', maps: PARALOGUES },
  difficulties: (['Normal', 'Hard', 'Maddening'] as const).map((value) => ({ value, label: value })),
  moveClasses: FE17_MOVE_CLASSES,
  moveClassExamples: FE17_MOVE_CLASS_EXAMPLES,
  lord: 'Alear',
  story: FE17_STORY,
  chapterLabel: label,
  mapLabel: label,
}
