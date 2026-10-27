/** A GBA game's support table, as scripts/build-fe6-supports.py and build-gba-supports.py write it. */
export interface GbaSupportData {
  affinities: readonly { name: string; atk: number; def: number; hit: number; avoid: number; crit: number; dodge: number }[]
  /** Support points needed for each level. */
  levels: { C: number; B: number; A: number }
  /** How many tiles away (counting steps) a partner still counts. */
  reach: number
  /** The most support levels a unit can hold. */
  maxLevels: number
}

export interface GbaPartner {
  affinity: string
  /** 1 C, 2 B, 3 A. */
  level: number
}

type Stat = 'atk' | 'def' | 'hit' | 'avoid' | 'crit' | 'dodge'
const STATS: Stat[] = ['atk', 'def', 'hit', 'avoid', 'crit', 'dodge']

/**
 * A unit's support bonus in The Binding Blade, The Blazing Blade and The Sacred Stones, the way their battle code works it out (the
 * same routine in all three: scripts/build-fe6-supports.py, build-gba-supports.py): for each partner in range, its own affinity's row
 * and the partner's, times the level; the totals halved once, rounded down.
 */
export function gbaSupportBonus(data: GbaSupportData, own: string, partners: GbaPartner[]): Record<Stat, number> {
  const row = (name: string) => data.affinities.find((a) => a.name === name)!
  const sum = Object.fromEntries(STATS.map((k) => [k, 0])) as Record<Stat, number>
  for (const p of partners) for (const k of STATS) sum[k] += (row(own)[k] + row(p.affinity)[k]) * p.level
  return Object.fromEntries(STATS.map((k) => [k, Math.floor(sum[k] / 2)])) as Record<Stat, number>
}
