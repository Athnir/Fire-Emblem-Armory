import { describe, expect, it } from 'vitest'
// Every game's weapons, loaded with the file rather than inside a test: loading them inside one counted against its 5-second limit,
// which the full run's parallel load pushed past (5.3 s, against 0.8 s on its own).
import { ALL_WEAPONS } from '../../data/weapons'
import { ALL_SPRITES, LATER_SPRITES } from '../sprites'
import { effectivenessIcons } from '../weaponIcons'

describe('sprites', () => {
  for (const [name, sprite] of Object.entries({ ...ALL_SPRITES, ...LATER_SPRITES })) {
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
  it('give every effective weapon at least one icon', () => {
    for (const w of ALL_WEAPONS.filter((x) => x.effectiveness)) {
      expect(effectivenessIcons(w.effectiveness!.vs).length, `${w.name}: ${w.effectiveness!.vs}`).toBeGreaterThan(0)
    }
  })
})
