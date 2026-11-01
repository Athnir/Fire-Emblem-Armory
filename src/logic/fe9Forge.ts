import type { Fe9Weapon } from '../data/fe9/types'

/** How many steps each stat was forged: Mt +1, Hit +5, Crit +3 and Wt −1 per step; a step below 0 lowers the stat (Wt: heavier). */
export interface Fe9ForgeSteps {
  mt: number
  hit: number
  crit: number
  wt: number
}

export const NO_FORGE: Fe9ForgeSteps = { mt: 0, hit: 0, crit: 0, wt: 0 }

/** The most steps the forge allows: Mt +5, Hit +25, Crit +9, and Wt −5 but never below 1 (main.dol 0x80133fbc sets the
 * ranges, 0x80132cfc enforces them). */
export function fe9ForgeMaxSteps(w: Fe9Weapon): Fe9ForgeSteps {
  return { mt: 5, hit: 5, crit: 3, wt: Math.max(0, Math.min(5, w.wt - 1)) }
}

/** The fewest: the forge lowers a stat too, a step at a time while it's above its floor. Mt −5 but never below 1, Hit −25,
 * Crit −9 while it's above 0 (a Crit of 5 goes 5, 2, then −1, which counts as 0), and Wt 5 heavier. */
export function fe9ForgeMinSteps(w: Fe9Weapon): Fe9ForgeSteps {
  const down = (steps: number) => 0 - Math.max(0, Math.min(5, steps))
  return { mt: down(w.mt - 1), hit: down(Math.ceil((w.hit - 1) / 5)), crit: down(Math.min(3, Math.ceil(w.crit / 3))), wt: -5 }
}

/** The forged weapon's Mt, Hit, Crit and Wt, as the game reads them (0x8001d37c-0x8001d500): Mt, Hit and Wt at least 1, Crit
 * at least 0. */
export function fe9ForgedStats(w: Fe9Weapon, s: Fe9ForgeSteps) {
  return {
    mt: Math.max(1, w.mt + s.mt),
    hit: Math.max(1, w.hit + 5 * s.hit),
    crit: Math.max(0, w.crit + 3 * s.crit),
    wt: Math.max(1, w.wt - s.wt),
  }
}

/**
 * What the forge charges, in gold: the base weapon's price plus the forging. Copied from the game's own
 * price routine (main.dol, 0x8001c284), which works on a "value" for each stat (Mt, Hit, Crit + 10,
 * and 23 − Wt so that lighter is higher). Each stat forged adds
 *   uses × price per use × |new value² − old value²| ÷ old value²,
 * so lowering a stat costs gold as raising it does (a Crit pushed to −1 is priced at −1, not 0),
 * and the sum is multiplied by 2.5 and rounded down once at the end. The game does this in
 * single-precision floats; Math.fround repeats that, so the totals match to the gold.
 */
export function fe9ForgeCost(w: Fe9Weapon, s: Fe9ForgeSteps): number {
  const uses = w.uses ?? 0
  const pricePerUse = uses ? w.worth / uses : 0
  let sum = 0
  const add = (value: number, change: number) => {
    if (!change) return
    const square = Math.fround(value * value)
    const perSquare = Math.fround(pricePerUse / square)
    const grown = Math.fround(Math.abs((value + change) * (value + change) - square))
    sum = Math.fround(uses * Math.fround(grown * perSquare) + sum)
  }
  add(w.mt, s.mt)
  add(w.hit, 5 * s.hit)
  add(w.crit + 10, 3 * s.crit)
  add(23 - w.wt, s.wt)
  return w.worth + Math.trunc(Math.fround(sum * 2.5))
}
