import { describe, expect, it } from 'vitest'
import { FE4_WEAPONS } from '../../data/fe4/fe4Weapons'

const get = (name: string) => FE4_WEAPONS.find((w) => w.name === name)!

describe("Genealogy of the Holy War's weapons", () => {
  it("uses Lil' Nordion's names, by the ROM's item ids", () => {
    expect(get('Safeguard')).toMatchObject({ romId: 14 })
    expect(get('Helswath')).toMatchObject({ romId: 44 })
    expect(get('Mjölnir')).toMatchObject({ romId: 70, category: 'Thunder' })
  })

  it('reads the item table: Iron Sword and Mystletainn as the game has them', () => {
    expect(get('Iron Sword')).toMatchObject({ mt: 6, hit: 80, wt: 3, uses: 50, worth: 1000, rank: 'C', range: '1' })
    expect(get('Mystletainn')).toMatchObject({ mt: 30, rank: 'Holy', skills: ['Critical'], stats: { skl: 20, mdf: 10 } })
  })

  it('has unique ids and names, and leaves out the broken stubs, empty books and ballista arches', () => {
    expect(new Set(FE4_WEAPONS.map((w) => w.id)).size).toBe(FE4_WEAPONS.length)
    expect(new Set(FE4_WEAPONS.map((w) => w.name)).size).toBe(FE4_WEAPONS.length)
    expect(FE4_WEAPONS.some((w) => /Broken|Empty Book|Arch$/.test(w.name))).toBe(false)
  })

  it('marks what each weapon is effective against, from the table', () => {
    expect(get('Ridersbane').effective).toEqual(['horseback'])
    expect(get('Ironbane Sword').effective).toEqual(['armour'])
    expect(get('Wing Clipper').effective).toEqual(['flying'])
  })

  it('reads the special rules: brave, spells cast from range, status effects', () => {
    expect(get('Brave Sword').rules).toEqual(['Strikes twice in a row'])
    expect(get('Flame Brand').rules).toEqual(['Casts Elfire from range'])
    expect(get('Berserk Edge').rules).toEqual(['May inflict berserk on the foe'])
  })
})
