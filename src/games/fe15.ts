import { createElement } from 'react'
import { ChapterWeapons } from '../components/ChapterWeapons'
import type { ChapterWeaponsConfig, ItemSource } from '../components/ChapterWeapons'
import { Fe15Supports } from '../components/Fe15Supports'
import { Fe15WeaponExtra } from '../components/Fe15Weapon'
import { MapViewer } from '../components/MapViewer'
import { FE15_ITEM_SOURCES } from '../data/fe15/fe15ItemSources'
import { FE15_LISTED } from '../data/fe15/fe15Listed'
import { FE15_BLOCK, FE15_MAP_SET, FE15_STORY } from '../data/fe15/fe15MapSet'
import type { Fe15Weapon } from '../data/fe15/fe15Types'
import type { ChapterMap } from '../data/maps/types'
import { turnsUpAt } from '../logic/spoiler'
import type { GameParts } from '.'

/** Sources the list leaves out until their switch is ticked: the amiibo dungeons'. */
const amiibo = (s: ItemSource) => s.kind.startsWith('amiibo-')

const routeName = (m: ChapterMap) =>
  m.route === 'Alm' ? "Alm's army" : m.route === 'Celica' ? "Celica's army" : m.route === 'Extra' ? 'Act 6 and amiibo' : undefined

const WEAPONS: ChapterWeaponsConfig = {
  weapons: FE15_LISTED,
  sources: FE15_ITEM_SOURCES,
  story: FE15_STORY,
  categories: ['Sword', 'Lance', 'Axe', 'Bow', 'Shield', 'Ring', 'Monster'],
  magic: new Set(),
  statNames: { hp: 'HP', str: 'Atk', skl: 'Skill', spd: 'Spd', lck: 'Lck', def: 'Def', res: 'Res', mov: 'Mov', avo: 'Avo', ddg: 'Crit avoid' },
  /** Against a unit it's effective on, the weapon's Mt is added twice more (the attack routine, 0x2f0b04: Mt x3). */
  effectiveMultiplier: 3,
  rankLabel: (w) => w.rank || '',
  shopName: 'blacksmith',
  routeName,
  optional: [{ label: 'Show amiibo items', covers: amiibo }],
  extra: (w) => createElement(Fe15WeaponExtra, { weapon: w as Fe15Weapon }),
}

/** Fire Emblem Echoes: Shadows of Valentia's screens and data: loaded on their own the first time the game is picked. */
const parts: GameParts = {
  weapons: () => createElement(ChapterWeapons, { config: WEAPONS }),
  maps: () => createElement(MapViewer, { set: FE15_MAP_SET }),
  supports: Fe15Supports,
  // Echoes has no weapon triangle: its data has no triangle table and its hit and attack routines no triangle step.
  triangle: null,
  story: FE15_BLOCK,
  afterStory: 'Act 6 (the seaways to Archanea and the Thabes Labyrinth)',
  newWeapons: (mapId) => {
    const at = FE15_BLOCK.maps.findIndex((m) => m.id === mapId)
    // Counts what the list shows by default: no amiibo items.
    return FE15_LISTED.filter((w) => {
      const sources = (FE15_ITEM_SOURCES[w.name] ?? []).filter((s) => !amiibo(s))
      const first = Math.min(Infinity, ...sources.map((s) => turnsUpAt(FE15_BLOCK, s.mapId, s.kind.endsWith('-later'))))
      return first === at
    }).length
  },
}

export default parts
