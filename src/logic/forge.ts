/**
 * Fates' Smithy forges by combining two copies of the same weapon plus a category mineral into a
 * "+1" version, then two +1's into a +2, and so on through +7 — doubling the base-weapon copies
 * needed at every step (2, 4, 8...128) while the mineral cost per combine just climbs 1 through 7.
 * Source: https://serenesforest.net/fire-emblem-fates/my-castle/smithy/
 *
 * The site's per-rank table lists the INCREMENTAL Might/Hit/Crit gained by that specific combine
 * step (not the running total) — confirmed by reproducing its "247 minerals for a +7" figure via
 * the binary-tree mineral sum below, which only matches under the incremental reading.
 */
export interface ForgeStep {
  rank: number
  /** Smithy building level required to perform this combine (gated by Dragon Vein points spent). */
  smithyLevel: 1 | 2 | 3
  mtGain: number
  hitGain: number
  /** 0 for weapons that can't critical — the Smithy uses a Crit-less bonus table for those. */
  critGain: number
  /** Minerals consumed by this one combine operation. */
  mineralsPerCombine: number
}

const NON_CRIT_STEPS: ForgeStep[] = [
  { rank: 1, smithyLevel: 1, mtGain: 2, hitGain: 0, critGain: 0, mineralsPerCombine: 1 },
  { rank: 2, smithyLevel: 1, mtGain: 2, hitGain: 2, critGain: 0, mineralsPerCombine: 2 },
  { rank: 3, smithyLevel: 2, mtGain: 2, hitGain: 3, critGain: 0, mineralsPerCombine: 3 },
  { rank: 4, smithyLevel: 2, mtGain: 2, hitGain: 4, critGain: 0, mineralsPerCombine: 4 },
  { rank: 5, smithyLevel: 3, mtGain: 1, hitGain: 6, critGain: 0, mineralsPerCombine: 5 },
  { rank: 6, smithyLevel: 3, mtGain: 1, hitGain: 7, critGain: 0, mineralsPerCombine: 6 },
  { rank: 7, smithyLevel: 3, mtGain: 1, hitGain: 8, critGain: 0, mineralsPerCombine: 7 },
]

const CRIT_STEPS: ForgeStep[] = [
  { rank: 1, smithyLevel: 1, mtGain: 2, hitGain: 0, critGain: 0, mineralsPerCombine: 1 },
  { rank: 2, smithyLevel: 1, mtGain: 2, hitGain: 2, critGain: 0, mineralsPerCombine: 2 },
  { rank: 3, smithyLevel: 2, mtGain: 2, hitGain: 2, critGain: 1, mineralsPerCombine: 3 },
  { rank: 4, smithyLevel: 2, mtGain: 2, hitGain: 2, critGain: 2, mineralsPerCombine: 4 },
  { rank: 5, smithyLevel: 3, mtGain: 1, hitGain: 4, critGain: 3, mineralsPerCombine: 5 },
  { rank: 6, smithyLevel: 3, mtGain: 1, hitGain: 5, critGain: 4, mineralsPerCombine: 6 },
  { rank: 7, smithyLevel: 3, mtGain: 1, hitGain: 5, critGain: 5, mineralsPerCombine: 7 },
]

export function forgeSteps(canCrit: boolean): ForgeStep[] {
  return canCrit ? CRIT_STEPS : NON_CRIT_STEPS
}

/** The highest forge rank a Smithy level reaches (level 0: no Smithy yet): +2, +4, then +7. */
export function maxForgeRank(smithyLevel: number): number {
  return CRIT_STEPS.filter((s) => s.smithyLevel <= smithyLevel).length
}

export interface ForgedBonus {
  mt: number
  hit: number
  crit: number
}

/** Cumulative Might/Hit/Crit bonus at a given forge rank (0-7), summing every step up to it. */
export function cumulativeForgeBonus(canCrit: boolean, rank: number): ForgedBonus {
  const steps = forgeSteps(canCrit).filter((s) => s.rank <= rank)
  return steps.reduce(
    (acc, s) => ({ mt: acc.mt + s.mtGain, hit: acc.hit + s.hitGain, crit: acc.crit + s.critGain }),
    { mt: 0, hit: 0, crit: 0 },
  )
}

/** Base-weapon copies needed to forge a rank-N weapon from scratch (doubles every rank: 2, 4, 8...128). */
export function copiesRequiredFromScratch(rank: number): number {
  return 2 ** rank
}

/**
 * Per-combine mineral cost, after the Smithy's proficiency discount: "the character running the
 * Smithy will discount the required minerals for their proficient weapon type (but no less than 1
 * mineral)" — https://serenesforest.net/fire-emblem-fates/my-castle/smithy/. Always -1, floored at 1;
 * it doesn't scale with rank.
 */
export function discountedMineralCost(mineralsPerCombine: number, proficientSmith: boolean): number {
  return proficientSmith ? Math.max(1, mineralsPerCombine - 1) : mineralsPerCombine
}

/**
 * Total minerals needed to forge a rank-N weapon from scratch. Each of the 2^(N-k) combine
 * operations performed at intermediate rank k costs k minerals (k-1 if the Smith is proficient with
 * this weapon's category, floored at 1), so this is sum_{k=1}^{N} cost(k) * 2^(N-k) — not just
 * 1+2+...+N, since every lower-rank pair has to be built (and mineral-paid-for) independently before
 * it can itself be combined upward.
 */
export function mineralsRequiredFromScratch(canCrit: boolean, rank: number, proficientSmith = false): number {
  const steps = forgeSteps(canCrit).filter((s) => s.rank <= rank)
  return steps.reduce(
    (total, s) => total + discountedMineralCost(s.mineralsPerCombine, proficientSmith) * 2 ** (rank - s.rank),
    0,
  )
}
