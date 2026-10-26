import { FatesMaps } from '../components/FatesMaps'
import { FatesSupports } from '../components/FatesSupports'
import { FatesWeapons } from '../components/FatesWeapons'
import { FATES_FORK } from '../data/maps/fatesStory'
import { FATES_TRIANGLE } from '../data/weapons/fatesTriangle'
import { ALL_WEAPONS } from '../data/weapons'
import { firstChapter, hiddenByDefault } from '../logic/fatesWeapons'
import type { GameParts } from '.'

/** Fates' screens and data: loaded on their own the first time the game is picked. */
const parts: GameParts = {
  weapons: FatesWeapons,
  maps: FatesMaps,
  supports: FatesSupports,
  triangle: {
    beats: FATES_TRIANGLE.beats,
    outside: 'Staves and stones are outside the triangle.',
    advantage: Object.entries(FATES_TRIANGLE.advantage).map(([rank, [atk, hit]]) => ({ rank, mt: atk, hit })),
    loser: 'mirror',
    mtLabel: 'Atk',
    rules: [
      "What it's worth depends on the rank the advantaged unit has in its weapon's type; the other side loses the same amount.",
      'The side at a disadvantage also loses its weapon rank bonus (below).',
      `Reaver weapons ("Reverses the weapon triangle and doubles weapon triangle effects") turn an advantage into a disadvantage and back, at double the amount, when only one side holds one. When both do, it's back to normal.`,
    ],
    reaver: 'flip-double',
    rankBonus: {
      rows: Object.entries(FATES_TRIANGLE.rankBonus).map(([types, byRank]) => ({
        types,
        byRank,
        first: types.startsWith('Staff') ? 'Healing' : 'Atk',
      })),
      rules: [
        "A unit's rank in the weapon type it's using adds this on its own, unless it's at a triangle disadvantage.",
        "For staves it adds to the HP healed and to the staff's hit.",
      ],
    },
  },
  fork: FATES_FORK,
  newWeapons: (mapId, route) => {
    const story = FATES_FORK.choices.find((c) => c.id === route)?.story ?? FATES_FORK.before
    const at = story.maps.findIndex((m) => m.id === mapId)
    if (at < 0) return 0
    const chapter = { story, at, route: route as 'Birthright' | 'Conquest' | 'Revelation' | undefined }
    // Counts what the list shows by default: no rank rewards and no DLC items.
    return ALL_WEAPONS.filter((w) => !hiddenByDefault(w) && story.maps[firstChapter(w, chapter)]?.id === mapId).length
  },
}

export default parts
