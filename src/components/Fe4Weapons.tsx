import { FE4_ITEM_SOURCES } from '../data/fe4/fe4ItemSources'
import { FE4_LISTED } from '../data/fe4/fe4Listed'
import { FE4_STORY } from '../data/fe4/fe4MapSet'
import { ChapterWeapons } from './ChapterWeapons'
import type { ChapterWeaponsConfig } from './ChapterWeapons'
import type { Fe4Weapon } from '../data/fe4/types'

const CONFIG: ChapterWeaponsConfig = {
  weapons: FE4_LISTED,
  sources: FE4_ITEM_SOURCES,
  story: FE4_STORY,
  categories: ['Sword', 'Lance', 'Axe', 'Bow', 'Fire', 'Thunder', 'Wind', 'Light', 'Dark', 'Staff'],
  magic: new Set(['Fire', 'Thunder', 'Wind', 'Light', 'Dark']),
  statNames: { str: 'Str', mag: 'Mag', skl: 'Skl', spd: 'Spd', lck: 'Lck', def: 'Def', mdf: 'Mdf', mov: 'Mov' },
  rankLabel: (w) => (w.rank === 'Holy' ? 'Holy weapon' : `Rank ${w.rank}`),
  shopName: 'home castle',
  // The game counts kills on each copy (+5, up to 100: $87:E13D, $87:E163): from 50 on, one of your units wielding it gets Skl + kills
  // - 50 crit, Critical or not ($84:FD98). Bargain halves repairs as it halves prices ($84:B3C3).
  extra: (w) => {
    const repair = (w as Fe4Weapon).repair
    return (
      <p className="text-neutral-500">
        {repair !== undefined && `Repairing it costs ${repair.toLocaleString()} gold per use spent (half with Bargain). `}
        From its 50th kill on, one of your units wielding it gets Skl + kills - 50 crit, Critical or not.
      </p>
    )
  },
}

/** Genealogy of the Holy War's weapons, read from the game's own item table: a filterable list and a detail panel. */
export function Fe4Weapons() {
  return <ChapterWeapons config={CONFIG} />
}
