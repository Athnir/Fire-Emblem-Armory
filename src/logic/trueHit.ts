/**
 * Fates' hit roll ("hybrid" system, shared with Shadows of Valentia): below a displayed 50 it's a
 * plain single roll, so true hit = displayed hit. From 50 up, the game draws one random number
 * 0–9999 and hits if it's below
 *
 *   hit × 100 + (40/3) × hit × sin((0.02 × hit − 1) × 180°)
 *
 * truncated to a whole number. Source: https://fireemblemwiki.org/wiki/True_hit
 *
 * The wiki writes the constant as "13.333", but that rounded value misses two rows of its own Fates
 * table by 0.01 (displayed 66 → 73.42 instead of 73.43, and 75 → 84.99 instead of 85.00). The
 * exact 40/3 with truncation reproduces all 50 rows (50–99), so that's what this uses.
 */
const HYBRID_CONSTANT = 40 / 3

export interface TrueHitResult {
  /** The displayed hit the calculation actually used, after clamping to 0–100 and dropping decimals. */
  displayed: number
  /** Real chance to hit, in hundredths of a percent (9014 = 90.14%). Kept as an integer so the two
   * decimals the game's 0–9999 roll can resolve are exact rather than float-rounded. */
  trueHitBasisPoints: number
  /** Why the input was adjusted, if it was: 'high' (above 100), 'low' (below 0), 'fraction'
   * (had decimals; displayed hit is always a whole number). Undefined when used as typed. */
  adjusted?: 'high' | 'low' | 'fraction'
}

export function fatesTrueHit(input: number): TrueHitResult {
  let displayed = input
  let adjusted: TrueHitResult['adjusted']
  if (displayed > 100) {
    displayed = 100
    adjusted = 'high'
  } else if (displayed < 0) {
    displayed = 0
    adjusted = 'low'
  } else if (!Number.isInteger(displayed)) {
    displayed = Math.trunc(displayed)
    adjusted = 'fraction'
  }

  if (displayed < 50) return { displayed, trueHitBasisPoints: displayed * 100, adjusted }

  const threshold =
    displayed * 100 + HYBRID_CONSTANT * displayed * Math.sin(((0.02 * displayed - 1) * 180 * Math.PI) / 180)
  // A roll of 0–9999 hits when below the threshold, so the hit count IS the truncated threshold,
  // capped at all 10,000 outcomes.
  return { displayed, trueHitBasisPoints: Math.min(Math.floor(threshold), 10000), adjusted }
}

/** "90.14" — always two decimals, the finest the 0–9999 roll can distinguish. */
export function formatBasisPoints(bp: number): string {
  return (bp / 100).toFixed(2)
}
