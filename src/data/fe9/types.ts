/** A Path of Radiance or Radiant Dawn weapon, read from the game's own item table. */
export interface TelliusWeapon {
  id: string
  name: string
  /** Crossbow and Dark are Radiant Dawn's. */
  category: 'Sword' | 'Lance' | 'Axe' | 'Bow' | 'Crossbow' | 'Knife' | 'Fire' | 'Thunder' | 'Wind' | 'Light' | 'Dark' | 'Staff'
  /** E to S (SS in Radiant Dawn), Prf for a weapon only one character can use, — for none needed. */
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
  /** Radiant Dawn's bargains: one-off stock at a base, by difficulty. */
  bargain?: { normal: string; hard: string }
  /** Set when the forge can use it as a base weapon: the chapters whose base offers it, by difficulty. */
  forge?: { normal: string; hard: string }
}

/** Path of Radiance's weapons use the shared shape. */
export type Fe9Weapon = TelliusWeapon
