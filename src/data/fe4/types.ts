/** A Genealogy of the Holy War weapon or staff, read from the game's own item table. */
export interface Fe4Weapon {
  id: string
  name: string
  /** The item's id in the game's table (hex in the notes). */
  romId: number
  category: 'Sword' | 'Lance' | 'Axe' | 'Bow' | 'Fire' | 'Thunder' | 'Wind' | 'Light' | 'Dark' | 'Staff'
  /** C, B and A are the weapon rank needed; Holy is a holy weapon, only its holy blood's bearer can wield it. */
  rank: 'C' | 'B' | 'A' | 'Holy'
  /** Absent on staves; null for Hell, which sets HP to 1 instead. */
  mt?: number | null
  hit?: number
  wt?: number
  /** '1', '1-2', '3-10'. */
  range: string
  uses: number
  /** null: not for sale at any price (the game gives it 65535). */
  worth: number | null
  /** What it's effective against: it counts as a critical hit on them. */
  effective?: ('horseback' | 'flying' | 'armour')[]
  /** Skills it grants while it's equipped. */
  skills?: string[]
  /** Its special rules, in the app's words. */
  rules?: string[]
  /** Stat changes while equipped (Serenes Forest's; the table isn't found in the ROM). */
  stats?: Partial<Record<'str' | 'mag' | 'skl' | 'spd' | 'lck' | 'def' | 'mdf' | 'mov', number>>
  /** Staves only: the experience a cast earns, and what it does. */
  exp?: number
  effect?: string
}
