import type { Affinity } from './fe9Supports'

/*
 * Radiant Dawn's support bonuses. The affinity values are the Fire Emblem Wiki's and Serenes Forest's
 * (they agree): the same as Path of Radiance's except Heaven (Hit +9) and Earth (Avoid +7.5), and halves
 * round up instead of down. They aren't stored as a table in the game's files. The support point rules
 * are in the game's data: FE10Data.cms (LZ10), table RelianceParam.
 */
export const FE10_AFFINITIES: Affinity[] = [
  { name: 'Fire', atk: 0.5, def: 0, hit: 2.5, avoid: 0 },
  { name: 'Thunder', atk: 0, def: 0.5, hit: 0, avoid: 2.5 },
  { name: 'Wind', atk: 0, def: 0, hit: 2.5, avoid: 2.5 },
  { name: 'Water', atk: 0.5, def: 0.5, hit: 0, avoid: 0 },
  { name: 'Dark', atk: 0.5, def: 0, hit: 0, avoid: 2.5 },
  { name: 'Light', atk: 0, def: 0.5, hit: 2.5, avoid: 0 },
  { name: 'Heaven', atk: 0, def: 0, hit: 9, avoid: 0 },
  { name: 'Earth', atk: 0, def: 0, hit: 0, avoid: 7.5 },
]

/** A pair's bonus at a support level (C = 1, B = 2, A = 3): both affinities added, times the level, a half rounded up. */
export function fe10SupportBonus(a: Affinity, b: Affinity, level: number) {
  const total = (k: 'atk' | 'def' | 'hit' | 'avoid') => Math.floor((a[k] + b[k]) * level + 0.5)
  return { atk: total('atk'), def: total('def'), hit: total('hit'), avoid: total('avoid') }
}

/**
 * Support points, from RelianceParam (bytes 32 64 96 97 0f 1e 03 05 04 01 02 02 01 00 ff fe): the points
 * each level needs in total (50, 100, 150), what each action is worth for a middling pair, and how much
 * more or less the five kinds of pair get (+2 to -2). Which kind a pair is depends on the two characters.
 */
export const FE10_SUPPORT_TOTALS = [50, 100, 150] as const
export const FE10_PAIR_OFFSETS = [2, 1, 0, -1, -2] as const
export const FE10_SUPPORT_ACTIONS: { action: string; points: number }[] = [
  { action: 'Shove or Smite the other unit', points: 1 },
  { action: 'Start a turn next to the other unit', points: 3 },
  { action: 'Use a staff or Sacrifice on the other unit', points: 4 },
  { action: 'Start a turn carrying the other unit', points: 5 },
  { action: 'Both start the chapter on the map (once per chapter)', points: 15 },
]
