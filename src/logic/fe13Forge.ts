/**
 * Awakening's forge, as the program checks and prices it: the check (code.bin 0x263cbc) and the cost (0x26bce0).
 *
 * A forged weapon keeps its added Mt (+1 a step), Hit (+5) and Crit (+3). The check allows at most 5 steps in a stat and 8 in all,
 * and holds the forged weapon's Mt at 30, Hit at 200 and Crit at 50. The cost is the weapon's worth times each stat's n(n+1)/2 for its
 * n steps, added up and then halved, the fraction dropped.
 */
export type Fe13ForgeStat = 'mt' | 'hit' | 'crit'
export type Fe13ForgeSteps = Record<Fe13ForgeStat, number>

export const FE13_FORGE_STEP: Fe13ForgeSteps = { mt: 1, hit: 5, crit: 3 }
export const FE13_FORGE_MAX_STEPS = 5
export const FE13_FORGE_MAX_TOTAL = 8
export const FE13_FORGE_CAP: Fe13ForgeSteps = { mt: 30, hit: 200, crit: 50 }

const STATS: Fe13ForgeStat[] = ['mt', 'hit', 'crit']

/** What forging these steps costs (0x26bce0): the halving comes after the stats are added, so an odd worth loses at most 1 in all. */
export function fe13ForgeCost(worth: number, steps: Fe13ForgeSteps): number {
  return Math.floor((worth * STATS.reduce((sum, s) => sum + (steps[s] * (steps[s] + 1)) / 2, 0)) / 2)
}

/** The most steps a stat can take now (0x263cbc): 5, what's left of the 8, and what keeps it under its cap from the weapon's base. */
export function fe13ForgeMax(stat: Fe13ForgeStat, steps: Fe13ForgeSteps, base: number): number {
  const used = STATS.reduce((sum, s) => sum + steps[s], 0)
  const room = Math.max(0, Math.floor((FE13_FORGE_CAP[stat] - base) / FE13_FORGE_STEP[stat]))
  return Math.min(FE13_FORGE_MAX_STEPS, steps[stat] + FE13_FORGE_MAX_TOTAL - used, room)
}
