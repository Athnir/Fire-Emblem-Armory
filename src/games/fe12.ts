import { createElement } from 'react'
import { ChapterWeapons } from '../components/ChapterWeapons'
import type { ChapterWeaponsConfig, ItemSource } from '../components/ChapterWeapons'
import { Fe12Forge } from '../components/Fe12Forge'
import { Fe12Supports } from '../components/Fe12Supports'
import { MapViewer } from '../components/MapViewer'
import { FE12_ITEM_SOURCES } from '../data/fe12/fe12ItemSources'
import { FE12_LISTED } from '../data/fe12/fe12Listed'
import { FE12_FORK, FE12_MAP_SET, FE12_STORY } from '../data/fe12/fe12MapSet'
import { FE12_TRIANGLE } from '../data/fe12/fe12Triangle'
import { walkFork } from '../logic/spoiler'
import { onDifficulty } from '../components/Difficulty'
import type { GameParts } from '.'

const dlc = (s: ItemSource) => s.kind.startsWith('dlc-')

const WEAPONS: ChapterWeaponsConfig = {
  weapons: FE12_LISTED,
  sources: FE12_ITEM_SOURCES,
  story: FE12_STORY,
  categories: ['Sword', 'Lance', 'Axe', 'Bow', 'Tome', 'Staff', 'Stone', 'Ballista'],
  magic: new Set(['Tome']),
  statNames: {},
  /** Against a unit it's effective on, the weapon's Mt is added twice more (overlay 00 at 0x21f3494: Mt x3). */
  effectiveMultiplier: 3,
  rankLabel: (w) => (w.rank ? `Rank ${w.rank}` : 'No weapon rank'),
  shopName: 'shops',
  routeName: (m) => (m.route === 'Extra' ? 'Archanean Chronicles' : m.route === 'DLC' ? 'DLC' : undefined),
  // The three downloadable chapters' items (on the cartridge, opened by the Nintendo WFC download in 2009-2010).
  optional: [{ label: 'Show DLC items', covers: dlc }],
  // The battle preparations' armory forges from Chapter 1 (MapTableData +0x18 0x04).
  extra: (w) => createElement(Fe12Forge, { weapon: w, opensAt: 'fe12-1' }),
}

/** New Mystery of the Emblem's screens and data: loaded on their own the first time the game is picked. Its weapon triangle and rank
 * bonuses are read in overlay 00 at 0x21f2a74 (scripts/build-triangles.py), its supports in the same overlay
 * (scripts/build-fe12-supports.py). */
const parts: GameParts = {
  weapons: () => createElement(ChapterWeapons, { config: WEAPONS }),
  maps: () => createElement(MapViewer, { set: FE12_MAP_SET }),
  supports: () => createElement(Fe12Supports),
  triangle: {
    beats: FE12_TRIANGLE.beats,
    outside: 'Bows, tomes, staves and dragonstones are outside the triangle.',
    advantage: Object.entries(FE12_TRIANGLE.advantage).map(([rank, [atk, hit]]) => ({ rank, mt: atk, hit })),
    loser: 'mirror',
    mtLabel: 'Atk',
    rules: [
      "What it's worth depends on the rank the advantaged unit has in its weapon's type; the other side loses the same amount.",
      'The side at a disadvantage also loses its weapon rank bonus (below).',
      "The attack part isn't tripled by effectiveness: only the weapon's own Mt is.",
    ],
    rankBonus: {
      rows: Object.entries(FE12_TRIANGLE.rankBonus).map(([types, byRank]) => ({
        types,
        byRank,
        first: types === 'Staff' ? 'Healing' : 'Atk',
      })),
      rules: [
        "A unit's rank in the weapon type it's using adds this on its own, unless it's at a triangle disadvantage.",
        'For staves it adds to the HP a healing staff restores.',
      ],
    },
  },
  fork: FE12_FORK,
  afterStory: 'The extra chapters',
  newWeapons: (mapId, route, difficulty = 'Normal') => {
    const story = walkFork(FE12_FORK, route).story
    const index = new Map(story.maps.map((m, i) => [m.id, i]))
    const at = index.get(mapId)
    return FE12_LISTED.filter((w) => {
      const sources = (FE12_ITEM_SOURCES[w.name] ?? []).filter((s) => !dlc(s) && onDifficulty(difficulty, s.difficulties))
      const first = Math.min(Infinity, ...sources.map((s) => (index.get(s.mapId) ?? Infinity) + (s.kind.endsWith('-later') ? 1 : 0)))
      return first === at
    }).length
  },
  difficulties: FE12_MAP_SET.difficulties,
}

export default parts
