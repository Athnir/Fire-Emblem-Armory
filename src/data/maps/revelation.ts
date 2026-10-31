import type { ChapterMap } from './types'
import { gameMap } from './fromGame'
import { GAME_TERRAIN } from './gameTerrain'
import { RAINBOW_SAGE_STAIRS } from './rainbowSage'

/**
 * Revelation 10's snow (the game's "Ice") over most of Izumo: what's under it stays hidden, and no unit can enter it until a
 * unit of yours attacks it, which clears that tile and the four beside it; foes can't. All of it gone is its second state
 * (`spent`). The user's account of the chapter.
 */
function izumo(): ChapterMap {
  const m = gameMap('fe14r-10')
  const patch = GAME_TERRAIN['fe14r-10'].spent ?? []
  return {
    ...m,
    changes: [
      ...m.changes,
      {
        id: 'snow',
        trigger: 'breakable',
        wide: true,
        dig: true,
        tile: { default: patch.find((p) => p.becomes === 'ta')!.tile },
        usableBy: 'Your units',
        effect:
          "Snow (Ice) covers most of Izumo and hides what's under it, foes included; no unit can enter it. A unit of yours that attacks a snow tile clears it and the four tiles beside it; foes can't.",
        patch,
      },
    ],
  }
}

/**
 * Revelation 19's one Dragon Vein does both things its file gives it: it splits each of your units into two, the copies being how
 * you reach the map's lower right, and it clears the rubble there (the user's account of the chapter).
 */
function hiddenStrings(): ChapterMap {
  const m = gameMap('fe14r-19')
  return {
    ...m,
    changes: m.changes.map((c) =>
      c.trigger === 'dragonVein'
        ? {
            ...c,
            effect:
              "Splits each of your units into two: the copies are how you reach the map's lower right. It also clears the rubble there, 3 tiles to floor and 9 to healing tiles.",
          }
        : c,
    ),
  }
}

/**
 * Revelation 24's patrols, read from its scripts (data-raw/fates/README.md, "Arrivals read by hand"): most of its groups wait
 * for the enemy to discover you.
 */
const DAYS_LOST_NOTE =
  "The enemy discovers you when one of its five patrols could attack one of your units or fights one (on Hard and Lunatic, when any foe could attack), or when a door is opened from the wrong side: (21, 8), (6, 17) or (13, 27) before the one beside it at (18, 8), (3, 17) or (16, 27) sets off a blast. Once the door at (16, 27) is opened first, you can't be discovered any more."

/**
 * Anankos's summons, read from the chapter script (data-raw/fates/README.md, "Anankos's summons"): each enemy phase a handler counts
 * his army and calls his summon function, which picks each summon point's group by his stage.
 */
export const ANANKOS_NOTE =
  "Anankos keeps summoning: each enemy phase he summons two units while fewer than seven of his army stand (the bosses aside), one while seven do. Each of the eight summon points holds one unit at a time and calls it back once it's defeated; which unit a point calls changes when both claws fall and again when his head falls."

/**
 * Revelation 9's whirlwinds, read live on Normal and Lunatic (data-raw/fates/README.md, "What each Dragon Vein changes"): the map
 * starts with two, and the turn and the difficulty decide the rest.
 */
const WIND_NOTE =
  'Whirlwinds rise on the top and bottom rows. Each player phase from turn 2, every whirlwind blows: your units in its five columns move five tiles along it (to the nearest tile they can stand on), and it clears. Then new ones rise: top 8-12 and bottom 17-21 on turns 1, 7, 13...; bottom 1-5, 12-16 and 21-25 on turns 4, 10, 16...; on Hard and Lunatic also bottom 3-7 and top 16-20 on turns 2, 8..., and top 7-11 and 17-21 on turns 5, 11...; on Lunatic also top 4-8 and 14-18 and bottom 9-13 and 19-23 on turns 3, 9..., and the whole bottom row on turns 6, 12...'

/** Revelation 20's bridges (read live): the first span of each pair is down when the battle starts, and only a vein moves one. */
const BRIDGES_NOTE =
  "Each bridge has two spots, and the battle starts with every bridge in its first. A Dragon Vein moves its bridge to the other spot, and the units on it; the bridges also swap by themselves (bridges 1, 4 and 7 every 3rd turn, 2, 5 and 8 every 4th, 3 and 6 every 5th), but only once no unit of yours can use a vein."

/**
 * Revelation 21's rooms, from its chapter script (handlers 19 to 35: an enemy acting in one is promoted or demoted by the vein
 * flag). Which nine are blue is from the user's screenshots of its scouting battle; either vein swaps the colours, and the
 * effects with them.
 */
const GOING_FORWARD_ROOMS: ChapterMap['rooms'] = [
  {
    color: 'blue',
    effect: 'an enemy that acts in it is promoted (Archer to Sniper, Knight to General...)',
    rects: [[6, 23, 9, 26], [1, 18, 4, 21], [11, 18, 16, 21], [22, 17, 26, 20], [6, 12, 9, 16], [18, 12, 20, 16], [8, 6, 13, 9], [21, 1, 26, 10], [1, 1, 8, 3]],
  },
  {
    color: 'red',
    effect: 'an enemy that acts in it is demoted back to its base class',
    rects: [[1, 23, 4, 26], [11, 23, 16, 26], [6, 18, 9, 21], [18, 18, 20, 20], [1, 12, 4, 16], [11, 12, 16, 16], [22, 12, 26, 15], [9, 1, 13, 4]],
  },
]

function goingForward(): ChapterMap {
  const m = gameMap('fe14r-21', { rooms: GOING_FORWARD_ROOMS })
  return { ...m, changes: m.changes.map((c) => (c.trigger === 'dragonVein' ? { ...c, swapsRooms: true as const } : c)) }
}

/** Revelation 11's veins start used up: springing a group's spike trap makes its vein usable, and the vein lowers them again. */
function forestOfMokushu(): ChapterMap {
  const m = gameMap('fe14r-11')
  return {
    ...m,
    changes: m.changes.map((c) =>
      c.trigger === 'dragonVein'
        ? { ...c, effect: `${c.effect} Usable only once that group's spikes have sprung.`, patch: undefined, noPreview: true as const }
        : c,
    ),
  }
}

const SPECIAL: Record<number, () => ChapterMap> = {
  9: () => gameMap('fe14r-9', { notes: [WIND_NOTE] }),
  10: izumo,
  11: forestOfMokushu,
  15: () => gameMap('fe14r-15', { links: RAINBOW_SAGE_STAIRS }),
  19: hiddenStrings,
  20: () => gameMap('fe14r-20', { notes: [BRIDGES_NOTE] }),
  21: goingForward,
  24: () => gameMap('fe14r-24', { notes: [DAYS_LOST_NOTE] }),
}

/*
 * Revelation chapters 6 to Endgame, built wholly from the game's own files (see fromGame.ts). Notes the
 * files can't give go in each chapter's `extra`.
 */
export const REVELATION_MAPS: ChapterMap[] = [
  ...Array.from({ length: 22 }, (_, i) => (SPECIAL[i + 6] ?? (() => gameMap(`fe14r-${i + 6}`)))()),
  gameMap('fe14r-endgame', { notes: [ANANKOS_NOTE] }),
]
