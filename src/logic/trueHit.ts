import { FE16_TRUE_HIT } from './fe16HitTable'
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

/** The hit systems the games use. */
export type HitSystem = 'hybrid-fates' | '2rn' | '1rn' | '1rn-byte' | '1rn-byte-below' | '1rn-byte-fifths' | '2rn-mod100'

export function trueHit(system: HitSystem, input: number): TrueHitResult {
  return system === '2rn'
    ? twoRnTrueHit(input)
    : system === '2rn-mod100'
      ? mod100TwoRnTrueHit(input)
      : system === '1rn'
      ? oneRnTrueHit(input)
      : system === '1rn-byte'
        ? byteRnTrueHit(input)
        : system === '1rn-byte-below'
        ? byteBelowTrueHit(input)
        : system === '1rn-byte-fifths'
          ? fifthsRnTrueHit(input)
          : fatesTrueHit(input)
}

/** Clamps a typed displayed hit to what the game can show: 0-100, whole numbers. */
function clampDisplayed(input: number): Pick<TrueHitResult, 'displayed' | 'adjusted'> {
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
  return { displayed, adjusted }
}

/**
 * "2RN" (FE7 to FE13, including Path of Radiance and Radiant Dawn): the game rolls two numbers 0-99 and
 * hits if their average is below the displayed hit. Counted over all 10,000 pairs, so it's exact:
 * displayed 80 -> 92.20%. Source: https://fireemblemwiki.org/wiki/True_hit
 *
 * Checked in both Tellius games' own code (sys/main.dol). The attack routine (FE9 0x801a8a28, FE10
 * 0x8002ff14) rolls hit with a helper that draws two numbers and compares their average, rounded down
 * (FE9 0x8000cd88, FE10 0x80089de8), then crit with a single draw. Each number is (16-bit random x 100) >> 16,
 * so 0-99 isn't quite even (655 or 656 of 65,536 each), but that moves no true hit at two decimals.
 */
/**
 * Three Houses' "2RN": two numbers, a hit when their average (rounded down) is below the displayed hit, as in the GBA games. Read in
 * the game's own code: the attack (0xdc120) takes the hit chance (0xd9560, clamped to 0-100) and calls the roll at 0x5bb8a0, which
 * steps the battle's random number generator (an LCG, its own seed) twice and takes each number as (16-bit result) mod 100. The modulo
 * makes 0-35 a little likelier than 36-99, which lifts the true hit by up to 0.04 points (displayed 50: 50.54%, not 50.50%). The table
 * is counted over every state of the generator (scripts/fe16_hit_table.py).
 */
export function mod100TwoRnTrueHit(input: number): TrueHitResult {
  const { displayed, adjusted } = clampDisplayed(input)
  return { displayed, trueHitBasisPoints: FE16_TRUE_HIT[displayed], adjusted }
}

export function twoRnTrueHit(input: number): TrueHitResult {
  const { displayed, adjusted } = clampDisplayed(input)
  let hits = 0
  for (let a = 0; a < 100; a++) for (let b = 0; b < 100; b++) if ((a + b) / 2 < displayed) hits++
  return { displayed, trueHitBasisPoints: hits, adjusted }
}

/**
 * "1RN" (Genealogy of the Holy War): one number 0-99, a hit if it's below the displayed hit, so the displayed hit is exact.
 *
 * Checked in the game's own code: the hit routine ($84:E564) takes the attacker's accuracy less the defender's avoid (and less
 * Prayer's bonus, 10 x (11 - HP) when the defender has the skill and 10 HP or less), clamps it to 0-100 and calls the roll at
 * $84:EF9C once. That draws one number from the game's random table ($80:A73A: 55 values, each 0-99) and hits when it's lower.
 */
export function oneRnTrueHit(input: number): TrueHitResult {
  const { displayed, adjusted } = clampDisplayed(input)
  return { displayed, trueHitBasisPoints: displayed * 100, adjusted }
}

/**
 * Mystery of the Emblem's single roll: a random byte (0-255) scaled to 0-99 ((byte × 100) >> 8), a hit when that number is at or
 * below the displayed hit. Read in the game's own code: the roll at $93:EA87, compared at $83:B836 (a hit on lower or equal). The
 * scaling makes some of 0-99 come up three times in 256 and the rest twice, and "at or below" adds one: a displayed 50 hits 131 times
 * in 256 (51.17%), and a displayed 0 still hits 3 times in 256 (1.17%). Rounded to two decimals.
 */
export function byteRnTrueHit(input: number): TrueHitResult {
  const { displayed, adjusted } = clampDisplayed(input)
  let hits = 0
  for (let b = 0; b < 256; b++) if (Math.floor((b * 100) / 256) <= displayed) hits++
  return { displayed, trueHitBasisPoints: Math.round((hits * 10000) / 256), adjusted }
}

/**
 * Gaiden's single roll: a random byte (0-255) scaled to 0-99 ((100 × byte) >> 8, the multiply at 15:$C6C9 from the roll at 9:$85CC),
 * and a hit when that number is below the displayed hit (9:$8506: on carry, at or above, it misses; a displayed 0 never rolls). So a
 * displayed h lands ceil(2.56 h) times in 256: never less than shown, and at most half a point more (a displayed 80 is 80.08%, 99 is
 * 99.22%). Rounded to two decimals.
 */
export function byteBelowTrueHit(input: number): TrueHitResult {
  const { displayed, adjusted } = clampDisplayed(input)
  let hits = 0
  for (let b = 0; b < 256; b++) if (Math.floor((b * 100) / 256) < displayed) hits++
  return { displayed, trueHitBasisPoints: Math.round((hits * 10000) / 256), adjusted }
}

/**
 * Shadow Dragon and the Blade of Light's single roll: a random byte (0-255) times 10, divided by 25 (so × 2 / 5, 0-102), held at
 * 100, and a hit when that number is at or below the displayed hit; a displayed 0 never rolls. Read in the game's own code: the roll
 * at 15:$CE7E (the byte from $C04E), compared at 15:$CD70 (a hit on lower or equal, none when the hit is 0). Even numbers come up three
 * times in 256 and odd ones twice, and 100 six times, so low hit rates land slightly more often than shown and high ones slightly less:
 * a displayed 10 is 10.94%, 50 exactly 50%, 99 only 97.66%. Rounded to two decimals.
 */
export function fifthsRnTrueHit(input: number): TrueHitResult {
  const { displayed, adjusted } = clampDisplayed(input)
  if (displayed === 0) return { displayed, trueHitBasisPoints: 0, adjusted }
  let hits = 0
  for (let b = 0; b < 256; b++) if (Math.min(Math.floor((b * 10) / 25), 100) <= displayed) hits++
  return { displayed, trueHitBasisPoints: Math.round((hits * 10000) / 256), adjusted }
}

export function fatesTrueHit(input: number): TrueHitResult {
  const { displayed, adjusted } = clampDisplayed(input)
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
