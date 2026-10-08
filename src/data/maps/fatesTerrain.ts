import type { TerrainLetter } from './types'

/** Fates' movement classes, as the Fire Emblem Wiki groups them for terrain costs. */
export const MOVE_CLASSES = [
  'Infantry A', 'Infantry B', 'Infantry C', 'Infantry D', 'Armor',
  'Cavalry A', 'Cavalry B', 'Mages', 'Beasts', 'Fliers',
] as const
export type MoveClass = (typeof MOVE_CLASSES)[number]

export const MOVE_CLASS_EXAMPLES: Record<MoveClass, string> = {
  'Infantry A': 'Mercenary, Samurai, Apothecary, Spear Fighter, Archer, Lancer',
  'Infantry B': 'Nohr Prince(ss), Hero, Swordmaster, Sniper, Spear Master, Basara',
  'Infantry C': 'Fighter, Outlaw, Villager, Ninja, Oni Savage',
  'Infantry D': 'Berserker, Adventurer, Master Ninja, Oni Chieftain, Witch',
  Armor: 'Knight, General',
  'Cavalry A': 'Cavalier, Troubadour',
  'Cavalry B': 'Paladin, Great Knight, Bow Knight, Dark Knight, Strategist',
  Mages: 'Dark Mage, Sorcerer, Butler, Maid, Diviner, Onmyoji, Monk, Shrine Maiden',
  Beasts: 'Wolfskin, Wolfssegner, Kitsune, Nine-Tails',
  Fliers: 'Wyvern, Sky Knight, Falcon Knight, Kinshi Knight',
}

export interface TerrainInfo {
  name: string
  def: number
  avo: number
  /** Percent of max HP restored at the start of the turn. */
  heal: number
  /** null = can't enter. A string covers the wiki's split entries (e.g. Beasts on water: "4/3"). */
  move: Record<MoveClass, number | string | null>
  note?: string
}

const all = (cost: number | null, fliers: number | null = cost): Record<MoveClass, number | null> => ({
  'Infantry A': cost, 'Infantry B': cost, 'Infantry C': cost, 'Infantry D': cost, Armor: cost,
  'Cavalry A': cost, 'Cavalry B': cost, Mages: cost, Beasts: cost, Fliers: fliers,
})

/**
 * Source: https://fireemblemwiki.org/wiki/Terrain/Nintendo_3DS_games (Fates table). Fliers get no
 * Def/Avo from terrain, only its HP recovery.
 */
export const FATES_TERRAIN: Record<TerrainLetter, TerrainInfo> = {
  '.': { name: 'Plain / floor', def: 0, avo: 0, heal: 0, move: all(1) },
  S: { name: 'Stairs', def: 0, avo: 10, heal: 0, move: all(1) },
  p: {
    name: 'Pillar', def: 1, avo: 10, heal: 0,
    move: { ...all(2), 'Cavalry A': 3, 'Cavalry B': 3, Beasts: 1, Fliers: 1 },
  },
  f: {
    name: 'Woods', def: 1, avo: 10, heal: 0,
    move: { ...all(2), 'Cavalry A': 3, 'Cavalry B': 3, Beasts: 1, Fliers: 1 },
  },
  t: { name: 'Throne', def: 3, avo: 30, heal: 20, move: all(2, 1) },
  w: {
    name: 'Water', def: 0, avo: -10, heal: 0,
    move: {
      'Infantry A': null, 'Infantry B': 5, 'Infantry C': 5, 'Infantry D': 4, Armor: null,
      'Cavalry A': null, 'Cavalry B': null, Mages: null, Beasts: '4/3', Fliers: 1,
    },
  },
  c: { name: 'Chest', def: 0, avo: 0, heal: 0, move: all(null, 1), note: 'Opened with a Chest Key or Locktouch from an adjacent tile.' },
  d: { name: 'Door', def: 0, avo: 0, heal: 0, move: all(null), note: 'Opened with a Door Key or Locktouch; floor once open.' },
  '#': { name: 'Wall', def: 0, avo: 0, heal: 0, move: all(null) },
  b: { name: 'Bridge', def: 0, avo: 0, heal: 0, move: all(1) },
  r: { name: 'Rubble', def: 0, avo: 0, heal: 0, move: all(null, 1) },
  H: { name: 'Healing tile', def: 0, avo: 0, heal: 20, move: all(1) },
  x: { name: 'Chasm', def: 0, avo: 0, heal: 0, move: all(null, 1), note: 'Only fliers can cross.' },
  F: { name: 'Fort', def: 2, avo: 20, heal: 20, move: all(2, 1) },
  G: { name: 'Old gate', def: 2, avo: 20, heal: 0, move: all(2, 1) },
  B: { name: 'Building', def: 0, avo: 0, heal: 0, move: all(null, 1) },
  v: { name: 'Village', def: 1, avo: 5, heal: 0, move: all(1) },
  // Every mountain shares Fates' Mountain row (user-confirmed), snowy ones included.
  n: {
    name: 'Snow mountain', def: 2, avo: 20, heal: 0,
    move: {
      'Infantry A': 4, 'Infantry B': 4, 'Infantry C': 3, 'Infantry D': 3, Armor: null,
      'Cavalry A': null, 'Cavalry B': 6, Mages: 4, Beasts: 2, Fliers: 1,
    },
  },
  // The wiki's Fort row lists "Gate" among its members (Def +2, Avo +20, heals 20%).
  g: { name: 'Gate', def: 2, avo: 20, heal: 20, move: all(2, 1) },
  k: { name: 'Thick wood', def: 0, avo: 0, heal: 0, move: all(null, 1), note: 'Only fliers can enter.' },
  W: {
    name: 'Wasteland', def: 0, avo: -10, heal: 0,
    move: {
      'Infantry A': 4, 'Infantry B': 4, 'Infantry C': 3, 'Infantry D': 3, Armor: null,
      'Cavalry A': null, 'Cavalry B': 6, Mages: 4, Beasts: 2, Fliers: 1,
    },
  },
}

/** Pots are their own obstacle in Fates (the wiki's "Medicine" / "Poison" terrain): nothing can
 * enter the tile until the pot is broken, after which it's floor. */
export const POT_TERRAIN_NOTE = 'Impassable to every unit, fliers included, until broken; floor afterwards.'
