import type { ItemSource } from '../logic/itemSources'
import type { GameItem } from './weapons/gameItems'

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
  /** Hit-avoidance bonus/penalty (chance to be missed entirely) — distinct from dodge below. */
  avoid: number
  /** Critical-evade bonus/penalty (chance to avoid being CRIT specifically) — Serenes' flavor text
   * calls this "Critical Evade", the Fire Emblem Wiki calls it "dodge"; same stat either way. */
  dodge: number
  /** e.g. "1", "1~2" */
  range: string
  /** Staff/Rod only — Fates kept limited durability for healing/utility staves even though every
   * other weapon type went infinite-use. Undefined for every other category. */
  uses?: number
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
 * unlike earlier games — fighting a NON-effective target isn't penalty-free either for most weapons:
 * they take a flat Might/Hit penalty. Confirmed per-weapon on Fire Emblem Wiki's own Fates stat rows
 * (not just the general https://fireemblemwiki.org/wiki/Bonus_damage#Fates writeup, which undersells
 * how many exceptions exist): Armorslayer/Wyrmslayer's own pages spell out "-4 attack, -10 hit
 * against non-X units" explicitly, while Falchion/Parallel Falchion/(Chrom's) Falchion's pages carry
 * no such clause at all — the "legendary" Falchion line is a genuine exception, not merely omitted
 * flavor text, and keeps its full stats against non-dragon targets. Also doesn't apply to Bow/Yumi
 * (except the Hunter's Bow, which IS penalized) — so this stays per-weapon, not derived from category.
 */
export interface WeaponEffectiveness {
  /** What this weapon deals bonus damage to, e.g. "Armoured units", "Dragon units". */
  vs: string
  /** Might multiplier vs. an effective target — 3x for everything in Fates except the Ballista (2x). */
  multiplier: number
  /** Might/Hit penalty vs. a non-effective target — undefined for the rare exceptions (the Falchion
   * line) that suffer no penalty at all and simply forgo the bonus. */
  nonEffectivePenalty?: { mt: number; hit: number }
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
  /**
   * Present only when one of the routes above was obtained through a one-off cross-faction
   * exception (a village reward, boss drop, etc. on the route OPPOSITE this weapon's category's own
   * faction) rather than that category's normal default — e.g. Dual Club (a Hoshido/Club item) also
   * drops on Conquest via a Chapter 10 village + Chapter 19 boss. Always a subset of `routes`, and
   * never 'Revelation' or 'all' — Revelation gets every category natively, so there's no "cross"
   * concept there. Drives the UI's separate "Cross" tab so these don't sit as a lone oddball inside
   * their native category's normal per-route listing.
   */
  crossRoutes?: Route[]
}

/** Categories that belong to Hoshido's weapon line — normally only obtainable on Birthright/Revelation. */
export const HOSHIDO_CATEGORIES: WeaponCategory[] = ['Katana', 'Naginata', 'Club', 'Shuriken', 'Yumi', 'Scroll', 'Rod']
/** Categories that belong to Nohr's weapon line — normally only obtainable on Conquest/Revelation. */
export const NOHR_CATEGORIES: WeaponCategory[] = ['Sword', 'Lance', 'Axe', 'Dagger', 'Bow', 'Tome', 'Staff']

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
  /** True for weapons that deal damage using the wielder's Magic against the target's Resistance,
   * instead of the default Strength-vs-Defence calculation. Always true for Tome/Scroll (that's the
   * whole category); also true for the handful of hybrid "elemental" weapons in physical categories
   * (Levin Sword, Leo's Iceblade, Bolt Naginata, Bolt Axe, Flame Shuriken, Shining Bow, Felicia's
   * Plate, Dragonstone/Dragonstone+) that Serenes' own description flags as "Magic weapon". */
  isMagic?: boolean
  /** False for weapons the Smithy won't forge: non-standard (dragonstones), sacred (Yato), or any unique the player can only ever hold one copy of. */
  forgeable: boolean
  /** False for weapons that explicitly cannot make a follow-up (double) attack even when the user's
   * Speed would normally earn one — undefined/omitted means the weapon follows the normal rule. */
  canFollowUp?: boolean
  /** True for the "Dual"/"Reverse"-type weapons that flip the weapon triangle (advantage becomes
   * disadvantage and vice versa) and double whichever triangle bonus/penalty applies. */
  reversesTriangle?: boolean
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
  /** Where the maps give it (chests, villages, enemy drops), read from the game's files at load. */
  mapSources?: ItemSource[]
  /** The game's own item record: stat changes, sell price, a staff's healing power. */
  game?: GameItem
  /** Read from the game's own description at load. */
  strikesTwice?: boolean
  /** Its Mt doubles in some fights (the condition is in its effect text): the Venge weapons and the like. */
  mightBoost?: true
  /** My Castle's one-time rewards for reaching a Battle Points / Visit Points total. */
  rankRewards?: { track: 'Battle Points' | 'Visit Points'; points: number }[]
  iconId: string
}
