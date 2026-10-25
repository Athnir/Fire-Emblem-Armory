import type { ComponentType } from 'react'
import { FatesWeapons } from '../components/FatesWeapons'
import { MapViewer } from '../components/MapViewer'
import { FatesSupports } from '../components/FatesSupports'
import { Fe9Supports } from '../components/Fe9Supports'
import { Fe10Supports } from '../components/Fe10Supports'
import { Fe9Maps } from '../components/Fe9Maps'
import { Fe9Weapons } from '../components/Fe9Weapons'
import { Fe10Weapons } from '../components/Fe10Weapons'
import { Fe10Maps } from '../components/Fe10Maps'
import { FE9_MAP_SET } from '../data/fe9/fe9MapSet'
import { FE9_WEAPONS } from '../data/fe9/fe9Weapons'
import { FE10_MAP_SET } from '../data/fe10/fe10MapSet'
import { FE10_WEAPONS } from '../data/fe10/fe10Weapons'
import type { StoryOrder } from '../data/maps/mapSet'
import type { TelliusWeapon } from '../data/fe9/types'
import { fe9ItemSources, fe10ItemSources } from '../logic/fe9ItemSources'
import { chaptersFor } from '../logic/spoilerWeapons'
import type { HitSystem } from '../logic/trueHit'

/**
 * Every game the app covers. Picking one shows all of that game's tools together; a game whose
 * weapons or maps aren't in yet shows that tab as coming soon. Adding a game is one entry here plus
 * its own data and screens.
 */
export interface Game {
  id: string
  /** As the picker lists it. */
  title: string
  /** Short form for tight spots. */
  short: string
  hitSystem: HitSystem
  weapons?: ComponentType
  maps?: ComponentType
  /** How supports boost units, and how the boosts add up. */
  supports?: ComponentType
  /** The chapters in the order they're played, for the spoiler block. A game without it can't use the block yet. */
  story?: StoryOrder
  /** What opens once the story is cleared ('The trial maps'), said when the block reaches the last chapter. */
  afterStory?: string
  /** How many weapons a chapter (a map id) gives, so the block can say what "Proceed" opened. */
  weaponsHere?: (mapId: string) => number
}

const countIn = (weapons: TelliusWeapon[], sources: Parameters<typeof chaptersFor>[1]) => (mapId: string) =>
  weapons.filter((w) => chaptersFor(w, sources).has(mapId)).length

export const GAMES: Game[] = [
  {
    id: 'fe9',
    title: 'Fire Emblem: Path of Radiance',
    short: 'Path of Radiance',
    hitSystem: '2rn',
    weapons: Fe9Weapons,
    maps: Fe9Maps,
    supports: Fe9Supports,
    story: FE9_MAP_SET.story,
    afterStory: 'The trial maps',
    weaponsHere: countIn(FE9_WEAPONS, fe9ItemSources),
  },
  {
    id: 'fe10',
    title: 'Fire Emblem: Radiant Dawn',
    short: 'Radiant Dawn',
    hitSystem: '2rn',
    weapons: Fe10Weapons,
    maps: Fe10Maps,
    supports: Fe10Supports,
    story: FE10_MAP_SET.story,
    weaponsHere: countIn(FE10_WEAPONS, fe10ItemSources),
  },
  {
    id: 'fates',
    title: 'Fire Emblem Fates',
    short: 'Fates',
    hitSystem: 'hybrid-fates',
    weapons: FatesWeapons,
    maps: MapViewer,
    supports: FatesSupports,
  },
]

export const DEFAULT_GAME = 'fates'
