/** A Path of Radiance weapon, read from the game's own item table. */
export interface Fe9Weapon {
  id: string
  name: string
  category: 'Sword' | 'Lance' | 'Axe' | 'Bow' | 'Knife' | 'Fire' | 'Thunder' | 'Wind' | 'Light' | 'Staff'
  /** E to S, or Prf for a weapon only one character can use. */
  rank: string
  mt: number
  hit: number
  crit: number
  wt: number
  /** '1', '1-2', '3-10', or '1-Mag/2' for long-range staves. */
  range: string
  /** null = never breaks. */
  uses: number | null
  worth: number
  /** Weapon experience per use. */
  wex: number
  /** Stat changes while equipped. */
  stats: Partial<Record<'hp' | 'str' | 'mag' | 'skl' | 'spd' | 'lck' | 'def' | 'res', number>>
  /** What it's effective against: flying, armour, horseback, beast, dragon, laguz. */
  effective: string[]
  /** Its special rules, in the app's words. */
  rules: string[]
  /** The game's raw rule flags (for the generator's checks). */
  flags: string[]
  /** Set when a base's shop sells it: the chapters whose base has it in stock, by difficulty. */
  shop?: { normal: string; hard: string }
  /** Set when the forge can use it as a base weapon: the chapters whose base offers it, by difficulty. */
  forge?: { normal: string; hard: string }
}
