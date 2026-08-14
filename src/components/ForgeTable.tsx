import { useState } from 'react'
import { copiesRequiredFromScratch, cumulativeForgeBonus, mineralsRequiredFromScratch } from '../logic/forge'
import type { Weapon } from '../data/types'
import { FORGE_MINERALS } from '../data/types'

export function ForgeTable({ weapon, highlightRank }: { weapon: Weapon; highlightRank?: number }) {
  const [proficientSmith, setProficientSmith] = useState(false)

  if (!weapon.forgeable) {
    return (
      <p className="text-sm text-neutral-500">
        Not forgeable — the Smithy excludes non-standard weapons (dragonstones, etc.) and any weapon
        you can only ever hold one copy of.
      </p>
    )
  }

  const mineral = FORGE_MINERALS[weapon.category] ?? '—'
  const ranks = [0, 1, 2, 3, 4, 5, 6, 7]

  return (
    <div className="overflow-x-auto">
      <p className="mb-2 text-sm text-neutral-400">
        Forging mineral: <span className="text-neutral-200">{mineral}</span> — combine two copies of
        the previous rank plus mineral(s) to reach the next.
      </p>
      <label className="mb-2 flex items-center gap-2 text-sm text-neutral-300">
        <input
          type="checkbox"
          checked={proficientSmith}
          onChange={(e) => setProficientSmith(e.target.checked)}
        />
        Smith is proficient with {weapon.category} (−1 mineral per combine, never below 1)
      </label>
      <table className="w-full min-w-[560px] border-collapse text-sm">
        <thead>
          <tr className="border-b border-neutral-700 text-left text-neutral-400">
            <th className="py-1 pr-3">Rank</th>
            <th className="py-1 pr-3">Mt</th>
            <th className="py-1 pr-3">Hit</th>
            <th className="py-1 pr-3">Crit</th>
            <th className="py-1 pr-3">Copies from scratch</th>
            <th className="py-1 pr-3">Minerals from scratch</th>
          </tr>
        </thead>
        <tbody>
          {ranks.map((rank) => {
            const bonus = cumulativeForgeBonus(weapon.canCrit, rank)
            return (
              <tr
                key={rank}
                className={`border-b border-neutral-800 ${rank === highlightRank ? 'bg-emerald-950' : ''}`}
              >
                <td className="py-1 pr-3 text-neutral-200">{rank === 0 ? 'Base' : `+${rank}`}</td>
                <td className="py-1 pr-3">{weapon.stats.mt + bonus.mt}</td>
                <td className="py-1 pr-3">{weapon.stats.hit + bonus.hit}</td>
                <td className="py-1 pr-3">{weapon.stats.crit + bonus.crit}</td>
                <td className="py-1 pr-3 text-neutral-400">{rank === 0 ? '—' : copiesRequiredFromScratch(rank)}</td>
                <td className="py-1 pr-3 text-neutral-400">
                  {rank === 0
                    ? '—'
                    : `${mineralsRequiredFromScratch(weapon.canCrit, rank, proficientSmith)} ${mineral}`}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
