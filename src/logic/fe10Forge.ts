import type { TelliusWeapon } from '../data/fe9/types'

/**
 * Radiant Dawn's forge, from the game's own code (main.dol). Each stat can go down as well as up:
 * Mt and Wt by 1 a step, Hit by 5, Crit by 3, at most 5 steps either way (the forge screen, 0x80219d48
 * onward). A forged stat never drops below 1 (Crit below 0), and a stat can only be lowered while it's
 * above 1 (the stat getters 0x80110da8-0x80110eb0).
 */
export interface Fe10ForgeChange {
  mt: number
  hit: number
  crit: number
  wt: number
}

export const NO_CHANGE: Fe10ForgeChange = { mt: 0, hit: 0, crit: 0, wt: 0 }
export const FE10_FORGE_STEP: Fe10ForgeChange = { mt: 1, hit: 5, crit: 3, wt: 1 }
export const FE10_FORGE_LIMIT = 5
const FLOOR: Fe10ForgeChange = { mt: 1, hit: 1, crit: 0, wt: 1 }

/** The forged weapon's Mt, Hit, Crit and Wt. */
export function fe10ForgedStats(w: TelliusWeapon, c: Fe10ForgeChange): Fe10ForgeChange {
  const at = (k: keyof Fe10ForgeChange) => Math.min(255, Math.max(FLOOR[k], w[k] + c[k] * FE10_FORGE_STEP[k]))
  return { mt: at('mt'), hit: at('hit'), crit: at('crit'), wt: at('wt') }
}

/** Whether one more step down is allowed: within the limit, and the stat still above 1. */
export function fe10CanLower(w: TelliusWeapon, c: Fe10ForgeChange, k: keyof Fe10ForgeChange): boolean {
  return c[k] > -FE10_FORGE_LIMIT && fe10ForgedStats(w, c)[k] > 1
}

/**
 * What the forge charges, in gold: the base weapon's price plus, for each stat, steps² × a tenth of the
 * price, each rounded down on its own (main.dol 0x80112364). The game works in single-precision floats,
 * which Math.fround repeats: the tenth is 0.1f × price, and each stat's share is steps² × that.
 */
export function fe10ForgeCost(w: TelliusWeapon, c: Fe10ForgeChange): number {
  const tenth = Math.fround(Math.fround(0.1) * Math.fround(w.worth))
  const share = (steps: number) => Math.trunc(Math.fround(Math.fround(steps * steps) * tenth))
  return w.worth + share(c.mt) + share(c.hit) + share(c.crit) + share(c.wt)
}
