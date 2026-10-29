import { useState } from 'react'
import type { ChapterWeapon } from './ChapterWeapons'

const CELL = 'py-1 pr-2 sm:pr-3'
type Steps = { mt: number; hit: number; crit: number }
const NONE: Steps = { mt: 0, hit: 0, crit: 0 }
const ROWS: { key: keyof Steps; label: string; per: number }[] = [
  { key: 'mt', label: 'Mt', per: 1 },
  { key: 'hit', label: 'Hit', per: 5 },
  { key: 'crit', label: 'Crit', per: 3 },
]
/** Steps per stat, steps in all, and the highest Crit a forge reaches (Serenes Forest). */
const MAX_STEPS = 5
const MAX_TOTAL = 8
const MAX_CRIT = 50
/** A stat's n-th step costs n/2 of the weapon's worth, so n steps cost n(n+1)/4 of it (Serenes Forest). */
const stepCost = (worth: number, n: number) => Math.floor((worth * n * (n + 1)) / 4)

/** Awakening's forge for one weapon (any armory's): pick the steps for each stat and see the cost. */
export function Fe13Forge({ weapon: w }: { weapon: ChapterWeapon & { forge?: true } }) {
  const [steps, setSteps] = useState<Steps>(NONE)
  if (!w.forge || !w.worth) return null
  const worth = w.worth
  const used = steps.mt + steps.hit + steps.crit
  const critRoom = Math.max(0, Math.floor((MAX_CRIT - (w.crit ?? 0)) / 3))
  const max = (key: keyof Steps) => Math.min(MAX_STEPS, steps[key] + MAX_TOTAL - used, key === 'crit' ? critRoom : MAX_STEPS)
  const cost = ROWS.reduce((sum, r) => sum + stepCost(worth, steps[r.key]), 0)
  const base = { mt: w.mt ?? 0, hit: w.hit ?? 0, crit: w.crit ?? 0 }
  const step = (key: keyof Steps, by: number) => setSteps((s) => ({ ...s, [key]: Math.max(0, Math.min(max(key), s[key] + by)) }))
  const button = 'h-7 w-7 rounded border border-neutral-700 bg-neutral-900 text-neutral-200 disabled:opacity-30'
  return (
    <div className="flex flex-col gap-2">
      <h3 className="font-semibold text-neutral-100">Forge</h3>
      <table className="w-full border-collapse text-xs sm:text-sm">
        <thead>
          <tr className="border-b border-neutral-700 text-left text-neutral-400">
            <th className={CELL}>Stat</th>
            <th className={CELL}>Base</th>
            <th className={CELL}>Forged</th>
            <th className={CELL}>Steps</th>
          </tr>
        </thead>
        <tbody>
          {ROWS.map(({ key, label, per }) => (
            <tr key={key} className="border-b border-neutral-800">
              <td className={`${CELL} text-neutral-100`}>{label}</td>
              <td className={CELL}>{base[key]}</td>
              <td className={`${CELL} ${steps[key] ? 'text-emerald-300' : ''}`}>{base[key] + per * steps[key]}</td>
              <td className={`${CELL} whitespace-nowrap`}>
                <button className={button} onClick={() => step(key, -1)} disabled={!steps[key]} aria-label={`Less ${label}`}>
                  −
                </button>
                <span className="inline-block w-12 text-center text-neutral-300">{steps[key]}</span>
                <button className={button} onClick={() => step(key, 1)} disabled={steps[key] >= max(key)} aria-label={`More ${label}`}>
                  +
                </button>
                <span className="ml-2 text-neutral-500">+{per} each</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="text-neutral-300">
        Cost: <span className="text-lg text-amber-200">{cost.toLocaleString()}G</span>{' '}
        <span className="text-neutral-500">
          ({used} of {MAX_TOTAL} steps)
        </span>
      </p>
      <ul className="list-disc space-y-1 pl-5 text-neutral-400">
        <li>
          Up to {MAX_STEPS} steps in each stat and {MAX_TOTAL} in all; Crit stops at {MAX_CRIT}.
        </li>
        <li>A stat's first step costs half the weapon's worth, its second a whole worth more, then 1½, 2 and 2½ times its worth.</li>
        <li>Forging names the weapon. Uses, rank and range stay the base weapon's.</li>
        <li className="text-neutral-500">The forge's limits and costs are from Serenes Forest; not yet checked in the game's code.</li>
      </ul>
    </div>
  )
}
