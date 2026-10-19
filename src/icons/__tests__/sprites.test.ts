import { describe, expect, it } from 'vitest'
import { ALL_SPRITES } from '../sprites'

describe('sprites', () => {
  for (const [name, sprite] of Object.entries(ALL_SPRITES)) {
    it(`${name} is 10×10 and only uses colours from its palette`, () => {
      expect(sprite.rows).toHaveLength(10)
      for (const row of sprite.rows) {
        expect(row, `${name}: "${row}"`).toHaveLength(10)
        for (const ch of row) if (ch !== '.') expect(sprite.palette, `${name} uses '${ch}'`).toHaveProperty(ch)
      }
    })
  }
})

describe('weapon effectiveness icons', () => {
  it('give every effective weapon at least one icon', async () => {
    const { ALL_WEAPONS } = await import('../../data/weapons')
    const { effectivenessIcons } = await import('../weaponIcons')
    for (const w of ALL_WEAPONS.filter((x) => x.effectiveness)) {
      expect(effectivenessIcons(w.effectiveness!.vs).length, `${w.name}: ${w.effectiveness!.vs}`).toBeGreaterThan(0)
    }
  })
})
