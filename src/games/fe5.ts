import { createElement } from 'react'
import { ChapterWeapons } from '../components/ChapterWeapons'
import type { ChapterWeaponsConfig } from '../components/ChapterWeapons'
import { Fe5Supports } from '../components/Fe5Supports'
import { MapViewer } from '../components/MapViewer'
import { FE5_ITEM_SOURCES } from '../data/fe5/fe5ItemSources'
import { FE5_LISTED } from '../data/fe5/fe5Listed'
import { FE5_FORK, FE5_MAP_SET, FE5_STORY } from '../data/fe5/fe5MapSet'
import { FE5_TRIANGLE } from '../data/fe5/fe5Triangle'
import type { ChapterMap } from '../data/maps/types'
import { walkFork } from '../logic/spoiler'
import type { GameParts } from '.'

/** The two routes after Chapter 15, as the weapon page names them; the rest of the story has none. */
const routeName = (m: ChapterMap) =>
  m.heading === 'Ch.16A' || m.heading === 'Ch.17A' ? 'Chapters 16A and 17A' : m.heading === 'Ch.16B' || m.heading === 'Ch.17B' ? 'Chapters 16B and 17B' : undefined

const WEAPONS: ChapterWeaponsConfig = {
  weapons: FE5_LISTED,
  sources: FE5_ITEM_SOURCES,
  story: FE5_STORY,
  categories: ['Sword', 'Lance', 'Axe', 'Bow', 'Fire', 'Thunder', 'Wind', 'Light', 'Dark', 'Staff'],
  magic: new Set(['Fire', 'Thunder', 'Wind', 'Light', 'Dark']),
  statNames: { str: 'Str', mag: 'Mag', skl: 'Skl', spd: 'Spd', def: 'Def', con: 'Con', lck: 'Lck', mov: 'Mov' },
  /** Against a unit it's effective on, the weapon's Mt is added twice more: tripled (the attack routine, $83:D347). */
  effectiveMultiplier: 3,
  rankLabel: (w) => (w.rank === 'Prf' ? 'No rank needed' : `Rank ${w.rank}`),
  shopName: 'shops',
  routeName,
}

const stars = [0, 1, 2, 3, 4, 5]

/** Thracia 776's screens and data: loaded on their own the first time the game is picked. */
const parts: GameParts = {
  weapons: () => createElement(ChapterWeapons, { config: WEAPONS }),
  maps: () => createElement(MapViewer, { set: FE5_MAP_SET }),
  supports: Fe5Supports,
  triangle: {
    beats: FE5_TRIANGLE.beats,
    outside: 'Bows and staves are outside the triangle.',
    advantage: [{ hit: FE5_TRIANGLE.bonus, avoid: FE5_TRIANGLE.bonus }],
    loser: 'winner-only',
    mtLabel: 'Mt',
    rules: [
      `Only the side with the advantage gets anything: +${FE5_TRIANGLE.bonus} hit and +${FE5_TRIANGLE.bonus} avoid. The other side's numbers don't change, but its hit against the higher avoid is ${FE5_TRIANGLE.bonus} lower.`,
      'Fire beats wind, wind beats thunder and thunder beats fire; light and dark magic each beat all three, and nothing beats them.',
      "A magic sword striking from 2 tiles away counts as its magic (the Flame Sword as fire), at 1 tile as a sword.",
      "Weapon rank doesn't change it.",
    ],
    leadership: {
      byStars: stars.map((n) => ({ hit: n * FE5_TRIANGLE.leadershipPerStar, avoid: n * FE5_TRIANGLE.leadershipPerStar })),
      rules: [
        `Every unit in the same army with the same leader that has leadership stars gives +${FE5_TRIANGLE.leadershipPerStar} hit and avoid per star, wherever it is on the map; several leaders add up.`,
        `Charm gives +${FE5_TRIANGLE.charm} hit and avoid to each unit of the same army within 1 to 3 tiles of the charming unit, per charming unit.`,
        'It all adds to the triangle, supports and terrain; nothing is rounded.',
      ],
    },
  },
  fork: FE5_FORK,
  newWeapons: (mapId, route) => {
    const story = walkFork(FE5_FORK, route).story
    const index = new Map(story.maps.map((m, i) => [m.id, i]))
    const at = index.get(mapId)
    return FE5_LISTED.filter((w) => {
      const first = Math.min(Infinity, ...(FE5_ITEM_SOURCES[w.name] ?? []).map((s) => (index.get(s.mapId) ?? Infinity) + (s.kind.endsWith('-later') ? 1 : 0)))
      return first === at
    }).length
  },
}

export default parts
