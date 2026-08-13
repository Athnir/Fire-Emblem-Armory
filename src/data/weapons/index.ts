import type { Weapon } from '../types'
import { SWORDS } from './swords'
import { SHURIKENS } from './shurikens'
import { KATANAS } from './katanas'
import { LANCES } from './lances'
import { NAGINATAS } from './naginatas'
import { AXES } from './axes'
import { CLUBS } from './clubs'
import { BOWS } from './bows'
import { YUMI } from './yumi'
import { TOMES } from './tomes'
import { SCROLLS } from './scrolls'
import { DAGGERS } from './daggers'
import { STAVES } from './staves'
import { RODS } from './rods'
import { OTHER } from './other'

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
  ...YUMI,
  ...TOMES,
  ...SCROLLS,
  ...DAGGERS,
  ...STAVES,
  ...RODS,
  ...OTHER,
]
