export type Route = 'Birthright' | 'Conquest' | 'Revelation' | 'all'
export type Faction = 'Hoshido' | 'Nohr' | 'Neutral'
export type WeaponRankLetter = 'E' | 'D' | 'C' | 'B' | 'A' | 'S'

/**
 * Hoshido/Nohr run parallel weapon lines with matching mechanics (Katana~Sword, Naginata~Lance,
 * Club~Axe, Shuriken~Dagger, Yumi~Bow, Scroll~Tome, Rod~Staff) — kept as distinct categories rather
 * than unified, since a Birthright/Revelation run only ever sees the Hoshido names and a
 * Conquest/Revelation run only ever sees the Nohr names.
 */
export type WeaponCategory =
  | 'Sword' | 'Katana'
  | 'Lance' | 'Naginata'
  | 'Axe' | 'Club'
  | 'Bow' | 'Yumi'
  | 'Tome' | 'Scroll'
  | 'Dagger' | 'Shuriken'
  | 'Staff' | 'Rod'
  | 'Other'

/** Smithy forging mineral per category — Rod/Staff/Other aren't forgeable, so they have none. */
export const FORGE_MINERALS: Partial<Record<WeaponCategory, string>> = {
  Katana: 'Pearl', Sword: 'Crystal',
  Naginata: 'Coral', Lance: 'Ruby',
  Club: 'Lapis', Axe: 'Sapphire',
  Shuriken: 'Quartz', Dagger: 'Onyx',
  Yumi: 'Jade', Bow: 'Emerald',
  Scroll: 'Amber', Tome: 'Topaz',
}

export interface WeaponStats {
  mt: number
  hit: number
  crit: number
  avoid: number
  /** e.g. "1", "1~2" */
  range: string
  /** Shop cost; 0 for weapons that are never sold. */
  worth: number
}

export interface WeaponAvailability {
  /** Which route(s) this weapon can actually be obtained on. */
  routes: Route[]
  /**
   * Where/how it's obtained (shop, chapter reward, boss drop, forge-only, amiibo, etc). Serenes
   * Forest's stat tables don't include per-chapter item locations, so this is filled in from
   * verified secondary sources where possible and left explicitly TBD otherwise — never guessed.
   */
  source: string
}

export interface Weapon {
  id: string
  name: string
  category: WeaponCategory
  faction: Faction
  rank: WeaponRankLetter
  stats: WeaponStats
  /** Additional effects / on-hit / on-equip text, from Serenes Forest's description column. */
  effects: string
  /** Whether this weapon can land critical hits — determines which Smithy forge bonus table applies. */
  canCrit: boolean
  /** False for weapons the Smithy won't forge: non-standard (dragonstones), sacred (Yato), or any unique the player can only ever hold one copy of. */
  forgeable: boolean
  isDlc?: boolean
  isAmiibo?: boolean
  isPersonal?: boolean
  /** Character this personal weapon is locked to, if isPersonal. */
  personalTo?: string
  availability: WeaponAvailability
  iconId: string
}
