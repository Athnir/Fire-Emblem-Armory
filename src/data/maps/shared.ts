import type { ChapterMap, TerrainLetter, Tile } from './types'
import { commons, pairs } from './units'
import { GAME_TERRAIN } from './gameTerrain'

const tilesBecome = (becomes: TerrainLetter, tiles: Tile[]) => tiles.map((tile) => ({ tile, becomes }))

/*
 * The shared chapters (1 to 5), before the route split. The Prologue is left out: it's a scripted
 * battle with almost no input from the player. Grids are read off the Fire
 * Emblem Wiki minimaps at 6 px per tile; each Dragon Vein's patch is the difference between the
 * normal minimap and the wiki's after-vein ("_dv") minimap. Wiki chapter pages count rows from the
 * top, so their coordinates are converted to bottom-left (1, 1) here.
 */

export const CHAPTER_1: ChapterMap = {
  id: 'fe14-1',
  route: 'Shared',
  chapter: 1,
  title: 'Nohr',
  width: 13,
  height: 13,
  grid: GAME_TERRAIN['fe14-1'].grid,
  victory: 'Defeat Xander.',
  defeat: 'Corrin is defeated.',
  objectives: [],
  units: [{ type: 'boss', name: 'Xander', tile: [7, 10] }],
  starts: [[7, 3]],
  objects: [],
  changes: [
    {
      id: 'vein',
      trigger: 'dragonVein',
      // Wiki: column 7, row 4, where Xander stands.
      tile: { default: [7, 10] },
      usableBy: 'Royals (Xander uses it after the first round of combat)',
      effect: 'Creates a healing tile at the centre of the map.',
      patch: tilesBecome('H', [[7, 7]]),
    },
  ],
  notes: [],
  terrainOverrides: { ...GAME_TERRAIN['fe14-1'].terrain, ...{ H: { heal: 50 } } },
  sources: [
    { label: 'Fire Emblem Wiki minimaps', url: 'https://fireemblemwiki.org/wiki/Category:Fates_maps' },
    { label: 'Fire Emblem Wiki: Nohr (chapter)', url: 'https://fireemblemwiki.org/wiki/Nohr_(chapter)' },
  ],
}

export const CHAPTER_2: ChapterMap = {
  id: 'fe14-2',
  route: 'Shared',
  chapter: 2,
  title: 'Gift of Ganglari',
  width: 15,
  height: 15,
  grid: GAME_TERRAIN['fe14-2'].grid,
  terrainOverrides: GAME_TERRAIN['fe14-2'].terrain,
  victory: 'Rout the enemy.',
  defeat: 'Corrin dies, or your army is routed.',
  objectives: [],
  units: [
    { type: 'boss', name: "Rinkah", tile: [4, 15] },
    { type: 'boss', name: "Kaze", tile: [12, 15] },
    ...commons("Hoshidan", [[3, 14], [13, 14]]),
    ...commons("Hoshidan", [[4, 14], [12, 14]], ['Hard', 'Lunatic']),
  ],
  starts: [[8, 2], [7, 1], [9, 1]],
  objects: [],
  changes: [
    {
      id: 'vein',
      trigger: 'dragonVein',
      // Wiki: column 8, row 13, one tile above where Corrin begins.
      tile: { default: [8, 3] },
      usableBy: 'Royals',
      effect: 'Clears the debris to reveal a large healing area.',
      patch: [
        ...tilesBecome('H', [[7, 7], [8, 7], [9, 7], [7, 6], [8, 6], [9, 6], [7, 5], [8, 5], [9, 5]]),
        ...tilesBecome('.', [[6, 6], [10, 6], [8, 4]]),
      ],
    },
  ],
  notes: ['Gunter and Felicia (or Jakob) join on turn 1.'],
  sources: [
    { label: 'Fire Emblem Wiki minimaps', url: 'https://fireemblemwiki.org/wiki/Category:Fates_maps' },
    { label: 'Fire Emblem Wiki: Gift of Ganglari', url: 'https://fireemblemwiki.org/wiki/Gift_of_Ganglari' },
  ],
}

export const CHAPTER_3: ChapterMap = {
  id: 'fe14-3',
  route: 'Shared',
  chapter: 3,
  title: 'Journey Begins',
  width: 20,
  height: 18,
  grid: GAME_TERRAIN['fe14-3'].grid,
  terrainOverrides: GAME_TERRAIN['fe14-3'].terrain,
  victory: 'Seize the old gate.',
  defeat: 'Corrin dies, or your army is routed.',
  objectives: [{ type: 'seize', tiles: [[17, 5]], label: 'Seize point (old gate)' }],
  units: [
    { type: 'boss', name: "Omozu", tile: [17, 5] },
    { type: 'enemy', name: "Hoshidan Samurai", tile: [17, 15], paired: true },
    ...commons("Hoshidan", [[12, 16], [17, 16], [12, 15], [18, 15], [17, 14], [14, 6], [14, 5]]),
    ...commons("Hoshidan", [[20, 6]], ['Hard', 'Lunatic']),
    ...commons("Hoshidan", [[19, 7], [15, 5]], ['Lunatic']),
    ...commons("Hoshidan", [[20, 5]], ['Normal']),
    { type: 'ally', name: 'Hans', tile: [5, 16] },
  ],
  starts: [[1, 16], [3, 16], [4, 16]],
  objects: [],
  changes: [
    {
      id: 'vein-west',
      trigger: 'dragonVein',
      // Wiki: column 9, row 13.
      tile: { default: [9, 6] },
      usableBy: 'Royals',
      effect: 'Creates a stone bridge across the canyon.',
      patch: tilesBecome('b', [[10, 6], [11, 6], [12, 6], [13, 6], [10, 5], [11, 5], [12, 5]]),
    },
    {
      id: 'vein-north',
      trigger: 'dragonVein',
      // Wiki: column 11, row 9.
      tile: { default: [11, 10] },
      usableBy: 'Royals',
      effect: 'Creates a stone bridge across the canyon.',
      patch: tilesBecome('b', [[12, 10], [13, 10], [14, 10], [15, 10], [16, 10], [17, 10]]),
    },
  ],
  notes: ['Reinforcements: Sky Knights (2 on Normal, 3 on Hard/Lunatic) once a unit reaches the ground around the old gate.'],
  sources: [
    { label: 'Fire Emblem Wiki minimaps', url: 'https://fireemblemwiki.org/wiki/Category:Fates_maps' },
    { label: 'Fire Emblem Wiki: Journey Begins', url: 'https://fireemblemwiki.org/wiki/Journey_Begins' },
  ],
}

export const CHAPTER_4: ChapterMap = {
  id: 'fe14-4',
  route: 'Shared',
  chapter: 4,
  title: 'Hoshido',
  width: 18,
  height: 18,
  grid: GAME_TERRAIN['fe14-4'].grid,
  terrainOverrides: GAME_TERRAIN['fe14-4'].terrain,
  victory: 'Rout the enemy.',
  defeat: 'Corrin dies, or your army is routed.',
  objectives: [],
  units: [
    { type: 'boss', name: "Faceless", tile: [8, 11] },
    ...commons("Faceless", [
        [15, 17], [9, 16], [17, 15], [16, 13], [7, 12], [7, 11], [14, 8], [1, 7],
        [3, 4], [8, 3], [2, 2],
      ]),
    ...commons("Faceless", [[8, 12], [18, 11]], ['Hard', 'Lunatic']),
    { type: 'ally', name: 'Hinoka', tile: [3, 18], note: 'Talk to her with Corrin for a Concoction.' },
    { type: 'ally', name: 'Sakura', tile: [1, 18] },
    { type: 'ally', name: 'Ryoma', tile: [18, 1] },
  ],
  starts: [[17, 2], [18, 2], [17, 1]],
  objects: [{ type: 'village', tile: [17, 4], reward: 'Goddess Icon' }],
  // The wiki places each vein relative to a landmark (the village entrance, Hinoka, the boss);
  // each one lands beside exactly one snow mountain, and that mountain is its patch.
  changes: [
    {
      id: 'vein-east',
      trigger: 'dragonVein',
      tile: { default: [14, 5] },
      usableBy: 'Royals',
      effect: 'Melts the snow mountain next to it with flames.',
      patch: tilesBecome('.', [
        [14, 10], [15, 10], [12, 9], [13, 9], [14, 9], [15, 9], [16, 9], [12, 8],
        [13, 8], [14, 8], [15, 8], [16, 8], [13, 7], [14, 7], [15, 7], [16, 7],
        [14, 6], [15, 6],
      ]),
    },
    {
      id: 'vein-south',
      trigger: 'dragonVein',
      tile: { default: [11, 3] },
      usableBy: 'Royals',
      effect: 'Melts the snow mountain next to it with flames.',
      patch: tilesBecome('.', [
        [7, 5], [8, 5], [9, 5], [7, 4], [8, 4], [9, 4], [10, 4], [6, 3],
        [7, 3], [8, 3], [9, 3], [10, 3], [7, 2], [8, 2], [9, 2], [10, 2],
      ]),
    },
    {
      id: 'vein-west',
      trigger: 'dragonVein',
      tile: { default: [2, 5] },
      usableBy: 'Royals',
      effect: 'Melts the snow mountain next to it with flames.',
      patch: tilesBecome('.', [
        [2, 11], [1, 10], [2, 10], [1, 9], [2, 9], [3, 9], [4, 9], [1, 8],
        [2, 8], [3, 8], [1, 7], [2, 7], [3, 7], [1, 6], [2, 6], [3, 6],
      ]),
    },
    {
      id: 'vein-northwest',
      trigger: 'dragonVein',
      tile: { default: [4, 14] },
      usableBy: 'Royals',
      effect: 'Melts the snow mountain next to it with flames.',
      patch: tilesBecome('.', [
        [1, 17], [2, 17], [3, 17], [4, 17], [1, 16], [2, 16], [3, 16], [4, 16],
        [1, 15], [2, 15], [3, 15], [4, 15], [1, 14], [2, 14], [3, 14],
      ]),
    },
    {
      id: 'vein-center-north',
      trigger: 'dragonVein',
      tile: { default: [6, 14] },
      usableBy: 'Royals',
      effect: 'Melts the snow mountain next to it with flames.',
      patch: tilesBecome('.', [
        [7, 14], [8, 14], [9, 14], [6, 13], [7, 13], [8, 13], [9, 13], [10, 13],
        [5, 12], [6, 12], [7, 12], [8, 12], [9, 12], [10, 12], [11, 12], [4, 11],
        [5, 11], [6, 11], [7, 11], [8, 11], [9, 11], [10, 11], [11, 11], [5, 10],
        [6, 10], [7, 10], [8, 10], [9, 10], [10, 10], [6, 9], [7, 9], [8, 9],
        [9, 9], [7, 8], [8, 8],
      ]),
    },
    {
      id: 'vein-center-south',
      trigger: 'dragonVein',
      tile: { default: [10, 9] },
      usableBy: 'Royals',
      effect: 'Melts the snow mountain next to it with flames.',
      patch: tilesBecome('.', [
        [7, 14], [8, 14], [9, 14], [6, 13], [7, 13], [8, 13], [9, 13], [10, 13],
        [5, 12], [6, 12], [7, 12], [8, 12], [9, 12], [10, 12], [11, 12], [4, 11],
        [5, 11], [6, 11], [7, 11], [8, 11], [9, 11], [10, 11], [11, 11], [5, 10],
        [6, 10], [7, 10], [8, 10], [9, 10], [10, 10], [6, 9], [7, 9], [8, 9],
        [9, 9], [7, 8], [8, 8],
      ]),
    },
    {
      id: 'vein-northeast',
      trigger: 'dragonVein',
      tile: { default: [15, 13] },
      usableBy: 'Royals',
      effect: 'Melts the snow mountain next to it with flames.',
      patch: tilesBecome('.', [
        [11, 17], [12, 17], [13, 17], [14, 17], [15, 17], [11, 16], [12, 16], [13, 16],
        [14, 16], [15, 16], [16, 16], [11, 15], [12, 15], [13, 15], [14, 15], [15, 15],
        [16, 15], [12, 14], [13, 14], [14, 14], [15, 14], [12, 13], [13, 13], [14, 13],
      ]),
    },
  ],
  notes: ['Rinkah and Kaze join on turn 1.'],
  sources: [
    { label: 'Fire Emblem Wiki minimaps', url: 'https://fireemblemwiki.org/wiki/Category:Fates_maps' },
    { label: 'Fire Emblem Wiki: Hoshido (chapter)', url: 'https://fireemblemwiki.org/wiki/Hoshido_(chapter)' },
  ],
}

export const CHAPTER_5: ChapterMap = {
  id: 'fe14-5',
  route: 'Shared',
  chapter: 5,
  title: 'Mother',
  width: 15,
  height: 18,
  grid: GAME_TERRAIN['fe14-5'].grid,
  victory: 'Rout the enemy.',
  defeat: 'Corrin dies.',
  objectives: [],
  units: [
    { type: 'boss', name: "???", tile: [8, 1] },
    ...commons("Invader", [[2, 11], [14, 11], [2, 10]]),
    ...pairs("Invader", [[6, 6]], ['Hard', 'Lunatic']),
    ...commons("Invader", [[14, 10], [7, 6], [9, 5]], ['Hard', 'Lunatic']),
    ...commons("Invader", [[8, 6]], ['Lunatic']),
    ...commons("Invader", [[6, 6], [9, 6], [7, 5]], ['Normal']),
    { type: 'ally', name: 'Ryoma', tile: [8, 2] },
  ],
  starts: [[7, 18], [8, 18], [9, 18], [8, 17], [8, 14]],
  objects: [],
  changes: [],
  notes: [
    'Corrin starts as a Feral Dragon. Sakura and Azura join on turn 1.',
    "Reinforcements (Hard/Lunatic only): Dark Mages from the map corners once you enter the southern group's range.",
  ],
  terrainOverrides: GAME_TERRAIN['fe14-5'].terrain,
  sources: [
    { label: 'Fire Emblem Wiki minimaps', url: 'https://fireemblemwiki.org/wiki/Category:Fates_maps' },
    { label: 'Fire Emblem Wiki: Mother', url: 'https://fireemblemwiki.org/wiki/Mother' },
  ],
}

export const SHARED_MAPS: ChapterMap[] = [CHAPTER_1, CHAPTER_2, CHAPTER_3, CHAPTER_4, CHAPTER_5]
