import type { ChapterMap, TerrainLetter, Tile } from './types'
import { commons, pairs } from './units'

const tilesBecome = (becomes: TerrainLetter, tiles: Tile[]) => tiles.map((tile) => ({ tile, becomes }))

/*
 * The shared chapters (Prologue to Chapter 5), before the route split. Grids are read off the Fire
 * Emblem Wiki minimaps at 6 px per tile; each Dragon Vein's patch is the difference between the
 * normal minimap and the wiki's after-vein ("_dv") minimap. Wiki chapter pages count rows from the
 * top, so their coordinates are converted to bottom-left (1, 1) here.
 */

export const PROLOGUE: ChapterMap = {
  id: 'fe14-prologue',
  route: 'Shared',
  chapter: 0,
  title: 'Ties That Bind',
  width: 20,
  height: 22,
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
  victory: 'Automatic at the end of player phase 2.',
  defeat: 'None.',
  objectives: [],
  units: [
    { type: 'boss', name: 'Xander', tile: [12, 16] },
    { type: 'named', name: "Nohrian royal or retainer", tile: [8, 8] },
    { type: 'named', name: "Nohrian royal or retainer", tile: [10, 5] },
    { type: 'named', name: "Nohrian royal or retainer", tile: [1, 18] },
    { type: 'named', name: "Nohrian royal or retainer", tile: [5, 5] },
    { type: 'named', name: "Nohrian royal or retainer", tile: [9, 6] },
    { type: 'named', name: "Nohrian royal or retainer", tile: [3, 20] },
    { type: 'named', name: "Nohrian royal or retainer", tile: [2, 19] },
    { type: 'named', name: "Nohrian royal or retainer", tile: [7, 9] },
    { type: 'named', name: "Nohrian royal or retainer", tile: [9, 5] },
    { type: 'named', name: "Nohrian royal or retainer", tile: [7, 6] },
    { type: 'named', name: "Nohrian royal or retainer", tile: [10, 6] },
    { type: 'named', name: "Nohrian royal or retainer", tile: [5, 6] },
    { type: 'named', name: "Nohrian royal or retainer", tile: [19, 12] },
    { type: 'named', name: "Nohrian royal or retainer", tile: [8, 5] },
    { type: 'ally', name: 'Hoshidan royal or retainer', tile: [20, 11] },
    { type: 'ally', name: 'Hoshidan royal or retainer', tile: [20, 10] },
    { type: 'ally', name: 'Hoshidan royal or retainer', tile: [20, 9] },
    { type: 'ally', name: 'Hoshidan royal or retainer', tile: [12, 6] },
    { type: 'ally', name: 'Hoshidan royal or retainer', tile: [12, 5] },
    { type: 'ally', name: 'Hoshidan royal or retainer', tile: [13, 5] },
    { type: 'ally', name: 'Hoshidan royal or retainer', tile: [15, 5] },
    { type: 'ally', name: 'Hoshidan royal or retainer', tile: [14, 4] },
    { type: 'ally', name: 'Hoshidan royal or retainer', tile: [13, 3] },
    { type: 'ally', name: 'Hoshidan royal or retainer', tile: [15, 3] },
    { type: 'ally', name: 'Hoshidan royal or retainer', tile: [12, 2] },
    { type: 'ally', name: 'Hoshidan royal or retainer', tile: [14, 2] },
    { type: 'ally', name: 'Hoshidan royal or retainer', tile: [16, 1] },
    { type: 'ally', name: 'Ryoma', tile: [11, 16] },
  ],
  starts: [[19, 11]],
  objects: [],
  changes: [
    {
      id: 'vein',
      trigger: 'dragonVein',
      // Wiki: column 6, row 6, three squares south of the northwestern bridge rubble.
      tile: { default: [6, 17] },
      usableBy: "Royals (Camilla uses it on enemy phase 1; Corrin can't reach it)",
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
    'Takumi joins on turn 2 and leaves after the chapter.',
    'The starting enemies are Xander, Camilla, Leo, Elise, Gunter, Flora, Peri, Keaton, Beruka, Nyx, Niles, Effie, Arthur, Benny and one generic soldier; the allies are Hoshido\'s royals and retainers.',
  ],
  unconfirmed: ['Which named Nohrian (or ally) stands on which tile.'],
  sources: [
    { label: 'Fire Emblem Wiki minimaps', url: 'https://fireemblemwiki.org/wiki/Category:Fates_maps' },
    { label: 'Fire Emblem Wiki: Ties That Bind', url: 'https://fireemblemwiki.org/wiki/Ties_That_Bind' },
  ],
}

export const CHAPTER_1: ChapterMap = {
  id: 'fe14-1',
  route: 'Shared',
  chapter: 1,
  title: 'Nohr',
  width: 13,
  height: 13,
  grid: [
    'xxxxxxxxxxxxx', // 13
    'xxxxxxxxxxxxx', // 12
    'xxxx.....xxxx', // 11
    'xxx.......xxx', // 10
    'xx.........xx', // 9
    'xx.........xx', // 8
    'xx.........xx', // 7
    'xx.........xx', // 6
    'xx.........xx', // 5
    'xxx.......xxx', // 4
    'xxxx.....xxxx', // 3
    'xxxxxxxxxxxxx', // 2
    'xxxxxxxxxxxxx', // 1
  ],
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
  terrainOverrides: { H: { heal: 50 } },
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
  grid: [
    '...............', // 15
    '...............', // 14
    '...............', // 13
    '...............', // 12
    '.pp.........pp.', // 11
    '...............', // 10
    '...............', // 9
    '.....rrrrr.....', // 8
    '.....rrrrr.....', // 7
    '.....rrrrr.....', // 6
    '.....rrrrr.....', // 5
    '.....rrrrr.....', // 4
    '...............', // 3
    '...............', // 2
    '.pp.........pp.', // 1
  ],
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
  grid: [
    'xxxxxxxxxxxxxxxx....', // 18
    'xxxxxx.xxxxxxxxx...f', // 17
    'bbbbb...bbb.xxxx..ff', // 16
    'xxxxx.f.xxx.bbbbF...', // 15
    'xxxxx...xxxxxxxx....', // 14
    'xxxxxxxbxxxxxxxx....', // 13
    'xxxxxxxbxxxxxxxxx...', // 12
    'xxxxxxxbxxxxxxxxxx.W', // 11
    'xxxxxxx..bbxxxxxxbWW', // 10
    'xxxxx....xxxxxxxxx.f', // 9
    'xxxx.....xxxxxxBBBfW', // 8
    'xxx.....fxxxxx.BBBff', // 7
    'bbbb.F...xxxx..BBB.f', // 6
    'xbbx..f..xxxb...G...', // 5
    'xxxxx...xxxxxx......', // 4
    'xxxxxxxxxxxxxxx..ff.', // 3
    'xxxxxxxx..xxxxxx....', // 2
    'xxxxxxbbF.bxxxxxf...', // 1
  ],
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
  unconfirmed: ['The dark tiles at (19, 10), (20, 10), (20, 11) and (20, 8) are recalled as wasteland, not checked in-game.'],
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
  grid: [
    '....ff..fff.ffffff', // 18
    'nnnnf....fnnnnnfff', // 17
    'nnnnff...fnnnnnnff', // 16
    'nnnn..ffffnnnnnnff', // 15
    'nnn..fnnnffnnnnfff', // 14
    'fff.fnnnnnfnnnff..', // 13
    'ff.fnnnnnnnff.....', // 12
    'fnfnnnnnnnnf.....f', // 11
    'nnffnnnnnnff.nnfff', // 10
    'nnnnfnnnnffnnnnnff', // 9
    'nnn.ffnn...nnnnnf.', // 8
    'nnnf..ff..ffnnnn..', // 7
    'nnnff....ffffnnBBB', // 6
    'f..fffnnnffff..BBB', // 5
    'f...ffnnnnff....v.', // 4
    '.....nnnnn........', // 3
    'f..fffnnnn........', // 2
    'fffffffff.........', // 1
  ],
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
  grid: [
    '...............', // 18
    '.##.........##.', // 17
    '.###......####.', // 16
    '.####.....###..', // 15
    '..##.......##..', // 14
    '..#....#.......', // 13
    '......###......', // 12
    '......###......', // 11
    '......##.......', // 10
    '.....#.........', // 9
    '.........##....', // 8
    '..##.....##.##.', // 7
    '.###......####.', // 6
    '.####.....####.', // 5
    '.##.........##.', // 4
    '##...........##', // 3
    '...............', // 2
    '...............', // 1
  ],
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
  unconfirmed: ['Which Mercenary drops the HP Tonic (its tile isn\'t recorded).'],
  terrainOverrides: { '#': { name: 'Building rubble' } },
  sources: [
    { label: 'Fire Emblem Wiki minimaps', url: 'https://fireemblemwiki.org/wiki/Category:Fates_maps' },
    { label: 'Fire Emblem Wiki: Mother', url: 'https://fireemblemwiki.org/wiki/Mother' },
  ],
}

export const SHARED_MAPS: ChapterMap[] = [PROLOGUE, CHAPTER_1, CHAPTER_2, CHAPTER_3, CHAPTER_4, CHAPTER_5]
