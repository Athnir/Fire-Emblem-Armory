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

/*
 * Revelation chapters 6 to Endgame, built wholly from the game's own files (see fromGame.ts). Notes the
 * files can't give go in each chapter's `extra`.
 */
export const REVELATION_MAPS: ChapterMap[] = [
  ...Array.from({ length: 22 }, (_, i) =>
    i + 6 === 10
      ? izumo()
      : i + 6 === 15
        ? gameMap('fe14r-15', { links: RAINBOW_SAGE_STAIRS })
        : i + 6 === 19
          ? hiddenStrings()
          : i + 6 === 24
            ? gameMap('fe14r-24', { notes: [DAYS_LOST_NOTE] })
            : gameMap(`fe14r-${i + 6}`),
  ),
  gameMap('fe14r-endgame', { notes: [ANANKOS_NOTE] }),
]
