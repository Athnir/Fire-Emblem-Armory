import { createElement } from 'react'
import { ChapterWeapons } from '../components/ChapterWeapons'
import type { ChapterWeaponsConfig } from '../components/ChapterWeapons'
import { Fe3Supports } from '../components/Fe3Supports'
import { MapViewer } from '../components/MapViewer'
import { FE3_ITEM_SOURCES } from '../data/fe3/fe3ItemSources'
import { FE3_LISTED } from '../data/fe3/fe3Listed'
import { FE3_MAP_SET, FE3_STORY } from '../data/fe3/fe3MapSet'
import type { ChapterMap } from '../data/maps/types'
import type { GameParts } from '.'

/** The book a chapter is in: Book 2 starts the army afresh, so its sources are listed apart. */
const routeName = (m: ChapterMap) => (m.id.startsWith('fe3-1-') ? 'Book 1' : 'Book 2')

const WEAPONS: ChapterWeaponsConfig = {
  weapons: FE3_LISTED,
  sources: FE3_ITEM_SOURCES,
  story: FE3_STORY,
  categories: ['Sword', 'Lance', 'Axe', 'Bow', 'Tome', 'Staff'],
  magic: new Set(['Tome']),
  statNames: {},
  /** Against a unit it's effective on, Mt is tripled (held at 33 first; the attack routine, $83:B395). */
  effectiveMultiplier: 3,
  rankLabel: (w) => (w.rank === 'Prf' ? 'Personal weapon' : `Weapon level ${w.rank}`),
  shopName: 'shops',
  routeName,
}

/** Mystery of the Emblem's screens and data: loaded on their own the first time the game is picked. It has no weapon triangle. */
const parts: GameParts = {
  weapons: () => createElement(ChapterWeapons, { config: WEAPONS }),
  maps: () => createElement(MapViewer, { set: FE3_MAP_SET }),
  supports: Fe3Supports,
  triangle: null,
  story: FE3_STORY,
  newWeapons: (mapId) => {
    const index = new Map(FE3_STORY.maps.map((m, i) => [m.id, i]))
    const at = index.get(mapId)
    return FE3_LISTED.filter((w) => {
      const first = Math.min(Infinity, ...(FE3_ITEM_SOURCES[w.name] ?? []).map((s) => (index.get(s.mapId) ?? Infinity) + (s.kind.endsWith('-later') ? 1 : 0)))
      return first === at
    }).length
  },
}

export default parts
