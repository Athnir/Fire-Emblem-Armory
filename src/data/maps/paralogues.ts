import type { ChapterMap } from './types'
import { gameMap } from './fromGame'

/*
 * The 22 paralogues, built wholly from the game's own files (see fromGame.ts). Each one's `availableIn`
 * says which routes can reach it: 1-6 every route, 7-14 Birthright and Revelation (Hoshidan fathers),
 * 15-22 Conquest and Revelation (Nohrian fathers).
 */
const EXTRA: Record<number, Partial<ChapterMap>> = {
  15: {
    notes: [
      // The chapter script (data-raw/fates/README.md, "Arrivals read by hand"): handlers 5 and 6.
      'The enemy keeps summoning from seven spawn pools, one beside each Dragon Vein: each enemy phase the next pool in turn sends one unit, going round from the vein at (18, 4) (two pools a phase on Lunatic until 20 have been counted). Groups 1-2 to 7-2 come first, each counting twice, until 12 have been counted; then Groups 1-1 to 7-1.',
      "Using a vein shuts its pool for good, but the cycle moves on to the next open pool, so the others spawn more often. A unit standing on a pool's spawn tile also blocks it.",
    ],
  },
}

export const PARALOGUE_MAPS: ChapterMap[] = Array.from({ length: 22 }, (_, i) => gameMap(`fe14-x${i + 1}`, EXTRA[i + 1]))
