import { describe, expect, it } from 'vitest'
import { FE1_ITEM_SOURCES } from '../../data/fe1/fe1ItemSources'
import { FE1_LISTED } from '../../data/fe1/fe1Listed'
import { FE1_MAPS } from '../../data/fe1/fe1Maps'
import { FE1_STORY } from '../../data/fe1/fe1MapSet'
import { FE1_MOVE_CLASSES, FE1_TERRAIN } from '../../data/fe1/fe1Terrain'
import { FE1_WEAPONS } from '../../data/fe1/fe1Weapons'
import type { ChapterMap, MapObject } from '../../data/maps/types'
import { applyChanges, rowCodes, sameTile, terrainAt, terrainInfo } from '../maps'
import { trueHit } from '../trueHit'

const map = (id: string) => FE1_MAPS.find((m) => m.id === id)!
const allUnits = (m: ChapterMap) => [...m.units, ...(m.reinforcements ?? []).flatMap((g) => g.units)]
const weapon = (name: string) => FE1_LISTED.find((w) => w.name === name)

describe("Shadow Dragon and the Blade of Light's maps", () => {
  it('has its 25 chapters in order, each map its own size', () => {
    expect(FE1_MAPS.map((m) => m.id)).toEqual(Array.from({ length: 25 }, (_, i) => `fe1-${i + 1}`))
    expect(FE1_STORY.maps.map((m) => m.id)).toEqual(FE1_MAPS.map((m) => m.id))
    for (const m of FE1_MAPS) {
      expect(m.grid.length, m.id).toBe(m.height)
      for (const row of m.grid) expect(row.length, m.id).toBe(m.width * 2)
    }
    // The cursor never reaches the stored map's outer ring (6:$A97B): Chapter 1 is stored 32 x 15, played 30 x 13.
    expect([map('fe1-1').width, map('fe1-1').height]).toEqual([30, 13])
  })

  it("gives every tile a terrain from the game's table, with a cost for every movement type", () => {
    const codes = new Set(FE1_MAPS.flatMap((m) => m.grid.flatMap(rowCodes)))
    for (const code of codes) {
      const info = FE1_TERRAIN[code]
      expect(info, code).toBeDefined()
      expect(Object.keys(info!.move).sort(), code).toEqual([...FE1_MOVE_CLASSES].sort())
    }
    // Grassland gives 5 Avoid where floors give none (15:$EBD8), and a fortress, castle gate or throne heals.
    expect(FE1_TERRAIN.tv?.avo).toBe(5)
    expect(FE1_TERRAIN.ta?.avo).toBe(0)
    expect(FE1_TERRAIN.bb?.note).toMatch(/3 to 10 HP/)
  })

  it('makes Marth seize a castle or throne in every chapter', () => {
    for (const m of FE1_MAPS) {
      expect(m.objectives.filter((o) => o.type === 'seize').length, m.id).toBe(1)
      expect(m.victory, m.id).toMatch(/^Seize the (castle|throne) with Marth$/)
    }
  })

  it('marks the recruits each chapter has, with who talks to them (the talk table at 15:$EDB5)', () => {
    const talk = (id: string, name: string) => allUnits(map(id)).find((u) => u.name === name)?.talk
    expect(talk('fe1-3', 'Navarre')).toBe('Recruit: talk with Caeda')
    expect(talk('fe1-13', 'Astram')).toBe('Recruit: talk with Midia')
    expect(talk('fe1-14', 'Catria')).toBe('Recruit: talk with Marth (only with Minerva in your army)')
    expect(talk('fe1-19', 'Tiki')).toBe('Recruit: talk with Bantu')
  })
})

describe("Shadow Dragon and the Blade of Light's weapons", () => {
  it('lists only what something in the game gives or a unit carries', () => {
    for (const w of FE1_LISTED) expect(FE1_ITEM_SOURCES[w.name]?.length, w.name).toBeGreaterThan(0)
    // Hellarn: no shop, chest, village, unit or foe has it.
    expect(FE1_WEAPONS.some((w) => w.name === 'Hellarn')).toBe(true)
    expect(weapon('Hellarn')).toBeUndefined()
  })

  it("drops a foe's second item to the unit that beats it (6:$AD79, 6:$935E), never its first", () => {
    expect(FE1_ITEM_SOURCES.Gradivus).toEqual([{ mapId: 'fe1-20', kind: 'drop', text: 'Dropped by Camus' }])
    expect(weapon('Falchion')?.foeOnly).toBeUndefined()
    // Gazzak wields a Steel Axe and drops his Vulnerary (seen in Mesen).
    expect(map('fe1-1').units.find((u) => u.type === 'boss')).toMatchObject({ name: 'Gazzak', drops: ['Vulnerary'] })
  })

  it('gives what seizing a castle or throne gives', () => {
    expect(FE1_ITEM_SOURCES.Parthia).toEqual([{ mapId: 'fe1-12', kind: 'event', text: 'Given when Marth seizes the throne' }])
  })

  it("triples an effective weapon's Mt and names the classes its list does", () => {
    expect(weapon('Rapier')?.effective).toEqual(['cavalier', 'armour'])
    expect(weapon('Ridersbane')?.effective).toEqual(['cavaliers-only'])
    expect(weapon('Falchion')?.effective).toEqual(['fe1-medeus'])
  })
})

describe("Shadow Dragon and the Blade of Light's shops, doors and drawbridges", () => {
  type Shop = Extract<MapObject, { type: 'shop' }>
  const shops = FE1_MAPS.flatMap((m) => m.objects.filter((o): o is Shop => o.type === 'shop').map((o) => ({ id: m.id, o })))
  const secret = shops.filter(({ o }) => o.kind === 'Secret shop')
  const everyone = (m: ChapterMap, t: [number, number]) => Object.values(terrainInfo(m, terrainAt(m, t)).move)

  it("names its shops as the other games' are, so the map draws and lists them (the commands at 11:$8457)", () => {
    // ぶきや, どうぐや and ひみつのみせ: the armory, the vendor (the Switch release's "Shop") and the secret shop.
    expect(new Set(shops.map(({ o }) => o.kind))).toEqual(new Set(['Armory', 'Vendor', 'Secret shop']))
    // The vendor sells items, staves and tomes: never a sword, lance, axe or bow, which only the armory sells.
    const category = new Map(FE1_WEAPONS.map((w) => [w.name, w.category]))
    const sold = (kind: string) => new Set(shops.filter(({ o }) => o.kind === kind).flatMap(({ o }) => o.stock.map((i) => category.get(i))))
    expect([...sold('Vendor')].filter(Boolean).sort()).toEqual(['Staff', 'Tome'])
    expect([...sold('Armory')].sort()).toEqual(['Axe', 'Ballista', 'Bow', 'Lance', 'Sword'])
    expect(FE1_ITEM_SOURCES.Fire).toContainEqual({ mapId: 'fe1-8', kind: 'shop', text: 'Sold at the vendor' })
    expect(FE1_ITEM_SOURCES.Thoron.filter((s) => s.kind === 'shop')).toEqual([
      { mapId: 'fe1-17', kind: 'shop', text: 'Sold at the secret shop, with a VIP Card' },
    ])
  })

  it('has four secret shops, open to a unit holding the VIP Card on its tile (11:$A2B2, $A2C2), as Fire Emblem Wiki places them', () => {
    expect(secret.map(({ id, o }) => [id, o.tile, o.stock])).toEqual([
      ['fe1-17', [25, 24], ['Master Key', 'Physic', 'Barrier', 'Thoron', 'Swarm']],
      ['fe1-21', [30, 23], ['Power Ring', 'Speed Ring', 'Secret Book', 'Goddess Icon']],
      ['fe1-23', [15, 27], ["Paladin's Honor", 'Hero Crest', "Bishop's Ring", "Orion's Bolt", 'Skydrake Whip']],
      ['fe1-24', [1, 1], ['Seraph Robe', 'Dracoshield', 'Talisman', 'Boots']],
    ])
    // "In the tile directly above the throne. Covered by a door that must be unlocked" (Chapters 17 and 23): a door no unit enters
    // until a key opens it onto floor (6:$9690), so its shop is reached once it's open.
    for (const { id, o } of secret.filter(({ id }) => id === 'fe1-17' || id === 'fe1-23')) {
      const m = map(id)
      expect(terrainAt(m, [o.tile[0], o.tile[1] - 1]), id).toBe('bc')
      expect(terrainAt(m, o.tile), id).toBe('ob')
      expect(m.objects, id).toContainEqual({ type: 'door', tile: o.tile })
      expect(everyone(m, o.tile).every((c) => c === null), id).toBe(true)
      const door = m.changes.find((c) => sameTile(c.tile.default, o.tile))!
      const opened = applyChanges(m, new Set([door.id]))
      expect(terrainAt(opened, o.tile), id).toBe('ta')
      expect(everyone(opened, o.tile).every((c) => c !== null), id).toBe(true)
      expect(o.note, id).toBe('On the door: once it is open, a unit holding the VIP Card can shop on its tile.')
    }
    // "The lone forest surrounded by mountains" (Chapter 21) and "the lone plain tile surrounded by mountains" (Chapter 24): tiles
    // units enter as they are.
    expect(terrainAt(map('fe1-21'), [30, 23])).toBe('ba')
    expect(terrainAt(map('fe1-24'), [1, 1])).toBe('tv')
    for (const { id, o } of secret.filter(({ id }) => id === 'fe1-21' || id === 'fe1-24')) {
      expect(everyone(map(id), o.tile).some((c) => c !== null), id).toBe(true)
      expect(o.note, id).toBeUndefined()
    }
  })

  it('draws every door and drawbridge, each previewing what its key leaves (6:$9690)', () => {
    const changes = FE1_MAPS.flatMap((m) => m.changes.map((c) => ({ m, c })))
    expect(changes.filter(({ c }) => c.id.startsWith('door-'))).toHaveLength(30)
    expect(changes.filter(({ c }) => c.id.startsWith('bridge-')).map(({ m, c }) => [m.id, c.tile.default])).toEqual([
      ['fe1-14', [18, 24]],
      ['fe1-20', [23, 16]],
    ])
    for (const { m, c } of changes) {
      const t = c.tile.default
      const door = c.id.startsWith('door-')
      expect(terrainAt(m, t), c.id).toBe(door ? 'ob' : 'tg')
      expect(c.patch, c.id).toEqual([{ tile: t, becomes: door ? 'ta' : 'tb' }])
      expect(c.effect, c.id).toMatch(door ? /Door Key, or a Thief holding a Master Key, opens it/ : /Bridge Key, or a Thief holding a Master Key, lowers it/)
    }
    // A door is the only door tile: no other tile on any map is drawn as one.
    const doorTiles = FE1_MAPS.flatMap((m) => m.grid.flatMap((row, i) => rowCodes(row).flatMap((code, x) => (code === 'ob' ? [[m.id, x + 1, m.height - i].join()] : []))))
    expect(doorTiles.sort()).toEqual(changes.filter(({ c }) => c.id.startsWith('door-')).map(({ m, c }) => [m.id, ...c.tile.default].join()).sort())
  })
})

describe("Shadow Dragon and the Blade of Light's hit roll", () => {
  it('rolls a byte × 10 / 25, held at 100, and hits at or below the displayed hit (15:$CE7E, $CD70)', () => {
    expect(trueHit('1rn-byte-fifths', 0).trueHitBasisPoints).toBe(0)
    expect(trueHit('1rn-byte-fifths', 1).trueHitBasisPoints).toBe(195)
    expect(trueHit('1rn-byte-fifths', 50).trueHitBasisPoints).toBe(5000)
    expect(trueHit('1rn-byte-fifths', 99).trueHitBasisPoints).toBe(9766)
    expect(trueHit('1rn-byte-fifths', 100).trueHitBasisPoints).toBe(10000)
  })
})
