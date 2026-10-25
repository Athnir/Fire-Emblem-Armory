import { FE9_MAP_SET } from '../data/fe9/fe9MapSet'
import { FE9_BASES, FE9_WEAPONS } from '../data/fe9/fe9Weapons'
import { fe9ItemSources } from '../logic/fe9ItemSources'
import { Fe9Forge } from './Fe9Forge'
import { TelliusWeapons } from './TelliusWeapons'
import type { TelliusWeaponsConfig } from './TelliusWeapons'

const CONFIG: TelliusWeaponsConfig = {
  weapons: FE9_WEAPONS,
  story: FE9_MAP_SET.story!,
  bases: FE9_BASES,
  // Path of Radiance ends a list that runs to the last base with "onward"; Radiant Dawn groups its lists by part.
  chapterStyle: { parts: false, onward: true },
  categories: ['Sword', 'Lance', 'Axe', 'Bow', 'Knife', 'Fire', 'Thunder', 'Wind', 'Light', 'Staff'],
  /** Against a unit it's effective on, the weapon's Mt doubles (main.dol, 0x801a9084). */
  effectiveMultiplier: 2,
  mapSources: fe9ItemSources,
  forge: (w) => <Fe9Forge weapon={w} />,
}

/** Path of Radiance's weapons, read from the game's own item table. */
export function Fe9Weapons() {
  return <TelliusWeapons config={CONFIG} />
}
