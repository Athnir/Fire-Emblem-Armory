import type { Fe9Weapon } from '../data/fe9/types'

/** How many steps each stat was forged: Mt +1, Hit +5, Crit +3 and Wt −1 per step. */
export interface Fe9ForgeSteps {
  mt: number
  hit: number
  crit: number
  wt: number
}

export const NO_FORGE: Fe9ForgeSteps = { mt: 0, hit: 0, crit: 0, wt: 0 }

/** The most steps the forge allows: Mt +5, Hit +25, Crit +9, and Wt −5 but never below 1. */
export function fe9ForgeMaxSteps(w: Fe9Weapon): Fe9ForgeSteps {
  return { mt: 5, hit: 5, crit: 3, wt: Math.min(5, w.wt - 1) }
}

/** The forged weapon's Mt, Hit, Crit and Wt. */
export function fe9ForgedStats(w: Fe9Weapon, s: Fe9ForgeSteps) {
  return { mt: w.mt + s.mt, hit: w.hit + 5 * s.hit, crit: w.crit + 3 * s.crit, wt: w.wt - s.wt }
}

/**
 * What the forge charges, in gold: the base weapon's price plus the forging. Copied from the game's own
 * price routine (main.dol, 0x8001c284), which works on a "value" for each stat (Mt, Hit, Crit + 10,
 * and 23 − Wt so that lighter is higher). Each stat forged adds
 *   uses × price per use × |new value² − old value²| ÷ old value²,
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
