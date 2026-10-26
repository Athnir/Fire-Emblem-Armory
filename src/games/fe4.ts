import { Fe4Maps } from '../components/Fe4Maps'
import { Fe4Weapons } from '../components/Fe4Weapons'
import { FE4_BONUSES } from '../data/fe4/fe4Bonuses'
import { FE4_ITEM_SOURCES } from '../data/fe4/fe4ItemSources'
import { FE4_STORY } from '../data/fe4/fe4MapSet'
import { FE4_WEAPONS } from '../data/fe4/fe4Weapons'
import type { GameParts } from '.'

/** Genealogy of the Holy War's screens and data: loaded on their own the first time the game is picked. */
const parts: GameParts = {
  weapons: Fe4Weapons,
  maps: Fe4Maps,
  // No support levels; the Charisma and lover bonuses that stand in for them are a unit's own (the Unit Planner's).
  supports: null,
  triangle: {
    beats: FE4_BONUSES.beats,
    outside: 'Bows and staves are outside the triangle.',
    advantage: [{ hit: FE4_BONUSES.triangle, avoid: FE4_BONUSES.triangle }],
    loser: 'winner-only',
    mtLabel: 'Mt',
    rules: [
      `Only the side with the advantage gets anything: +${FE4_BONUSES.triangle} hit and +${FE4_BONUSES.triangle} avoid. The other side's numbers don't change, but its hit against the higher avoid is ${FE4_BONUSES.triangle} lower.`,
      'Light and dark magic each beat fire, thunder and wind; nothing beats them.',
      "Weapon rank doesn't change it.",
    ],
    leadership: {
      byStars: FE4_BONUSES.leadership.map((v) => ({ hit: v, avoid: v })),
      rules: [
        `A unit gets its commander's leadership bonus while the commander is within ${FE4_BONUSES.reach} tiles (counting steps) and in the same army.`,
        'The lord (Sigurd, then Seliph) gets their own leadership bonus wherever they are.',
        'It adds to the triangle and anything else; nothing is rounded.',
      ],
    },
  },
  story: FE4_STORY,
  newWeapons: (mapId) => {
    const index = new Map(FE4_STORY.maps.map((m, i) => [m.id, i]))
    const at = index.get(mapId)
    return FE4_WEAPONS.filter((w) => {
      const first = Math.min(Infinity, ...(FE4_ITEM_SOURCES[w.name] ?? []).map((s) => (index.get(s.mapId) ?? Infinity) + (s.kind === 'drop-later' ? 1 : 0)))
      return first === at
    }).length
  },
}

export default parts
