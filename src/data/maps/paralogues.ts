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
      "Every enemy phase, each Dragon Vein you haven't used yet sends out reinforcements from beside it; using a vein stops its group.",
    ],
  },
}

export const PARALOGUE_MAPS: ChapterMap[] = Array.from({ length: 22 }, (_, i) => gameMap(`fe14-x${i + 1}`, EXTRA[i + 1]))
