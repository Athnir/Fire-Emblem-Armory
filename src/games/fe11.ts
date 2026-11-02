import { createElement } from 'react'
import { ChapterWeapons } from '../components/ChapterWeapons'
import { Fe11Forge } from '../components/Fe11Forge'
import type { ChapterWeaponsConfig } from '../components/ChapterWeapons'
import { MapViewer } from '../components/MapViewer'
import { FE11_ITEM_SOURCES } from '../data/fe11/fe11ItemSources'
import { FE11_LISTED } from '../data/fe11/fe11Listed'
import { FE11_MAP_SET, FE11_STORY } from '../data/fe11/fe11MapSet'
import { FE11_TRIANGLE } from '../data/fe11/fe11Triangle'
import { onDifficulty } from '../components/Difficulty'
import type { GameParts } from '.'

const WEAPONS: ChapterWeaponsConfig = {
  weapons: FE11_LISTED,
  sources: FE11_ITEM_SOURCES,
  story: FE11_STORY,
  categories: ['Sword', 'Lance', 'Axe', 'Bow', 'Tome', 'Staff', 'Stone', 'Ballista'],
  magic: new Set(['Tome']),
  statNames: {},
  /** Against a unit it's effective on, the weapon's Mt is added twice more (overlay 00 at 0x21c7954: Mt x3). */
  effectiveMultiplier: 3,
  rankLabel: (w) => (w.rank ? `Rank ${w.rank}` : 'No weapon rank'),
  shopName: 'shops',
  // Forging opens in Chapter 4 (data-raw/fe11/README.md: not confirmed in the code).
  extra: (w) => createElement(Fe11Forge, { weapon: w, opensAt: 'fe11-4' }),
}

/** Shadow Dragon's screens and data: loaded on their own the first time the game is picked. It has no supports. Its weapon triangle
 * and rank bonuses are read in overlay 00 at 0x21c6ef0 (scripts/build-triangles.py). */
const parts: GameParts = {
  weapons: () => createElement(ChapterWeapons, { config: WEAPONS }),
  maps: () => createElement(MapViewer, { set: FE11_MAP_SET }),
  supports: null,
  triangle: {
    beats: FE11_TRIANGLE.beats,
    outside: 'Bows, tomes, staves and dragonstones are outside the triangle.',
    advantage: Object.entries(FE11_TRIANGLE.advantage).map(([rank, [atk, hit]]) => ({ rank, mt: atk, hit })),
    loser: 'mirror',
    mtLabel: 'Atk',
    rules: [
      "What it's worth depends on the rank the advantaged unit has in its weapon's type; the other side loses the same amount.",
      'The side at a disadvantage also loses its weapon rank bonus (below).',
      "The attack part isn't tripled by effectiveness: only the weapon's own Mt is.",
      "On the Hard modes, the foes the game levels have their weapon ranks raised to at least C (Hard, Brutal), B (Savage, Fiendish) or A (Merciless), and get these numbers by those ranks.",
    ],
    rankBonus: {
      rows: Object.entries(FE11_TRIANGLE.rankBonus).map(([types, byRank]) => ({ types, byRank, first: 'Atk' })),
      rules: ["A unit's rank in the weapon type it's using adds this on its own, unless it's at a triangle disadvantage."],
    },
  },
  story: FE11_STORY,
  newWeapons: (mapId, _route, difficulty = 'Normal') => {
    const index = new Map(FE11_STORY.maps.map((m, i) => [m.id, i]))
    const at = index.get(mapId)
    return FE11_LISTED.filter((w) => {
      const sources = (FE11_ITEM_SOURCES[w.name] ?? []).filter((s) => onDifficulty(difficulty, s.difficulties))
      const first = Math.min(Infinity, ...sources.map((s) => (index.get(s.mapId) ?? Infinity) + (s.kind.endsWith('-later') ? 1 : 0)))
      return first === at
    }).length
  },
  difficulties: FE11_MAP_SET.difficulties,
}

export default parts
