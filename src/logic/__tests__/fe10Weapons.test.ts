import { describe, expect, it } from 'vitest'
import { FE10_WEAPONS } from '../../data/fe10/fe10Weapons'

const w = (name: string) => FE10_WEAPONS.find((x) => x.name === name)!

describe("Radiant Dawn weapons from the game's item table", () => {
  it('reads stats, uses and worth', () => {
    expect(w('Iron Sword')).toMatchObject({ rank: 'D', mt: 6, hit: 90, crit: 0, wt: 7, range: '1', uses: 50, worth: 500, wex: 2 })
    expect(w('Silver Sword')).toMatchObject({ rank: 'A', mt: 12, hit: 80, wt: 10, uses: 30 })
    expect(w('Tempest Blade')).toMatchObject({ rank: 'S', range: '1-2' })
    expect(w('Rexflame')).toMatchObject({ rank: 'SS', stats: { spd: 3 } })
  })

  it("reads personal weapons, stat bonuses and what can't break", () => {
    expect(w('Ragnell')).toMatchObject({ rank: 'Prf', uses: null, stats: { def: 5 } })
    expect(w('Ragnell').rules).toEqual(expect.arrayContaining(['Ike only', "Can't be sold", "Can't be stolen"]))
    expect(w('Amiti').rules).toEqual(expect.arrayContaining(['Elincia (and Renning) only', 'Strikes twice in a row, when attacking and when countering']))
    expect(w('Lughnasadh')).toMatchObject({ stats: { spd: 5 }, rules: expect.arrayContaining(['Leonardo only']) })
  })

  it("reads Radiant Dawn's own rules: crossbows, Marksman range, the Onager and magic effectiveness", () => {
    expect(w('Bowgun')).toMatchObject({ category: 'Crossbow', rank: '—', mt: 24, effective: ['flying'] })
    expect(w('Bowgun').rules.join(' ')).toMatch(/Mt alone/)
    // A Marksman reaches one tile further with an ordinary bow, not a longbow.
    expect(w('Iron Bow').rules).toContain('A Marksman can fire it at 2-3 range')
    expect(w('Double Bow').rules).toContain('A Marksman can fire it at 1-3 range')
    expect(w('Iron Longbow').rules.join(' ')).not.toMatch(/Marksman/)
    expect(w('Onager').rules).toContain('Always hits')
    expect(w('Onager').rules.join(' ')).toMatch(/Damage is its Mt alone/)
    // Fire against beasts, thunder against dragons, wind against fliers.
    expect([w('Fire').effective, w('Thunder').effective, w('Wind').effective]).toEqual([['beast'], ['dragon'], ['flying']])
    expect(w('Worm').category).toBe('Dark')
  })

  it('lists shops, one-off bargains, and what only a description said', () => {
    // What only a description said is a rule now; staves keep what they do.
    expect(w('Florete').rules.join(' ')).toMatch(/magic damage/)
    expect(w('Onager').rules.join(' ')).toMatch(/around the target/)
    expect(w('Heal').rules.join(' ')).toMatch(/HP/)
    expect(w('Bowgun').shop!.normal).toMatch(/^Part 3: Ch\.2/)
    // Serenes Forest's Part 3 bargains: Florete and Silencer in Ch.4, Wo Dao in Ch.5.
    expect(w('Florete').bargain).toEqual({ normal: 'Part 3: Ch.4', hard: 'Part 3: Ch.4' })
    expect(w('Silencer').bargain!.normal).toBe('Part 3: Ch.4')
    expect(w('Wo Dao').bargain!.normal).toBe('Part 3: Ch.5')
  })

  it('leaves out laguz strikes, the spirits and placeholders', () => {
    for (const name of ['Fang', 'Talon', 'Beak', 'Breath', 'Fire Tail', 'dummy']) expect(FE10_WEAPONS.some((x) => x.name === name), name).toBe(false)
  })
})
