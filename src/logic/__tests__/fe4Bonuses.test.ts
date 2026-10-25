import { describe, expect, it } from 'vitest'
import { FE4_BONUSES } from '../../data/fe4/fe4Bonuses'

describe("Genealogy of the Holy War's bonuses, read from its battle code", () => {
  it("matches Serenes' calculations page: leadership +10 per star from the second, Charisma and lover +10, triangle +20, 3 tiles", () => {
    expect(FE4_BONUSES.leadership).toEqual([0, 0, 10, 20, 30, 40])
    expect([FE4_BONUSES.charisma, FE4_BONUSES.lover, FE4_BONUSES.triangle, FE4_BONUSES.reach]).toEqual([10, 10, 20, 3])
  })

  it('has the physical and magic triangles, with light and dark beating the three elements', () => {
    expect(FE4_BONUSES.beats).toMatchObject({ Sword: ['Axe'], Axe: ['Lance'], Lance: ['Sword'], Fire: ['Wind'], Wind: ['Thunder'], Thunder: ['Fire'] })
    expect(FE4_BONUSES.beats.Light).toEqual(['Fire', 'Thunder', 'Wind'])
    expect(FE4_BONUSES.beats.Dark).toEqual(['Fire', 'Thunder', 'Wind'])
  })
})
