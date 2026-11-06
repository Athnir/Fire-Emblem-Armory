import type { ItemSource } from '../../components/ChapterWeapons'

/** A battalion's stats, as the battalion page lists them (Three Houses' battalion table, fixed_data.bin section 11). */
export type Fe16BattalionStat = 'Phys' | 'Mag' | 'Hit' | 'Crit' | 'Avo' | 'Prot' | 'Res' | 'Cha'

export interface Fe16Battalion {
  /** The battalion's number in the game's table. */
  id: number
  name: string
  /** The Authority rank it needs. */
  rank: 'E' | 'D' | 'C' | 'B' | 'A'
  /** Its kind: a unit whose class flies can equip only a flying one. */
  kind: 'Infantry' | 'Armored' | 'Cavalry' | 'Flying'
  endurance: number
  /** Each stat at levels 1 to 5 (Cha doesn't rise). */
  stats: Record<Fe16BattalionStat, number[]>
  /** Its gambit (`FE16_GAMBITS`). */
  gambit: number
  /** What the Battalion Guild asks for it, where the guild offers it. */
  price?: number
  /** Only foes lead it: nothing gives it to you. */
  foeOnly?: true
}

export interface Fe16Gambit {
  id: number
  name: string
  /** An attack (against Prt), a magic attack (against Rsl), or one that helps allies. */
  kind: 'physical' | 'magic' | 'support'
  mt?: number
  hit: number
  /** Min and max range. */
  range: [number, number]
  uses: number
  /** The game's own help text: what the gambit does. */
  help: string
  /** A support gambit that restores HP (its Mt is the healing's). */
  heals?: true
  effective?: string[]
  /** The tiles it covers, from the user's tile [0, 0]: x across, y forward (the target stands at [0, -range[0]]). */
  area: [number, number][]
}

/** Where a battalion turns up, as a weapon's source, and for a line that holds on some routes only (the guild's stock, a quest) the
 * routes: 'cf', 'ss', 'am', 'vw'. */
export interface Fe16BattalionSource extends ItemSource {
  routes?: string[]
}
