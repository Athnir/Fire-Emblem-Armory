import { FE6_ITEM_SOURCES } from '../data/fe6/fe6ItemSources'
import { FE6_STORY } from '../data/fe6/fe6MapSet'
import { FE6_LISTED } from '../data/fe6/fe6Listed'
import { ChapterWeapons } from './ChapterWeapons'
import type { ChapterWeaponsConfig } from './ChapterWeapons'

const CONFIG: ChapterWeaponsConfig = {
  weapons: FE6_LISTED,
  sources: FE6_ITEM_SOURCES,
  story: FE6_STORY,
  categories: ['Sword', 'Lance', 'Axe', 'Bow', 'Anima', 'Light', 'Dark', 'Staff', 'Stone'],
  magic: new Set(['Anima', 'Light', 'Dark']),
  statNames: { hp: 'HP', str: 'Str', skl: 'Skl', spd: 'Spd', def: 'Def', res: 'Res', lck: 'Lck', mov: 'Mov', con: 'Con' },
  /** Against a unit it's effective on, Mt is tripled (the attack routine, 0x0802489C). */
  effectiveMultiplier: 3,
  rankLabel: (w) => (w.rank === 'Prf' ? 'No rank needed' : `Rank ${w.rank}`),
  shopName: 'shops',
}

/** The Binding Blade's weapons, read from the game's own item table: a filterable list and a detail panel. */
export function Fe6Weapons() {
  return <ChapterWeapons config={CONFIG} />
}
