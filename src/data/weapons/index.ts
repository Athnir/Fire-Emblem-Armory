import type { Weapon } from '../types'
import { SWORDS } from './swords'
import { SHURIKENS } from './shurikens'
import { KATANAS } from './katanas'
import { LANCES } from './lances'
import { NAGINATAS } from './naginatas'
import { AXES } from './axes'
import { CLUBS } from './clubs'
import { BOWS } from './bows'

/** Every weapon category gets folded in here as its data file is added. */
export const ALL_WEAPONS: Weapon[] = [
  ...SWORDS,
  ...SHURIKENS,
  ...KATANAS,
  ...LANCES,
  ...NAGINATAS,
  ...AXES,
  ...CLUBS,
  ...BOWS,
]
