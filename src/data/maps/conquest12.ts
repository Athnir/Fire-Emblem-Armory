import { GAME_TERRAIN } from './gameTerrain'
import type { ChapterMap, Difficulty, MapObject, MapUnit, PotEffect, Tile } from './types'

// Common foes: their tile, not their class.
const commons = (tiles: Tile[], difficulties?: Difficulty[]): MapUnit[] =>
  tiles.map((tile) => ({ type: 'enemy', name: 'Hoshidan', tile, difficulties }))

const heal = (percent: number): PotEffect => ({ type: 'heal', percent })
const damage = (percent: number): PotEffect => ({ type: 'damage', percent })
const status = (changes: Extract<PotEffect, { type: 'stats' }>['changes']): PotEffect => ({ type: 'stats', kind: 'status', changes })
const tonic = (changes: Extract<PotEffect, { type: 'stats' }>['changes']): PotEffect => ({ type: 'stats', kind: 'tonic', changes })
const debuff = (changes: Extract<PotEffect, { type: 'stats' }>['changes']): PotEffect => ({ type: 'stats', kind: 'debuff', changes })
const SILENCE: PotEffect = { type: 'silence' }
const FREEZE: PotEffect = { type: 'freeze' }
const HEX: PotEffect = { type: 'hex' }

// Every pot hits all units, either side, within 2 tiles (fandom chapter page).
const medicine = (tile: Tile, effect: PotEffect): MapObject => ({ type: 'pot', tile, pot: 'medicine', effect, radius: 2 })
const poison = (tile: Tile, effect: PotEffect): MapObject => ({ type: 'pot', tile, pot: 'poison', effect, radius: 2 })

/**
 * Pot effects: LfitLoyal's "Chapter 12 Conquest Medicine/Poison Pot Guide" ("Distribute Freely").
 * Medicine vs. poison: the cyan/purple dots on the wiki minimap, which agree with the guide's
 * colours at all 69 pots. Multi-stat medicine = tonic (+2 each, Luck +4); single-stat medicine =
 * status (+4); multi-stat poison = -5 each.
 */
const POTS: MapObject[] = [
  // Medicine (28)
  medicine([1, 28], heal(30)),
  medicine([9, 27], tonic({ def: 2, lck: 4 })),
  medicine([11, 27], status({ res: 4 })),
  medicine([14, 27], tonic({ mag: 2, lck: 4 })),
  medicine([3, 25], status({ mag: 4 })),
  medicine([19, 25], heal(30)),
  medicine([9, 24], heal(30)),
  medicine([11, 23], status({ skl: 4 })),
  medicine([7, 22], status({ skl: 4 })),
  medicine([13, 22], heal(30)),
  medicine([15, 22], heal(30)),
  medicine([9, 21], heal(30)),
  medicine([10, 21], status({ res: 4 })),
  medicine([17, 18], heal(30)),
  medicine([1, 14], tonic({ str: 2, skl: 2 })),
  medicine([10, 14], tonic({ def: 2, res: 2 })),
  medicine([10, 13], heal(30)),
  medicine([11, 13], tonic({ skl: 2, res: 2 })),
  medicine([9, 12], status({ res: 4 })),
  medicine([13, 11], tonic({ str: 2, def: 2 })),
  medicine([13, 10], heal(30)),
  medicine([19, 10], heal(30)),
  medicine([5, 9], heal(30)),
  medicine([4, 8], status({ def: 4 })),
  medicine([16, 7], status({ mag: 4 })),
  medicine([2, 4], status({ res: 4 })),
  medicine([9, 4], status({ def: 4 })),
  medicine([6, 1], status({ lck: 4 })),
  // Poison (41)
  poison([4, 28], damage(30)),
  poison([10, 28], debuff({ str: -5, def: -5 })),
  poison([16, 28], HEX),
  poison([9, 25], FREEZE),
  poison([15, 25], debuff({ str: -5, res: -5 })),
  poison([14, 24], debuff({ str: -5, lck: -5 })),
  poison([4, 22], HEX),
  poison([17, 22], damage(30)),
  poison([5, 21], damage(30)),
  poison([17, 21], damage(30)),
  poison([4, 20], SILENCE),
  poison([8, 20], damage(30)),
  poison([11, 20], damage(30)),
  poison([12, 20], HEX),
  poison([13, 20], HEX),
  poison([14, 20], FREEZE),
  poison([16, 20], debuff({ mag: -5, lck: -5 })),
  poison([5, 19], SILENCE),
  poison([6, 19], SILENCE),
  poison([7, 19], damage(30)),
  poison([9, 19], HEX),
  poison([10, 19], HEX),
  poison([15, 19], damage(30)),
  poison([2, 18], SILENCE),
  poison([9, 18], debuff({ str: -5, spd: -5 })),
  poison([18, 15], damage(30)),
  poison([4, 14], damage(30)),
  poison([16, 14], damage(30)),
  poison([19, 14], damage(30)),
  poison([18, 12], debuff({ mag: -5, lck: -5 })),
  poison([2, 11], HEX),
  poison([1, 10], damage(30)),
  poison([7, 9], FREEZE),
  poison([12, 9], FREEZE),
  poison([15, 8], damage(30)),
  poison([4, 6], SILENCE),
  poison([10, 5], SILENCE),
  poison([11, 5], debuff({ str: -5, lck: -5 })),
  poison([19, 5], FREEZE),
  poison([18, 2], debuff({ str: -5, spd: -5 })),
  poison([13, 1], HEX),
]

export const CONQUEST_12: ChapterMap = {
  id: 'fe14c-12',
  route: 'Conquest',
  chapter: 12,
  title: 'Bitter Intrigue',
  location: 'Palace Macarath',
  width: 19,
  height: 28,
  grid: GAME_TERRAIN['fe14c-12'].grid,
  terrainOverrides: GAME_TERRAIN['fe14c-12'].terrain,
  victory: 'Defeat Ryoma, or have Corrin escape.',
  defeat: 'Corrin dies, your army is routed, or 16 turns pass.',
  // The three tiles behind Ryoma (confirmed in-game by the user). The middle one starts with a pot on it.
  objectives: [{ type: 'escape', tiles: [[9, 28], [10, 28], [11, 28]], label: 'Corrin escape point' }],
  // Enemy starting tiles from the three difficulty minimaps (Hard and Lunatic only add units; no
  // one moves). Pairs show as two dots on one tile: Saizo & Kagero and the two Samurai pairs.
  // Totals match the wiki's 31 / 38 / 42 enemies.
  units: [
    {
      type: 'boss',
      name: 'Ryoma',
      tile: [10, 27],
      note: 'Never moves.',
      drops: ['Secret Book'],
    },
    {
      type: 'named',
      name: 'Saizo & Kagero',
      tile: [10, 16],
      paired: true,
      drops: ['Flame Shuriken (Saizo)'],
    },
    // Fandom: the Kodachi is dropped by "Hoshidan Samurai (1 SW of Ryoma)". His partner on the
    // other side carries one too, but doesn't drop it.
    { type: 'enemy', name: 'Hoshidan Samurai', tile: [9, 26], drops: ['Kodachi'] },
    { type: 'enemy', name: 'Hoshidan Samurai', tile: [11, 26] },
    { type: 'enemy', name: 'Hoshidan Samurai', tile: [2, 25], paired: true },
    { type: 'enemy', name: 'Hoshidan Samurai', tile: [17, 26], paired: true },
    ...commons([
      [7, 27], [2, 26], [5, 26], [6, 26], [14, 26], [15, 26], [18, 26],
      [8, 22], [10, 22], [14, 22], [7, 21], [12, 21], [9, 20], [10, 20],
      [5, 15], [11, 15], [15, 15], [9, 14], [10, 11], [5, 10], [6, 10], [18, 9],
    ]),
    ...commons([[11, 25], [10, 24], [1, 17], [2, 17], [18, 17], [19, 17], [9, 15]], ['Hard', 'Lunatic']),
    ...commons([[6, 22], [15, 21], [5, 16], [15, 16]], ['Lunatic']),
  ],
  // Corrin + 12. Same tiles on every difficulty.
  starts: [
    [5, 3], [8, 3], [9, 3], [11, 3], [12, 3], [15, 3],
    [5, 2], [7, 2], [9, 2], [10, 2], [11, 2], [13, 2], [15, 2],
  ],
  objects: [
    ...POTS,
    { type: 'chest', tile: [5, 24], contents: 'Armorslayer' },
    { type: 'chest', tile: [15, 24], contents: '5,000 Gold' },
    { type: 'door', tile: [2, 23] },
    { type: 'door', tile: [18, 23] },
  ],
  changes: [
    {
      id: 'vein',
      trigger: 'dragonVein',
      // Wiki: "Column 10, row 14" (Normal/Hard) and "column 10, row 11" (Lunatic), counting rows
      // from the top: adjacent to Saizo & Kagero, and two tiles north of them.
      tile: { default: [10, 15], Lunatic: [10, 18] },
      usableBy: 'Royals',
      effect: 'Earthquake: breaks every pot on the map at once, and each pot\'s effect still fires.',
      breaksAllPots: true,
    },
  ],
  notes: [
    "Elise can't be deployed (she falls ill).",
    'Reinforcements: Apothecaries from the southwest and southeast once one of your units reaches row 18 (Fire Emblem Wiki); the Fandom wiki gives end of turn 5 on Hard/Lunatic instead.',
    'Two Door Keys are dropped by the two Apothecaries carrying Iron Yumi.',
  ],
}
