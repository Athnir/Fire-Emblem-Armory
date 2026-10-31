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

/*
 * Revelation chapters 6 to Endgame, built wholly from the game's own files (see fromGame.ts). Notes the
 * files can't give go in each chapter's `extra`.
 */
export const REVELATION_MAPS: ChapterMap[] = [
  ...Array.from({ length: 22 }, (_, i) => (i + 6 === 10 ? izumo() : i + 6 === 15 ? gameMap('fe14r-15', { links: RAINBOW_SAGE_STAIRS }) : i + 6 === 19 ? hiddenStrings() : gameMap(`fe14r-${i + 6}`))),
  gameMap('fe14r-endgame'),
]
