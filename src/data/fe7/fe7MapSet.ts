import { storyOrder } from '../../logic/spoiler'
import type { MapSet, StoryFork, StoryOrder } from '../maps/mapSet'
import type { ChapterMap } from '../maps/types'
import { FE7_MAPS } from './fe7Maps'
import { FE7_MOVE_CLASSES, FE7_MOVE_CLASS_EXAMPLES } from './fe7Terrain'

const byId = new Map(FE7_MAPS.map((m) => [m.id, m]))
const pick = (...ids: string[]) =>
  ids.map((id) => {
    const m = byId.get(id)
    if (!m) throw new Error(`no FE7 map ${id}`)
    return m
  })

const STORIES = ['Lyn', 'Eliwood', 'Hector'] as const
/** The version a chapter's title names ('Four-Fanged Offense (vs Lloyd)'), where the story has two. */
const version = (m: ChapterMap) => m.title.match(/\((vs [^)]+)\)$/)?.[1]

function chapterName(m: ChapterMap) {
  const h = m.heading ?? `Ch.${m.chapter}`
  const base = h === 'Final' ? 'Final Chapter' : h === 'Prologue' ? 'Prologue' : `Chapter ${h.slice(3)}`
  const v = version(m)
  return v ? `${base} (${v})` : base
}

const words = { name: chapterName, short: (m: ChapterMap) => m.heading ?? `Ch.${m.chapter}` }
/** Without the block every story is listed at once, so each chapter says whose story it's in. */
const wordsWithStory = {
  name: (m: ChapterMap) => (m.route === 'Lyn' ? chapterName(m) : `${chapterName(m)}, ${m.route}'s story`),
  short: (m: ChapterMap) => (m.route === 'Lyn' ? words.short(m) : `${words.short(m)} (${m.route[0]})`),
}

const ofStory = (story: string) => FE7_MAPS.filter((m) => m.route === story)

// The stories as the game plays them: Lyn's first, then Eliwood's or Hector's. Each of those splits twice: Lloyd or Linus in
// Chapter 23 (Hector's 24), by the lords' levels, then Kenneth or Jerme in 25 (Hector's 27), by the EXP your magic users gained.
// The gaiden chapters are listed where they come, as every GBA game's are.
const LYN = ofStory('Lyn')
const ELIWOOD = {
  before: pick('fe7-e-11', 'fe7-e-12', 'fe7-e-13', 'fe7-e-13x', 'fe7-e-14', 'fe7-e-15', 'fe7-e-16', 'fe7-e-16x', 'fe7-e-17', 'fe7-e-18',
    'fe7-e-18x', 'fe7-e-19', 'fe7-e-20', 'fe7-e-21', 'fe7-e-22', 'fe7-e-22x'),
  first: ['fe7-e-23-lloyd', 'fe7-e-23-linus'],
  middle: pick('fe7-e-24'),
  second: ['fe7-e-25-kenneth', 'fe7-e-25-jerme'],
  after: pick('fe7-e-26', 'fe7-e-26x', 'fe7-e-27', 'fe7-e-28', 'fe7-e-29', 'fe7-e-29x', 'fe7-e-30', 'fe7-e-final', 'fe7-e-final-2'),
  numbers: ['23', '25'],
}
const HECTOR = {
  before: pick('fe7-h-11', 'fe7-h-12', 'fe7-h-13', 'fe7-h-13x', 'fe7-h-14', 'fe7-h-15', 'fe7-h-16', 'fe7-h-17', 'fe7-h-17x', 'fe7-h-18',
    'fe7-h-19', 'fe7-h-19x', 'fe7-h-19x-2', 'fe7-h-20', 'fe7-h-21', 'fe7-h-22', 'fe7-h-23', 'fe7-h-23x'),
  first: ['fe7-h-24-lloyd', 'fe7-h-24-linus'],
  middle: pick('fe7-h-25', 'fe7-h-26'),
  second: ['fe7-h-27-kenneth', 'fe7-h-27-jerme'],
  after: pick('fe7-h-28', 'fe7-h-28x', 'fe7-h-29', 'fe7-h-30', 'fe7-h-31', 'fe7-h-31x', 'fe7-h-32', 'fe7-h-32x', 'fe7-h-final',
    'fe7-h-final-2'),
  numbers: ['24', '27'],
}

/** The story up to a split: nothing outside it opens. */
const upToSplit = (maps: ChapterMap[]): StoryOrder => ({ ...storyOrder(maps, words), opensAt: () => Infinity })
const toTheEnd = (maps: ChapterMap[]): StoryOrder => ({ ...storyOrder(maps, words), opensAt: () => Infinity })
const versus = (id: string) => version(byId.get(id)!)!.slice(3)

function lordStory(id: string, label: string, s: typeof ELIWOOD) {
  const start = [...LYN, ...s.before]
  const secondSplit = (first: ChapterMap[]): StoryFork => ({
    before: upToSplit(first),
    choices: s.second.map((v) => ({
      id: versus(v).toLowerCase(),
      label: `${s.numbers[1]}: ${versus(v)}`,
      proceed: `Proceed to Chapter ${s.numbers[1]} (vs ${versus(v)})`,
      story: toTheEnd([...first, ...pick(v), ...s.after]),
    })),
  })
  const firstSplit: StoryFork = {
    before: upToSplit(start),
    choices: s.first.map((v) => {
      const first = [...start, ...pick(v), ...s.middle]
      return {
        id: versus(v).toLowerCase(),
        label: `${s.numbers[0]}: ${versus(v)}`,
        proceed: `Proceed to Chapter ${s.numbers[0]} (vs ${versus(v)})`,
        story: upToSplit(first),
        fork: secondSplit(first),
      }
    }),
  }
  return { id, label, proceed: `Proceed to ${label} (Chapter 11)`, story: upToSplit(start), fork: firstSplit }
}

/**
 * The Blazing Blade as the spoiler block walks it: Lyn's story, then Eliwood's or Hector's (Hector's opens once Eliwood's is
 * cleared, but the block lets you pick), each splitting at Lloyd or Linus and at Kenneth or Jerme.
 */
export const FE7_FORK: StoryFork = {
  before: upToSplit(LYN),
  choices: [lordStory('eliwood', "Eliwood's story", ELIWOOD), lordStory('hector', "Hector's story", HECTOR)],
}

/** Every chapter in the order the map page lists them (each story in turn): the weapon page's chapter names without the block. */
export const FE7_STORY = storyOrder(FE7_MAPS, wordsWithStory)

const label = (m: ChapterMap) => `${chapterName(m).replace(/ \(vs [^)]+\)$/, '')}: ${m.title}`

/** The Blazing Blade on the map page: a button per story, Normal and Hard (Lyn's story is Normal only). */
export const FE7_MAP_SET: MapSet = {
  maps: FE7_MAPS,
  routes: {
    list: STORIES,
    maps: (story) => ofStory(story),
    side: () => [],
    of: (m) => m.route,
  },
  difficulties: [
    { value: 'Normal', label: 'Normal' },
    { value: 'Hard', label: 'Hard' },
  ],
  moveClasses: FE7_MOVE_CLASSES,
  moveClassExamples: FE7_MOVE_CLASS_EXAMPLES,
  lord: 'Lyn',
  terrainNote: 'Fliers get no Def or Avoid from terrain (their rows in the game are all 0); Res still applies.',
  chapterLabel: label,
  mapLabel: label,
}
