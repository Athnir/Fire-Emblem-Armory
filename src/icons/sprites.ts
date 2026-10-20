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
  palette: { o: '#3a240f', y: '#e3b341', l: '#fbe7a1', s: '#a8781f', t: '#c98a2b' },
  rows: [
    '..........',
    '...t..t...',
    '....tt....',
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

/* Weapon notes: what a weapon is effective against, and its special rules. */

/** A knight's helm: effective against armoured units. */
export const ARMOR_HELM: Sprite = {
  palette: { o: '#2b2b33', l: '#e4e6ea', m: '#a9aeb8', d: '#6f7480', k: '#1a1a20' },
  rows: [
    '...oooo...',
    '..ollmmo..',
    '.ollmmmdo.',
    '.olmmmmdo.',
    '.okkkkkko.',
    '.ommmmmdo.',
    '.omdmdmdo.',
    '.ommmmmdo.',
    '..oddddo..',
    '...oooo...',
  ],
}

/** A dragon's head: effective against dragons. */
export const DRAGON_HEAD: Sprite = {
  palette: { o: '#1d2e1a', g: '#5c9a3c', h: '#c9b77a', y: '#f2d24b', w: '#f4f1e6' },
  rows: [
    'oo........',
    '.ohoo.....',
    '..oggooo..',
    '.ogyggggo.',
    '.ogggggggo',
    '.oggggwwwo',
    '.oggoooooo',
    '.oggwwwo..',
    '..ogggggo.',
    '...ooooo..',
  ],
}

/** A wing: effective against fliers. */
export const WING: Sprite = {
  palette: { o: '#3a3f4a', l: '#f6f7fb', s: '#b9c0cf' },
  rows: [
    '.......oo.',
    '.....oollo',
    '...oollllo',
    '.oolllllo.',
    'olllllllo.',
    'olslslslo.',
    '.olslslo..',
    '..olslo...',
    '...ooo....',
    '..........',
  ],
}

/** A horse's head: effective against mounted units (and, in Fates, beasts). */
export const HORSE_HEAD: Sprite = {
  palette: { o: '#2a1a0e', b: '#a5703f', m: '#4a2f17', y: '#111111', n: '#7a5030' },
  rows: [
    '....o.o...',
    '...obobo..',
    '..obbbbmo.',
    '.obybbbmo.',
    'obbbbbbbmo',
    'onbbbbbbmo',
    '.oobbbbbmo',
    '...obbbbmo',
    '...obbbbbo',
    '...ooooooo',
  ],
}

/** A horned mask: effective against monsters (Faceless, Stoneborn and the like). */
export const MONSTER: Sprite = {
  palette: { o: '#22142c', p: '#7b4fa3', y: '#f6e05e', w: '#efe7d3' },
  rows: [
    '.o......o.',
    '.oo....oo.',
    '..oooooo..',
    '.oppppppo.',
    '.oyyppyyo.',
    '.oppppppo.',
    '.opwpwpwo.',
    '..oppppo..',
    '...oooo...',
    '..........',
  ],
}

/** A sword: effective against sword users. */
export const SWORD_ICON: Sprite = {
  palette: { s: '#5c6370', l: '#e8ebf0', g: '#d4a72c', b: '#7a4e25' },
  rows: [
    '....ls....',
    '....ls....',
    '....ls....',
    '....ls....',
    '....ls....',
    '..gggggg..',
    '....bb....',
    '....bb....',
    '....gg....',
    '..........',
  ],
}

/** A lance: effective against lance users. */
export const LANCE_ICON: Sprite = {
  palette: { s: '#5c6370', l: '#e8ebf0', b: '#8a5a2b' },
  rows: [
    '....ss....',
    '...slls...',
    '..slllls..',
    '..ssssss..',
    '....bb....',
    '....bb....',
    '....bb....',
    '....bb....',
    '....bb....',
    '....bb....',
  ],
}

/** A double-headed axe: effective against axe users. */
export const AXE_ICON: Sprite = {
  palette: { s: '#5c6370', l: '#e8ebf0', b: '#8a5a2b' },
  rows: [
    '....bb....',
    'ss..bb..ss',
    'slssbbssls',
    'sllsbbslls',
    'slssbbssls',
    'ss..bb..ss',
    '....bb....',
    '....bb....',
    '....bb....',
    '....bb....',
  ],
}

/** A tome: effective against tome users. */
export const TOME_ICON: Sprite = {
  palette: { o: '#2a1610', r: '#a8322a', y: '#e8c14a', p: '#efe6cf' },
  rows: [
    '..........',
    '.oooooooo.',
    '.orrrrrpo.',
    '.orryrrpo.',
    '.oryyyrpo.',
    '.orryrrpo.',
    '.orrrrrpo.',
    '.oooooooo.',
    '..........',
    '..........',
  ],
}

/** A magic sparkle: the weapon hits with Magic against Resistance. */
export const MAGIC: Sprite = {
  palette: { p: '#8b6cf0', l: '#efeaff' },
  rows: [
    '....pp....',
    '....pp....',
    '...pllp...',
    'pppllllppp',
    'pppllllppp',
    '...pllp...',
    '....pp....',
    '....pp....',
    '..........',
    '..........',
  ],
}

/** An upside-down triangle: reverses the weapon triangle (and doubles its effects). */
export const REVERSED_TRIANGLE: Sprite = {
  palette: { o: '#0f3b44', c: '#38c6d9', l: '#a6eef7' },
  rows: [
    'oooooooooo',
    'olccccccco',
    '.occcccco.',
    '.occcccco.',
    '..occcco..',
    '..occcco..',
    '...occo...',
    '...occo...',
    '....oo....',
    '..........',
  ],
}

/** A crit spark crossed out: can't land critical hits. */
export const NO_CRIT: Sprite = {
  palette: { r: '#e0453a', y: '#f2c94c' },
  rows: [
    '...rrrr...',
    '.rr....rr.',
    '.r..y.rrr.',
    'r..yyrr..r',
    'r.yyrryy.r',
    'r..rryy..r',
    'r.rr.y...r',
    '.rrr....r.',
    '.rr....rr.',
    '...rrrr...',
  ],
}

/** Two strikes with the second crossed out: can't make a follow-up attack. */
export const NO_FOLLOW_UP: Sprite = {
  palette: { w: '#e5e7eb', d: '#6b7280', r: '#e0453a' },
  rows: [
    '..........',
    '.ww...dd..',
    '..ww...dd.',
    '...ww...dd',
    '..ww..dd..',
    '.ww..dd...',
    '......r..r',
    '.......rr.',
    '.......rr.',
    '......r..r',
  ],
}

/** A gold ×2: the Brave weapons' two hits in a row (in Fates only when it starts the fight). */
export const BRAVE: Sprite = {
  palette: { y: '#e8c14a' },
  rows: [
    '..........',
    '.......yy.',
    'y...y.y..y',
    '.y.y.....y',
    '..y.....y.',
    '.y.y...y..',
    'y...y.y...',
    '......yyyy',
    '..........',
    '..........',
  ],
}

/** A red up-arrow: the weapon's Mt doubles (on counterattacks, when attacking, or when Skill is higher). */
export const MIGHT_UP: Sprite = {
  palette: { o: '#4a0f0c', r: '#e0453a' },
  rows: [
    '....oo....',
    '...orro...',
    '..orrrro..',
    '.orrrrrro.',
    'oooorroooo',
    '...orro...',
    '...orro...',
    '...orro...',
    '...orro...',
    '...oooo...',
  ],
}

/** A crack: a wall or partition that can be attacked down. Light, so it shows on dark wall tiles. */
export const CRACK: Sprite = {
  palette: { l: '#f1e3c2', d: '#1c1712' },
  rows: [
    '....l.....',
    '....ld....',
    '...ld.....',
    '...lld....',
    '.....ld...',
    '......lld.',
    '.....ld...',
    '....ld....',
    '..lld.....',
    '..........',
  ],
}

/** A paw print: effective against laguz (Path of Radiance's beast, bird and dragon tribes). */
export const PAW: Sprite = {
  palette: { b: '#d39a5c' },
  rows: [
    '..bb..bb..',
    '..bb..bb..',
    'bb......bb',
    'bb......bb',
    '...bbbb...',
    '..bbbbbb..',
    '..bbbbbb..',
    '...bbbb...',
    '..........',
    '..........',
  ],
}

/** A lion's face in its mane: effective against beast laguz (Path of Radiance). */
export const LION_HEAD: Sprite = {
  palette: { m: '#9a4d1c', f: '#e8b04a', e: '#1a1208', n: '#5a2e14' },
  rows: [
    '..mmmmmm..',
    '.mmmmmmmm.',
    'mmmffffmmm',
    'mmffffffmm',
    'mfeffffefm',
    'mffffffffm',
    'mmffnnffmm',
    '.mmfnnfmm.',
    '..mmffmm..',
    '...mmmm...',
  ],
}

/** A grey boulder: rolls down a fixed path when set off (Path of Radiance Ch.25). */
export const BOULDER: Sprite = {
  palette: { o: '#2b2724', g: '#8a8580', l: '#c4beb6', d: '#5e5954' },
  rows: [
    '..........',
    '...oooo...',
    '..ollggo..',
    '.ollgggdo.',
    '.olggggdo.',
    '.oggggddo.',
    '.ogggdddo.',
    '..odddoo..',
    '...ooo....',
    '..........',
  ],
}

/** A gold glint: something buried here to dig up. */
export const BURIED: Sprite = {
  palette: { y: '#c2410c', w: '#fff7ed' },
  rows: [
    '....y.....',
    '....y.....',
    '...ywy....',
    'yyywwwyyy.',
    '...ywy....',
    '....y...y.',
    '....y..ywy',
    '........y.',
    '..........',
    '..........',
  ],
}

export const ALL_SPRITES = {
  PILLAR, TREE, VASE_MEDICINE, VASE_POISON, FORT, GATE, HOUSE, CHEST, DOOR, STAIRS, RUBBLE,
  SNOW_PEAK, HEAL, DRAGON_VEIN, SKULL, ALLY, NAMED_ENEMY, COMMON_ENEMY, COMMON_PAIR, DROP_BADGE, CAPTURE_BADGE,
  REINFORCEMENT, JOINER,
  ARMOR_HELM, DRAGON_HEAD, WING, HORSE_HEAD, MONSTER, SWORD_ICON, LANCE_ICON, AXE_ICON, TOME_ICON, MAGIC, REVERSED_TRIANGLE, NO_CRIT, NO_FOLLOW_UP,
  BRAVE, MIGHT_UP, CRACK, PAW, LION_HEAD, BOULDER, BURIED,
}
