import { createElement } from 'react'
import { ChapterWeapons } from '../components/ChapterWeapons'
import type { ChapterWeaponsConfig } from '../components/ChapterWeapons'
import { MapViewer } from '../components/MapViewer'
import { onDifficulty } from '../components/Difficulty'
import { FE17_ITEM_SOURCES } from '../data/fe17/fe17ItemSources'
import { FE17_LISTED } from '../data/fe17/fe17Listed'
import { FE17_MAP_SET, FE17_STORY } from '../data/fe17/fe17MapSet'
import type { GameParts } from '.'

const WEAPONS: ChapterWeaponsConfig = {
  weapons: FE17_LISTED,
  sources: FE17_ITEM_SOURCES,
  story: FE17_STORY,
  categories: ['Sword', 'Lance', 'Axe', 'Bow', 'Knife', 'Tome', 'Staff', 'Arts', 'Special'],
  magic: new Set(['Tome']),
  statNames: { hp: 'HP', str: 'Str', dex: 'Dex', spd: 'Spd', lck: 'Lck', def: 'Def', mag: 'Mag', res: 'Res', bld: 'Bld', mov: 'Mov',
    avo: 'Avo', ddg: 'Ddg' },
  /** Against a unit it's effective on, the weapon's effectiveness skill multiplies by its EfficacyValue: 3 (skill.xml). */
  effectiveMultiplier: 3,
  rankLabel: (w) => (w.rank ? `Rank ${w.rank}` : 'No weapon rank'),
  shopName: 'the Somniel',
}

/** Fire Emblem Engage's screens and data: loaded on their own the first time the game is picked. */
const parts: GameParts = {
  weapons: () => createElement(ChapterWeapons, { config: WEAPONS }),
  maps: () => createElement(MapViewer, { set: FE17_MAP_SET }),
  story: FE17_STORY,
  newWeapons: (mapId, _route, difficulty = 'Normal') => {
    const index = new Map(FE17_STORY.maps.map((m, i) => [m.id, i]))
    const at = index.get(mapId)
    return FE17_LISTED.filter((w) => {
      const sources = (FE17_ITEM_SOURCES[w.name] ?? []).filter((s) => onDifficulty(difficulty, s.difficulties))
      const first = Math.min(Infinity, ...sources.map((s) => (index.get(s.mapId) ?? Infinity) + (s.kind.endsWith('-later') ? 1 : 0)))
      return first === at
    }).length
  },
  difficulties: FE17_MAP_SET.difficulties,
}

export default parts
