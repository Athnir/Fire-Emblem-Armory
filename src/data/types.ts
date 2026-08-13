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
}

/** Present only if the weapon is actually sold in a shop — undefined means it can't be bought at all. */
export interface WeaponPurchase {
  buy: number
  /** Shop sell-back price ("discount" price you get selling it back), where verified — Fates' sell
   * prices aren't a fixed fraction of buy, so this is left off rather than guessed when unconfirmed. */
  sell?: number
}

/**
 * Fates' own take on effective damage: the target's weakness triples (3x) this weapon's Might, but —
 * unlike earlier games — fighting a NON-effective target isn't penalty-free either: the weapon takes
 * a flat Might/Hit penalty. Confirmed via https://fireemblemwiki.org/wiki/Bonus_damage#Fates: -4
 * Might / -10 Hit is the norm, though this doesn't apply to Bow/Yumi (except the Hunter's Bow, which
 * IS penalized) — so it's tracked per-weapon rather than derived from category.
 */
export interface WeaponEffectiveness {
  /** What this weapon deals bonus damage to, e.g. "Armoured units", "Dragon units". */
  vs: string
  /** Might multiplier vs. an effective target — 3x for everything in Fates except the Ballista (2x). */
  multiplier: number
  /** Might/Hit penalty vs. a non-effective target. */
  nonEffectivePenalty: { mt: number; hit: number }
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
  /** True if obtained via My Castle (Treasure random pool or a Battle Rank milestone reward). */
  isMyCastle?: boolean
  /** Omitted entirely for weapons that can't be bought anywhere (personal, novelty, amiibo-scan, etc). */
  purchase?: WeaponPurchase
  /** Present only for weapons that deal bonus damage to some unit type. */
  effectiveness?: WeaponEffectiveness
  availability: WeaponAvailability
  iconId: string
}
