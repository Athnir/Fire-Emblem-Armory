/** Map ids (the map page's) by difficulty: the chapters whose base has an item, in the order they're played. */
export interface ChapterIds {
  normal: string[]
  hard: string[]
}

/** A Path of Radiance or Radiant Dawn weapon, read from the game's own item table. */
export interface TelliusWeapon {
  id: string
  name: string
  /** Crossbow, Dark and Card are Radiant Dawn's (a card is an item that attacks with magic); Strike is a laguz's own claws, breath
   * or beak (`ofClass`), or a weapon of the same type a unit carries (Radiant Dawn's Judge, Ashera's own). */
  category: 'Sword' | 'Lance' | 'Axe' | 'Bow' | 'Crossbow' | 'Knife' | 'Fire' | 'Thunder' | 'Wind' | 'Light' | 'Dark' | 'Staff' | 'Card' | 'Strike'
  /** A laguz's own attack, which comes with its class: every unit of the class has it. */
  ofClass?: true
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
  /** Hidden growth changes, in percent: a Fixed-mode level-up after a battle fought with it adds them (Path of Radiance). */
  growths?: Partial<Record<'hp' | 'str' | 'mag' | 'skl' | 'spd' | 'lck' | 'def' | 'res', number>>
  /** A weapon that isn't a tome but deals magic damage: its magic type (Path of Radiance's Flame Lance: fire), or 'neutral', magic
   * outside the triangle (Radiant Dawn's white dragons' Breath). */
  magic?: 'fire' | 'thunder' | 'wind' | 'light' | 'neutral'
  /** What it's effective against: flying, armour, horseback, beast, dragon, laguz. */
  effective: string[]
  /** Its special rules, in the app's words. */
  rules: string[]
  /** The game's raw rule flags (for the generator's checks). */
  flags: string[]
  /** Set when a base's shop sells it: the chapters whose base has it in stock, by difficulty. */
  shop?: { normal: string; hard: string }
  /** The same chapters as `shop`, as the map ids the spoiler block counts them by. */
  shopAt?: ChapterIds
  /** Radiant Dawn's bargains: one-off stock at a base, by difficulty. */
  bargain?: { normal: string; hard: string }
  bargainAt?: ChapterIds
  /** Set when the forge can use it as a base weapon: the chapters whose base offers it, by difficulty. */
  forge?: { normal: string; hard: string }
  forgeAt?: ChapterIds
  /** A foe's own weapon: nothing gives it to the player (Ashnard's Gurgurant, Rewarp). Listed, but marked as not available. */
  foeOnly?: true
  /** The chapters whose base conversation gives it (Jill's Brave Axe, Tarvos): weapons you can get that no shop sells. */
  baseAt?: string[]
  /** The chapters whose own script hands it over outside a base conversation, a chest or a village (Ragnell). */
  giftAt?: string[]
  /** The chapters whose placement files put it in the hands of a unit on your side (a recruit's own weapon, a starting kit). */
  kitAt?: string[]
}

/** Path of Radiance's weapons use the shared shape. */
export type Fe9Weapon = TelliusWeapon
