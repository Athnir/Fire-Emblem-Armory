import { Fe9Maps } from '../components/Fe9Maps'
import { Fe9Supports } from '../components/Fe9Supports'
import { Fe9Weapons } from '../components/Fe9Weapons'
import { fe9ItemSources } from '../data/fe9/fe9ItemSources'
import { FE9_TRIANGLE } from '../data/fe9/fe9Triangle'
import { FE9_MAP_SET } from '../data/fe9/fe9MapSet'
import { FE9_WEAPONS } from '../data/fe9/fe9Weapons'
import type { GameParts } from '.'
import { newWeaponsIn } from './newWeapons'

/** Path of Radiance's screens and data: loaded on their own the first time the game is picked. */
const parts: GameParts = {
  weapons: Fe9Weapons,
  maps: Fe9Maps,
  supports: Fe9Supports,
  triangle: {
    beats: FE9_TRIANGLE.beats,
    outside: 'Bows, knives, light magic and staves are outside the triangle.',
    advantage: [{ hit: FE9_TRIANGLE.hit, mt: FE9_TRIANGLE.mt }],
    loser: 'mirror',
    mtLabel: 'Mt',
    rules: [
      `The Mt change comes before effectiveness doubles Mt, so an effective weapon gains ${2 * FE9_TRIANGLE.mt} with the advantage and loses as much with the disadvantage.`,
      "Weapon rank doesn't change it, and it's the same on every difficulty.",
    ],
  },
  story: FE9_MAP_SET.story,
  afterStory: 'The trial maps',
  newWeapons: newWeaponsIn(FE9_WEAPONS, fe9ItemSources, FE9_MAP_SET.story!),
}

export default parts
