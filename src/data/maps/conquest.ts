import type { ChapterMap, TerrainLetter, Tile } from './types'
import { commons, pairs } from './units'

const tilesBecome = (becomes: TerrainLetter, tiles: Tile[]) => tiles.map((tile) => ({ tile, becomes }))

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
  // The Prologue's battlefield, fought from the other side.
  grid: [
    '...w............www.', // 22
    '...ww......ff..www..', // 21
    '...brrb.....f..www..', // 20
    '....ww.........ww...', // 19
    '.....ww.......www...', // 18
    '......w.......www...', // 17
    '......ww......bbb...', // 16
    '.......ww.....ww....', // 15
    '........ww...ww.....', // 14
    '........ww...ww.....', // 13
    '.........ww.ww......', // 12
    '....ff....wwww..f...', // 11
    '....ff....www...ff..', // 10
    '.....f....www...ff..', // 9
    '.........www.....f..', // 8
    '.........ww.........', // 7
    '.........bb.........', // 6
    '........bbb.........', // 5
    '........www...ff....', // 4
    'ff.....www...ff.ff..', // 3
    'fff....www..ffff....', // 2
    'ffff..www...fffff...', // 1
  ],
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
      patch: tilesBecome('.', [
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
  unconfirmed: ['Which of (17, 10) and (18, 10) is Yukimura and which is Sakura.'],
  sources: [
    { label: 'Fire Emblem Wiki minimaps', url: 'https://fireemblemwiki.org/wiki/Category:Fates_maps' },
    { label: "Fire Emblem Wiki: Embrace the Dark", url: 'https://fireemblemwiki.org/wiki/Embrace_the_Dark' },
  ],
}

export const CONQUEST_7: ChapterMap = {
  id: 'fe14c-7',
  route: 'Conquest',
  chapter: 7,
  title: "A Dragon's Decree",
  width: 19,
  height: 20,
  grid: [
    'kkkff.f..f.fff..ff.', // 20
    'kkk..f..ff..ff...f.', // 19
    'kkf.ff.www.ff...fff', // 18
    'kkf..wwwwwww....fww', // 17
    'ffwwwww..wwwww..www', // 16
    '...wwww..fwwww.wwwf', // 15
    'ff.wwwww.fwww..ww..', // 14
    'f..wwwww.wwww.wwww.', // 13
    'f.f..wwwwwwww..wwww', // 12
    '..f.ff.wwww..f.wwww', // 11
    '.....f.bbbbf....www', // 10
    '......fbbbb.......w', // 9
    'f...f..wwww.ff.....', // 8
    'f..fwwwwwwww.......', // 7
    'ff.f.wwwffwwww..ww.', // 6
    'kffwwwwwwwwwww.wwww', // 5
    'kkk.wwwwwwwwww.wwww', // 4
    'k....www..www...www', // 3
    'k...f.f..ff..f...fw', // 2
    'k....ff...ff..f.f.k', // 1
  ],
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
  unconfirmed: ['The dark blocks in the corners are shown as thick wood (only fliers can enter).'],
  sources: [
    { label: 'Fire Emblem Wiki minimaps', url: 'https://fireemblemwiki.org/wiki/Category:Fates_maps' },
    { label: "Fire Emblem Wiki: A Dragon's Decree", url: 'https://fireemblemwiki.org/wiki/A_Dragon%27s_Decree' },
  ],
}

export const CONQUEST_8: ChapterMap = {
  id: 'fe14c-8',
  route: 'Conquest',
  chapter: 8,
  title: 'Cold Reception',
  width: 25,
  height: 17,
  grid: [
    'BBBBB..fff.BBB....##.....', // 17
    'BBBBB..##..BBB.f..##.ff..', // 16
    'BBBBB..##...v.##f....ff..', // 15
    'B...B.........##.....ff..', // 14
    '..g................BBB...', // 13
    '.....##............BBB...', // 12
    'ff...##.........##..v...f', // 11
    '................##......f', // 10
    '.BBB.......###.......##..', // 9
    '.BBB.......###.....f.##..', // 8
    '..v....##..###....ff.....', // 7
    '.......##.........f......', // 6
    '....................BBB..', // 5
    '...BBB..............BBB..', // 4
    '...BBB............##.v...', // 3
    'ff..v..........f..##.....', // 2
    'ff............fff......f.', // 1
  ],
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
      patch: tilesBecome('w', [
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
      patch: tilesBecome('w', [
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
  unconfirmed: ['Flora (named) is among the starting enemies; her tile isn\'t recorded.'],
  sources: [
    { label: 'Fire Emblem Wiki minimaps', url: 'https://fireemblemwiki.org/wiki/Category:Fates_maps' },
    { label: "Fire Emblem Wiki: Cold Reception", url: 'https://fireemblemwiki.org/wiki/Cold_Reception' },
  ],
}

export const CONQUEST_9: ChapterMap = {
  id: 'fe14c-9',
  route: 'Conquest',
  chapter: 9,
  title: 'Another Trial',
  width: 30,
  height: 15,
  grid: [
    '..WWWWWWWWWWW....############.', // 15
    '...WWff...ff...#.#############', // 14
    'W..WWWW......####......#...#.#', // 13
    '.........######...###.c###....', // 12
    '....W########...##..S##..#.###', // 11
    '.f...####.....####............', // 10
    '..........#..#S..#......##.#..', // 9
    '..............#.t.#..#...#.#c.', // 8
    '...........#..##.##..#.#.#.##.', // 7
    '..f.W####......###..#.........', // 6
    '...f.########...........S#.###', // 5
    '.........######....#...###....', // 4
    '...fWWW.....f#.##..#..#....###', // 3
    '.W.WWWWWWW.....###############', // 2
    '....W.WWWfWW.f...############.', // 1
  ],
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
  unconfirmed: [
    'The 3,000G is dropped by the lead Spear Fighter of a pair; the pairs at (13, 8) and (21, 8) are one Samurai pair and one Spear Fighter pair, but which is which isn\'t recorded.',
    'The darker brown ground on the west side is shown as wasteland.',
  ],
  sources: [
    { label: 'Fire Emblem Wiki minimaps', url: 'https://fireemblemwiki.org/wiki/Category:Fates_maps' },
    { label: "Fire Emblem Wiki: Another Trial", url: 'https://fireemblemwiki.org/wiki/Another_Trial' },
  ],
}

export const CONQUEST_10: ChapterMap = {
  id: 'fe14c-10',
  route: 'Conquest',
  chapter: 10,
  title: 'Unhappy Reunion',
  width: 26,
  height: 22,
  grid: [
    'B.BBBBBBB....B.BBBBBBBBBBB', // 22
    '.v.www........v...........', // 21
    '..........................', // 20
    '...www#.........##B##...##', // 19
    '###wwwB.......#wwwwwww.www', // 18
    '...www#.......#wwwwwww.www', // 17
    '...www........#wwwwwww.www', // 16
    '...wwwBBB......wwwwBBB....', // 15
    '...wwwBBB......wwwwBBB....', // 14
    '.##www.v.##B##.wwww.v.#...', // 13
    '.##www.........wwww...#...', // 12
    '......................#...', // 11
    '......................#...', // 10
    '...wwwwwwwwwwwwwwww...#...', // 9
    '...www#wwwwwwww#www...#...', // 8
    '...ww#.#wwwwww#.#ww...#...', // 7
    '...w#...#wwww#...#w...#...', // 6
    '...w#...#wwww#...#w...#...', // 5
    '........#wwww#........#...', // 4
    '........#wwww#........#...', // 3
    '...##...##ww##...##.......', // 2
    '...##...##ww##...##.......', // 1
  ],
  victory: 'Defend the green zone for 11 turns.',
  defeat: 'Corrin dies, your army is routed, or an enemy seizes any of the flashing green tiles.',
  objectives: [],
  units: [
    { type: 'boss', name: "Takumi", tile: [2, 2], drops: ["Elixir"] },
    ...commons("Hoshidan", [
        [1, 15], [1, 14], [25, 12], [5, 11], [18, 11], [25, 11], [4, 10], [6, 10],
        [17, 10], [3, 8], [21, 8], [6, 4], [8, 4], [15, 4], [8, 3], [17, 3],
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
      patch: tilesBecome('.', [
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
  unconfirmed: [
    'Which tiles make up the green zone.',
    'Oboro and Hinata (named) are among the starting enemies; their tiles aren\'t recorded.',
  ],
  sources: [
    { label: 'Fire Emblem Wiki minimaps', url: 'https://fireemblemwiki.org/wiki/Category:Fates_maps' },
    { label: "Fire Emblem Wiki: Unhappy Reunion", url: 'https://fireemblemwiki.org/wiki/Unhappy_Reunion' },
  ],
}

export const CONQUEST_11: ChapterMap = {
  id: 'fe14c-11',
  route: 'Conquest',
  chapter: 11,
  title: 'Rainbow Sage',
  width: 30,
  height: 30,
  grid: [
    'xxxxxxxxxxxxx.g.xxxxxxxxxxxxxx', // 30
    'xxxxxxxxxxxxx...xxxxxxxxxxxxxx', // 29
    'xxxxxxxxxxxx.x...xxxxxxxxxxxxx', // 28
    'xxxxxxxxxxx...x...xxxxxxxxxxxx', // 27
    'xxxxxxxxxx.........xxxxxxxxxxx', // 26
    'xxxxxxxxxxx.......xxxxxxxxxxxx', // 25
    'xxxxxxxxxxxx.....xxxxxxxxxxxxx', // 24
    'xxxxxxxxxxxxx...xxxxxxxxxxxxxx', // 23
    'xc.gg..xxxxxxxSxxxxxxxxxxxxxxx', // 22
    'x.....Sxxxxxxxxxxxxxxx..gg.cxx', // 21
    'x......xxxxxxxxxxxxxxx......xx', // 20
    'x......xxxxxxxxxxxxxxx......xx', // 19
    'x......xxxg...S...gxxx......xx', // 18
    'x......xxx.........xxx......xx', // 17
    'x......xxx.........xxx......xx', // 16
    'xS.....xxx.........xxx......xx', // 15
    'xxxxxxxxxx.........xxx......xx', // 14
    'xxxxxxxxxxS.......Sxxx......xx', // 13
    'xxxxxxxxxxxxxxxxxxxxxx.....Sxx', // 12
    'xx..gg..Sxxxxxxxxxxxxxxxxxxxxx', // 11
    'xx.......xxxxxxxxxxxxxxxxxxxxx', // 10
    'xx.......xxxxxxxxxxxxxxxxxxxxx', // 9
    'xx.......xxxxxxxxxS..gg..xxxxx', // 8
    'xx.......xxxxxxxx.........xxxx', // 7
    'xxS......xxxxxxxx.........xxxx', // 6
    'xxxxxxxxxxxxxxxxx.........xxxx', // 5
    'xxxxxxxxxxxxxxxxx.........xxxx', // 4
    'xxxxxxxxxxxxxxxxxx......Sxxxxx', // 3
    'x....S........S.xxxxxxxxxxxxxx', // 2
    'x...............xxxxxxxxxxxxxx', // 1
  ],
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
    { type: 'chest', tile: [2, 22], contents: 'Spirit Dust or Enfeeble' },
    { type: 'chest', tile: [28, 21], contents: 'Spirit Dust or Enfeeble' },
  ],
  changes: [],
  notes: ['Kaze joins at the end of the chapter.', "The chests are in Kaze's room (Spirit Dust) and Azama's room (Enfeeble)."],
  unconfirmed: [
    'Which gate holds Kaze and which holds Azama, and so which chest is which.',
    'How the staircase tiles link the platforms.',
    'Setsuna and Rinkah (named) are among the starting enemies; their tiles aren\'t recorded.',
  ],
  sources: [
    { label: 'Fire Emblem Wiki minimaps', url: 'https://fireemblemwiki.org/wiki/Category:Fates_maps' },
    { label: "Fire Emblem Wiki: Rainbow Sage", url: 'https://fireemblemwiki.org/wiki/Rainbow_Sage_(Conquest_chapter)' },
  ],
}

export const CONQUEST_6_TO_11: ChapterMap[] = [CONQUEST_6, CONQUEST_7, CONQUEST_8, CONQUEST_9, CONQUEST_10, CONQUEST_11]
