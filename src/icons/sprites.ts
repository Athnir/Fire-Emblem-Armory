/**
 * The app's own pixel-art icons, bundled as data so nothing depends on the device's emoji font.
 * Each sprite is 10×10: one string per row, one character per pixel, '.' = transparent, every other
 * character looked up in the sprite's palette. Map tiles are 10 units wide, so on the map one sprite
 * pixel = one unit.
 */
export interface Sprite {
  rows: string[]
  palette: Record<string, string>
}

const OUTLINE = '#2b2118'

export const PILLAR: Sprite = {
  palette: { o: '#4a4038', l: '#d8cfbf', m: '#a2978a', d: '#7c7266' },
  rows: [
    '..........',
    '.oooooooo.',
    '.olllllmo.',
    '..ollmdo..',
    '..ollmdo..',
    '..ollmdo..',
    '..ollmdo..',
    '..ollmdo..',
    '.oommmddo.',
    '.oooooooo.',
  ],
}

export const TREE: Sprite = {
  palette: { o: '#1f3d1a', g: '#3f7a32', h: '#6fae52', t: '#6b4a2a' },
  rows: [
    '....oo....',
    '...oghgo..',
    '..ogghggo.',
    '.ogghgggo.',
    '..oggggo..',
    '.ogghgggo.',
    'ogggggggo.',
    '.ooootooo.',
    '....tt....',
    '....tt....',
  ],
}

/** Fates' breakable pots, in the medicine (green) or poison (purple) colours. */
export function vase(body: string, shade: string, light: string): Sprite {
  return {
    palette: { o: OUTLINE, b: body, s: shade, l: light },
    rows: [
      '..........',
      '..oooooo..',
      '...obbo...',
      '..obbbbo..',
      '.olbbbbbo.',
      '.olbbbbso.',
      '.obbbbbso.',
      '..obbbso..',
      '...oooo...',
      '..........',
    ],
  }
}
export const VASE_MEDICINE = vase('#3fbf8f', '#23805c', '#a8f0d0')
export const VASE_POISON = vase('#a35fc9', '#6a3a88', '#dcb8f0')

/** Fort: a little rook. */
export const FORT: Sprite = {
  palette: { o: '#3d342b', s: '#9c948a', l: '#c9c1b6', d: '#5a5047' },
  rows: [
    '.ss.ss.ss.',
    '.slssslss.',
    '.ssssssss.',
    '..slsssd..',
    '..slssdd..',
    '..slsssd..',
    '..slsssd..',
    '.sslssssd.',
    '.oooooooo.',
    '..........',
  ],
}

export const GATE: Sprite = {
  palette: { o: '#3d342b', s: '#9c948a', l: '#c9c1b6', d: '#2e231a' },
  rows: [
    's.ss..ss.s',
    'ssssssssss',
    'sllssssss.',
    'sl.dddd.s.',
    'sldddddds.',
    'sldddddds.',
    'sldddddds.',
    'sldddddds.',
    'oooooooooo',
    '..........',
  ],
}

export const HOUSE: Sprite = {
  palette: { r: '#b5452f', R: '#7d2c1d', w: '#f0e6d2', d: '#6b4a2a', o: OUTLINE },
  rows: [
    '....rr....',
    '...rrrR...',
    '..rrrrrR..',
    '.rrrrrrrR.',
    'oooooooooo',
    '.wwwwwwww.',
    '.wwwddwww.',
    '.wwwddwww.',
    '.wwwddwww.',
    '.oooooooo.',
  ],
}

export const CHEST: Sprite = {
  palette: { o: '#3a240f', b: '#8a5a2b', l: '#b07a40', y: '#e3b341' },
  rows: [
    '..........',
    '..........',
    '.oooooooo.',
    '.ollllllo.',
    '.obbbbbbo.',
    '.ooooyooo.',
    '.obbbybbo.',
    '.obbbbbbo.',
    '.oooooooo.',
    '..........',
  ],
}

export const DOOR: Sprite = {
  palette: { o: '#3a240f', b: '#9a6a35', l: '#c08a4a', y: '#e3b341' },
  rows: [
    '..oooooo..',
    '.oblblbbo.',
    '.oblblbbo.',
    '.oblblbbo.',
    '.oblblyyo.',
    '.oblblbbo.',
    '.oblblbbo.',
    '.oblblbbo.',
    '.oblblbbo.',
    '.oooooooo.',
  ],
}

export const STAIRS: Sprite = {
  palette: { s: '#d6c39a', o: '#7d6a48' },
  rows: [
    '..........',
    '......ssss',
    '......oooo',
    '....ssssss',
    '....oooooo',
    '..ssssssss',
    '..oooooooo',
    'ssssssssss',
    'oooooooooo',
    '..........',
  ],
}

export const RUBBLE: Sprite = {
  palette: { o: '#2e2620', r: '#8a7a6a', l: '#b3a493' },
  rows: [
    '..........',
    '..........',
    '......oo..',
    '.....olro.',
    '..oo.orro.',
    '.olro.oo..',
    '.orrro.oo.',
    'oolrroolro',
    'orrrrrorro',
    'oooooooooo',
  ],
}

export const SNOW_PEAK: Sprite = {
  palette: { o: '#5a6b7a', w: '#ffffff', m: '#a9bccb', d: '#7f93a4' },
  rows: [
    '..........',
    '....oo....',
    '...owwo...',
    '..owwwmo..',
    '..owmmmo..',
    '.ommmmmdo.',
    '.ommmmddo.',
    'ommmmmmddo',
    'oooooooooo',
    '..........',
  ],
}

export const HEAL: Sprite = {
  palette: { w: '#effffb', o: '#1f7a6a' },
  rows: [
    '..........',
    '...oooo...',
    '...owwo...',
    '.ooowwooo.',
    '.owwwwwwo.',
    '.owwwwwwo.',
    '.ooowwooo.',
    '...owwo...',
    '...oooo...',
    '..........',
  ],
}

export const DRAGON_VEIN: Sprite = {
  palette: { o: '#0e5a66', c: '#36d3e8', l: '#b8f6ff', w: '#ffffff' },
  rows: [
    '....oo....',
    '...ocwo...',
    '..occlco..',
    '..oclcco..',
    '.occlccco.',
    '.occcwcco.',
    '..occcco..',
    '...occo...',
    '....oo....',
    '..........',
  ],
}

export const SKULL: Sprite = {
  palette: { o: '#3a0d0d', w: '#f1ece0', s: '#c9c0ae' },
  rows: [
    '..oooooo..',
    '.owwwwwwo.',
    'owwwwwwwso',
    'owoowwoowo',
    'owoowwoowo',
    'owwwoowwso',
    '.owwwwwso.',
    '..owowoo..',
    '..owwwwo..',
    '...oooo...',
  ],
}

/** A small soldier: green for allies, red for named enemies. */
export function figure(body: string, shade: string): Sprite {
  return {
    palette: { o: OUTLINE, b: body, s: shade, k: '#f1d3b0' },
    rows: [
      '...oooo...',
      '..obbbbo..',
      '..okkkko..',
      '...okko...',
      '..obbbbo..',
      '.obbbbbso.',
      '.okbbbsko.',
      '..obbbso..',
      '..obo.so..',
      '..oo..oo..',
    ],
  }
}
export const ALLY = figure('#3fa35a', '#226b38')
export const NAMED_ENEMY = figure('#c9443b', '#82241e')

/** Common foes are deliberately plain: they mark where an enemy is without competing for attention. */
export const COMMON_ENEMY: Sprite = {
  palette: { o: '#5a0f0f', r: '#d9443b', l: '#f08a80' },
  rows: [
    '..........',
    '..........',
    '...oooo...',
    '..orrrro..',
    '..orlrro..',
    '..orrrro..',
    '..orrrro..',
    '...oooo...',
    '..........',
    '..........',
  ],
}

/** Two common foes paired up on one tile. */
export const COMMON_PAIR: Sprite = {
  palette: { o: '#5a0f0f', r: '#d9443b', l: '#f08a80' },
  rows: [
    '.oooo.....',
    'orlrro....',
    'orrrro....',
    'orrrooooo.',
    '.ooorlrro.',
    '...orrrro.',
    '...orrrro.',
    '....oooo..',
    '..........',
    '..........',
  ],
}

/** A common foe carrying a droppable item: gold ring so it stands out from the plain ones. */
export const COMMON_DROPPER: Sprite = {
  palette: { y: '#e3b341', o: '#5a0f0f', r: '#d9443b', l: '#f08a80' },
  rows: [
    '..........',
    '..yyyyyy..',
    '.yoooooy..',
    '.yorrroy..',
    '.yorlroy..',
    '.yorrroy..',
    '.yoooooy..',
    '..yyyyyy..',
    '..........',
    '..........',
  ],
}

/** An enemy reinforcement: a hollow red ring, so arrivals read apart from the foes already on the map. */
export const REINFORCEMENT: Sprite = {
  palette: { o: '#5a0f0f', r: '#e0603a' },
  rows: [
    '..........',
    '...oooo...',
    '..orrrro..',
    '.oro..oro.',
    '.or....ro.',
    '.or....ro.',
    '.oro..oro.',
    '..orrrro..',
    '...oooo...',
    '..........',
  ],
}

/** A unit joining your army mid-chapter: a blue figure, the colour of your starting tiles. */
export const JOINER = figure('#3b82f6', '#1e4fa8')

/** Badge for "drops an item on defeat": a little gold sack, drawn in a tile's top-right corner. */
export const DROP_BADGE: Sprite = {
  palette: { o: '#3a240f', y: '#e3b341', l: '#fbe7a1', s: '#a8781f' },
  rows: [
    '..........',
    '...o..o...',
    '....oo....',
    '...oyyo...',
    '..oyyyyo..',
    '.oylyyyso.',
    '.oyyyyyso.',
    '.oyyyysso.',
    '..oooooo..',
    '..........',
  ],
}

/** Badge for a boss or named foe that can be captured: a coil of rope, drawn in the bottom-right corner. */
export const CAPTURE_BADGE: Sprite = {
  palette: { o: '#3a2a12', r: '#c9a066', l: '#ead2a0' },
  rows: [
    '..........',
    '...oooo...',
    '..orrlro..',
    '.oro..oro.',
    '.or....ro.',
    '.or....ro.',
    '.oro..oro.',
    '..orrrrooo',
    '...oooo.oo',
    '..........',
  ],
}

export const ALL_SPRITES = {
  PILLAR, TREE, VASE_MEDICINE, VASE_POISON, FORT, GATE, HOUSE, CHEST, DOOR, STAIRS, RUBBLE,
  SNOW_PEAK, HEAL, DRAGON_VEIN, SKULL, ALLY, NAMED_ENEMY, COMMON_ENEMY, COMMON_PAIR, COMMON_DROPPER, DROP_BADGE, CAPTURE_BADGE,
  REINFORCEMENT, JOINER,
}
