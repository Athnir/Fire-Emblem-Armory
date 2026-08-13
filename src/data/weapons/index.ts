import type { Weapon } from '../types'
import { SWORDS } from './swords'
import { SHURIKENS } from './shurikens'

/** Every weapon category gets folded in here as its data file is added. */
export const ALL_WEAPONS: Weapon[] = [...SWORDS, ...SHURIKENS]
