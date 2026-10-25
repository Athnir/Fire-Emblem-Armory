import { FE10_MAP_SET } from '../data/fe10/fe10MapSet'
import { FE10_WEAPONS } from '../data/fe10/fe10Weapons'
import { fe10ItemSources } from '../logic/fe9ItemSources'
import { Fe10Forge } from './Fe10Forge'
import { TelliusWeapons } from './TelliusWeapons'
import type { TelliusWeaponsConfig } from './TelliusWeapons'

const CONFIG: TelliusWeaponsConfig = {
  weapons: FE10_WEAPONS,
  story: FE10_MAP_SET.story!,
  categories: ['Sword', 'Lance', 'Axe', 'Bow', 'Crossbow', 'Knife', 'Fire', 'Thunder', 'Wind', 'Light', 'Dark', 'Staff'],
  /** Against a unit it's effective on, the weapon's Mt triples (main.dol 0x8002f37c: x << 2, minus x). */
  effectiveMultiplier: 3,
  mapSources: fe10ItemSources,
  forge: (w) => <Fe10Forge weapon={w} />,
}

/** Radiant Dawn's weapons, read from the game's own item table. */
export function Fe10Weapons() {
  return <TelliusWeapons config={CONFIG} />
}
