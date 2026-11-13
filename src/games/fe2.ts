import { createElement } from 'react'
import { ChapterWeapons } from '../components/ChapterWeapons'
import type { ChapterWeaponsConfig } from '../components/ChapterWeapons'
import { MapViewer } from '../components/MapViewer'
import { FE2_ITEM_SOURCES } from '../data/fe2/fe2ItemSources'
import { FE2_LISTED } from '../data/fe2/fe2Listed'
import { FE2_BLOCK, FE2_MAP_SET, FE2_STORY } from '../data/fe2/fe2MapSet'
import type { ChapterMap } from '../data/maps/types'
import { turnsUpAt } from '../logic/spoiler'
import type { GameParts } from '.'

const routeName = (m: ChapterMap) => (m.route === 'Alm' ? "Alm's army" : m.route === 'Celica' ? "Celica's army" : m.route === 'Dungeon' ? 'the dungeons' : undefined)

const WEAPONS: ChapterWeaponsConfig = {
  weapons: FE2_LISTED,
  sources: FE2_ITEM_SOURCES,
  story: FE2_STORY,
  categories: ['Sword', 'Lance', 'Bow', 'Shield', 'Ring', 'Monster'],
  magic: new Set(),
  statNames: {},
  /** Against a unit it's effective on, the weapon's Mt counts three times (the damage routine, 9:$825E: Str + 3 × Mt). */
  effectiveMultiplier: 3,
  rankLabel: () => '',
  shopName: 'chests',
  routeName,
}

/** Fire Emblem Gaiden's screens and data: loaded on their own the first time the game is picked. It has no supports (its special
 * attacks, the triangle attack and Alm and Celica's, are a unit's) and no weapon triangle: neither the hit nor the damage routine
 * has a term for one. */
const parts: GameParts = {
  weapons: () => createElement(ChapterWeapons, { config: WEAPONS }),
  maps: () => createElement(MapViewer, { set: FE2_MAP_SET }),
  supports: null,
  triangle: null,
  story: FE2_BLOCK,
  newWeapons: (mapId) => {
    const at = FE2_BLOCK.maps.findIndex((m) => m.id === mapId)
    return FE2_LISTED.filter((w) => {
      const first = Math.min(Infinity, ...(FE2_ITEM_SOURCES[w.name] ?? []).map((s) => turnsUpAt(FE2_BLOCK, s.mapId, s.kind.endsWith('-later'))))
      return first === at
    }).length
  },
}

export default parts
