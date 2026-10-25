import { FatesMaps } from '../components/FatesMaps'
import { FatesSupports } from '../components/FatesSupports'
import { FatesWeapons } from '../components/FatesWeapons'
import type { GameParts } from '.'

/** Fates' screens and data: loaded on their own the first time the game is picked. */
const parts: GameParts = { weapons: FatesWeapons, maps: FatesMaps, supports: FatesSupports }

export default parts
