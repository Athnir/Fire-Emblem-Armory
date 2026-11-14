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

/** Castle (Genealogy of the Holy War): two towers and a keep with a flag. */
export const CASTLE: Sprite = {
  palette: { o: '#3d342b', s: '#9c948a', l: '#c9c1b6', d: '#2e231a', r: '#c0392b' },
  rows: [
    '....lrr...',
    '....l.....',
    's.s.ll.s.s',
    'sss.ls.sss',
    'slssssssds',
    'slsssssssd',
    'slssddsssd',
    'slssddsssd',
    'oooooooooo',
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

/** Rubble no unit crosses: ruins, a broken column's stub and a fallen block of its stone (the user: the old rock pile read as
 * mountains). */
export const RUBBLE: Sprite = {
  palette: { o: '#3a3028', l: '#d2c6ae', m: '#a89b84', d: '#7a6e5c' },
  rows: [
    '..........',
    '.ooo......',
    '.olmo.....',
    '.olmo.....',
    '.olmo..oo.',
    '.olmd.olmo',
    'oolmdoolmo',
    'ollmmmoddo',
    'odddoddddo',
    'oooooooooo',
  ],
}

/** A cherry tree no unit passes (Fates' Hoshidan gardens, the game's "Cherry Tree"): a crown of pink blossom on its trunk. */
export const CHERRY_TREE: Sprite = {
  palette: { o: '#4a2a3a', p: '#f2a6c4', P: '#d9789e', w: '#ffe0ec', t: '#5a3a26' },
  rows: [
    '...oooo...',
    '..owppPo..',
    '.owpppPPo.',
    'opppwpPPPo',
    'oPpppppPPo',
    '.oPPpPPPo.',
    '..ooottoo.',
    '....otto..',
    '....otto..',
    '...oooooo.',
  ],
}

/** A mountain (grey rock like the peaks, without their snowcaps, lit on its left): every map's but a snowy one's, which keeps the
 * snowy peak (the user's call). */
export const MOUNTAIN: Sprite = {
  palette: { o: '#3f3a36', l: '#aaa196', m: '#8a8178', d: '#5f5850' },
  rows: [
    '..........',
    '....oo....',
    '...olmo...',
    '..ollmmo..',
    '..olmmdo..',
    '.ollmmmdo.',
    '.olmmdmdo.',
    'ollmmmmddo',
    'oooooooooo',
    '..........',
  ],
}

/** A fire trap's tile as the game draws it: cracked lava, crust plates split by glowing cracks (the user's call; it flares on its
 * turns). */
export const LAVA_CRACK: Sprite = {
  palette: { k: '#3a1410', c: '#5e2117', r: '#8e3518', y: '#a8692c' },
  rows: [
    'ckkkrckkkc',
    'kckkrkkckk',
    'kkkryrrrkk',
    'rrrykckyrr',
    'kckrkkkrkc',
    'kkkrkckrkk',
    'ckryrrryck',
    'krrkkckkrr',
    'kkrkckkkrk',
    'ckrkkkckrc',
  ],
}

/** Barrels (the GBA games' ships and storehouses): a banded wooden barrel, standing on the ground around it. */
export const BARREL: Sprite = {
  palette: { o: '#3b2614', w: '#a0703c', W: '#7a5128', l: '#c99a5e', b: '#55565c' },
  rows: [
    '...oooo...',
    '..owlwWo..',
    '.obbbbbbo.',
    '.owlwwWWo.',
    '.owlwwWWo.',
    '.owlwwWWo.',
    '.obbbbbbo.',
    '..owlwWo..',
    '...oooo...',
    '..........',
  ],
}

/** A door mat (the user's call): where a unit visits a house of a town (the Tellius games'), in front of its door, in place of a
 * little house that would sit oddly before a whole house. */
export const DOOR_MAT: Sprite = {
  palette: { o: '#4a2a18', r: '#a8432a', y: '#d9a441', f: '#e0cfa0' },
  rows: [
    '..........',
    '..........',
    '.oooooooo.',
    'forrrrrrof',
    'foryyyyrof',
    'forrrrrrof',
    '.oooooooo.',
    '..........',
    '..........',
    '..........',
  ],
}

/** Bones (the GBA games' deserts): two crossed bones, no skull, so they're never a boss's marker. */
export const BONES: Sprite = {
  palette: { o: '#5a5246', b: '#efe9d8', s: '#c9c0a8' },
  rows: [
    '.oo....oo.',
    'obbo..obbo',
    'obso..obso',
    '.oobooboo.',
    '...obbo...',
    '...obso...',
    '.ooboosoo.',
    'obbo..obbo',
    'obso..obso',
    '.oo....oo.',
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

/** A boss arriving later: the boss's skull outlined in the reinforcement ring's orange. */
export const BOSS_REINFORCEMENT: Sprite = { ...SKULL, palette: { ...SKULL.palette, o: '#c2410c' } }

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
/** A named partner unit (Path of Radiance's army 3): the ally's figure in yellow. */
export const PARTNER = figure('#e2b93b', '#8a6a12')
export const NAMED_ENEMY = figure('#c9443b', '#82241e')
/** A named foe arriving later: the named foe's figure in the reinforcement ring's orange. */
export const NAMED_REINFORCEMENT = figure('#e0603a', '#9a3412')

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

/** A generic green unit (another army's soldier, a horse): plain, like a common foe. The person icon is kept
 * for named green units, to draw the eye to them. */
export const COMMON_ALLY: Sprite = {
  palette: { o: '#0f4a1f', r: '#3fa35a', l: '#8fdc9f' },
  rows: COMMON_ENEMY.rows,
}

/** A partner unit with no name of its own: a plain yellow dot. */
export const COMMON_PARTNER: Sprite = {
  palette: { o: '#5a4505', r: '#e2b93b', l: '#f7e08a' },
  rows: COMMON_ENEMY.rows,
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

/** Badge for a foe holding something rare you can take from it but it doesn't drop (a thief's Steal, or a capture): a cut gem,
 * drawn in the top-left corner. */
export const STEAL_BADGE: Sprite = {
  palette: { o: '#3d1238', l: '#ffe1f7', c: '#e45bc9', d: '#9c2d8c' },
  rows: [
    '..........',
    '..oooooo..',
    '.olllccdo.',
    'olccccccdo',
    'oooooooooo',
    '.occccddo.',
    '..occcdo..',
    '...ocdo...',
    '....oo....',
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

/** Grima: a horned purple head with its six red eyes, effective against Grima (Awakening's Falchions), apart from the dragons' head. */
export const GRIMA: Sprite = {
  palette: { k: '#1a0b24', p: '#4c1d95', r: '#ef4444' },
  rows: [
    'k........k',
    'kk......kk',
    '.kkkkkkkk.',
    '.kprpprpk.',
    '.kppppppk.',
    '.kprpprpk.',
    '.kppppppk.',
    '.kprpprpk.',
    '..kppppk..',
    '...kkkk...',
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

/** A cracked stretch of wall: effective against breakable doors and walls (Path of Radiance's axes). */
export const BREACH: Sprite = {
  palette: { o: '#2b2b33', s: '#a9a39a', l: '#d8d2c6', d: '#6d675f', k: '#1a1a20' },
  rows: [
    'oooooooooo',
    'olslskslso',
    'oddddkdddo',
    'oslskslslo',
    'odddkddddo',
    'oslkslslso',
    'oddkdddddo',
    'oslskslslo',
    'oddddkdddo',
    'oooooooooo',
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
/** A change the chapter's script makes to the map (the user: apart from a wall you break, so the two can't be mixed up): a gold
 * star burst on its tile, tap it for what changes and when. */
export const MAP_EVENT: Sprite = {
  palette: { o: '#2a2112', y: '#f2c94c', w: '#fff3c4' },
  rows: [
    '....o.....',
    '...oyo....',
    '.o.oyo.o..',
    '.oyoyoyo..',
    '..oywwyo..',
    'ooyywwyyoo',
    '..oyyyyo..',
    '.oyo.oyo..',
    '.oo...oo..',
    '..........',
  ],
}

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

/** A shiny spot (Fates' challenge battles): an eight-rayed cyan sparkle, apart from the orange glint of something buried. */
export const SHINY: Sprite = {
  palette: { c: '#22d3ee', w: '#ecfeff' },
  rows: [
    '....c.....',
    '.c..c..c..',
    '..c.c.c...',
    '...cwc....',
    'cccwwwccc.',
    '...cwc....',
    '..c.c.c...',
    '.c..c..c..',
    '....c.....',
    '..........',
  ],
}

/** An event tile (Awakening): the question-mark bubble the game shows over a unit that stops on one. */
export const EVENT_TILE: Sprite = {
  palette: { b: '#facc15', q: '#1c1917' },
  rows: [
    '.bbbbbbb..',
    'bbbqqqbbb.',
    'bbqbbbqbb.',
    'bbbbbbqbb.',
    'bbbbbqbbb.',
    'bbbbqbbbb.',
    'bbbbbbbbb.',
    '.bbbqbbb..',
    '...bb.....',
    '...b......',
  ],
}

/** A ballista: a wooden frame with a drawn bow and a bolt laid on it. */
export const BALLISTA: Sprite = {
  palette: { o: '#2b1d10', w: '#9a6b3a', l: '#d9b27a', s: '#cbd5e1' },
  rows: [
    '..o....o..',
    '.ol....lo.',
    'ol..ss..lo',
    'o..oswo..o',
    '...owwo...',
    '..oowwoo..',
    '..owwwwo..',
    '.ow.ww.wo.',
    '.o..oo..o.',
    '..........',
  ],
}

/** A house on fire (Radiant Dawn Part 3 Ch.9's arson): flames alone, unlike the torch on its stick. */
export const FLAME: Sprite = {
  palette: { o: '#7c2d12', r: '#ea580c', y: '#fde047', w: '#fef9c3' },
  rows: [
    '....o.....',
    '...oro..o.',
    '...orro.ro',
    '..orrro.ro',
    '.orryrrorr',
    '.orryyrrro',
    'orryywyrro',
    'orryywyyro',
    '.orryyyro.',
    '..oooooo..',
  ],
}

/** A gas vent (The Blazing Blade's and The Sacred Stones' traps): purple gas puffing up from an iron grate. */
export const GAS_VENT: Sprite = {
  palette: { o: '#3f3f46', d: '#18181b', p: '#6b21a8', g: '#c084fc' },
  rows: [
    '..pp..pp..',
    '.pggppggp.',
    '..pggggp..',
    '...pggp...',
    '....pp....',
    '.oooooooo.',
    '.odododoo.',
    '.oooooooo.',
    '.odododoo.',
    '.oooooooo.',
  ],
}

/** An arrow launcher (The Sacred Stones' Tower): an arrow rising from its slot in the floor. */
export const ARROW_TRAP: Sprite = {
  palette: { w: '#e5e7eb', b: '#92400e', f: '#dc2626', o: '#3f3f46', d: '#18181b' },
  rows: [
    '....w.....',
    '...www....',
    '..wwwww...',
    '....b.....',
    '....b.....',
    '...fbf....',
    '..f.b.f...',
    '..f.b.f...',
    '.oooooooo.',
    '.oddddddo.',
  ],
}

/** Radiant Dawn's Tower floors: a healing ring, and three shields for Def, Def x2 and Res. */
export const HEAL_FLOOR: Sprite = {
  palette: { o: '#14532d', g: '#4ade80', w: '#f0fdf4' },
  rows: [
    '..oooooo..',
    '.oggggggo.',
    'oggowwoggo',
    'oggowwoggo',
    'ogwwwwwwgo',
    'ogwwwwwwgo',
    'oggowwoggo',
    'oggowwoggo',
    '.oggggggo.',
    '..oooooo..',
  ],
}
/** The Tower's Defense, strong Defense and Resistance floors (Radiant Dawn's Endgame), as patterns laid in its flagstone rather than
 * an icon on each tile (the user: with nearly every tile one, icons were too busy). Each joins its neighbours edge to edge; a map
 * takes its own design for each kind (`floorPattern`). */
export const FLOOR_PATTERNS: Record<'def' | 'def2' | 'res', Sprite[]> = {
  def: [
    {
      palette: { t: 'rgba(222, 228, 234, 0.5)', l: 'rgba(255, 255, 255, 0.16)' },
      rows: [
        '....tt....',
        '...tllt...',
        '..tl..lt..',
        '.tl....lt.',
        'tl......lt',
        'tl......lt',
        '.tl....lt.',
        '..tl..lt..',
        '...tllt...',
        '....tt....',
      ],
    },
    {
      palette: { t: 'rgba(222, 228, 234, 0.5)', l: 'rgba(255, 255, 255, 0.16)' },
      rows: [
        'l........l',
        '.tttttttt.',
        '.t......t.',
        '.t......t.',
        '.t......t.',
        '.t......t.',
        '.t......t.',
        '.t......t.',
        '.tttttttt.',
        'l........l',
      ],
    },
    {
      palette: { t: 'rgba(222, 228, 234, 0.5)', l: 'rgba(255, 255, 255, 0.16)' },
      rows: [
        '....tl....',
        '....tl....',
        '....tl....',
        '....tl....',
        'tttttttttt',
        'lllltlllll',
        '....tl....',
        '....tl....',
        '....tl....',
        '....tl....',
      ],
    },
    {
      palette: { t: 'rgba(222, 228, 234, 0.5)', l: 'rgba(255, 255, 255, 0.16)' },
      rows: [
        '.t......t.',
        'tt..tt..tt',
        '..tt..tt..',
        '..t....t..',
        '.t......t.',
        '.t......t.',
        '..t....t..',
        '..tt..tt..',
        'tt..tt..tt',
        '.t......t.',
      ],
    },
    {
      palette: { t: 'rgba(222, 228, 234, 0.5)', l: 'rgba(255, 255, 255, 0.16)' },
      rows: [
        'tl...tl...',
        'l...tl...t',
        '...tl...tl',
        '..tl...tl.',
        '.tl...tl..',
        'tl...tl...',
        'l...tl...t',
        '...tl...tl',
        '..tl...tl.',
        '.tl...tl..',
      ],
    },
  ],
  def2: [
    {
      palette: { t: 'rgba(241, 210, 122, 0.6)', l: 'rgba(255, 255, 255, 0.16)' },
      rows: [
        '....tt....',
        '...tllt...',
        '..tl..lt..',
        '.tl....lt.',
        'tl......lt',
        'tl......lt',
        '.tl....lt.',
        '..tl..lt..',
        '...tllt...',
        '....tt....',
      ],
    },
    {
      palette: { t: 'rgba(241, 210, 122, 0.6)', l: 'rgba(255, 255, 255, 0.16)' },
      rows: [
        'l........l',
        '.tttttttt.',
        '.t......t.',
        '.t......t.',
        '.t......t.',
        '.t......t.',
        '.t......t.',
        '.t......t.',
        '.tttttttt.',
        'l........l',
      ],
    },
    {
      palette: { t: 'rgba(241, 210, 122, 0.6)', l: 'rgba(255, 255, 255, 0.16)' },
      rows: [
        '....tl....',
        '....tl....',
        '....tl....',
        '....tl....',
        'tttttttttt',
        'lllltlllll',
        '....tl....',
        '....tl....',
        '....tl....',
        '....tl....',
      ],
    },
    {
      palette: { t: 'rgba(241, 210, 122, 0.6)', l: 'rgba(255, 255, 255, 0.16)' },
      rows: [
        '.t......t.',
        'tt..tt..tt',
        '..tt..tt..',
        '..t....t..',
        '.t......t.',
        '.t......t.',
        '..t....t..',
        '..tt..tt..',
        'tt..tt..tt',
        '.t......t.',
      ],
    },
    {
      palette: { t: 'rgba(241, 210, 122, 0.6)', l: 'rgba(255, 255, 255, 0.16)' },
      rows: [
        'tl...tl...',
        'l...tl...t',
        '...tl...tl',
        '..tl...tl.',
        '.tl...tl..',
        'tl...tl...',
        'l...tl...t',
        '...tl...tl',
        '..tl...tl.',
        '.tl...tl..',
      ],
    },
  ],
  res: [
    {
      palette: { t: 'rgba(206, 168, 242, 0.55)', l: 'rgba(255, 255, 255, 0.16)' },
      rows: [
        '....tt....',
        '...tllt...',
        '..tl..lt..',
        '.tl....lt.',
        'tl......lt',
        'tl......lt',
        '.tl....lt.',
        '..tl..lt..',
        '...tllt...',
        '....tt....',
      ],
    },
    {
      palette: { t: 'rgba(206, 168, 242, 0.55)', l: 'rgba(255, 255, 255, 0.16)' },
      rows: [
        'l........l',
        '.tttttttt.',
        '.t......t.',
        '.t......t.',
        '.t......t.',
        '.t......t.',
        '.t......t.',
        '.t......t.',
        '.tttttttt.',
        'l........l',
      ],
    },
    {
      palette: { t: 'rgba(206, 168, 242, 0.55)', l: 'rgba(255, 255, 255, 0.16)' },
      rows: [
        '....tl....',
        '....tl....',
        '....tl....',
        '....tl....',
        'tttttttttt',
        'lllltlllll',
        '....tl....',
        '....tl....',
        '....tl....',
        '....tl....',
      ],
    },
    {
      palette: { t: 'rgba(206, 168, 242, 0.55)', l: 'rgba(255, 255, 255, 0.16)' },
      rows: [
        '.t......t.',
        'tt..tt..tt',
        '..tt..tt..',
        '..t....t..',
        '.t......t.',
        '.t......t.',
        '..t....t..',
        '..tt..tt..',
        'tt..tt..tt',
        '.t......t.',
      ],
    },
    {
      palette: { t: 'rgba(206, 168, 242, 0.55)', l: 'rgba(255, 255, 255, 0.16)' },
      rows: [
        'tl...tl...',
        'l...tl...t',
        '...tl...tl',
        '..tl...tl.',
        '.tl...tl..',
        'tl...tl...',
        'l...tl...t',
        '...tl...tl',
        '..tl...tl.',
        '.tl...tl..',
      ],
    },
  ],
}

/** The Tower's Defense and Resistance floors (Radiant Dawn), as the game draws them: the hall's own flagstone with an emblem inlaid in a
 * carved square (the user's call: the floor's colour and texture, not a big shield). Drawn over the map's floor colour, so the carving
 * is a shade of it: a silver shield (Def +10), a gold one (Def +15), a violet rune (Res). */
const SIGIL_PALETTE = { d: 'rgba(0,0,0,0.22)', l: 'rgba(255,255,255,0.2)', o: 'rgba(0,0,0,0.42)' }
export const DEF_SIGIL: Sprite = {
  palette: { ...SIGIL_PALETTE, s: '#dfe3e8', S: '#a9b0b8' },
  rows: [
    '..........',
    '.dddddddd.',
    '.d......l.',
    '.d.osso.l.',
    '.d.osSo.l.',
    '.d.osSo.l.',
    '.d..oo..l.',
    '.d......l.',
    '.dllllllll',
    '..........',
  ],
}
export const DEF2_SIGIL: Sprite = {
  palette: { ...SIGIL_PALETTE, s: '#f1d27a', S: '#b8902e' },
  rows: [
    '..........',
    '.dddddddd.',
    '.d......l.',
    '.d.osso.l.',
    '.d.oSSo.l.',
    '.d.osSo.l.',
    '.d..oo..l.',
    '.d......l.',
    '.dllllllll',
    '..........',
  ],
}
export const RES_SIGIL: Sprite = {
  palette: { ...SIGIL_PALETTE, v: '#cfa8f2', V: '#8e5cc4' },
  rows: [
    '..........',
    '.dddddddd.',
    '.d......l.',
    '.d..ov..l.',
    '.d.ovVv.l.',
    '.d..vVo.l.',
    '.d...o..l.',
    '.d......l.',
    '.dllllllll',
    '..........',
  ],
}

export const DEF_FLOOR: Sprite = {
  palette: { o: '#1f2937', l: '#e5e7eb', m: '#9ca3af', d: '#6b7280' },
  rows: [
    '.oooooooo.',
    '.ollllmmo.',
    '.olllmmmo.',
    '.ollmmmdo.',
    '.ollmmmdo.',
    '.olmmmddo.',
    '..ommmdo..',
    '..ommddo..',
    '...oddo...',
    '....oo....',
  ],
}
export const DEF2_FLOOR: Sprite = {
  palette: { o: '#713f12', y: '#fde047', g: '#ca8a04', d: '#854d0e' },
  rows: [
    '.oooooooo.',
    '.oyyyyygo.',
    '.oddddddo.',
    '.oyyyyggo.',
    '.oddddddo.',
    '.oyyyggdo.',
    '..oyyggo..',
    '..oyggdo..',
    '...oggo...',
    '....oo....',
  ],
}
export const RES_FLOOR: Sprite = {
  palette: { o: '#3b0764', v: '#a855f7', l: '#e9d5ff', w: '#ffffff' },
  rows: [
    '.oooooooo.',
    '.ovvvvvvo.',
    '.ovvwvvvo.',
    '.ovwwwvvo.',
    '.ovvwvvvo.',
    '.ovvvvlvo.',
    '..ovvvlo..',
    '..ovvllo..',
    '...ovlo...',
    '....oo....',
  ],
}

/** Burning ground (Radiant Dawn Part 3 Ch.8): low flames licking up from glowing cracks in the floor, unlike
 * the single tall flame of a burning house. */
export const BURNING_GROUND: Sprite = {
  palette: { o: '#7c2d12', r: '#ea580c', y: '#fde047', k: '#451a03' },
  rows: [
    '..........',
    '.o....o...',
    '.ro..oro..',
    'ory.oryro.',
    'oryroyyrro',
    'ryyyyyyyyr',
    'kkrkkkrkkk',
    'kyykkkkyyk',
    'kkkkyykkkk',
    'kkkkkkkkkk',
  ],
}

/** Bamboo spikes: three sharpened stakes, cut on the slant, standing out of the ground. */
export const SPIKES: Sprite = {
  palette: { g: '#a3b86c', d: '#5f7a2e', k: '#5b4a2a' },
  rows: [
    '..........',
    '.g...g....',
    '.gg..gg..g',
    '.gd..gd..g',
    '.gd..gd.gg',
    '.gd..gd.gd',
    '.gd..gd.gd',
    '.gd..gd.gd',
    'kkkkkkkkkk',
    '..........',
  ],
}

/** Revelation 26's guardian floor (守護床: Avo +40, heals 20%): a golden ring with a sparkle at its heart. */
export const WARD: Sprite = {
  palette: { o: '#b45309', y: '#facc15', w: '#fffbeb' },
  rows: [
    '..........',
    '..oooooo..',
    '.o..yy..o.',
    'o...yy...o',
    'o.yywwyy.o',
    'o.yywwyy.o',
    'o...yy...o',
    '.o..yy..o.',
    '..oooooo..',
    '..........',
  ],
}

/** A summoning sigil (Birthright's Endgame, 召喚床: costs 2 to cross): a purple circle with a triangle drawn in it. */
export const SIGIL: Sprite = {
  palette: { p: '#3b0764', l: '#fae8ff' },
  rows: [
    '..pppppp..',
    '.p......p.',
    'p...ll...p',
    'p..l..l..p',
    'p.l....l.p',
    'p.llllll.p',
    'p........p',
    '.p......p.',
    '..pppppp..',
    '..........',
  ],
}

/** A fissure (亀裂: Def -1, Avo -20): a wide rift splitting the ground across, unlike a breakable wall's thin upright crack. */
export const FISSURE: Sprite = {
  palette: { k: '#1c1410', e: '#b08a64' },
  rows: [
    '..........',
    '..........',
    '.e.....e..',
    'ekee..ekee',
    'kkkkeekkkk',
    '.kkkkkkkk.',
    '..kk..kk..',
    '...k...k..',
    '..........',
    '..........',
  ],
}

/** An acid bog (毒沼: 10% of HP a turn): bubbles rising from a purple pool. */
export const ACID_BOG: Sprite = {
  palette: { p: '#6b2f8a', l: '#d8b4fe', o: '#4c1d63' },
  rows: [
    '..........',
    '......lo..',
    '..lo..oo..',
    '..oo......',
    '.....lo...',
    '.....oo...',
    '.pppppppp.',
    'pplppppppp',
    'ppppppplpp',
    '.pppppppp.',
  ],
}

/** Muck (Def -1, Avo -20, 20% of HP a turn, slow going): lumps of brown mud. */
export const MUCK: Sprite = {
  palette: { m: '#94704a', l: '#d2ae84', o: '#2e2014' },
  rows: [
    '..........',
    '..........',
    '...mm.....',
    '..mlmm.mm.',
    '.mmmmmmlm.',
    'mmlmmmmmmm',
    'mmmmmlmmmm',
    'oooooooooo',
    '..........',
    '..........',
  ],
}

/** Caltrops (撒菱: Def -3, Avo -30, 30% of HP a turn): three iron spikes scattered on the floor. */
export const CALTROPS: Sprite = {
  palette: { g: '#cbd5e1', d: '#475569' },
  rows: [
    '..........',
    '..g.......',
    '.gdg...g..',
    '..d...gdg.',
    '.......d..',
    '...g......',
    '..gdg..g..',
    '...d..gdg.',
    '.......d..',
    '..........',
  ],
}

/** A pit: a hole in the boards, its broken planks around the rim. */
export const PIT: Sprite = {
  palette: { o: '#1a140e', p: '#8a6a44', l: '#b08a5a', d: '#0b0912' },
  rows: [
    '..........',
    '.pl..lp...',
    'plooooolp.',
    '.oddddddo.',
    'lodddddddo',
    '.oddddddol',
    'ploddddop.',
    '.loooooo..',
    '..pl..lp..',
    '..........',
  ],
}

/** A mountain trail (Def +1, Avo +10; slow for armour and horses): a winding footpath. */
export const TRAIL: Sprite = {
  palette: { p: '#d8bf8a', d: '#6b5233' },
  rows: [
    '..........',
    '..pp......',
    '...pp..d..',
    '....pp....',
    '...pp.....',
    '..pp...d..',
    '...pp.....',
    '.d..pp....',
    '.....pp...',
    '..........',
  ],
}

/** The coast (Path of Radiance: a trail's stats by the sea): foam breaking on sand. */
/** A coast's other looks, picked tile by tile so a beach doesn't repeat (the user's call): a lone wave, sand with a shell, wet
 * sand and a line of foam, pebbles. */
export const COAST_VARIANTS: Sprite[] = [
  {
    palette: { w: '#eef5f7', b: '#5fa3bd', g: '#8f7a52' },
    rows: [
      '..........',
      '......g...',
      '..........',
      '..ww...ww.',
      '.w..wbw..w',
      '......w...',
      '..........',
      '.g........',
      '.......g..',
      '..........',
    ],
  },
  {
    palette: { s: '#f3e3d2', S: '#d19a8a', g: '#8f7a52' },
    rows: [
      '..........',
      '...g......',
      '........g.',
      '..........',
      '....sSs...',
      '...sSsSs..',
      '...sssss..',
      '.g........',
      '......g...',
      '..........',
    ],
  },
  {
    palette: { d: '#97815a', w: '#eef5f7', g: '#8f7a52' },
    rows: [
      '..........',
      '.g.....g..',
      '..........',
      '..dddd....',
      '.dddddddd.',
      '..dddddd..',
      '..........',
      'ww..ww..ww',
      '..ww..ww..',
      '..........',
    ],
  },
  {
    palette: { p: '#cfc6b4', P: '#8e8573', g: '#8f7a52' },
    rows: [
      '..........',
      '..pp......',
      '..PP...g..',
      '.......pp.',
      '.g.....PP.',
      '..........',
      '....pp....',
      '....PP..g.',
      '.g........',
      '..........',
    ],
  },
]

export const COAST: Sprite = {
  palette: { w: '#eef5f7', b: '#5fa3bd' },
  rows: [
    '..........',
    '.ww...ww..',
    'w..wbw..w.',
    '....w....w',
    '..........',
    '..........',
    '.ww...ww..',
    'w..wbw..w.',
    '....w....w',
    '..........',
  ],
}

/** Supplies to burn (Radiant Dawn Part 3 Ch.3): grain sacks with a flame licking at them. */
export const SUPPLIES: Sprite = {
  palette: { o: '#3a2a1a', s: '#d6b77a', d: '#a8864d', t: '#7a5a2e', y: '#fde047', r: '#f97316' },
  rows: [
    '.......y..',
    '......yry.',
    '..oo..rrr.',
    '.osso..r..',
    '.ossdoo...',
    'osssdtso..',
    'ossdtsssdo',
    'osssttssdo',
    '.oodoossdo',
    '...oooooo.',
  ],
}

/** An armory (The Binding Blade): a striped shop awning over crossed swords. */
export const ARMORY: Sprite = {
  palette: { a: '#b5452f', w: '#f0e6d2', o: OUTLINE, l: '#e8ebf0', g: '#d4a72c', b: '#7a4e25' },
  rows: [
    '.awawawaw.',
    'awawawawaw',
    'oooooooooo',
    '.l......l.',
    '..l....l..',
    '...l..l...',
    '....ll....',
    '...gllg...',
    '..gb..bg..',
    '.b......b.',
  ],
}

/** A vendor (item shop): a blue-striped awning over a potion. */
export const VENDOR: Sprite = {
  palette: { a: '#2f6f9f', w: '#f0e6d2', o: OUTLINE, c: '#b08c56', p: '#4ade80', h: '#bbf7d0' },
  rows: [
    '.awawawaw.',
    'awawawawaw',
    'oooooooooo',
    '....cc....',
    '....oo....',
    '...o..o...',
    '..ohpppo..',
    '..oppppo..',
    '..oppppo..',
    '...oooo...',
  ],
}

/** A secret shop (it lets in only a Member Card's holder): a dark purple awning over a gold card. */
export const SECRET_SHOP: Sprite = {
  palette: { a: '#5b2a7a', w: '#c9b0e0', o: OUTLINE, g: '#d4a72c', y: '#f5dc7a' },
  rows: [
    '.awawawaw.',
    'awawawawaw',
    'oooooooooo',
    '..........',
    '.oooooooo.',
    '.ogggggyo.',
    '.ogoooogo.',
    '.ogggggyo.',
    '.oooooooo.',
    '..........',
  ],
}

/** An arena: a round stone front with two tiers of arches. */
export const ARENA: Sprite = {
  palette: { o: '#6b5f52', s: '#d8cfbf', d: '#4a4038' },
  rows: [
    '..........',
    '.oooooooo.',
    'osssssssso',
    'osdsdsdsdo',
    'osdsdsdsdo',
    'oooooooooo',
    'osdsdsdsdo',
    'osdsdsdsdo',
    'oooooooooo',
    '..........',
  ],
}

/** A peak: two sharp, dark crags with snow on top (taller and rockier than a mountain). */
export const PEAK: Sprite = {
  palette: { o: '#3f3a36', w: '#ffffff', m: '#8a8178', d: '#5f5850' },
  rows: [
    '...o......',
    '..owo.....',
    '..owmo.o..',
    '.ommmoowo.',
    '.ommdmowmo',
    'ommmmdmmmo',
    'ommmmmdmmo',
    'ommmmmmddo',
    'oooooooooo',
    '..........',
  ],
}

/** A bulwark (Echoes): a timber barricade of crossed stakes that mounted units can't cross. */
export const BULWARK: Sprite = {
  palette: { o: '#3a2a1a', w: '#a8743a', d: '#7a5228' },
  rows: [
    '..........',
    '.o......o.',
    '.ow....wo.',
    '..ow..wo..',
    '.ooowwooo.',
    '.wwwddwww.',
    '..ow..wo..',
    '.ow....wo.',
    '.o......o.',
    '..........',
  ],
}

/** A tunnel (Mystery of the Emblem): a rounded rocky mound with a dark arched mouth at its foot. */
export const TUNNEL: Sprite = {
  palette: { o: '#3f3a36', m: '#8a8178', l: '#ada397', d: '#1e1a16' },
  rows: [
    '..........',
    '...oooo...',
    '..omllmo..',
    '.ommllmmo.',
    '.ommddmmo.',
    'ommddddmmo',
    'ommddddmmo',
    'ommddddmmo',
    'oooooooooo',
    '..........',
  ],
}

/** A grave (Echoes' cemeteries): a rounded headstone with a cross. */
export const GRAVE: Sprite = {
  palette: { o: '#3a3a3a', s: '#c8c8c0', d: '#8a8a82' },
  rows: [
    '...oooo...',
    '..ossssd..',
    '.ossoossd.',
    '.ossoossd.',
    '.oooooood.',
    '.ossoossd.',
    '.ossoossd.',
    '.ossssssd.',
    'oooooooooo',
    '..........',
  ],
}

/** A monster's health bars (Three Houses): the pips along the bottom of its marker, one per bar. */
export const HEALTH_PIPS: Sprite = {
  palette: { o: '#0a0a0a', g: '#4ade80' },
  rows: [
    '..........',
    '..........',
    '..........',
    'oooooooooo',
    'oggoggoggo',
    'oggoggoggo',
    'oooooooooo',
    '..........',
    '..........',
    '..........',
  ],
}

/** A Crest Stone set in a wall (Three Houses' Holy Tomb): a red stone in a grey setting, which the chapter's looters take. */
export const CREST_STONE: Sprite = {
  palette: { o: '#2e2a26', g: '#8f8a80', y: '#d9a441', r: '#c0392b', l: '#f2a49a' },
  rows: [
    '..........',
    '...oooo...',
    '..oggggo..',
    '.oggyyggo.',
    '.ogyrlygo.',
    '.ogyrrygo.',
    '.oggyyggo.',
    '..oggggo..',
    '...oooo...',
    '..........',
  ],
}

/** Fell ground (Thabes' ruins): cracked purple floor that costs a unit 20 Avoid. */
export const FELL_FLOOR: Sprite = {
  palette: { o: '#2a1a3a', p: '#8a5aa8', d: '#5a3a70' },
  rows: [
    '..........',
    '.pp..o.pp.',
    '.p..o...p.',
    '...o.o....',
    '..o...oo..',
    '.o..p...o.',
    '...ppp.o..',
    '.o..p..o..',
    '.pp.o...p.',
    '..........',
  ],
}

/** Thick wood (Fates): a wall of trees only fliers cross, darker and denser than the woods' single tree. */
export const THICK_WOOD: Sprite = {
  palette: { o: '#10200d', g: '#2a5521', h: '#477f37', d: '#1b3816' },
  rows: [
    '.oo..oo...',
    'oghooghoo.',
    'ogggoggggo',
    'oggdgogdgo',
    '.oggoggggo',
    'oghggoghgo',
    'ogggdggggo',
    'oggggoggdo',
    '.ooggoggo.',
    '...oo.oo..',
  ],
}

/** Trees on a map whose trees are snowy (Radiant Dawn's Part 3 Endgame and Part 4 Prologue: pale grey-blue on the game's
 * minimap): the tree and thick wood with snow on their boughs. */
export const SNOW_TREE: Sprite = {
  palette: { o: '#33424f', g: '#6f8796', h: '#e8eef4', w: '#c9d5df', t: '#5b4a3a' },
  rows: [
    '....oo....',
    '...ohhho..',
    '..oghwhgo.',
    '.ogghhggo.',
    '..ohhhho..',
    '.ogwhgwgo.',
    'ohhhhhhho.',
    '.ooootooo.',
    '....tt....',
    '....tt....',
  ],
}
export const SNOW_THICK_WOOD: Sprite = {
  palette: { o: '#26323c', g: '#5d7484', h: '#e8eef4', d: '#465a68', w: '#c9d5df' },
  rows: [
    '.oo..oo...',
    'ohhoohhoo.',
    'ogwgohhhwo',
    'oggdgogdgo',
    '.ohhohhhho',
    'oghggoghgo',
    'ohhhdgwhgo',
    'oggggohhdo',
    '.ooggoggo.',
    '...oo.oo..',
  ],
}

/** An old gate (Fates' 廃墟門): the castle gate's posts, broken, with no lintel left. */
export const OLD_GATE: Sprite = {
  palette: { o: '#3d342b', s: '#8f877c', l: '#b9b1a5', r: '#6f665b' },
  rows: [
    'ss........',
    'sss..s....',
    'slss.ss...',
    'sl....ss..',
    'sl.....s..',
    'sl.....ss.',
    'sl.....ss.',
    'sl..r..ss.',
    'oooorroooo',
    '..........',
  ],
}

/** A gateway (Fates' 門口, the Rainbow Sage's): a roofed wooden gate with an open way through. */
export const GATEWAY: Sprite = {
  palette: { t: '#3a3a46', r: '#a8402e', d: '#5a2018' },
  rows: [
    '.tttttttt.',
    'tttttttttt',
    '.rrrrrrrr.',
    '.r.r..r.r.',
    '.r......r.',
    '.r......r.',
    '.r......r.',
    '.r......r.',
    '.d......d.',
    '..........',
  ],
}

/** Rubble that blocks everyone, fliers too (Fates' indoor rubble): a heap filling the tile, unlike the low rubble fliers cross. */
export const RUBBLE_WALL: Sprite = {
  palette: { o: '#1e1a16', r: '#6a5e52', l: '#9c8e7e' },
  rows: [
    '..oo..oo..',
    '.olro.olro',
    'olrrrolrro',
    'orrrrorrro',
    'oolrroolro',
    'olrrrrolro',
    'orrlrrrrro',
    'orrrrlrrro',
    'orrrrrrrro',
    'oooooooooo',
  ],
}

/** Snow and ice to dig through (Revelation 10): a cracked block. */
export const ICE_BLOCK: Sprite = {
  palette: { o: '#5d7c93', w: '#f4fbff', b: '#cfe6f3', d: '#9cc3dc' },
  rows: [
    'oooooooooo',
    'owwwwwwwbo',
    'owwbwwwwbo',
    'owbbwwwbdo',
    'owwwwwbbdo',
    'obwwwwwwdo',
    'owwbbwwwdo',
    'owwwwwwddo',
    'obdddddddo',
    'oooooooooo',
  ],
}

/** A house units stand in (the GBA games' houses and inns): Avo like a village's, but no looter goes for it, so it isn't drawn as one. */
export const COTTAGE: Sprite = {
  palette: { r: '#5b7186', R: '#3d4f60', c: '#8a6a52', w: '#e8dcc0', y: '#f2c94c', d: '#6b4a2a', o: OUTLINE },
  rows: [
    '......cc..',
    '..rrrrcc..',
    '.rrrrrrrR.',
    'rrrrrrrrrR',
    'oooooooooo',
    '.wwwwwwww.',
    '.wyywwddw.',
    '.wyywwddw.',
    '.wwwwwddw.',
    '.oooooooo.',
  ],
}

/** A house with nothing to visit (the GBA games' house tiles, stood in for Avo 10): part of the village's scenery, drawn like its
 * houses with a muted brown roof and windows, no door, so the villages and houses you can visit stand out (the user's call). */
export const TOWN_HOUSE: Sprite = {
  palette: { o: OUTLINE, r: '#8d7a64', R: '#5e4f40', w: '#e3d9c2', n: '#6f8aa6' },
  rows: [
    '..........',
    '...oooo...',
    '..orrrro..',
    '.orrrrrro.',
    '.oRRRRRRo.',
    '..owwwwo..',
    '..ownnwo..',
    '..owwwwo..',
    '..oooooo..',
    '..........',
  ],
}

/** A tile the lord can't enter (Shadow Dragon's reinforcement entry tiles): a crown struck through, drawn as a corner badge. */
export const NO_LORD: Sprite = {
  palette: { y: '#f2c94c', R: '#d23c3c', o: OUTLINE },
  rows: [
    '........RR',
    '.......RR.',
    '.y..y.RR..',
    '.yy.yRRyy.',
    '.yyyRRyyy.',
    '.yyRRyyyy.',
    '.oRRooooo.',
    '.RR.......',
    'RR........',
    'R.........',
  ],
}

/** A snag: a fallen tree across a bridge (the GBA games), attacked down like a cracked wall. */
export const SNAG: Sprite = {
  palette: { o: '#2b1d10', b: '#9a6b3c', B: '#6e4a26', e: '#e6c08a', l: '#c9955a' },
  rows: [
    '..........',
    '..........',
    '......o...',
    '.....obo..',
    '.ooooobooo',
    'oelobbbbbo',
    'oleobbbbbo',
    'oeloBBBBBo',
    '.ooooooooo',
    '..........',
  ],
}

/** Three Houses' swamp (Prt -1, 10% of HP a turn, slow going): murky green water with reeds and a bubble. */
export const SWAMP: Sprite = {
  palette: { w: '#4a5a32', d: '#2f3a1f', b: '#b5c77a', r: '#7d8f45' },
  rows: [
    '..........',
    '.r......r.',
    '.r..b...r.',
    '.rr.....rr',
    '..........',
    '.wwwwwwww.',
    'wwdwwwbwww',
    'wwwwdwwwww',
    '.wwwwwwdw.',
    '..........',
  ],
}

/** A floor trap (Three Houses' Arianrhod: 20% of HP a turn): an iron grate glowing red at its heart. */
export const FLOOR_TRAP: Sprite = {
  palette: { o: '#2e2a26', g: '#8f8a80', r: '#c0392b', y: '#f59e0b' },
  rows: [
    '..........',
    '.oooooooo.',
    '.og.gg.go.',
    '.oggrrggo.',
    '.o.ryyr.o.',
    '.o.ryyr.o.',
    '.oggrrggo.',
    '.og.gg.go.',
    '.oooooooo.',
    '..........',
  ],
}

/** A crater (Three Houses' Ailell: Prt -1, Avoid -20, 20% of HP a turn): a scorched rim around a glowing pit. */
export const CRATER: Sprite = {
  palette: { k: '#3a2a20', b: '#6b4a32', r: '#ea580c', y: '#fde047' },
  rows: [
    '..........',
    '...kkkk...',
    '..kbbbbk..',
    '.kbrrrrbk.',
    '.kbryyrbk.',
    '.kbryyrbk.',
    '.kbrrrrbk.',
    '..kbbbbk..',
    '...kkkk...',
    '..........',
  ],
}

/** An onager (Three Houses: a siege engine a unit on it fires): a throwing arm on a wheeled frame. */
export const ONAGER: Sprite = {
  palette: { o: '#2b1d10', w: '#9a6b3a', y: '#d9b27a', s: '#7d7468' },
  rows: [
    '.......ss.',
    '......oyso',
    '.....oyo..',
    '....oyo...',
    '...oyo....',
    '.oooyooooo',
    '.owwwwwwwo',
    '.oo.oo.oo.',
    '.oo....oo.',
    '..........',
  ],
}

/** A fire orb (a siege engine a unit on it fires): a glowing orb on a stone stand. */
export const FIRE_ORB: Sprite = {
  palette: { o: '#2b1d10', p: '#8a4f8f', r: '#d07ae0', l: '#f6d5fb', g: '#7d7468' },
  rows: [
    '..........',
    '...oooo...',
    '..oprrpo..',
    '.oprllrpo.',
    '.oprllrpo.',
    '..oprrpo..',
    '...oooo...',
    '....gg....',
    '..gggggg..',
    '..........',
  ],
}

/** Fog laid over a tile (Engage's Dragon Vein): two drifting grey-white banks. */
export const FOG: Sprite = {
  palette: { g: '#9ca3af', w: '#f3f4f6' },
  rows: [
    '..........',
    '..gggg....',
    '.gwwwwgg..',
    'gwwwwwwwg.',
    '.gggwwwwg.',
    '....gggg..',
    '..ggg.....',
    '.gwwwggg..',
    'gwwwwwwwgg',
    '.ggggggg..',
  ],
}

/** Water laid over a tile (Engage's Dragon Vein): a rippling blue pool. */
export const PUDDLE: Sprite = {
  palette: { d: '#1e3a8a', b: '#3b82f6', l: '#bfdbfe' },
  rows: [
    '..........',
    '...dddd...',
    '.ddbbbbdd.',
    'dbbllllbbd',
    'dblbbbblbd',
    'dblbllblbd',
    'dbbllllbbd',
    '.ddbbbbdd.',
    '...dddd...',
    '..........',
  ],
}

/** Stone pillars laid over a tile (Engage's Dragon Vein): two rough grey columns, the left one taller. */
export const STONE_PILLARS: Sprite = {
  palette: { o: '#3f3a34', l: '#d6d3d1', m: '#a8a29e', d: '#78716c' },
  rows: [
    '..oo......',
    '.olmo.....',
    '.olmo..oo.',
    '.olmd.olmo',
    '.olmd.olmo',
    '.olmd.olmd',
    'oolmdoolmd',
    'olmmddlmmd',
    'oooooooooo',
    '..........',
  ],
}

/** Miasma laid over a tile (the Corrupted's): dark violet bubbles rising off the ground. */
export const MIASMA: Sprite = {
  palette: { o: '#2e1065', p: '#7e22ce', l: '#d8b4fe' },
  rows: [
    '......oo..',
    '.oo..oplo.',
    'oplo.oppo.',
    'oppo..oo..',
    '.oo..oo...',
    '....oplo..',
    '.oo.oppo..',
    'oplo.oo.oo',
    'oppo..oplo',
    '.oo....oo.',
  ],
}

/** Frost laid over a tile (Engage's Dragon Vein: Mov +2): a pale snowflake. */
export const FROST: Sprite = {
  palette: { b: '#38bdf8', w: '#f0f9ff' },
  rows: [
    '....b.....',
    '.b..w..b..',
    '..b.w.b...',
    '...bwb....',
    'bwwwwwwwb.',
    '...bwb....',
    '..b.w.b...',
    '.b..w..b..',
    '....b.....',
    '..........',
  ],
}

/**
 * A multi-tile building's pieces (the user's call), a sprite for each place in it: a, b, c along its top (left, middle, right),
 * d, e, f through its middle, g, h, i along its front (scripts/gba_walls.py places them). A village: houses, trees and a well in a
 * fenced yard, its gate in the front's middle; a castle: blue-roofed towers at its corners, battlements, a banner and an arched
 * wall. A 3 x 2 building takes the top and front rows, a wider one repeats the middle column.
 */
const VILLAGE_PIECE_PALETTE: Sprite['palette'] = {
  o: OUTLINE, f: '#4d3d27', p: '#ece4cf', r: '#c4462f', R: '#8e2a1c', w: '#efe6cf', n: '#5b7fa6', d: '#5c4a36', g: '#3f6e2e',
  h: '#6fae52', t: '#6b4a2a', b: '#4f8fc0', y: '#d8c18f',
}

export const VILLAGE_PIECES: Record<'a' | 'b' | 'c' | 'd' | 'e' | 'f' | 'g' | 'h' | 'i', Sprite> = {
  a: {
    palette: VILLAGE_PIECE_PALETTE,
    rows: [
      'fpfpfpfpfp',
      'p.........',
      'f..oooo...',
      'p.orrrro..',
      'forrrrrro.',
      'poRRRRRRo.',
      'f.owwwwo..',
      'p.ownwdo..',
      'f.oooooo..',
      'p.........',
    ],
  },
  b: {
    palette: VILLAGE_PIECE_PALETTE,
    rows: [
      'fpfpfpfpfp',
      '..........',
      '.ggg......',
      'ghhhg.....',
      'ghhgg.....',
      '.ggg..ggg.',
      '..t..ghhhg',
      '..t...ggg.',
      '..........',
      '..........',
    ],
  },
  c: {
    palette: VILLAGE_PIECE_PALETTE,
    rows: [
      'fpfpfpfpfp',
      '.........p',
      '...oooo..f',
      '..orrrro.p',
      '.orrrrrrof',
      '.oRRRRRRop',
      '..owwwwo.f',
      '..odwnwo.p',
      '..oooooo.f',
      '.........p',
    ],
  },
  d: {
    palette: VILLAGE_PIECE_PALETTE,
    rows: [
      'f.........',
      'p....ggg..',
      'f...ghhhg.',
      'p...ghhgg.',
      'f....ggg..',
      'p.....t...',
      'f.ggg.t...',
      'pghhhg....',
      'f.ggg.....',
      'p.........',
    ],
  },
  e: {
    palette: VILLAGE_PIECE_PALETTE,
    rows: [
      '..........',
      '..........',
      '....oo....',
      '...obbo...',
      '...obbo...',
      '....oo....',
      '....yy....',
      '....yy....',
      '....yy....',
      '....yy....',
    ],
  },
  f: {
    palette: VILLAGE_PIECE_PALETTE,
    rows: [
      '.........f',
      '.........p',
      '...oooo..f',
      '..orrrro.p',
      '..oRRRRo.f',
      '...owwo..p',
      '...owdo..f',
      '...oooo..p',
      '.........f',
      '.........p',
    ],
  },
  g: {
    palette: VILLAGE_PIECE_PALETTE,
    rows: [
      'f.oooo....',
      'porrrro...',
      'foRRRRo...',
      'p.owwo....',
      'f.owdo....',
      'p.oooo....',
      'f....ggg..',
      'p...ghhhg.',
      'f....ggg..',
      'ppfpfpfpfp',
    ],
  },
  h: {
    palette: VILLAGE_PIECE_PALETTE,
    rows: [
      '....yy....',
      '....yy....',
      '.gggyy....',
      'ghhhgy....',
      '.gggyy....',
      '....yy....',
      '....yy....',
      '....yy....',
      '...fyyf...',
      'fpffyyfpfp',
    ],
  },
  i: {
    palette: VILLAGE_PIECE_PALETTE,
    rows: [
      '.........f',
      '....ggg..p',
      '...ghhhg.f',
      '...ghhgg.p',
      '....ggg..f',
      '.....t...p',
      '.ggg.t...f',
      'ghhhg....p',
      '.ggg.....f',
      'fpfpfpfpfp',
    ],
  },
}

/** More of a village's middle and edge pieces, for a building wider or taller than 3 (a town's blocks): picked tile by tile so a
 * big block is houses, trees and bushes, not one piece repeated. */
export const VILLAGE_VARIANTS: Record<'b' | 'd' | 'e' | 'f' | 'h', Sprite[]> = {
  b: [
    {
      palette: VILLAGE_PIECE_PALETTE,
      rows: [
        'fpfpfpfpfp',
        '..........',
        '...oooo...',
        '..orrrro..',
        '.orrrrrro.',
        '.oRRRRRRo.',
        '..owwwwo..',
        '..ownwdo..',
        '..oooooo..',
        '..........',
      ],
    },
    {
      palette: VILLAGE_PIECE_PALETTE,
      rows: [
        'fpfpfpfpfp',
        '..........',
        '..oooo....',
        '.orrrro...',
        '.oRRRRo...',
        '..owwo....',
        '..owdoggg.',
        '..oooghhhg',
        '......ggg.',
        '..........',
      ],
    },
  ],
  h: [
    {
      palette: VILLAGE_PIECE_PALETTE,
      rows: [
        '..........',
        '...oooo...',
        '..orrrro..',
        '.orrrrrro.',
        '.oRRRRRRo.',
        '..owwwwo..',
        '..ownwdo..',
        '..oooooo..',
        '..........',
        'fpfpfpfpfp',
      ],
    },
    {
      palette: VILLAGE_PIECE_PALETTE,
      rows: [
        '..........',
        '.....ggg..',
        '..ggghhhg.',
        '.ghhghhgg.',
        '..gggggg..',
        '......t...',
        '......t...',
        '..........',
        '..........',
        'fpfpfpfpfp',
      ],
    },
  ],
  d: [
    {
      palette: VILLAGE_PIECE_PALETTE,
      rows: [
        'f.........',
        'p.........',
        'f..oooo...',
        'p.orrrro..',
        'f.oRRRRo..',
        'p..owwo...',
        'f..owdo...',
        'p..oooo...',
        'f.........',
        'p.........',
      ],
    },
  ],
  f: [
    {
      palette: VILLAGE_PIECE_PALETTE,
      rows: [
        '.........f',
        '..ggg....p',
        '.ghhhg...f',
        '.ghhgg...p',
        '..ggg....f',
        '...t.....p',
        '...t.ggg.f',
        '....ghhhgp',
        '.....ggg.f',
        '.........p',
      ],
    },
  ],
  e: [
    {
      palette: VILLAGE_PIECE_PALETTE,
      rows: [
        '..........',
        '...oooo...',
        '..orrrro..',
        '.orrrrrro.',
        '.oRRRRRRo.',
        '..owwwwo..',
        '..ownwdo..',
        '..oooooo..',
        '..........',
        '..........',
      ],
    },
    {
      palette: VILLAGE_PIECE_PALETTE,
      rows: [
        '..........',
        '.oooo.....',
        'orrrro....',
        'oRRRRo....',
        '.owwo.....',
        '.owdo.....',
        '.oooo.ggg.',
        '.....ghhhg',
        '......ggg.',
        '..........',
      ],
    },
    {
      palette: VILLAGE_PIECE_PALETTE,
      rows: [
        '..........',
        '.ggg......',
        'ghhhg.....',
        'ghhgg.ggg.',
        '.ggg.ghhhg',
        '..t..ghhgg',
        '..t...ggg.',
        '.......t..',
        '.......t..',
        '..........',
      ],
    },
  ],
}

const CASTLE_PIECE_PALETTE: Sprite['palette'] = {
  o: OUTLINE, S: '#bdb6a6', D: '#8a8274', B: '#4f6f9a', L: '#7896c0', k: OUTLINE, r: '#c4462f', y: '#e0c060',
}

export const CASTLE_PIECES: Record<'a' | 'b' | 'c' | 'd' | 'e' | 'f' | 'g' | 'h' | 'i', Sprite> = {
  a: {
    palette: CASTLE_PIECE_PALETTE,
    rows: [
      '....oo....',
      '...oLBo...',
      '..oLLBBo..',
      '.oLBBBBBo.',
      '.oooooooo.',
      '.oSSSSSSoo',
      '.oSkSSkSoS',
      '.oSSSSSSoD',
      '.oSDSSDSoS',
      '.oSSSSSSoS',
    ],
  },
  b: {
    palette: CASTLE_PIECE_PALETTE,
    rows: [
      '..........',
      '..........',
      '..........',
      '..........',
      'oo.oo.oo.o',
      'oooooooooo',
      'SSSDSSSSDS',
      'SDSSSSDSSS',
      'SSSSDSSSSD',
      'DSSSSSSDSS',
    ],
  },
  c: {
    palette: CASTLE_PIECE_PALETTE,
    rows: [
      '....oo....',
      '...oBLo...',
      '..oBBLLo..',
      '.oBBBBBLo.',
      '.oooooooo.',
      'ooSSSSSSo.',
      'SoSkSSkSo.',
      'DoSSSSSSo.',
      'SoSDSSDSo.',
      'SoSSSSSSo.',
    ],
  },
  d: {
    palette: CASTLE_PIECE_PALETTE,
    rows: [
      '.oSSSSSSoS',
      '.oSDSSDSoS',
      '.oSSkSSSoD',
      '.oSSSSSSoS',
      '.oSDSSDSoS',
      '.oSSSSSSoS',
      '.oSSkSSSoD',
      '.oSSSSSSoS',
      '.oSDSSDSoS',
      '.oSSSSSSoS',
    ],
  },
  e: {
    palette: CASTLE_PIECE_PALETTE,
    rows: [
      'SSSDSSSSDS',
      'SDSSoySSSS',
      'SSSSoyrrSD',
      'DSSSoyrrrS',
      'SSSSoyrrSS',
      'SDSSoySSDS',
      'SSSSoySSSS',
      'DSSSoySSSD',
      'SSSDSSSSSS',
      'SDSSSSDSSS',
    ],
  },
  f: {
    palette: CASTLE_PIECE_PALETTE,
    rows: [
      'SoSSSSSSo.',
      'SoSDSSDSo.',
      'DoSSSkSSo.',
      'SoSSSSSSo.',
      'SoSDSSDSo.',
      'SoSSSSSSo.',
      'DoSSSkSSo.',
      'SoSSSSSSo.',
      'SoSDSSDSo.',
      'SoSSSSSSo.',
    ],
  },
  g: {
    palette: CASTLE_PIECE_PALETTE,
    rows: [
      '.oSSSSSSoS',
      '.oSDSSDSoS',
      '.oSSkSSSoD',
      '.oSSSSSSoS',
      '.oSDSSDSoS',
      'ooSSSSSSoS',
      'oSSDSSSSDS',
      'oSSSSSDSSS',
      'oDSSSSSSSS',
      'oooooooooo',
    ],
  },
  h: {
    palette: CASTLE_PIECE_PALETTE,
    rows: [
      'SSSDSSSSDS',
      'SDSSSSDSSS',
      'SSSooooSSD',
      'DSoDDDDoSS',
      'SSoDkkDoDS',
      'SDoDkkDoSS',
      'SSoDkkDoSS',
      'DSoDkkDoSD',
      'SSoDkkDoSS',
      'oooooooooo',
    ],
  },
  i: {
    palette: CASTLE_PIECE_PALETTE,
    rows: [
      'SoSSSSSSo.',
      'SoSDSSDSo.',
      'DoSSSkSSo.',
      'SoSSSSSSo.',
      'SoSDSSDSo.',
      'SoSSSSSSoo',
      'SDSSSSDSSo',
      'SSSDSSSSSo',
      'SSSSSSSSDo',
      'oooooooooo',
    ],
  },
}

const TOWN_HOUSE_PALETTE: Sprite['palette'] = {
  o: OUTLINE, r: '#b5452f', R: '#8e2a1c', l: '#d0634a', w: '#e8dcc0', s: '#c9bb9c', n: '#5b7fa6', d: '#6b4a2a', b: '#8a6a44',
  y: '#e0c060',
}

/** A town house over its tiles (the user's call: one house, not a village):
 * roof along its top, plaster walls, a front with its door; one window or none to a tile, so it reads as a house. Its places
 * as a village's: a-c top, d-f middle, g-i front. */
export const HOUSE_PIECES: Record<'a' | 'b' | 'c' | 'd' | 'e' | 'f' | 'g' | 'h' | 'i', Sprite> = {
  a: {
    palette: TOWN_HOUSE_PALETTE,
    rows: [
      '....oooooo',
      '...oolllll',
      '..oorrrrrr',
      '.ooRRRRRRR',
      'oorrrrrrrr',
      'oRRRRRRRRR',
      'orrrrrrrrr',
      'oRRRRRRRRR',
      'orrrrrrrrr',
      'oooooooooo',
    ],
  },
  b: {
    palette: TOWN_HOUSE_PALETTE,
    rows: [
      'oooooooooo',
      'llllllllll',
      'rrrrrrrrrr',
      'RRRRRRRRRR',
      'rrrrrrrrrr',
      'RRRRRRRRRR',
      'rrrrrrrrrr',
      'RRRRRRRRRR',
      'rrrrrrrrrr',
      'oooooooooo',
    ],
  },
  c: {
    palette: TOWN_HOUSE_PALETTE,
    rows: [
      'oooooo....',
      'llllloo...',
      'rrrrrroo..',
      'RRRRRRRoo.',
      'rrrrrrrroo',
      'RRRRRRRRRo',
      'rrrrrrrrro',
      'RRRRRRRRRo',
      'rrrrrrrrro',
      'oooooooooo',
    ],
  },
  d: {
    palette: TOWN_HOUSE_PALETTE,
    rows: [
      'obbbbbbbbb',
      'owwwwwwwww',
      'owwwwwwwww',
      'owwwwwwwww',
      'owwwwwwwww',
      'owwwwwwwww',
      'owwwwwwwww',
      'owwwwwwwww',
      'owwwwwwwww',
      'owwwwwwwww',
    ],
  },
  e: {
    palette: TOWN_HOUSE_PALETTE,
    rows: [
      'bbbbbbbbbb',
      'wwwwwwwwww',
      'wwwwwwwwww',
      'wwwwwwwwww',
      'wwwwwwwwww',
      'wwwwwwwwww',
      'wwwwwwwwww',
      'wwwwwwwwww',
      'wwwwwwwwww',
      'wwwwwwwwww',
    ],
  },
  f: {
    palette: TOWN_HOUSE_PALETTE,
    rows: [
      'bbbbbbbbbo',
      'wwwwwwwwwo',
      'wwwwwwwwwo',
      'wwwwwwwwwo',
      'wwwwwwwwwo',
      'wwwwwwwwwo',
      'wwwwwwwwwo',
      'wwwwwwwwwo',
      'wwwwwwwwwo',
      'wwwwwwwwwo',
    ],
  },
  g: {
    palette: TOWN_HOUSE_PALETTE,
    rows: [
      'obbbbbbbbb',
      'owwwwwwwww',
      'owwonnowww',
      'owwonnowww',
      'owwonnowww',
      'owwsssswww',
      'owwwwwwwww',
      'owwwwwwwww',
      'owwwwwwwww',
      'oooooooooo',
    ],
  },
  h: {
    palette: TOWN_HOUSE_PALETTE,
    rows: [
      'bbbbbbbbbb',
      'wwwwwwwwww',
      'wwwoooowww',
      'wwoddddoww',
      'wwoddddoww',
      'wwodddyoww',
      'wwoddddoww',
      'wwoddddoww',
      'wwoddddoww',
      'oooooooooo',
    ],
  },
  i: {
    palette: TOWN_HOUSE_PALETTE,
    rows: [
      'bbbbbbbbbo',
      'wwwwwwwwwo',
      'wwwonnowwo',
      'wwwonnowwo',
      'wwwonnowwo',
      'wwwsssswwo',
      'wwwwwwwwwo',
      'wwwwwwwwwo',
      'wwwwwwwwwo',
      'oooooooooo',
    ],
  },
}

/** A fountain drawn whole (Path of Radiance's Endgame courtyard): a stone basin's rim along its outer sides, water inside, a jet on a
 * plinth in its middle. Places as HOUSE_PIECES'. */
const FOUNTAIN_PALETTE: Sprite['palette'] = {
  o: OUTLINE, r: '#ddd6c8', R: '#a39b8b', w: '#4f97cc', W: '#a9dcf5', s: '#ffffff', S: '#d6f0ff', p: '#c9c1b2', P: '#9a9282',
}
export const FOUNTAIN_PIECES: Record<'a' | 'b' | 'c' | 'd' | 'e' | 'f' | 'g' | 'h' | 'i', Sprite> = {
  a: {
    palette: FOUNTAIN_PALETTE,
    rows: [
      '.ooooooooo',
      'orrrrrrrrr',
      'orRRRRRRRR',
      'orRwwwwwww',
      'orRwwwwwww',
      'orRwwwwWww',
      'orRwwWwwww',
      'orRwwwwwww',
      'orRwwwwwWw',
      'orRwwwwwww',
    ],
  },
  b: {
    palette: FOUNTAIN_PALETTE,
    rows: [
      'oooooooooo',
      'rrrrrrrrrr',
      'RRRRRRRRRR',
      'wwwwwwwwww',
      'wwwwwwwwww',
      'wwwwwwwWww',
      'wwwwwWwwww',
      'wwWwwwwwww',
      'wwwwwwwwWw',
      'wwwwwwwwww',
    ],
  },
  c: {
    palette: FOUNTAIN_PALETTE,
    rows: [
      'ooooooooo.',
      'rrrrrrrrro',
      'RRRRRRRRro',
      'wwwwwwwRro',
      'wwwwwwwRro',
      'wwwwwwwRro',
      'wwwwwWwRro',
      'wwWwwwwRro',
      'wwwwwwwRro',
      'wwwwwwwRro',
    ],
  },
  d: {
    palette: FOUNTAIN_PALETTE,
    rows: [
      'orRwwwwwww',
      'orRwwwwwww',
      'orRwWwwwww',
      'orRwwwwwww',
      'orRwwwwwww',
      'orRwwwwWww',
      'orRwwWwwww',
      'orRwwwwwww',
      'orRwwwwwWw',
      'orRwwwwwww',
    ],
  },
  e: {
    palette: FOUNTAIN_PALETTE,
    rows: [
      'wwwwwwwwww',
      'wwwwwwwwww',
      'wwwwsswwww',
      'wwwsSSswww',
      'wwwwSSwwww',
      'wwwpPPpWww',
      'wwwppppwww',
      'wwWwwwwwww',
      'wwwwwwwwWw',
      'wwwwwwwwww',
    ],
  },
  f: {
    palette: FOUNTAIN_PALETTE,
    rows: [
      'wwwwwwwRro',
      'wwwwwwwRro',
      'wwwwWwwRro',
      'wwwwwwwRro',
      'wwwwwwwRro',
      'wwwwwwwRro',
      'wwwwwWwRro',
      'wwWwwwwRro',
      'wwwwwwwRro',
      'wwwwwwwRro',
    ],
  },
  g: {
    palette: FOUNTAIN_PALETTE,
    rows: [
      'orRwwwwwww',
      'orRwwwwwww',
      'orRwWwwwww',
      'orRwwwwwww',
      'orRwwwwwww',
      'orRwwwwWww',
      'orRwwWwwww',
      'orRRRRRRRR',
      'orRRRRRRRR',
      '.ooooooooo',
    ],
  },
  h: {
    palette: FOUNTAIN_PALETTE,
    rows: [
      'wwwwwwwwww',
      'wwwwwwwwww',
      'wwwwWwwwww',
      'wwwwwwwwww',
      'wwwwwwwwww',
      'wwwwwwwWww',
      'wwwwwWwwww',
      'RRRRRRRRRR',
      'RRRRRRRRRR',
      'oooooooooo',
    ],
  },
  i: {
    palette: FOUNTAIN_PALETTE,
    rows: [
      'wwwwwwwRro',
      'wwwwwwwRro',
      'wwwwWwwRro',
      'wwwwwwwRro',
      'wwwwwwwRro',
      'wwwwwwwRro',
      'wwwwwWwRro',
      'RRRRRRRRro',
      'RRRRRRRRro',
      'ooooooooo.',
    ],
  },
}

/** Houses packed so close that only their roofs show (Radiant Dawn's Part 1 Ch.1 and Ch.3, the user's calls): shingle courses that
 * run on from tile to tile, edged only where the roof ends; places as HOUSE_PIECES'. A door under the eave where a house can be visited,
 * and a chimney on the tiles the user picked. */
export const ROOFTOP_PIECES: Record<'a' | 'b' | 'c' | 'd' | 'e' | 'f' | 'g' | 'h' | 'i', Sprite> = {
  a: {
    palette: TOWN_HOUSE_PALETTE,
    rows: [
      'oooooooooo',
      'olllllllll',
      'orrrrrrrrr',
      'oRRRRRRRRR',
      'orrrrrrrrr',
      'oRRRRRRRRR',
      'orrrrrrrrr',
      'oRRRRRRRRR',
      'orrrrrrrrr',
      'oRRRRRRRRR',
    ],
  },
  b: {
    palette: TOWN_HOUSE_PALETTE,
    rows: [
      'oooooooooo',
      'llllllllll',
      'rrrrrrrrrr',
      'RRRRRRRRRR',
      'rrrrrrrrrr',
      'RRRRRRRRRR',
      'rrrrrrrrrr',
      'RRRRRRRRRR',
      'rrrrrrrrrr',
      'RRRRRRRRRR',
    ],
  },
  c: {
    palette: TOWN_HOUSE_PALETTE,
    rows: [
      'oooooooooo',
      'lllllllllo',
      'rrrrrrrrro',
      'RRRRRRRRRo',
      'rrrrrrrrro',
      'RRRRRRRRRo',
      'rrrrrrrrro',
      'RRRRRRRRRo',
      'rrrrrrrrro',
      'RRRRRRRRRo',
    ],
  },
  d: {
    palette: TOWN_HOUSE_PALETTE,
    rows: [
      'orrrrrrrrr',
      'oRRRRRRRRR',
      'orrrrrrrrr',
      'oRRRRRRRRR',
      'orrrrrrrrr',
      'oRRRRRRRRR',
      'orrrrrrrrr',
      'oRRRRRRRRR',
      'orrrrrrrrr',
      'oRRRRRRRRR',
    ],
  },
  e: {
    palette: TOWN_HOUSE_PALETTE,
    rows: [
      'rrrrrrrrrr',
      'RRRRRRRRRR',
      'rrrrrrrrrr',
      'RRRRRRRRRR',
      'rrrrrrrrrr',
      'RRRRRRRRRR',
      'rrrrrrrrrr',
      'RRRRRRRRRR',
      'rrrrrrrrrr',
      'RRRRRRRRRR',
    ],
  },
  f: {
    palette: TOWN_HOUSE_PALETTE,
    rows: [
      'rrrrrrrrro',
      'RRRRRRRRRo',
      'rrrrrrrrro',
      'RRRRRRRRRo',
      'rrrrrrrrro',
      'RRRRRRRRRo',
      'rrrrrrrrro',
      'RRRRRRRRRo',
      'rrrrrrrrro',
      'RRRRRRRRRo',
    ],
  },
  g: {
    palette: TOWN_HOUSE_PALETTE,
    rows: [
      'orrrrrrrrr',
      'oRRRRRRRRR',
      'orrrrrrrrr',
      'oRRRRRRRRR',
      'orrrrrrrrr',
      'oRRRRRRRRR',
      'orrrrrrrrr',
      'oRRRRRRRRR',
      'oRRRRRRRRR',
      'oooooooooo',
    ],
  },
  h: {
    palette: TOWN_HOUSE_PALETTE,
    rows: [
      'rrrrrrrrrr',
      'RRRRRRRRRR',
      'rrrrrrrrrr',
      'RRRRRRRRRR',
      'rrrrrrrrrr',
      'RRRRRRRRRR',
      'rrrrrrrrrr',
      'RRRRRRRRRR',
      'RRRRRRRRRR',
      'oooooooooo',
    ],
  },
  i: {
    palette: TOWN_HOUSE_PALETTE,
    rows: [
      'rrrrrrrrro',
      'RRRRRRRRRo',
      'rrrrrrrrro',
      'RRRRRRRRRo',
      'rrrrrrrrro',
      'RRRRRRRRRo',
      'rrrrrrrrro',
      'RRRRRRRRRo',
      'RRRRRRRRRo',
      'oooooooooo',
    ],
  },
}
export const ROOFTOP_DOORS: Record<'g' | 'h' | 'i', Sprite> = {
  g: {
    palette: TOWN_HOUSE_PALETTE,
    rows: [
      'orrrrrrrrr',
      'oRRRRRRRRR',
      'orrrrrrrrr',
      'oRRRRRRRRR',
      'oooooooooo',
      'owwoddowww',
      'owwoddowww',
      'owwoddywww',
      'owwoddowww',
      'oooooooooo',
    ],
  },
  h: {
    palette: TOWN_HOUSE_PALETTE,
    rows: [
      'rrrrrrrrrr',
      'RRRRRRRRRR',
      'rrrrrrrrrr',
      'RRRRRRRRRR',
      'oooooooooo',
      'wwwoddowww',
      'wwwoddowww',
      'wwwoddywww',
      'wwwoddowww',
      'oooooooooo',
    ],
  },
  i: {
    palette: TOWN_HOUSE_PALETTE,
    rows: [
      'rrrrrrrrro',
      'RRRRRRRRRo',
      'rrrrrrrrro',
      'RRRRRRRRRo',
      'oooooooooo',
      'wwwoddowwo',
      'wwwoddowwo',
      'wwwoddywwo',
      'wwwoddowwo',
      'oooooooooo',
    ],
  },
}
export const CHIMNEY: Sprite = {
  palette: { o: '#3b2614', b: '#9a5a3c', B: '#6e3a26', s: 'rgba(230, 230, 230, 0.55)' },
  rows: [
    '.....s....',
    '......s...',
    '.....oooo.',
    '.....obBo.',
    '.....obBo.',
    '.....obBo.',
    '..........',
    '..........',
    '..........',
    '..........',
  ],
}

/** A town house turned side-on (taller than it's wide), seen as its roof alone (the user's call: not a tall silo): the ridge
 * runs front to back, the left slope in shade and the right one lit. Places as HOUSE_PIECES': j-l its back, m-o its middle,
 * p-r its front. */
export const HOUSE_SIDE_PIECES: Record<'j' | 'k' | 'l' | 'm' | 'n' | 'o' | 'p' | 'q' | 'r', Sprite> = {
  j: {
    palette: TOWN_HOUSE_PALETTE,
    rows: [
      'oooooooooo',
      'oRrRRrRRrl',
      'oRrRRrRRrl',
      'oRrRRrRRrl',
      'oRrRRrRRrl',
      'oRrRRrRRrl',
      'oRrRRrRRrl',
      'oRrRRrRRrl',
      'oRrRRrRRrl',
      'oRrRRrRRrl',
    ],
  },
  k: {
    palette: TOWN_HOUSE_PALETTE,
    rows: [
      'oooooooooo',
      'oRrRrlrlro',
      'oRrRrlrlro',
      'oRrRrlrlro',
      'oRrRrlrlro',
      'oRrRrlrlro',
      'oRrRrlrlro',
      'oRrRrlrlro',
      'oRrRrlrlro',
      'oRrRrlrlro',
    ],
  },
  l: {
    palette: TOWN_HOUSE_PALETTE,
    rows: [
      'oooooooooo',
      'lrlrrlrrlo',
      'lrlrrlrrlo',
      'lrlrrlrrlo',
      'lrlrrlrrlo',
      'lrlrrlrrlo',
      'lrlrrlrrlo',
      'lrlrrlrrlo',
      'lrlrrlrrlo',
      'lrlrrlrrlo',
    ],
  },
  m: {
    palette: TOWN_HOUSE_PALETTE,
    rows: [
      'oRrRRrRRrl',
      'oRrRRrRRrl',
      'oRrRRrRRrl',
      'oRrRRrRRrl',
      'oRrRRrRRrl',
      'oRrRRrRRrl',
      'oRrRRrRRrl',
      'oRrRRrRRrl',
      'oRrRRrRRrl',
      'oRrRRrRRrl',
    ],
  },
  n: {
    palette: TOWN_HOUSE_PALETTE,
    rows: [
      'oRrRrlrlro',
      'oRrRrlrlro',
      'oRrRrlrlro',
      'oRrRrlrlro',
      'oRrRrlrlro',
      'oRrRrlrlro',
      'oRrRrlrlro',
      'oRrRrlrlro',
      'oRrRrlrlro',
      'oRrRrlrlro',
    ],
  },
  o: {
    palette: TOWN_HOUSE_PALETTE,
    rows: [
      'lrlrrlrrlo',
      'lrlrrlrrlo',
      'lrlrrlrrlo',
      'lrlrrlrrlo',
      'lrlrrlrrlo',
      'lrlrrlrrlo',
      'lrlrrlrrlo',
      'lrlrrlrrlo',
      'lrlrrlrrlo',
      'lrlrrlrrlo',
    ],
  },
  p: {
    palette: TOWN_HOUSE_PALETTE,
    rows: [
      'oRrRRrRRrl',
      'oRrRRrRRrl',
      'oRrRRrRRrl',
      'oRrRRrRRrl',
      'oRrRRrRRrl',
      'oRrRRrRRrl',
      'oRrRRrRRrl',
      'oRrRRrRRrl',
      'oRrRRrRRrl',
      'oooooooooo',
    ],
  },
  q: {
    palette: TOWN_HOUSE_PALETTE,
    rows: [
      'oRrRrlrlro',
      'oRrRrlrlro',
      'oRrRrlrlro',
      'oRrRrlrlro',
      'oRrRrlrlro',
      'oRrRrlrlro',
      'oRrRrlrlro',
      'oRrRrlrlro',
      'oRrRrlrlro',
      'oooooooooo',
    ],
  },
  r: {
    palette: TOWN_HOUSE_PALETTE,
    rows: [
      'lrlrrlrrlo',
      'lrlrrlrrlo',
      'lrlrrlrrlo',
      'lrlrrlrrlo',
      'lrlrrlrrlo',
      'lrlrrlrrlo',
      'lrlrrlrrlo',
      'lrlrrlrrlo',
      'lrlrrlrrlo',
      'oooooooooo',
    ],
  },
}

/** A town house's walls and front ends with a window where
 * the piece has none, or none where it has one: picked tile by tile. */
export const HOUSE_VARIANTS: Record<'d' | 'e' | 'f' | 'g' | 'i', Sprite[]> = {
  d: [
    {
      palette: TOWN_HOUSE_PALETTE,
      rows: [
        'obbbbbbbbb',
        'owwwwwwwww',
        'owwwwwwwww',
        'owwonnowww',
        'owwonnowww',
        'owwonnowww',
        'owwsssswww',
        'owwwwwwwww',
        'owwwwwwwww',
        'owwwwwwwww',
      ],
    },
  ],
  e: [
    {
      palette: TOWN_HOUSE_PALETTE,
      rows: [
        'bbbbbbbbbb',
        'wwwwwwwwww',
        'wwwwwwwwww',
        'wwwonnowww',
        'wwwonnowww',
        'wwwonnowww',
        'wwwsssswww',
        'wwwwwwwwww',
        'wwwwwwwwww',
        'wwwwwwwwww',
      ],
    },
  ],
  f: [
    {
      palette: TOWN_HOUSE_PALETTE,
      rows: [
        'bbbbbbbbbo',
        'wwwwwwwwwo',
        'wwwwwwwwwo',
        'wwwonnowwo',
        'wwwonnowwo',
        'wwwonnowwo',
        'wwwsssswwo',
        'wwwwwwwwwo',
        'wwwwwwwwwo',
        'wwwwwwwwwo',
      ],
    },
  ],
  g: [
    {
      palette: TOWN_HOUSE_PALETTE,
      rows: [
        'obbbbbbbbb',
        'owwwwwwwww',
        'owwwwwwwww',
        'owwwwwwwww',
        'owwwwwwwww',
        'owwwwwwwww',
        'owwwwwwwww',
        'owwwwwwwww',
        'owwwwwwwww',
        'oooooooooo',
      ],
    },
  ],
  i: [
    {
      palette: TOWN_HOUSE_PALETTE,
      rows: [
        'bbbbbbbbbo',
        'wwwwwwwwwo',
        'wwwwwwwwwo',
        'wwwwwwwwwo',
        'wwwwwwwwwo',
        'wwwwwwwwwo',
        'wwwwwwwwwo',
        'wwwwwwwwwo',
        'wwwwwwwwwo',
        'oooooooooo',
      ],
    },
  ],
}

/** A wide house's front past its door (a window, or a blank wall), and a
 * 2-wide house's door in its left tile. */
export const HOUSE_FRONT: Record<'window' | 'blank' | 'door-left' | 'door-right', Sprite> = {
  window: {
    palette: TOWN_HOUSE_PALETTE,
    rows: [
      'bbbbbbbbbb',
      'wwwwwwwwww',
      'wwwonnowww',
      'wwwonnowww',
      'wwwonnowww',
      'wwwsssswww',
      'wwwwwwwwww',
      'wwwwwwwwww',
      'wwwwwwwwww',
      'oooooooooo',
    ],
  },
  blank: {
    palette: TOWN_HOUSE_PALETTE,
    rows: [
      'bbbbbbbbbb',
      'wwwwwwwwww',
      'wwwwwwwwww',
      'wwwwwwwwww',
      'wwwwwwwwww',
      'wwwwwwwwww',
      'wwwwwwwwww',
      'wwwwwwwwww',
      'wwwwwwwwww',
      'oooooooooo',
    ],
  },
  'door-left': {
    palette: TOWN_HOUSE_PALETTE,
    rows: [
      'obbbbbbbbb',
      'owwwwwwwww',
      'owwoooowww',
      'owoddddoww',
      'owoddddoww',
      'owodddyoww',
      'owoddddoww',
      'owoddddoww',
      'owoddddoww',
      'oooooooooo',
    ],
  },
  // A door at a house's right end, over a door mat there.
  'door-right': {
    palette: TOWN_HOUSE_PALETTE,
    rows: [
      'bbbbbbbbbo',
      'wwwwwwwwwo',
      'wwwoooowwo',
      'wwoddddowo',
      'wwoddddowo',
      'wwodddyowo',
      'wwoddddowo',
      'wwoddddowo',
      'wwoddddowo',
      'oooooooooo',
    ],
  },
}

const CHURCH_PALETTE: Sprite['palette'] = {
  o: OUTLINE, r: '#5a6b85', R: '#43516a', l: '#7d8ea8', S: '#c4bdad', D: '#968e80', g: '#6f8fc7', G: '#b0507a', y: '#e0c060',
  d: '#6b4a2a',
}

/** A church over its tiles: a slate roof with a gold cross on its ridge,
 * grey stone walls with tall stained-glass windows and a rose window, an arched door. Places as a village's. */
export const CHURCH_PIECES: Record<'a' | 'b' | 'c' | 'd' | 'e' | 'f' | 'g' | 'h' | 'i', Sprite> = {
  a: {
    palette: CHURCH_PALETTE,
    rows: [
      '....oooooo',
      '...oolllll',
      '..oorrrrrr',
      '.ooRRRRRRR',
      'oorrrrrrrr',
      'oRRRRRRRRR',
      'orrrrrrrrr',
      'oRRRRRRRRR',
      'orrrrrrrrr',
      'oooooooooo',
    ],
  },
  b: {
    palette: CHURCH_PALETTE,
    rows: [
      'oooo..oooo',
      'lllloyolll',
      'rrrrryyrrr',
      'RRRRoyoRRR',
      'rrrrryrrrr',
      'RRRRRRRRRR',
      'rrrrrrrrrr',
      'RRRRRRRRRR',
      'rrrrrrrrrr',
      'oooooooooo',
    ],
  },
  c: {
    palette: CHURCH_PALETTE,
    rows: [
      'oooooo....',
      'llllloo...',
      'rrrrrroo..',
      'RRRRRRRoo.',
      'rrrrrrrroo',
      'RRRRRRRRRo',
      'rrrrrrrrro',
      'RRRRRRRRRo',
      'rrrrrrrrro',
      'oooooooooo',
    ],
  },
  d: {
    palette: CHURCH_PALETTE,
    rows: [
      'oDDDDDDDDD',
      'oSSSSSSSSS',
      'oSSoooSSSS',
      'oSogggoSSS',
      'oSoGGGoSSS',
      'oSogggoSSS',
      'oSoGGGoSSS',
      'oSoooooSSS',
      'oSSSSSSSSS',
      'oSSSSDSSSS',
    ],
  },
  e: {
    palette: CHURCH_PALETTE,
    rows: [
      'DDDDDDDDDD',
      'SSSSSSSSSS',
      'SSSoooSSSS',
      'SSogGgoSSS',
      'SSoGgGoSSS',
      'SSogGgoSSS',
      'SSSoooSSSS',
      'SSSSSSSSSS',
      'DSSSSDSSSS',
      'SSSSSSSSSS',
    ],
  },
  f: {
    palette: CHURCH_PALETTE,
    rows: [
      'DDDDDDDDDo',
      'SSSSSSSSSo',
      'SSSSoooSSo',
      'SSSogggoSo',
      'SSSoGGGoSo',
      'SSSogggoSo',
      'SSSoGGGoSo',
      'SSSoooooSo',
      'SSSSSSSSSo',
      'SSSSDSSSSo',
    ],
  },
  g: {
    palette: CHURCH_PALETTE,
    rows: [
      'oDDDDDDDDD',
      'oSSSSSSSSS',
      'oSSoooSSSS',
      'oSogggoSSS',
      'oSoGGGoSSS',
      'oSogggoSSS',
      'oSoooooSSS',
      'oSSSSSSSSS',
      'oSSSSSSSSS',
      'oooooooooo',
    ],
  },
  h: {
    palette: CHURCH_PALETTE,
    rows: [
      'DDDDDDDDDD',
      'SSSooooSSS',
      'SSoddddoSS',
      'SoddddddoS',
      'SoddddddoS',
      'SoddddydoS',
      'SoddddddoS',
      'SoddddddoS',
      'SoddddddoS',
      'oooooooooo',
    ],
  },
  i: {
    palette: CHURCH_PALETTE,
    rows: [
      'DDDDDDDDDo',
      'SSSSSSSSSo',
      'SSSSoooSSo',
      'SSSogggoSo',
      'SSSoGGGoSo',
      'SSSogggoSo',
      'SSSoooooSo',
      'SSSSSSSSSo',
      'SSSSSSSSSo',
      'oooooooooo',
    ],
  },
}

const CAMP_PALETTE: Sprite['palette'] = {
  o: OUTLINE, r: '#6e5644', R: '#4a392d', l: '#8a705a', w: '#9a7448', W: '#7a5a36', k: OUTLINE, d: '#5c4228', y: '#c9a050',
  b: '#3d4a5c',
}

/** A prison camp's barracks over its tiles: plank walls under a dark shingle
 * roof, barred windows, a plank door. Places as a village's. */
export const CAMP_PIECES: Record<'a' | 'b' | 'c' | 'd' | 'e' | 'f' | 'g' | 'h' | 'i', Sprite> = {
  a: {
    palette: CAMP_PALETTE,
    rows: [
      '....oooooo',
      '...oolllll',
      '..oorrrrrr',
      '.ooRRRRRRR',
      'oorrrrrrrr',
      'oRRRRRRRRR',
      'orrrrrrrrr',
      'oRRRRRRRRR',
      'orrrrrrrrr',
      'oooooooooo',
    ],
  },
  b: {
    palette: CAMP_PALETTE,
    rows: [
      'oooooooooo',
      'llllllllll',
      'rrrrrrrrrr',
      'RRRRRRRRRR',
      'rrrrrrrrrr',
      'RRRRRRRRRR',
      'rrrrrrrrrr',
      'RRRRRRRRRR',
      'rrrrrrrrrr',
      'oooooooooo',
    ],
  },
  c: {
    palette: CAMP_PALETTE,
    rows: [
      'oooooo....',
      'llllloo...',
      'rrrrrroo..',
      'RRRRRRRoo.',
      'rrrrrrrroo',
      'RRRRRRRRRo',
      'rrrrrrrrro',
      'RRRRRRRRRo',
      'rrrrrrrrro',
      'oooooooooo',
    ],
  },
  d: {
    palette: CAMP_PALETTE,
    rows: [
      'oWWWWWWWWW',
      'oWwwWwwWww',
      'oWwwWwwWww',
      'oWwwWwwWww',
      'oWwwWwwWww',
      'oWwwWwwWww',
      'oWwwWwwWww',
      'oWwwWwwWww',
      'oWwwWwwWww',
      'oWwwWwwWww',
    ],
  },
  e: {
    palette: CAMP_PALETTE,
    rows: [
      'WWWWWWWWWW',
      'wWwwWwwWww',
      'wWwwWwwWww',
      'wWwwWwwWww',
      'wWwwWwwWww',
      'wWwwWwwWww',
      'wWwwWwwWww',
      'wWwwWwwWww',
      'wWwwWwwWww',
      'wWwwWwwWww',
    ],
  },
  f: {
    palette: CAMP_PALETTE,
    rows: [
      'WWWWWWWWWo',
      'wwWwwWwwWo',
      'wwWwwWwwWo',
      'wwWwwWwwWo',
      'wwWwwWwwWo',
      'wwWwwWwwWo',
      'wwWwwWwwWo',
      'wwWwwWwwWo',
      'wwWwwWwwWo',
      'wwWwwWwwWo',
    ],
  },
  g: {
    palette: CAMP_PALETTE,
    rows: [
      'oWWWWWWWWW',
      'oWwwWwwWww',
      'oWoooooowW',
      'oWobkbkbow',
      'oWobkbkbow',
      'oWoooooowW',
      'oWwwWwwWww',
      'oWwwWwwWww',
      'oWwwWwwWww',
      'oooooooooo',
    ],
  },
  h: {
    palette: CAMP_PALETTE,
    rows: [
      'WWWWWWWWWW',
      'wWwwWwwWww',
      'wWoooooWww',
      'wWodddoWww',
      'wWodddoWww',
      'wWoddyoWww',
      'wWodddoWww',
      'wWodddoWww',
      'wWodddoWww',
      'oooooooooo',
    ],
  },
  i: {
    palette: CAMP_PALETTE,
    rows: [
      'WWWWWWWWWo',
      'wwWwwWwwWo',
      'WwooooooWo',
      'wobkbkboWo',
      'wobkbkboWo',
      'WwooooooWo',
      'wwWwwWwwWo',
      'wwWwwWwwWo',
      'wwWwwWwwWo',
      'oooooooooo',
    ],
  },
}

/** A watchtower: a lookout hut on four legs, a ladder up. */
export const WATCHTOWER: Sprite = {
  palette: { o: OUTLINE, r: '#6e5644', w: '#9a7448', W: '#6e5232', k: OUTLINE },
  rows: [
    '...oooo...',
    '..orrrro..',
    '.orrrrrro.',
    '.owwkkwwo.',
    '.oWWWWWWo.',
    '..ow..wo..',
    '..oWkkWo..',
    '..ow..wo..',
    '..oWkkWo..',
    '..oo..oo..',
  ],
}

/** A wide church's front past its door: a stained-glass window. */
export const CHURCH_FRONT_PLAIN: Sprite = {
  palette: CHURCH_PALETTE,
  rows: [
    'DDDDDDDDDD',
    'SSSSSSSSSS',
    'SSSoooSSSS',
    'SSogggoSSS',
    'SSoGGGoSSS',
    'SSogggoSSS',
    'SSoooooSSS',
    'SSSSSSSSSS',
    'SSSSSSSSSS',
    'oooooooooo',
  ],
}

/** A long barracks' front past its door: a barred window. */
export const CAMP_FRONT_PLAIN: Sprite = {
  palette: CAMP_PALETTE,
  rows: [
    'WWWWWWWWWW',
    'wWwwWwwWww',
    'wWoooooowW',
    'wWobkbkbow',
    'wWobkbkbow',
    'wWoooooowW',
    'wWwwWwwWww',
    'wWwwWwwWww',
    'wWwwWwwWww',
    'oooooooooo',
  ],
}

const STALL_PALETTE: Sprite['palette'] = {
  o: OUTLINE, r: '#c4462f', w: '#f2ecdc', t: '#8a6a44', T: '#5e4630', a: '#d9a441', g: '#6fae52', p: '#b07ad0', y: '#e8c84a',
}

/** A market's stalls along its tiles: a striped awning over a counter of goods, its ends on posts. */
export const MARKET_STALL: Record<'left' | 'mid' | 'right' | 'alone', Sprite> = {
  left: {
    palette: STALL_PALETTE,
    rows: [
      '.ooooooooo',
      'orrwwrrwwr',
      'orrwwrrwwr',
      '.ooooooooo',
      '.t........',
      '.t........',
      '.tagyapgay',
      'ottttttttt',
      '.TTTTTTTTT',
      '.T........',
    ],
  },
  mid: {
    palette: STALL_PALETTE,
    rows: [
      'oooooooooo',
      'wrrwwrrwwr',
      'wrrwwrrwwr',
      'oooooooooo',
      '..........',
      '..........',
      'pgaypagyap',
      'tttttttttt',
      'TTTTTTTTTT',
      '..........',
    ],
  },
  right: {
    palette: STALL_PALETTE,
    rows: [
      'ooooooooo.',
      'rwwrrwwrro',
      'rwwrrwwrro',
      'ooooooooo.',
      '........t.',
      '........t.',
      'yagpaygat.',
      'ttttttttto',
      'TTTTTTTTT.',
      '........T.',
    ],
  },
  alone: {
    palette: STALL_PALETTE,
    rows: [
      '.oooooooo.',
      'orrwwrrwwo',
      'orrwwrrwwo',
      '.oooooooo.',
      '.t......t.',
      '.t......t.',
      '.tagyapgt.',
      'otttttttto',
      '.TTTTTTTT.',
      '.T......T.',
    ],
  },
}

/** Crates stacked on one tile (a town's cargo). */
export const CRATES: Sprite = {
  palette: { o: '#3b2614', w: '#b88a52', W: '#8a6236', l: '#d4a86e' },
  rows: [
    '..........',
    '.oooooo...',
    '.olwwwWo..',
    '.owlwlWo..',
    '.owwlwWooo',
    '.oooooooWW',
    '..owlwwWlw',
    '..owwlwlWW',
    '..owwwlwWW',
    '..oooooooo',
  ],
}

/** The props the Tellius maps' models put on an odds-and-ends tile (the user's call: drawn as the game's model shows them). */
export const PROP_SPRITES: Record<'box' | 'cart' | 'flowerpot' | 'statue' | 'pillar' | 'sandbags' | 'gold', Sprite> = {
  // Crates stacked to the tile's edges, so a row of them reads as one stack (the user: the old crates looked off side by side).
  box: {
    palette: { o: '#3b2614', w: '#b88a52', W: '#8a6236', l: '#d4a86e' },
    rows: [
      '..oooooo..',
      '..olwwWo..',
      '..owlwWo..',
      '..oooooo..',
      'oooooooooo',
      'olwwWolwWo',
      'owlwWowlWo',
      'owwlWowwlo',
      'owwwWowwWo',
      'oooooooooo',
    ],
  },
  cart: {
    palette: { o: '#3b2614', w: '#a0703c', W: '#7a5128', l: '#c99a5e', k: '#55565c' },
    rows: [
      '..........',
      '..........',
      'oooooooo..',
      'olwlwlwoo.',
      'owwwwwwWoo',
      'oooooooooo',
      '.okko.okko',
      'okllko.oko',
      '.okko...o.',
      '..oo......',
    ],
  },
  flowerpot: {
    palette: { o: '#3b2614', g: '#4f8a3a', G: '#2f5a24', f: '#e06a7a', y: '#f0d060', c: '#b5653d', C: '#8a4526' },
    rows: [
      '..f..y....',
      '.fyf.g.f..',
      '..gGgfyf..',
      '.gGgGg.gG.',
      '..GgGgGg..',
      '.oooooooo.',
      '.occccCCo.',
      '..occcCo..',
      '..occcCo..',
      '...oooo...',
    ],
  },
  statue: {
    palette: { o: '#2e2f33', s: '#c9c6bd', S: '#9a978f', l: '#e6e3da' },
    rows: [
      '....oo....',
      '...olso...',
      '...osSo...',
      '..olssSo..',
      '..osssSo..',
      '...osSo...',
      '...osSo...',
      '.oooooooo.',
      '.olsssSSo.',
      '.oooooooo.',
    ],
  },
  pillar: {
    palette: { o: '#22343a', s: '#6f9aa0', S: '#4a7076', l: '#a9cfd2' },
    rows: [
      '..........',
      '..oooooo..',
      '...olSo...',
      '...olSo...',
      '...olSo...',
      '...olSo...',
      '...olSo...',
      '...olSo...',
      '..oooooo..',
      '.oossssoo.',
    ],
  },
  sandbags: {
    palette: { o: '#4a3b24', s: '#c9b07a', S: '#9c8456', l: '#e0cc98' },
    rows: [
      '..........',
      '..........',
      '...oooo...',
      '..olssSo..',
      '.oooooooo.',
      'olssSolsSo',
      'osSSSosSSo',
      'oooooooooo',
      '..........',
      '..........',
    ],
  },
  gold: {
    palette: { o: '#6b4a10', y: '#e3b02e', Y: '#ffe489', d: '#a87a18' },
    rows: [
      '..........',
      '..........',
      '....oo....',
      '...oyYo...',
      '..oyyYyo..',
      '.oyYyyyyo.',
      'oyyyyYyydo',
      'odyyyyyddo',
      '.oooooooo.',
      '..........',
    ],
  },
}

/** Odds and ends lying about (the games' small props, carts): a sack, a crate and a jar. */
export const ODDS_AND_ENDS: Sprite = {
  palette: { o: '#3b2614', w: '#b88a52', W: '#8a6236', l: '#d4a86e', s: '#cdbb8e', S: '#a8946a', j: '#9c5a3c', J: '#6e3a26', b: '#55565c' },
  rows: [
    '..........',
    '..oo......',
    '.osso..oo.',
    '.osSso.ojj',
    'osssSo.ojJ',
    'osssSooooJ',
    'oSSSSowwWo',
    '.oooooolwW',
    '.....owwwW',
    '.....ooooo',
  ],
}

/** Odds and ends inside a castle (the user's call: most of the props in stone halls are lights): a brass candlestick, lit. */
export const CANDLESTICK: Sprite = {
  palette: { o: '#3b2614', y: '#ffb52e', W: '#fff2a8', w: '#f2ead2', g: '#d8a93a', G: '#9c7424' },
  rows: [
    '....yy....',
    '...yWWy...',
    '....yy....',
    '...owwo...',
    '...owwo...',
    '..oGggGo..',
    '....gG....',
    '....gG....',
    '...oggo...',
    '..oGgggGo.',
  ],
}

/** Lava no one crosses: molten and glowing, a little crust drifting on it (burning ground and fire traps are cracked lava). */
export const LAVA_POOL: Sprite = {
  // Toned down (the user: the bright lava was hard to look at across a whole map).
  palette: { k: '#2e100c', r: '#8e3518', y: '#a8692c', w: '#b88a4e' },
  rows: [
    'rryyrrrryr',
    'ryywyrkkrr',
    'rryyyrrkry',
    'yrrrrrrryy',
    'yyrkkrryyw',
    'ryrrkryywy',
    'rrryrrrryy',
    'ywyyrrkkrr',
    'yyyrrrrkrr',
    'rryrrryrry',
  ],
}


export const ALL_SPRITES = {
  ...Object.fromEntries(Object.entries(VILLAGE_PIECES).map(([k, v]) => [`VILLAGE_PIECE_${k}`, v])),
  ...Object.fromEntries(Object.entries(CASTLE_PIECES).map(([k, v]) => [`CASTLE_PIECE_${k}`, v])),
  ...Object.fromEntries(Object.entries(HOUSE_PIECES).map(([k, v]) => [`HOUSE_PIECE_${k}`, v])),
  ...Object.fromEntries(Object.entries(HOUSE_SIDE_PIECES).map(([k, v]) => [`HOUSE_SIDE_PIECE_${k}`, v])),
  ...Object.fromEntries(Object.entries(ROOFTOP_PIECES).map(([k, v]) => [`ROOFTOP_PIECE_${k}`, v])),
  ...Object.fromEntries(Object.entries(ROOFTOP_DOORS).map(([k, v]) => [`ROOFTOP_DOOR_${k}`, v])),
  CHIMNEY,
  ...Object.fromEntries(Object.entries(FOUNTAIN_PIECES).map(([k, v]) => [`FOUNTAIN_PIECE_${k}`, v])),
  ...Object.fromEntries(Object.entries(MARKET_STALL).map(([k, v]) => [`MARKET_STALL_${k}`, v])),
  ...Object.fromEntries(Object.entries(HOUSE_VARIANTS).flatMap(([k, vs]) => vs.map((v, i) => [`HOUSE_VARIANT_${k}${i}`, v]))),
  ...Object.fromEntries(Object.entries(HOUSE_FRONT).map(([k, v]) => [`HOUSE_FRONT_${k}`, v])),
  ...Object.fromEntries(Object.entries(CHURCH_PIECES).map(([k, v]) => [`CHURCH_PIECE_${k}`, v])),
  ...Object.fromEntries(Object.entries(CAMP_PIECES).map(([k, v]) => [`CAMP_PIECE_${k}`, v])),
  ...Object.fromEntries(COAST_VARIANTS.map((v, i) => [`COAST_VARIANT_${i}`, v])),
  ...Object.fromEntries(Object.entries(PROP_SPRITES).map(([k, v]) => [`PROP_${k}`, v])),
  ...Object.fromEntries(Object.entries(FLOOR_PATTERNS).flatMap(([k, vs]) => vs.map((v, i) => [`FLOOR_PATTERN_${k}${i}`, v]))),
  SNOW_TREE, SNOW_THICK_WOOD, CRATES, ODDS_AND_ENDS, CANDLESTICK, LAVA_POOL, DEF_SIGIL, DEF2_SIGIL, RES_SIGIL, WATCHTOWER, CHURCH_FRONT_PLAIN, CAMP_FRONT_PLAIN, DOOR_MAT,
  ...Object.fromEntries(Object.entries(VILLAGE_VARIANTS).flatMap(([k, vs]) => vs.map((v, i) => [`VILLAGE_VARIANT_${k}${i}`, v]))),
  FOG, PUDDLE, STONE_PILLARS, MIASMA, FROST,
  SWAMP, FLOOR_TRAP, CRATER, ONAGER, FIRE_ORB,
  TOWN_HOUSE, MOUNTAIN, LAVA_CRACK, BARREL, BONES, PILLAR, TREE, VASE_MEDICINE, VASE_POISON, FORT, GATE, HOUSE, CHEST, DOOR, STAIRS, RUBBLE,
  SNOW_PEAK, HEAL, DRAGON_VEIN, SKULL, ALLY, NAMED_ENEMY, COMMON_ENEMY, COMMON_PAIR, DROP_BADGE, CAPTURE_BADGE, STEAL_BADGE,
  REINFORCEMENT, JOINER, COMMON_ALLY,
  ARMOR_HELM, DRAGON_HEAD, GRIMA, WING, HORSE_HEAD, MONSTER, SWORD_ICON, LANCE_ICON, AXE_ICON, TOME_ICON, MAGIC, REVERSED_TRIANGLE, NO_CRIT, NO_FOLLOW_UP,
  BRAVE, MIGHT_UP, CRACK, PAW, LION_HEAD, BOULDER, BURIED, SHINY, BALLISTA, PIT, SUPPLIES, FLAME,
  HEAL_FLOOR, DEF_FLOOR, DEF2_FLOOR, RES_FLOOR, BURNING_GROUND, SPIKES, ARMORY, VENDOR, SECRET_SHOP, ARENA, PEAK, BULWARK, GRAVE, FELL_FLOOR,
  THICK_WOOD, OLD_GATE, GATEWAY, RUBBLE_WALL, ICE_BLOCK, COTTAGE, SNAG, TUNNEL,
}

/** A ledge: two down-pointing chevrons, the way the ground drops. */
export const LEDGE: Sprite = {
  palette: { o: '#4a3a28' },
  rows: [
    '..........',
    '.o......o.',
    '..o....o..',
    '...o..o...',
    '....oo....',
    '.o......o.',
    '..o....o..',
    '...o..o...',
    '....oo....',
    '..........',
  ],
}

/** A torch on its post, lit. */
export const TORCH: Sprite = {
  palette: { o: '#3a2a1a', y: '#fde047', r: '#f97316', w: '#8b5a2b' },
  rows: [
    '....y.....',
    '...yry....',
    '...rrr....',
    '..ryyyr...',
    '...rrr....',
    '...owo....',
    '....w.....',
    '....w.....',
    '....w.....',
    '...ooo....',
  ],
}

/** A foe's own weapon: a bold red X, for what the player can never use. */
export const NOT_FOR_PLAYER: Sprite = {
  palette: { r: '#c0392b', d: '#8e2a20' },
  rows: [
    'rr......rr',
    'rrr....rrr',
    '.rrr..rrr.',
    '..rrrrrr..',
    '...rrrr...',
    '...rrrr...',
    '..rrrrrr..',
    '.rrr..rrr.',
    'rrr....rrr',
    'rr......rr',
  ],
}

/** A thicket (Genealogy of the Holy War: Avo 40, only barbarians, hunters and fliers get in): crowns crowded over brambles. */
export const THICKET: Sprite = {
  palette: { o: '#13260f', g: '#2e5e24', h: '#4f8a3c', b: '#5a3d22' },
  rows: [
    '.oo...oo..',
    'oggo.ogho.',
    'ohggoogggo',
    'ogggohgggo',
    '.ooggggoo.',
    '.oghggggo.',
    'oggggghggo',
    '.oooggooo.',
    'b.b.oo.b.b',
    '.b.b..b.b.',
  ],
}

/** A church (Genealogy of the Holy War: it heals a unit standing in it at the start of the turn): a chapel under its cross. */
export const CHURCH: Sprite = {
  palette: { y: '#f2d27a', r: '#6f5a8c', R: '#4e3f63', w: '#e8e0d0', d: '#6b4a2a', o: '#2b2430' },
  rows: [
    '....y.....',
    '...yyy....',
    '....y.....',
    '...rrR....',
    '..rrrrR...',
    '.rrrrrrR..',
    'oooooooooo',
    '.wwwddwww.',
    '.wwwddwww.',
    '.oooooooo.',
  ],
}

/**
 * A village (Shadow Dragon and the Blade of Light's and Mystery of the Emblem's: a wall tile over the village you visit, grassland on
 * both sides), drawn as the game draws it, over three tiles wide and two tall: a small house about a tile wide (the user: not a
 * mansion) with a low stone wall close round it, its door on the tile you visit (`middleFront`) and a path out through the gateway;
 * the wall's sides on the grass either side.
 */
const VILLAGE_HOUSE_PALETTE: Sprite['palette'] = {
  o: OUTLINE, r: '#c4462f', R: '#8e2a1c', D: '#6e2416', c: '#7a6656', w: '#efe6cf', n: '#5b7fa6', N: '#9fc0dc', d: '#6b4a2a',
  y: '#e0c060', s: '#d8cfbd', S: '#9a9080', P: '#c9b48a', h: '#3f7a32', g: '#6fae52',
}
export const VILLAGE_HOUSE: Record<'leftTop' | 'middleTop' | 'rightTop' | 'leftFront' | 'middleFront' | 'rightFront', Sprite> = {
  leftTop: {
    palette: VILLAGE_HOUSE_PALETTE,
    rows: [
      '..........',
      '..........',
      '..........',
      '..........',
      '..........',
      '......oooo',
      '.....sssso',
      '.....SSSor',
      '.....ooorr',
      '.....osooo',
    ],
  },
  middleTop: {
    palette: VILLAGE_HOUSE_PALETTE,
    rows: [
      '.......oo.',
      '......occo',
      '..ooooocco',
      '..orrRRcco',
      '.orrrRRRo.',
      'orrrrRRRRo',
      'RrRrRRDRDR',
      'rrrrrRRRRR',
      'rrrrrRRRRR',
      'oooooooooo',
    ],
  },
  rightTop: {
    palette: VILLAGE_HOUSE_PALETTE,
    rows: [
      '..........',
      '..........',
      '..........',
      '..........',
      '..........',
      'oooo......',
      'ossss.....',
      'RoSSS.....',
      'RRooo.....',
      'oooso.....',
    ],
  },
  leftFront: {
    palette: VILLAGE_HOUSE_PALETTE,
    rows: [
      '.....oso.o',
      '.....oso.o',
      '.....oso.o',
      '.....oso.o',
      '.....oso.o',
      '.....oso.o',
      '.....ooooo',
      '.....sssss',
      '.....SSSSS',
      '.....ooooo',
    ],
  },
  middleFront: {
    palette: VILLAGE_HOUSE_PALETTE,
    rows: [
      'wwwwwwwwww',
      'wNnooooNnw',
      'wnnoddonnw',
      'wwwodyowww',
      'wwwoddowww',
      'oooooooooo',
      'ooS.PP.Soo',
      'ssS.PP.Sss',
      'SSS.PP.SSS',
      'ooo.PP.ooo',
    ],
  },
  rightFront: {
    palette: VILLAGE_HOUSE_PALETTE,
    rows: [
      'o.oso.....',
      'o.oso.....',
      'o.oso.....',
      'o.oso.....',
      'o.oso.....',
      'o.oso.....',
      'ooooo.....',
      'sssss.....',
      'SSSSS.....',
      'ooooo.....',
    ],
  },
}

/** The same village razed (Shadow Dragon and the Blade of Light's Chapter 1): a burnt roof's beams over broken walls and rubble. */
const RUINED_VILLAGE_PALETTE: Sprite['palette'] = { k: '#2e2622', b: '#6b4a2a', w: '#c9bca4', a: '#8f8270', s: '#5f5548' }
export const RUINED_VILLAGE_TOP: Sprite = {
  palette: RUINED_VILLAGE_PALETTE,
  rows: [
    '..........',
    '..........',
    '...k......',
    '..kb...k..',
    '.kb.k.kb..',
    'kb...kb.k.',
    'w.....b..w',
    'wa.......w',
    'waw...a.ww',
    'wwa..awaww',
  ],
}
export const RUINED_VILLAGE_FRONT: Sprite = {
  palette: RUINED_VILLAGE_PALETTE,
  rows: [
    'wwa..awaww',
    'wa......aw',
    'w........w',
    'wa..s....w',
    'w..sas..aw',
    'wassaass.w',
    '.asaaasaa.',
    'aaksaaaksa',
    '.ssaassss.',
    '..........',
  ],
}

/** A door nothing opens (Gaiden's door-like walls, which no key or unit opens: it plays as a wall), iron-banded and handleless, so it
 * can't be taken for one that opens. */
export const SEALED_DOOR: Sprite = {
  palette: { o: '#2a2622', b: '#6e5a44', l: '#8c7558', i: '#3c3c40', h: '#8a8a90' },
  rows: [
    '..oooooo..',
    '.oblblbbo.',
    '.oblblbbo.',
    '.iihiihii.',
    '.oblblbbo.',
    '.oblblbbo.',
    '.iihiihii.',
    '.oblblbbo.',
    '.oblblbbo.',
    '.oooooooo.',
  ],
}

/**
 * A fort drawn whole with stairs up its front (Gaiden's small forts): the middle row is no castle's walls but the raised platform
 * the stairs climb to, steps down its sides and its floor in the middle (the user's call).
 */
export const STAIR_FORT_PIECES: Record<'d' | 'e' | 'f', Sprite> = {
  d: {
    palette: CASTLE_PIECE_PALETTE,
    rows: [
      '.oSSSSSSSS',
      '.oDSDSDSDS',
      '.oSSSSSSSS',
      '.oDSDSDSDS',
      '.oSSSSSSSS',
      '.oDSDSDSDS',
      '.oSSSSSSSS',
      '.oDSDSDSDS',
      '.oSSSSSSSS',
      '.oDSDSDSDS',
    ],
  },
  e: {
    palette: CASTLE_PIECE_PALETTE,
    rows: [
      'SSSSSSSSSS',
      'SDDDDDDDDS',
      'SDSSSSSSDS',
      'SDSSSSSSDS',
      'SDSSSSSSDS',
      'SDSSSSSSDS',
      'SDSSSSSSDS',
      'SDSSSSSSDS',
      'SDDDDDDDDS',
      'SSSSSSSSSS',
    ],
  },
  f: {
    palette: CASTLE_PIECE_PALETTE,
    rows: [
      'SSSSSSSSo.',
      'SDSDSDSDo.',
      'SSSSSSSSo.',
      'SDSDSDSDo.',
      'SSSSSSSSo.',
      'SDSDSDSDo.',
      'SSSSSSSSo.',
      'SDSDSDSDo.',
      'SSSSSSSSo.',
      'SDSDSDSDo.',
    ],
  },
}

/** A stone bridge's side under its deck (Gaiden's: a castle tile only fliers cross, drawn as the game draws it): the deck's edge, then
 * the dark under its arch. */
export const BRIDGE_SIDE: Sprite = {
  palette: { l: '#c8c8c0', s: '#9a9a92', d: '#6a6a64', k: '#1e1e24' },
  rows: [
    'llllllllll',
    'ssssssssss',
    'sdsssssdss',
    'ssssssssss',
    'sskkkkkkss',
    'skkkkkkkks',
    'skkkkkkkks',
    'kkkkkkkkkk',
    'kkkkkkkkkk',
    'kkkkkkkkkk',
  ],
}

/** A ship's mast seen from above (a tile only fliers cross): its yard across it with the sail furled on it, the mast's top over
 * them. */
export const MAST: Sprite = {
  palette: { o: '#2b1d10', b: '#8a6034', l: '#b4874a', s: '#ece2c8', S: '#c4b694' },
  rows: [
    '..........',
    '....oo....',
    '...obbo...',
    'oooobboooo',
    'osSsllsSso',
    'oSsSllSsSo',
    'oooobboooo',
    '...obbo...',
    '...obbo...',
    '....oo....',
  ],
}

/** A small stone fort seen from above (Gaiden's: walls only fliers cross round the fort tile and its stairs), by place: big stone
 * blocks in staggered courses, a capstone on each corner, the walls' inner faces in shadow (the user: its own design, not a
 * castle's towers). Its middle is the fort tile's own. */
const FORT_PALETTE: Sprite['palette'] = { o: '#2c2a30', L: '#dedcd2', M: '#b9b7ad', D: '#8a887f', S: '#5f5d57' }
export const FORT_PIECES: Record<'a' | 'b' | 'c' | 'd' | 'e' | 'f' | 'g' | 'h' | 'i', Sprite> = {
  a: {
    palette: FORT_PALETTE,
    rows: [
      'oooooooooo',
      'oLLLLLLLSM',
      'oLMMMMMMSM',
      'oLMMMMMMSM',
      'oLMMMMMMSD',
      'oLMMMMMMSL',
      'oLMMMMMMSM',
      'oLMMMMMMSM',
      'oSSSSSSSSM',
      'oDDDDDDDDD',
    ],
  },
  b: {
    palette: FORT_PALETTE,
    rows: [
      'oooooooooo',
      'DLMMMMDLMM',
      'DLMMMMDLMM',
      'DLMMMMDLMM',
      'DDDDDDDDDD',
      'LLLDLLLLLD',
      'MMMDLMMMMD',
      'MMMDLMMMMD',
      'MMMDLMMMMD',
      'DDDDDDDDDD',
    ],
  },
  c: {
    palette: FORT_PALETTE,
    rows: [
      'oooooooooo',
      'MLLLLLLLSo',
      'MLMMMMMMSo',
      'MLMMMMMMSo',
      'DLMMMMMMSo',
      'LLMMMMMMSo',
      'LLMMMMMMSo',
      'LLMMMMMMSo',
      'LSSSSSSSSo',
      'oDDDDDDDDo',
    ],
  },
  d: {
    palette: FORT_PALETTE,
    rows: [
      'oLLLDLLLLD',
      'oMMMDLMMMD',
      'oMMMDLMMMD',
      'oMMMDLMMMD',
      'oDDDDDDDDD',
      'oDLLLLLDLD',
      'oDLMMMMDLD',
      'oDLMMMMDLD',
      'oDLMMMMDLD',
      'oDDDDDDDDD',
    ],
  },
  e: {
    palette: FORT_PALETTE,
    rows: [
      '..........',
      '..........',
      '..........',
      '..........',
      '..........',
      '..........',
      '..........',
      '..........',
      '..........',
      '..........',
    ],
  },
  f: {
    palette: FORT_PALETTE,
    rows: [
      'SLDLLLLLDo',
      'SMDLMMMMDo',
      'SMDLMMMMDo',
      'SMDLMMMMDo',
      'SDDDDDDDDo',
      'SLLLLDLLLo',
      'SMMMMDLMMo',
      'SMMMMDLMMo',
      'SMMMMDLMMo',
      'SDDDDDDDDo',
    ],
  },
  g: {
    palette: FORT_PALETTE,
    rows: [
      'oLLLDLLLLD',
      'oLLLLLLLSM',
      'oLMMMMMMSM',
      'oLMMMMMMSM',
      'oLMMMMMMSD',
      'oLMMMMMMSL',
      'oLMMMMMMSM',
      'oLMMMMMMSM',
      'oSSSSSSSSM',
      'oooooooooo',
    ],
  },
  h: {
    palette: FORT_PALETTE,
    rows: [
      'SSSSSSSSSS',
      'DLMMMMDLMM',
      'DLMMMMDLMM',
      'DLMMMMDLMM',
      'DDDDDDDDDD',
      'LLLDLLLLLD',
      'MMMDLMMMMD',
      'MMMDLMMMMD',
      'MMMDLMMMMD',
      'oooooooooo',
    ],
  },
  i: {
    palette: FORT_PALETTE,
    rows: [
      'oLDLLLLLDo',
      'MLLLLLLLSo',
      'MLMMMMMMSo',
      'MLMMMMMMSo',
      'DLMMMMMMSo',
      'LLMMMMMMSo',
      'LLMMMMMMSo',
      'LLMMMMMMSo',
      'LSSSSSSSSo',
      'oooooooooo',
    ],
  },
}

/** A gate in a rampart that the chapter's script opens (Genealogy of the Holy War's passes: the user, a gate of its own, not the
 * rampart's bricks): wooden doors banded with iron between stone posts, by place in a gate two tiles wide or alone. */
const RAMPART_GATE_PALETTE: Sprite['palette'] = { o: '#2b2118', s: '#a8a296', S: '#6f6a60', w: '#9a6a3a', W: '#6e4a26', i: '#3a3634', h: '#d8b04a' }
export const RAMPART_GATE: Record<'left' | 'right' | 'alone', Sprite> = {
  left: {
    palette: RAMPART_GATE_PALETTE,
    rows: [
      'oooooooooo',
      'osSoWWWWWW',
      'osSowwwwwW',
      'osSowWwwwW',
      'osSoiiiiii',
      'osSowwwwwW',
      'osSowWwwhW',
      'osSoiiiiii',
      'osSowwwwwW',
      'oooooooooo',
    ],
  },
  right: {
    palette: RAMPART_GATE_PALETTE,
    rows: [
      'oooooooooo',
      'WWWWWWoSso',
      'WwwwwwoSso',
      'WwwwWwoSso',
      'iiiiiioSso',
      'WwwwwwoSso',
      'WhwwWwoSso',
      'iiiiiioSso',
      'WwwwwwoSso',
      'oooooooooo',
    ],
  },
  alone: {
    palette: RAMPART_GATE_PALETTE,
    rows: [
      'oooooooooo',
      'oSoWWWWoSo',
      'oSowwwWoSo',
      'oSowWwWoSo',
      'oSoiiiioSo',
      'oSowhwWoSo',
      'oSowwwWoSo',
      'oSoiiiioSo',
      'oSowwwWoSo',
      'oooooooooo',
    ],
  },
}

/** A castle one tile tall on open ground (Shadow Dragon's and New Mystery's, its gate below its middle: the user, the castle came out
 * chopped): blue-roofed towers either side of a keep with its banner and gateway, by place along the row. */
const CASTLE_ROW_PALETTE: Sprite['palette'] = { o: '#2b2622', S: '#b8ad98', L: '#d9cfba', k: '#2a2420', r: '#c0392b', B: '#7ea6d8', b: '#4c74a8' }
export const CASTLE_ROW: Record<'left' | 'middle' | 'right', Sprite> = {
  left: {
    palette: CASTLE_ROW_PALETTE,
    rows: [
      '..oBbo....',
      '.oBBbbo...',
      'oBBBbbbo..',
      'BBBBbbbbo.',
      'oLLLLLLoLL',
      'oSSSSSSoSS',
      'oSSkkSSoSS',
      'oSSSSSSoSS',
      'oSSSSSSoSS',
      'oooooooooo',
    ],
  },
  middle: {
    palette: CASTLE_ROW_PALETTE,
    rows: [
      '.S.S.S.S..',
      'oLLLLLLLLo',
      'oSSSrrSSSo',
      'oSSSrSSSSo',
      'oSSSSSSSSo',
      'oSSooooSSo',
      'oSSokkoSSo',
      'oSSokkoSSo',
      'oSSokkoSSo',
      'oSSokkoSSo',
    ],
  },
  right: {
    palette: CASTLE_ROW_PALETTE,
    rows: [
      '....oBbo..',
      '...oBBbbo.',
      '..oBBBbbbo',
      'SoBBBBbbbb',
      'LLoLLLLLLo',
      'SSoSSSSSSo',
      'SSoSSkkSSo',
      'SSoSSSSSSo',
      'SSoSSSSSSo',
      'oooooooooo',
    ],
  },
}

/** A drawbridge raised (Shadow Dragon and the Blade of Light's, Mystery of the Emblem's): its two leaves stood up on the banks, the
 * river between, as the games draw it; a key lowers it. Its leaves at the top and bottom (a crossing north to south), or at the sides. */
const RAISED_BRIDGE_PALETTE: Sprite['palette'] = { o: '#2b1d10', p: '#a8783e', b: '#7a5328', c: '#cfcfd4' }
export const RAISED_BRIDGE: Record<'ns' | 'ew', Sprite> = {
  ns: {
    palette: RAISED_BRIDGE_PALETTE,
    rows: [
      'oooooooooo',
      'opbpbpbpbo',
      'oooooooooo',
      '.c......c.',
      '..........',
      '..........',
      '.c......c.',
      'oooooooooo',
      'opbpbpbpbo',
      'oooooooooo',
    ],
  },
  ew: {
    palette: RAISED_BRIDGE_PALETTE,
    rows: [
      'ooo....ooo',
      'opoc..cobo',
      'obo....opo',
      'opo....obo',
      'obo....opo',
      'opo....obo',
      'obo....opo',
      'opo....obo',
      'oboc..copo',
      'ooo....ooo',
    ],
  },
}

/** An altar no unit can step onto (Shadow Dragon and the Blade of Light's Chapter 24): a stone dais with steps, a blue cloth over its
 * top, drawn over the wall it plays as. */
export const ALTAR: Sprite = {
  palette: { o: '#26222c', B: '#9fb8ee', b: '#4a63c8', s: '#e6d8c8', S: '#a89888' },
  rows: [
    '..........',
    '.oooooooo.',
    '.oBBBBBBo.',
    '.obbbbbbo.',
    '.obbobbbo.',
    'oooooooooo',
    'osssssssso',
    'oSSSSSSSSo',
    'osssssssso',
    'oooooooooo',
  ],
}

/** A doorway the chapter's script shuts (Mystery of the Emblem's Book 1 Endgame): its door standing open, for now. */
export const OPEN_DOOR: Sprite = {
  palette: { o: '#3a240f', b: '#9a6a35', l: '#c08a4a', k: '#15121a' },
  rows: [
    '..oooooo..',
    '.olbkkkko.',
    '.olbkkkko.',
    '.olbkkkko.',
    '.olbkkkko.',
    '.olbkkkko.',
    '.olbkkkko.',
    '.olbkkkko.',
    '.olbkkkko.',
    '.oooooooo.',
  ],
}
