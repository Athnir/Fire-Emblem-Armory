import { describe, expect, it } from 'vitest'
import { FE5_ITEM_SOURCES } from '../../data/fe5/fe5ItemSources'
import { FE5_LISTED } from '../../data/fe5/fe5Listed'
import { FE5_MAPS } from '../../data/fe5/fe5Maps'
import { FE5_FORK, FE5_MAP_SET, FE5_STORY } from '../../data/fe5/fe5MapSet'
import { FE5_SUPPORTS } from '../../data/fe5/fe5Supports'
import { FE5_MOVE_CLASSES, FE5_TERRAIN } from '../../data/fe5/fe5Terrain'
import { FE5_TRIANGLE } from '../../data/fe5/fe5Triangle'
import { FE5_WEAPONS } from '../../data/fe5/fe5Weapons'
import type { ChapterMap } from '../../data/maps/types'
import { rowCodes, terrainAt } from '../maps'
import { walkFork } from '../spoiler'

const map = (id: string) => FE5_MAPS.find((m) => m.id === id)!
const allUnits = (m: ChapterMap) => [...m.units, ...(m.reinforcements ?? []).flatMap((g) => g.units)]
const foes = (m: ChapterMap) => m.units.filter((u) => u.type !== 'ally').length

describe("Thracia 776's maps", () => {
  it('has every chapter, each grid its own size', () => {
    expect(FE5_MAPS).toHaveLength(35)
    for (const m of FE5_MAPS) {
      expect(m.grid.length, m.id).toBe(m.height)
      for (const row of m.grid) expect(row.length, m.id).toBe(m.width * 2)
    }
    // The stored map keeps a column and a row the cursor never reaches ($83:BDD8): Chapter 1 is stored 23 x 21.
    expect([map('fe5-1').width, map('fe5-1').height]).toEqual([22, 20])
  })

  it("gives every tile a terrain from the game's table, with a cost for every movement type", () => {
    for (const code of new Set(FE5_MAPS.flatMap((m) => m.grid.flatMap(rowCodes)))) {
      const info = FE5_TERRAIN[code]
      expect(info, code).toBeDefined()
      for (const mc of FE5_MOVE_CLASSES) expect(mc in info!.move, `${code} ${mc}`).toBe(true)
    }
    // Indoors, mounted units and fliers have to dismount; forts, gates and thrones heal a flat 5 HP.
    expect(FE5_TERRAIN.tn!.move).toMatchObject({ Mounted: null, Fliers: null, Infantry: 1 })
    expect(FE5_TERRAIN.bb!.note).toContain('5 HP')
  })

  it('places every unit inside its map', () => {
    for (const m of FE5_MAPS) {
      for (const u of allUnits(m)) {
        const [x, y] = u.tile
        expect(x >= 1 && x <= m.width && y >= 1 && y <= m.height, `${m.id} ${u.name} ${u.tile}`).toBe(true)
      }
    }
  })

  it('starts each chapter with the enemies the Fire Emblem Wiki counts', () => {
    // Each chapter page's "enemy" figure, reinforcements left out.
    const wiki: Record<string, number> = {
      'fe5-1': 15, 'fe5-2': 12, 'fe5-2x': 16, 'fe5-3': 19, 'fe5-4': 18, 'fe5-4x': 28, 'fe5-5': 40,
      // The opening loads Raydrik, Tolman's squad of 17, six Lance Armors and two Soldiers: 26. The wiki's roster names the same
      // classes and gives 25, without saying which unit it leaves out.
      'fe5-6': 26,
      'fe5-7': 20,
      // Marty, out of your army since Chapter 3, is put back on the map as an enemy (the wiki counts him).
      'fe5-8': 12,
      'fe5-8x': 39, 'fe5-9': 31, 'fe5-10': 30, 'fe5-11': 28, 'fe5-11x': 36, 'fe5-12': 27, 'fe5-12x': 17,
      // The prep group holds 39 of Friege's units (Paulus, loaded after it, leaves before the battle); the wiki gives 38.
      'fe5-13': 39,
      'fe5-14': 38, 'fe5-14x': 7, 'fe5-15': 20, 'fe5-16a': 40, 'fe5-17a': 38, 'fe5-16b': 21, 'fe5-17b': 40, 'fe5-18': 41,
      'fe5-19': 36, 'fe5-20': 22, 'fe5-21': 39, 'fe5-21x': 30, 'fe5-22': 46, 'fe5-23': 17, 'fe5-24': 40, 'fe5-24x': 23,
      'fe5-final': 37,
    }
    for (const m of FE5_MAPS) expect(foes(m), m.id).toBe(wiki[m.id])
  })

  it("names the defeat conditions the wiki gives: Leif, Ced in Chapter 23, and the tiles enemies mustn't reach", () => {
    expect(map('fe5-1').defeat).toBe('Leif is defeated')
    expect(map('fe5-23').defeat).toBe('Leif or Ced is defeated')
    for (const id of ['fe5-9', 'fe5-13', 'fe5-14', 'fe5-20']) expect(map(id).defeat, id).toContain('or an enemy reaches')
  })

  it('reads the objectives, recruits and the openings', () => {
    expect(map('fe5-1').objectives).toEqual([{ type: 'seize', tiles: [[17, 16]], label: 'Seize the gate with Leif' }])
    expect(map('fe5-1').units.find((u) => u.name === 'Weismann')).toMatchObject({ type: 'boss', tile: [17, 16], carries: ['Longsword'] })
    expect(map('fe5-15').objectives[0]).toMatchObject({ type: 'arrive' })
    expect(map('fe5-4').objectives[0]).toMatchObject({ type: 'escape' })
    expect(map('fe5-8').units.find((u) => u.name === 'Marty')).toMatchObject({ type: 'named', talk: 'Recruit: talk with Osian or Halvan' })
  })

  it("never shows an end scene's cast as an arrival, nor starting tiles nothing uses", () => {
    // A script that ends the chapter only stages its end scene: Chapter 4's Ishtar, Julius, Veld and Manfroy, Chapter 9's Altena (on
    // the escape point) and Chapter 2x's Safy (on the gate Leif seizes, joining at the end).
    const arriving = (id: string) => [...(map(id).reinforcements ?? []).flatMap((g) => g.units), ...(map(id).joiners ?? [])].map((u) => u.name)
    for (const name of ['Ishtar', 'Julius', 'Veld', 'Manfroy']) expect(arriving('fe5-4')).not.toContain(name)
    expect(arriving('fe5-9')).not.toContain('Altena')
    expect(arriving('fe5-2x')).not.toContain('Safy')
    expect(FE5_ITEM_SOURCES['Heal']).toContainEqual({ mapId: 'fe5-2x', kind: 'kit-later', text: 'Carried by Safy, who joins at the end of the chapter' })
    // Chapter 4 has no preparations and its opening places everyone: its starting-position list is unused (and partly off the map).
    expect(map('fe5-4').starts).toEqual([])
    for (const m of FE5_MAPS)
      for (const [x, y] of m.starts) expect(x >= 1 && x <= m.width && y >= 1 && y <= m.height, `${m.id} (${x}, ${y})`).toBe(true)
  })

  it('says when each gaiden chapter opens', () => {
    for (const id of ['fe5-2x', 'fe5-4x', 'fe5-8x', 'fe5-11x', 'fe5-12x', 'fe5-14x', 'fe5-21x', 'fe5-24x'])
      expect(map(id).notes.some((n) => n.startsWith('Opens if')), id).toBe(true)
  })

  it("draws Chapter 24's secret shop, the game's only one, on the door its tile is", () => {
    // The Secret Shop command is offered on a shop's tile that's neither an armory's nor a vendor's ($87:8B59). Fire Emblem Wiki:
    // Life, Speed, Skill, Power and Shield Rings, "in the isolated top-right chamber", with the door unlocked.
    const secret = FE5_MAPS.flatMap((m) => m.objects.filter((o) => o.type === 'shop' && o.kind === 'Secret shop').map((o) => ({ id: m.id, o })))
    expect(secret).toHaveLength(1)
    expect(secret[0]).toMatchObject({
      id: 'fe5-24',
      o: { tile: [21, 42], stock: ['Life Ring', 'Speed Ring', 'Skill Ring', 'Strength Ring', 'Shield Ring'] },
    })
    expect(map('fe5-24').objects).toContainEqual({ type: 'door', tile: [21, 42] })
  })
})

describe("Thracia 776's map changes", () => {
  const changes = (id: string, prefix: string) => map(id).changes.filter((c) => c.id.startsWith(prefix))
  const becomes = (c: ChapterMap['changes'][number], t: [number, number]) =>
    c.patch!.find((p) => p.tile[0] === t[0] && p.tile[1] === t[1])?.becomes
  const opens = (m: ChapterMap, x: number, y: number) =>
    m.changes.some((c) => c.patch?.some((p) => p.tile[0] === x && p.tile[1] === y && p.becomes !== 'ws'))

  it('previews every door and drawbridge, each opened by a key, a thief with a Lockpick or the Unlock staff', () => {
    let doors = 0
    let bridges = 0
    for (const m of FE5_MAPS) {
      for (const c of m.changes.filter((x) => x.id.startsWith('door-') || x.id.startsWith('bridge-'))) {
        const tile = c.tile.default
        const door = c.id.startsWith('door-')
        // On the door ('ob') or raised drawbridge ('wo') tile, which opens onto floor, road or a magic floor (Chapter 24x's), or
        // lowers into a bridge.
        expect(terrainAt(m, tile), `${m.id} ${c.id}`).toBe(door ? 'ob' : 'wo')
        expect(door ? ['tn', 'ta', 'bw'] : ['tb'], `${m.id} ${c.id}`).toContain(becomes(c, tile))
        expect(c.effect, c.id).toMatch(door ? /Door Key, or with a Lockpick if it has Steal, and the Unlock staff/ : /Bridge Key/)
        if (door) doors++
        else bridges++
      }
      // Every door and drawbridge tile on the map opens: the Door and Drawbridge commands run its definition ($87:8F14, $87:8FF6).
      for (let y = 1; y <= m.height; y++)
        for (let x = 1; x <= m.width; x++)
          if (['ob', 'wo'].includes(terrainAt(m, [x, y])))
            expect(opens(m, x, y), `${m.id} (${x}, ${y})`).toBe(true)
    }
    expect([doors, bridges]).toEqual([103, 5])
    // The Unlock staff targets a door its user can see ($87:C3E1): on a fog map, once it's in sight.
    expect(changes('fe5-4x', 'door-')[0].effect).toContain('from any distance once it can be seen')
    // Chapter 5's arena door also opens a wall in the west; Chapter 8x's door at (10, 17) opens the one at (6, 20) with it.
    expect(map('fe5-5').changes.find((c) => c.id === 'door-23-20')!.effect).toContain('The wall at (1, 12) opens too.')
    expect(map('fe5-8x').changes.find((c) => c.id === 'door-10-17')!.effect).toContain('The door at (6, 20) opens with it.')
  })

  it('keeps rooms under a roof closed until a change opens them, the units inside out of sight', () => {
    for (const m of FE5_MAPS) {
      for (let y = 1; y <= m.height; y++)
        for (let x = 1; x <= m.width; x++)
          if (terrainAt(m, [x, y]) === 'ws')
            expect(opens(m, x, y), `${m.id} (${x}, ${y})`).toBe(true)
    }
    expect(FE5_TERRAIN.ws!.move).toMatchObject({ Fliers: null, Infantry: null })
    const closed = FE5_MAPS.filter((m) => m.grid.some((row) => rowCodes(row).includes('ws'))).map((m) => m.id)
    expect(closed).toEqual(['fe5-4', 'fe5-24', 'fe5-final'])
    // Chapter 4's upper room opens with its doors at (11, 24) and (12, 24); Dalsin waits inside.
    expect(map('fe5-4').changes.find((c) => c.id === 'door-11-24')!.effect).toContain('The closed room behind it opens with it.')
    expect(map('fe5-4').units.find((u) => u.name === 'Dalsin')!.note).toContain('Out of sight in a closed room')
    // The Final Chapter's throne room: once your units stand on all six magic seals, as your phase starts ($B9:BAED).
    const throne = map('fe5-final').changes.find((c) => c.id.startsWith('event-'))!
    expect(throne.effect).toMatch(/^At the start of the first player phase with your units on all six magic seals .+: the closed room opens/)
    expect(map('fe5-final').units.find((u) => u.name === 'Veld')!.note).toContain('Out of sight')
  })

  it("puts Chapter 24's Kia chest in the room only a civilian opens, on the other army's phase", () => {
    // Fire Emblem Wiki: the center-north door "can only be opened by one of the Civilians", one of the four boys picked on turn 5.
    const m = map('fe5-24')
    expect(m.objects).toContainEqual({ type: 'chest', tile: [10, 43], contents: 'Kia' })
    expect(m.objects.some((o) => o.type === 'hidden')).toBe(false)
    const room = m.changes.find((c) => c.id === 'event-10-38')!
    expect(terrainAt(m, [10, 43])).toBe('ws')
    expect(becomes(room, [10, 43])).toBe('oa')
    expect(becomes(room, [10, 38])).toBe('tn')
    expect(room.effect).toContain("only on the other army's phase")
    expect(room.effect).toContain('one of the four civilians')
    expect(FE5_ITEM_SOURCES['Kia']).toEqual([{ mapId: 'fe5-24', kind: 'chest', text: 'In a chest' }])
  })

  it('lets foes raze houses, villages and churches on the enemy phase, and break cracked walls that have no HP', () => {
    for (const m of FE5_MAPS) {
      for (const c of changes(m.id, 'raze-')) {
        expect(['oe', 'oc', 'oj', 'od'], `${m.id} ${c.id}`).toContain(terrainAt(m, c.tile.default))
        expect(becomes(c, c.tile.default), `${m.id} ${c.id}`).toBe('tm')
      }
      for (const c of changes(m.id, 'wall-')) {
        expect(c.trigger).toBe('breakable')
        expect(terrainAt(m, c.tile.default), `${m.id} ${c.id}`).toBe('wj')
        expect(c.effect).toContain("no HP: your units can't break it")
      }
    }
    expect(FE5_MAPS.reduce((n, m) => n + changes(m.id, 'raze-').length, 0)).toBe(57)
    // Fire Emblem Wiki, The Onslaught: "The east and west gates and the chipped sections of wall can be broken by an enemy", and
    // turn into wasteland.
    expect(changes('fe5-14', 'wall-').map((c) => becomes(c, c.tile.default))).toEqual(['te', 'te', 'te', 'te'])
    expect(changes('fe5-20', 'wall-')).toHaveLength(6)
    expect(map('fe5-21x').notes).toContain(
      'The cracked walls at (2, 7), (27, 7) and (11, 1) never break: no event of the chapter breaks them.',
    )
  })

  it("starts each map with its opening's changes made", () => {
    // Fire Emblem Wiki, Iz Coast: every village but "the one destroyed in the opening cutscene".
    expect(terrainAt(map('fe5-2'), [17, 13])).toBe('tm')
    expect(changes('fe5-2', 'raze-')).toHaveLength(3)
    // Chapter 11's courtyard doors start open; the trap shuts them. Fire Emblem Wiki, Fort Dandrum: "If Leif or a unit carrying him
    // waits in the northern courtyard (columns 5–11, rows 8–11...) before Kempf leaves the map, six doors ... appear".
    const doors: [number, number][] = [[8, 30], [8, 28], [8, 26], [8, 20], [8, 18], [8, 16]]
    for (const t of doors) expect(['tn', 'ta']).toContain(terrainAt(map('fe5-11'), t))
    const trap = map('fe5-11').changes.find((c) => c.zone)!
    expect(trap.zone).toEqual([5, 21, 11, 24])
    expect(trap.effect).toMatch(
      /^As soon as Leif, or a unit carrying Leif, stops in the area from \(5, 21\) to \(11, 24\), while Kempf is on the map:/,
    )
    for (const t of doors) expect(becomes(trap, t)).toBe('ob')
    // Chapter 11x's bottom door is opened by its opening.
    expect(terrainAt(map('fe5-11x'), [2, 1])).toBe('tn')
  })

  it("fills Chapter 4's chests at random with Leif's and Lifis's items and four the game adds", () => {
    // Fire Emblem Wiki, The Dungeon: "anywhere from 4 to 16 chests", the Javelin, Steel Sword, Rapier and Vulnerary in them.
    const m = map('fe5-4')
    const chests = m.objects.filter((o) => o.type === 'chest')
    expect(chests).toHaveLength(16)
    for (const c of chests) expect(terrainAt(m, c.tile)).toBe('oa')
    expect(m.notes[0]).toMatch(/^As the chapter opens, the items Leif and Lifis carry are taken from them/)
    for (const name of ['Javelin', 'Steel Sword', 'Rapier', 'Vulnerary'])
      expect(FE5_ITEM_SOURCES[name], name).toContainEqual({ mapId: 'fe5-4', kind: 'chest', text: 'In a chest' })
  })

  it('says what sets off the changes turns and areas make', () => {
    // Fire Emblem Wiki, Across the River: "When a player unit crosses the river to the east bank (acts within columns 21–30, rows
    // 1–23), the western bridge is removed".
    expect(changes('fe5-22', 'event-')[0].effect).toBe(
      'At the start of the first enemy phase after one of your units stops in the area from (21, 7) to (30, 29): the bridge is raised.',
    )
    expect(changes('fe5-17a', 'event-').map((c) => c.effect)).toEqual([
      "At the start of turn 10's enemy phase: a bridge is lowered.",
      "At the start of turn 15's enemy phase: the bridge is raised.",
      'As soon as a unit stops on (28, 22): the wall opens.',
    ])
    // Chapter 17B: Leif's visit to any of the eight houses closes them all; the gates open once 20,000 gold is paid.
    expect(changes('fe5-17b', 'visit-')[0]).toMatchObject({
      wide: true,
      effect: 'When Leif visits any of these eight houses, all eight close.',
    })
    expect(changes('fe5-17b', 'event-').some((c) => c.effect.includes('once 20,000 gold is paid at the house at (1, 5)'))).toBe(true)
    // Nothing a chapter's end scene does is drawn: Chapter 4's central room stays shut.
    expect(terrainAt(map('fe5-4'), [11, 14])).toBe('wa')
  })
})

describe("Thracia 776's foes worth capturing", () => {
  const unit = (id: string, name: string) => allUnits(map(id)).find((u) => u.name === name)!
  // What an armory or vendor sells in any chapter (the game's one secret shop, in Chapter 24, doesn't count).
  const sold = new Set(
    FE5_MAPS.flatMap((m) => m.objects.flatMap((o) => (o.type === 'shop' && o.kind !== 'Secret shop' ? o.stock : []))),
  )

  it('takes them by capture', () => {
    expect(FE5_MAP_SET.takeBy).toBe('capture')
  })

  it('marks only foes, with things they carry that no shop sells and that last', () => {
    let marked = 0
    for (const m of FE5_MAPS) {
      for (const u of allUnits(m)) {
        if (!u.steal) continue
        marked++
        expect(u.type, `${m.id} ${u.name}`).not.toBe('ally')
        expect(u.steal.length, `${m.id} ${u.name}`).toBeGreaterThan(0)
        for (const s of u.steal) {
          expect(u.carries, `${m.id} ${u.name}`).toContain(s)
          expect(sold.has(s), `${m.id} ${u.name} ${s}`).toBe(false)
          // Used up for a moment: never marked, even where nothing sells it.
          expect(['Vulnerary', 'Pure Water', 'Antitoxin', 'Torch', 'Door Key', 'Chest Key', 'Bridge Key', 'Lockpick']).not.toContain(s)
        }
      }
      for (const j of m.joiners ?? []) expect('steal' in j, `${m.id} ${j.name}`).toBe(false)
    }
    expect(marked).toBeGreaterThan(0)
  })

  it("doesn't mark a foe a talk recruits: its items come with it", () => {
    for (const m of FE5_MAPS) {
      for (const u of allUnits(m)) if (u.talk?.startsWith('Recruit')) expect(u.steal, `${m.id} ${u.name}`).toBeUndefined()
    }
    expect(unit('fe5-24', 'Galzus').carries).toContain('Master Sword')
  })

  it('names every item, the skill manuals at the end of the item table included', () => {
    for (const m of FE5_MAPS) for (const u of allUnits(m)) for (const c of u.carries ?? []) expect(c, m.id).not.toMatch(/^item 0x/)
    // Fire Emblem Wiki: Gustaf (Gustav) carries an Adept Manual.
    expect(unit('fe5-18', 'Gustav').carries).toContain('Adept Manual')
  })

  it("counts a weapon or staff only when fewer than 15 capturable foes in the whole game hold it (the user's call)", () => {
    // Thracia's shops sell so few weapons that "no shop sells it" alone would mark nearly every soldier.
    const arms = new Set(FE5_WEAPONS.map((w) => w.name))
    const holders = new Map<string, number>()
    for (const m of FE5_MAPS) for (const u of allUnits(m)) for (const s of u.steal ?? []) holders.set(s, (holders.get(s) ?? 0) + 1)
    for (const [s, n] of holders) if (arms.has(s)) expect(n, s).toBeLessThan(15)
    for (const common of ['Javelin', 'Short Lance', 'Jörmungandr', 'Battle Axe', 'Ridersbane', 'Thoron', 'Hel', 'Longbow', 'Greatsword'])
      expect(holders.has(common), common).toBe(false)
    // An item that lasts counts whatever its count: the scrolls and skill manuals.
    expect(unit('fe5-12', 'Colho').steal).toEqual(['Vantage Manual'])
  })

  it('marks the foes Fire Emblem Wiki says are captured, with what its inventories list', () => {
    // Cohen: Blizzard, Berserk, Restore, Master Lance. Brook: Master Lance, Armorslayer, Master Bow and a Ridersbane, which 34
    // capturable foes hold. Largo: a Greatbow beside a Greatlance and a Ridersbane (common) and a Master Seal, which shops sell.
    expect(unit('fe5-22', 'Cohen').steal).toEqual(['Blizzard', 'Berserk', 'Restore', 'Master Lance'])
    expect(unit('fe5-16a', 'Brook').steal).toEqual(['Master Lance', 'Armorslayer', 'Master Bow'])
    expect(unit('fe5-10', 'Largo').steal).toEqual(['Greatbow'])
    expect(unit('fe5-17b', 'Amalda').steal).toEqual(['Master Sword', "Bragi's Scroll"])
    // Veld in the Endgame: captured by a unit with at least 12 Con (his own 6 and the Dark Bishop's 5); his Jörmungandr is common.
    expect(unit('fe5-final', 'Veld').steal).toEqual(['Petrify'])
    // Palman, Lobos, Truman (Tolman) and Weismann can be captured too, but hold only common weapons.
    for (const [id, name] of [['fe5-17b', 'Palman'], ['fe5-3', 'Lobos'], ['fe5-6', 'Tolman'], ['fe5-1', 'Weismann']])
      expect(unit(id, name).steal, name).toBeUndefined()
    // Mounted foes once the Sleep staff can be yours (Salem's, from Chapter 12): Mueller's Master Sword, Farden's Flame Sword.
    expect(unit('fe5-17a', 'Muller').steal).toEqual(['Master Sword'])
    expect(unit('fe5-23', 'Faden').steal).toEqual(['Flame Sword', 'Master Lance'])
  })

  it("leaves unmarked the foes no unit of yours can capture", () => {
    // Con 20 (Fire Emblem Wiki: Gustaf, Zaom, List, Baldack, Wolf, Nikalaf and Zyle "cannot be captured due to his high
    // constitution"); Raydrik, and Mus made from him, too.
    for (const [id, name] of [
      ['fe5-18', 'Gustav'], ['fe5-21x', 'Zaun'], ['fe5-13', 'Liszt'], ['fe5-14', 'Baldach'], ['fe5-19', 'Wolfe'], ['fe5-17a', 'Nicolov'],
      ['fe5-15', 'Seil'], ['fe5-24', 'Raydrik'], ['fe5-final', 'Mus'],
    ])
      expect(unit(id, name).steal, name).toBeUndefined()
    // Mounted (Con 20) before a Sleep staff can be yours: Eisenau and Merlock, as the wiki says.
    expect(unit('fe5-7', 'Eisenhau').steal).toBeUndefined()
    expect(unit('fe5-9', 'Merloch').steal).toBeUndefined()
    expect(allUnits(map('fe5-6')).filter((u) => u.name === 'Cavalier').every((u) => !u.steal)).toBe(true)
    // The skill bit that bars capture: Kempf, Fred and Olwen.
    for (const [id, name] of [['fe5-11', 'Kempf'], ['fe5-10', 'Fred'], ['fe5-10', 'Olwen']])
      expect(unit(id, name).steal, name).toBeUndefined()
    // Mareeta leaves Chapter 5 once she's captured; Veld watches its arena from a room no unit can walk or fly into.
    expect(unit('fe5-5', 'Mareeta').steal).toBeUndefined()
    expect(unit('fe5-5', 'Veld').steal).toBeUndefined()
  })
})

describe("Thracia 776's story under the spoiler block", () => {
  it('walks Chapters 1 to 15 with their gaiden chapters, then 16A and 17A or 16B and 17B, then the rest', () => {
    expect(walkFork(FE5_FORK, '').story.maps).toHaveLength(21)
    const a = walkFork(FE5_FORK, 'a').story.maps.map((m) => m.id)
    expect(a).toContain('fe5-17a')
    expect(a).not.toContain('fe5-16b')
    expect(a[a.length - 1]).toBe('fe5-final')
    const reached = new Set([...a, ...walkFork(FE5_FORK, 'b').story.maps.map((m) => m.id)])
    for (const m of FE5_MAPS) expect(reached.has(m.id), m.id).toBe(true)
    expect(FE5_STORY.name(map('fe5-12x'))).toBe('Chapter 12x')
  })
})

describe("Thracia 776's weapons, triangle and supports", () => {
  const w = (name: string) => FE5_WEAPONS.find((x) => x.name === name)!

  it('reads the item table, with its prices worked out as the game does', () => {
    expect(w('Iron Sword')).toMatchObject({ mt: 6, hit: 70, wt: 6, uses: 40, worth: 2200 })
    expect(w('Light Brand').rules).toContain('Leif only')
    // Bragi's Blade's list of wielders has no end marker, so it runs on into Light Brand's: Leif can wield it too.
    expect(w("Bragi's Blade").rules![0]).toBe('Nanna, Dermott, Fergus and Leif only')
    expect(w('Flame Sword').rules![0]).toContain('fire magic from 2 tiles away')
  })

  it("lists what turns up; a weapon only foes hold that can be neither captured nor robbed of it is foe-only", () => {
    for (const x of FE5_LISTED) expect(FE5_ITEM_SOURCES[x.name]?.length, x.name).toBeGreaterThan(0)
    expect(FE5_ITEM_SOURCES['Forseti']).toContainEqual({ mapId: 'fe5-23', kind: 'kit-later', text: 'Carried by Ced on joining' })
    // The Loptrian Fang: Raydrik and Mus are at Con 20, and it weighs 20, which no thief's Con passes. The Shadow Sword: Chapter 5's
    // Mareeta, behind the arena door whose opening takes her away (Fire Emblem Wiki: stolen only through a glitch).
    expect(FE5_LISTED.filter((x) => x.foeOnly).map((x) => x.name).sort()).toEqual(['Loptrian Fang', 'Shadow Sword'])
    expect(FE5_ITEM_SOURCES['Shadow Sword']).toEqual([
      { mapId: 'fe5-5', kind: 'foe-held-later', text: 'Carried by Mareeta, a foe, arriving mid-chapter: neither capture nor Steal can take it' },
    ])
  })

  it("takes a foe's items by capture where it can be captured, else by Steal where a thief could", () => {
    // Fire Emblem Wiki: the Adept manual, "steal from enemy Gustaf" in Chapter 18; the Thrud Scroll, stolen from Baráth in
    // Chapter 20. Both are at Con 20 or barred from capture; Steal needs only more Spd than the foe and more Con than the item weighs.
    expect(FE5_ITEM_SOURCES['Adept Manual']).toEqual([
      { mapId: 'fe5-18', kind: 'foe', text: 'Carried by Gustav, a foe: a thief with more than 12 Spd can steal it' },
    ])
    expect(FE5_ITEM_SOURCES["Thrud's Scroll"]).toEqual([
      { mapId: 'fe5-20', kind: 'foe', text: 'Carried by Bharat, a foe: a thief with more than 8 Spd can steal it' },
    ])
    expect(FE5_ITEM_SOURCES['Venin Edge']).toContainEqual({
      mapId: 'fe5-11', kind: 'foe', text: 'Carried by Kempf, a foe: a thief with more than 12 Spd and 6 Con can steal it',
    })
    // Every foe's line says how, and one that can't be taken is only said where nothing else gives the item.
    for (const [name, list] of Object.entries(FE5_ITEM_SOURCES)) {
      const held = list.filter((s) => s.kind.startsWith('foe-held'))
      if (held.length) expect(held, name).toHaveLength(list.length)
      for (const s of list.filter((x) => x.kind.startsWith('foe')))
        expect(s.text, name).toMatch(
          s.kind.startsWith('foe-held') ? /: neither capture nor Steal can take it$/ : /: (capture to take it|a thief .+ can steal it)$/,
        )
    }
  })

  it("counts a unit's starting items once per route, where it joins", () => {
    const routes = (id: string) => (/16a|17a/.test(id) ? ['A'] : /16b|17b/.test(id) ? ['B'] : ['A', 'B'])
    const joins = new Map<string, Set<string>>()
    for (const list of Object.values(FE5_ITEM_SOURCES)) {
      for (const s of list.filter((x) => x.kind.startsWith('kit'))) {
        const who = s.text.match(/^Carried by (.+?)(,| on)/)![1]
        for (const r of routes(s.mapId)) joins.set(`${who} (${r})`, new Set([...(joins.get(`${who} (${r})`) ?? []), s.mapId]))
      }
    }
    for (const [who, chapters] of joins) expect([...chapters], who).toHaveLength(1)
  })

  it('gives only the advantaged side 5 hit and avoid; leadership 3 per star; supports +10 or +20 within 3 tiles', () => {
    expect([FE5_TRIANGLE.bonus, FE5_TRIANGLE.leadershipPerStar, FE5_TRIANGLE.charm]).toEqual([5, 3, 10])
    expect(FE5_TRIANGLE.beats.Light).toEqual(['Wind', 'Fire', 'Thunder'])
    expect(FE5_SUPPORTS).toMatchObject({ reach: 3, bonuses: [10, 20] })
  })
})
