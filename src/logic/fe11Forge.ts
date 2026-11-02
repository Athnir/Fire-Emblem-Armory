/**
 * Shadow Dragon's forge, as the shop's forge menu works it out (arm9: the limits in each stat's menu class, shop::RefinePower /
 * RefineHit / RefineCritical / RefineWeight, and the price at 0x2056dc0).
 *
 * Each stat has a step: Mt 1, Hit 5, Crit 3, Wt 1. Changing a stat by d costs the weapon's price P times T(q) = q(q+1)/2 for the
 * q = d / step whole steps, plus the remainder's share of the next step (r / step of P x (T(q + 1) - T(q)), rounded down). The forge
 * costs (the four stats' costs + P) / 2.
 */
export type ForgeStat = 'mt' | 'hit' | 'crit' | 'wt'

export const FE11_FORGE_STEP: Record<ForgeStat, number> = { mt: 1, hit: 5, crit: 3, wt: 1 }

/** Each stat moves either way: Mt by up to 10 (0 to 30), Hit by up to 50 (0 to 200), Crit by up to 30 (0 to 50), Wt by up to 10
 * (1 to 30). */
export function fe11ForgeRange(stat: ForgeStat, base: number): [number, number] {
  const [by, lo, hi] = { mt: [10, 0, 30], hit: [50, 0, 200], crit: [30, 0, 50], wt: [10, 1, 30] }[stat]
  return [Math.min(base, Math.max(base - by, lo)), Math.max(base, Math.min(base + by, hi))]
}

const tri = (n: number) => (n * (n + 1)) >> 1

/** One stat's share for a change of `by` (either way). */
export function fe11ForgeStatCost(price: number, stat: ForgeStat, by: number): number {
  const step = FE11_FORGE_STEP[stat]
  const d = Math.abs(by)
  const q = Math.floor(d / step)
  const r = d % step
  const whole = price * tri(q)
  return whole + (r ? Math.floor((r * (price * tri(q + 1) - whole)) / step) : 0)
}

/** What forging costs: (each stat's share + the weapon's price) / 2. */
export function fe11ForgeCost(price: number, change: Partial<Record<ForgeStat, number>>): number {
  const sum = (Object.keys(FE11_FORGE_STEP) as ForgeStat[]).reduce((s, k) => s + fe11ForgeStatCost(price, k, change[k] ?? 0), 0)
  return (sum + price) >> 1
}
