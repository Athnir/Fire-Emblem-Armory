import { FE4_ITEM_SOURCES } from '../data/fe4/fe4ItemSources'
import { FE4_STORY } from '../data/fe4/fe4MapSet'
import { FE4_WEAPONS } from '../data/fe4/fe4Weapons'
import { ChapterWeapons } from './ChapterWeapons'
import type { ChapterWeaponsConfig } from './ChapterWeapons'

const CONFIG: ChapterWeaponsConfig = {
  weapons: FE4_WEAPONS,
  sources: FE4_ITEM_SOURCES,
  story: FE4_STORY,
  categories: ['Sword', 'Lance', 'Axe', 'Bow', 'Fire', 'Thunder', 'Wind', 'Light', 'Dark', 'Staff'],
  magic: new Set(['Fire', 'Thunder', 'Wind', 'Light', 'Dark']),
  statNames: { str: 'Str', mag: 'Mag', skl: 'Skl', spd: 'Spd', lck: 'Lck', def: 'Def', mdf: 'Mdf', mov: 'Mov' },
  rankLabel: (w) => (w.rank === 'Holy' ? 'Holy weapon' : `Rank ${w.rank}`),
  shopName: 'home castle',
}

/** Genealogy of the Holy War's weapons, read from the game's own item table: a filterable list and a detail panel. */
export function Fe4Weapons() {
  return <ChapterWeapons config={CONFIG} />
}
