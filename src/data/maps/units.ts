import type { Difficulty, MapUnit, Tile } from './types'

/** Common foes by tile only (no class). `difficulties` = the ones they appear on, when not all. */
export const commons = (name: string, tiles: Tile[], difficulties?: Difficulty[]): MapUnit[] =>
  tiles.map((tile) => ({ type: 'enemy', name, tile, difficulties }))

/** Two common foes paired up on each tile. */
export const pairs = (name: string, tiles: Tile[], difficulties?: Difficulty[]): MapUnit[] =>
  tiles.map((tile) => ({ type: 'enemy', name, tile, paired: true, difficulties }))
