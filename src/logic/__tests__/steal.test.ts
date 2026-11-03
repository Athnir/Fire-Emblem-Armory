import { describe, expect, it } from 'vitest'
import { FE1_MAPS } from '../../data/fe1/fe1Maps'
import { FE10_MAPS } from '../../data/fe10/fe10Maps'
import { FE11_MAPS } from '../../data/fe11/fe11Maps'
import { FE13_MAPS } from '../../data/fe13/fe13Maps'
import { FE15_MAPS } from '../../data/fe15/fe15Maps'
import { FE16_MAPS } from '../../data/fe16/fe16Maps'
import { FE17_MAPS } from '../../data/fe17/fe17Maps'
import { FE3_MAPS } from '../../data/fe3/fe3Maps'
import { FE4_MAPS } from '../../data/fe4/fe4Maps'
import { FE5_MAPS } from '../../data/fe5/fe5Maps'
import { FE6_MAPS } from '../../data/fe6/fe6Maps'
import { FE6_WEAPONS } from '../../data/fe6/fe6Weapons'
import { FE7_MAPS } from '../../data/fe7/fe7Maps'
import { FE7_WEAPONS } from '../../data/fe7/fe7Weapons'
import { FE8_MAPS } from '../../data/fe8/fe8Maps'
import { FE8_WEAPONS } from '../../data/fe8/fe8Weapons'
import { FE9_MAPS } from '../../data/fe9/fe9Maps'
import { FATES_MAP_SET } from '../../data/maps'
import type { ChapterMap, Difficulty, MapUnit } from '../../data/maps/types'

const units = (m: ChapterMap): MapUnit[] => [...m.units, ...(m.reinforcements ?? []).flatMap((g) => g.units)]
const marked = (maps: ChapterMap[]) => maps.flatMap((m) => units(m).filter((u) => u.steal?.length).map((u) => ({ m, u })))
const on = (u: MapUnit, d: Difficulty) => !u.difficulties || u.difficulties.includes(d)
const steals = (maps: ChapterMap[], id: string, name: string, d: Difficulty = 'Normal') =>
  units(maps.find((m) => m.id === id)!)
    .filter((u) => u.name === name && on(u, d))
    .map((u) => u.steal ?? [])

// Items used up for a moment's effect: never rare, whatever sells them.
const MOMENTARY = /^(vulnerary|elixir|pure water|antitoxin|torch|door key|chest key|lockpick|mine|light rune|herb|concoction|olivi grass|panacea|laguz stone|wild stone)$/i

describe('Foes holding something rare to steal', () => {
  it('are marked only where a foe can be robbed: a thief steals, or Thracia 776 captures', () => {
    // No steal at all (Fates, Awakening, Echoes, Shadow Dragon, Engage, the Famicom and SNES games but Thracia), or one that takes
    // only gold (Genealogy of the Holy War).
    for (const maps of [FE1_MAPS, FE3_MAPS, FE4_MAPS, FE11_MAPS, FE13_MAPS, FE15_MAPS, FE17_MAPS, FATES_MAP_SET.maps]) expect(marked(maps)).toEqual([])
    for (const maps of [FE5_MAPS, FE6_MAPS, FE7_MAPS, FE8_MAPS, FE9_MAPS, FE10_MAPS, FE16_MAPS]) expect(marked(maps).length).toBeGreaterThan(0)
  })

  it('are foes the battle keeps: never a green unit, a recruit (who brings its items), or a unit on a trial map', () => {
    for (const maps of [FE5_MAPS, FE6_MAPS, FE7_MAPS, FE8_MAPS, FE9_MAPS, FE10_MAPS, FE16_MAPS]) {
      for (const { m, u } of marked(maps)) {
        const what = `${m.id} ${u.name}`
        expect(u.type, what).not.toBe('ally')
        expect(u.talk ?? '', what).not.toMatch(/^Recruit/)
        expect(m.route, what).not.toBe('Trial')
        expect(new Set(u.steal).size, what).toBe(u.steal!.length)
        for (const item of u.steal!) {
          expect(u.drops ?? [], what).not.toContain(item)
          expect(item, what).not.toMatch(MOMENTARY)
        }
      }
    }
  })

  it('in the GBA games: only items, never a weapon or staff, none any armory or vendor sells (a secret shop still counts as rare)', () => {
    for (const [maps, weapons] of [
      [FE6_MAPS, FE6_WEAPONS],
      [FE7_MAPS, FE7_WEAPONS],
      [FE8_MAPS, FE8_WEAPONS],
    ] as const) {
      const names = new Set(weapons.map((w) => w.name))
      const sold = new Set(
        maps.flatMap((m) => m.objects.flatMap((o) => (o.type === 'shop' && o.kind !== 'Secret shop' ? (o.stock ?? []) : []))),
      )
      for (const { m, u } of marked(maps)) {
        for (const item of u.steal!) {
          expect(u.carries, `${m.id} ${u.name}`).toContain(item)
          expect(names.has(item), `${m.id} ${u.name}: ${item}`).toBe(false)
          expect(sold.has(item), `${m.id} ${u.name}: ${item}`).toBe(false)
        }
      }
    }
    // The Binding Blade's crests and stat boosters are sold only behind a Member Card (Chapters 16 and 21): still rare.
    expect(steals(FE6_MAPS, 'fe6-21', 'Murdock')).toEqual([['Knight crest']])
  })

  it("in Path of Radiance and Radiant Dawn: what the unit's note lists, weapons too", () => {
    for (const maps of [FE9_MAPS, FE10_MAPS])
      for (const { m, u } of marked(maps)) {
        const gear = (u.note ?? '').split(': ').slice(1).join(': ').split(/, |\. /)
        for (const item of u.steal!) expect(gear, `${m.id} ${u.name}`).toContain(item)
      }
  })

  it('matches the steals Fire Emblem Wiki lists on its chapter pages', () => {
    // The Binding Blade, The Ghosts of Bern: "Guiding Ring: Steal from Brunnya", a Druid's Blue Gem, a Manakete's Red Gem.
    expect(steals(FE6_MAPS, 'fe6-23', 'Brunnya')).toEqual([['Guiding ring']])
    expect(steals(FE6_MAPS, 'fe6-23', 'Druid')).toContainEqual(['Blue gem'])
    expect(steals(FE6_MAPS, 'fe6-23', 'Manakete')).toContainEqual(['Red gem'])
    // The Blazing Blade, Pirate Ship: Speedwings from Zoldam on Normal, a Guiding Ring on Hard; Night of Farewells' Bishop's Angelic Robe.
    expect(steals(FE7_MAPS, 'fe7-e-17', 'Zoldam', 'Normal')).toEqual([['Speedwings']])
    expect(steals(FE7_MAPS, 'fe7-e-17', 'Zoldam', 'Hard')).toEqual([['Guiding ring']])
    expect(steals(FE7_MAPS, 'fe7-e-26x', 'Bishop')).toContainEqual(['Angelic robe'])
    // The Sacred Stones: Waterside Renvall's Mage's Energy Ring; Revolt at Carcino's arriving Pegasus Knight's Talisman.
    expect(steals(FE8_MAPS, 'fe8-7', 'Mage')).toContainEqual(['Energy Ring'])
    expect(
      (FE8_MAPS.find((m) => m.id === 'fe8-eirika-10')!.reinforcements ?? []).flatMap((g) => g.units).find((u) => u.steal?.includes('Talisman')),
    ).toBeTruthy()
    // Radiant Dawn: "Secret Book: Steal from Maraj" (Tides of Intrigue); The Lost Heir's Soldier's Master Seal.
    expect(steals(FE10_MAPS, 'fe10-2-2', 'Maraj')).toEqual([['Secret Book']])
    expect(steals(FE10_MAPS, 'fe10-1-5', 'Soldier').flat()).toContain('Master Seal')
  })

  it("leaves out what can't be taken: a worn accessory, a recruit's items", () => {
    // Path of Radiance: a thief can't take what's equipped (the Steal tutorial), so Shiharam's Full Guard and Ena's Demi Band,
    // the accessories they wear, stay theirs (Fire Emblem Wiki lists only their Elixirs as steals).
    expect(steals(FE9_MAPS, 'fe9-20', 'Shiharam').flat()).not.toContain('Full Guard')
    expect(steals(FE9_MAPS, 'fe9-21', 'Ena').flat()).not.toContain('Demi Band')
    // Amelia joins with her Speedwing, Klein with his White Gem.
    for (const id of ['fe8-eirika-9', 'fe8-ephraim-9']) expect(steals(FE8_MAPS, id, 'Amelia').flat()).toEqual([])
    expect(steals(FE6_MAPS, 'fe6-11a', 'Klein').flat()).toEqual([])
  })
})
