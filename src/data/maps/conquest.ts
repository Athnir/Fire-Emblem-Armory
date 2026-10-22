import type { ChapterMap, Tile } from './types'
import type { TerrainCode } from './terrainCodes'
import { commons, pairs } from './units'
import { GAME_TERRAIN } from './gameTerrain'

const tilesBecome = (becomes: TerrainCode, tiles: Tile[]) => tiles.map((tile) => ({ tile, becomes }))

/*
 * Conquest chapters 6–11. Same method as the shared chapters: grids and every unit's starting tile
 * read off the Fire Emblem Wiki minimaps (Normal / Hard / Lunatic), unit totals checked against the
 * wiki's enemy tables, bosses found by the minimap's glow, coordinates converted to bottom-left (1, 1).
 */

export const CONQUEST_6: ChapterMap = {
  id: 'fe14c-6',
  route: 'Conquest',
  chapter: 6,
  title: 'Embrace the Dark',
  width: 20,
  height: 22,
  grid: GAME_TERRAIN['fe14c-6'].grid,
  terrainOverrides: GAME_TERRAIN['fe14c-6'].terrain,
  victory: 'Defeat 4 enemies.',
  defeat: 'Corrin dies, or your army is routed.',
  objectives: [],
  units: [
    { type: 'named', name: "Yukimura or Sakura", tile: [18, 10] },
    { type: 'boss', name: "Ryoma", tile: [13, 15] },
    { type: 'named', name: "Hinoka & Takumi", tile: [15, 3], paired: true },
    { type: 'named', name: "Yukimura or Sakura", tile: [17, 10] },
  ],
  starts: [[8, 21], [4, 14], [5, 13], [4, 8], [6, 8], [5, 7]],
  objects: [],
  changes: [
    {
      id: 'vein',
      trigger: 'dragonVein',
      // Wiki: column 6, row 6, three squares south of the rubble on the north-western bridge.
      tile: { default: [6, 17] },
      usableBy: 'Royals',
      effect: 'Uses fire to dry up the river.',
      patch: tilesBecome('ta', [
        [4, 22], [17, 22], [18, 22], [19, 22], [4, 21], [5, 21], [16, 21], [17, 21],
        [18, 21], [16, 20], [17, 20], [18, 20], [5, 19], [6, 19], [16, 19], [17, 19],
        [6, 18], [7, 18], [15, 18], [16, 18], [17, 18], [7, 17], [15, 17], [16, 17],
        [17, 17], [7, 16], [8, 16], [8, 15], [9, 15], [15, 15], [16, 15], [9, 14],
        [10, 14], [14, 14], [15, 14], [9, 13], [10, 13], [14, 13], [15, 13], [10, 12],
        [11, 12], [13, 12], [14, 12], [11, 11], [12, 11], [13, 11], [14, 11], [11, 10],
        [12, 10], [13, 10], [11, 9], [12, 9], [13, 9], [10, 8], [11, 8], [12, 8],
        [10, 7], [11, 7], [9, 4], [10, 4], [11, 4], [8, 3], [9, 3], [10, 3],
        [8, 2], [9, 2], [10, 2], [7, 1], [8, 1], [9, 1],
      ]),
    },
  ],
  notes: [
    'Xander, Camilla, Leo and Elise fight for you this chapter only (no EXP, no trading).',
    'Felicia (or Jakob) joins on turn 1.',
  ],
}

export const CONQUEST_7: ChapterMap = {
  id: 'fe14c-7',
  route: 'Conquest',
  chapter: 7,
  title: "A Dragon's Decree",
  width: 19,
  height: 20,
  grid: GAME_TERRAIN['fe14c-7'].grid,
  terrainOverrides: GAME_TERRAIN['fe14c-7'].terrain,
  victory: 'Rout the enemy.',
  defeat: 'Corrin dies, or your army is routed.',
  objectives: [],
  units: [
    { type: 'boss', name: "Faceless", tile: [3, 2] },
    ...pairs("Faceless", [[11, 19]]),
    ...commons("Faceless", [
        [6, 20], [5, 19], [2, 13], [1, 11], [5, 10], [5, 9], [2, 7], [9, 3],
        [4, 1], [18, 1],
      ]),
    ...pairs("Faceless", [[1, 7]], ['Lunatic']),
    ...commons("Faceless", [[1, 7]], ['Hard']),
    ...commons("Faceless", [[13, 19], [8, 1]], ['Hard', 'Lunatic']),
    ...commons("Faceless", [[16, 2]], ['Lunatic']),
  ],
  starts: [[14, 10], [15, 9]],
  objects: [],
  changes: [],
  notes: ['Silas and Elise join on turn 3; Arthur and Effie on turn 4.'],
}

export const CONQUEST_8: ChapterMap = {
  id: 'fe14c-8',
  route: 'Conquest',
  chapter: 8,
  title: 'Cold Reception',
  width: 25,
  height: 17,
  grid: GAME_TERRAIN['fe14c-8'].grid,
  terrainOverrides: GAME_TERRAIN['fe14c-8'].terrain,
  victory: 'Defeat Kilma.',
  defeat: 'Corrin dies, or your army is routed.',
  objectives: [],
  units: [
    { type: 'boss', name: "Kilma", tile: [3, 13], drops: ["Talisman"] },
    ...commons("Ice Tribe", [
        [17, 16], [9, 14], [2, 13], [7, 13], [19, 12], [15, 10], [9, 8], [10, 8],
        [7, 6], [3, 2], [3, 1],
      ]),
    ...commons("Ice Tribe", [[14, 10], [5, 1]], ['Hard', 'Lunatic']),
  ],
  starts: [[24, 3], [22, 2], [23, 2], [25, 2], [22, 1], [25, 1]],
  objects: [
    { type: 'village', tile: [13, 15], reward: 'end-of-chapter gold (see notes)' },
    { type: 'village', tile: [3, 7], reward: 'end-of-chapter gold (see notes)' },
    { type: 'village', tile: [21, 11], reward: 'end-of-chapter gold (see notes)' },
    { type: 'village', tile: [22, 3], reward: 'end-of-chapter gold (see notes)' },
    { type: 'village', tile: [5, 2], reward: 'end-of-chapter gold (see notes)' },
  ],
  changes: [
    {
      id: 'vein-east',
      trigger: 'dragonVein',
      // Wiki: column 17, row 14, five west and one north of the south-eastern village.
      tile: { default: [17, 4] },
      usableBy: 'Royals',
      effect: 'Melts the ice into a lake for 1 turn.',
      patch: tilesBecome('tf', [
        [14, 14], [12, 13], [13, 13], [14, 13], [15, 13], [11, 12], [12, 12], [13, 12],
        [14, 12], [15, 12], [16, 12], [10, 11], [11, 11], [12, 11], [13, 11], [14, 11],
        [15, 11], [16, 11], [9, 10], [10, 10], [11, 10], [12, 10], [13, 10], [14, 10],
        [15, 10], [16, 10], [8, 9], [9, 9], [10, 9], [11, 9], [15, 9], [16, 9],
        [17, 9], [8, 8], [9, 8], [10, 8], [11, 8], [15, 8], [16, 8], [17, 8],
        [10, 7], [11, 7], [15, 7], [16, 7], [17, 7], [10, 6], [11, 6], [12, 6],
        [13, 6], [14, 6], [15, 6], [16, 6], [17, 6], [9, 5], [10, 5], [11, 5],
        [12, 5], [13, 5], [14, 5], [15, 5], [16, 5], [17, 5], [9, 4], [10, 4],
        [11, 4], [12, 4], [13, 4], [14, 4], [15, 4], [16, 4], [9, 3], [10, 3],
        [11, 3], [12, 3], [13, 3], [14, 3], [15, 3], [10, 2], [11, 2], [12, 2],
        [13, 2], [14, 2], [15, 2], [11, 1], [12, 1], [13, 1], [14, 1],
      ]),
    },
    {
      id: 'vein-west',
      trigger: 'dragonVein',
      // Wiki: column 10, row 17, five east and one south of the south-western village.
      tile: { default: [10, 1] },
      usableBy: 'Royals',
      effect: 'Melts the ice into a lake for 1 turn.',
      patch: tilesBecome('tf', [
        [14, 14], [12, 13], [13, 13], [14, 13], [15, 13], [11, 12], [12, 12], [13, 12],
        [14, 12], [15, 12], [16, 12], [10, 11], [11, 11], [12, 11], [13, 11], [14, 11],
        [15, 11], [16, 11], [9, 10], [10, 10], [11, 10], [12, 10], [13, 10], [14, 10],
        [15, 10], [16, 10], [8, 9], [9, 9], [10, 9], [11, 9], [15, 9], [16, 9],
        [17, 9], [8, 8], [9, 8], [10, 8], [11, 8], [15, 8], [16, 8], [17, 8],
        [10, 7], [11, 7], [15, 7], [16, 7], [17, 7], [10, 6], [11, 6], [12, 6],
        [13, 6], [14, 6], [15, 6], [16, 6], [17, 6], [9, 5], [10, 5], [11, 5],
        [12, 5], [13, 5], [14, 5], [15, 5], [16, 5], [17, 5], [9, 4], [10, 4],
        [11, 4], [12, 4], [13, 4], [14, 4], [15, 4], [16, 4], [9, 3], [10, 3],
        [11, 3], [12, 3], [13, 3], [14, 3], [15, 3], [10, 2], [11, 2], [12, 2],
        [13, 2], [14, 2], [15, 2], [11, 1], [12, 1], [13, 1], [14, 1],
      ]),
    },
  ],
  notes: [
    'Villages pay out at the end: 1 visited = 1,000G, 2 = 5,000G, 3 or more = 10,000G.',
    'Enemy Lancers head for the villages; reaching one brings out Ice Tribe reinforcements.',
    'Odin and Niles join on turn 2.',
  ],
}

export const CONQUEST_9: ChapterMap = {
  id: 'fe14c-9',
  route: 'Conquest',
  chapter: 9,
  title: 'Another Trial',
  width: 30,
  height: 15,
  grid: GAME_TERRAIN['fe14c-9'].grid,
  terrainOverrides: GAME_TERRAIN['fe14c-9'].terrain,
  victory: 'Seize the throne.',
  defeat: 'Corrin dies, or your army is routed.',
  objectives: [{ type: 'seize', tiles: [[17, 8]], label: 'Seize point (throne)' }],
  units: [
    { type: 'boss', name: "Haitaka", tile: [17, 8], drops: ["Heart Seal"], capturable: true },
    ...pairs("Hoshidan", [[13, 8], [21, 8]]),
    ...commons("Hoshidan", [
        [22, 13], [19, 10], [8, 9], [17, 9], [8, 8], [16, 8], [8, 7], [21, 7],
        [30, 6], [21, 3],
      ]),
    ...pairs("Hoshidan", [[23, 5]], ['Lunatic']),
    ...commons("Hoshidan", [[9, 9], [9, 7], [22, 3]], ['Hard', 'Lunatic']),
    ...commons("Hoshidan", [[21, 13], [16, 9], [19, 9]], ['Lunatic']),
    ...commons("Hoshidan", [[9, 8]], ['Normal']),
    ...commons("Hoshidan", [[23, 5]], ['Normal', 'Hard']),
    { type: 'ally', name: 'Nyx', tile: [12, 3], note: 'Talk to her with Corrin to recruit her.' },
  ],
  starts: [[1, 7], [1, 6], [2, 6], [2, 5], [1, 4], [2, 4], [3, 4], [30, 4], [3, 3]],
  objects: [
    { type: 'chest', tile: [23, 12], contents: 'Rescue' },
    { type: 'chest', tile: [29, 8], contents: 'Brass Naginata' },
  ],
  changes: [
    {
      id: 'vein',
      trigger: 'dragonVein',
      // Wiki: column 29, row 3, five squares north of the Brass Naginata chest.
      tile: { default: [29, 13] },
      usableBy: 'Royals',
      effect: "Calls acid rain: every unit's HP drops to 1.",
    },
  ],
  notes: ['Azura joins on turn 1.'],
}

export const CONQUEST_10: ChapterMap = {
  id: 'fe14c-10',
  route: 'Conquest',
  chapter: 10,
  title: 'Unhappy Reunion',
  width: 26,
  height: 22,
  grid: GAME_TERRAIN['fe14c-10'].grid,
  terrainOverrides: GAME_TERRAIN['fe14c-10'].terrain,
  victory: 'Defend the green zone for 11 turns.',
  defeat: 'Corrin dies, your army is routed, or an enemy seizes any of the flashing green tiles.',
  objectives: [{ type: 'defend', tiles: [[10, 22], [11, 22], [12, 22], [13, 22]], label: 'Green zone (defend)' }],
  units: [
    { type: 'boss', name: "Takumi", tile: [2, 2], drops: ["Elixir"] },
    { type: 'named', name: 'Hinata', tile: [3, 8] },
    { type: 'named', name: 'Oboro', tile: [21, 8] },
    ...commons("Hoshidan", [
        [1, 15], [1, 14], [25, 12], [5, 11], [18, 11], [25, 11], [4, 10], [6, 10],
        [17, 10], [6, 4], [8, 4], [15, 4], [8, 3], [17, 3],
        [21, 2], [25, 2],
      ]),
    ...commons("Hoshidan", [[3, 11], [19, 10], [17, 4], [6, 3]], ['Hard', 'Lunatic']),
    ...commons("Hoshidan", [[20, 11], [25, 8], [26, 8], [12, 2]], ['Lunatic']),
  ],
  starts: [[10, 19], [11, 19], [12, 19], [13, 19], [10, 18], [11, 18], [12, 18], [13, 18], [11, 17], [12, 17]],
  objects: [
    { type: 'village', tile: [2, 21], reward: "10,000 Gold" },
    { type: 'village', tile: [15, 21], reward: "Master Seal" },
    { type: 'village', tile: [8, 13], reward: "Dual Club" },
    { type: 'village', tile: [21, 13], reward: "Dracoshield" },
  ],
  changes: [
    {
      id: 'vein',
      trigger: 'dragonVein',
      // Wiki: column 2, row 21, Takumi's own tile.
      tile: { default: [2, 2] },
      usableBy: 'Takumi, automatically at the start of turn 7 (if he is still on it)',
      effect: 'Lowers the water to make the sea passable.',
      patch: tilesBecome('ta', [
        [4, 21], [5, 21], [6, 21], [4, 19], [5, 19], [6, 19], [4, 18], [5, 18],
        [6, 18], [16, 18], [17, 18], [18, 18], [19, 18], [20, 18], [21, 18], [22, 18],
        [24, 18], [25, 18], [26, 18], [4, 17], [5, 17], [6, 17], [16, 17], [17, 17],
        [18, 17], [19, 17], [20, 17], [21, 17], [22, 17], [24, 17], [25, 17], [26, 17],
        [4, 16], [5, 16], [6, 16], [16, 16], [17, 16], [18, 16], [19, 16], [20, 16],
        [21, 16], [22, 16], [24, 16], [25, 16], [26, 16], [4, 15], [5, 15], [6, 15],
        [16, 15], [17, 15], [18, 15], [19, 15], [4, 14], [5, 14], [6, 14], [16, 14],
        [17, 14], [18, 14], [19, 14], [4, 13], [5, 13], [6, 13], [16, 13], [17, 13],
        [18, 13], [19, 13], [4, 12], [5, 12], [6, 12], [16, 12], [17, 12], [18, 12],
        [19, 12], [4, 9], [5, 9], [6, 9], [7, 9], [8, 9], [9, 9], [10, 9],
        [11, 9], [12, 9], [13, 9], [14, 9], [15, 9], [16, 9], [17, 9], [18, 9],
        [19, 9], [4, 8], [5, 8], [6, 8], [8, 8], [9, 8], [10, 8], [11, 8],
        [12, 8], [13, 8], [14, 8], [15, 8], [17, 8], [18, 8], [19, 8], [4, 7],
        [5, 7], [9, 7], [10, 7], [11, 7], [12, 7], [13, 7], [14, 7], [18, 7],
        [19, 7], [4, 6], [10, 6], [11, 6], [12, 6], [13, 6], [19, 6], [4, 5],
        [10, 5], [11, 5], [12, 5], [13, 5], [19, 5], [10, 4], [11, 4], [12, 4],
        [13, 4], [10, 3], [11, 3], [12, 3], [13, 3], [11, 2], [12, 2], [11, 1],
        [12, 1],
      ]),
    },
  ],
  notes: [
    'Camilla, Selena and Beruka join on turn 3.',
    'Reinforcements keep arriving (29 on Normal, 35 on Hard, 41 on Lunatic).',
  ],
}

export const CONQUEST_11: ChapterMap = {
  id: 'fe14c-11',
  route: 'Conquest',
  chapter: 11,
  title: 'Rainbow Sage',
  width: 30,
  height: 30,
  grid: GAME_TERRAIN['fe14c-11'].grid,
  terrainOverrides: GAME_TERRAIN['fe14c-11'].terrain,
  victory: 'Defeat Hinoka.',
  defeat: 'Corrin dies, or your army is routed.',
  objectives: [],
  units: [
    { type: 'named', name: "Kaze or Azama", tile: [5, 22] },
    { type: 'named', name: "Kaze or Azama", tile: [25, 21] },
    { type: 'boss', name: "Hinoka", tile: [15, 28] },
    ...pairs("Hoshidan", [[12, 18], [18, 18], [15, 17]]),
    ...commons("Hoshidan", [
        [15, 30], [14, 29], [16, 29], [6, 22], [5, 20], [7, 20], [27, 20], [24, 19],
        [25, 19], [8, 11], [7, 10], [9, 10], [9, 9], [20, 8], [19, 7], [21, 7],
        [19, 5],
      ]),
    ...pairs("Hoshidan", [[15, 29]], ['Lunatic']),
    ...commons("Hoshidan", [[6, 21], [25, 18], [7, 11], [20, 6]], ['Hard', 'Lunatic']),
    ...commons("Hoshidan", [[26, 20], [4, 17], [14, 17], [16, 17], [8, 10], [19, 6]], ['Lunatic']),
    ...commons("Hoshidan", [[15, 29]], ['Normal', 'Hard']),
  ],
  starts: [[8, 2], [9, 2], [10, 2], [11, 2], [12, 2], [9, 1], [10, 1], [11, 1], [12, 1], [13, 1], [14, 1]],
  objects: [
    { type: 'chest', tile: [2, 22], contents: 'Spirit Dust' },
    { type: 'chest', tile: [28, 21], contents: 'Enfeeble' },
  ],
  changes: [],
  notes: ['Kaze joins at the end of the chapter.', "The chests are in Kaze's room (Spirit Dust) and Azama's room (Enfeeble)."],
  unconfirmed: [
    'How the staircase tiles link the platforms.',
  ],
}

export const CONQUEST_6_TO_11: ChapterMap[] = [CONQUEST_6, CONQUEST_7, CONQUEST_8, CONQUEST_9, CONQUEST_10, CONQUEST_11]
