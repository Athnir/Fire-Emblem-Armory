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
}

export const GAMES: Game[] = [
  { id: 'fe9', title: 'Fire Emblem: Path of Radiance', short: 'Path of Radiance', hitSystem: '2rn', weapons: Fe9Weapons, maps: Fe9Maps, supports: Fe9Supports },
  { id: 'fe10', title: 'Fire Emblem: Radiant Dawn', short: 'Radiant Dawn', hitSystem: '2rn', weapons: Fe10Weapons, maps: Fe10Maps, supports: Fe10Supports },
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
