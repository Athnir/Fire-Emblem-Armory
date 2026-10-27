import { createElement } from 'react'
import { ChapterWeapons } from '../components/ChapterWeapons'
import type { ChapterWeaponsConfig } from '../components/ChapterWeapons'
import { GbaSupports } from '../components/GbaSupports'
import { MapViewer } from '../components/MapViewer'
import { FE7_ITEM_SOURCES } from '../data/fe7/fe7ItemSources'
import { FE7_LISTED } from '../data/fe7/fe7Listed'
import { FE7_FORK, FE7_MAP_SET, FE7_STORY } from '../data/fe7/fe7MapSet'
import { FE7_SUPPORTS } from '../data/fe7/fe7Supports'
import { FE7_TRIANGLE } from '../data/fe7/fe7Triangle'
import { walkFork } from '../logic/spoiler'
import type { GameParts } from '.'

const WEAPONS: ChapterWeaponsConfig = {
  weapons: FE7_LISTED,
  sources: FE7_ITEM_SOURCES,
  story: FE7_STORY,
  categories: ['Sword', 'Lance', 'Axe', 'Bow', 'Anima', 'Light', 'Dark', 'Staff', 'Stone'],
  magic: new Set(['Anima', 'Light', 'Dark']),
  statNames: { hp: 'HP', str: 'Str', skl: 'Skl', spd: 'Spd', def: 'Def', res: 'Res', lck: 'Lck', mov: 'Mov', con: 'Con' },
  /** Against a unit it's effective on, Mt (with the triangle's +1 or −1) is doubled (the attack routine, 0x08028B10). */
  effectiveMultiplier: 2,
  rankLabel: (w) => (w.rank === 'Prf' ? 'No rank needed' : `Rank ${w.rank}`),
  shopName: 'shops',
}

/** The Blazing Blade's screens and data: loaded on their own the first time the game is picked. */
const parts: GameParts = {
  weapons: () => createElement(ChapterWeapons, { config: WEAPONS }),
  maps: () => createElement(MapViewer, { set: FE7_MAP_SET }),
  supports: () => createElement(GbaSupports, { data: FE7_SUPPORTS }),
  triangle: {
    beats: FE7_TRIANGLE.beats,
    outside: 'Bows, staves and dragonstones are outside the triangle.',
    advantage: [{ hit: FE7_TRIANGLE.hit, mt: FE7_TRIANGLE.mt }],
    loser: 'mirror',
    mtLabel: 'Mt',
    rules: [
      'Anima magic beats light, light beats dark, and dark beats anima, by the same amounts as the weapons.',
      `The Mt change comes before effectiveness doubles Mt, so an effective weapon gains ${2 * FE7_TRIANGLE.mt} with the advantage and loses as much with the disadvantage.`,
      'A reaver (Swordreaver, Lancereaver, Axereaver, Swordslayer) reverses the triangle and doubles it when only one side holds one; two reavers leave it as it is.',
      "Weapon rank doesn't change it, and it's the same on Hard.",
    ],
    reaver: 'flip-double',
  },
  fork: FE7_FORK,
  newWeapons: (mapId, route) => {
    const story = walkFork(FE7_FORK, route).story
    const index = new Map(story.maps.map((m, i) => [m.id, i]))
    const at = index.get(mapId)
    return FE7_LISTED.filter((w) => {
      const first = Math.min(Infinity, ...(FE7_ITEM_SOURCES[w.name] ?? []).map((s) => (index.get(s.mapId) ?? Infinity) + (s.kind.endsWith('-later') ? 1 : 0)))
      return first === at
    }).length
  },
}

export default parts
