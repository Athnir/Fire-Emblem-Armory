import type { ChapterMap } from './types'
import { RAINBOW_SAGE_STAIRS } from './rainbowSage'
import { gameMap } from './fromGame'

/*
 * Birthright chapters 6 to Endgame, built wholly from the game's own files (see fromGame.ts). Notes the
 * files can't give go in each chapter's `extra`.
 */
export const BIRTHRIGHT_MAPS: ChapterMap[] = [
  ...Array.from({ length: 22 }, (_, i) => (i + 6 === 19 ? gameMap('fe14b-19', { links: RAINBOW_SAGE_STAIRS }) : gameMap(`fe14b-${i + 6}`))),
  gameMap('fe14b-endgame'),
]
