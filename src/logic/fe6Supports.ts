import { FE6_SUPPORTS } from '../data/fe6/fe6Supports'

export interface Fe6Partner {
  affinity: string
  /** 1 C, 2 B, 3 A. */
  level: number
}

type Stat = 'atk' | 'def' | 'hit' | 'avoid' | 'crit' | 'dodge'
const STATS: Stat[] = ['atk', 'def', 'hit', 'avoid', 'crit', 'dodge']

/**
 * A unit's support bonus in The Binding Blade, the way the battle code works it out (scripts/build-fe6-supports.py): for each
 * partner in range, its own affinity's row and the partner's, times the level; the totals halved once, rounded down.
 */
export function fe6SupportBonus(own: string, partners: Fe6Partner[]): Record<Stat, number> {
  const row = (name: string) => FE6_SUPPORTS.affinities.find((a) => a.name === name)!
  const sum = Object.fromEntries(STATS.map((k) => [k, 0])) as Record<Stat, number>
  for (const p of partners) for (const k of STATS) sum[k] += (row(own)[k] + row(p.affinity)[k]) * p.level
  return Object.fromEntries(STATS.map((k) => [k, Math.floor(sum[k] / 2)])) as Record<Stat, number>
}
