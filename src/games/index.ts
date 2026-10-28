import type { ComponentType } from 'react'
import type { StoryFork, StoryOrder } from '../data/maps/mapSet'
import type { TriangleRules } from '../logic/triangle'
import type { HitSystem } from '../logic/trueHit'

/** What the game picker and the true hit page need: small, so it's in the app from the start. */
export interface GameInfo {
  id: string
  /** As the picker lists it. */
  title: string
  /** Short form for tight spots. */
  short: string
  /** Missing while the game's hit system hasn't been checked in its own code yet. */
  hitSystem?: HitSystem
}

/** A game's screens and data. These are big, so each game's are their own file, loaded when the game is first picked. */
export interface GameParts {
  weapons?: ComponentType
  maps?: ComponentType
  /** How supports boost units, and how the boosts add up. `null`: the game has nothing like supports, so the tab is left out. */
  supports?: ComponentType | null
  /** The weapon triangle: who beats whom, what it's worth, its special rules, and leadership where the game has it. */
  triangle?: TriangleRules
  /** The chapters in the order they're played, for the spoiler block. A game without it can't use the block yet. */
  story?: StoryOrder
  /** For a game whose story splits (Fates' routes): the chapters before the split and one story per route. */
  fork?: StoryFork
  /** What opens once the story is cleared ('The trial maps'), said when the block reaches the last chapter. */
  afterStory?: string
  /** How many weapons turn up for the first time in a chapter (a map id), so the block can say what "Proceed" opened. */
  newWeapons?: (mapId: string, route?: string) => number
}

/**
 * Every game the app covers. Picking one shows all of that game's tools together; a game whose weapons or maps aren't in
 * yet shows that tab as coming soon. Adding a game is one entry here plus its own file in this folder (`load` imports it),
 * its data and its screens. The build precaches every file, so each game works offline without being opened first.
 */
export interface Game extends GameInfo {
  load: () => Promise<GameParts>
}

export const GAMES: Game[] = [
  {
    id: 'fe4',
    title: 'Fire Emblem: Genealogy of the Holy War',
    short: 'Genealogy of the Holy War',
    hitSystem: '1rn',
    load: () => import('./fe4').then((m) => m.default),
  },
  {
    id: 'fe5',
    title: 'Fire Emblem: Thracia 776',
    short: 'Thracia 776',
    hitSystem: '1rn',
    load: () => import('./fe5').then((m) => m.default),
  },
  {
    id: 'fe6',
    title: 'Fire Emblem: The Binding Blade',
    short: 'The Binding Blade',
    hitSystem: '2rn',
    load: () => import('./fe6').then((m) => m.default),
  },
  {
    id: 'fe7',
    title: 'Fire Emblem: The Blazing Blade',
    short: 'The Blazing Blade',
    hitSystem: '2rn',
    load: () => import('./fe7').then((m) => m.default),
  },
  {
    id: 'fe8',
    title: 'Fire Emblem: The Sacred Stones',
    short: 'The Sacred Stones',
    hitSystem: '2rn',
    load: () => import('./fe8').then((m) => m.default),
  },
  {
    id: 'fe9',
    title: 'Fire Emblem: Path of Radiance',
    short: 'Path of Radiance',
    hitSystem: '2rn',
    load: () => import('./fe9').then((m) => m.default),
  },
  {
    id: 'fe10',
    title: 'Fire Emblem: Radiant Dawn',
    short: 'Radiant Dawn',
    hitSystem: '2rn',
    load: () => import('./fe10').then((m) => m.default),
  },
  {
    id: 'fates',
    title: 'Fire Emblem Fates',
    short: 'Fates',
    hitSystem: 'hybrid-fates',
    load: () => import('./fates').then((m) => m.default),
  },
]

export const DEFAULT_GAME = 'fates'
