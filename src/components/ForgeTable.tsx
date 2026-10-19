import { useState } from 'react'
import { copiesRequiredFromScratch, cumulativeForgeBonus, mineralsRequiredFromScratch } from '../logic/forge'
import type { Weapon } from '../data/types'
import { FORGE_MINERALS } from '../data/types'

const CELL = 'py-1 pr-2 sm:pr-3'

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
    <div>
      <p className="mb-2 text-sm text-neutral-400">
        Forging mineral: <span className="text-neutral-200">{mineral}</span> — combine two copies of
        the previous rank plus mineral(s) to reach the next. Copies and {mineral} below are the totals
        from scratch.
      </p>
      <label className="mb-2 flex items-center gap-2 text-sm text-neutral-300">
        <input
          type="checkbox"
          checked={proficientSmith}
          onChange={(e) => setProficientSmith(e.target.checked)}
        />
        Smith is proficient with {weapon.category} (−1 mineral per combine, never below 1)
      </label>
      {/* Fits a phone: short headers, numbers only. Copies and minerals count from scratch (all base copies). */}
      <table className="w-full border-collapse text-xs sm:text-sm">
        <thead>
          <tr className="border-b border-neutral-700 text-left text-neutral-400">
            <th className={CELL}>Rank</th>
            <th className={CELL}>Mt</th>
            <th className={CELL}>Hit</th>
            <th className={CELL}>Crit</th>
            <th className={CELL} title="Base copies needed from scratch">Copies</th>
            <th className={CELL} title={`${mineral} needed from scratch`}>{mineral}</th>
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
                <td className={`${CELL} text-neutral-200`}>{rank === 0 ? 'Base' : `+${rank}`}</td>
                <td className={CELL}>{weapon.stats.mt + bonus.mt}</td>
                <td className={CELL}>{weapon.stats.hit + bonus.hit}</td>
                <td className={CELL}>{weapon.stats.crit + bonus.crit}</td>
                <td className={`${CELL} text-neutral-400`}>{rank === 0 ? '—' : copiesRequiredFromScratch(rank)}</td>
                <td className={`${CELL} text-neutral-400`}>
                  {rank === 0 ? '—' : mineralsRequiredFromScratch(weapon.canCrit, rank, proficientSmith)}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
