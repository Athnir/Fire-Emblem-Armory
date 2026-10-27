import { createElement } from 'react'
import { ChapterWeapons } from '../components/ChapterWeapons'
import type { ChapterWeaponsConfig } from '../components/ChapterWeapons'
import { GbaSupports } from '../components/GbaSupports'
import { MapViewer } from '../components/MapViewer'
import { FE8_ITEM_SOURCES } from '../data/fe8/fe8ItemSources'
import { FE8_LISTED } from '../data/fe8/fe8Listed'
import { FE8_FORK, FE8_MAP_SET, FE8_ROUTE_NAME, FE8_STORY } from '../data/fe8/fe8MapSet'
import { FE8_SUPPORTS } from '../data/fe8/fe8Supports'
import { FE8_TRIANGLE } from '../data/fe8/fe8Triangle'
import { walkFork } from '../logic/spoiler'
import type { GameParts } from '.'

const WEAPONS: ChapterWeaponsConfig = {
  weapons: FE8_LISTED,
  sources: FE8_ITEM_SOURCES,
  story: FE8_STORY,
  categories: ['Sword', 'Lance', 'Axe', 'Bow', 'Anima', 'Light', 'Dark', 'Staff', 'Stone', 'Monster'],
  magic: new Set(['Anima', 'Light', 'Dark']),
  statNames: { hp: 'HP', str: 'Str', skl: 'Skl', spd: 'Spd', def: 'Def', res: 'Res', lck: 'Lck', mov: 'Mov', con: 'Con' },
  /** Against a unit it's effective on, Mt (with the triangle's +1 or −1) is tripled (the attack routine, 0x0802AABC); the legendary
   * weapons double it instead (their own `effectiveMultiplier`). */
  effectiveMultiplier: 3,
  rankLabel: (w) => (w.rank === 'Prf' ? 'No rank needed' : `Rank ${w.rank}`),
  shopName: 'shops',
  routeName: FE8_ROUTE_NAME,
}

/** The Sacred Stones' screens and data: loaded on their own the first time the game is picked. */
const parts: GameParts = {
  weapons: () => createElement(ChapterWeapons, { config: WEAPONS }),
  maps: () => createElement(MapViewer, { set: FE8_MAP_SET }),
  supports: () => createElement(GbaSupports, { data: FE8_SUPPORTS }),
  triangle: {
    beats: FE8_TRIANGLE.beats,
    outside: "Bows, staves, dragonstones and monsters' weapons are outside the triangle.",
    advantage: [{ hit: FE8_TRIANGLE.hit, mt: FE8_TRIANGLE.mt }],
    loser: 'mirror',
    mtLabel: 'Mt',
    rules: [
      'Anima magic beats light, light beats dark, and dark beats anima, by the same amounts as the weapons.',
      `The Mt change comes before effectiveness triples Mt, so an effective weapon gains ${3 * FE8_TRIANGLE.mt} with the advantage and loses as much with the disadvantage (${2 * FE8_TRIANGLE.mt} for the legendary weapons, whose effectiveness doubles Mt).`,
      'A reaver (Swordreaver, Lancereaver, Axereaver, Swordslayer) reverses the triangle and doubles it when only one side holds one; two reavers leave it as it is.',
      "Weapon rank doesn't change it, and it's the same on every difficulty.",
    ],
    reaver: 'flip-double',
  },
  fork: FE8_FORK,
  newWeapons: (mapId, route) => {
    const story = walkFork(FE8_FORK, route).story
    const index = new Map(story.maps.map((m, i) => [m.id, i]))
    const at = index.get(mapId)
    return FE8_LISTED.filter((w) => {
      const first = Math.min(Infinity, ...(FE8_ITEM_SOURCES[w.name] ?? []).map((s) => (index.get(s.mapId) ?? Infinity) + (s.kind.endsWith('-later') ? 1 : 0)))
      return first === at
    }).length
  },
}

export default parts
