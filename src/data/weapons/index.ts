import type { Weapon } from '../types'
import { SWORDS } from './swords'

/** Every weapon type gets folded in here as its data file is added — Swords is the first. */
export const ALL_WEAPONS: Weapon[] = [...SWORDS]
