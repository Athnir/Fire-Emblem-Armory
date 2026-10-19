import type { ChapterMap, TerrainLetter, Tile } from './types'
import { commons, pairs } from './units'
import { GAME_TERRAIN } from './gameTerrain'

const tilesBecome = (becomes: TerrainLetter, tiles: Tile[]) => tiles.map((tile) => ({ tile, becomes }))

/*
 * Conquest 13 to Endgame, generated from data-raw/fates/conquest (the Fire Emblem Wiki minimaps and
 * chapter pages). A first pass: each grid still needs a check by eye against its minimap, and the
 * `unconfirmed` lists say what isn't settled yet. Terrain and Dragon Vein tiles come from the game's own
 * files (see gameTerrain.ts).
 */

export const CONQUEST_13: ChapterMap = {
  id: 'fe14c-13',
  route: 'Conquest',
  chapter: 13,
  title: "Uprising",
  width: 21,
  height: 19,
  grid: GAME_TERRAIN['fe14c-13'].grid,
  terrainOverrides: GAME_TERRAIN['fe14c-13'].terrain,
  victory: "Rout the enemy.",
  defeat: "Corrin dies, or your army is routed.",
  objectives: [],
  units: [
    { type: 'boss', name: "Scarlet", tile: [2, 1] },
    { type: 'named', name: "Takumi", tile: [18, 10] },
    { type: 'named', name: "Orochi", tile: [4, 10] },
    { type: 'named', name: "Reina", tile: [10, 7] },
    ...pairs("Chevois", [[13, 1], [15, 1]]),
    ...commons("Chevois", [
        [1, 19], [1, 18], [21, 18], [1, 17], [21, 17], [3, 12], [4, 12], [17, 12],
        [18, 12], [8, 7], [11, 7], [12, 7], [1, 2], [3, 2],
    ]),
    ...pairs("Chevois", [[3, 1], [8, 1], [10, 1]], ['Lunatic']),
    ...commons("Chevois", [[21, 19], [5, 12], [19, 12], [9, 7]], ['Hard', 'Lunatic']),
    ...commons("Chevois", [[4, 11], [18, 11], [9, 8], [11, 8]], ['Lunatic']),
  ],
  starts: [[10, 19], [12, 19], [13, 19], [10, 18], [12, 18], [13, 18], [14, 18], [11, 17], [12, 17], [14, 17]],
  corrinStart: [12, 18],
  objects: [
    { type: 'village', tile: [9, 9], reward: "5,000 Gold" },
    { type: 'village', tile: [16, 7], reward: "Master Seal" },
    { type: 'village', tile: [18, 2], reward: "Blessed Lance" },
    { type: 'village', tile: [12, 4], reward: "Arms Scroll" },
  ],
  changes: [],
  notes: [
    "Benny and Charlotte join on turn 3.",
    "Reinforcements: 5 on Normal, 7 on Hard, 9 on Lunatic.",
  ],
}

export const CONQUEST_14: ChapterMap = {
  id: 'fe14c-14',
  route: 'Conquest',
  chapter: 14,
  title: "Voice of Paradise",
  width: 25,
  height: 20,
  grid: GAME_TERRAIN['fe14c-14'].grid,
  terrainOverrides: GAME_TERRAIN['fe14c-14'].terrain,
  victory: "Defeat Kumagera.",
  defeat: "Corrin dies, or your army is routed.",
  objectives: [],
  units: [
    { type: 'boss', name: "Kumagera", tile: [23, 15], capturable: true },
    ...pairs("Hoshidan", [[14, 8]]),
    ...commons("Hoshidan", [
        [12, 19], [13, 19], [14, 19], [12, 14], [14, 14], [23, 14], [12, 12], [11, 11],
        [12, 11], [17, 11], [25, 9], [18, 8], [20, 8], [21, 8], [25, 7], [14, 5],
        [15, 5], [21, 5], [22, 5], [19, 4], [21, 4],
    ]),
    ...commons("Hoshidan", [[21, 9]], ['Hard']),
    ...commons("Hoshidan", [[13, 18], [25, 15], [13, 14], [17, 10], [15, 4]], ['Hard', 'Lunatic']),
    ...commons("Hoshidan", [[19, 8], [21, 7], [25, 5], [18, 4], [19, 2]], ['Lunatic']),
    ...commons("Hoshidan", [[23, 16]], ['Normal', 'Lunatic']),
    { type: 'ally', name: "Keaton", tile: [13, 1], note: "Talk to him with Corrin to recruit him." },
  ],
  starts: [[4, 10], [3, 9], [4, 9], [5, 9], [3, 8], [4, 8], [5, 8], [5, 7], [5, 6], [6, 6], [4, 5], [5, 5]],
  objects: [
    { type: 'chest', tile: [16, 20], contents: "Seraph Robe" },
    { type: 'chest', tile: [20, 9], contents: "10,000 Gold" },
  ],
  changes: [],
  notes: [
    "Leo joins on turn 1.",
    "Reinforcements: 2 on Normal, 4 on Hard, 6 on Lunatic.",
    "Corrin's Yato becomes the Grim Yato at the end of the chapter.",
  ],
}

export const CONQUEST_15: ChapterMap = {
  id: 'fe14c-15',
  route: 'Conquest',
  chapter: 15,
  title: "The Black Pillar",
  width: 30,
  height: 30,
  grid: GAME_TERRAIN['fe14c-15'].grid,
  victory: "Defeat the boss (a Hero), or have every unit escape, within 20 turns.",
  defeat: "Corrin dies, your army is routed, or 20 turns pass.",
  objectives: [{ type: 'escape', tiles: [[30, 26], [30, 25], [30, 24], [30, 20], [30, 19], [30, 18], [30, 17]], label: 'Escape point' }],
  units: [
    { type: 'boss', name: "Hero", tile: [3, 9], drops: ["Speedwing"], note: "Stands on an old gate." },
    ...commons("Invader", [
        [21, 29], [15, 28], [21, 28], [15, 27], [25, 27], [26, 27], [25, 23], [19, 21],
        [20, 21], [19, 20], [25, 20], [23, 17], [7, 15], [11, 12], [11, 11], [15, 10],
        [8, 8], [20, 8], [8, 7], [20, 7], [15, 5], [11, 4], [14, 4], [5, 3],
    ]),
    ...commons("Invader", [[11, 10], [1, 9], [8, 9], [1, 8]], ['Lunatic']),
  ],
  starts: [[5, 26], [6, 25], [9, 25]],
  objects: [],
  changes: [
    {
      id: 'vein',
      trigger: 'dragonVein',
      // Wiki: column 8, row 7, one south and one west of Gunter's starting tile.
      tile: { default: [8, 24] },
      usableBy: "Royals",
      effect: "Splits each allied unit into two bodies: the Replicas appear in the area around (28, 6).",
    },
  ],
  notes: [
    "The cliff splits the map in two; the halves aren't connected.",
    "Gunter joins on turn 1.",
    "Jakob (male Corrin) or Felicia (female Corrin) joins at the end.",
  ],
  terrainOverrides: GAME_TERRAIN['fe14c-15'].terrain,
}

export const CONQUEST_16: ChapterMap = {
  id: 'fe14c-16',
  route: 'Conquest',
  chapter: 16,
  title: "Invasion",
  width: 30,
  height: 22,
  grid: GAME_TERRAIN['fe14c-16'].grid,
  terrainOverrides: GAME_TERRAIN['fe14c-16'].terrain,
  victory: "Defeat Shura.",
  defeat: "Corrin dies, or your army is routed.",
  objectives: [],
  units: [
    { type: 'enemy', name: "Hero", tile: [25, 12], drops: ["Heart Seal"], difficulties: ['Normal', 'Hard'] },
    { type: 'enemy', name: "Hero", tile: [25, 12], paired: true, drops: ["Heart Seal"], difficulties: ['Lunatic'] },
    ...pairs("Ruffian", [[24, 13], [11, 12]]),
    ...commons("Ruffian", [
        [8, 18], [10, 18], [21, 18], [8, 17], [7, 15], [23, 15], [11, 14], [25, 14],
        [3, 13], [4, 12], [23, 10], [24, 10], [8, 9], [27, 8], [8, 7], [10, 7],
        [22, 7], [26, 7], [10, 6], [21, 6],
    ]),
    ...commons("Ruffian", [
        [10, 17], [22, 17], [2, 14], [23, 14], [11, 10], [28, 10], [29, 10], [23, 9],
        [8, 6],
    ], ['Hard', 'Lunatic']),
    ...commons("Ruffian", [[24, 17], [6, 16], [4, 15], [2, 12], [6, 8], [23, 6]], ['Lunatic']),
    { type: 'ally', name: "Nohrian Lancer", tile: [23, 18] },
    { type: 'ally', name: "Nohrian Lancer", tile: [3, 16] },
    { type: 'ally', name: "Nohrian Lancer", tile: [29, 13] },
    { type: 'ally', name: "Nohrian Lancer", tile: [7, 6] },
  ],
  starts: [[15, 14], [14, 13], [15, 13], [16, 13], [17, 13], [15, 12], [16, 12], [17, 12], [14, 11], [15, 11], [16, 11], [17, 11], [15, 10]],
  objects: [],
  changes: [],
  notes: [
    "Xander joins on turn 1.",
    "Shura is whichever of the four Nohrian Lancers you speak to last.",
    "Gold at the end: 10,000 minus 300 per turn taken.",
    "Spare Shura and he joins at the end; otherwise you get Boots.",
  ],
}

export const CONQUEST_17: ChapterMap = {
  id: 'fe14c-17',
  route: 'Conquest',
  chapter: 17,
  title: "Den of Betrayal",
  width: 25,
  height: 22,
  grid: GAME_TERRAIN['fe14c-17'].grid,
  terrainOverrides: GAME_TERRAIN['fe14c-17'].terrain,
  victory: "Defeat Kotaro.",
  defeat: "Corrin dies, or your army is routed.",
  objectives: [],
  units: [
    { type: 'boss', name: "Kotaro", tile: [21, 20], note: "Stands on a throne." },
    ...commons("Mokushujin", [
        [11, 19], [14, 19], [10, 18], [15, 18], [19, 18], [23, 18], [14, 17], [16, 17],
        [4, 15], [10, 15], [12, 15], [3, 14], [24, 14], [8, 13], [16, 13], [23, 13],
        [24, 12], [23, 11], [12, 10], [14, 10], [13, 9], [15, 9], [20, 9], [18, 8],
        [19, 8], [23, 8], [20, 5], [17, 4], [21, 4], [17, 3], [20, 3],
    ]),
    ...commons("Mokushujin", [[3, 16], [15, 16], [11, 14], [17, 13], [13, 11], [20, 6], [25, 5]], ['Hard', 'Lunatic']),
    ...commons("Mokushujin", [[19, 19], [18, 15]], ['Lunatic']),
    { type: 'ally', name: "Saizo", tile: [7, 2] },
  ],
  starts: [[1, 4], [2, 4], [4, 4], [2, 3], [4, 3], [5, 3], [1, 2], [3, 2], [4, 2], [5, 2], [1, 1], [2, 1], [3, 1], [4, 1]],
  objects: [
    { type: 'chest', tile: [7, 21], contents: "5,000 Gold" },
    { type: 'chest', tile: [24, 2], contents: "Master Seal" },
  ],
  changes: [
    {
      id: 'vein-1',
      trigger: 'dragonVein',
      // Wiki: column 7, row 20, next to Saizo's starting tile.
      tile: { default: [7, 3] },
      usableBy: "Royals",
      effect: "Opens or blocks paths in the cavern.",
      patch: [{ tile: [10, 5], becomes: '.' }],
    },
    {
      id: 'vein-2',
      trigger: 'dragonVein',
      // Wiki: column 5, row 11.
      tile: { default: [5, 12] },
      usableBy: "Royals",
      effect: "Opens or blocks paths in the cavern.",
      patch: [{ tile: [3, 15], becomes: '#' }, { tile: [7, 10], becomes: '#' }],
    },
    {
      id: 'vein-3',
      trigger: 'dragonVein',
      // Wiki: column 8, row 9.
      tile: { default: [8, 14] },
      usableBy: "Royals",
      effect: "Opens or blocks paths in the cavern.",
      patch: [{ tile: [7, 16], becomes: '#' }, { tile: [12, 14], becomes: '.' }, { tile: [9, 13], becomes: '.' }],
    },
    {
      id: 'vein-4',
      trigger: 'dragonVein',
      // Wiki: column 9, row 4.
      tile: { default: [9, 19] },
      usableBy: "Royals",
      effect: "Opens or blocks paths in the cavern.",
      patch: [{ tile: [11, 18], becomes: '#' }],
    },
    {
      id: 'vein-5',
      trigger: 'dragonVein',
      // Wiki: column 10, row 7.
      tile: { default: [10, 16] },
      usableBy: "Royals",
      effect: "Opens or blocks paths in the cavern.",
    },
    {
      id: 'vein-6',
      trigger: 'dragonVein',
      // Wiki: column 17, row 6.
      tile: { default: [17, 17] },
      usableBy: "Royals",
      effect: "Opens or blocks paths in the cavern.",
      patch: [{ tile: [15, 15], becomes: '#' }, { tile: [17, 15], becomes: '.' }, { tile: [20, 14], becomes: '#' }],
    },
    {
      id: 'vein-7',
      trigger: 'dragonVein',
      // Wiki: column 22, row 19.
      tile: { default: [22, 4] },
      usableBy: "Royals",
      effect: "Opens or blocks paths in the cavern.",
      patch: [{ tile: [23, 12], becomes: '.' }, { tile: [23, 9], becomes: '#' }, { tile: [20, 4], becomes: '.' }],
    },
    {
      id: 'vein-8',
      trigger: 'dragonVein',
      // Wiki: column 14, row 17.
      tile: { default: [14, 6] },
      usableBy: "Royals",
      effect: "Opens or blocks paths in the cavern.",
      patch: [{ tile: [13, 6], becomes: '.' }, { tile: [17, 6], becomes: '#' }],
    },
    {
      id: 'vein-9',
      trigger: 'dragonVein',
      // Wiki: column 15, row 13.
      tile: { default: [15, 10] },
      usableBy: "Royals",
      effect: "Opens or blocks paths in the cavern.",
      patch: [{ tile: [14, 11], becomes: '.' }, { tile: [11, 9], becomes: '#' }, { tile: [17, 8], becomes: '#' }],
    },
  ],
  notes: [
    "Reinforcements: 12 on Normal, 16 on Hard, 20 on Lunatic.",
    "You get a Speedwing at the end if Saizo survives.",
  ],
}

export const CONQUEST_18: ChapterMap = {
  id: 'fe14c-18',
  route: 'Conquest',
  chapter: 18,
  title: "Black & White",
  width: 25,
  height: 24,
  grid: GAME_TERRAIN['fe14c-18'].grid,
  terrainOverrides: GAME_TERRAIN['fe14c-18'].terrain,
  victory: "Defeat Zola and the two boss Generals within 20 turns.",
  defeat: "Corrin dies, your army is routed, or 20 turns pass.",
  objectives: [],
  units: [
    { type: 'boss', name: "Generals", tile: [13, 5], paired: true, note: "Defeating both opens the door just north of them." },
    { type: 'boss', name: "Zola", tile: [13, 24], drops: ["10,000 Gold"], note: "Stands on a throne." },
    ...pairs("Nohrian", [[14, 23], [12, 22]]),
    ...commons("Nohrian", [
        [17, 22], [14, 20], [17, 19], [9, 18], [10, 18], [10, 17], [12, 15], [11, 11],
        [13, 11], [15, 11], [8, 10], [8, 9], [4, 7], [18, 6], [17, 5], [18, 5],
        [21, 5], [25, 4], [18, 1],
    ]),
    ...commons("Nohrian", [[5, 24], [21, 23], [15, 20], [9, 19], [3, 7], [25, 5], [18, 4], [17, 1]], ['Hard', 'Lunatic']),
    ...commons("Nohrian", [[12, 18], [13, 18], [14, 18], [9, 11], [21, 2]], ['Lunatic']),
    ...commons("Nohrian", [[25, 3]], ['Normal']),
    { type: 'ally', name: "Ryoma, Hinoka, Takumi or Sakura", tile: [12, 9] },
    { type: 'ally', name: "Ryoma, Hinoka, Takumi or Sakura", tile: [14, 9] },
    { type: 'ally', name: "Ryoma, Hinoka, Takumi or Sakura", tile: [12, 7] },
    { type: 'ally', name: "Ryoma, Hinoka, Takumi or Sakura", tile: [14, 7] },
  ],
  starts: [[1, 19], [2, 19], [24, 19], [25, 19], [1, 18], [2, 18], [24, 18], [25, 18], [1, 17], [2, 17], [24, 17], [25, 17], [1, 16], [25, 16]],
  objects: [
    { type: 'chest', tile: [4, 23], contents: "Master Seal" },
    { type: 'chest', tile: [22, 23], contents: "Energy Drop" },
    { type: 'door', tile: [6, 23] },
    { type: 'door', tile: [20, 23] },
    { type: 'door', tile: [13, 6] },
  ],
  changes: [],
  notes: [
    "Reinforcements: 6 on Normal, 8 on Hard, 8 on Lunatic.",
  ],
}

export const CONQUEST_19: ChapterMap = {
  id: 'fe14c-19',
  route: 'Conquest',
  chapter: 19,
  title: "Kitsune Lair",
  width: 25,
  height: 20,
  grid: GAME_TERRAIN['fe14c-19'].grid,
  victory: "Rout the enemy.",
  defeat: "Corrin dies, or your army is routed.",
  objectives: [],
  units: [
    { type: 'boss', name: "Kaden", tile: [3, 19], drops: ["Beaststone+"] },
    ...commons("Tribalist", [
        [3, 20], [23, 20], [23, 19], [24, 19], [2, 18], [8, 15], [16, 15], [18, 15],
        [20, 15], [7, 14], [10, 14], [17, 14], [19, 14], [7, 13], [10, 13], [9, 12],
        [2, 7], [9, 7], [19, 7], [3, 6], [8, 6], [9, 6], [2, 5], [7, 5],
        [8, 5],
    ]),
    ...pairs("Tribalist", [[25, 19], [7, 7]], ['Lunatic']),
    ...commons("Tribalist", [[11, 13], [8, 12]], ['Hard', 'Lunatic']),
    ...commons("Tribalist", [[1, 19], [17, 16], [19, 16], [9, 15], [8, 13]], ['Lunatic']),
  ],
  starts: [[22, 6], [21, 5], [22, 5], [23, 5], [20, 4], [21, 4], [22, 4], [23, 4], [24, 4], [21, 3], [22, 3], [23, 3], [22, 2]],
  objects: [],
  changes: [],
  notes: [
    "A bridge can appear over the stream at (14\u201316, 13).",
  ],
  terrainOverrides: GAME_TERRAIN['fe14c-19'].terrain,
}

export const CONQUEST_20: ChapterMap = {
  id: 'fe14c-20',
  route: 'Conquest',
  chapter: 20,
  title: "Winds of Change",
  width: 25,
  height: 29,
  grid: GAME_TERRAIN['fe14c-20'].grid,
  victory: "Seize the throne.",
  defeat: "Corrin dies, or your army is routed.",
  objectives: [
    { type: 'seize', tiles: [[21, 27]], label: "Seize point (throne)" },
  ],
  units: [
    { type: 'boss', name: "Fuga", tile: [21, 27], drops: ["Secret Book"], note: "Stands on the throne (the seize point)." },
    { type: 'named', name: "Hayato", tile: [9, 21], note: "Stands on a pillar." },
    { type: 'enemy', name: "Spear Master", tile: [24, 14], drops: ["Chest Key"] },
    ...pairs("Tribalist", [[12, 25]]),
    ...commons("Tribalist", [
        [6, 29], [8, 29], [2, 27], [14, 26], [1, 25], [3, 25], [17, 25], [13, 24],
        [21, 24], [16, 20], [15, 19], [24, 17], [2, 16], [10, 16], [3, 15], [9, 15],
        [10, 15], [23, 15], [3, 14], [23, 7], [24, 6], [25, 6], [1, 2], [2, 2],
        [3, 2],
    ]),
    ...pairs("Tribalist", [[15, 25]], ['Hard', 'Lunatic']),
    ...commons("Tribalist", [[7, 28], [1, 26], [3, 26], [21, 25], [25, 16]], ['Hard', 'Lunatic']),
    ...commons("Tribalist", [[7, 29], [8, 26], [10, 26], [7, 25], [9, 25], [14, 24], [15, 20], [22, 17]], ['Lunatic']),
  ],
  starts: [[13, 8], [14, 8], [15, 8], [16, 8], [13, 7], [14, 7], [16, 7], [13, 6], [15, 6], [16, 6], [13, 5], [14, 5], [15, 5], [16, 5]],
  objects: [
    { type: 'chest', tile: [1, 27], contents: "10,000 Gold" },
    { type: 'chest', tile: [2, 14], contents: "Rescue" },
    { type: 'chest', tile: [25, 20], contents: "Dragonstone+" },
  ],
  changes: [
    {
      id: 'vein-1',
      trigger: 'dragonVein',
      // Wiki: column 18, row 27.
      tile: { default: [18, 3] },
      usableBy: "Royals",
      effect: "Calls a wind that moves enemies (once per turn).",
    },
    {
      id: 'vein-2',
      trigger: 'dragonVein',
      // Wiki: column 23, row 22.
      tile: { default: [23, 8] },
      usableBy: "Royals",
      effect: "Calls a wind that moves enemies (once per turn).",
    },
    {
      id: 'vein-3',
      trigger: 'dragonVein',
      // Wiki: column 14, row 19.
      tile: { default: [14, 11] },
      usableBy: "Royals",
      effect: "Calls a wind that moves enemies (once per turn).",
    },
    {
      id: 'vein-4',
      trigger: 'dragonVein',
      // Wiki: column 16, row 15.
      tile: { default: [16, 15] },
      usableBy: "Royals",
      effect: "Calls a wind that moves enemies (once per turn).",
    },
    {
      id: 'vein-5',
      trigger: 'dragonVein',
      // Wiki: column 25, row 17.
      tile: { default: [25, 13] },
      usableBy: "Royals",
      effect: "Calls a wind that moves enemies (once per turn).",
    },
    {
      id: 'vein-6',
      trigger: 'dragonVein',
      // Wiki: column 23, row 10.
      tile: { default: [23, 20] },
      usableBy: "Royals",
      effect: "Calls a wind that moves enemies (once per turn).",
    },
    {
      id: 'vein-7',
      trigger: 'dragonVein',
      // Wiki: column 17, row 11.
      tile: { default: [17, 19] },
      usableBy: "Royals",
      effect: "Calls a wind that moves enemies (once per turn).",
    },
    {
      id: 'vein-8',
      trigger: 'dragonVein',
      // Wiki: column 11, row 8.
      tile: { default: [11, 22] },
      usableBy: "Royals",
      effect: "Calls a wind that moves enemies (once per turn).",
    },
    {
      id: 'vein-9',
      trigger: 'dragonVein',
      // Wiki: column 18, row 7.
      tile: { default: [18, 23] },
      usableBy: "Royals",
      effect: "Calls a wind that moves enemies (once per turn).",
    },
    {
      id: 'vein-10',
      trigger: 'dragonVein',
      // Wiki: column 5, row 7.
      tile: { default: [5, 23] },
      usableBy: "Royals",
      effect: "Calls a wind that moves enemies (once per turn).",
    },
    {
      id: 'vein-11',
      trigger: 'dragonVein',
      // Wiki: column 4, row 15.
      tile: { default: [4, 15] },
      usableBy: "Royals",
      effect: "Calls a wind that moves enemies (once per turn).",
    },
    {
      id: 'vein-12',
      trigger: 'dragonVein',
      // Wiki: column 8, row 16.
      tile: { default: [8, 14] },
      usableBy: "Royals",
      effect: "Calls a wind that moves enemies (once per turn).",
    },
    {
      id: 'vein-13',
      trigger: 'dragonVein',
      // Wiki: column 2, row 22.
      tile: { default: [2, 8] },
      usableBy: "Royals",
      effect: "Calls a wind that moves enemies (once per turn).",
    },
    {
      id: 'vein-14',
      trigger: 'dragonVein',
      // Wiki: column 9, row 23.
      tile: { default: [9, 7] },
      usableBy: "Royals",
      effect: "Calls a wind that moves enemies (once per turn).",
    },
  ],
  notes: [
    "A wind moves your units at the end of every enemy phase.",
    "Reinforcements: 5 on Normal, 13 on Hard, 21 on Lunatic.",
  ],
  terrainOverrides: GAME_TERRAIN['fe14c-20'].terrain,
}

export const CONQUEST_21: ChapterMap = {
  id: 'fe14c-21',
  route: 'Conquest',
  chapter: 21,
  title: "Eternal Stairway",
  width: 17,
  height: 30,
  grid: GAME_TERRAIN['fe14c-21'].grid,
  victory: "Have every unit escape.",
  defeat: "Corrin dies, or your army is routed.",
  objectives: [
    { type: 'escape', tiles: [
        [5, 30], [6, 30], [7, 30], [8, 30], [9, 30], [10, 30], [11, 30], [12, 30],
        [13, 30], [14, 30], [15, 30], [16, 30], [17, 30],
    ], label: "Escape point" },
  ],
  units: [
    { type: 'boss', name: "Faceless", tile: [10, 29], paired: true, drops: ["Arms Scroll"] },
    ...commons("Monster", [
        [15, 29], [5, 28], [4, 26], [14, 25], [12, 24], [8, 23], [11, 23], [13, 21],
        [8, 19], [7, 18], [12, 18], [4, 16], [11, 16], [16, 16], [5, 14], [15, 14],
        [9, 13], [10, 12], [12, 11], [5, 10], [16, 9], [3, 1], [4, 1], [13, 1],
        [14, 1],
    ]),
    ...commons("Monster", [[4, 25], [13, 22], [5, 15], [15, 15]], ['Hard', 'Lunatic']),
    ...commons("Monster", [[17, 30], [10, 28], [1, 22], [17, 15], [11, 12]], ['Lunatic']),
  ],
  starts: [[7, 6], [8, 6], [9, 6], [10, 6], [11, 6], [12, 6], [13, 6], [6, 5], [7, 5], [8, 5], [9, 5], [10, 5], [11, 5], [12, 5]],
  objects: [],
  changes: [
    {
      id: 'vein-1',
      trigger: 'dragonVein',
      // Wiki: column 6, row 24.
      tile: { default: [6, 7] },
      usableBy: "Royals",
      effect: "Freezes every enemy in place for one turn.",
    },
    {
      id: 'vein-2',
      trigger: 'dragonVein',
      // Wiki: column 4, row 18.
      tile: { default: [4, 13] },
      usableBy: "Royals",
      effect: "Freezes every enemy in place for one turn. Normal only.",
    },
    {
      id: 'vein-3',
      trigger: 'dragonVein',
      // Wiki: column 10, row 18.
      tile: { default: [11, 13] },
      usableBy: "Royals",
      effect: "Freezes every enemy in place for one turn.",
    },
    {
      id: 'vein-4',
      trigger: 'dragonVein',
      // Wiki: column 7, row 12.
      tile: { default: [7, 19] },
      usableBy: "Royals",
      effect: "Freezes every enemy in place for one turn.",
    },
    {
      id: 'vein-5',
      trigger: 'dragonVein',
      // Wiki: column 15, row 12.
      tile: { default: [15, 19] },
      usableBy: "Royals",
      effect: "Freezes every enemy in place for one turn. Normal and Hard only.",
    },
    {
      id: 'vein-6',
      trigger: 'dragonVein',
      // Wiki: column 10, row 6.
      tile: { default: [10, 25] },
      usableBy: "Royals",
      effect: "Freezes every enemy in place for one turn. Normal only.",
    },
    {
      id: 'vein-7',
      trigger: 'dragonVein',
      // Wiki: column 5, row 4.
      tile: { default: [5, 27] },
      usableBy: "Royals",
      effect: "Freezes every enemy in place for one turn.",
    },
    {
      id: 'vein-8',
      trigger: 'dragonVein',
      // Wiki: column 11, row 2.
      tile: { default: [11, 29] },
      usableBy: "Royals",
      effect: "Freezes every enemy in place for one turn.",
    },
  ],
  notes: [
    "Reinforcements: 2.",
  ],
  terrainOverrides: GAME_TERRAIN['fe14c-21'].terrain,
}

export const CONQUEST_22: ChapterMap = {
  id: 'fe14c-22',
  route: 'Conquest',
  chapter: 22,
  title: "Sakura",
  width: 25,
  height: 20,
  grid: GAME_TERRAIN['fe14c-22'].grid,
  terrainOverrides: GAME_TERRAIN['fe14c-22'].terrain,
  victory: "Seize the gate.",
  defeat: "Corrin dies, or your army is routed.",
  objectives: [
    { type: 'seize', tiles: [[13, 20]], label: "Seize point (gate)" },
  ],
  units: [
    { type: 'boss', name: "Yukimura", tile: [13, 20], drops: ["Gold Bar", "5,000 Gold"], note: "Stands on the gate (the seize point)." },
    { type: 'named', name: "Sakura", tile: [13, 16], drops: ["Spirit Dust"], note: "Stands on woods." },
    ...commons("Hoshidan", [
        [5, 16], [18, 16], [5, 15], [8, 15], [16, 15], [6, 14], [18, 14], [19, 14],
        [1, 12], [21, 11], [9, 10], [10, 10], [21, 10], [9, 9], [17, 9], [18, 9],
        [23, 8], [2, 7], [1, 6],
    ]),
    ...pairs("Hoshidan", [[8, 18], [17, 17]], ['Lunatic']),
    ...commons("Hoshidan", [[9, 18], [18, 17], [12, 16], [23, 16], [7, 15], [13, 14], [23, 13]], ['Hard', 'Lunatic']),
    ...commons("Hoshidan", [[19, 15]], ['Lunatic']),
    ...commons("Hoshidan", [[8, 18], [17, 17]], ['Normal', 'Hard']),
  ],
  starts: [[6, 3], [8, 3], [9, 3], [16, 3], [18, 3], [19, 3], [5, 2], [6, 2], [7, 2], [8, 2], [9, 2], [16, 2], [17, 2], [18, 2], [19, 2]],
  objects: [],
  changes: [
    {
      id: 'vein-1',
      trigger: 'dragonVein',
      // Wiki: column 3, row 13.
      tile: { default: [3, 8] },
      usableBy: "Royals",
      effect: "Flattens a levee.",
      patch: tilesBecome('.', [[4, 7], [4, 6], [4, 5]]),
    },
    {
      id: 'vein-2',
      trigger: 'dragonVein',
      // Wiki: column 6, row 6.
      tile: { default: [6, 15] },
      usableBy: "Royals",
      effect: "Flattens a levee.",
      patch: tilesBecome('.', [[8, 16], [9, 14], [9, 13], [5, 12], [6, 12], [7, 12], [8, 12], [9, 12]]),
    },
    {
      id: 'vein-3',
      trigger: 'dragonVein',
      // Wiki: column 10, row 4.
      tile: { default: [10, 17] },
      usableBy: "Royals",
      effect: "Flattens a levee.",
      patch: tilesBecome('.', [[9, 16], [10, 16], [11, 15], [11, 14], [11, 13]]),
    },
    {
      id: 'vein-4',
      trigger: 'dragonVein',
      // Wiki: column 15, row 4.
      tile: { default: [15, 17] },
      usableBy: "Royals",
      effect: "Flattens a levee.",
      patch: tilesBecome('.', [[19, 18], [19, 17], [14, 15], [14, 14], [14, 13]]),
    },
    {
      id: 'vein-5',
      trigger: 'dragonVein',
      // Wiki: column 18, row 7.
      tile: { default: [20, 14] },
      usableBy: "Royals",
      effect: "Flattens a levee.",
      patch: tilesBecome('.', [[19, 16], [17, 15], [18, 15], [17, 12], [18, 12], [19, 12], [20, 12]]),
    },
    {
      id: 'vein-6',
      trigger: 'dragonVein',
      // Wiki: column 20, row 13.
      tile: { default: [22, 8] },
      usableBy: "Royals",
      effect: "Flattens a levee.",
      patch: tilesBecome('.', [[14, 8], [18, 7], [19, 7]]),
    },
    {
      id: 'vein-7',
      trigger: 'dragonVein',
      // Wiki: column 17, row 16.
      tile: { default: [19, 5] },
      usableBy: "Royals",
      effect: "Flattens a levee.",
      patch: tilesBecome('.', [[14, 7], [15, 7], [16, 7], [17, 7]]),
    },
    {
      id: 'vein-sakura',
      trigger: 'dragonVein',
      // Wiki: column 13, row 5, Sakura's starting tile.
      tile: { default: [13, 16] },
      usableBy: "Sakura, on Hard and Lunatic only",
      effect: "Puts back every levee the other veins flattened (used by you after she is defeated, it flattens every levee still standing instead).",
    },
  ],
  notes: [
    "Mechanists on forts man Launchers.",
    "Reinforcements: 18 on Normal, 29 on Hard, 41 on Lunatic.",
  ],
}

export const CONQUEST_23: ChapterMap = {
  id: 'fe14c-23',
  route: 'Conquest',
  chapter: 23,
  title: "Possessed",
  width: 29,
  height: 23,
  grid: GAME_TERRAIN['fe14c-23'].grid,
  victory: "Seize the throne.",
  defeat: "Corrin dies, or your army is routed.",
  objectives: [
    { type: 'seize', tiles: [[5, 21]], label: "Seize point (throne)" },
  ],
  units: [
    { type: 'boss', name: "Takumi", tile: [5, 21], drops: ["Goddess Icon"], note: "Stands on the throne (the seize point). Mans a Ballista." },
    { type: 'named', name: 'Hinata', tile: [5, 15], note: 'Starts on a gate.' },
    ...pairs("Hoshidan", [[12, 22], [11, 21], [6, 15]]),
    ...commons("Hoshidan", [
        [2, 22], [20, 18], [21, 18], [7, 15], [17, 14], [16, 13], [17, 13],
        [24, 13], [25, 13], [26, 13], [10, 10], [9, 9], [10, 7], [7, 3], [5, 2],
        [6, 2],
    ]),
    ...pairs("Hoshidan", [[3, 21], [11, 20], [3, 15]], ['Hard', 'Lunatic']),
    ...commons("Hoshidan", [[12, 23], [21, 20], [22, 18], [4, 15], [25, 14], [18, 13], [9, 8], [6, 3]], ['Hard', 'Lunatic']),
    ...commons("Hoshidan", [[2, 21], [17, 21], [19, 21], [16, 20], [26, 18], [23, 17], [2, 15]], ['Lunatic']),
    ...commons("Hoshidan", [[11, 20], [3, 15]], ['Normal']),
    ...commons("Hoshidan", [[18, 20], [17, 19], [25, 19], [24, 18]], ['Normal', 'Hard']),
  ],
  starts: [[21, 5], [22, 5], [23, 5], [24, 5], [21, 4], [22, 4], [24, 4], [20, 3], [21, 3], [22, 3], [23, 3], [20, 2], [21, 2], [22, 2], [23, 2]],
  objects: [
    { type: 'chest', tile: [24, 21], contents: "10,000 Gold" },
    { type: 'chest', tile: [25, 21], contents: "Boots" },
  ],
  changes: [],
  notes: [
    "Reinforcements: 7 on Normal, 10 on Hard, 14 on Lunatic.",
  ],
  terrainOverrides: GAME_TERRAIN['fe14c-23'].terrain,
}

export const CONQUEST_24: ChapterMap = {
  id: 'fe14c-24',
  route: 'Conquest',
  chapter: 24,
  title: "Hinoka",
  width: 23,
  height: 30,
  grid: GAME_TERRAIN['fe14c-24'].grid,
  victory: "Seize the gate.",
  defeat: "Corrin dies, or your army is routed.",
  objectives: [
    { type: 'seize', tiles: [[12, 30]], label: "Seize point (gate)" },
  ],
  units: [
    { type: 'boss', name: "Hinoka", tile: [12, 30], paired: true, drops: ["Speedwing"], note: "Paired with an Oni Chieftain, on the gate (the seize point)." },
    ...commons("Hoshidan", [
        [1, 30], [17, 30], [5, 26], [17, 26], [23, 25], [10, 24], [14, 24], [15, 24],
        [3, 22], [3, 21], [6, 20], [7, 20], [16, 18], [17, 18], [16, 17], [4, 16],
        [9, 10], [10, 9], [7, 5], [8, 5], [1, 2], [1, 1],
    ]),
    ...commons("Hoshidan", [[18, 30], [1, 29], [23, 26], [8, 21], [3, 16], [10, 10]], ['Hard', 'Lunatic']),
    ...commons("Hoshidan", [
        [6, 29], [7, 29], [6, 28], [6, 27], [16, 26], [22, 26], [19, 21], [6, 19],
        [7, 6], [2, 1],
    ], ['Lunatic']),
    ...commons("Hoshidan", [[8, 22]], ['Normal']),
  ],
  starts: [[19, 6], [20, 6], [21, 6], [22, 6], [19, 5], [20, 5], [21, 5], [22, 5], [19, 4], [20, 4], [21, 4], [22, 4], [19, 3], [20, 3], [21, 3]],
  objects: [],
  changes: [
    {
      id: 'vein-1',
      trigger: 'dragonVein',
      // Wiki: column 7, row 21.
      tile: { default: [7, 10] },
      usableBy: "Royals",
      effect: "Slows fliers and speeds everyone else for two turns (by half their class's base Move).",
    },
    {
      id: 'vein-2',
      trigger: 'dragonVein',
      // Wiki: column 13, row 17.
      tile: { default: [13, 14] },
      usableBy: "Royals",
      effect: "Slows fliers and speeds everyone else for two turns (by half their class's base Move). Normal and Hard only.",
    },
    {
      id: 'vein-3',
      trigger: 'dragonVein',
      // Wiki: column 12, row 15.
      tile: { default: [12, 16] },
      usableBy: "Royals",
      effect: "Slows fliers and speeds everyone else for two turns (by half their class's base Move). Lunatic only.",
    },
    {
      id: 'vein-4',
      trigger: 'dragonVein',
      // Wiki: column 19, row 16.
      tile: { default: [19, 15] },
      usableBy: "Royals",
      effect: "Slows fliers and speeds everyone else for two turns (by half their class's base Move).",
    },
    {
      id: 'vein-5',
      trigger: 'dragonVein',
      // Wiki: column 14, row 4.
      tile: { default: [14, 27] },
      usableBy: "Royals",
      effect: "Slows fliers and speeds everyone else for two turns (by half their class's base Move). Normal only.",
    },
    {
      id: 'vein-6',
      trigger: 'dragonVein',
      // Wiki: column 10, row 4.
      tile: { default: [10, 27] },
      usableBy: "Royals",
      effect: "Slows fliers and speeds everyone else for two turns (by half their class's base Move).",
    },
    {
      id: 'vein-7',
      trigger: 'dragonVein',
      // Wiki: column 9, row 10.
      tile: { default: [9, 21] },
      usableBy: "Royals",
      effect: "Slows fliers and speeds everyone else for two turns (by half their class's base Move). Normal only.",
    },
    {
      id: 'vein-hinoka',
      trigger: 'dragonVein',
      // Wiki: column 12, row 1, Hinoka's tile.
      tile: { default: [12, 30] },
      usableBy: "Hinoka, whenever no other vein is in effect",
      effect: "Speeds fliers and slows everyone else for two turns.",
    },
  ],
  notes: [
    "Reinforcements: 17 on Normal, 22 on Hard, 34 on Lunatic.",
  ],
  terrainOverrides: GAME_TERRAIN['fe14c-24'].terrain,
}

export const CONQUEST_25: ChapterMap = {
  id: 'fe14c-25',
  route: 'Conquest',
  chapter: 25,
  title: "Ryoma",
  width: 28,
  height: 25,
  grid: GAME_TERRAIN['fe14c-25'].grid,
  terrainOverrides: GAME_TERRAIN['fe14c-25'].terrain,
  victory: "Defeat Ryoma.",
  defeat: "Corrin dies, or your army is routed.",
  objectives: [],
  units: [
    { type: 'boss', name: "Ryoma", tile: [13, 15], drops: ["Dracoshield"] },
    { type: 'named', name: "Saizo or Kagero", tile: [26, 24], note: "Stands on a cushion." },
    { type: 'named', name: "Saizo or Kagero", tile: [7, 24], note: "Stands on a cushion." },
    ...pairs("Hoshidan", [[7, 13]]),
    ...commons("Hoshidan", [
        [25, 23], [6, 22], [7, 22], [8, 22], [26, 22], [3, 19], [25, 19], [3, 18],
        [27, 18], [4, 15], [21, 15], [22, 15], [28, 15], [4, 14], [22, 10], [3, 9],
        [5, 9], [23, 9], [2, 8], [3, 8], [26, 5], [28, 4], [26, 3],
    ]),
    ...pairs("Hoshidan", [[21, 19]], ['Hard', 'Lunatic']),
    ...commons("Hoshidan", [[7, 23], [27, 23], [7, 20], [5, 16], [22, 16], [28, 16], [25, 15], [5, 8]], ['Hard', 'Lunatic']),
    ...commons("Hoshidan", [
        [4, 16], [25, 16], [6, 15], [1, 14], [25, 11], [23, 10], [28, 9], [27, 6],
        [1, 5], [1, 3], [2, 2],
    ], ['Lunatic']),
  ],
  starts: [[16, 9], [13, 5], [16, 5], [11, 4], [12, 4], [17, 4], [18, 4], [11, 3], [12, 3], [13, 3], [17, 3], [18, 3], [12, 2], [17, 2], [13, 1], [16, 1]],
  objects: [
    { type: 'chest', tile: [6, 14], contents: "Silence" },
    { type: 'chest', tile: [20, 25], contents: "10,000 Gold" },
    { type: 'door', tile: [11, 21] },
    { type: 'door', tile: [18, 21] },
    { type: 'door', tile: [14, 17] },
    { type: 'door', tile: [15, 17] },
    { type: 'door', tile: [14, 7] },
    { type: 'door', tile: [15, 7] },
  ],
  changes: [
    {
      id: 'vein',
      trigger: 'dragonVein',
      // Wiki: column 14, row 6, three north of the screen into the dueling chamber.
      tile: { default: [14, 20] },
      usableBy: "Royals",
      effect: "Turns the healing tiles into Avoid-penalty tiles.",
    },
  ],
  notes: [
    "Defeating Saizo (Normal), or both Saizo and Kagero (Hard, Lunatic), opens the screens to Ryoma's chamber.",
  ],
}

export const CONQUEST_26: ChapterMap = {
  id: 'fe14c-26',
  route: 'Conquest',
  chapter: 26,
  title: "Treason",
  width: 26,
  height: 30,
  grid: GAME_TERRAIN['fe14c-26'].grid,
  terrainOverrides: GAME_TERRAIN['fe14c-26'].terrain,
  victory: "Seize the throne.",
  defeat: "Corrin dies, or your army is routed.",
  objectives: [
    { type: 'seize', tiles: [[13, 12]], label: "Seize point (throne)" },
  ],
  units: [
    { type: 'boss', name: "Iago", tile: [13, 12], drops: ["Excalibur"], note: "Stands on the throne (the seize point). Cycles through his staves in inventory order." },
    ...commons("Nohrian", [
        [4, 19], [12, 19], [15, 19], [4, 18], [13, 18], [17, 17], [10, 16], [17, 16],
        [3, 15], [2, 14], [24, 14], [26, 14], [2, 13], [3, 13], [21, 13], [24, 13],
        [25, 13], [26, 12], [3, 11], [25, 11], [3, 10], [14, 9], [13, 8], [15, 8],
        [10, 7], [17, 7], [10, 6], [3, 5], [13, 5], [14, 5], [17, 5], [23, 5],
        [10, 4], [17, 4],
    ]),
    ...commons("Nohrian", [
        [14, 18], [22, 18], [10, 17], [13, 17], [6, 13], [21, 12], [26, 11], [1, 10],
        [5, 6], [12, 6], [15, 6], [17, 6], [10, 5],
    ], ['Hard', 'Lunatic']),
    ...commons("Nohrian", [[1, 14], [26, 9]], ['Lunatic']),
  ],
  starts: [[13, 28], [14, 28], [12, 27], [13, 27], [14, 27], [15, 27], [12, 26], [13, 26], [14, 26], [15, 26], [12, 25], [13, 25], [14, 25], [15, 25], [13, 24], [14, 24]],
  objects: [
    { type: 'chest', tile: [1, 16], contents: "Spy's Yumi (Normal, if Kaze is alive with shuriken rank below B) or Spy's Shuriken" },
    { type: 'chest', tile: [26, 16], contents: "Venge Naginata" },
    { type: 'chest', tile: [9, 12], contents: "20,000 Gold" },
    { type: 'chest', tile: [14, 12], contents: "Bifr\u00f6st" },
    { type: 'chest', tile: [18, 12], contents: "Seraph Robe" },
    { type: 'door', tile: [13, 21] },
    { type: 'door', tile: [14, 21] },
    { type: 'door', tile: [8, 19] },
    { type: 'door', tile: [19, 19] },
    { type: 'door', tile: [8, 18] },
    { type: 'door', tile: [19, 18] },
    { type: 'door', tile: [5, 12] },
    { type: 'door', tile: [22, 12] },
    { type: 'door', tile: [5, 11] },
    { type: 'door', tile: [22, 11] },
    { type: 'door', tile: [13, 10] },
    { type: 'door', tile: [14, 10] },
    { type: 'door', tile: [3, 8] },
    { type: 'door', tile: [4, 8] },
    { type: 'door', tile: [23, 8] },
    { type: 'door', tile: [24, 8] },
    { type: 'door', tile: [7, 6] },
    { type: 'door', tile: [20, 6] },
    { type: 'door', tile: [7, 5] },
    { type: 'door', tile: [20, 5] },
  ],
  changes: [],
  notes: [
    "Reinforcements: 8 on Hard, 27 on Lunatic.",
  ],
}

export const CONQUEST_27: ChapterMap = {
  id: 'fe14c-27',
  route: 'Conquest',
  chapter: 27,
  title: "The Empty King",
  width: 29,
  height: 30,
  grid: GAME_TERRAIN['fe14c-27'].grid,
  terrainOverrides: GAME_TERRAIN['fe14c-27'].terrain,
  victory: "Defeat Garon.",
  defeat: "Corrin dies, or your army is routed.",
  objectives: [],
  units: [
    { type: 'boss', name: "Garon", tile: [15, 30], note: "Stands on a throne." },
    ...commons("Invader", [
        [14, 23], [15, 23], [16, 23], [15, 22], [3, 21], [27, 21], [3, 19], [27, 19],
        [2, 15], [28, 15], [2, 13], [28, 13], [1, 9], [29, 9], [1, 7], [29, 7],
    ]),
    ...pairs("Invader", [[3, 20], [27, 20]], ['Hard', 'Lunatic']),
    ...commons("Invader", [[15, 24]], ['Lunatic']),
  ],
  starts: [[7, 19], [23, 19], [6, 13], [24, 13], [5, 7], [25, 7], [13, 2], [14, 2], [15, 2], [16, 2], [17, 2], [13, 1], [14, 1], [15, 1], [16, 1], [17, 1]],
  objects: [
    { type: 'door', tile: [3, 22] },
    { type: 'door', tile: [2, 16] },
    { type: 'door', tile: [1, 10] },
    { type: 'door', tile: [27, 22] },
    { type: 'door', tile: [28, 16] },
    { type: 'door', tile: [29, 10] },
  ],
  changes: [],
  notes: [
    "Corrin's Grim Yato becomes the Shadow Yato before battle preparations.",
  ],
}

export const CONQUEST_ENDGAME: ChapterMap = {
  id: 'fe14c-endgame',
  route: 'Conquest',
  chapter: 28,
  title: "Night Breaks Through",
  width: 29,
  height: 30,
  grid: GAME_TERRAIN['fe14c-endgame'].grid,
  terrainOverrides: GAME_TERRAIN['fe14c-endgame'].terrain,
  victory: "Defeat Takumi.",
  defeat: "Corrin dies, or your army is routed.",
  objectives: [],
  units: [
    { type: 'boss', name: "Takumi", tile: [15, 2], paired: true, note: "Paired with his own Replica." },
    ...commons("Invader", [
        [5, 20], [5, 19], [25, 19], [26, 19], [14, 15], [15, 15], [16, 15], [15, 12],
        [12, 11], [13, 11], [16, 10], [13, 9], [17, 8], [17, 7], [18, 7], [15, 5],
    ]),
    ...pairs("Invader", [[3, 8], [4, 8], [26, 8], [26, 7]], ['Hard', 'Lunatic']),
    ...commons("Invader", [
        [27, 20], [3, 19], [15, 14], [15, 13], [12, 12], [18, 12], [14, 10], [15, 9],
        [14, 6], [16, 6], [17, 5],
    ], ['Lunatic']),
    ...commons("Invader", [[3, 8], [4, 8], [26, 8], [26, 7]], ['Normal']),
  ],
  starts: [[14, 28], [15, 28], [16, 28], [17, 28], [13, 27], [14, 27], [15, 27], [16, 27], [14, 26], [15, 26], [16, 26], [17, 26], [13, 25], [14, 25], [15, 25], [16, 25]],
  objects: [],
  changes: [
    {
      id: 'vein-1',
      trigger: 'dragonVein',
      // Wiki: column 12, row 26.
      tile: { default: [12, 5] },
      usableBy: "Royals",
      effect: "Raises five barrier blocks (30 HP each) to blunt Takumi's attack.",
      patch: tilesBecome('#', [[13, 13], [17, 13], [14, 8], [15, 8], [16, 8]]),
    },
    {
      id: 'vein-2',
      trigger: 'dragonVein',
      // Wiki: column 13, row 14.
      tile: { default: [13, 17] },
      usableBy: "Royals",
      effect: "Raises five barrier blocks (30 HP each) to blunt Takumi's attack.",
      patch: tilesBecome('#', [[13, 13], [17, 13], [14, 8], [15, 8], [16, 8]]),
    },
    {
      id: 'vein-3',
      trigger: 'dragonVein',
      // Wiki: column 14, row 9.
      tile: { default: [14, 22] },
      usableBy: "Royals",
      effect: "Raises five barrier blocks (30 HP each) to blunt Takumi's attack.",
      patch: tilesBecome('#', [[13, 13], [17, 13], [14, 8], [15, 8], [16, 8]]),
    },
    {
      id: 'vein-4',
      trigger: 'dragonVein',
      // Wiki: column 14, row 18.
      tile: { default: [14, 13] },
      usableBy: "Royals",
      effect: "Raises five barrier blocks (30 HP each) to blunt Takumi's attack.",
      patch: tilesBecome('#', [[13, 13], [17, 13], [14, 8], [15, 8], [16, 8]]),
    },
    {
      id: 'vein-5',
      trigger: 'dragonVein',
      // Wiki: column 14, row 22.
      tile: { default: [14, 9] },
      usableBy: "Royals",
      effect: "Raises five barrier blocks (30 HP each) to blunt Takumi's attack.",
      patch: tilesBecome('#', [[13, 13], [17, 13], [14, 8], [15, 8], [16, 8]]),
    },
    {
      id: 'vein-6',
      trigger: 'dragonVein',
      // Wiki: column 15, row 13.
      tile: { default: [15, 18] },
      usableBy: "Royals",
      effect: "Raises five barrier blocks (30 HP each) to blunt Takumi's attack.",
      patch: tilesBecome('#', [[13, 13], [17, 13], [14, 8], [15, 8], [16, 8]]),
    },
    {
      id: 'vein-7',
      trigger: 'dragonVein',
      // Wiki: column 15, row 18.
      tile: { default: [15, 13] },
      usableBy: "Royals",
      effect: "Raises five barrier blocks (30 HP each) to blunt Takumi's attack.",
      patch: tilesBecome('#', [[13, 13], [17, 13], [14, 8], [15, 8], [16, 8]]),
    },
    {
      id: 'vein-8',
      trigger: 'dragonVein',
      // Wiki: column 16, row 11.
      tile: { default: [16, 20] },
      usableBy: "Royals",
      effect: "Raises five barrier blocks (30 HP each) to blunt Takumi's attack.",
      patch: tilesBecome('#', [[13, 13], [17, 13], [14, 8], [15, 8], [16, 8]]),
    },
    {
      id: 'vein-9',
      trigger: 'dragonVein',
      // Wiki: column 16, row 18.
      tile: { default: [16, 13] },
      usableBy: "Royals",
      effect: "Raises five barrier blocks (30 HP each) to blunt Takumi's attack.",
      patch: tilesBecome('#', [[13, 13], [17, 13], [14, 8], [15, 8], [16, 8]]),
    },
    {
      id: 'vein-10',
      trigger: 'dragonVein',
      // Wiki: column 16, row 22.
      tile: { default: [16, 9] },
      usableBy: "Royals",
      effect: "Raises five barrier blocks (30 HP each) to blunt Takumi's attack.",
      patch: tilesBecome('#', [[13, 13], [17, 13], [14, 8], [15, 8], [16, 8]]),
    },
    {
      id: 'vein-11',
      trigger: 'dragonVein',
      // Wiki: column 17, row 14.
      tile: { default: [17, 17] },
      usableBy: "Royals",
      effect: "Raises five barrier blocks (30 HP each) to blunt Takumi's attack.",
      patch: tilesBecome('#', [[13, 13], [17, 13], [14, 8], [15, 8], [16, 8]]),
    },
    {
      id: 'vein-12',
      trigger: 'dragonVein',
      // Wiki: column 18, row 26.
      tile: { default: [18, 5] },
      usableBy: "Royals",
      effect: "Raises five barrier blocks (30 HP each) to blunt Takumi's attack.",
      patch: tilesBecome('#', [[13, 13], [17, 13], [14, 8], [15, 8], [16, 8]]),
    },
  ],
  notes: [
    "Takumi's area attack hits your units in the main hall for 50% of their max HP every 3 turns (every 2 on Lunatic).",
    "Reinforcements: 1 on Normal, 20 on Hard, 22 on Lunatic.",
  ],
}

export const CONQUEST_13_TO_ENDGAME: ChapterMap[] = [CONQUEST_13, CONQUEST_14, CONQUEST_15, CONQUEST_16, CONQUEST_17, CONQUEST_18, CONQUEST_19, CONQUEST_20, CONQUEST_21, CONQUEST_22, CONQUEST_23, CONQUEST_24, CONQUEST_25, CONQUEST_26, CONQUEST_27, CONQUEST_ENDGAME]
