import type { ChapterWeapon } from '../../components/ChapterWeapons'

/** A combat art a weapon teaches (Data/Skill.bin's 戦技 rows): learned once the unit's mastery of the weapon reaches `mastery`. */
export interface Fe15Art {
  /** null: the item names an art no skill has (the Sage's and Hexlock Shields' 'SID_G.物理半減' / 'SID_G.魔法半減'). */
  name: string | null
  id?: string
  mastery?: number
  /** HP the art costs. */
  hp?: number
  mt?: number
  hit?: number
  avo?: number
  crit?: number
  range?: number
  /** Hits in one attack (Double Lion: 2, Astral Blade: 5). */
  strikes?: number
  /** Attack as a percentage of normal (Astral Blade: 50). */
  attack?: number
  /** Against these the art's own Mt bonus counts three times. */
  effective?: string[]
  effect?: string
}

/** A forge star: what it costs and the weapon's total bonuses at it. */
export interface Fe15Star {
  silver: number
  gold: number
  mt: number
  wt: number
  hit: number
  crit: number
}

/** An evolution: the weapon it becomes at a blacksmith, the cost and the stars it needs first. */
export interface Fe15Evolution {
  into: string
  silver: number
  gold: number
  stars: number
}

export interface Fe15Weapon extends ChapterWeapon {
  arts?: Fe15Art[]
  /** The first row of its forge list: its value in marks (a blacksmith trades it in for half, Serenes Forest). */
  markValue?: { silver: number; gold: number }
  forge?: Fe15Star[]
  evolve?: Fe15Evolution[]
}
