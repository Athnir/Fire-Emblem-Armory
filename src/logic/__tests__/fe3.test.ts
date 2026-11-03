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
      // Gharnef only passes through Chapter 12: its script takes him off on turn 4's enemy phase ($8C:B115), so he's a named foe there.
      'fe3-1-11': ['Jiol'], 'fe3-1-12': [], 'fe3-1-13': ['Holstad'], 'fe3-1-14': ['Morzas'],
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
    expect(map('fe3-1-1').units.find((u) => u.name === 'Gazzak')).toMatchObject({ type: 'boss', carries: ['Iron Axe'] })
    // Chapter 1's opening walks Caeda in from the left while the camera scrolls 16 columns: she ends beside Marth.
    expect(map('fe3-1-1').forced?.find((f) => f.name === 'Caeda')?.tile).toEqual([26, 8])
    expect(map('fe3-1-4').units.find((u) => u.name === 'Matthis')?.talk).toBe('Recruit: talk with Lena')
    expect(map('fe3-1-4').objects).toContainEqual({
      type: 'village', tile: [22, 18], reward: '', note: 'Merric joins your army. Only Marth can visit it. Thief can raze it before you visit.',
    })
    expect(map('fe3-1-5').objects.filter((o) => o.type === 'chest')).toHaveLength(5)
    expect(map('fe3-2-e1').notes[0]).toContain('Binding Shield')
  })

  it("brings the spawn slots' reinforcements in when the scripts say, one group per arrival", () => {
    // Turn 14's event fills two slots alike: one group.
    const g = map('fe3-1-4').reinforcements!
    expect(g.map((x) => x.units.map((u) => u.name))).toEqual([['Pegasus Knight', 'Cavalier']])
    expect(g[0].when).toBe(
      "From turn 14's enemy phase, one on each tile at the start of each enemy phase while it is free, 16 on each in all; they stop " +
        'once Merach is defeated',
    )
    // Book 1's Chapter 8: turn 15 fills eight slots once each.
    expect(map('fe3-1-8').reinforcements!.map((x) => [x.when, x.units.length])).toEqual([
      ["From turn 15's enemy phase, one arrives on each tile at the start of the first enemy phase it is free", 8],
    ])
    // Slots with other odds are groups of their own (Book 1's Chapter 13).
    expect(map('fe3-1-13').reinforcements!.map((x) => (x.when as string).match(/\((\d+)% chance/)![1])).toEqual(['60', '70', '50', '80'])
    // An area event's groups show its area, held to the playable grid.
    for (const m of FE3_MAPS) {
      for (const x of m.reinforcements ?? []) {
        expect(/marked area/.test(x.when as string) === Boolean(x.areas?.length), `${m.id} ${x.id}`).toBe(true)
        for (const a of x.areas ?? []) {
          const [x1, y1, x2, y2] = a.rect
          expect(x1 >= 1 && y1 >= 1 && x2 <= m.width && y2 <= m.height && x1 <= x2 && y1 <= y2, `${m.id} ${x.id}`).toBe(true)
        }
      }
      // One group per arrival: no two groups share their time.
      const whens = (m.reinforcements ?? []).map((x) => x.when)
      expect(new Set(whens).size, m.id).toBe(whens.length)
    }
    expect(map('fe3-1-6').reinforcements![0].areas).toEqual([{ who: 'player', rect: [1, 1, 14, 8] }])
  })
})

describe("Mystery of the Emblem's map changes", () => {
  const at = (id: string, [x, y]: [number, number]) => {
    const m = map(id)
    return rowCodes(m.grid[m.height - y])[x - 1]
  }
  const change = (id: string, cid: string) => map(id).changes.find((c) => c.id === cid)!

  it("starts each map as its opening leaves it: no unit, starting tile or seize tile on a wall", () => {
    // Book 2's Chapter 20 opens by showing its whole castle (SHOW 0x10, $83:F204): before, nearly every tile was wall.
    for (const m of FE3_MAPS) {
      for (const u of m.units) expect(at(m.id, u.tile), `${m.id} ${u.name}`).not.toBe('wa')
      for (const s of m.starts) expect(at(m.id, s), `${m.id} start ${s}`).not.toBe('wa')
      for (const o of m.objectives) for (const t of o.tiles ?? []) expect(at(m.id, t), `${m.id} seize`).not.toBe('wa')
    }
    // The Endgame's Earth Dragons stand on altars no unit moves onto: the summoning sigil's code, its stats kept.
    expect(map('fe3-2-e2-3').units.filter((u) => u.name === 'Earth Dragon').every((u) => at('fe3-2-e2-3', u.tile) === 'oi')).toBe(true)
  })

  it('starts the closed rooms under their roofs, each opened by a door, a chest, an area or a turn', () => {
    expect(Object.values(FE3_TERRAIN.ws!.move).every((c) => c === null)).toBe(true)
    const roofed = FE3_MAPS.filter((m) => m.grid.flatMap(rowCodes).includes('ws')).map((m) => m.id)
    expect(roofed).toEqual(['fe3-1-15', 'fe3-2-6', 'fe3-2-14', 'fe3-2-16', 'fe3-2-17', 'fe3-2-20', 'fe3-2-e2-1'])
    for (const id of roofed) {
      const m = map(id)
      const opened = new Set(m.changes.flatMap((c) => c.patch!.map((p) => p.tile.join())))
      for (let y = 1; y <= m.height; y++) for (let x = 1; x <= m.width; x++) if (at(id, [x, y]) === 'ws') expect(opened.has(`${x},${y}`), `${id} ${x},${y}`).toBe(true)
    }
  })

  it("opens doors and lowers drawbridges for a Thief of either army or a key, and says what each script's change waits for", () => {
    for (const m of FE3_MAPS)
      for (const c of m.changes.filter((c) => c.id.startsWith('door-'))) expect(at(m.id, c.tile.default!), `${m.id} ${c.id}`).toBe('ob')
    expect(change('fe3-1-15', 'door-4-25').effect).toBe(
      'A door: a Thief of either army, or a unit holding a Door Key, opens it, and the closed room behind it opens.',
    )
    // Drawbridges (TILE_OBJECTS kind 6): their +8 metatile is a bridge; Book 2's Chapter 3 lowers its whole bridge (SHOW 0x14).
    expect(change('fe3-1-11', 'bridge-17-25').patch).toEqual([{ tile: [17, 25], becomes: 'tb' }])
    expect(change('fe3-2-3', 'bridge-14-7').patch).toHaveLength(9)
    // The Book 1 Endgame's doors start open and shut on set turns, unless a unit stands there.
    expect(change('fe3-1-endgame', 'turn-4-14').effect).toMatch(/^At the start of the enemy phase on turns 5, 6 and 7, this door shuts unless/)
    // Twin villages: visiting one closes the other.
    expect(change('fe3-1-13', 'visit-12-22').effect).toBe('Visiting this village closes the one at (9, 22).')
    // Book 2's Chapter 14: Marth stopping on three tiles lifts three rooms' roofs.
    expect(map('fe3-2-14').changes.map((c) => c.effect)).toEqual([
      'When Marth stops on (5, 22), the closed room opens.',
      'When Marth stops on (19, 24), the closed room opens.',
      'When Marth stops on (28, 22), the closed room opens.',
    ])
  })
})

describe("Mystery of the Emblem's joins and gifts", () => {
  it("never shows a scene's cast as a unit: what an event loads and takes off again", () => {
    // Book 2's Chapter 1 brings Ogma and Catria on for a talk, Chapter 3 two Pallas, Chapter 14 Gotoh's scene ("Lena").
    expect(map('fe3-2-1').reinforcements!.flatMap((g) => g.units).some((u) => ['Ogma', 'Catria'].includes(u.name))).toBe(false)
    expect(map('fe3-2-3').reinforcements!.flatMap((g) => g.units).some((u) => u.name === 'Palla')).toBe(false)
    expect(map('fe3-2-14').joiners!.map((j) => j.name)).toEqual(['Tiki'])
    expect(FE3_ITEM_SOURCES['Bolganone'].some((s) => s.mapId === 'fe3-2-14')).toBe(false)
    expect(FE3_ITEM_SOURCES['Bolganone']).toContainEqual({ mapId: 'fe3-2-e2-3', kind: 'kit', text: 'Carried by Lena on joining' })
  })

  it('counts what joins or is given during or after a battle from the next chapter, the last chapter from itself', () => {
    expect(FE3_ITEM_SOURCES['Parthia']).toContainEqual({ mapId: 'fe3-1-10', kind: 'event-later', text: 'Given at the end of the chapter to Marth' })
    expect(FE3_ITEM_SOURCES['Excalibur']).toContainEqual({ mapId: 'fe3-1-4', kind: 'kit-later', text: 'Carried by Merric on joining' })
    // A talk swaps in its own record: the foe called Navarre in Book 2's Chapter 6 joins as Samuel.
    expect(FE3_ITEM_SOURCES['Aquarius']).toEqual([{ mapId: 'fe3-2-6', kind: 'kit-later', text: 'Carried by Samuel on joining' }])
    // A foe who starts the talk itself (Book 1's Chapter 11: Catria and Palla talk to Marth) is the recruit, with its gear.
    expect(map('fe3-1-11').units.filter((u) => u.talk?.startsWith('Recruit: talks to Marth')).map((u) => u.name)).toEqual(['Catria', 'Palla'])
    expect(FE3_ITEM_SOURCES['Killer Sword']).toContainEqual({ mapId: 'fe3-1-11', kind: 'kit-later', text: 'Carried by Catria on joining' })
    // No one joins a book twice.
    const joins = new Map<string, Set<string>>()
    for (const lst of Object.values(FE3_ITEM_SOURCES))
      for (const s of lst) {
        const who = s.text.match(/^Carried by (.+) on joining$/)?.[1]
        if (who) joins.set(`${who} ${s.mapId.split('-')[1]}`, new Set([...(joins.get(`${who} ${s.mapId.split('-')[1]}`) ?? []), s.mapId]))
      }
    for (const [who, at] of joins) expect([...at], who).toHaveLength(1)
  })
})

describe("Mystery of the Emblem's conditions and leavers", () => {
  const unit = (id: string, name: string) => map(id).units.find((u) => u.name === name)!

  it("says what each placement, talk and village asks first, read from the scripts' checks and the condition lists", () => {
    // The opening places Catria and Palla only with Minerva in your army (IF_PRESENT), and their talks ask the same (condition 3).
    expect(unit('fe3-1-11', 'Catria')).toMatchObject({
      note: 'Lv 3 Pegasus Knight. Placed only with Minerva in your army. Comes to Marth to talk.',
      talk: 'Recruit: talks to Marth, with Minerva in your army',
    })
    // Minerva's talk waits for Maria to join (flag 4: set by the opening, cleared by Marth's talk with Maria).
    expect(unit('fe3-1-8', 'Minerva').talk).toBe('Recruit: talk with Marth, once Marth has talked to Maria')
    // Sheena's lasts until a death sets flag 18 (the Soldiers' and Archers' character events, and Samson's).
    expect(unit('fe3-2-17', 'Sheena').talk).toBe('Recruit: talk with Marth, until Samson or any Soldier or Archer is defeated')
    // Carried flags: who was recruited or fell in an earlier chapter.
    expect(unit('fe3-2-6', 'Rickard').note).toMatch(/Placed only if Julian didn't talk to him in Chapter 5\. Doesn't move or attack\.$/)
    expect(unit('fe3-2-8', 'Jeorge').note).toMatch(/Placed only if Jeorge wasn't defeated in Chapter 5\.$/)
    // The Starlight village: Marth's alone (its who byte), holding both spheres (condition 1).
    expect(map('fe3-1-17').objects).toContainEqual(expect.objectContaining({
      tile: [26, 25], reward: 'Starlight',
      note: 'Only Marth can visit it, holding the Lightsphere and Starsphere (it takes them). Thief can raze it before you visit.',
    }))
    expect(FE3_ITEM_SOURCES['Starlight']).toContainEqual({ mapId: 'fe3-1-17', kind: 'village', text: 'Given at a village for the Lightsphere and Starsphere' })
  })

  it('reads the Endgame from the seize records, and what the deaths hand out', () => {
    expect(map('fe3-2-e1').notes[0]).toBe(
      "Opens if your army holds the Binding Shield when Marth seizes the throne in Book 2's Chapter 20; without it, the game ends there.",
    )
    expect(map('fe3-2-20').notes).toContain(
      "Once Hardin is defeated, if your army holds the Lifesphere, Lightsphere, Starsphere, Geosphere and Darksphere, Marth gets the " +
        "Binding Shield (they're taken).",
    )
    // The last throne waits for Medeus (condition 18: flag 9, set by the opening, cleared by his death).
    expect(map('fe3-2-e2-3').objectives[0].label).toBe('Seize the throne with Marth, once Medeus is defeated')
    expect(map('fe3-2-e2-3').victory).toBe('Defeat Medeus, then seize throne')
  })

  it('says who leaves, and when; a boss a turn always takes off only passes through', () => {
    for (const name of ['Minerva', 'Palla', 'Catria', 'Est']) {
      expect(unit('fe3-1-6', name).note).toMatch(/Leaves at the start of the enemy phase on turn 2\. Advances on your army, never attacking\.$/)
    }
    expect(unit('fe3-1-12', 'Gharnef')).toMatchObject({ type: 'named', note: 'Lv 10 Bishop. Leaves at the start of the enemy phase on turn 4.' })
    // He can't be hurt without the Starlight (Imhullu) and leaves first: his Falchion drops only in Chapter 18.
    expect(FE3_ITEM_SOURCES['Falchion'].some((s) => s.mapId === 'fe3-1-12')).toBe(false)
    expect(unit('fe3-2-1', 'Lorenz')).toMatchObject({ type: 'boss', note: 'Lv 1 General. Leaves when Marth talks to him.' })
    expect(map('fe3-2-e2-3').units.filter((u) => u.name === 'Earth Dragon').every((u) => u.note!.endsWith('Leaves once Medeus is defeated.'))).toBe(true)
  })
})

describe("Mystery of the Emblem's foes' AI", () => {
  const units = (id: string, name: string) => allUnits(map(id)).filter((u) => u.name === name)
  const unit = (id: string, name: string) => units(id, name)[0]

  it('marks the looters, from their movement scripts, with the chests they empty and the exits they leave by', () => {
    // Movement script 0x15 and on: LOOT 1 (after one chest), go to (30, 18), leave script 26 (a walk off the map, REMOVE).
    const thieves = units('fe3-1-5', 'Thief')
    expect(thieves).toHaveLength(4)
    expect(thieves.every((u) => u.looter && u.note!.endsWith(
      'Goes for the chests, emptying what it reaches, until it has emptied one chest, then makes for (30, 18) and leaves the map, ' +
        'never attacking.',
    ) === (u.goesTo![0][1] === 18))).toBe(true)
    // Book 1's Chapter 8: its leave script 25 opens a door instead of taking it off.
    expect(unit('fe3-1-8', 'Thief').note).toBe(
      'Lv 7. Goes for the chests, emptying what it reaches, then makes for (19, 20) and opens the door at (19, 21), then makes for ' +
        '(18, 28) and leaves the map, never attacking.',
    )
    // The chests in Book 1's Chapter 15's closed rooms count: its thieves walk to the tiles that open them, then loot.
    expect(units('fe3-1-15', 'Thief').every((u) => u.looter && /^Lv \d+\. Heads for \(\d+, \d+\), then goes for the chests/.test(u.note!))).toBe(true)
    // A village names the looters on the map at the start: Book 1's Chapter 17's thief can raze the Starlight's village.
    expect(map('fe3-1-17').objects).toContainEqual(expect.objectContaining({
      tile: [26, 25], note: 'Only Marth can visit it, holding the Lightsphere and Starsphere (it takes them). Thief can raze it before you visit.',
    }))
    for (const m of FE3_MAPS) {
      for (const u of allUnits(m)) {
        expect('_ai' in u, `${m.id} ${u.name}`).toBe(false)
        for (const [x, y] of u.goesTo ?? []) expect(x >= 1 && x <= m.width && y >= 1 && y <= m.height, `${m.id} ${u.name}`).toBe(true)
      }
    }
  })

  it('says who leaves the map, who comes to talk, and who never attacks (decision script 0x02)', () => {
    expect(unit('fe3-1-7', 'Pyrathi')).toMatchObject({
      note: 'Lv 1 Pirate. Makes for (30, 12) and leaves the map, never attacking.', goesTo: [[30, 12]],
    })
    expect(unit('fe3-1-7', 'Pyrathi').looter).toBeUndefined()
    // Decision scripts' 0x13: walk to that character and start the talk.
    expect(unit('fe3-1-5', 'Rickard').note).toBe('Lv 1 Thief. Comes to Marth to talk.')
    expect(unit('fe3-1-13', 'Xane').note).toMatch(/Comes to Marth to talk\.$/)
    expect(unit('fe3-2-4', 'Sirius').note).toBe('Lv 4 Paladin. Comes to Ogma to talk. Once Ogma is defeated, stops moving and attacking.')
    expect(unit('fe3-1-11', 'Catria').note).toMatch(/Comes to Marth to talk\.$/)
  })

  it('says what the events give the foes later (event command 0x18), with what sets it off', () => {
    expect(unit('fe3-2-7', 'Astram').note).toBe(
      'Lv 4 Hero. Doesn\'t move or attack. Once one of your units stops in the area from (1, 21) to (15, 30), advances on your army.',
    )
    expect(unit('fe3-1-8', 'Minerva').note).toBe(
      'Lv 1 Dragon Knight. Doesn\'t move or attack. Once Maria is defeated, advances on your army. Once Marth has talked to Maria, ' +
        'comes to Marth to talk.',
    )
    expect(unit('fe3-2-17', 'Sheena').note).toBe(
      "Lv 1 General. Doesn't move or attack. Once Samson or any Soldier or Archer is defeated, attacks what it can reach.",
    )
    // Book 2's Chapter 18: Marth's visit sends the Wolfguard off the map.
    expect(unit('fe3-2-18', 'Wolf').note).toMatch(/Once Marth visits the village at \(2, 7\), makes for \(12, 22\) and leaves the map, never attacking\.$/)
    expect(map('fe3-2-18').objects).toContainEqual(expect.objectContaining({
      tile: [2, 7],
      note: 'Wolf, Vyland, Sedgar and Roshea, with the Paladins and Horsemen, make for (12, 22) and leave the map, never attacking. ' +
        'Only Marth can visit it.',
    }))
  })

  it('reads a terrain goal from the tile under a roof, and names the nearest tile where one is nearest', () => {
    // The opening walks Gazzak out of his castle: his AI takes him back.
    expect(unit('fe3-1-1', 'Gazzak')).toMatchObject({ note: 'Lv 5 Pirate. Heads for the nearest castle tile, at (5, 9).', goesTo: [[5, 9]] })
    // Lang sits on his throne under his room's roof: no goal.
    expect(unit('fe3-2-6', 'Lang').note).toBe('Lv 10 General')
    expect(units('fe3-2-2', 'Dragon Knight').filter((u) => u.goesTo).map((u) => u.goesTo)).toEqual([[[23, 24]], [[8, 24]]])
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
