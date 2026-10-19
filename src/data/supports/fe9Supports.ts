/*
 * Path of Radiance's support bonuses: each unit has an affinity, and each affinity adds these
 * amounts per support level. From the Fire Emblem Wiki's support bonus page for the game (it matches
 * Serenes Forest's); the values aren't in the game's data files, so they're kept here by hand.
 */
export interface Affinity {
  name: string
  /** Per support level. A pair's bonus is (both affinities added together) x level, rounded down. */
  atk: number
  def: number
  hit: number
  avoid: number
}

export const FE9_AFFINITIES: Affinity[] = [
  { name: 'Fire', atk: 0.5, def: 0, hit: 2.5, avoid: 0 },
  { name: 'Thunder', atk: 0, def: 0.5, hit: 0, avoid: 2.5 },
  { name: 'Wind', atk: 0, def: 0, hit: 2.5, avoid: 2.5 },
  { name: 'Water', atk: 0.5, def: 0.5, hit: 0, avoid: 0 },
  { name: 'Dark', atk: 0.5, def: 0, hit: 0, avoid: 2.5 },
  { name: 'Light', atk: 0, def: 0.5, hit: 2.5, avoid: 0 },
  { name: 'Heaven', atk: 0, def: 0, hit: 5, avoid: 0 },
  { name: 'Earth', atk: 0, def: 0, hit: 0, avoid: 5 },
]

export const FE9_LEVELS = ['C', 'B', 'A'] as const

/** A pair's bonus at a support level (C = 1, B = 2, A = 3): both affinities added, times the level, rounded down. */
export function fe9SupportBonus(a: Affinity, b: Affinity, level: number) {
  const total = (k: 'atk' | 'def' | 'hit' | 'avoid') => Math.floor((a[k] + b[k]) * level)
  return { atk: total('atk'), def: total('def'), hit: total('hit'), avoid: total('avoid') }
}
