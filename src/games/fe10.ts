import { Fe10Maps } from '../components/Fe10Maps'
import { Fe10Supports } from '../components/Fe10Supports'
import { Fe10Weapons } from '../components/Fe10Weapons'
import { fe10ItemSources } from '../data/fe10/fe10ItemSources'
import { FE10_TRIANGLE } from '../data/fe10/fe10Triangle'
import { FE10_MAP_SET } from '../data/fe10/fe10MapSet'
import { FE10_WEAPONS } from '../data/fe10/fe10Weapons'
import type { GameParts } from '.'
import { newWeaponsIn } from './newWeapons'

/** Radiant Dawn's screens and data: loaded on their own the first time the game is picked. */
const parts: GameParts = {
  weapons: Fe10Weapons,
  maps: Fe10Maps,
  supports: Fe10Supports,
  triangle: {
    beats: FE10_TRIANGLE.beats,
    outside: 'Bows, crossbows, knives, staves and laguz strikes are outside the triangle.',
    advantage: [{ hit: FE10_TRIANGLE.hit, mt: FE10_TRIANGLE.mt }],
    loser: 'mirror',
    mtLabel: 'Mt',
    rules: [
      'Turned off on Hard mode, for both sides.',
      'Against light and dark, fire, thunder and wind count as one: each beats light, and dark beats all three. Among themselves they go fire > wind > thunder > fire.',
      `The Mt change comes before effectiveness triples Mt, so an effective weapon gains ${3 * FE10_TRIANGLE.mt} with the advantage and loses as much with the disadvantage.`,
      "Weapon rank doesn't change it.",
    ],
    offOn: 'Hard mode',
    leadership: {
      byStars: [0, 1, 2, 3, 4, 5].map((n) => ({ hit: n * FE10_TRIANGLE.leadershipPerStar, avoid: n * FE10_TRIANGLE.leadershipPerStar })),
      rules: [
        `Every unit in an army gets +${FE10_TRIANGLE.leadershipPerStar} hit and +${FE10_TRIANGLE.leadershipPerStar} avoid for each star of its commander's leadership, wherever they stand on the map.`,
        "The other army's leadership doesn't lower yours; each side only adds its own.",
      ],
    },
  },
  story: FE10_MAP_SET.story,
  newWeapons: newWeaponsIn(FE10_WEAPONS, fe10ItemSources, FE10_MAP_SET.story!),
}

export default parts
