import { Fe10Maps } from '../components/Fe10Maps'
import { Fe10Supports } from '../components/Fe10Supports'
import { Fe10Weapons } from '../components/Fe10Weapons'
import { fe10ItemSources } from '../data/fe10/fe10ItemSources'
import { FE10_MAP_SET } from '../data/fe10/fe10MapSet'
import { FE10_WEAPONS } from '../data/fe10/fe10Weapons'
import type { GameParts } from '.'
import { newWeaponsIn } from './newWeapons'

/** Radiant Dawn's screens and data: loaded on their own the first time the game is picked. */
const parts: GameParts = {
  weapons: Fe10Weapons,
  maps: Fe10Maps,
  supports: Fe10Supports,
  story: FE10_MAP_SET.story,
  newWeapons: newWeaponsIn(FE10_WEAPONS, fe10ItemSources, FE10_MAP_SET.story!),
}

export default parts
