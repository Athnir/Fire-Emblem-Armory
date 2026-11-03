import { storyOrder } from '../../logic/spoiler'
import type { MapSet } from '../maps/mapSet'
import type { ChapterMap } from '../maps/types'
import { FE17_MAPS } from './fe17Maps'
import { FE17_OPENS } from './fe17Opens'
import { FE17_MOVE_CLASSES, FE17_MOVE_CLASS_EXAMPLES } from './fe17Terrain'

const STORY_MAPS = FE17_MAPS.filter((m) => m.route === 'Story')
const PARALOGUES = FE17_MAPS.filter((m) => m.route === 'Paralogue')
const XENOLOGUE = FE17_MAPS.filter((m) => m.route === 'Fell Xenologue')
/** Each location's skirmish (a dropdown of their own: the user's call), the main story's and Fell Xenologue's. */
const SKIRMISHES = FE17_MAPS.filter((m) => m.route === 'Skirmish')
const xenologueSkirmish = (m: ChapterMap) => XENOLOGUE.some((x) => x.id === m.skirmishOf)

/** "Prologue", "Chapter 4", "Paralogue", "Fell Xenologue 1": the game's own headings. */
const name = (m: ChapterMap) => m.heading ?? m.title
const short = (m: ChapterMap) =>
  m.route === 'Paralogue' ? m.title : m.route === 'Fell Xenologue' ? `FX ${m.chapter}` : m.chapter === 0 ? 'Prologue' : `Ch.${m.chapter}`

/** Engage as it's played: the Prologue, then Chapters 1-26. A paralogue opens on the world map once the chapter it names is cleared,
 * so it's played before the next chapter's battle; Fell Xenologue opens with the Somniel's Ancient Well (fe17Opens.ts). */
export const FE17_STORY = {
  ...storyOrder(STORY_MAPS, { name, short }),
  opensAt: (id: string) => {
    const at = FE17_OPENS[id]
    return at ? STORY_MAPS.findIndex((m) => m.id === at) : Infinity
  },
}

/** Every map, for naming where a weapon turns up (a paralogue's or Fell Xenologue's too). */
export const FE17_ALL = storyOrder([...STORY_MAPS, ...PARALOGUES, ...XENOLOGUE], { name, short })

/** The stories the bar selects: the main story, and Fell Xenologue, a story of its own (the user's call). */
const STORIES = ['Main story', 'Fell Xenologue'] as const
const label = (m: ChapterMap) => (m.route === 'Story' && m.chapter === 0 ? `Prologue: ${m.title}` : `${name(m)}: ${m.title}`)

/** Engage on the map page: the main story's chapters and its paralogues (the Divine Paralogues with them), or Fell Xenologue's, on its
 * three difficulties. */
export const FE17_MAP_SET: MapSet = {
  maps: FE17_MAPS,
  routes: {
    list: STORIES,
    maps: (r) => (r === 'Fell Xenologue' ? XENOLOGUE : STORY_MAPS),
    side: (r) => (r === 'Fell Xenologue' ? [] : PARALOGUES),
    of: (m) => (m.route === 'Fell Xenologue' ? 'Fell Xenologue' : 'Main story'),
    sideLabel: 'Paralogues',
    fourth: {
      label: 'Skirmishes',
      maps: (r) => SKIRMISHES.filter((m) => xenologueSkirmish(m) === (r === 'Fell Xenologue')),
    },
  },
  difficulties: (['Normal', 'Hard', 'Maddening'] as const).map((value) => ({ value, label: value })),
  moveClasses: FE17_MOVE_CLASSES,
  moveClassExamples: FE17_MOVE_CLASS_EXAMPLES,
  lord: 'Alear',
  story: FE17_STORY,
  chapterLabel: label,
  mapLabel: label,
}
