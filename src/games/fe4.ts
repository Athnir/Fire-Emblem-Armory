import { Fe4Maps } from '../components/Fe4Maps'
import { Fe4Supports } from '../components/Fe4Supports'
import { Fe4Weapons } from '../components/Fe4Weapons'
import { FE4_ITEM_SOURCES } from '../data/fe4/fe4ItemSources'
import { FE4_STORY } from '../data/fe4/fe4MapSet'
import { FE4_WEAPONS } from '../data/fe4/fe4Weapons'
import type { GameParts } from '.'

/** Genealogy of the Holy War's screens and data: loaded on their own the first time the game is picked. */
const parts: GameParts = {
  weapons: Fe4Weapons,
  maps: Fe4Maps,
  supports: Fe4Supports,
  story: FE4_STORY,
  newWeapons: (mapId) => {
    const index = new Map(FE4_STORY.maps.map((m, i) => [m.id, i]))
    const at = index.get(mapId)
    return FE4_WEAPONS.filter((w) => {
      const first = Math.min(Infinity, ...(FE4_ITEM_SOURCES[w.name] ?? []).map((s) => (index.get(s.mapId) ?? Infinity) + (s.kind === 'drop-later' ? 1 : 0)))
      return first === at
    }).length
  },
}

export default parts
