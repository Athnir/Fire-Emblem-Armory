import { Fe4Maps } from '../components/Fe4Maps'
import { Fe4Supports } from '../components/Fe4Supports'
import { Fe4Weapons } from '../components/Fe4Weapons'
import type { GameParts } from '.'

/** Genealogy of the Holy War's screens and data: loaded on their own the first time the game is picked. */
const parts: GameParts = {
  weapons: Fe4Weapons,
  maps: Fe4Maps,
  supports: Fe4Supports,
}

export default parts
