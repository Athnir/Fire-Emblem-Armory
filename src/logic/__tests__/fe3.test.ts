import { describe, expect, it } from 'vitest'
import { FE3_ITEM_SOURCES } from '../../data/fe3/fe3ItemSources'
import { FE3_LISTED } from '../../data/fe3/fe3Listed'
import { FE3_MAPS } from '../../data/fe3/fe3Maps'
import { FE3_STORY } from '../../data/fe3/fe3MapSet'
import { FE3_SUPPORTS } from '../../data/fe3/fe3Supports'
import { FE3_MOVE_CLASSES, FE3_TERRAIN } from '../../data/fe3/fe3Terrain'
import { FE3_WEAPONS } from '../../data/fe3/fe3Weapons'
import type { ChapterMap } from '../../data/maps/types'
import { rowCodes } from '../maps'
import { trueHit } from '../trueHit'

const map = (id: string) => FE3_MAPS.find((m) => m.id === id)!
const allUnits = (m: ChapterMap) => [...m.units, ...(m.reinforcements ?? []).flatMap((g) => g.units)]
const ids = [
  ...Array.from({ length: 19 }, (_, i) => `fe3-1-${i + 1}`),
  'fe3-1-endgame',
  ...Array.from({ length: 20 }, (_, i) => `fe3-2-${i + 1}`),
  'fe3-2-e1',
  'fe3-2-e2-1',
  'fe3-2-e2-2',
  'fe3-2-e2-3',
]

describe("Mystery of the Emblem's maps", () => {
  it('has both books, each map its own size', () => {
    expect(FE3_MAPS.map((m) => m.id)).toEqual(ids)
    for (const m of FE3_MAPS) {
      expect(m.grid.length, m.id).toBe(m.height)
      for (const row of m.grid) expect(row.length, m.id).toBe(m.width * 2)
    }
    // The cursor never reaches the stored map's outer ring ($83:D822 and on): Chapter 1 is stored 32 x 15, played 30 x 13.
    expect([map('fe3-1-1').width, map('fe3-1-1').height]).toEqual([30, 13])
  })

  it("gives every tile a terrain from the game's table, with a cost for every movement type", () => {
    const codes = new Set(FE3_MAPS.flatMap((m) => m.grid.flatMap(rowCodes)))
    for (const code of codes) {
      const info = FE3_TERRAIN[code]
      expect(info, code).toBeDefined()
      for (const mc of FE3_MOVE_CLASSES) expect(mc in info!.move, `${code} ${mc}`).toBe(true)
    }
    // Castle gates, thrones and forts heal 3 to 9 HP ($93:DF10); the rest of a castle doesn't.
    for (const code of ['ol', 'bc', 'bb'] as const) expect(FE3_TERRAIN[code]!.note, code).toContain('3 to 9 HP')
    expect(FE3_TERRAIN.ou!.note).toBeUndefined()
    expect(FE3_TERRAIN.tn!.move).toMatchObject({ 'Cavaliers & horsemen': null, 'Pegasus & dragon knights': null, Lord: 1 })
  })

  it('places every unit inside its map', () => {
    for (const m of FE3_MAPS) {
      for (const u of allUnits(m)) {
        const [x, y] = u.tile
        expect(x >= 1 && x <= m.width && y >= 1 && y <= m.height, `${m.id} ${u.name} ${u.tile}`).toBe(true)
      }
    }
  })

  it('starts each chapter with the foes the Fire Emblem Wiki lists', () => {
    // Each chapter page's Mystery of the Emblem roster ("Enemy Units"), reinforcements left out.
    const wiki: Record<string, number> = {
      'fe3-1-1': 14, 'fe3-1-2': 17, 'fe3-1-3': 15,
      // The page's headline figure says 14; its own roster lists 16 (Merach, two Iron Knights, Matthis and twelve more).
      'fe3-1-4': 16,
      'fe3-1-5': 21, 'fe3-1-6': 16, 'fe3-1-7': 20, 'fe3-1-8': 19, 'fe3-1-9': 19, 'fe3-1-10': 21,
      // Palla and Catria come in at the start only with Minerva in your army (the turn-0 script asks), as she is by then.
      'fe3-1-11': 22,
      'fe3-1-12': 17, 'fe3-1-13': 20, 'fe3-1-14': 19, 'fe3-1-15': 22, 'fe3-1-16': 23, 'fe3-1-17': 19, 'fe3-1-18': 22, 'fe3-1-19': 23,
      'fe3-1-endgame': 23, 'fe3-2-1': 15,
      // Headline 14; the roster lists 15 (Lumel, two Dracoknights, five Cavaliers, three Soldiers, two Hunters, Warren, a Thief).
      'fe3-2-2': 15,
      'fe3-2-3': 17, 'fe3-2-4': 27, 'fe3-2-5': 32, 'fe3-2-6': 20, 'fe3-2-7': 25,
      // Headline "24*"; the roster lists 21, Jeorge and Astram (who come only if they lived through Chapters 5 and 7) included.
      'fe3-2-8': 21,
      'fe3-2-9': 24, 'fe3-2-10': 24, 'fe3-2-11': 21, 'fe3-2-12': 16, 'fe3-2-13': 21, 'fe3-2-14': 17, 'fe3-2-15': 31, 'fe3-2-16': 32,
      'fe3-2-17': 30, 'fe3-2-18': 29, 'fe3-2-19': 31, 'fe3-2-20': 32, 'fe3-2-e1': 23, 'fe3-2-e2-1': 30, 'fe3-2-e2-2': 24,
      // The page counts Medeus and the four bishops (5) and puts the Earth Dragons under reinforcements; the chapter's own list
      // places five Earth Dragons as it loads.
      'fe3-2-e2-3': 10,
    }
    for (const m of FE3_MAPS) expect(m.units.length, m.id).toBe(wiki[m.id])
  })

  it("names the bosses the wiki's chapter list gives", () => {
    const bosses = (id: string) => map(id).units.filter((u) => u.type === 'boss').map((u) => u.name)
    // The patch's spellings: Marions is the wiki's Emereus, Kanaris its Kannival, Vorzen its Volzhin, Holstad its Hollstadt, Rumel its
    // Lumel, Rucke its Lykke, Guile its Gail, Toras its Torus, Dahl its Dall, Nerring its Nehring.
    const wiki: Record<string, string[]> = {
      'fe3-1-1': ['Gazzak'], 'fe3-1-2': ['Gomer'], 'fe3-1-3': ['Hyman'], 'fe3-1-4': ['Merach'], 'fe3-1-5': ['Marions'],
      'fe3-1-6': ['Harmein'], 'fe3-1-7': ['Kanaris'], 'fe3-1-8': ['Zharov'], 'fe3-1-9': ['Khozen'], 'fe3-1-10': ['Vorzen'],
      'fe3-1-11': ['Jiol'], 'fe3-1-12': ['Gharnef'], 'fe3-1-13': ['Holstad'], 'fe3-1-14': ['Morzas'],
      // The wiki calls Tiki the boss; she isn't on the game's boss list ($93:FEB5): she's a talk recruit.
      'fe3-1-15': [],
      'fe3-1-16': ['Camus'], 'fe3-1-17': ['Michalis'], 'fe3-1-18': ['Gharnef'], 'fe3-1-19': ['Xemcel'], 'fe3-1-endgame': ['Medeus'],
      'fe3-2-1': ['Lorenz'], 'fe3-2-2': ['Rumel'], 'fe3-2-3': ['Rucke'], 'fe3-2-4': ['Guile'], 'fe3-2-5': ['Toras'], 'fe3-2-6': ['Lang'],
      'fe3-2-7': ['Dahl'], 'fe3-2-8': ['Hardin'], 'fe3-2-9': ['Yodel'], 'fe3-2-10': ['Arlen'], 'fe3-2-11': [], 'fe3-2-12': [],
      'fe3-2-13': [], 'fe3-2-14': [], 'fe3-2-15': ['Eibel'], 'fe3-2-16': ['Willow'], 'fe3-2-17': ['Sheena'], 'fe3-2-18': [],
      'fe3-2-19': ['Nerring'], 'fe3-2-20': ['Hardin'], 'fe3-2-e1': [], 'fe3-2-e2-1': [], 'fe3-2-e2-2': ['Gharnef'],
      'fe3-2-e2-3': ['Medeus'],
    }
    for (const m of FE3_MAPS) expect(bosses(m.id), m.id).toEqual(wiki[m.id])
  })

  it('reads the objectives, recruits, starting tiles and openings', () => {
    for (const m of FE3_MAPS) {
      expect(m.defeat, m.id).toBe('Marth is defeated')
      expect(m.objectives.filter((o) => o.type === 'seize'), m.id).toHaveLength(1)
      expect(m.starts, m.id).toContainEqual(m.corrinStart)
    }
    expect(map('fe3-1-1').objectives[0]).toMatchObject({ tiles: [[5, 9]], label: 'Seize the castle with Marth' })
    expect(map('fe3-1-1').units.find((u) => u.name === 'Gazzak')).toMatchObject({ type: 'boss', note: 'Lv 5 Pirate', carries: ['Iron Axe'] })
    // Chapter 1's opening walks Caeda in from the left while the camera scrolls 16 columns: she ends beside Marth.
    expect(map('fe3-1-1').forced?.find((f) => f.name === 'Caeda')?.tile).toEqual([26, 8])
    expect(map('fe3-1-4').units.find((u) => u.name === 'Matthis')?.talk).toBe('Recruit: talk with Lena')
    expect(map('fe3-1-4').objects).toContainEqual({ type: 'village', tile: [22, 18], reward: '', note: 'Merric joins your army.' })
    expect(map('fe3-1-5').objects.filter((o) => o.type === 'chest')).toHaveLength(5)
    expect(map('fe3-2-e1').notes[0]).toContain('Binding Shield')
  })

  it("brings the spawn slots' reinforcements in when the scripts say", () => {
    const g = map('fe3-1-4').reinforcements!
    expect(g.map((x) => x.units[0].name)).toEqual(['Pegasus Knight', 'Cavalier'])
    expect(g[0].when).toBe(
      'From turn 14, enemy phase: one at the start of each enemy phase while the tile is free, 16 in all; they stop once Merach is defeated',
    )
  })
})

describe("Mystery of the Emblem's story under the spoiler block", () => {
  it('walks Book 1, then Book 2, Endgame 1 and the three parts of Endgame 2', () => {
    expect(FE3_STORY.maps.map((m) => m.id)).toEqual(ids)
    expect(FE3_STORY.name(map('fe3-1-5'))).toBe('Book 1, Chapter 5')
    expect(FE3_STORY.name(map('fe3-1-endgame'))).toBe('Book 1, Endgame')
    expect(FE3_STORY.name(map('fe3-2-e2-2'))).toBe('Book 2, Endgame 2 (part 2)')
  })
})

describe("Mystery of the Emblem's weapons, hit and supports", () => {
  const w = (name: string) => FE3_WEAPONS.find((x) => x.name === name)!

  it('reads the item table: numbers, locks, the classes each item is for, and the weapons the battle code treats apart', () => {
    expect(w('Iron Sword')).toMatchObject({ mt: 5, hit: 90, wt: 2, uses: 42, worth: 420, rank: '1' })
    expect(w('Rapier')).toMatchObject({ rank: 'Prf', rules: ['Marth and Phina only'], effective: ['armour', 'cavalier'] })
    expect(w('Lady Sword').rules).toEqual(['Female Knights and Dancers only'])
    expect(w('Levin Sword').rules![0]).toContain('Mt alone')
    expect(w('Falchion')).toMatchObject({ uses: null, effective: ['dragons-all'] })
    expect(w('Wyrmslayer').effective).toEqual(['dragons-most'])
  })

  it('lists what turns up: drops included, foe-only only where nothing else gives it', () => {
    for (const x of FE3_LISTED) expect(FE3_ITEM_SOURCES[x.name]?.length, x.name).toBeGreaterThan(0)
    expect(FE3_ITEM_SOURCES.Falchion).toContainEqual({ mapId: 'fe3-1-18', kind: 'drop', text: 'Dropped by Gharnef' })
    expect(FE3_ITEM_SOURCES.Gradivus).toContainEqual({ mapId: 'fe3-2-20', kind: 'drop', text: 'Dropped by Hardin' })
    expect(FE3_LISTED.filter((x) => x.foeOnly).map((x) => x.name)).toEqual(['Imhullu', 'Dulam', 'Meteor', 'Swarm'])
    // Chapter 1's armory, as Serenes Forest's shop list has it.
    expect(map('fe3-1-1').objects.find((o) => o.type === 'shop')).toMatchObject({
      kind: 'Armory',
      stock: ['Iron Sword', 'Iron Lance', 'Javelin', 'Iron Bow', 'Iron Axe'],
    })
  })

  it('rolls hit with one scaled byte, a hit at or below the displayed hit', () => {
    expect(trueHit('1rn-byte', 0).trueHitBasisPoints).toBe(117)
    expect(trueHit('1rn-byte', 50).trueHitBasisPoints).toBe(5117)
    expect(trueHit('1rn-byte', 99).trueHitBasisPoints).toBe(10000)
    expect(trueHit('1rn-byte', 100).trueHitBasisPoints).toBe(10000)
  })

  it('gives supports +5 or +10 within 3 tiles, and the Geosphere +10', () => {
    expect(FE3_SUPPORTS).toMatchObject({ reach: 3, bonuses: [5, 10], geosphere: 10 })
  })
})
