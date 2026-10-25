import type { ComponentType } from 'react'
import type { StoryFork, StoryOrder } from '../data/maps/mapSet'
import type { HitSystem } from '../logic/trueHit'

/** What the game picker and the true hit page need: small, so it's in the app from the start. */
export interface GameInfo {
  id: string
  /** As the picker lists it. */
  title: string
  /** Short form for tight spots. */
  short: string
  hitSystem: HitSystem
}

/** A game's screens and data. These are big, so each game's are their own file, loaded when the game is first picked. */
export interface GameParts {
  weapons?: ComponentType
  maps?: ComponentType
  /** How supports boost units, and how the boosts add up. */
  supports?: ComponentType
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
