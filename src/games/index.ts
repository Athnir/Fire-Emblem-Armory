import type { ComponentType } from 'react'
import { FatesWeapons } from '../components/FatesWeapons'
import { MapViewer } from '../components/MapViewer'
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
}

export const GAMES: Game[] = [
  { id: 'fe9', title: 'Fire Emblem: Path of Radiance', short: 'Path of Radiance', hitSystem: '2rn' },
  { id: 'fates', title: 'Fire Emblem Fates', short: 'Fates', hitSystem: 'hybrid-fates', weapons: FatesWeapons, maps: MapViewer },
]

export const DEFAULT_GAME = 'fates'
