import { Fe6Maps } from '../components/Fe6Maps'
import { Fe6Supports } from '../components/Fe6Supports'
import { Fe6Weapons } from '../components/Fe6Weapons'
import { FE6_ITEM_SOURCES } from '../data/fe6/fe6ItemSources'
import { FE6_LISTED } from '../data/fe6/fe6Listed'
import { FE6_FORK } from '../data/fe6/fe6MapSet'
import { FE6_TRIANGLE } from '../data/fe6/fe6Triangle'
import { walkFork } from '../logic/spoiler'
import type { GameParts } from '.'

/** The Binding Blade's screens and data: loaded on their own the first time the game is picked. */
const parts: GameParts = {
  weapons: Fe6Weapons,
  maps: Fe6Maps,
  supports: Fe6Supports,
  triangle: {
    beats: FE6_TRIANGLE.beats,
    outside: 'Bows, staves and dragonstones are outside the triangle.',
    advantage: [{ hit: FE6_TRIANGLE.hit, mt: FE6_TRIANGLE.mt }],
    loser: 'mirror',
    mtLabel: 'Mt',
    rules: [
      'Anima magic beats light, light beats dark, and dark beats anima, by the same amounts as the weapons.',
      `The Mt change comes before effectiveness triples Mt, so an effective weapon gains ${3 * FE6_TRIANGLE.mt} with the advantage and loses as much with the disadvantage.`,
      'A reaver (Swordreaver, Lancereaver, Axereaver) turns an advantage into a disadvantage and back when only one side holds one; it doesn’t double it.',
      "Weapon rank doesn't change it, and it's the same on Hard.",
    ],
    reaver: 'flip',
  },
  fork: FE6_FORK,
  afterStory: 'The trial maps',
  newWeapons: (mapId, route) => {
    const story = walkFork(FE6_FORK, route).story
    const index = new Map(story.maps.map((m, i) => [m.id, i]))
    const at = index.get(mapId)
    return FE6_LISTED.filter((w) => {
      const first = Math.min(Infinity, ...(FE6_ITEM_SOURCES[w.name] ?? []).map((s) => (index.get(s.mapId) ?? Infinity) + (s.kind.endsWith('-later') ? 1 : 0)))
      return first === at
    }).length
  },
}

export default parts
