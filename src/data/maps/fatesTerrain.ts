import type { TerrainCode } from './terrainCodes'

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
  /** Resistance, where the game's terrain gives it (The Binding Blade). */
  res?: number
  avo: number
  /** Percent of max HP restored at the start of the turn. */
  heal: number
  /** By movement class (the game's own groups). null = can't enter. A string covers the wiki's split
   * entries (e.g. Beasts on water: "4/3"). */
  move: Record<string, number | string | null>
  note?: string
}

const all = (cost: number | null, fliers: number | null = cost): Record<MoveClass, number | null> => ({
  'Infantry A': cost, 'Infantry B': cost, 'Infantry C': cost, 'Infantry D': cost, Armor: cost,
  'Cavalry A': cost, 'Cavalry B': cost, Mages: cost, Beasts: cost, Fliers: fliers,
})

/**
 * Defaults per letter, matching the game's own terrain data (and the Fire Emblem Wiki's Fates
 * table). Maps built from the game files carry each letter's exact values for that map in
 * `terrainOverrides`. Fliers get no Def/Avo from terrain, only its HP recovery.
 */
export const FATES_TERRAIN: Partial<Record<TerrainCode, TerrainInfo>> = {
  ta: { name: 'Plain / floor', def: 0, avo: 0, heal: 0, move: all(1) },
  tc: { name: 'Stairs', def: 0, avo: 10, heal: 0, move: all(1) },
  bh: {
    name: 'Pillar', def: 1, avo: 10, heal: 0,
    move: { ...all(2), 'Cavalry A': 3, 'Cavalry B': 3, Beasts: 1, Fliers: 1 },
  },
  ba: {
    name: 'Woods', def: 1, avo: 10, heal: 0,
    move: { ...all(2), 'Cavalry A': 3, 'Cavalry B': 3, Beasts: 1, Fliers: 1 },
  },
  bc: { name: 'Throne', def: 3, avo: 30, heal: 20, move: all(2, 1) },
  tf: {
    name: 'Water', def: 0, avo: -10, heal: 0,
    move: {
      'Infantry A': null, 'Infantry B': 5, 'Infantry C': 5, 'Infantry D': 4, Armor: null,
      'Cavalry A': null, 'Cavalry B': null, Mages: null, Beasts: '4/3', Fliers: 1,
    },
  },
  oa: { name: 'Chest', def: 0, avo: 0, heal: 0, move: all(null, 1), note: 'Opened with a Chest Key or Locktouch from an adjacent tile.' },
  ob: { name: 'Door', def: 0, avo: 0, heal: 0, move: all(null), note: 'Opened with a Door Key or Locktouch; floor once open.' },
  wa: { name: 'Wall', def: 0, avo: 0, heal: 0, move: all(null) },
  tb: { name: 'Bridge', def: 0, avo: 0, heal: 0, move: all(1) },
  wj: { name: 'Rubble', def: 0, avo: 0, heal: 0, move: all(null, 1) },
  ha: { name: 'Healing tile', def: 0, avo: 0, heal: 20, move: all(1) },
  wd: { name: 'Chasm', def: 0, avo: 0, heal: 0, move: all(null, 1), note: 'Only fliers can cross.' },
  bb: { name: 'Fort', def: 2, avo: 20, heal: 20, move: all(2, 1) },
  be: { name: 'Old gate', def: 2, avo: 20, heal: 0, move: all(2, 1) },
  oe: { name: 'Building', def: 0, avo: 0, heal: 0, move: all(null, 1) },
  oc: { name: 'Village', def: 1, avo: 5, heal: 0, move: all(1) },
  // Every mountain shares Fates' Mountain row (user-confirmed), snowy ones included.
  bm: {
    name: 'Mountain', def: 2, avo: 20, heal: 0,
    move: {
      'Infantry A': 4, 'Infantry B': 4, 'Infantry C': 3, 'Infantry D': 3, Armor: null,
      'Cavalry A': null, 'Cavalry B': 6, Mages: 4, Beasts: 2, Fliers: 1,
    },
  },
  // Def +3, Avo +30, heals 20% (user-confirmed; the wiki's table lumps gates in with forts).
  bd: { name: 'Gate', def: 3, avo: 30, heal: 20, move: all(2, 1) },
  wh: { name: 'Thick wood', def: 0, avo: 0, heal: 0, move: all(null, 1), note: 'Only fliers can enter.' },
  we: { name: 'Lake / sea', def: 0, avo: 0, heal: 0, move: all(null, 1), note: 'Only fliers can cross.' },
  wg: { name: 'Partition', def: 0, avo: 0, heal: 0, move: all(null, 1), note: 'A low wall: only fliers can cross.' },
  wb: { name: 'Cliff / peak', def: 0, avo: 0, heal: 0, move: all(null, 1), note: 'Only fliers can cross.' },
  of: { name: 'Ballista', def: 0, avo: 0, heal: 0, move: all(null, 1), note: 'Manned by a unit standing on it.' },
  og: { name: 'Fire Orb', def: 0, avo: 0, heal: 0, move: all(null, 1), note: 'Manned by a unit standing on it.' },
  oh: { name: 'Launcher', def: 0, avo: 0, heal: 0, move: all(null, 1), note: 'Manned by a unit standing on it.' },
  dc: {
    name: 'Caltrops', def: -3, avo: -30, heal: -30,
    move: { ...all(2), 'Cavalry A': 3, 'Cavalry B': 3, Fliers: 1 },
  },
  wm: {
    name: 'Dark Waters', def: 1, avo: 10, heal: 0, move: all(null),
    note: "Your army can't enter it; some enemies move on it freely.",
  },
  bf: { name: 'Gate', def: 0, avo: 10, heal: 0, move: all(1) },
  bi: { name: 'Cushion', def: 2, avo: 20, heal: 20, move: all(2, 1) },
  od: { name: 'Village (closed)', def: 0, avo: 0, heal: 0, move: all(1) },
  wi: { name: 'Storm', def: 0, avo: 0, heal: 0, move: all(null, 2) },
  hc: { name: 'Chamber', def: 0, avo: 0, heal: 5, move: all(1) },
  sa: { name: 'Frozen lake', def: 0, avo: 0, heal: 0, move: all(1), note: 'Walkable until a Dragon Vein melts it into lake.' },
  td: {
    name: 'Desert', def: 0, avo: -10, heal: 0,
    move: { ...all(2), 'Cavalry A': 3, 'Cavalry B': 3, Mages: 1, Fliers: 1 },
  },
  da: { name: 'Acid Bog', def: 0, avo: 0, heal: -10, move: all(1), note: 'Takes 10% of max HP at the start of each turn.' },
  sb: { name: 'Darkness', def: 0, avo: 0, heal: 0, move: all(null), note: 'Impassable until the chapter lifts it.' },
  bj: { name: 'Ward', def: 0, avo: 40, heal: 20, move: all(1) },
  tj: {
    name: 'Shallow water', def: 0, avo: -10, heal: 0,
    move: { ...all(2), 'Cavalry A': 3, 'Cavalry B': 3, Fliers: 1 },
  },
  oi: { name: 'Sigil', def: 0, avo: 0, heal: 0, move: all(2, 1) },
  db: {
    name: 'Muck', def: -1, avo: -20, heal: -20,
    move: { ...all(2), 'Cavalry A': 3, 'Cavalry B': 3, Beasts: 1, Fliers: 1 },
  },
  bs: { name: 'Fissure', def: -1, avo: -20, heal: 0, move: all(1) },
  bg: { name: 'Ledge', def: 2, avo: 30, heal: 0, move: all(1) },
  // Radiant Dawn's letters (its maps carry their own table); never on a Fates map.
  te: {
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
