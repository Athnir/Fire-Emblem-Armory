import type { ChapterMap } from './types'
import { gameMap } from './fromGame'

/*
 * Revelation chapters 6 to Endgame, built wholly from the game's own files (see fromGame.ts). Notes the
 * files can't give go in each chapter's `extra`.
 */
export const REVELATION_MAPS: ChapterMap[] = [
  ...Array.from({ length: 22 }, (_, i) => gameMap(`fe14r-${i + 6}`)),
  gameMap('fe14r-endgame'),
]
