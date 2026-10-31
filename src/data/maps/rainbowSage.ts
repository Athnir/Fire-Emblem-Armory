import type { Tile } from './types'

/**
 * The Rainbow Sage's map (Birthright 19, Conquest 11, Revelation 15): each staircase takes a unit to the other end of its pair.
 * Checked in the game by the user.
 */
export const RAINBOW_SAGE_STAIRS: [Tile, Tile][] = [
  [[6, 2], [3, 6]],
  [[15, 2], [25, 3]],
  [[19, 8], [28, 12]],
  [[9, 11], [2, 15]],
  [[7, 21], [11, 13]],
  [[23, 21], [19, 13]],
  [[15, 18], [15, 22]],
]
