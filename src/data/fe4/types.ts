/** A Genealogy of the Holy War weapon or staff, read from the game's own item table. */
export interface Fe4Weapon {
  id: string
  name: string
  /** The item's id in the game's table (hex in the notes). */
  romId: number
  category: 'Sword' | 'Lance' | 'Axe' | 'Bow' | 'Fire' | 'Thunder' | 'Wind' | 'Light' | 'Dark' | 'Staff'
  /** C, B and A are the weapon rank needed; Holy is a holy weapon, only one with its Major holy blood can wield it. */
  rank: 'C' | 'B' | 'A' | 'Holy'
  /** Absent on staves; null for Hell, which sets HP to 1 instead. */
  mt?: number | null
  hit?: number
  wt?: number
  /** '1', '1-2', '3-10'. */
  range: string
  uses: number
  /** null: not for sale (the game gives it 65535, or it's a holy weapon, which no shop takes). */
  worth: number | null
  /** What repairing it costs per use spent: its price / uses ($87:E25D). */
  repair?: number
  /** What it's effective against: every hit on them is a critical. */
  effective?: ('horseback' | 'flying' | 'armour')[]
  /** Skills it grants while it's equipped. */
  skills?: string[]
  /** Its special rules, in the app's words. */
  rules?: string[]
  /** Stat changes while equipped (the holy weapons' records at $83:89E3; the Safeguard's and Barrier Blade's +7 in the code). */
  stats?: Partial<Record<'str' | 'mag' | 'skl' | 'spd' | 'lck' | 'def' | 'mdf' | 'mov', number>>
  /** Staves only: the experience a cast earns, and what it does. */
  exp?: number
  effect?: string
}
