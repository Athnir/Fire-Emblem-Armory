import { createElement } from 'react'
import { ChapterWeapons } from '../components/ChapterWeapons'
import type { ChapterWeaponsConfig } from '../components/ChapterWeapons'
import { MapViewer } from '../components/MapViewer'
import { FE1_ITEM_SOURCES } from '../data/fe1/fe1ItemSources'
import { FE1_LISTED } from '../data/fe1/fe1Listed'
import { FE1_MAP_SET, FE1_STORY } from '../data/fe1/fe1MapSet'
import type { GameParts } from '.'

const WEAPONS: ChapterWeaponsConfig = {
  weapons: FE1_LISTED,
  sources: FE1_ITEM_SOURCES,
  story: FE1_STORY,
  categories: ['Sword', 'Lance', 'Bow', 'Ballista', 'Axe', 'Dragonstone', 'Tome', 'Staff'],
  magic: new Set(['Tome']),
  statNames: {},
  /** Against a unit it's effective on, Mt is counted three times (the attack routine, 15:$CC84). */
  effectiveMultiplier: 3,
  rankLabel: (w) => (w.rank === 'Prf' ? 'Personal weapon' : `Weapon level ${w.rank}`),
  shopName: 'shops',
}

/** Shadow Dragon and the Blade of Light's screens and data: loaded on their own the first time the game is picked. It has no
 * supports and no weapon triangle: neither the hit nor the damage routine has a term for either. */
const parts: GameParts = {
  weapons: () => createElement(ChapterWeapons, { config: WEAPONS }),
  maps: () => createElement(MapViewer, { set: FE1_MAP_SET }),
  supports: null,
  triangle: null,
  story: FE1_STORY,
  newWeapons: (mapId) => {
    const index = new Map(FE1_STORY.maps.map((m, i) => [m.id, i]))
    const at = index.get(mapId)
    return FE1_LISTED.filter((w) => {
      const first = Math.min(Infinity, ...(FE1_ITEM_SOURCES[w.name] ?? []).map((s) => (index.get(s.mapId) ?? Infinity) + (s.kind.endsWith('-later') ? 1 : 0)))
      return first === at
    }).length
  },
}

export default parts
