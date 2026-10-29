import { createElement } from 'react'
import { ChapterWeapons } from '../components/ChapterWeapons'
import type { ChapterWeaponsConfig, ItemSource } from '../components/ChapterWeapons'
import { Fe13Forge } from '../components/Fe13Forge'
import { Fe13Supports } from '../components/Fe13Supports'
import { MapViewer } from '../components/MapViewer'
import { FE13_ITEM_SOURCES } from '../data/fe13/fe13ItemSources'
import { FE13_LISTED } from '../data/fe13/fe13Listed'
import { FE13_BLOCK, FE13_MAP_SET, FE13_STORY } from '../data/fe13/fe13MapSet'
import { FE13_TRIANGLE } from '../data/fe13/fe13Triangle'
import type { ChapterMap } from '../data/maps/types'
import { turnsUpAt } from '../logic/spoiler'
import type { GameParts } from '.'

/** Sources the list leaves out until their switch is ticked: the DLC maps', and the renown rewards. */
const dlc = (s: ItemSource) => s.kind.startsWith('dlc-')
const renown = (s: ItemSource) => s.kind === 'renown'

const routeName = (m: ChapterMap) => (m.route === 'Paralogue' ? 'Paralogues' : m.route === 'DLC' ? 'DLC' : undefined)

const WEAPONS: ChapterWeaponsConfig = {
  weapons: FE13_LISTED,
  sources: FE13_ITEM_SOURCES,
  story: FE13_STORY,
  categories: ['Sword', 'Lance', 'Axe', 'Bow', 'Tome', 'Staff', 'Stone', 'Monster'],
  magic: new Set(['Tome']),
  statNames: { str: 'Str', mag: 'Mag', skl: 'Skill', spd: 'Spd', lck: 'Lck', def: 'Def', res: 'Res' },
  /** Against a unit it's effective on, the weapon's Mt is added twice more (the attack routine, 0x3efb70: Mt x3). */
  effectiveMultiplier: 3,
  rankLabel: (w) => (w.rank === '–' ? 'No weapon rank' : `Rank ${w.rank}`),
  shopName: 'shops',
  routeName,
  optional: [
    { label: 'Show DLC items', covers: dlc },
    { label: 'Show renown rewards', covers: renown },
  ],
  extra: (w) => createElement(Fe13Forge, { weapon: w }),
}

/** Fire Emblem Awakening's screens and data: loaded on their own the first time the game is picked. */
const parts: GameParts = {
  weapons: () => createElement(ChapterWeapons, { config: WEAPONS }),
  maps: () => createElement(MapViewer, { set: FE13_MAP_SET }),
  supports: Fe13Supports,
  triangle: {
    beats: FE13_TRIANGLE.beats,
    outside: "Bows, tomes, staves, stones and monsters' weapons are outside the triangle.",
    advantage: Object.entries(FE13_TRIANGLE.advantage).map(([rank, [atk, hit]]) => ({ rank, mt: atk, hit })),
    loser: 'mirror',
    mtLabel: 'Atk',
    rules: [
      "What it's worth depends on the rank the advantaged unit has in its weapon's type; the other side loses the same amount.",
      'The side at a disadvantage also loses its weapon rank bonus (below).',
      "The attack part isn't tripled by effectiveness: only the weapon's own Mt is.",
    ],
    rankBonus: {
      rows: Object.entries(FE13_TRIANGLE.rankBonus).map(([types, byRank]) => ({
        types,
        byRank,
        first: types === 'Staff' ? 'Healing' : 'Atk',
      })),
      rules: [
        "A unit's rank in the weapon type it's using adds this on its own, unless it's at a triangle disadvantage.",
        'For staves it adds to the HP healed.',
      ],
    },
  },
  story: FE13_BLOCK,
  afterStory: 'The SpotPass paralogues',
  newWeapons: (mapId) => {
    const at = FE13_BLOCK.maps.findIndex((m) => m.id === mapId)
    // Counts what the list shows by default: no DLC items and no renown rewards.
    return FE13_LISTED.filter((w) => {
      const sources = (FE13_ITEM_SOURCES[w.name] ?? []).filter((s) => !dlc(s) && !renown(s))
      const first = Math.min(Infinity, ...sources.map((s) => turnsUpAt(FE13_BLOCK, s.mapId, s.kind.endsWith('-later'))))
      return first === at
    }).length
  },
}

export default parts
