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

  it('reads the special rules from the code: brave, a magic sword from range, status effects, effectiveness', () => {
    expect(get('Brave Sword').rules).toEqual(['Strikes twice in a row.'])
    // $84:DB25 swaps the whole item for the spell from 2 tiles away.
    expect(get('Flame Brand').rules).toEqual(["From 2 tiles away it attacks as Elfire: the spell's Mt, Hit and Wt, Mag against Res, in the magic triangle."])
    expect(get('Berserk Edge').rules).toEqual(["After a hit, a (30 - the foe's Res)% chance to inflict berserk."])
    // $84:E27F: crit 100 against what it's effective on, and a crit doubles the whole attack ($84:E6A9).
    expect(get('Ridersbane').rules).toEqual(['Against them every hit is a critical, the whole attack doubled, unless the foe has Nihil.'])
  })

  it("reads the holy weapons' bonuses and who may wield them, and the staves' effects and experience, from the ROM", () => {
    // $83:89E3: the record's +1 is the weapon, +10..+15 the bonuses while it's equipped; the Safeguard's +7 Def is in the code.
    expect(get('Tyrfing')).toMatchObject({ stats: { skl: 10, spd: 10, mdf: 20 }, skills: ['Miracle'], worth: null })
    expect(get('Yewfelle').skills).toEqual(['Renewal'])
    expect(get('Safeguard').stats).toEqual({ def: 7 })
    expect(get('Barrier Blade').stats).toEqual({ mdf: 7 })
    expect(get('Tyrfing').rules).toEqual(['Only a unit with its Major holy blood and a rank in swords can wield it.', "Can't be sold."])
    expect(get('Valkyrie Staff')).toMatchObject({ range: '—', worth: null, exp: 100 })
    expect(get('Valkyrie Staff').rules![0]).toBe('Only a unit with its Major holy blood and a rank in staves can wield it.')
    // A cast earns price / uses / 20 + 10 ($84:F99D); heals are 10 + the caster's Mag ($87:E86A).
    expect(get('Fortify Staff')).toMatchObject({ exp: 85, effect: "Restores 10 + the caster's Mag HP to every ally in range." })
    expect(get('Iron Sword').repair).toBe(20)
  })
})
