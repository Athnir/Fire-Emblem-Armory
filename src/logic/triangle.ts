/** What one step of the weapon triangle is worth: to hit, to attack (Mt or Atk) and to avoid. */
export interface TriangleBonus {
  hit: number
  mt?: number
  avoid?: number
}

/**
 * A game's weapon triangle, as its battle code applies it, for the weapon triangle tab. Each game's numbers are generated from its own
 * files (`scripts/build-triangles.py`, FE4's `scripts/build-fe4-bonuses.py`); the sentences are in the game's own file.
 */
export interface TriangleRules {
  /** Each weapon type and the types it beats, in the game's order. */
  beats: Readonly<Record<string, readonly string[]>>
  /** What sits outside the triangle. */
  outside: string
  /** What the advantage is worth: one entry, or (Fates) one per rank of the advantaged unit's weapon, from E up. */
  advantage: readonly ({ rank?: string } & TriangleBonus)[]
  /** 'mirror': the other side loses as much. 'winner-only' (FE4): only the advantaged side gains. */
  loser: 'mirror' | 'winner-only'
  /** What the game calls the attack part ('Mt', or Fates' 'Atk'). */
  mtLabel: string
  /** Special effects and how it stacks, one sentence each. */
  rules: readonly string[]
  /** Fates: reaver weapons flip the triangle and double it when only one side holds one. */
  reaver?: boolean
  /** Radiant Dawn: a difficulty that turns it off for both sides. */
  offOn?: string
  /** Fates: what each weapon rank adds on its own, by weapon type and rank from E up ([attack or healing, hit]). */
  rankBonus?: {
    rows: readonly { types: string; byRank: Readonly<Record<string, readonly [number, number]>>; first: string }[]
    rules: readonly string[]
  }
  /** FE4 and Radiant Dawn: the commander's leadership, by stars (0 up). */
  leadership?: { byStars: readonly TriangleBonus[]; rules: readonly string[] }
}

export interface TriangleOutcome {
  /** +1 advantage, -1 disadvantage, 0 neither; reavers make it +2 / -2. */
  level: number
  you: TriangleBonus
  foe: TriangleBonus
  /** Fates: the side at a disadvantage loses its weapon rank bonus. */
  youLoseRankBonus: boolean
  foeLoseRankBonus: boolean
}

const scale = (b: TriangleBonus, k: number): TriangleBonus => ({
  hit: b.hit * k,
  ...(b.mt !== undefined && { mt: b.mt * k }),
  ...(b.avoid !== undefined && { avoid: b.avoid * k }),
})

/** The triangle's effect on both sides when `you` attack with one weapon type and the foe holds another. */
export function triangleOutcome(
  rules: TriangleRules,
  you: string,
  foe: string,
  opts: { rank?: string; yourReaver?: boolean; foeReaver?: boolean; off?: boolean } = {},
): TriangleOutcome {
  let level = rules.beats[you]?.includes(foe) ? 1 : rules.beats[foe]?.includes(you) ? -1 : 0
  if (rules.reaver && !!opts.yourReaver !== !!opts.foeReaver) level *= -2
  if (opts.off) level = 0
  const row = rules.advantage.find((a) => a.rank === opts.rank) ?? rules.advantage[rules.advantage.length - 1]
  const none = scale(row, 0)
  const sideGain = (k: number) => (rules.loser === 'mirror' ? scale(row, k) : k > 0 ? scale(row, k) : none)
  return {
    level,
    you: sideGain(level),
    foe: sideGain(-level),
    youLoseRankBonus: !!rules.rankBonus && level < 0,
    foeLoseRankBonus: !!rules.rankBonus && level > 0,
  }
}
