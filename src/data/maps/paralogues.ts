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
      'Seven spawn pools, one beside each Dragon Vein, take turns sending reinforcements every enemy phase in a repeating cycle (Group 1 to 7 follow the cycle).',
      "Using a vein shuts its pool for good, but the cycle moves on to the next open pool, so the others spawn more often. A unit standing on a pool's spawn tile also blocks it.",
    ],
  },
}

export const PARALOGUE_MAPS: ChapterMap[] = Array.from({ length: 22 }, (_, i) => gameMap(`fe14-x${i + 1}`, EXTRA[i + 1]))
