import { describe, expect, it } from 'vitest'
import { FE5_ITEM_SOURCES } from '../../data/fe5/fe5ItemSources'
import { FE5_LISTED } from '../../data/fe5/fe5Listed'
import { FE5_MAPS } from '../../data/fe5/fe5Maps'
import { FE5_FORK, FE5_STORY } from '../../data/fe5/fe5MapSet'
import { FE5_SUPPORTS } from '../../data/fe5/fe5Supports'
import { FE5_MOVE_CLASSES, FE5_TERRAIN } from '../../data/fe5/fe5Terrain'
import { FE5_TRIANGLE } from '../../data/fe5/fe5Triangle'
import { FE5_WEAPONS } from '../../data/fe5/fe5Weapons'
import type { ChapterMap } from '../../data/maps/types'
import { rowCodes } from '../maps'
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
    for (const m of FE5_MAPS) {
      for (const row of m.grid) {
        for (const code of rowCodes(row)) {
          const info = FE5_TERRAIN[code]
          expect(info, `${m.id} ${code}`).toBeDefined()
          for (const mc of FE5_MOVE_CLASSES) expect(mc in info!.move, `${code} ${mc}`).toBe(true)
        }
      }
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

  it('says when each gaiden chapter opens', () => {
    for (const id of ['fe5-2x', 'fe5-4x', 'fe5-8x', 'fe5-11x', 'fe5-12x', 'fe5-14x', 'fe5-21x', 'fe5-24x'])
      expect(map(id).notes.some((n) => n.startsWith('Opens if')), id).toBe(true)
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

  it('lists what turns up, with no foe-only marks: any foe can be captured and its items taken', () => {
    for (const x of FE5_LISTED) {
      expect(FE5_ITEM_SOURCES[x.name]?.length, x.name).toBeGreaterThan(0)
      expect(x.foeOnly, x.name).toBeUndefined()
    }
    expect(FE5_ITEM_SOURCES['Forseti']).toContainEqual({ mapId: 'fe5-23', kind: 'kit-later', text: 'Carried by Ced on joining' })
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
